#!/usr/bin/env python3
"""Compabob: Telegram poller helper.

Reads a Telegram getUpdates response on stdin, drafts a reply for each text
message from the allowed chat, and advances the polling offset. It never sends
anything: each reply is written as a draft file for the user to review.

  argv: <allowed_chat_id> <offset_file> <out_dir> <prompt_file> <log_file>
"""
import datetime
import json
import pathlib
import subprocess
import sys


def main() -> int:
    allowed, offset_file, out_dir, prompt_file, log_file = sys.argv[1:6]

    def log(msg: str) -> None:
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file, "a", encoding="utf-8") as fh:
            fh.write(f"[{stamp}] {msg}\n")

    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        return 0
    if not data.get("ok"):
        return 0
    updates = data.get("result", [])
    if not updates:
        return 0

    try:
        instructions = pathlib.Path(prompt_file).read_text(encoding="utf-8").strip()
    except OSError:
        instructions = "Draft a short reply for the user to review. Do not send anything."

    max_update = None
    for upd in updates:
        uid = upd.get("update_id")
        if isinstance(uid, int):
            max_update = uid if max_update is None else max(max_update, uid)
        msg = upd.get("message") or upd.get("edited_message")
        if not msg:
            continue
        chat_id = str((msg.get("chat") or {}).get("id", ""))
        text = msg.get("text", "")
        sender = (msg.get("from") or {}).get("first_name", "unknown")
        if chat_id != str(allowed):
            log(f"ignored message from non-allowed chat {chat_id}")
            continue
        if not text:
            log(f"skipped non-text message from chat {chat_id}")
            continue
        draft_one(chat_id, sender, text, instructions, out_dir, log)

    # advance the offset so processed updates are not fetched again
    if max_update is not None:
        pathlib.Path(offset_file).write_text(str(max_update + 1), encoding="utf-8")
    return 0


def draft_one(chat_id, sender, text, instructions, out_dir, log) -> None:
    prompt = (
        f"{instructions}\n\n"
        f"--- Telegram message from {sender} ---\n{text}\n--- end ---"
    )
    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--model", "sonnet"],
            capture_output=True, text=True, timeout=240,
        )
        body = result.stdout.strip() or "(the assistant returned an empty reply)"
    except Exception as exc:  # log and keep the poller alive
        body = f"(could not generate a reply: {exc})"
        log(f"claude failed for chat {chat_id}: {exc}")

    ts = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    draft = pathlib.Path(out_dir) / f"draft-{chat_id}-{ts}.md"
    draft.write_text(
        f"# Telegram draft reply\n\n"
        f"- chat id: {chat_id}\n"
        f"- from: {sender}\n"
        f"- received: {ts}\n\n"
        f"## Their message\n\n{text}\n\n"
        f"## Draft reply (NOT sent)\n\n{body}\n\n"
        f"---\n"
        f"Review and edit the draft reply above. To send it, run:\n"
        f"  bash modules/telegram/send.sh {chat_id} {draft.name}\n",
        encoding="utf-8",
    )
    log(f"drafted reply for chat {chat_id} -> {draft.name}")
    print(f"  draft written: reports/telegram/{draft.name}")


if __name__ == "__main__":
    sys.exit(main())
