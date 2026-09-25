# Module: Telegram

Turn a Telegram bot into an inbound channel for your assistant. When someone
messages the bot, the assistant drafts a reply in your voice and saves it for you
to review. **It never sends anything on its own.** You read the draft and, only
if you want it sent, send it yourself. This is the same draft-first contract the
kit applies to email.

## How it works

- `poll.sh` long-polls Telegram for new messages. For each text message from your
  allowed chat, it asks the assistant (`claude -p`) for a reply and writes that
  reply as a draft in `reports/telegram/draft-<chat>-<timestamp>.md`.
- `send.sh` is the only thing that sends. It is never called automatically, and
  the `comms-guard` hook intercepts it so a send always needs your explicit "yes".
- Only messages from `TELEGRAM_ALLOWED_CHAT_ID` are answered. A stranger who finds
  your bot is ignored.

## Setup

1. **Create a bot.** Message [@BotFather](https://t.me/BotFather) on Telegram, send
   `/newbot`, follow the prompts. It gives you a bot token.
2. **Find your chat id.** Message [@userinfobot](https://t.me/userinfobot); it
   replies with your numeric id.
3. **Fill in `.env`.** From the kit root:
   ```bash
   cp .env.example .env   # if you have not already
   ```
   Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ALLOWED_CHAT_ID` in `.env`. That file is
   git-ignored and never leaves your machine.

## Run it (the default way)

Run the poller by hand whenever you want the bot live:

```bash
bash modules/telegram/poll.sh
```

It runs until you stop it with Ctrl-C. Message your bot from Telegram; a draft
appears in `reports/telegram/`. This manual mode is the supported, low-maintenance
path: nothing runs in the background, nothing to break after an OS update.

## Run it unattended (optional)

If you want the bot always on, `install.sh` generates a background service
(a launchd agent on macOS, a systemd user unit on Linux):

```bash
bash modules/telegram/install.sh
```

It only generates the file and prints the command to activate it. A background
daemon is the part of any kit most likely to need attention later, so this is
opt-in on purpose. After activating, set `telegram: true` in
`config/user.config.yaml`.

## Sending a reply

`poll.sh` only ever drafts. To send a draft after reviewing (and editing) it:

```bash
bash modules/telegram/send.sh <chat_id> draft-<chat>-<timestamp>.md
```

The assistant cannot send for you: the `comms-guard` hook blocks any `send.sh`
call made from a session. Sending is always the command above, run by you.

## Cost note

Each inbound message triggers one headless `claude -p` call (pinned to
`--model sonnet` to keep it modest). It runs on your Claude subscription or API
credits like any other session.

## Disable it

Stop the poller (Ctrl-C, or the deactivation command `install.sh` printed),
and set `telegram: false` in `config/user.config.yaml`.
