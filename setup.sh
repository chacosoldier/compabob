#!/usr/bin/env bash
# Compabob — one-time setup.
# Creates your personal files (vault/, memory/, config/) from the shipped *.example
# seeds and fills in your details. Those files live outside git, so a kit update can
# never touch them. Safe to re-run: it never overwrites files you already have.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

bold() { printf '\033[1m%s\033[0m\n' "$1"; }
ok()   { printf '  \033[0;32mok\033[0m   %s\n' "$1"; }
warn() { printf '  \033[1;33mwarn\033[0m %s\n' "$1"; }

bold ""
bold "Compabob — setup"
echo "Creates your personal workspace and fills in your details. About a minute."
echo

# --- 1. Prerequisites (warn only, never block) -----------------------------
command -v python3 >/dev/null 2>&1 && ok "python3 found" || warn "python3 not found — install Python 3.10+"
command -v git     >/dev/null 2>&1 && ok "git found"     || warn "git not found"
command -v claude  >/dev/null 2>&1 && ok "claude CLI found" \
  || warn "claude CLI not found — install: npm install -g @anthropic-ai/claude-code"
echo

# --- 2. Prompt -------------------------------------------------------------
# In piped / scripted mode we add a newline after `read` so warnings emitted
# right after a prompt do not visually collide with the prompt line.
ask() {  # ask VARNAME "Question" "default"
  local __var="$1" __q="$2" __def="${3:-}" __ans=""
  if [ -n "$__def" ]; then printf '%s [%s]: ' "$__q" "$__def"; else printf '%s: ' "$__q"; fi
  read -r __ans || true
  [ -t 0 ] || echo
  [ -z "$__ans" ] && __ans="$__def"
  eval "$__var=\$__ans"
}

bold "Tell me about you and your assistant:"
ask ASSISTANT_NAME   "What should the assistant be called" "Aide"
# No `whoami` default: it leaks the OS account name (root, ubuntu, runner, ...)
# into personalized files for users who just press Enter. Empty is handled below.
ask USER_NAME        "Your name (used in your assistant's memory)" ""
if [ -z "$USER_NAME" ]; then
  warn "no name given — using '_YOUR_NAME_HERE_' as a placeholder; edit memory/MEMORY.md to fix"
  USER_NAME="_YOUR_NAME_HERE_"
fi
ask USER_ROLE        "Your role / job title"               "Knowledge Worker"
ask PRIMARY_LANGUAGE "Your main working language"          "English"
echo

bold "Which best describes your work?"
echo "  1) generalist   2) consultant   3) engineer   4) sales   5) founder   6) researcher"
ask PERSONA_PICK "Pick 1-6 (or the name)" "1"
case "$PERSONA_PICK" in
  1|generalist)  PERSONA=generalist;;
  2|consultant)  PERSONA=consultant;;
  3|engineer)    PERSONA=engineer;;
  4|sales)       PERSONA=sales;;
  5|founder)     PERSONA=founder;;
  6|researcher)  PERSONA=researcher;;
  *)             warn "did not recognize \"$PERSONA_PICK\" — using generalist"; PERSONA=generalist;;
esac
ask WORK_ON "In a sentence or two, what do you work on" ""
echo

# --- 3. Create your personal files from the seeds (never overwrite) --------
CREATED=()
seed() {  # seed SRC DEST
  local src="$1" dest="$2"
  if [ -e "$dest" ]; then
    warn "$dest already exists — keeping your version"
  elif [ -e "$src" ]; then
    cp -R "$src" "$dest"
    ok "created $dest"
    CREATED+=("$dest")
  fi
}
seed "vault.example"                        "vault"
seed "memory.example"                       "memory"
seed "config/user.config.yaml.template"     "config/user.config.yaml"
seed ".claude/settings.local.json.template" ".claude/settings.local.json"

# --- 4. Apply the persona preset ------------------------------------------
# Persona runs BEFORE the placeholder pass so that any {{USER_NAME}}-style
# tokens a user typed into the "what you work on" prompt resolve correctly in
# the seeded role-and-priorities.md (persona files don't use those tokens
# themselves, so this swap is otherwise a no-op for them).
# shellcheck source=scripts/lib/personas.sh
source scripts/lib/personas.sh
apply_persona "$PERSONA" "$WORK_ON" || warn "persona step skipped — role-and-priorities.md left as the template"

# --- 5. Fill your details into the files just created (all git-ignored) ----
if [ ${#CREATED[@]} -gt 0 ]; then
  ASSISTANT_NAME="$ASSISTANT_NAME" USER_NAME="$USER_NAME" USER_ROLE="$USER_ROLE" \
  PRIMARY_LANGUAGE="$PRIMARY_LANGUAGE" \
  python3 - "${CREATED[@]}" <<'PYEOF'
import os, sys, pathlib

repl = {
    "{{ASSISTANT_NAME}}":   os.environ["ASSISTANT_NAME"],
    "{{USER_NAME}}":        os.environ["USER_NAME"],
    "{{USER_ROLE}}":        os.environ["USER_ROLE"],
    "{{PRIMARY_LANGUAGE}}": os.environ["PRIMARY_LANGUAGE"],
}

def esc_yaml(v):
    # values land inside double-quoted YAML strings; escape so a quote or
    # backslash in a name cannot produce an invalid file.
    return v.replace("\\", "\\\\").replace('"', '\\"')

exts = {".md", ".json", ".yaml", ".yml", ".txt"}
n = 0
for arg in sys.argv[1:]:
    root = pathlib.Path(arg)
    files = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file()]
    for p in files:
        if p.suffix not in exts:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        is_yaml = p.suffix in (".yaml", ".yml")
        new = text
        for key, val in repl.items():
            new = new.replace(key, esc_yaml(val) if is_yaml else val)
        if new != text:
            p.write_text(new, encoding="utf-8")
            n += 1
print(f"  ok   personalized {n} file(s)")
PYEOF
else
  warn "nothing new created — your existing files were kept (your data is safe)"
fi

# --- 6. Permissions and runtime dirs --------------------------------------
chmod +x setup.sh update.sh scripts/*.sh scripts/lib/*.sh hooks/*.sh hooks/*.py \
         hooks/prompt-injection-defender/*.py modules/*/*.sh 2>/dev/null || true
mkdir -p .tmp reports
ok "made scripts executable and created runtime directories"

# --- 7. Integrations (optional) -------------------------------------------
echo
bold "Integrations (optional): web + browser tools, web search, Google Workspace."
echo "These add MCP servers your assistant can use. You can also do this later."
ask DO_INT "Set them up now? (y/N)" "n"
case "$DO_INT" in
  [Yy]*) bash scripts/install-integrations.sh || warn "integration setup did not finish — run it again later" ;;
  *)     echo "  skipped — run  bash scripts/install-integrations.sh  any time" ;;
esac

# --- 8. Done ---------------------------------------------------------------
echo
bold "Setup complete."
echo "Your assistant is called \"$ASSISTANT_NAME\". Persona: $PERSONA."
echo
echo "Next:"
echo "  1. Start it:        claude"
echo "  2. Refine memory:   memory/topics/role-and-priorities.md is pre-filled — edit it"
echo "  3. Optional checks: bash scripts/init.sh"
echo "  4. Opt-in modules:  see modules/README.md"
echo
echo "Your data (vault/, memory/, config/user.config.yaml, .mcp.json, .env) is git-ignored."
echo "Update the kit any time with ./update.sh — it never touches those files."
