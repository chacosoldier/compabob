#!/usr/bin/env python3
"""modules/dictation/learn.py: promote recurring dictation corrections.

What it does, once a day (a launchd/cron job) or on demand:
  1. Read data/dictation/calls.jsonl. For each successful row, token-diff
     raw -> cleaned and extract 1->1 word substitutions (e.g. sequel -> SQL).
  2. Count occurrences + consistency per (wrong -> right).
  3. Auto-promote a substitution when occurrences >= LEARN_MIN_OCCURRENCES and
     consistency >= LEARN_MIN_CONSISTENCY and its `right` isn't already a
     corrections target -> append to glossary.yaml.corrections (source: learned),
     bump `version`. (Only ever appends source:learned; never rewrites seed
     entries or terms.)
  4. Append a data/dictation/promotions.log line for each promotion.
  5. Prune calls.jsonl rows older than LEARN_RETENTION_DAYS (privacy + bound).

Honest limitation: this learns from the MODEL's own corrections, not from your
post-edits in the target app. It won't catch errors the model never fixed. The
manual escape hatch is hand-editing glossary.yaml anytime.

CLI:
  --report           print the candidate table; no writes, no prune
  --dry-run          show what would be promoted; no writes, no prune
  --calls PATH       override calls.jsonl (test fixtures)
  --glossary PATH    override glossary.yaml (test fixtures)

DICTATION_AUTO_PROMOTE=0 -> propose-only (log, never write to glossary).
Needs pyyaml (`pip3 install pyyaml`). Run with system python3.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import yaml

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent.parent  # modules/dictation -> compabob root

_ENV_FILE = _HERE / ".env"
_ENV_EXAMPLE = _HERE / ".env.example"
_DEFAULT_CALLS = _PROJECT_ROOT / "data" / "dictation" / "calls.jsonl"
_DEFAULT_GLOSSARY = _HERE / "glossary.yaml"
_PROMOTIONS_LOG = _PROJECT_ROOT / "data" / "dictation" / "promotions.log"

_DEFAULTS = {
    "DICTATION_AUTO_PROMOTE": "1",
    "LEARN_MIN_OCCURRENCES": "4",
    "LEARN_MIN_CONSISTENCY": "0.9",
    "LEARN_RETENTION_DAYS": "30",
}

_TS_FMT = "%Y-%m-%dT%H:%M:%S"
_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


# --- Config -----------------------------------------------------------
def load_config() -> dict:
    cfg = dict(_DEFAULTS)
    for f in (_ENV_EXAMPLE, _ENV_FILE):
        try:
            text = f.read_text()
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip().strip('"').strip("'")
    for k in list(cfg):
        if k in os.environ:
            cfg[k] = os.environ[k]
    return cfg


# --- Substitution extraction ------------------------------------------
def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text or "")


def extract_substitutions(raw: str, cleaned: str) -> list[tuple[str, str]]:
    """1->1 word substitutions raw -> cleaned (wrong lowercased, right as-cleaned).

    Skips case-only changes (handled by the prompt, not the glossary) and
    pure-digit tokens. Filler deletions are `delete` opcodes -> ignored.
    """
    rt, ct = _tokens(raw), _tokens(cleaned)
    sm = difflib.SequenceMatcher(a=[t.lower() for t in rt], b=[t.lower() for t in ct])
    subs: list[tuple[str, str]] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "replace" or (i2 - i1) != 1 or (j2 - j1) != 1:
            continue
        wrong = rt[i1].lower()
        right = ct[j1]
        if wrong == right.lower():  # case-only change, not a real correction
            continue
        if wrong.isdigit() or right.isdigit():
            continue
        subs.append((wrong, right))
    return subs


def load_rows(calls_path: Path) -> list[dict]:
    rows: list[dict] = []
    if not calls_path.exists():
        return rows
    for line in calls_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def tally(rows: list[dict]) -> dict[str, Counter]:
    """wrong (lowercased) -> Counter of right-values across successful rows."""
    tallies: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        if not r.get("success"):
            continue
        raw, cleaned = r.get("raw", ""), r.get("cleaned", "")
        if not raw or not cleaned or raw == cleaned:
            continue
        for wrong, right in extract_substitutions(raw, cleaned):
            tallies[wrong][right] += 1
    return tallies


# --- Candidate selection ----------------------------------------------
def find_candidates(tallies: dict[str, Counter], min_occ: int, min_cons: float) -> list[dict]:
    """Qualifying (wrong -> right) substitutions sorted by support."""
    out: list[dict] = []
    for wrong, counter in tallies.items():
        total = sum(counter.values())
        right, occ = counter.most_common(1)[0]
        consistency = occ / total if total else 0.0
        out.append(
            {
                "wrong": wrong,
                "right": right,
                "occurrences": occ,
                "total": total,
                "consistency": consistency,
                "qualifies": occ >= min_occ and consistency >= min_cons,
            }
        )
    out.sort(key=lambda c: (c["qualifies"], c["occurrences"]), reverse=True)
    return out


# --- Glossary I/O -----------------------------------------------------
def load_glossary(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except (OSError, yaml.YAMLError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("version", 0)
    data.setdefault("terms", [])
    data.setdefault("corrections", [])
    if not isinstance(data["corrections"], list):
        data["corrections"] = []
    return data


def write_glossary(path: Path, data: dict) -> None:
    ordered = {
        "version": data.get("version", 0),
        "terms": data.get("terms", []),
        "corrections": data.get("corrections", []),
    }
    header = (
        "# dictation glossary: see modules/dictation/README.md 'Glossary format'.\n"
        "# GITIGNORED: your own names/jargon. learn.py appends to `corrections`;\n"
        "# you seed `terms` by hand. Hand-editable anytime.\n"
    )
    body = yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True, default_flow_style=False)
    path.write_text(header + body)


def _existing_right_targets(glossary: dict) -> set[str]:
    out = set()
    for c in glossary.get("corrections") or []:
        if isinstance(c, dict) and c.get("right"):
            out.add(str(c["right"]).lower())
    return out


def _existing_wrongs(glossary: dict) -> set[str]:
    out = set()
    for c in glossary.get("corrections") or []:
        if not isinstance(c, dict):
            continue
        wrong = c.get("wrong") or []
        if isinstance(wrong, str):
            wrong = [wrong]
        out.update(str(w).lower() for w in wrong)
    return out


def build_promotions(candidates: list[dict], glossary: dict) -> list[dict]:
    """Group qualifying candidates by `right`, skipping ones already covered."""
    have_right = _existing_right_targets(glossary)
    have_wrong = _existing_wrongs(glossary)
    grouped: dict[str, dict] = {}
    for c in candidates:
        if not c["qualifies"]:
            continue
        right = c["right"]
        if right.lower() in have_right:
            continue
        if c["wrong"] in have_wrong:
            continue
        g = grouped.setdefault(right, {"wrong": [], "right": right, "occurrences": 0})
        if c["wrong"] not in g["wrong"]:
            g["wrong"].append(c["wrong"])
            g["occurrences"] += c["occurrences"]
    return list(grouped.values())


# --- Pruning ----------------------------------------------------------
def prune_calls(calls_path: Path, retention_days: int) -> int:
    """Drop rows older than retention_days. Returns count pruned."""
    rows = load_rows(calls_path)
    if not rows:
        return 0
    cutoff = datetime.now() - timedelta(days=retention_days)
    kept: list[dict] = []
    pruned = 0
    for r in rows:
        ts = r.get("ts", "")
        try:
            when = datetime.strptime(ts, _TS_FMT)
        except (ValueError, TypeError):
            kept.append(r)  # unparseable ts -> keep (don't silently drop)
            continue
        if when >= cutoff:
            kept.append(r)
        else:
            pruned += 1
    if pruned:
        calls_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept))
    return pruned


def log_promotions(promotions: list[dict], path: Path = _PROMOTIONS_LOG) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime(_TS_FMT)
        with path.open("a") as f:
            for p in promotions:
                f.write(
                    json.dumps(
                        {"ts": stamp, "wrong": p["wrong"], "right": p["right"], "occurrences": p["occurrences"]},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
    except Exception as exc:  # noqa: BLE001
        print(f"[dictation-learn] promotions.log write failed: {exc}", file=sys.stderr)


# --- Report -----------------------------------------------------------
def print_report(candidates: list[dict]) -> None:
    print(f"{'wrong':<22}{'right':<22}{'occ':<6}{'total':<7}{'cons':<7}{'promote?'}")
    print("-" * 70)
    for c in candidates:
        print(
            f"{c['wrong'][:20]:<22}{c['right'][:20]:<22}{c['occurrences']:<6}"
            f"{c['total']:<7}{c['consistency']:<7.2f}{'YES' if c['qualifies'] else ''}"
        )
    if not candidates:
        print("(no substitutions found in calls.jsonl)")


# --- Main -------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Promote recurring dictation corrections.")
    ap.add_argument("--report", action="store_true", help="print candidate table; no writes")
    ap.add_argument("--dry-run", action="store_true", help="show would-be promotions; no writes")
    ap.add_argument("--calls", type=Path, default=_DEFAULT_CALLS, help="override calls.jsonl")
    ap.add_argument("--glossary", type=Path, default=_DEFAULT_GLOSSARY, help="override glossary.yaml")
    args = ap.parse_args(argv)

    cfg = load_config()
    min_occ = int(cfg["LEARN_MIN_OCCURRENCES"])
    min_cons = float(cfg["LEARN_MIN_CONSISTENCY"])
    retention = int(cfg["LEARN_RETENTION_DAYS"])
    auto_promote = cfg["DICTATION_AUTO_PROMOTE"] != "0"

    promotions_log = args.calls.parent / "promotions.log"
    rows = load_rows(args.calls)
    tallies = tally(rows)
    glossary = load_glossary(args.glossary)
    candidates = find_candidates(tallies, min_occ, min_cons)

    if args.report:
        print_report(candidates)
        return 0

    promotions = build_promotions(candidates, glossary)

    if not promotions:
        print(f"No new corrections to promote ({len(candidates)} candidates, none qualifying/new).")
        if not args.dry_run:
            pruned = prune_calls(args.calls, retention)
            if pruned:
                print(f"Pruned {pruned} calls.jsonl row(s) older than {retention}d.")
        return 0

    if args.dry_run:
        print(f"[dry-run] would {'promote' if auto_promote else 'propose'} {len(promotions)} correction(s):")
        for p in promotions:
            print(f"  {', '.join(p['wrong'])} -> {p['right']} (×{p['occurrences']})")
        return 0

    if auto_promote:
        for p in promotions:
            glossary["corrections"].append(
                {
                    "wrong": p["wrong"],
                    "right": p["right"],
                    "source": "learned",
                    "occurrences": p["occurrences"],
                    "added": datetime.now().strftime(_TS_FMT),
                }
            )
        glossary["version"] = int(glossary.get("version", 0) or 0) + 1
        write_glossary(args.glossary, glossary)
        log_promotions(promotions, promotions_log)
        print(f"Promoted {len(promotions)} correction(s); glossary version -> {glossary['version']}.")
    else:
        log_promotions(promotions, promotions_log)
        print(f"Proposed {len(promotions)} correction(s) (auto-promote off; glossary not written).")

    pruned = prune_calls(args.calls, retention)
    if pruned:
        print(f"Pruned {pruned} calls.jsonl row(s) older than {retention}d.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
