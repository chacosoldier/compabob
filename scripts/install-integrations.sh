#!/usr/bin/env bash
# Compabob — integration installer.
#
# Adds MCP servers to .mcp.json from scripts/integrations-catalog.json.
# Keyless integrations (web, utility) are configured fully. Keyed ones (search,
# google) are configured as far as possible and the remaining key/OAuth step is
# printed for you to finish. Nothing is downloaded here: MCP servers fetch
# themselves the first time Claude Code uses them.
#
# Safe to re-run: it never removes or overwrites a server you already have.
#
#   usage: install-integrations.sh [category ...]   e.g. install-integrations.sh web utility
#          install-integrations.sh                  (no args: interactive picker)
#          install-integrations.sh --help
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"
CATALOG="scripts/integrations-catalog.json"
MCP_FILE=".mcp.json"
MCP_SEED=".mcp.json.example"
CONFIG="config/user.config.yaml"

bold() { printf '\033[1m%s\033[0m\n' "$1"; }
ok()   { printf '  \033[0;32mok\033[0m   %s\n' "$1"; }
warn() { printf '  \033[1;33mwarn\033[0m %s\n' "$1"; }

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  bold "Compabob — integration installer"
  echo "Adds MCP servers to .mcp.json. Categories: web, utility, search, google."
  echo "  install-integrations.sh web utility   configure those categories"
  echo "  install-integrations.sh               interactive picker"
  exit 0
fi

[ -f "$CATALOG" ] || { echo "missing $CATALOG — run this from inside the kit" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "python3 is required" >&2; exit 1; }

bold ""
bold "Compabob — integrations"
echo

# --- choose categories -----------------------------------------------------
CHOSEN=()
if [ "$#" -gt 0 ]; then
  CHOSEN=("$@")
else
  echo "Pick the integrations to set up (y/N each):"
  ask_cat() {  # ask_cat <id> <description>
    local ans=""
    printf '  %-8s %s? [y/N]: ' "$1" "$2"
    read -r ans || true
    case "$ans" in [Yy]*) CHOSEN+=("$1");; esac
  }
  ask_cat web     "Playwright + scrapling-fetch (no key)"
  ask_cat utility "time + fetch (no key)"
  ask_cat search  "exa web search (needs an API key)"
  ask_cat google  "Gmail + Calendar (needs OAuth)"
  echo
fi

if [ "${#CHOSEN[@]}" -eq 0 ]; then
  warn "nothing chosen — no changes made"
  exit 0
fi

# --- ensure .mcp.json exists (only now that we know we'll touch it) -------
if [ ! -f "$MCP_FILE" ]; then
  if [ -f "$MCP_SEED" ]; then cp "$MCP_SEED" "$MCP_FILE"; else printf '{\n  "mcpServers": {}\n}\n' > "$MCP_FILE"; fi
  ok "created $MCP_FILE"
fi

# --- preflight: runtimes (warn only, never block) -------------------------
command -v npx >/dev/null 2>&1 && ok "npx found" \
  || warn "npx not found — install Node.js; npx-based servers stay registered but will not run until you do"
command -v uvx >/dev/null 2>&1 && ok "uvx found" \
  || warn "uvx not found — install uv (https://docs.astral.sh/uv/); uvx-based servers stay registered but will not run until you do"
echo

# --- merge .mcp.json + report (Python does the JSON work) -----------------
python3 - "$CATALOG" "$MCP_FILE" "$CONFIG" "${CHOSEN[@]}" <<'PYEOF'
import json, sys

catalog_path, mcp_path, config_path, *chosen = sys.argv[1:]
GREEN, YELLOW, BOLD, NC = "\033[0;32m", "\033[1;33m", "\033[1m", "\033[0m"

catalog = json.load(open(catalog_path))
cats = {c["id"]: c for c in catalog["categories"]}

mcp = json.load(open(mcp_path))
mcp.setdefault("mcpServers", {})

added, skipped, guided, unknown = [], [], [], []
for cid in chosen:
    cat = cats.get(cid)
    if not cat:
        unknown.append(cid)
        continue
    for name, spec in cat.get("servers", {}).items():
        if name in mcp["mcpServers"]:
            skipped.append(name)
        else:
            mcp["mcpServers"][name] = spec
            added.append(name)
    if cat.get("requires_keys"):
        guided.append(cat)

# idempotent write: deterministic output, so a re-run with the same choices
# produces a byte-identical file.
with open(mcp_path, "w") as f:
    json.dump(mcp, f, indent=2)
    f.write("\n")

for name in added:   print(f"  {GREEN}ok{NC}   added MCP server: {name}")
for name in skipped: print(f"  {GREEN}ok{NC}   already present, kept: {name}")
for cid in unknown:  print(f"  {YELLOW}warn{NC} unknown category (ignored): {cid}")

# If nothing was added, skipped, OR queued for guided setup (e.g. every
# requested category was unknown), nothing actually happened. Fail loud so the
# user notices instead of seeing a misleading "Done.". Note: `google` only
# guides, so a google-only selection still counts as a real action.
if not added and not skipped and not guided:
    print()
    print(f"  {YELLOW}warn{NC} nothing was installed — valid categories are: web | utility | search | google")
    sys.exit(1)

if guided:
    print()
    print(f"{BOLD}One more step for the keyed integrations:{NC}")
    for cat in guided:
        print(f"  - {cat['label']}")
        print(f"    Walkthrough: modules/integrations/README.md#{cat.get('doc_anchor','')}")
        if cat.get("env_hint"):
            print(f"    Provide {cat['env_hint']} (see .env.example).")

# flip integrations: false -> true in the user config, if it exists
try:
    lines = open(config_path).read().splitlines()
    out, flipped = [], False
    for ln in lines:
        if (not flipped and ln.lstrip().startswith("integrations:")
                and "false" in ln):
            out.append(ln.replace("false", "true", 1)); flipped = True
        else:
            out.append(ln)
    if flipped:
        open(config_path, "w").write("\n".join(out) + "\n")
        print()
        print(f"  {GREEN}ok{NC}   set integrations: true in {config_path}")
except FileNotFoundError:
    pass
PYEOF

echo
bold "Done."
echo "Review .mcp.json, then inside a Claude Code session run:  claude mcp list"
echo "Re-run any time to add more:  bash scripts/install-integrations.sh"
