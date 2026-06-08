"""CRM merge backbone. Folds Google Contacts (vCards), LinkedIn Connections,
LinkedIn message frequency, and vault People/ notes into a single local SQLite
database plus a JSON export plus a self-contained offline HTML browser.

Design goals:
- You own the data (no external CRM dependency, no live API calls).
- Identity merge across sources (email > LinkedIn slug > normalized name),
  using union-find so a person seen in three exports collapses to one record.
- A common-name-collision guard, so two different "John Smith" rows are not
  fused just because they share a generic name.
- Relationship-strength signal (LinkedIn message count) ranks records.
- Idempotent: safe to re-run; rebuilds the DB from scratch each time.

Everything is stdlib. Bring your own static exports:
  - Google Takeout zip (Contacts as vCard) — https://takeout.google.com
  - LinkedIn data export (Connections.csv, messages.csv) — Settings > Data privacy
  - your vault's People/ notes (optional)

Usage:
  python3 build.py \
    --takeout-zip ~/Downloads/takeout-XXXX.zip \
    --linkedin-dir ~/Downloads/linkedin-export \
    --vault-people vault/People \
    --me "Your Full Name" \
    --out data/crm-merge
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import sys
import unicodedata
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_LINKEDIN_DIR = PROJECT_DIR / "data" / "linkedin"
DEFAULT_VAULT_PEOPLE = PROJECT_DIR / "vault" / "People"
DEFAULT_OUT = PROJECT_DIR / "data" / "crm-merge"


def find_takeout_zip() -> str:
    """Best-effort: newest *.zip in ~/Downloads whose name mentions 'takeout'."""
    downloads = Path.home() / "Downloads"
    if not downloads.exists():
        return ""
    candidates = [
        p for p in downloads.glob("*.zip")
        if "takeout" in p.name.lower() or "google" in p.name.lower()
    ]
    if not candidates:
        return ""
    return str(max(candidates, key=lambda p: p.stat().st_mtime))


def normalize_name(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z\s]", "", s).strip().lower()
    return re.sub(r"\s+", " ", s)


def normalize_email(s: str) -> str:
    return s.strip().lower() if s else ""


# ---------- vCard parser (no deps) ----------

def parse_vcards(blob: str) -> list[dict]:
    cards = []
    for raw in blob.split("END:VCARD"):
        if "BEGIN:VCARD" not in raw:
            continue
        card = {"emails": [], "phones": [], "orgs": [], "titles": [],
                "addresses": [], "categories": [], "fn": None, "n": None,
                "bday": None, "note": None, "url": None}
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("BEGIN:") or line.startswith("VERSION"):
                continue
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key_upper = key.upper().split(";")[0]
            if key_upper == "FN":
                card["fn"] = value
            elif key_upper == "N":
                card["n"] = value
            elif key_upper == "EMAIL":
                e = normalize_email(value)
                if e and e not in card["emails"]:
                    card["emails"].append(e)
            elif key_upper == "TEL":
                p = re.sub(r"[^\d+]", "", value)
                if p and p not in card["phones"]:
                    card["phones"].append(p)
            elif key_upper == "ORG":
                card["orgs"].append(value)
            elif key_upper == "TITLE":
                card["titles"].append(value)
            elif key_upper == "ADR":
                card["addresses"].append(value)
            elif key_upper == "BDAY":
                card["bday"] = value
            elif key_upper == "NOTE":
                card["note"] = value
            elif key_upper == "URL":
                card["url"] = value
            elif key_upper == "CATEGORIES":
                card["categories"] = [c.strip() for c in value.split(",")]
        if card["fn"] or card["emails"] or card["phones"]:
            cards.append(card)
    return cards


def load_google_contacts(zip_path: Path) -> list[dict]:
    if not zip_path or not zip_path.exists():
        print(f"WARN: Takeout zip not found ({zip_path}), skipping Google Contacts",
              file=sys.stderr)
        return []
    contacts = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if not info.filename.endswith(".vcf") or "Contacts" not in info.filename:
                continue
            with zf.open(info.filename) as f:
                blob = f.read().decode("utf-8", errors="replace")
            for c in parse_vcards(blob):
                c["_source"] = "google_contacts"
                c["_source_file"] = info.filename.split("/")[-1]
                contacts.append(c)
    return contacts


# ---------- LinkedIn ----------

def load_linkedin_connections(folder: Path) -> list[dict]:
    p = folder / "Connections.csv"
    if not p.exists():
        return []
    text = p.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines(keepends=True)
    # LinkedIn prefixes the export with a "Notes:" preamble + a blank line.
    if lines and lines[0].lstrip().startswith("Notes:"):
        blank_at = next((i for i, line in enumerate(lines) if not line.strip()), 0)
        body = "".join(lines[blank_at + 1:])
    else:
        body = text
    rows = list(csv.DictReader(body.splitlines()))
    out = []
    for r in rows:
        first = (r.get("First Name") or "").strip()
        last = (r.get("Last Name") or "").strip()
        fn = " ".join(filter(None, [first, last])).strip()
        if not fn:
            continue
        out.append({
            "fn": fn,
            "first_name": first,
            "last_name": last,
            "linkedin_url": (r.get("URL") or "").strip(),
            "email": normalize_email(r.get("Email Address") or ""),
            "company": (r.get("Company") or "").strip(),
            "position": (r.get("Position") or "").strip(),
            "connected_on": (r.get("Connected On") or "").strip(),
            "_source": "linkedin",
        })
    return out


def load_linkedin_message_stats(folder: Path, me_names: tuple[str, ...]) -> dict[str, int]:
    """Returns correspondent-name -> message count, used as a relationship signal."""
    p = folder / "messages.csv"
    if not p.exists():
        return {}
    counts: dict[str, int] = defaultdict(int)
    with p.open(encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            frm = (r.get("FROM") or "").strip()
            to = (r.get("TO") or "").strip()
            other = to if frm in me_names else frm
            if other and other not in me_names and other != "LinkedIn Member":
                counts[other] += 1
    return dict(counts)


# ---------- Vault People/ ----------

def load_vault_people(folder: Path) -> list[dict]:
    if not folder.exists():
        return []
    out = []
    for p in sorted(folder.glob("*.md")):
        name = p.stem
        try:
            rel = str(p.relative_to(PROJECT_DIR))
        except ValueError:
            rel = str(p)
        out.append({
            "fn": name,
            "vault_note": rel,
            "_source": "vault",
        })
    return out


# ---------- Merge engine ----------

def make_keys(record: dict) -> list[str]:
    """Returns the set of merge keys this record exposes."""
    keys: list[str] = []
    if record.get("fn"):
        n = normalize_name(record["fn"])
        # Require at least 2 word tokens AND >= 5 letters total, so we never
        # collapse records on a single common first name ("Pedro", "Anna").
        if n and " " in n and len(n.replace(" ", "")) >= 5:
            keys.append(f"name:{n}")
    for e in record.get("emails", []) or [record.get("email")]:
        if e and "@" in e:
            keys.append(f"email:{e}")
    if record.get("linkedin_url"):
        m = re.search(r"linkedin\.com/in/([a-zA-Z0-9_-]+)", record["linkedin_url"])
        if m:
            keys.append(f"linkedin:{m.group(1).lower()}")
    return keys


def merge_records(google: list[dict], linkedin: list[dict],
                  msg_counts: dict[str, int],
                  vault: list[dict],
                  name_collision_threshold: int) -> list[dict]:
    """Union-find merge across all sources. Returns merged list of dicts."""
    all_records: list[dict] = []

    for r in google:
        all_records.append({
            "fn": r.get("fn") or "",
            "emails": list(r.get("emails", [])),
            "phones": list(r.get("phones", [])),
            "company": (r.get("orgs") or [""])[0],
            "position": (r.get("titles") or [""])[0],
            "address": (r.get("addresses") or [""])[0],
            "bday": r.get("bday"),
            "note": r.get("note"),
            "url": r.get("url"),
            "categories": r.get("categories", []),
            "linkedin_url": "",
            "connected_on": "",
            "vault_note": "",
            "linkedin_messages": 0,
            "sources": ["google_contacts"],
            "_source_files": [r.get("_source_file", "")],
        })
    for r in linkedin:
        all_records.append({
            "fn": r.get("fn") or "",
            "emails": [r["email"]] if r.get("email") else [],
            "phones": [],
            "company": r.get("company") or "",
            "position": r.get("position") or "",
            "address": "",
            "bday": None,
            "note": None,
            "url": "",
            "categories": [],
            "linkedin_url": r.get("linkedin_url") or "",
            "connected_on": r.get("connected_on") or "",
            "vault_note": "",
            "linkedin_messages": msg_counts.get(r.get("fn", ""), 0),
            "sources": ["linkedin"],
            "_source_files": [],
        })
    for r in vault:
        all_records.append({
            "fn": r.get("fn") or "",
            "emails": [],
            "phones": [],
            "company": "",
            "position": "",
            "address": "",
            "bday": None,
            "note": None,
            "url": "",
            "categories": [],
            "linkedin_url": "",
            "connected_on": "",
            "vault_note": r.get("vault_note") or "",
            "linkedin_messages": 0,
            "sources": ["vault"],
            "_source_files": [],
        })

    # Build key -> record-indices index, then union-find.
    key_to_idx: dict[str, list[int]] = defaultdict(list)
    for i, rec in enumerate(all_records):
        for k in make_keys(rec):
            key_to_idx[k].append(i)

    parent = list(range(len(all_records)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for label, indices in key_to_idx.items():
        # A name shared by many records is almost certainly a common/generic
        # name (or a parsing artifact), not the same person. Above the
        # threshold, do not merge on that name key. Email and LinkedIn slug
        # keys are exact identifiers and always merge.
        if label.startswith("name:") and len(indices) > name_collision_threshold:
            continue
        for j in range(1, len(indices)):
            union(indices[0], indices[j])

    # Group records by root and collapse.
    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(len(all_records)):
        groups[find(i)].append(i)

    merged = []
    for root, members in groups.items():
        merged_rec = {
            "fn": "",
            "emails": [],
            "phones": [],
            "company": "",
            "position": "",
            "address": "",
            "bday": None,
            "note": None,
            "url": "",
            "categories": [],
            "linkedin_url": "",
            "connected_on": "",
            "vault_note": "",
            "linkedin_messages": 0,
            "sources": [],
            "_source_files": [],
        }
        for idx in members:
            r = all_records[idx]
            for s in r["sources"]:
                if s not in merged_rec["sources"]:
                    merged_rec["sources"].append(s)
            for e in r["emails"]:
                if e and e not in merged_rec["emails"]:
                    merged_rec["emails"].append(e)
            for p in r["phones"]:
                if p and p not in merged_rec["phones"]:
                    merged_rec["phones"].append(p)
            for c in r["categories"]:
                if c and c not in merged_rec["categories"]:
                    merged_rec["categories"].append(c)
            for sf in r["_source_files"]:
                if sf and sf not in merged_rec["_source_files"]:
                    merged_rec["_source_files"].append(sf)
            # Prefer the longest fn (LinkedIn names are usually fuller).
            if r["fn"] and len(r["fn"]) > len(merged_rec["fn"]):
                merged_rec["fn"] = r["fn"]
            for field in ("company", "position", "address", "url",
                          "linkedin_url", "connected_on", "vault_note"):
                if r[field] and not merged_rec[field]:
                    merged_rec[field] = r[field]
            if r["bday"] and not merged_rec["bday"]:
                merged_rec["bday"] = r["bday"]
            if r["note"] and not merged_rec["note"]:
                merged_rec["note"] = r["note"]
            merged_rec["linkedin_messages"] = max(
                merged_rec["linkedin_messages"], r["linkedin_messages"])
        merged.append(merged_rec)

    # Sort by relationship signal: most-messaged first, then breadth of sources.
    merged.sort(
        key=lambda r: (
            -r["linkedin_messages"],
            -len(r["sources"]),
            r["fn"].lower(),
        )
    )
    return merged


# ---------- SQLite + JSON output ----------

def write_outputs(merged: list[dict], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path = out_dir / "contacts.db"
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE contacts (
        id INTEGER PRIMARY KEY,
        fn TEXT,
        emails TEXT,
        phones TEXT,
        company TEXT,
        position TEXT,
        address TEXT,
        bday TEXT,
        note TEXT,
        url TEXT,
        categories TEXT,
        linkedin_url TEXT,
        connected_on TEXT,
        vault_note TEXT,
        linkedin_messages INTEGER,
        sources TEXT
    )""")
    cur.execute("CREATE INDEX idx_fn ON contacts(fn)")
    cur.execute("CREATE INDEX idx_company ON contacts(company)")
    cur.execute("CREATE INDEX idx_msg ON contacts(linkedin_messages DESC)")
    for r in merged:
        cur.execute(
            "INSERT INTO contacts (fn, emails, phones, company, position, address, "
            "bday, note, url, categories, linkedin_url, connected_on, vault_note, "
            "linkedin_messages, sources) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                r["fn"],
                json.dumps(r["emails"], ensure_ascii=False),
                json.dumps(r["phones"], ensure_ascii=False),
                r["company"], r["position"], r["address"], r["bday"], r["note"],
                r["url"], json.dumps(r["categories"], ensure_ascii=False),
                r["linkedin_url"], r["connected_on"], r["vault_note"],
                r["linkedin_messages"], json.dumps(r["sources"]),
            ),
        )
    conn.commit()
    conn.close()
    print(f"  contacts.db: {db_path.stat().st_size:,} bytes")

    json_path = out_dir / "contacts.json"
    json_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False))
    print(f"  contacts.json: {json_path.stat().st_size:,} bytes")


