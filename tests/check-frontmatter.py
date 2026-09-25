#!/usr/bin/env python3
"""Every agent and skill has the frontmatter Claude Code needs to load it.

- .claude/agents/*.md: name + description, except error-handling.md (a shared
  reference) and _-prefixed files, which must have NO frontmatter (with it,
  Claude Code would register them as agents).
- .claude/skills/*/SKILL.md: name (matching the folder) + description, and the
  description fits Claude Code's 1,536-character listing cap.
- any frontmatter value that contains ": " is quoted; unquoted, it is invalid
  YAML (a stdlib check, so CI needs no PyYAML).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FM = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
errors = []


def fields(path: Path) -> dict | None:
    m = FM.match(path.read_text(encoding="utf-8"))
    if not m:
        return None
    out = {}
    for line in m.group(1).splitlines():
        k, sep, v = line.partition(":")
        if sep and not line.startswith((" ", "\t")):
            v = v.strip()
            if ": " in v and not v.startswith(('"', "'")):
                errors.append(f"{path.relative_to(ROOT)}: {k.strip()} contains ': ' but is not quoted (invalid YAML)")
            out[k.strip()] = v.strip('"')
    return out


for f in sorted((ROOT / ".claude/agents").glob("*.md")):
    fm = fields(f)
    if f.name.startswith("_"):
        if fm is not None:
            errors.append(f"{f.relative_to(ROOT)}: _-prefixed file has frontmatter, so it would load as an agent")
        continue
    if f.name == "error-handling.md":
        continue
    if fm is None or not fm.get("name") or not fm.get("description"):
        errors.append(f"{f.relative_to(ROOT)}: missing name or description")

for f in sorted((ROOT / ".claude/skills").glob("*/SKILL.md")):
    fm = fields(f)
    rel = f.relative_to(ROOT)
    if fm is None or not fm.get("name") or not fm.get("description"):
        errors.append(f"{rel}: missing name or description")
        continue
    if fm["name"] != f.parent.name:
        errors.append(f"{rel}: name {fm['name']!r} does not match folder {f.parent.name!r}")
    if len(fm["description"]) > 1536:
        errors.append(f"{rel}: description is {len(fm['description'])} chars (cap 1536)")

for e in errors:
    print(f"  FAIL  {e}")
print("frontmatter: all passed" if not errors else f"frontmatter: {len(errors)} failed")
sys.exit(1 if errors else 0)
