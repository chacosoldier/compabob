#!/usr/bin/env bash
# UserPromptSubmit hook: inject the current date and time so the assistant is
# never guessing "today". stdout from a UserPromptSubmit hook is added to context.
#
# Scheduled runs (proactive, telegram, linkedin-outreach) export
# COMPABOB_RUN_CONTEXT=scheduled. Without this line a headless run looks like a
# fresh interactive session and the assistant may stop to ask a question nobody
# is there to answer.

echo "Current time: $(date '+%Y-%m-%d %H:%M %Z (%A)')"
if [ "${COMPABOB_RUN_CONTEXT:-}" = "scheduled" ]; then
  echo "Run context: non-interactive scheduled run. No user is present: do not ask questions; finish the task and write the result where the prompt says."
fi
exit 0
