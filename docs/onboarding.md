# Onboarding

Getting from a fresh clone to an assistant that is genuinely useful. The kit is
scaffolding: the value compounds as you personalize it, so do not try to
configure everything at once.

## Honest expectations on time

- **Setup itself is about two minutes.** `setup.sh` asks a handful of questions
  and creates your files.
- **A genuinely useful assistant is about the first hour**, working through the
  loop below.
- **The real payoff is the first month**, as memory fills in and you add an
  agent or two. The compounding is the point.

If you clone it and never personalize it, you will not get much from it. That is
by design: the structure is generic so your version does not have to be.

## Setup

```bash
git clone https://github.com/chacosoldier/compabob.git
cd compabob
./setup.sh
```

New to the terminal? The [README walkthrough](../README.md#full-walkthrough-no-terminal-experience-needed) covers installing everything from scratch.

`setup.sh` asks for your assistant's name, your name, role, and language, and
which **persona** best fits your work (consultant, engineer, sales, founder, or
generalist). The persona pre-fills `memory/topics/role-and-priorities.md` with
role-appropriate starter content so the assistant has something real to reason
about on day one. It then creates your personal `vault/`, `memory/`, and
`config/` from the shipped seeds.

At the end it offers to set up integrations. You can skip that and do it later.

Start the assistant:

```bash
claude
```

Optional, any time: `bash scripts/init.sh` confirms everything is wired. A
warning there means an optional item is not set up, not that something is broken.

## The first hour

Get one loop working end to end before you touch anything else. This is the
second-brain loop, the core value of the kit.

1. **Save something.** Paste in notes from a real meeting or document and ask:
   *"Save this to the vault as a meeting note."*
2. **Retrieve it.** In a later message or a new session ask:
   *"What do we know about [that topic or person]?"* The assistant finds the note.
3. **Use it.** Ask it to *"draft a follow-up email using that context."* You get
   a draft, not a sent message (see the safety note below).

Then try a skill: `/morning-brief` for a daily summary, or `/meeting-prep`
before your next meeting. If `/morning-brief` says it has little to show, that is
expected on day one, the system is working, it just has nothing stored yet.

### First-hour checklist

- [ ] `./setup.sh` run, `claude` starts and uses your assistant's name
- [ ] One real note saved to the vault
- [ ] That note retrieved and summarized back to you
- [ ] One draft produced from it
- [ ] `/morning-brief` tried once

## A note on the safety guards

The kit runs a few hooks that you will not normally notice. They block dangerous
shell commands, stop secrets being read into context, and hold any outbound
message as a draft until you approve it. If the assistant ever says it was
blocked from doing something, that is a guard doing its job, not a bug. See
[architecture.md](architecture.md) for the full list.

## The first week

Fill in memory as the assistant asks, or in one sitting:

- `memory/topics/role-and-priorities.md` — already pre-filled from your persona;
  refine it to your real situation.
- `memory/topics/working-style.md` — how you like to work and be challenged.
- `memory/topics/stakeholders.md` — who you work with, in what language.

The more honest these are, the less generic the assistant is. None of them block
anything: leave a field blank and the assistant will ask if it needs it.

Also in the first week:

- Delete the fictional example notes in `vault/` (every note tagged `#example`)
  once you have seen the structure, and replace them with your own.
- Try more skills: `/post-call`, `/handover`, `/log-decision`. The full list is
  in the [README](../README.md#skills).
- When the assistant gets something wrong, correct it and ask it to remember the
  correction. That is how it improves.

## When you outgrow the core

- **Add an agent** for a part of your work the core does not cover: run `/add-agent`.
- **Connect external tools** (browser automation, web search, Gmail, Calendar):
  run `bash scripts/install-integrations.sh`. See
  [modules/integrations/README.md](../modules/integrations/README.md).
- **Turn on scheduled briefs**: enable the [`proactive`](../modules/README.md) module.
- **Chat with the assistant from your phone**: enable the
  [`telegram`](../modules/telegram/README.md) module.
- **Sharpen memory retrieval**: build a search index over your notes with
  `/index-memory`. See [How to improve memory](how-to-improve-memory.md).

## Staying up to date

Run `./update.sh` whenever you want the latest version of the kit. Your `vault/`,
`memory/`, `config/`, `.env`, and `.mcp.json` are git-ignored and are never
touched by an update, so personalizing the kit and keeping it current are not in
tension. The [customization guide](customization-guide.md) explains the detail.
