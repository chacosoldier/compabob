#!/usr/bin/env bash
# Compabob: integration installer.
#
# Adds MCP servers to .mcp.json from scripts/integrations-catalog.json.
# Keyless integrations (web, utility) are configured fully. The keyed one
# (search) is configured as far as possible and the remaining key step is
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

# shellcheck source=scripts/lib/common.sh
source scripts/lib/common.sh

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  bold "Compabob: integration installer"
  echo "Adds MCP servers to .mcp.json. Categories: web, utility, search."
  echo "  install-integrations.sh web utility   configure those categories"
  echo "  install-integrations.sh               interactive picker"
  exit 0
fi

[ -f "$CATALOG" ] || { echo "missing $CATALOG — run this from inside the kit" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "python3 is required" >&2; exit 1; }

bold ""
bold "Compabob: integrations"
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
  ask_cat utility "time and timezone math (no key)"
  ask_cat search  "exa web search (needs an API key)"
  echo
fi

if [ "${#CHOSEN[@]}" -eq 0 ]; then
  warn "nothing chosen — no changes made"
  exit 0
fi

# --- preflight: runtimes (warn only, never block) -------------------------
command -v npx >/dev/null 2>&1 && ok "npx found" \
  || warn "npx not found — install Node.js; npx-based servers stay registered but will not run until you do"
command -v uvx >/dev/null 2>&1 && ok "uvx found" \
  || warn "uvx not found — install uv (https://docs.astral.sh/uv/); uvx-based servers stay registered but will not run until you do"
echo

# --- merge .mcp.json + report (Python does the JSON work) -----------------
# .mcp.json is created only when at least one server is actually added, so an
# unknown category or an all-skipped run never leaves an empty file behind.
python3 - "$CATALOG" "$MCP_FILE" "$MCP_SEED" "${CHOSEN[@]}" <<'PYEOF'
import json, os, sys

catalog_path, mcp_path, seed_path, *chosen = sys.argv[1:]
GREEN, YELLOW, BOLD, NC = "\033[0;32m", "\033[1;33m", "\033[1m", "\033[0m"

catalog = json.load(open(catalog_path))
cats = {c["id"]: c for c in catalog["categories"]}

existed = os.path.exists(mcp_path)
if existed:
    mcp = json.load(open(mcp_path))
elif os.path.exists(seed_path):
    mcp = json.load(open(seed_path))
else:
    mcp = {}
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
if added:
    with open(mcp_path, "w") as f:
        json.dump(mcp, f, indent=2)
        f.write("\n")
    if not existed:
        print(f"  {GREEN}ok{NC}   created {mcp_path}")

for name in added:   print(f"  {GREEN}ok{NC}   added MCP server: {name}")
for name in skipped: print(f"  {GREEN}ok{NC}   already present, kept: {name}")
for cid in unknown:  print(f"  {YELLOW}warn{NC} unknown category (ignored): {cid}")

# If nothing was added, skipped, OR queued for guided setup (e.g. every
# requested category was unknown), nothing actually happened. Fail loud so the
# user notices instead of seeing a misleading "Done.".
if not added and not skipped and not guided:
    print()
    print(f"  {YELLOW}warn{NC} nothing was installed. Valid categories are: web | utility | search")
    sys.exit(1)

if guided:
    print()
    print(f"{BOLD}One more step for the keyed integrations:{NC}")
    for cat in guided:
        print(f"  - {cat['label']}")
        print(f"    Walkthrough: modules/integrations/README.md#{cat.get('doc_anchor','')}")
        if cat.get("env_hint"):
            print(f"    Provide {cat['env_hint']} (see .env.example).")
PYEOF

if set_config_flag integrations true "$CONFIG"; then
  echo
  ok "set integrations: true in $CONFIG"
fi

echo
bold "Done."
echo "Review .mcp.json, then in a terminal in this folder run:  claude mcp list"
echo "(Servers show as pending until you start claude here and approve the project's MCP servers.)"
echo "Re-run any time to add more:  bash scripts/install-integrations.sh"
