#!/usr/bin/env bash
# Compabob: one-time setup.
# Creates your personal files (vault/, memory/, config/user.config.yaml) from the shipped *.example
# seeds and fills in your details. Those files live outside git, so a kit update can
# never touch them. Safe to re-run: it never overwrites files you already have, and a
# run that stopped halfway is finished by running it again.
#
#   ./setup.sh             asks seven short questions
#   ./setup.sh --help      every question can also be answered with an option
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# shellcheck source=scripts/lib/common.sh
source scripts/lib/common.sh

# --- 0. Options (all optional) ---------------------------------------------
# Every question below can also be answered up front, so setup can run without a
# keyboard: from the /setup skill inside Claude Code, or from CI. An option answers
# its question. --non-interactive answers anything still open with its default.
usage() {
  cat <<'EOF'
usage: ./setup.sh [options]

  --assistant NAME     what the assistant is called              (default: Aide)
  --user NAME          your name
  --role TEXT          your role or job title                     (default: Knowledge Worker)
  --language TEXT      your main working language                 (default: English)
  --persona ID         generalist | consultant | engineer | sales | founder | researcher, or 1-6
  --focus TEXT         a sentence or two on what you work on
  --integrations       also set up the keyless integrations (web and browser tools, time)
  --no-integrations    skip them (the default)
  --non-interactive    never ask; use the default for anything not given above
  -h, --help           show this help

Without options, setup asks each of these as a question.
EOF
}

ASSISTANT_NAME=""; USER_NAME=""; USER_ROLE=""; PRIMARY_LANGUAGE=""
PERSONA_PICK="";   WORK_ON="";   DO_INT="";    INT_FROM_FLAG=0; NONINTERACTIVE=0
missing_value() { echo "setup.sh: $1 needs a value" >&2; usage >&2; exit 2; }
while [ $# -gt 0 ]; do
  case "$1" in
    --assistant) [ $# -ge 2 ] || missing_value "$1"; ASSISTANT_NAME="$2";   shift 2 ;;
    --user)      [ $# -ge 2 ] || missing_value "$1"; USER_NAME="$2";        shift 2 ;;
    --role)      [ $# -ge 2 ] || missing_value "$1"; USER_ROLE="$2";        shift 2 ;;
    --language)  [ $# -ge 2 ] || missing_value "$1"; PRIMARY_LANGUAGE="$2"; shift 2 ;;
    --persona)   [ $# -ge 2 ] || missing_value "$1"; PERSONA_PICK="$2";     shift 2 ;;
    --focus)     [ $# -ge 2 ] || missing_value "$1"; WORK_ON="$2";          shift 2 ;;
    --integrations)    DO_INT="y"; INT_FROM_FLAG=1; shift ;;
    --no-integrations) DO_INT="n"; shift ;;
    --non-interactive|--yes|-y) NONINTERACTIVE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "setup.sh: unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

bold ""
bold "Compabob: setup"
echo "Creates your personal workspace and fills in your details. About a minute."
echo

# --- 1. Prerequisites --------------------------------------------------------
# Setup writes your details into the seed files with a short Python program, so
# without a working python3 it cannot finish. It stops here, before creating
# anything, rather than leave half-filled files behind. git and claude only warn.
python3_works() {
  command -v python3 >/dev/null 2>&1 || return 1
  # A Mac without the Command Line Tools ships /usr/bin/python3 as a stub that
  # only opens an "install the developer tools?" window. Spot it without running
  # it, so no window pops up in the middle of setup.
  if [ "$(uname -s)" = "Darwin" ] && [ "$(command -v python3)" = "/usr/bin/python3" ] \
     && ! xcode-select -p >/dev/null 2>&1; then
    return 1
  fi
  python3 -c 'import sys' >/dev/null 2>&1
}
if python3_works; then
  ok "python3 found"
else
  echo
  echo "Setup needs Python 3, and this computer does not have a working one yet."
  if [ "$(uname -s)" = "Darwin" ]; then
    echo "  Fix (Mac): run   xcode-select --install   and click Install in the window that"
    echo "  opens (a few minutes). Or, if you use Homebrew:   brew install python"
  else
    echo "  Fix (Linux): install it with your package manager, for example  sudo apt install python3"
  fi
  echo "Then run setup again. Nothing has been created or changed."
  exit 1
fi
command -v git >/dev/null 2>&1 && ok "git found" \
  || warn "git not found. Fine for now; you need it later to update the kit"
if command -v claude >/dev/null 2>&1; then
  ok "claude command found"
elif [ -n "${CLAUDECODE:-}" ]; then
  ok "running inside Claude Code"
else
  warn "claude command not found. Fine if you use the Claude desktop app or VS Code."
  say  "For the terminal, install it with:  curl -fsSL https://claude.ai/install.sh | bash"
fi
echo

make_runtime_dirs() {
  chmod +x setup.sh update.sh scripts/*.sh scripts/lib/*.sh hooks/*.sh hooks/*.py \
           hooks/prompt-injection-defender/*.py modules/*/*.sh 2>/dev/null || true
  mkdir -p .tmp reports
}

