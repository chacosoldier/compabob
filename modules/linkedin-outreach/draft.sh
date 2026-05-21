#!/usr/bin/env bash
# Compabob LinkedIn outreach: draft one invitation card for your review.
#
# Picks the person at the top of your queue, decides whether a genuine hook
# calls for a one-line note or a clean no-note invite, and writes a review card
# to reports/linkedin-outreach/cards/. It NEVER sends anything. You review the
# card, send the invite yourself on LinkedIn, then run record.sh.
#
#   usage: bash modules/linkedin-outreach/draft.sh
#          bash modules/linkedin-outreach/draft.sh --scheduled  (used by install.sh; skips weekends)
set -uo pipefail

MODULE_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$MODULE_DIR/../.." && pwd)"
cd "$PROJECT_DIR"

# launchd and cron run with a minimal PATH; put common tool dirs on it so the
# claude and python3 binaries are found when this runs unattended.
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$HOME/.npm-global/bin:$PATH"

[ -f .env ] && { set -a; . ./.env; set +a; }

for c in claude python3; do
  command -v "$c" >/dev/null 2>&1 || { echo "$c not found, it is required." >&2; exit 1; }
done

PRE_FLAG=""
[ "${1:-}" = "--scheduled" ] && PRE_FLAG="--enforce-weekday"

OUT_DIR="$PROJECT_DIR/reports/linkedin-outreach"
mkdir -p "$OUT_DIR/cards"
LOG="$OUT_DIR/draft.log"

# Preflight: weekday (when scheduled), one card at a time, daily cap, queue not
# empty. On any fail it prints a plain reason and we stop quietly.
if ! REASON="$(python3 "$MODULE_DIR/_outreach.py" preflight $PRE_FLAG)"; then
  echo "$REASON"
  exit 0
fi
echo "$REASON"
echo "Drafting a card with claude -p (model: sonnet)..."

claude -p "$(cat "$MODULE_DIR/prompts/draft-note.md")" \
  --model sonnet \
  --allowedTools "Read,Write" 2>&1 | tee -a "$LOG"

echo
CARD="$(ls -t "$OUT_DIR"/cards/*.md 2>/dev/null | head -1)"
if [ -n "${CARD:-}" ] && [ -f "$CARD" ]; then
  echo "Review the card:"
  echo "  $CARD"
  echo
  echo "When you have acted on it, record the outcome:"
  echo "  bash modules/linkedin-outreach/record.sh \"$CARD\" sent"
  echo "  (use 'rejected' if you decide not to reach out, 'skipped' if the profile was wrong)"
else
  echo "No card file was written. Check the output above or $LOG."
fi
