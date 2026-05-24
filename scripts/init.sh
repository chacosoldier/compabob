#!/usr/bin/env bash
# Per-session health check. Run it any time to confirm the setup is intact.
# Local checks only, no network. Exit code is the number of failures.
set -u

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
WARN=0; FAIL=0
ok()   { printf "  ${GREEN}ok${NC}    %s\n" "$1"; }
warn() { printf "  ${YELLOW}warn${NC}  %s\n" "$1"; WARN=$((WARN+1)); }
fail() { printf "  ${RED}fail${NC}  %s\n" "$1"; FAIL=$((FAIL+1)); }

printf "\n${BOLD}Compabob — init check${NC}\n"
printf "%s\n\n" "$(date '+%Y-%m-%d %H:%M')"

# 1. Tooling
command -v python3 >/dev/null 2>&1 && ok "python3 ($(python3 --version 2>&1))" || fail "python3 not found"
command -v claude  >/dev/null 2>&1 && ok "claude CLI found" || warn "claude CLI not found (npm install -g @anthropic-ai/claude-code)"

# 2. Setup has run — your personal files exist
if [ -d vault ] && [ -d memory ] && [ -f config/user.config.yaml ]; then
  ok "setup has run (vault/, memory/, config present)"
else
  fail "setup has not run — run ./setup.sh"
fi

# 3. Core kit files
for f in CONSTITUTION.md CLAUDE.md .claude/settings.json; do
  [ -f "$f" ] && ok "present: $f" || fail "missing: $f"
done
[ -f memory/MEMORY.md ] && ok "present: memory/MEMORY.md" || fail "missing: memory/MEMORY.md (run ./setup.sh)"
[ -f .claude/settings.local.json ] && ok "present: settings.local.json" \
  || warn "settings.local.json missing — run ./setup.sh"

# 4. Settings JSON is valid
if [ -f .claude/settings.json ]; then
  if python3 -c 'import json; json.load(open(".claude/settings.json"))' 2>/dev/null; then
    ok ".claude/settings.json is valid JSON"
  else
    fail ".claude/settings.json is not valid JSON"
  fi
fi

# 5. Hooks referenced in settings exist on disk
if [ -f .claude/settings.json ]; then
  MISSING=$(python3 - <<'PY'
import json, re, os
try:
    cfg = json.load(open(".claude/settings.json"))
except Exception:
    raise SystemExit("")
missing = []
for events in cfg.get("hooks", {}).values():
    for entry in events:
        for hook in entry.get("hooks", []):
            cmd = hook.get("command", "")
            m = re.search(r'\$CLAUDE_PROJECT_DIR/(\S+?)"', cmd)
            if m and not os.path.exists(m.group(1)):
                missing.append(m.group(1))
print(",".join(missing))
PY
)
  if [ -z "$MISSING" ]; then ok "all wired hooks exist"; else fail "missing hook(s): $MISSING"; fi
fi

# 6. Agents and skills
AGENTS=$(find .claude/agents -maxdepth 1 -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
SKILLS=$(find .claude/skills -maxdepth 2 -name 'SKILL.md' 2>/dev/null | wc -l | tr -d ' ')
[ "$AGENTS" -gt 0 ] && ok "$AGENTS agent file(s)" || fail "no agents in .claude/agents/"
[ "$SKILLS" -gt 0 ] && ok "$SKILLS skill(s)" || warn "no skills in .claude/skills/"

# 7. Vault
[ -d vault/.obsidian ] && ok "vault is an Obsidian vault" || warn "vault/.obsidian missing"
[ -f "vault/00-Home.md" ] && ok "vault front door present" || warn "vault/00-Home.md missing"

# 8. Git
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  ok "git: branch $(git branch --show-current 2>/dev/null || echo '?')"
else
  warn "not a git clone — './update.sh' will not work (download is not a clone)"
fi

# 9. Module health (only checks what you have enabled)
if [ -f config/user.config.yaml ]; then
  if grep -qE '^[[:space:]]*integrations:[[:space:]]*true' config/user.config.yaml; then
    if [ -f .mcp.json ] && python3 -c 'import json; json.load(open(".mcp.json"))' 2>/dev/null; then
      ok "integrations enabled — .mcp.json is valid JSON"
    else
      # Hard fail: config and disk state contradict each other and the assistant
      # cannot use the missing servers. Either run install-integrations.sh, or
      # set integrations: false in config/user.config.yaml.
      fail "integrations enabled but .mcp.json is missing or invalid (run scripts/install-integrations.sh, or set integrations: false in config/user.config.yaml)"
    fi
  fi
  if grep -qE '^[[:space:]]*telegram:[[:space:]]*true' config/user.config.yaml; then
    if [ -f .env ] && grep -qE '^[[:space:]]*TELEGRAM_BOT_TOKEN=.+' .env; then
      ok "telegram enabled — bot token present in .env"
    else
      warn "telegram enabled but TELEGRAM_BOT_TOKEN is not set in .env"
    fi
  fi
fi

printf "\n"
if [ "$FAIL" -eq 0 ] && [ "$WARN" -eq 0 ]; then
  printf "${GREEN}${BOLD}All checks passed.${NC} Start the assistant with: claude\n\n"
elif [ "$FAIL" -eq 0 ]; then
  printf "${YELLOW}${BOLD}%d warning(s), 0 failures.${NC} Operational — warnings above are optional items, not breakage. Start with: claude\n\n" "$WARN"
else
  printf "${RED}${BOLD}%d failure(s), %d warning(s).${NC} Fix the failures first.\n\n" "$FAIL" "$WARN"
fi
exit "$FAIL"