# --- 2. What is there to do? -------------------------------------------------
# Fresh: your files do not exist yet. Unfinished: they exist but still hold blanks
# because an earlier run stopped early; only the blanks get filled. Done: nothing
# left to set up, so no questions are asked.
has_blanks() { [ -e "$1" ] && grep -rqE "$SETUP_TOKENS" "$1" 2>/dev/null; }
has_braces() { [ -e "$1" ] && grep -rqE '\{\{(ASSISTANT_NAME|USER_NAME|USER_ROLE|PRIMARY_LANGUAGE)\}\}' "$1" 2>/dev/null; }

FRESH=0; UNFINISHED=0; NEED_IDENTITY=0
for p in vault memory config/user.config.yaml; do
  if [ ! -e "$p" ]; then FRESH=1; NEED_IDENTITY=1
  elif has_blanks "$p"; then
    UNFINISHED=1
    if has_braces "$p"; then NEED_IDENTITY=1; fi
  fi
done
# The persona is offered only while role-and-priorities.md is still the untouched template.
PERSONA_PENDING=0
if [ ! -d memory ] || grep -qF 'Core responsibilities: [fill in].' memory/topics/role-and-priorities.md 2>/dev/null; then
  PERSONA_PENDING=1
fi

if [ "$FRESH" = 0 ] && [ "$UNFINISHED" = 0 ]; then
  bold "Already set up."
  echo "Your assistant is called \"$(cfg_get assistant name)\" and knows you as \"$(cfg_get user name)\"."
  echo "Persona: $(cfg_get persona preset || true)."
  echo
  echo "To change any of this, edit config/user.config.yaml and memory/MEMORY.md, or ask your"
  echo "assistant to. To start from scratch, move vault/, memory/ and config/user.config.yaml"
  echo "somewhere else first, then run setup again."
  if [ ! -e .claude/settings.local.json ]; then
    cp .claude/settings.local.json.template .claude/settings.local.json
    ok "created .claude/settings.local.json"
  fi
  make_runtime_dirs
  exit 0
fi
if [ "$FRESH" = 0 ]; then
  warn "an earlier setup stopped early: your files exist but still have blanks. Only the blanks get filled now."
  echo
fi

# --- 3. Questions ------------------------------------------------------------
# In piped / scripted mode we add a newline after `read` so warnings emitted
# right after a prompt do not visually collide with the prompt line.
ask() {  # ask VARNAME "Question" "default"
  local __var="$1" __q="$2" __def="${3:-}" __ans="" __cur=""
  eval "__cur=\${$__var:-}"
  if [ -n "$__cur" ]; then                 # answered by an option: show it, skip the prompt
    say "$__q: $__cur"
    return 0
  fi
  if [ "$NONINTERACTIVE" = 1 ]; then       # --non-interactive: take the default
    say "$__q: ${__def:-(left blank)}"
    eval "$__var=\$__def"
    return 0
  fi
  if [ -n "$__def" ]; then printf '%s [%s]: ' "$__q" "$__def"; else printf '%s: ' "$__q"; fi
  read -r __ans || true
  [ -t 0 ] || echo
  [ -z "$__ans" ] && __ans="$__def"
  eval "$__var=\$__ans"
}

if [ "$NEED_IDENTITY" = 1 ]; then
  bold "Tell me about you and your assistant:"
  ask ASSISTANT_NAME   "What should the assistant be called" "Aide"
  # No `whoami` default: it leaks the OS account name (root, ubuntu, runner, ...)
  # into personalized files for users who just press Enter. Empty is handled below.
  ask USER_NAME        "Your name (used in your assistant's memory)" ""
  ask USER_ROLE        "Your role / job title"               "Knowledge Worker"
  ask PRIMARY_LANGUAGE "Your main working language"          "English"
  echo
else
  # Only the name is missing (an earlier run got none). Ask just that.
  ask USER_NAME        "Your name (used in your assistant's memory)" ""
fi
if [ -z "$USER_NAME" ]; then
  warn "no name given, using '_YOUR_NAME_HERE_' as a placeholder. Run setup again with your name to fill it in"
  USER_NAME="_YOUR_NAME_HERE_"
fi

PERSONA=""
if [ "$PERSONA_PENDING" = 1 ]; then
  bold "Which best describes your work?"
  echo "  1) generalist   knowledge work broadly, the neutral default"
  echo "  2) consultant   client-facing delivery, proposals, stakeholder work"
  echo "  3) engineer     shipping software and owning technical decisions"
  echo "  4) sales        pipeline, deals, accounts, quota"
  echo "  5) founder      running a business: strategy, fundraising, hiring, product"
  echo "  6) researcher   academia and R&D: literature, paper drafting, experiments"
  ask PERSONA_PICK "Pick 1-6 (or the name)" "1"
  case "$PERSONA_PICK" in
    1|generalist)  PERSONA=generalist;;
    2|consultant)  PERSONA=consultant;;
    3|engineer)    PERSONA=engineer;;
    4|sales)       PERSONA=sales;;
    5|founder)     PERSONA=founder;;
    6|researcher)  PERSONA=researcher;;
    *)             warn "did not recognize \"$PERSONA_PICK\", using generalist"; PERSONA=generalist;;
  esac
  ask WORK_ON "In a sentence or two, what do you work on" ""
  echo
