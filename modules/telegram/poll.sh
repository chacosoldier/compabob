#!/usr/bin/env bash
# Compabob: Telegram poller.
#
# Long-polls Telegram for inbound messages. For each text message from your
# allowed chat it asks the assistant for a reply and saves that reply as a DRAFT
# in reports/telegram/. It NEVER sends anything: you review the draft and, only
# if you want it sent, run modules/telegram/send.sh yourself.
#
#   usage: bash modules/telegram/poll.sh     (runs until you stop it with Ctrl-C)
set -uo pipefail

MODULE_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$MODULE_DIR/../.." && pwd)"
cd "$PROJECT_DIR" || exit 1

# launchd and cron run with a minimal PATH; put common tool dirs on it so the
# claude and python3 binaries are found when this runs unattended.
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$HOME/.npm-global/bin:$PATH"
# Tell the assistant nobody is watching (see hooks/hook-inject-now.sh).
export COMPABOB_RUN_CONTEXT=scheduled

# --- secrets ---------------------------------------------------------------
[ -f .env ] && { set -a; . ./.env; set +a; }
TOKEN="${TELEGRAM_BOT_TOKEN:-}"
ALLOWED="${TELEGRAM_ALLOWED_CHAT_ID:-}"

if [ -z "$TOKEN" ]; then
  echo "TELEGRAM_BOT_TOKEN is not set. Copy .env.example to .env and fill it in." >&2
  exit 1
fi
if [ -z "$ALLOWED" ]; then
  echo "TELEGRAM_ALLOWED_CHAT_ID is not set. Set it in .env so the bot only ever" >&2
  echo "answers you. Message @userinfobot on Telegram to find your chat id." >&2
  exit 1
fi
for c in claude curl python3; do
  command -v "$c" >/dev/null 2>&1 || { echo "$c not found; it is required." >&2; exit 1; }
done

API="https://api.telegram.org/bot$TOKEN"
GEN_DIR="$MODULE_DIR/generated"
OUT_DIR="$PROJECT_DIR/reports/telegram"
OFFSET_FILE="$GEN_DIR/offset"
LOG="$OUT_DIR/telegram.log"
PROMPT_FILE="$MODULE_DIR/tasks/inbound-reply.txt"
mkdir -p "$GEN_DIR" "$OUT_DIR"

trap 'echo; echo "poller stopped."; exit 0' INT

echo "Telegram poller running. Inbound messages become drafts in reports/telegram/."
echo "It never sends. Stop with Ctrl-C."

while true; do
  OFFSET="$(cat "$OFFSET_FILE" 2>/dev/null || echo 0)"
  RESP="$(curl -s --max-time 70 "$API/getUpdates?timeout=50&offset=$OFFSET" 2>/dev/null || echo '')"
  if [ -z "$RESP" ]; then sleep 5; continue; fi
  printf '%s' "$RESP" | python3 "$MODULE_DIR/_handle.py" \
    "$ALLOWED" "$OFFSET_FILE" "$OUT_DIR" "$PROMPT_FILE" "$LOG" || true
done
