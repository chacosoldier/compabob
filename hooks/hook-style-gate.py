#!/usr/bin/env python3
"""Stop hook: flag em dashes and paragraph walls in the assistant's last reply.

Why a hook and not another line in the style guide: in the setup this kit is
distilled from, the no-em-dash rule was stated three times as "absolute" and
still broken in 44% of long replies. It held only once a hook checked it.

What it checks, in the last assistant text of the session:
  - em dashes used as connectors. Code (fenced and inline), blockquote lines,
    and a dash that opens a line (Spanish dialogue) do not count.
  - paragraph walls: a reply of 1000+ prose characters with one paragraph over
    700. Bullets, tables, headers, and code do not count toward a wall.

Mode, from `style_gate:` in config/user.config.yaml (default warn):
  off    do nothing
  warn   show a one-line note to the user; the reply stands
  block  ask the assistant to rewrite only the flagged sentences (once per
         reply: Claude Code sets stop_hook_active on the retry)

Fails open: any error, missing file, or odd payload exits 0 with no output.

For tests:  python3 hooks/hook-style-gate.py --text FILE [--mode warn|block]
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

EMDASH = "\u2014"  # escaped on purpose, so this file never contains the character it hunts
FENCE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE = re.compile(r"`[^`\n]*`")
BLOCKQUOTE = re.compile(r"^\s*>")
STRUCTURAL_LINE = re.compile(r"^\s*(?:[-*+]\s|\d+[.)]\s|>|#{1,6}\s|\|)")
WALL_MIN_PROSE, WALL_MAX_PARAGRAPH = 1000, 700
MODES = ("off", "warn", "block")


def is_machine_payload(text: str) -> bool:
    """A reply that is a JSON payload, not prose."""
    return text.lstrip().startswith(("{", "[", "```json"))


def emdash_hits(text: str, width: int = 20) -> list[tuple[int, str]]:
    """(line number, short quote) for each connector em dash in the prose."""
    # Blank out fenced code but keep its newlines, so line numbers stay true.
    text = FENCE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    hits = []
    for n, line in enumerate(text.splitlines(), 1):
        if EMDASH not in line or BLOCKQUOTE.match(line):
            continue
        prose = INLINE_CODE.sub(lambda m: " " * len(m.group(0)), line)
        for m in re.finditer(EMDASH, prose):
            if not prose[: m.start()].strip():
                continue  # line-initial dash: dialogue, not a connector
            start, end = max(0, m.start() - width), min(len(line), m.end() + width)
            quote = ("..." if start else "") + line[start:end].strip() + ("..." if end < len(line) else "")
            hits.append((n, quote))
    return hits


def longest_wall(text: str) -> tuple[int, int]:
    """(longest prose paragraph, total prose chars), code and structure excluded."""
    stripped = FENCE.sub("", text)
    longest = total = 0
    for block in re.split(r"\n\s*\n", stripped):
        lines = [ln for ln in block.splitlines() if ln.strip() and not STRUCTURAL_LINE.match(ln)]
        size = len("\n".join(lines).strip())
        longest, total = max(longest, size), total + size
    return longest, total


def findings(text: str) -> list[tuple[str, str]]:
    """(what was found, how to fix it) for each problem in the reply."""
    if not text.strip() or is_machine_payload(text):
        return []
    out = []
    hits = emdash_hits(text)
    if hits:
        quoted = "; ".join(f'line {n} "{q}"' for n, q in hits[:3])
        more = f" (+{len(hits) - 3} more)" if len(hits) > 3 else ""
        out.append((f"{len(hits)} em dash(es) used as connectors: {quoted}{more}",
                    "replace each with a comma, a period, a colon, or parentheses"))
    wall, total = longest_wall(text)
    if total >= WALL_MIN_PROSE and wall > WALL_MAX_PARAGRAPH:
        out.append((f"a {wall}-character paragraph in a {total}-character reply",
                    "split it into shorter paragraphs, or into bullets if it lists parallel items"))
    return out


def last_assistant_text(path: str) -> str:
    last = ""
    with open(path, errors="ignore") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if not isinstance(rec, dict) or rec.get("type") != "assistant":
                continue
            content = (rec.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            text = "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
            if text.strip():
                last = text
    return last


def read_mode(project_dir: str) -> str:
    try:
        cfg = Path(project_dir, "config", "user.config.yaml").read_text(encoding="utf-8")
    except OSError:
        return "warn"
    m = re.search(r"^style_gate:\s*[\"']?(\w+)", cfg, re.MULTILINE)
    return m.group(1) if m and m.group(1) in MODES else "warn"


def verdict(text: str, mode: str) -> dict | None:
    if mode == "off":
        return None
    found = findings(text)
    if not found:
        return None
    if mode == "block":
        return {
            "decision": "block",
            "reason": "Style check on your reply. "
            + " ".join(f"Found {what}: {fix}." for what, fix in found)
            + " Change nothing else.",
        }
    note = "; ".join(what for what, _ in found)
    return {"systemMessage": f"Style note: {note}. (style_gate: warn in config/user.config.yaml)"}


def main() -> int:
    args = sys.argv[1:]
    if args[:1] == ["--text"] and len(args) >= 2:
        mode = args[3] if args[2:3] == ["--mode"] and len(args) >= 4 else "warn"
        out = verdict(Path(args[1]).read_text(encoding="utf-8"), mode)
        if out:
            print(json.dumps(out))
        return 0

    payload = json.loads(sys.stdin.read() or "{}")
    if not isinstance(payload, dict) or payload.get("stop_hook_active"):
        return 0
    transcript = payload.get("transcript_path") or ""
    if not transcript or not os.path.isfile(transcript):
        return 0
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or "."
    out = verdict(last_assistant_text(transcript), read_mode(project_dir))
    if out:
        print(json.dumps(out))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a style check must never break a session
        sys.exit(0)
