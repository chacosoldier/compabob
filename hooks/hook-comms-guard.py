#!/usr/bin/env python3
"""PreToolUse(Bash) hook: enforce draft-first for external communication.

The constitution says nothing leaves the machine without explicit human approval.
This hook blocks shell commands that would send email or messages directly. It is
a backstop, not the main mechanism: the assistant is instructed to draft first.

Reads the tool call as JSON on stdin. Exit 0 allows; exit 2 blocks. Fails open.
"""
import json
import re
import sys

# Commands that send a message or email.
SEND_BINARIES = [
    (r"\bsendmail\b", "sendmail"),
    (r"\bmail\s+-s\b", "the mail command"),
    (r"\bmutt\s+.*-s\b", "mutt"),
    (r"\bmailx\b", "mailx"),
    (r"\bswaks\b", "swaks (SMTP test tool)"),
    (r"\bosascript\b.*\b(Mail|Messages)\b", "AppleScript sending Mail or Messages"),
    # Running the helper, not reading it: `cat` or `grep` on send.sh stays allowed.
    (r"(?:^|[;&|(]\s*|\b(?:bash|sh|zsh|exec)\s+)(?:\S*/)?telegram/send\.sh\b", "the Telegram send helper"),
]

# curl / wget POSTs to known messaging or email delivery endpoints.
SEND_ENDPOINTS = re.compile(
    r"\b(curl|wget|http|https)\b.*("
    r"api\.telegram\.org/bot.*/sendmessage|"
    r"hooks\.slack\.com|slack\.com/api/chat\.postmessage|"
    r"api\.sendgrid\.com|api\.mailgun\.net|api\.postmarkapp\.com|"
    r"api\.resend\.com|graph\.microsoft\.com/.*/sendmail|"
    r"gmail\.googleapis\.com/.*/messages/send|"
    r"discord\.com/api/webhooks"
    r")",
    re.IGNORECASE,
)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    if data.get("tool_name") != "Bash":
        return 0
    command = (data.get("tool_input") or {}).get("command", "")
    if not isinstance(command, str):
        return 0

    matched = None
    for pattern, label in SEND_BINARIES:
        if re.search(pattern, command, re.IGNORECASE):
            matched = label
            break
    if not matched and SEND_ENDPOINTS.search(command):
        matched = "a messaging or email API endpoint"

    if matched:
        sys.stderr.write(
            f"Blocked: this command would send an external communication via {matched}. "
            "Draft the message and show it to the user for approval first. "
            "Once approved, the user sends it, or explicitly confirms this exact command.\n"
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
