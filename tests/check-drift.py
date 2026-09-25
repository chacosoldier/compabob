#!/usr/bin/env python3
"""The docs list what the tree ships, and nothing it does not.

- every skill folder appears as `/name` in the README skills table
- every module folder appears in modules/README.md and the README modules table
- the persona list in setup.sh and the config template matches config/personas/
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
readme = (ROOT / "README.md").read_text(encoding="utf-8")
modules_readme = (ROOT / "modules/README.md").read_text(encoding="utf-8")
errors = []

skills = sorted(p.parent.name for p in (ROOT / ".claude/skills").glob("*/SKILL.md"))
for s in skills:
    if f"| `/{s}` |" not in readme:
        errors.append(f"skill /{s} is missing from the README skills table")
for s in re.findall(r"^\| `/([\w-]+)` \|", readme, re.MULTILINE):
    if s not in skills:
        errors.append(f"README lists /{s}, but .claude/skills/{s}/ does not exist")

modules = sorted(p.name for p in (ROOT / "modules").iterdir() if p.is_dir() and (p / "README.md").exists())
for m in modules:
    if f"[`{m}/`]" not in modules_readme:
        errors.append(f"module {m} is missing from the modules/README.md table")
    if f"| `{m}` |" not in readme:
        errors.append(f"module {m} is missing from the README modules table")
for m in re.findall(r"^\| `([\w-]+)` \| (?:Available|Roadmap|Deferred)", readme, re.MULTILINE):
    if m not in modules:
        errors.append(f"README lists module {m}, but modules/{m}/ does not exist")

personas = sorted(p.stem for p in (ROOT / "config/personas").glob("*.md") if p.stem != "README")
setup = (ROOT / "setup.sh").read_text(encoding="utf-8")
template = (ROOT / "config/user.config.yaml.template").read_text(encoding="utf-8")
preset_line = next((ln for ln in template.splitlines() if ln.strip().startswith("preset:")), "")
for p in personas:
    if f"{p})" not in setup and f"|{p})" not in setup:
        errors.append(f"persona {p} is not offered in setup.sh")
    if p not in preset_line:
        errors.append(f"persona {p} is not in the preset comment of config/user.config.yaml.template")

for e in errors:
    print(f"  FAIL  {e}")
print("drift: all passed" if not errors else f"drift: {len(errors)} failed")
sys.exit(1 if errors else 0)