# ---------- HTML browser ----------

def write_html_browser(merged: list[dict], out_dir: Path) -> None:
    """Single-file searchable browser with all data inlined. Open in any browser."""
    template = HTML_TEMPLATE
    payload = json.dumps(merged, ensure_ascii=False)
    template = template.replace("__DATA_PLACEHOLDER__", payload)
    template = template.replace(
        "__GENERATED_AT__", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    template = template.replace("__TOTAL__", str(len(merged)))
    out = out_dir / "browser.html"
    out.write_text(template, encoding="utf-8")
    print(f"  browser.html: {out.stat().st_size:,} bytes")


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><title>CRM</title>
<style>
:root{--bg:#0d0e10;--panel:#15171b;--line:#2a2e35;--text:#e6e8eb;--muted:#8a8f99;--accent:#d4a373;--green:#7a9e7e;--cool:#6a9eb5;--pink:#c08497}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,system-ui,sans-serif;font-size:14px;line-height:1.5}
.wrap{max-width:1200px;margin:0 auto;padding:30px 24px}
h1{font-size:32px;font-weight:200;margin:0 0 4px;letter-spacing:-0.02em}
h1 em{font-style:normal;color:var(--accent)}
.sub{color:var(--muted);font-size:13px;margin:0 0 24px}
.toolbar{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px;align-items:center;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}
.toolbar input,.toolbar select{background:var(--bg);color:var(--text);border:1px solid var(--line);border-radius:6px;padding:8px 10px;font-size:14px;font-family:inherit}
.toolbar input{flex:1;min-width:200px}
.toolbar .pill{background:var(--bg);border:1px solid var(--line);border-radius:14px;padding:4px 10px;font-size:12px;color:var(--muted);cursor:pointer;transition:.15s}
.toolbar .pill.active{background:var(--accent);color:var(--bg);border-color:var(--accent)}
.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:16px}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px}
.stat .v{font-size:22px;color:var(--accent);font-weight:300}
.stat .l{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:0.05em}
@media(max-width:720px){.stats{grid-template-columns:repeat(2,1fr)}}
.list{background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.row{display:grid;grid-template-columns:auto 1fr auto auto;gap:14px;padding:12px 16px;border-bottom:1px solid var(--line);align-items:start;cursor:pointer;transition:.1s}
.row:last-child{border-bottom:none}
.row:hover{background:rgba(212,163,115,0.05)}
.row .avatar{width:36px;height:36px;background:var(--bg);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:500;color:var(--accent);border:1px solid var(--line);flex-shrink:0}
.row .body .nm{font-weight:500;font-size:15px}
.row .body .meta{color:var(--muted);font-size:12px;margin-top:2px}
.row .badges{display:flex;gap:4px;flex-wrap:wrap;justify-content:flex-end}
.badge{font-size:10px;padding:2px 7px;border-radius:8px;background:var(--bg);color:var(--muted);border:1px solid var(--line)}
.badge.linkedin{color:var(--cool);border-color:var(--cool)}
.badge.google{color:var(--green);border-color:var(--green)}
.badge.vault{color:var(--accent);border-color:var(--accent)}
.score{color:var(--accent);font-size:13px;font-weight:500;min-width:30px;text-align:right}
.empty{padding:60px;text-align:center;color:var(--muted)}
.detail{position:fixed;top:0;right:-500px;width:500px;height:100vh;background:var(--panel);border-left:1px solid var(--line);transition:right .25s;overflow-y:auto;padding:24px;z-index:10}
.detail.open{right:0}
.detail h2{margin:0 0 8px;font-weight:300;font-size:24px}
.detail .field{margin:14px 0}
.detail .label{font-size:11px;text-transform:uppercase;color:var(--muted);letter-spacing:0.05em;margin-bottom:4px}
.detail .value{font-size:14px;word-break:break-word}
.detail .close{position:absolute;top:14px;right:14px;background:transparent;color:var(--muted);border:1px solid var(--line);border-radius:6px;width:30px;height:30px;cursor:pointer}
.detail a{color:var(--accent);text-decoration:none}
.detail a:hover{text-decoration:underline}
.overlay{position:fixed;inset:0;background:rgba(0,0,0,0.6);opacity:0;pointer-events:none;transition:.25s;z-index:9}
.overlay.open{opacity:1;pointer-events:all}
</style></head><body><div class="wrap">
<h1>Your <em>CRM</em></h1>
<p class="sub">Merged from Google Contacts + LinkedIn + vault People/. Source of truth lives in <code>data/crm-merge/contacts.db</code>. Generated __GENERATED_AT__.</p>
<div class="stats" id="stats"></div>
<div class="toolbar">
  <input id="q" placeholder="Search by name, company, position, email, phone..." />
  <span class="pill" data-filter="all">All</span>
  <span class="pill" data-filter="multi">In 2+ sources</span>
  <span class="pill" data-filter="vault">In vault</span>
  <span class="pill" data-filter="linkedin">LinkedIn</span>
  <span class="pill" data-filter="google">Google</span>
  <span class="pill" data-filter="msgs">Messaged</span>
</div>
<div class="list" id="list"></div>
<div id="empty" class="empty" style="display:none">No matches.</div>
</div>
<div class="overlay" id="overlay"></div>
<aside class="detail" id="detail">
  <button class="close" onclick="closeDetail()">&times;</button>
  <h2 id="d-name"></h2>
  <div id="d-body"></div>
</aside>
<script>
const DATA = __DATA_PLACEHOLDER__;
const TOTAL = __TOTAL__;
let activeFilter = 'all';
let q = '';

function initials(name){
  const parts = (name||'').trim().split(/\\s+/).filter(Boolean);
  if(!parts.length) return '?';
  return (parts[0][0] + (parts.length>1?parts[parts.length-1][0]:'')).toUpperCase();
}
function escapeHTML(s){
  return (s||'').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function passes(r){
  if(activeFilter==='multi' && r.sources.length<2) return false;
  if(activeFilter==='vault' && !r.sources.includes('vault')) return false;
  if(activeFilter==='linkedin' && !r.sources.includes('linkedin')) return false;
  if(activeFilter==='google' && !r.sources.includes('google_contacts')) return false;
  if(activeFilter==='msgs' && (r.linkedin_messages||0)===0) return false;
  if(q){
    const hay = [r.fn, r.company, r.position, ...(r.emails||[]), ...(r.phones||[]), r.linkedin_url, r.note]
      .filter(Boolean).join(' ').toLowerCase();
    if(!hay.includes(q)) return false;
  }
  return true;
}
function render(){
  const list = document.getElementById('list');
  const visible = DATA.filter(passes);
  list.innerHTML = '';
  visible.slice(0, 500).forEach((r, i) => {
    const idx = DATA.indexOf(r);
    const row = document.createElement('div');
    row.className = 'row';
    row.onclick = () => showDetail(idx);
    const sources = r.sources.map(s => {
      const label = s==='google_contacts'?'GC':s==='linkedin'?'LI':s==='vault'?'V':s;
      const cls = s==='google_contacts'?'google':s;
      return `<span class="badge ${cls}">${label}</span>`;
    }).join('');
    const meta = [r.position, r.company].filter(Boolean).join(' · ') || (r.emails[0]||r.phones[0]||'');
    row.innerHTML = `
      <div class="avatar">${initials(r.fn)}</div>
      <div class="body">
        <div class="nm">${escapeHTML(r.fn||'(no name)')}</div>
        <div class="meta">${escapeHTML(meta)}</div>
      </div>
      <div class="score">${r.linkedin_messages||''}</div>
      <div class="badges">${sources}</div>`;
    list.appendChild(row);
  });
  document.getElementById('empty').style.display = visible.length === 0 ? 'block' : 'none';
  if(visible.length > 500) {
    const more = document.createElement('div');
    more.className = 'empty';
    more.style.padding = '14px';
    more.textContent = `... and ${visible.length - 500} more. Refine search to see them.`;
    list.appendChild(more);
  }
  renderStats(visible);
}
function renderStats(visible){
  const stats = document.getElementById('stats');
  const inMulti = DATA.filter(r=>r.sources.length>=2).length;
  const linkedin = DATA.filter(r=>r.sources.includes('linkedin')).length;
  const google = DATA.filter(r=>r.sources.includes('google_contacts')).length;
  const vault = DATA.filter(r=>r.sources.includes('vault')).length;
  stats.innerHTML = `
    <div class="stat"><div class="v">${TOTAL.toLocaleString()}</div><div class="l">Unique people</div></div>
    <div class="stat"><div class="v">${linkedin.toLocaleString()}</div><div class="l">From LinkedIn</div></div>
    <div class="stat"><div class="v">${google.toLocaleString()}</div><div class="l">From Google</div></div>
    <div class="stat"><div class="v">${vault.toLocaleString()}</div><div class="l">In vault</div></div>
    <div class="stat"><div class="v">${inMulti.toLocaleString()}</div><div class="l">In 2+ sources</div></div>`;
}
function showDetail(idx){
  const r = DATA[idx];
  document.getElementById('d-name').textContent = r.fn || '(no name)';
  const body = document.getElementById('d-body');
  const fields = [
    ['Sources', r.sources.join(', ')],
    ['Position', r.position],
    ['Company', r.company],
    ['Emails', (r.emails||[]).join(', ')],
    ['Phones', (r.phones||[]).join(', ')],
    ['LinkedIn', r.linkedin_url ? `<a href="${escapeHTML(r.linkedin_url)}" target="_blank">${escapeHTML(r.linkedin_url)}</a>` : ''],
    ['LinkedIn messages', r.linkedin_messages||''],
    ['Connected on', r.connected_on],
    ['Birthday', r.bday],
    ['Address', r.address],
    ['Vault note', r.vault_note ? `<a href="../../${escapeHTML(r.vault_note)}">${escapeHTML(r.vault_note)}</a>` : ''],
    ['Categories', (r.categories||[]).join(', ')],
    ['URL', r.url ? `<a href="${escapeHTML(r.url)}" target="_blank">${escapeHTML(r.url)}</a>` : ''],
    ['Note', r.note],
  ];
  body.innerHTML = fields.filter(([,v]) => v).map(([k,v]) => `
    <div class="field">
      <div class="label">${k}</div>
      <div class="value">${typeof v === 'string' && (v.startsWith('<a') || v.startsWith('<span')) ? v : escapeHTML(String(v))}</div>
    </div>`).join('');
  document.getElementById('detail').classList.add('open');
  document.getElementById('overlay').classList.add('open');
}
function closeDetail(){
  document.getElementById('detail').classList.remove('open');
  document.getElementById('overlay').classList.remove('open');
}
document.getElementById('overlay').onclick = closeDetail;
document.getElementById('q').oninput = e => { q = e.target.value.toLowerCase(); render(); };
document.querySelectorAll('.pill').forEach(p => {
  p.onclick = () => {
    document.querySelectorAll('.pill').forEach(x => x.classList.remove('active'));
    p.classList.add('active');
    activeFilter = p.dataset.filter;
    render();
  };
});
document.querySelector('.pill[data-filter="all"]').classList.add('active');
render();
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser(description="Merge contact exports into one local CRM.")
    ap.add_argument("--takeout-zip", default="",
                    help="Google Takeout zip (Contacts as vCard). "
                         "Default: newest takeout/google zip in ~/Downloads.")
    ap.add_argument("--linkedin-dir", default=str(DEFAULT_LINKEDIN_DIR),
                    help="Folder with LinkedIn Connections.csv and messages.csv.")
    ap.add_argument("--vault-people", default=str(DEFAULT_VAULT_PEOPLE),
                    help="Folder of per-person markdown notes (optional).")
    ap.add_argument("--me", default="",
                    help="Your name(s) as they appear in LinkedIn messages, "
                         "comma-separated. Used to count message frequency.")
    ap.add_argument("--name-collision-threshold", type=int, default=30,
                    help="Do not merge on a name shared by more than this many "
                         "records (guards against generic-name collisions).")
    ap.add_argument("--out", default=str(DEFAULT_OUT),
                    help="Output directory for contacts.db / .json / browser.html.")
    args = ap.parse_args()

    takeout = args.takeout_zip or find_takeout_zip()
    me_names = tuple(n.strip() for n in args.me.split(",") if n.strip())

    print("Loading sources...")
    google = load_google_contacts(Path(takeout)) if takeout else []
    print(f"  Google Contacts: {len(google)} vCards")

    linkedin = load_linkedin_connections(Path(args.linkedin_dir))
    print(f"  LinkedIn Connections: {len(linkedin)}")

    msg_counts = load_linkedin_message_stats(Path(args.linkedin_dir), me_names)
    print(f"  LinkedIn message correspondents: {len(msg_counts)}")

    vault = load_vault_people(Path(args.vault_people))
    print(f"  Vault People notes: {len(vault)}")

    if not (google or linkedin or vault):
        print("\nNo sources found. Point --takeout-zip / --linkedin-dir / "
              "--vault-people at your exports. See the module README.",
              file=sys.stderr)
        sys.exit(1)

    print("\nMerging by email + LinkedIn slug + normalized name...")
    merged = merge_records(google, linkedin, msg_counts, vault,
                           args.name_collision_threshold)
    print(f"  Total unique people after merge: {len(merged)}")

    in_multi = sum(1 for r in merged if len(r["sources"]) >= 2)
    print(f"  Appearing in 2+ sources: {in_multi}")
    in_vault = sum(1 for r in merged if "vault" in r["sources"])
    print(f"  Linked to vault note: {in_vault}")

    print(f"\nWriting outputs to {args.out}/")
    out_dir = Path(args.out)
    write_outputs(merged, out_dir)
    write_html_browser(merged, out_dir)
    print("Done.")


if __name__ == "__main__":
    main()
