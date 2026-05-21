#!/usr/bin/env python3
"""Compabob LinkedIn outreach module helper.

Two subcommands:

  preflight [--enforce-weekday]
      Decide whether it is OK to draft a new outreach card right now.
      Exit 0 = clear to draft (a one-line status is printed).
      Exit 1 = a gate failed; the reason is printed on stdout.
      Side effect: the first time it runs, it creates the queue file at
      vault/LinkedIn Outreach Queue.md from the shipped seed.

  record <card-file> <sent|rejected|skipped>
      Record the outcome of a drafted card: move its queue line into the
      matching section of the queue file, stamp the card, and archive it.

No external dependencies; standard library only.
"""
from __future__ import annotations

import os
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = MODULE_DIR.parent.parent
QUEUE_FILE = PROJECT_DIR / "vault" / "LinkedIn Outreach Queue.md"
SEED_FILE = MODULE_DIR / "queue.example.md"
CARDS_DIR = PROJECT_DIR / "reports" / "linkedin-outreach" / "cards"
ARCHIVE_DIR = CARDS_DIR / "archive"

DEFAULT_DAILY_CAP = 5
OUTCOME_SECTION = {"sent": "Sent", "rejected": "Rejected", "skipped": "Skipped"}


def fail(reason: str) -> None:
    print(reason)
    sys.exit(1)


def rel(p: Path) -> str:
    try:
        return str(p.relative_to(PROJECT_DIR))
    except ValueError:
        return str(p)


def daily_cap() -> int:
    raw = os.environ.get("LINKEDIN_OUTREACH_DAILY_CAP", "").strip()
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    return DEFAULT_DAILY_CAP


# --- queue file -----------------------------------------------------------


def unchecked_queue_entries() -> list[str]:
    """Return the raw '- [ ] ' lines under the '## Queue' heading."""
    if not QUEUE_FILE.exists():
        return []
    out: list[str] = []
    in_queue = False
    for line in QUEUE_FILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            in_queue = stripped == "## Queue"
            continue
        if in_queue and stripped.startswith("- [ ] "):
            out.append(line)
    return out


def move_queue_line(queue_line: str, dest_section: str, annotation: str) -> bool:
    """Remove queue_line from '## Queue' and append it (annotated) to dest_section.

    Returns True if the line was found and moved. Idempotent-ish: if the line is
    not under '## Queue' anymore, returns False and changes nothing.
    """
    if not QUEUE_FILE.exists() or not queue_line.strip():
        return False
    target = queue_line.strip()
    lines = QUEUE_FILE.read_text(encoding="utf-8").splitlines()

    section = None
    queue_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("## "):
            section = stripped[3:].strip()
        elif section == "Queue" and stripped == target:
            queue_idx = i
    if queue_idx is None:
        return False

    annotated = f"{lines[queue_idx]}  <!-- {annotation} -->"
    del lines[queue_idx]

    dest_idx = next(
        (j for j, ln in enumerate(lines) if ln.strip() == f"## {dest_section}"),
        None,
    )
    if dest_idx is None:
        lines += ["", f"## {dest_section}", "", annotated]
    else:
        insert_at = dest_idx + 1
        while insert_at < len(lines) and lines[insert_at].strip() == "":
            insert_at += 1
        lines.insert(insert_at, annotated)

    QUEUE_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


# --- cards ----------------------------------------------------------------


def open_cards() -> list[Path]:
    """Cards drafted but not yet recorded (directly in cards/, not archive/)."""
    if not CARDS_DIR.exists():
        return []
    return sorted(p for p in CARDS_DIR.glob("*.md"))


def parse_frontmatter(path: Path) -> dict[str, str]:
    """Parse a simple key: value YAML-ish frontmatter block. First colon splits."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    fm: dict[str, str] = {}
    for line in text.splitlines()[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            key, value = line.split(":", 1)
            fm[key.strip()] = value.strip()
    return fm


def count_sent_today() -> int:
    if not ARCHIVE_DIR.exists():
        return 0
    today = date.today().isoformat()
    n = 0
    for p in ARCHIVE_DIR.glob("*.md"):
        fm = parse_frontmatter(p)
        if fm.get("outcome") == "sent" and fm.get("recorded", "").startswith(today):
            n += 1
    return n


def stamp_frontmatter(text: str, outcome: str, today: str) -> str:
    """Set 'outcome:' and add/replace 'recorded:' in the card's frontmatter."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return text

    out: list[str] = []
    saw_outcome = saw_recorded = False
    for i, line in enumerate(lines):
        key = line.split(":", 1)[0].strip() if ":" in line else ""
        if 0 < i < end and key == "outcome":
            out.append(f"outcome: {outcome}")
            saw_outcome = True
        elif 0 < i < end and key == "recorded":
            out.append(f"recorded: {today}")
            saw_recorded = True
        elif i == end:
            if not saw_outcome:
                out.append(f"outcome: {outcome}")
            if not saw_recorded:
                out.append(f"recorded: {today}")
            out.append(line)
        else:
            out.append(line)
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


