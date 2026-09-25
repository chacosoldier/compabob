# Modules

The core kit runs with zero external services. Modules add capability when you want it. Nothing here is enabled by default. Each module has its own `README.md` with an enable step.

| Module | Status | What it adds |
|--------|--------|--------------|
| [`proactive/`](proactive/) | **Available** | Scheduled automation: a morning brief and a weekly review that run on a timer and leave their output in `reports/`. |
| [`telegram/`](telegram/) | **Available** | A Telegram bot. Inbound messages are drafted for your approval; it never auto-sends. Bot-token based, polling. |
| [`integrations/`](integrations/) | **Available** | An MCP integration picker: web + browser tools, Google Workspace, web search, and utilities. Run `scripts/install-integrations.sh`. |
| [`linkedin-outreach/`](linkedin-outreach/) | **Available** | Daily LinkedIn connection-invitation drafting from a queue you keep: it decides hook vs. no-note and writes a review card. You send it; it never sends. |
| [`crm-merge/`](crm-merge/) | **Available** | Folds Google Contacts + LinkedIn export + vault notes into one local CRM (SQLite + JSON + offline HTML browser), deduping people across sources. No creds. Run by hand or via the `/merge-contacts` skill. |
| [`lead-pipeline/`](lead-pipeline/) | **Available** | Builds a ranked outbound list: discover, clean, **dedup against your CRM**, enrich, score. One CSV per stage. Run by hand or via the `/build-list` skill. exa MCP optional for discovery. |
| [`memory-search/`](memory-search/) | **Available** | A search index over memory and the vault: ranked keyword search out of the box, semantic (search by meaning) with Ollama. Built by the `/index-memory` skill. |
| [`transcribe/`](transcribe/) | **Available, highly encouraged** | One-hotkey local call recording + transcription (mlx-whisper). Captures both sides, copies the text to your clipboard, and files a markdown transcript into `vault/raw/meetings/`. No cloud, no API key, audio never leaves your machine. |
| [`dictation/`](dictation/) | **Available** | A cleanup endpoint your dictation app (e.g. [Handy](https://github.com/cjpais/Handy)) posts to: it fixes punctuation/fillers and rewrites words it keeps getting wrong (your names, jargon) using a glossary that **grows itself** from recurring corrections. OpenAI-compatible upstream (Groq default, Ollama for fully local). |

## Not built (on purpose, for now)

- **Extra agents gallery** (designer, evaluator, sales coach, project manager). The eight core agents cover the common shape of knowledge work; role-specific agents are one `/add-agent` away, so a gallery waits for demand.
- **Team mode** (shared, department, and personal tiers). It needs a permission model, per-user isolation, and governance, each worth real hardening. Until then, each person runs their own copy; a shared vault can be a separate, jointly-owned folder.
- **WhatsApp.** No official API for personal accounts, and unofficial bridges risk an account ban. Use the Telegram module; if you already have a WhatsApp Business Cloud API number, adapt `telegram/` as the reference.

Vote or offer help on the [roadmap issue](https://github.com/chacosoldier/compabob/issues/12).

## How to enable a module

1. Read the module's `README.md`.
2. Run its enable step (most have an `install.sh` or a short manual step).
3. Set its flag to `true` in `config/user.config.yaml` so `/system-audit` knows to check it.

## How to add your own module

A module is just a directory under `modules/` with a `README.md` and whatever scripts or agent files it needs. Keep it self-contained and opt-in. If it adds an agent, the agent file is copied into `.claude/agents/`; if it adds automation, it ships its own runner and install step.
