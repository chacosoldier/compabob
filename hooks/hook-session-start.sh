#!/usr/bin/env bash
# SessionStart hook: orient the assistant at the start of a session (and after
# /clear or a compaction). Injects the memory index, a recent handover note, and
# one-line notices about things that need the user's attention.
# stdout from a SessionStart hook is added to the session context.

set -u
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$PROJECT_DIR" 2>/dev/null || exit 0

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

if [ ${#NOTICES[@]} -gt 0 ]; then
  echo
  echo "## Notices"
  for n in "${NOTICES[@]}"; do echo "- $n"; done
fi

exit 0
