#!/usr/bin/env bash
# SessionStart hook: orient the assistant at the start of a session (and after
# /clear or a compaction). Injects the memory index, a recent handover note, and
# one-line notices about things that need the user's attention.
# stdout from a SessionStart hook is added to the session context.

set -u
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$PROJECT_DIR" 2>/dev/null || exit 0

# The SessionStart payload (JSON on stdin) says why the session started:
# startup, resume, clear, compact or fork. Read it without jq.
input=""
[ -t 0 ] || input=$(cat 2>/dev/null || true)
SOURCE=$(printf '%s' "$input" | tr -d ' \n' | sed -n 's/.*"source":"\([a-z]*\)".*/\1/p')
SCHEDULED=0
[ "${COMPABOB_RUN_CONTEXT:-}" = "scheduled" ] && SCHEDULED=1
# shellcheck source=../scripts/lib/common.sh
. scripts/lib/common.sh 2>/dev/null || true
SETUP_TOKENS="${SETUP_TOKENS:-_YOUR_NAME_HERE_}"

MEMORY_CAP_BYTES=12288   # MEMORY.md loads every session; past this it crowds out the task
HANDOVER_MAX_DAYS=7

mtime() { stat -f %m "$1" 2>/dev/null || stat -c %Y "$1" 2>/dev/null || echo 0; }

MEM="memory/MEMORY.md"
if [ -f "$MEM" ]; then
  echo "## Memory index (memory/MEMORY.md)"
  echo
  cat "$MEM"
  echo
  echo "Follow the links above into memory/topics/ only as needed."
fi

HANDOVER=".tmp/handover.md"
if [ -f "$HANDOVER" ]; then
  age_h=$(( ( $(date +%s) - $(mtime "$HANDOVER") ) / 3600 ))
  echo
  if [ "$age_h" -lt $(( HANDOVER_MAX_DAYS * 24 )) ]; then
    echo "## Handover from a previous session (.tmp/handover.md, written ${age_h}h ago)"
    echo
    cat "$HANDOVER"
  else
    echo "Note: .tmp/handover.md is $(( age_h / 24 )) days old and was not loaded. Read it only if the user asks to resume that work."
  fi
fi

# Notices: one line each, only when there is something to say.
NOTICES=()
if [ -f "$MEM" ]; then
  bytes=$(wc -c < "$MEM" | tr -d ' ')
  [ "$bytes" -gt "$MEMORY_CAP_BYTES" ] && \
    NOTICES+=("memory/MEMORY.md is ${bytes} bytes, over the ${MEMORY_CAP_BYTES}-byte cap. Offer to move detail into memory/topics/ and keep one-line pointers.")
