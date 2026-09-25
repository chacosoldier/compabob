#!/usr/bin/env bash
# Run one proactive task: invoke the assistant headless on a saved prompt and
# write the result to reports/proactive/. Used by the scheduler; also runnable
# by hand to test a task.
#   usage: run-task.sh <task-name>     (task-name matches tasks/<task-name>.txt)
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

# launchd and cron run with a minimal PATH; put common tool dirs on it so the
# claude and python3 binaries are found when this runs unattended.
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$HOME/.npm-global/bin:$PATH"
# Tell the assistant nobody is watching (see hooks/hook-inject-now.sh).
export COMPABOB_RUN_CONTEXT=scheduled

TASK="${1:-}"
if [ -z "$TASK" ]; then
  echo "usage: run-task.sh <task-name>" >&2
  exit 1
fi

PROMPT_FILE="$PROJECT_DIR/modules/proactive/tasks/$TASK.txt"
if [ ! -f "$PROMPT_FILE" ]; then
  echo "no such task: $TASK (expected $PROMPT_FILE)" >&2
  exit 1
fi

OUT_DIR="$PROJECT_DIR/reports/proactive"
mkdir -p "$OUT_DIR"
OUT="$OUT_DIR/$TASK-$(date +%Y-%m-%d).md"
LOG="$OUT_DIR/proactive.log"

if ! command -v claude >/dev/null 2>&1; then
  echo "[$(date '+%Y-%m-%d %H:%M')] $TASK skipped: claude CLI not found" >> "$LOG"
  exit 1
fi

cd "$PROJECT_DIR"
# --model sonnet keeps scheduled runs cheap; claude -p defaults to a larger model.
if claude -p "$(cat "$PROMPT_FILE")" --model sonnet > "$OUT" 2>>"$LOG"; then
  echo "[$(date '+%Y-%m-%d %H:%M')] $TASK ok -> $OUT" >> "$LOG"
else
  echo "[$(date '+%Y-%m-%d %H:%M')] $TASK FAILED (see above)" >> "$LOG"
  exit 1
fi
