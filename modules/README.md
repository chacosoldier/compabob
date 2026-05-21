# Modules

The core kit runs with zero external services. Modules add capability when you want it. Nothing here is enabled by default. Each module has its own `README.md` with an enable step.

| Module | Status | What it adds |
|--------|--------|--------------|
| [`proactive/`](proactive/) | **Available** | Scheduled automation: a morning brief and a weekly review that run on a timer and leave their output in `reports/`. |
| [`telegram/`](telegram/) | **Available** | A Telegram bot. Inbound messages are drafted for your approval; it never auto-sends. Bot-token based, polling. |
| [`integrations/`](integrations/) | **Available** | An MCP integration picker: web + browser tools, Google Workspace, web search, and utilities. Run `scripts/install-integrations.sh`. |
| [`linkedin-outreach/`](linkedin-outreach/) | **Available** | Daily LinkedIn connection-invitation drafting from a queue you keep: it decides hook vs. no-note and writes a review card. You send it; it never sends. |
| [`memory-search/`](memory-search/) | **Available** | A search index over memory and the vault: ranked keyword search out of the box, semantic (search by meaning) with Ollama. Built by the `/index-memory` skill. |
| [`extra-agents/`](extra-agents/) | Roadmap | A gallery of additional agents (designer, evaluator, sales coach, project manager) to copy into `.claude/agents/`. |
| [`whatsapp/`](whatsapp/) | Roadmap | A WhatsApp channel. Not built: unofficial bridges risk an account ban. Use the Telegram module instead. |
| [`team/`](team/) | Deferred | Multi-user team mode: shared, department, and personal tiers. See its README for why it is not in this release. |

## How to enable a module

1. Read the module's `README.md`.
2. Run its enable step (most have an `install.sh` or a short manual step).
3. Set its flag to `true` in `config/user.config.yaml` so `/system-audit` knows to check it.

## How to add your own module

A module is just a directory under `modules/` with a `README.md` and whatever scripts or agent files it needs. Keep it self-contained and opt-in. If it adds an agent, the agent file is copied into `.claude/agents/`; if it adds automation, it ships its own runner and install step.
