#!/usr/bin/env bash
# Compabob: shared helpers for the kit's shell scripts. Sourced, not run.
#   source "$PROJECT_DIR/scripts/lib/common.sh"

bold() { printf '\033[1m%s\033[0m\n' "$1"; }
ok()   { printf '  \033[0;32mok\033[0m   %s\n' "$1"; }
warn() { printf '  \033[1;33mwarn\033[0m %s\n' "$1"; }
say()  { printf '  %s\n' "$1"; }

# set_config_flag <key> <true|false> [config-file]
# Sets the first `key: true|false` line in the user config, keeping its
# indentation and trailing comment. Returns 0 when it changed the value,
# 2 when the value was already set, 1 when the file or key is missing.
set_config_flag() {
  local key="$1" val="$2" cfg="${3:-config/user.config.yaml}"
  [ -f "$cfg" ] || return 1
  python3 - "$cfg" "$key" "$val" <<'PY'
import pathlib, re, sys
path, key, val = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
lines = path.read_text(encoding="utf-8").splitlines()
pat = re.compile(r"^(\s*" + re.escape(key) + r":\s*)(true|false)\b(.*)$")
for i, line in enumerate(lines):
    m = pat.match(line)
    if m:
        if m.group(2) == val:
            sys.exit(2)
        lines[i] = m.group(1) + val + m.group(3)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        sys.exit(0)
sys.exit(1)
PY
}
