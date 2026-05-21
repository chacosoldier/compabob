#!/usr/bin/env bash
# Compabob LinkedIn outreach: record what you did with a drafted card.
#
# After you act on a card (send the invite on LinkedIn, or decide not to), run
# this so the module moves the person out of '## Queue' into the right section
# of your queue file and archives the card. Recording also frees the slot for
# the next draft.
#
#   usage: bash modules/linkedin-outreach/record.sh <card-file> <sent|rejected|skipped>
set -uo pipefail

MODULE_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$MODULE_DIR/../.." && pwd)"
cd "$PROJECT_DIR"

CARD="${1:-}"
OUTCOME="${2:-}"
if [ -z "$CARD" ] || [ -z "$OUTCOME" ]; then
  echo "usage: record.sh <card-file> <sent|rejected|skipped>" >&2
  echo "  card-file: a card from reports/linkedin-outreach/cards/ (file name or path)" >&2
  exit 1
fi

command -v python3 >/dev/null 2>&1 || { echo "python3 not found, it is required." >&2; exit 1; }
exec python3 "$MODULE_DIR/_outreach.py" record "$CARD" "$OUTCOME"
