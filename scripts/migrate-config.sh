#!/usr/bin/env bash
# Compabob: bring config/user.config.yaml up to date with the kit's template.
#
# Adds keys a kit update introduced (for example a new module flag) with their
# default value and comment. It never changes or removes a line you already
# have, and it writes config/user.config.yaml.bak before touching the file.
#
#   usage: bash scripts/migrate-config.sh          add missing keys
#          bash scripts/migrate-config.sh --check  list missing keys, change nothing
#                                                  (exit 1 when something is missing)
set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR" || exit 1

TEMPLATE="config/user.config.yaml.template"
CONFIG="config/user.config.yaml"
[ -f "$TEMPLATE" ] || { echo "missing $TEMPLATE" >&2; exit 1; }
[ -f "$CONFIG" ] || exit 0   # setup has not run yet: nothing to migrate

python3 - "$TEMPLATE" "$CONFIG" "${1:-}" <<'PY'
import pathlib, re, shutil, sys

template_path, config_path, mode = sys.argv[1], sys.argv[2], sys.argv[3]
TOP = re.compile(r"^([A-Za-z_][\w-]*):")
CHILD = re.compile(r"^\s+([A-Za-z_][\w-]*):")


def blocks(lines):
    """Map each top-level key to (start, end): its line and its indented children."""
    out, i = {}, 0
    while i < len(lines):
        m = TOP.match(lines[i])
        if not m:
            i += 1
            continue
        start, j, end = i, i + 1, i
        while j < len(lines) and (lines[j].startswith((" ", "\t")) or not lines[j].strip()):
            if lines[j].strip():
                end = j
            j += 1
        out[m.group(1)] = (start, end)
        i = j
    return out


tpl = pathlib.Path(template_path).read_text(encoding="utf-8").splitlines()
cfg = pathlib.Path(config_path).read_text(encoding="utf-8").splitlines()
tpl_blocks, cfg_blocks = blocks(tpl), blocks(cfg)

inserts = []   # (after_line_index, [lines], label)
appends = []   # ([lines], label)
for key, (ts, te) in tpl_blocks.items():
    if key not in cfg_blocks:
        # Carry the comment lines directly above the key, so the new setting
        # arrives with its explanation.
        head = ts
        while head > 0 and tpl[head - 1].startswith("#"):
            head -= 1
        appends.append((tpl[head:te + 1], key))
        continue
    cs, ce = cfg_blocks[key]
    have = {CHILD.match(l).group(1) for l in cfg[cs + 1:ce + 1] if CHILD.match(l)}
    missing = [l for l in tpl[ts + 1:te + 1] if CHILD.match(l) and CHILD.match(l).group(1) not in have]
    if missing:
        inserts.append((ce, missing, key))

labels = [f"{k}.{CHILD.match(l).group(1)}" for _, ls, k in inserts for l in ls] + [k for _, k in appends]
if not labels:
    sys.exit(0)

if mode == "--check":
    print("config/user.config.yaml is missing: " + ", ".join(labels))
    sys.exit(1)

shutil.copyfile(config_path, config_path + ".bak")
for after, lines, _ in sorted(inserts, key=lambda t: t[0], reverse=True):
    cfg[after + 1:after + 1] = lines
for lines, _ in appends:
    if cfg and cfg[-1].strip():
        cfg.append("")
    cfg.extend(lines)
pathlib.Path(config_path).write_text("\n".join(cfg) + "\n", encoding="utf-8")
print("  added to config/user.config.yaml: " + ", ".join(labels) + " (backup: user.config.yaml.bak)")
PY