# --- subcommands ----------------------------------------------------------


def cmd_preflight(enforce_weekday: bool) -> None:
    if not QUEUE_FILE.exists():
        QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if SEED_FILE.exists():
            shutil.copy(SEED_FILE, QUEUE_FILE)
        else:  # defensive: seed missing, write a minimal queue
            QUEUE_FILE.write_text(
                "# LinkedIn Outreach Queue\n\n## Queue\n\n"
                "## Sent\n\n## Rejected\n\n## Skipped\n",
                encoding="utf-8",
            )
        fail(
            f"created your queue at {rel(QUEUE_FILE)}. "
            f"Add people to its '## Queue' section, then run draft.sh again."
        )

    if enforce_weekday and datetime.now().weekday() >= 5:
        fail(
            f"weekend ({datetime.now():%A}); the scheduled run skips weekends. "
            f"Run draft.sh by hand if you want a card anyway."
        )

    opened = open_cards()
    if opened:
        fail(
            f"a card is still open ({opened[0].name}). Act on it and run "
            f"record.sh before drafting another."
        )

    cap = daily_cap()
    sent = count_sent_today()
    if sent >= cap:
        fail(
            f"daily cap reached ({sent}/{cap} sent today). Next card tomorrow, "
            f"or raise LINKEDIN_OUTREACH_DAILY_CAP in .env."
        )

    entries = unchecked_queue_entries()
    if not entries:
        fail(
            f"the queue is empty. Add people to the '## Queue' section of "
            f"{rel(QUEUE_FILE)}."
        )

    print(f"clear: {len(entries)} queued, {sent}/{cap} sent today.")
    sys.exit(0)


def cmd_record(card_arg: str, outcome: str) -> None:
    if outcome not in OUTCOME_SECTION:
        fail(f"unknown outcome '{outcome}'. Use: sent, rejected, or skipped.")

    p = Path(card_arg)
    card = next(
        (c for c in (p, CARDS_DIR / card_arg, CARDS_DIR / p.name) if c.is_file()),
        None,
    )
    if card is None:
        if (ARCHIVE_DIR / p.name).is_file():
            fail(f"{p.name} was already recorded (it is in {rel(ARCHIVE_DIR)}).")
        fail(f"card not found: {card_arg}\nLook in {rel(CARDS_DIR)} for the file name.")

    fm = parse_frontmatter(card)
    queue_line = fm.get("queue_line", "")
    if not queue_line:
        fail(
            f"{card.name} has no 'queue_line' in its frontmatter; "
            f"cannot sync the queue. Move the entry by hand."
        )

    today = date.today().isoformat()
    moved = move_queue_line(queue_line, OUTCOME_SECTION[outcome], f"{outcome} {today}")

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    stamped = stamp_frontmatter(card.read_text(encoding="utf-8"), outcome, today)
    (ARCHIVE_DIR / card.name).write_text(stamped, encoding="utf-8")
    card.unlink()

    queue_note = "" if moved else " (queue line not found; queue left unchanged)"
    print(
        f"recorded {card.name} as {outcome}; moved to {OUTCOME_SECTION[outcome]} "
        f"in the queue{queue_note}. Card archived under {rel(ARCHIVE_DIR)}."
    )
    sys.exit(0)


def main() -> None:
    args = sys.argv[1:]
    if not args:
        fail(
            "usage: _outreach.py preflight [--enforce-weekday]\n"
            "       _outreach.py record <card-file> <sent|rejected|skipped>"
        )
    if args[0] == "preflight":
        cmd_preflight("--enforce-weekday" in args[1:])
    elif args[0] == "record":
        if len(args) != 3:
            fail("usage: _outreach.py record <card-file> <sent|rejected|skipped>")
        cmd_record(args[1], args[2])
    else:
        fail(f"unknown subcommand: {args[0]}")


if __name__ == "__main__":
    main()
