#!/usr/bin/env bash
# PreToolUse hook: context-scoped action-surface guard.
#
# Checks each tool call against hooks/tool_scopes.yaml for the active context.
# Reasoning is unconstrained; only the action surface (sends, mutations,
# external writes) is bounded per context.
#
# Context detection order:
#   1. $CLAUDE_CONTEXT env var          (set by cron scripts / orchestrators)
#   2. /tmp/claude-context-<session_id> (written by skills at session start)
#   3. Default: "interactive"           (allow_all — no behavior change)
#
# Fail-open: YAML parse errors, unknown contexts, or missing scopes file all
# fall through as allow. A broken guard must never block real work.
#
# Blocks are logged to data/performance/tool-scope-blocks.jsonl so operators
# can tighten the scopes file based on what was actually attempted.

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
SCOPES_FILE="$PROJECT_DIR/hooks/tool_scopes.yaml"
CHECKER="$PROJECT_DIR/hooks/tool_scope_check.py"
LOG_FILE="$PROJECT_DIR/data/performance/tool-scope-blocks.jsonl"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)

# No tool name — fail open.
[ -z "$TOOL_NAME" ] && exit 0

# Detect active context.
CONTEXT="${CLAUDE_CONTEXT:-}"
if [ -z "$CONTEXT" ] && [ -f "/tmp/claude-context-${SESSION_ID}" ]; then
    CONTEXT=$(cat "/tmp/claude-context-${SESSION_ID}" 2>/dev/null | tr -d '[:space:]')
fi
CONTEXT="${CONTEXT:-interactive}"

# Scopes file or checker missing — fail open.
[ ! -f "$SCOPES_FILE" ] && exit 0
[ ! -f "$CHECKER" ] && exit 0

# Run checker. Prefer `uv run --script` (PEP-723 inline deps, no global install);
# fall back to plain `python3` if uv is not available and pyyaml is on the path.
if command -v uv >/dev/null 2>&1; then
    RESULT=$(uv run --script "$CHECKER" "$TOOL_NAME" "$CONTEXT" "$SCOPES_FILE" 2>/dev/null)
else
    RESULT=$(python3 "$CHECKER" "$TOOL_NAME" "$CONTEXT" "$SCOPES_FILE" 2>/dev/null)
fi

# Parse verdict — default allow on any failure.
VERDICT=$(echo "$RESULT" | python3 -c \
  "import json,sys; print(json.load(sys.stdin).get('verdict','allow'))" 2>/dev/null \
  || echo "allow")
REASON=$(echo "$RESULT" | python3 -c \
  "import json,sys; print(json.load(sys.stdin).get('reason','parse_error'))" 2>/dev/null \
  || echo "parse_error")

if [ "$VERDICT" = "deny" ]; then
    mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
    printf '%s\n' \
      "{\"ts\":\"$TIMESTAMP\",\"session\":\"$SESSION_ID\",\"context\":\"$CONTEXT\",\"tool\":\"$TOOL_NAME\",\"reason\":\"$REASON\"}" \
      >> "$LOG_FILE" 2>/dev/null || true

    # Build a safe JSON message (python handles quoting).
    MSG=$(python3 -c \
      "import json,sys; t,c=sys.argv[1],sys.argv[2]; print(json.dumps(f'Tool {t!r} is not permitted in context {c!r}. Edit hooks/tool_scopes.yaml to update the allowlist.'))" \
      "$TOOL_NAME" "$CONTEXT" 2>/dev/null \
      || echo '"Tool blocked by scope guard."')

    python3 -c "
import json, sys
msg = $MSG
print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'deny',
        'permissionDecisionReason': msg
    }
}))
" 2>/dev/null
    exit 0
fi

exit 0
