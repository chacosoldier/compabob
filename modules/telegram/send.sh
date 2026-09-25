#!/usr/bin/env bash
# Compabob: Telegram send helper. THE ONLY THING THAT SENDS A MESSAGE.
#
# This is never called automatically. The comms-guard hook intercepts it, so
# sending always needs your explicit approval, exactly like sending an email.
#
#   usage: send.sh <chat_id> <draft-file>
#     draft-file: the markdown draft poll.sh wrote (in reports/telegram/), or any
#                 text file. From a poll.sh draft, only the "Draft reply" section
#                 is sent, so you can review and edit the draft before sending.
set -uo pipefail

MODULE_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$MODULE_DIR/../.." && pwd)"
cd "$PROJECT_DIR"

[ -f .env ] && { set -a; . ./.env; set +a; }
TOKEN="${TELEGRAM_BOT_TOKEN:-}"
CHAT="${1:-}"
FILE="${2:-}"

[ -z "$TOKEN" ] && { echo "TELEGRAM_BOT_TOKEN is not set (see .env)." >&2; exit 1; }
if [ -z "$CHAT" ] || [ -z "$FILE" ]; then
  echo "usage: send.sh <chat_id> <draft-file>" >&2
  exit 1
fi

SRC="$FILE"
[ -f "$SRC" ] || SRC="reports/telegram/$FILE"
[ -f "$SRC" ] || { echo "no such file: $FILE" >&2; exit 1; }

MSG="$(python3 - "$SRC" <<'PY'
import pathlib, sys
text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
marker = "## Draft reply (NOT sent)"
if marker in text:
    body = text.split(marker, 1)[1].split("\n---\n", 1)[0]
    print(body.strip())
else:
    print(text.strip())
PY
)"
[ -z "$MSG" ] && { echo "the message is empty, nothing to send." >&2; exit 1; }

echo "About to send to Telegram chat $CHAT:"
echo "----"
printf '%s\n' "$MSG"
echo "----"

if curl -s -X POST "https://api.telegram.org/bot$TOKEN/sendMessage" \
     --data-urlencode "chat_id=$CHAT" \
     --data-urlencode "text=$MSG" >/dev/null; then
  echo "sent."
else
  echo "send failed, check the token, the chat id, and your connection." >&2
  exit 1
fi
