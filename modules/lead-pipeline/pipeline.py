"""Lead-list pipeline: the deterministic stages of an outbound list build.

The full motion is: discover -> clean -> dedup-against-CRM -> enrich -> score.
Discovery and enrichment are judgement/IO steps your assistant runs with MCP
tools (web search, an enrichment provider, public registries) — see the
/build-list skill. THIS script owns the three deterministic stages, each of
which reads a CSV and writes the next, so the pipeline is debuggable and
resumable: you can inspect (or hand-fix) the output of any stage.

    clean   raw candidates      -> normalize, drop junk, dedup within the list
    dedup   against your CRM     -> tag each row proceed / warm / skip
    score   against your ICP     -> fit score + tier, write a ranked top-N

The senior move this encodes: DEDUP AGAINST YOUR CRM BEFORE YOU ENRICH. You
never spend enrichment credits on a company you already know, and you never
cold-email a contact who is already a relationship or an open deal.

All stdlib. Lead CSVs are free-form; these columns are used when present and
everything else is preserved untouched:
    company, domain, contact_name, contact_email, title, country
plus any numeric size column you name in the ICP config.

Examples:
    python3 pipeline.py clean  --in raw.csv --out reports/lead-pipeline/01-cleaned.csv --country DE,BR
    python3 pipeline.py dedup  --in reports/lead-pipeline/01-cleaned.csv --crm data/crm-merge/contacts.json --out reports/lead-pipeline/02-deduped.csv
    python3 pipeline.py score  --in reports/lead-pipeline/02-deduped.csv --icp modules/lead-pipeline/icp.json --out reports/lead-pipeline/03-scored.csv --top 50
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_REPORTS = PROJECT_DIR / "reports" / "lead-pipeline"

# Legal-form suffixes stripped when normalizing a company name for matching.
LEGAL_SUFFIXES = {
    "gmbh", "ug", "ag", "kg", "ohg", "mbh", "se",        # DE
    "ltda", "sa", "eireli", "me", "epp",                  # BR / LATAM
    "inc", "llc", "ltd", "corp", "co", "company", "plc",  # EN
    "bv", "nv", "oy", "ab", "as", "sarl", "srl", "spa",   # EU
}


def norm_text(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s).strip()


def norm_company(s: str) -> str:
    """Lowercased, punctuation- and legal-suffix-stripped company key."""
    s = norm_text(s).lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    tokens = [t for t in s.split() if t and t not in LEGAL_SUFFIXES]
    return " ".join(tokens)


def norm_domain(s: str) -> str:
    s = norm_text(s).lower()
    s = re.sub(r"^https?://", "", s)
    s = re.sub(r"^www\.", "", s)
    s = s.split("/")[0].strip()
    return s


def email_domain(email: str) -> str:
    email = norm_text(email).lower()
    return email.split("@", 1)[1] if "@" in email else ""


def read_csv(path: Path) -> tuple[list[dict], list[str]]:
    if not path.exists():
        sys.exit(f"ERROR: input not found: {path}")
    with path.open(encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = reader.fieldnames or []
    return rows, list(fields)


def write_csv(rows: list[dict], fields: list[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Union of declared fields and any keys present on rows, declared order first.
    seen = list(fields)
    for r in rows:
        for k in r:
            if k not in seen:
                seen.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=seen, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"  wrote {len(rows)} rows -> {path}")


def get(row: dict, *names: str) -> str:
    """First non-empty value among case-insensitive column aliases."""
    lower = {k.lower(): v for k, v in row.items()}
    for n in names:
        v = lower.get(n.lower())
        if v and str(v).strip():
            return str(v).strip()
    return ""


# ---------- Stage: clean ----------

def stage_clean(args) -> None:
    rows, fields = read_csv(Path(args.infile))
    countries = {c.strip().upper() for c in args.country.split(",") if c.strip()} if args.country else set()

    kept: list[dict] = []
    seen_keys: set[str] = set()
    dropped_empty = dropped_country = dropped_dup = 0

    for r in rows:
        company = get(r, "company", "company name", "account")
        domain = norm_domain(get(r, "domain", "website", "url"))
        if not domain:
            domain = email_domain(get(r, "contact_email", "email"))
        # Must have something to identify the account.
        if not company and not domain:
            dropped_empty += 1
            continue
        if countries:
            country = get(r, "country", "country_code", "region").upper()
            if country and country not in countries:
                dropped_country += 1
                continue
        # Dedup within the list on domain, falling back to normalized company.
        key = f"d:{domain}" if domain else f"c:{norm_company(company)}"
        if key in seen_keys:
            dropped_dup += 1
            continue
        seen_keys.add(key)
        if domain:
            r["domain"] = domain
        kept.append(r)

    out = Path(args.out) if args.out else DEFAULT_REPORTS / "01-cleaned.csv"
    print(f"clean: {len(rows)} in -> {len(kept)} kept "
          f"(dropped {dropped_empty} empty, {dropped_country} off-country, {dropped_dup} dup)")
    write_csv(kept, fields, out)


# ---------- Stage: dedup against CRM ----------

def load_crm(path: Path) -> dict:
    """Build lookup indexes from a crm-merge contacts.json."""
    emails: set[str] = set()
    email_domains: dict[str, str] = {}   # domain -> a contact name (for the report)
    companies: dict[str, str] = {}       # normalized company -> contact name
    if not path.exists():
        print(f"WARN: CRM file not found ({path}); every lead will be 'proceed'.",
              file=sys.stderr)
        return {"emails": emails, "email_domains": email_domains, "companies": companies}
    data = json.loads(path.read_text(encoding="utf-8"))
    for rec in data:
        name = rec.get("fn") or ""
        for e in rec.get("emails", []) or []:
            e = e.lower().strip()
            if "@" in e:
                emails.add(e)
                dom = e.split("@", 1)[1]
                # Skip free webmail domains as account signals.
                if dom and dom not in FREEMAIL:
                    email_domains.setdefault(dom, name)
        comp = norm_company(rec.get("company") or "")
        if comp:
            companies.setdefault(comp, name)
    return {"emails": emails, "email_domains": email_domains, "companies": companies}


FREEMAIL = {
    "gmail.com", "googlemail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "live.com", "icloud.com", "gmx.de", "gmx.net", "web.de", "aol.com",
    "proton.me", "protonmail.com", "t-online.de",
}


def stage_dedup(args) -> None:
    rows, fields = read_csv(Path(args.infile))
    crm = load_crm(Path(args.crm))

    counts = {"proceed": 0, "warm": 0, "skip": 0}
    for r in rows:
        lead_email = get(r, "contact_email", "email").lower()
        lead_dom = norm_domain(get(r, "domain", "website", "url")) or email_domain(lead_email)
        lead_comp = norm_company(get(r, "company", "company name", "account"))

        disposition, match_on, match_name = "proceed", "", ""

        # 1. Exact person we already know -> skip (do not cold-outreach).
        if lead_email and lead_email in crm["emails"]:
            disposition, match_on = "skip", "email"
        # 2. We know someone at this account (by corporate email domain) -> warm.
        elif lead_dom and lead_dom not in FREEMAIL and lead_dom in crm["email_domains"]:
            disposition, match_on = "warm", "domain"
            match_name = crm["email_domains"][lead_dom]
        # 3. We know someone at this account (by company name) -> warm.
        elif lead_comp and lead_comp in crm["companies"]:
            disposition, match_on = "warm", "company"
            match_name = crm["companies"][lead_comp]

        r["disposition"] = disposition
        r["crm_match_on"] = match_on
        r["crm_known_contact"] = match_name
        counts[disposition] += 1

    out = Path(args.out) if args.out else DEFAULT_REPORTS / "02-deduped.csv"
    total = len(rows) or 1
    print(f"dedup against CRM: {len(rows)} leads")
    print(f"  proceed (cold, no match):        {counts['proceed']:>5}  "
          f"({100*counts['proceed']//total}%)")
    print(f"  warm (known account, new person):{counts['warm']:>5}  "
          f"({100*counts['warm']//total}%)  -> route via your existing contact")
    print(f"  skip (already a known contact):  {counts['skip']:>5}  "
          f"({100*counts['skip']//total}%)  -> do NOT cold-outreach")
    if not (crm["emails"] or crm["companies"]):
        print("  (CRM was empty — run modules/crm-merge first to make this stage useful.)")
    write_csv(rows, fields, out)


# ---------- Stage: score against ICP ----------

def load_icp(path: Path) -> dict:
    if not path.exists():
        sys.exit(f"ERROR: ICP config not found: {path}. "
                 f"Copy modules/lead-pipeline/icp.example.json to {path} and edit it.")
    return json.loads(path.read_text(encoding="utf-8"))


def score_row(r: dict, icp: dict) -> tuple[int, list[str]]:
    score, why = 0, []

    countries = {c.upper() for c in icp.get("target_countries", [])}
    if countries:
        country = get(r, "country", "country_code", "region").upper()
        if country and country in countries:
            pts = icp.get("country_points", 0)
            score += pts
            why.append(f"+{pts} country")

    kws = [k.lower() for k in icp.get("title_keywords", [])]
    title = get(r, "title", "position", "role").lower()
    if kws and title and any(k in title for k in kws):
        pts = icp.get("title_points", 0)
        score += pts
        why.append(f"+{pts} title")

    if get(r, "domain", "website", "url"):
        pts = icp.get("has_domain_points", 0)
        score += pts
        if pts:
            why.append(f"+{pts} domain")

    if get(r, "contact_email", "email"):
        pts = icp.get("has_email_points", 0)
        score += pts
        if pts:
            why.append(f"+{pts} email")

    size_field = icp.get("size_field")
    if size_field:
        raw = get(r, size_field)
        digits = re.sub(r"[^\d]", "", raw)
        if digits:
            n = int(digits)
            lo = icp.get("size_min", 0)
            hi = icp.get("size_max", 10**9)
            if lo <= n <= hi:
                pts = icp.get("size_points", 0)
                score += pts
                why.append(f"+{pts} size")

    return score, why


def stage_score(args) -> None:
    rows, fields = read_csv(Path(args.infile))
    icp = load_icp(Path(args.icp))
    tiers = icp.get("tiers", {"A": 70, "B": 45, "C": 0})

    scored = []
    for r in rows:
        # Never rank a contact we should not cold-outreach.
        if r.get("disposition") == "skip":
            r["fit_score"] = 0
            r["fit_tier"] = "skip"
            r["fit_reasons"] = "already a known contact"
            scored.append(r)
            continue
        s, why = score_row(r, icp)
        tier = next((t for t, thr in sorted(tiers.items(), key=lambda kv: -kv[1]) if s >= thr), "C")
        r["fit_score"] = s
        r["fit_tier"] = tier
        r["fit_reasons"] = ", ".join(why)
        scored.append(r)

    scored.sort(key=lambda r: -int(r.get("fit_score") or 0))

    out = Path(args.out) if args.out else DEFAULT_REPORTS / "03-scored.csv"
    write_csv(scored, fields, out)

    dist: dict[str, int] = {}
    for r in scored:
        dist[r["fit_tier"]] = dist.get(r["fit_tier"], 0) + 1
    print("score: tier distribution " + ", ".join(f"{t}={dist[t]}" for t in sorted(dist)))

    if args.top:
        actionable = [r for r in scored if r.get("disposition") != "skip"][: args.top]
        top_path = out.with_name(out.stem.replace("03-scored", "04-top") + ".csv") \
            if "03-scored" in out.stem else out.with_name(f"top-{args.top}.csv")
        write_csv(actionable, fields, top_path)
        print(f"  top {len(actionable)} actionable leads -> {top_path}")


def main():
    ap = argparse.ArgumentParser(description="Deterministic stages of a lead-list build.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("clean", help="normalize, drop junk, dedup within the list")
    c.add_argument("--in", dest="infile", required=True)
    c.add_argument("--out")
    c.add_argument("--country", default="", help="allowlist, comma-separated (e.g. DE,BR)")
    c.set_defaults(func=stage_clean)

    d = sub.add_parser("dedup", help="tag each lead proceed/warm/skip vs your CRM")
    d.add_argument("--in", dest="infile", required=True)
    d.add_argument("--crm", default=str(PROJECT_DIR / "data" / "crm-merge" / "contacts.json"))
    d.add_argument("--out")
    d.set_defaults(func=stage_dedup)

    s = sub.add_parser("score", help="ICP fit score + tier + ranked top-N")
    s.add_argument("--in", dest="infile", required=True)
    s.add_argument("--icp", default=str(Path(__file__).parent / "icp.json"))
    s.add_argument("--out")
    s.add_argument("--top", type=int, default=50)
    s.set_defaults(func=stage_score)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
