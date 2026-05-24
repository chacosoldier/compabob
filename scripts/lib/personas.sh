#!/usr/bin/env bash
# Compabob — persona preset helper. Sourced by setup.sh; not run directly.
#
# apply_persona <persona-id> <free-text "what you work on">
#   - seeds memory/topics/role-and-priorities.md from config/personas/<id>.md,
#     but only if that file is still the untouched template (never clobbers edits)
#   - records the chosen preset in config/user.config.yaml
#
# Must be called with the current directory at the kit root (setup.sh ensures it).

apply_persona() {
  local pid="$1" what="${2:-}"
  local persona_file="config/personas/$pid.md"

  if [ ! -f "$persona_file" ]; then
    printf '  \033[1;33mwarn\033[0m persona "%s" not found — skipping persona setup\n' "$pid"
    return 0
  fi

  PERSONA_ID="$pid" PERSONA_WHAT="$what" python3 - "$persona_file" <<'PYEOF'
import os, pathlib, sys

persona_file = pathlib.Path(sys.argv[1])
pid = os.environ["PERSONA_ID"]
what = os.environ["PERSONA_WHAT"].strip() or "[in a sentence or two, what you work on]"

text = persona_file.read_text(encoding="utf-8")

# strip YAML frontmatter, keep the body
body = text
if text.startswith("---"):
    parts = text.split("---", 2)
    if len(parts) == 3:
        body = parts[2].lstrip("\n")
body = body.replace("<WHAT_YOU_WORK_ON>", what)

# Seed role-and-priorities.md only if it still looks like the untouched template.
# The marker MUST be unique to memory.example/topics/role-and-priorities.md AND
# absent from every config/personas/*.md replacement, otherwise a re-run with a
# different persona will silently overwrite the user's edits.
# `Core responsibilities: [fill in].` qualifies: grep confirms it appears in the
# original template only. Do not loosen this without re-grepping all personas.
rp = pathlib.Path("memory/topics/role-and-priorities.md")
UNTOUCHED_MARKER = "Core responsibilities: [fill in]."
seeded = False
if rp.exists():
    current = rp.read_text(encoding="utf-8")
    if UNTOUCHED_MARKER in current:
        rp.write_text(body, encoding="utf-8")
        print(f"  \033[0;32mok\033[0m   seeded role-and-priorities.md from the {pid} persona")
        seeded = True
    else:
        print("  \033[0;32mok\033[0m   role-and-priorities.md already personalized — kept your version")
else:
    print("  \033[1;33mwarn\033[0m memory/topics/role-and-priorities.md not found — skipped")

# record the chosen preset in the config, but only when the file was actually
# seeded — so config.preset never disagrees with what is in role-and-priorities.md
if seeded:
    cfg = pathlib.Path("config/user.config.yaml")
    if cfg.exists():
        lines = cfg.read_text(encoding="utf-8").splitlines()
        out, done = [], False
        for ln in lines:
            if not done and ln.lstrip().startswith("preset:"):
                indent = ln[: len(ln) - len(ln.lstrip())]
                out.append(f'{indent}preset: "{pid}"')
                done = True
            else:
                out.append(ln)
        if done:
            cfg.write_text("\n".join(out) + "\n", encoding="utf-8")
            print(f'  \033[0;32mok\033[0m   recorded persona "{pid}" in config/user.config.yaml')
PYEOF
}
