# Module: LinkedIn outreach

Drafts your LinkedIn connection invitations, one a day, from a queue you keep.
For each person it decides whether there is a genuine reason to attach a note or
whether a clean no-note invite is the better call, writes the note when there
is one, and hands you a review card. **It never sends anything.** You read the
card, send the invite yourself on LinkedIn, and record what you did.

It is the same draft-first contract the kit applies to email and Telegram: the
assistant does the judgment and the writing, you keep the send.

## The idea: a note only when there is a real hook

Most connection requests are better off with no note at all. A generic note
("connecting with other people in growth...") does not improve acceptance and
can faintly hurt it, because anyone who knows LinkedIn reads a note as the start
of a pitch. A note earns its place only when there is a **genuine hook**:
something specific and true about that person (you met somewhere, a mutual
connection, a shared past employer, a rare title, a real recent move).

So the module is hook-gated. If your context note on a person carries a real
hook, it drafts one honest line. If it does not, it tells you to send a bare
invite. That decision, made well and consistently, is most of the value here.

## How it works

- You keep a queue at `vault/LinkedIn Outreach Queue.md`: one person per line,
  topmost first, each with a short context note.
- `draft.sh` takes the person at the top of the queue, decides hook or no-hook,
  drafts the note if warranted, and writes a review card to
  `reports/linkedin-outreach/cards/`.
- You open the card, send the invite on LinkedIn yourself, then run `record.sh`
  to log the outcome. That moves the person out of the queue and frees the slot
  for the next draft.

Only one card is open at a time, and there is a daily cap, so the queue drains
at a deliberate, human pace.

## Why you send it yourself

LinkedIn's terms restrict automated activity, and tools that send invites for
you work by driving a logged-in session, which puts your account at risk. This
module does not do that. It does the part that actually takes thought, deciding
who to reach and what to write, and leaves the click to you. If you already run
a LinkedIn automation MCP server and accept that trade-off, see "Wiring an
automated send" at the end.

## Setup

No credentials, no API keys.

1. The first time you run `draft.sh`, it creates the queue file for you at
   `vault/LinkedIn Outreach Queue.md` and stops.
2. Open that file and add people to the `## Queue` section. Line format:
   ```
   - [ ] https://www.linkedin.com/in/their-slug | who they are, and any genuine hook
   ```
   The context note after the `|` is the important part. Write a real, specific
   hook and you get a real note. Write something generic, or nothing, and you
   get a clean no-note invite, which is the right call when there is no hook.
   You can add people by hand, or ask your assistant in a session to suggest
   connections from your notes and meetings.
3. Set `linkedin_outreach: true` in `config/user.config.yaml`.

## Use it

Draft a card whenever you want one:

```bash
bash modules/linkedin-outreach/draft.sh
```

It prints where the card landed. Open it: it shows the person, your context
note, the hook-or-no-hook decision, and the drafted note (or a note-free
recommendation). To change the wording, just edit the card file.

### Send it, then record it

The card has the profile link and the exact note text. On LinkedIn, open the
profile, click **Connect**, and either "Add a note" and paste the text, or send
with no note for a bare invite.

Then record what you did, so the queue stays in sync:

```bash
bash modules/linkedin-outreach/record.sh <card-file> sent
```

Use `rejected` if you looked at the card and decided not to reach out, or
`skipped` if the profile was wrong or you are already connected. Recording
archives the card and frees the slot for the next `draft.sh`.

## Run it on a schedule (optional)

To draft a card automatically every weekday morning:

```bash
bash modules/linkedin-outreach/install.sh
```

It generates a schedule file (a launchd plist on macOS, a cron line on Linux)
and prints the one command to activate it. It does not touch your scheduler on
its own. The scheduled run skips weekends; a manual `draft.sh` never does.

A scheduled run only ever drafts a card. Nothing is sent, so you still review
and send every invite by hand.

## The daily cap

The module drafts, and lets you send, at most a few invites a day (default 5).
LinkedIn enforces its own weekly invite limits, and a steady trickle reads far
better than a burst. To change the cap, set `LINKEDIN_OUTREACH_DAILY_CAP` in
`.env`.

## Cost note

Each `draft.sh` run is one headless `claude -p` call, pinned to `--model sonnet`
to keep it modest. It runs on your Claude subscription or API credits like any
other session.

## Pairs well with

The `crm-relationships` agent tracks who you know and who you have reached out
to. Ask it to review your network for people worth queuing.

## Disable it

If you scheduled it, remove the schedule (the deactivation command is printed by
`install.sh`). Set `linkedin_outreach: false` in `config/user.config.yaml`. Your
queue file and any archived cards stay where they are.

## Wiring an automated send (advanced, optional)

If you run a LinkedIn MCP server that can send a connection request, and you
accept the terms-of-service trade-off, you can close the loop yourself: have
your assistant call that MCP tool with the `linkedin_url` and note text from a
card, then run `record.sh <card> sent`. This module deliberately does not ship
or depend on such a server.
