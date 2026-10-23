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

# cfg_get <section> <key> [config-file]
# Prints the value of   section:  /  key: "value"   from the user config, for
# example  cfg_get user name  prints  Maya. Plain awk, so it works without python3.
cfg_get() {
  local cfg="${3:-config/user.config.yaml}"
  [ -f "$cfg" ] || return 1
  awk -v sec="$1:" -v key="$2:" '
    /^[A-Za-z_]/ { cur = $1 }
    cur == sec && $1 == key {
      v = $0
      sub(/^[^:]*:[ \t]*/, "", v)
      sub(/"[ \t]*#[^"]*$/, "\"", v)
      gsub(/^"|"$/, "", v)
      print v
      exit
    }' "$cfg"
}

# Setup placeholders: the {{...}} tokens the seed files ship with, plus the stand-in
# setup writes when no name was given. A file that still holds one is unfinished.
# shellcheck disable=SC2034  # used by setup.sh and hooks/hook-session-start.sh
SETUP_TOKENS='\{\{(ASSISTANT_NAME|USER_NAME|USER_ROLE|PRIMARY_LANGUAGE)\}\}|_YOUR_NAME_HERE_'