fi

# --- 4. Create your personal files from the seeds (never overwrite) --------
seed() {  # seed SRC DEST
  local src="$1" dest="$2"
  if [ -e "$dest" ]; then
    ok "$dest already exists, keeping your version"
  elif [ -e "$src" ]; then
    cp -R "$src" "$dest"
    ok "created $dest"
  fi
}
seed "vault.example"                        "vault"
seed "memory.example"                       "memory"
seed "config/user.config.yaml.template"     "config/user.config.yaml"
seed ".claude/settings.local.json.template" ".claude/settings.local.json"

# --- 5. Apply the persona preset ------------------------------------------
# Persona runs BEFORE the fill pass so that any {{USER_NAME}}-style tokens a user
# typed into the "what you work on" answer resolve too.
# shellcheck source=scripts/lib/personas.sh
source scripts/lib/personas.sh
if [ -n "$PERSONA" ]; then
  apply_persona "$PERSONA" "$WORK_ON" || warn "persona step skipped, role-and-priorities.md left as the template"
fi

# --- 6. Fill your details into your files (all git-ignored) ----------------
# Runs over every personal file that still has a blank, not only the ones created
# a moment ago. So if a run ever stops halfway, running setup again finishes it.
TO_FILL=()
for p in vault memory config/user.config.yaml; do
  if has_blanks "$p"; then TO_FILL+=("$p"); fi
done
if [ ${#TO_FILL[@]} -gt 0 ]; then
  ASSISTANT_NAME="$ASSISTANT_NAME" USER_NAME="$USER_NAME" USER_ROLE="$USER_ROLE" \
  PRIMARY_LANGUAGE="$PRIMARY_LANGUAGE" \
  python3 - "${TO_FILL[@]}" <<'PYEOF'
import os, sys, pathlib

repl = {
    "{{ASSISTANT_NAME}}":   os.environ["ASSISTANT_NAME"],
    "{{USER_NAME}}":        os.environ["USER_NAME"],
    "{{USER_ROLE}}":        os.environ["USER_ROLE"],
    "{{PRIMARY_LANGUAGE}}": os.environ["PRIMARY_LANGUAGE"],
}
# A run that got no name wrote _YOUR_NAME_HERE_; a later run with a real name fills it.
if os.environ["USER_NAME"] != "_YOUR_NAME_HERE_":
    repl["_YOUR_NAME_HERE_"] = os.environ["USER_NAME"]
# A question that was not asked this run has no answer: leave its blank alone.
repl = {k: v for k, v in repl.items() if v}

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
print(f"  \033[0;32mok\033[0m   personalized {n} file(s)")
PYEOF
fi

# --- 7. Permissions and runtime dirs --------------------------------------
make_runtime_dirs
ok "made scripts executable and created runtime directories"

# --- 8. Integrations (optional) -------------------------------------------
echo
bold "Integrations (optional): web and browser tools, web search."
echo "These add tools your assistant can use. You can also do this later."
ask DO_INT "Set them up now? (y/N)" "n"
case "$DO_INT" in
  [Yy]*)
    if [ "$INT_FROM_FLAG" = 1 ]; then
      bash scripts/install-integrations.sh web utility || warn "integration setup did not finish. Run it again later"
    else
      bash scripts/install-integrations.sh || warn "integration setup did not finish. Run it again later"
    fi ;;
  *) say "skipped. Run  bash scripts/install-integrations.sh  any time" ;;
esac

# --- 9. Done ---------------------------------------------------------------
echo
bold "Setup complete."
echo "Your assistant is called \"$(cfg_get assistant name)\" and knows you as \"$(cfg_get user name)\". Persona: $(cfg_get persona preset || true)."
FAILS=0
bash scripts/init.sh >/dev/null 2>&1 || FAILS=$?
if [ "$FAILS" -eq 0 ]; then
  ok "health check passed"
else
  warn "the health check found $FAILS problem(s). Run  bash scripts/init.sh  to see them"
fi
echo
if [ -n "${CLAUDECODE:-}" ]; then
  echo "Done. From the next Claude Code session on, your assistant loads its memory automatically."
else
  echo "Next:"
  echo "  1. Start it:        claude   (or open this folder in the Claude desktop app or VS Code)"
  echo "  2. Refine memory:   memory/topics/role-and-priorities.md is pre-filled. Edit it"
  echo "  3. Opt-in modules:  see modules/README.md"
fi
echo
echo "Your data (vault/, memory/, config/user.config.yaml, .mcp.json, .env) is git-ignored."
echo "Update the kit any time with ./update.sh. It never touches those files."