fi
for f in reports/proactive/*-"$(date +%Y-%m-%d)".md; do
  [ -f "$f" ] && NOTICES+=("Today's scheduled output is ready: $f. Mention it to the user.")
done
if [ -f reports/proactive/proactive.log ]; then
  # Log lines start with "[YYYY-MM-DD HH:MM]"; only the last 7 days count.
  since=$(date -v-7d +%Y-%m-%d 2>/dev/null || date -d '7 days ago' +%Y-%m-%d 2>/dev/null || echo 0000)
  failed=$(grep FAILED reports/proactive/proactive.log | awk -v s="[$since" '$0 >= s' | tail -3)
  [ -n "$failed" ] && NOTICES+=("Recent scheduled-run failures (reports/proactive/proactive.log): $(echo "$failed" | tr '\n' ' ')")
fi
if [ -f scripts/migrate-config.sh ]; then
  missing=$(bash scripts/migrate-config.sh --check 2>/dev/null) || \
    NOTICES+=("$missing. Suggest the user run: bash scripts/migrate-config.sh")
fi

# Setup state. The assistant should open with this, before any task.
if [ "$SCHEDULED" = 0 ]; then
  SETUP_STATE="done"
  if [ ! -f "$MEM" ]; then
    SETUP_STATE=missing
  elif grep -qE '\{\{(ASSISTANT_NAME|USER_NAME|USER_ROLE|PRIMARY_LANGUAGE)\}\}' "$MEM"; then
    SETUP_STATE=unfinished
  elif grep -qE "$SETUP_TOKENS" "$MEM"; then
    SETUP_STATE=noname
  fi
  case "$SETUP_STATE" in
    missing)    NOTICES+=("Setup has not run: memory/MEMORY.md does not exist, so you do not yet know the user's name or your own. Greet the user, say the one-time setup is still pending (a few short questions, about a minute), and offer to run it now with /setup. Start other work only if they decline.") ;;
    unfinished) NOTICES+=("Setup did not finish: memory/MEMORY.md still contains {{...}} placeholders. Tell the user plainly and offer /setup, which fills in the blanks and keeps every file that already exists.") ;;
    noname)     NOTICES+=("Setup ran without a name: memory/MEMORY.md says _YOUR_NAME_HERE_. Ask the user what to call them, then offer /setup to write it in.") ;;
  esac

  # First-hour nudge: once, in the first session after setup, while the vault still
  # holds only the shipped #example notes (or none). The marker makes it one-time,
  # including across /clear and compaction, which also run this hook.
  NUDGE_MARK=".tmp/first-hour-nudge.done"
  if [ "$SETUP_STATE" = "done" ] && [ -d vault ] && [ ! -f "$NUDGE_MARK" ]; then
    real_note=$(find vault -name '*.md' ! -path '*/.obsidian/*' ! -name '00-Home.md' \
                  ! -path 'vault/Sources/README.md' -exec grep -L -E '^tags:.*example' {} + 2>/dev/null | head -1)
    if [ -z "$real_note" ]; then
      NOTICES+=("First session after setup: the vault holds only the fictional #example notes. Greet the user by the name in the memory index above and introduce yourself by yours. Then offer, in two lines, the two steps that make you an assistant rather than a chat: connecting their email and calendar (they click Connect once at claude.ai/customize/connectors, you guide them), and a ten-minute interview that sets up their knowledge base (projects, people, recurring deadlines). Then wait. This notice shows once.")
      mkdir -p .tmp 2>/dev/null && date '+%Y-%m-%d %H:%M' > "$NUDGE_MARK" 2>/dev/null || true
    fi
  fi
fi

# Kit changes since the last session: an update pulled new commits, or the user has
# edited kit files locally (their own data is git-ignored, so it never shows here).
# Skipped after a compaction, which would report the session's own work, and in
# scheduled runs, which would record a new HEAD before the user's session reads it.
HEAD_STATE=".tmp/last-session-head"
if [ "$SCHEDULED" = 0 ] && [ "$SOURCE" != "compact" ] \
   && HEAD_NOW=$(git --no-optional-locks rev-parse HEAD 2>/dev/null); then
  HEAD_OLD=$(cat "$HEAD_STATE" 2>/dev/null || true)
  if [ -n "$HEAD_OLD" ] && [ "$HEAD_OLD" != "$HEAD_NOW" ]; then
    n=$(git --no-optional-locks rev-list --count "$HEAD_OLD..$HEAD_NOW" 2>/dev/null || true)
    NOTICES+=("The kit changed since the last session: ${HEAD_OLD:0:8} to ${HEAD_NOW:0:8}${n:+ ($n commit(s))}. If the user asks what is new, CHANGELOG.md has it.")
  fi
  edited=$(git --no-optional-locks status --porcelain 2>/dev/null | cut -c4- | sed 's/^"//' \
             | awk -F/ '{ print (NF > 1 ? $1 "/" : $1) }' | sort -u | head -8 | tr '\n' ' ')
  if [ -n "$edited" ]; then
    NOTICES+=("Kit files edited locally and not in the upstream kit: ${edited% }. ./update.sh merges these when the kit updates; mention it only if the user asks about updating.")
  fi
  { mkdir -p .tmp && printf '%s\n' "$HEAD_NOW" > "$HEAD_STATE"; } 2>/dev/null || true
fi

if [ ${#NOTICES[@]} -gt 0 ]; then
  echo
  echo "## Notices"
  for n in "${NOTICES[@]}"; do echo "- $n"; done
fi

exit 0
