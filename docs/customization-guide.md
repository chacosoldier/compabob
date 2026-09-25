# Customization Guide

The kit is built to be changed. This is how. Nothing here is sacred; if a default does not fit your work, change it.

## Your data vs the kit

Two kinds of thing live side by side, and the difference is what makes updates safe:

- **Your data**: `vault/`, `memory/`, and `config/user.config.yaml` (plus `.mcp.json`, `.env`, and `.claude/settings.local.json`). `setup.sh` creates these from the shipped `*.example` seeds. They are git-ignored: not part of the kit's version control, so a kit update cannot touch them. Your knowledge base, your assistant's memory, and your settings all live here. Customize them however you like.
- **The kit** — `CONSTITUTION.md`, `.claude/agents/`, `.claude/skills/`, `hooks/`, `modules/`, the scripts, the docs. Version-controlled, and updated from upstream when you run `./update.sh`.

`setup.sh` personalizes only your data (it fills your name, role, and language into the seed copies). It never edits a kit file. That is what keeps the kit cleanly updatable.

## Updating

Run `./update.sh` to pull the latest kit. It sets aside any kit edits you have made, pulls, and re-applies them. Your `vault/`, `memory/`, and `config/user.config.yaml` are git-ignored, so they are never at risk, whatever happens. If the new kit adds a config key (a new module flag, say), `update.sh` adds it to your config with its default and leaves every value you set alone.

- **Adding** your own agents, skills, or hooks never conflicts: upstream does not have those files.
- **Editing a kit file** (an agent, the constitution) can produce a merge conflict on that one file when you update. That is normal git: `update.sh` names the file, you resolve it, done. Your data is untouched throughout.

## Placeholders

The shipped seeds (`vault.example/`, `memory.example/`, `config/user.config.yaml.template`) contain `{{...}}` tokens. `setup.sh` fills them in *your copies only*. Kit files contain no placeholders, which is why they update cleanly.

## The constitution

`CONSTITUTION.md` is the behavior contract loaded every session. Edit it to match how you actually work: the communication style, the routing rules, the safety rules, the quality standards. This is the highest-leverage file in the kit. If the assistant consistently does something you do not want, the fix usually belongs here.

`CLAUDE.md` is a thin loader that imports the constitution and points at memory. You rarely need to touch it.

## Agents

Each file in `.claude/agents/` is one agent.

**To add one:** run the `/add-agent` skill, or copy `.claude/agents/_agent-template.md.template`. Then add its routing line to `CONSTITUTION.md` (Agent Architecture & Routing). `_orchestrator-reference.md` is not a registry: it describes how the main session coordinates agents, not which ones exist.

**To edit one:** just edit its file. The `description` is the most important line: it decides what routes to the agent. Write it as "use for X, Y, Z" and name what it is *not* for.

**To remove one:** delete its file and its routing rows. Removing an agent you do not need keeps routing sharp.

Rules of thumb: one agent, one job. Keep the tool list to four to six. Advice-only agents get read tools only.

**A worked example.** Suppose `analyst` is too finance-flavoured for your work and you want it on product metrics. You would not write a new agent, you would edit two things in `.claude/agents/analyst.md`:

- The `description`, which is the routing signal. Before: "pipeline and revenue figures, forecasts, variance investigation." After: "product metrics: activation, retention, funnel conversion, feature adoption." Product questions now route here.
- The body's capability list, so what it does matches. Swap the revenue and pipeline bullets for activation, cohort retention, and funnel analysis.

That is the whole pattern: change the description to change what routes in, change the body to change what it does once there. No code, no new file.

## Skills

Each directory in `.claude/skills/` is one slash command, defined by its `SKILL.md`. To add a workflow, copy an existing skill directory, rename it, and rewrite `SKILL.md`. The frontmatter `description` is what makes `/your-skill` discoverable.

## Hooks

`hooks/` holds the guards and lifecycle scripts. They are wired in `.claude/settings.json` under the `hooks` key.

- **To add a hook:** write the script, then add an entry under the right event in `settings.json`. Hooks should fail open: an error must never break the session.
- **To disable a hook:** remove its entry from `settings.json` (leave the script in place, or delete it).
- **Optional hooks worth considering:** a pre-mortem reminder on plan-mode exit; a redundant-read deduplicator; a Python linter on file writes. The core ships lean on purpose; add what your work needs.

Context-injection hooks (SessionStart, UserPromptSubmit) write to stdout. Guard hooks (PreToolUse) exit `2` to block with a reason. See the existing hooks for the pattern.

## Adding a tool or integration

The core agents work from files. To give one a live data source, the pattern is a command-line client the agent calls via `Bash`:

1. Write a small CLI client (any language) that does one thing: query a CRM, read an inbox, fetch calendar events. Read credentials from a git-ignored `.env`, never from code.
2. Tell the relevant agent about it: add a short "Tool" section to the agent file naming the command and its usage.
3. Keep the contract narrow. One script, clear inputs and outputs, predictable behavior.

This is also how an MCP server would slot in: the agent calls it, the agent's description and instructions tell it when. Keep tool descriptions specific, schemas strict, and the tool count per agent low.

For ready-made MCP servers, the kit ships an installer: `bash scripts/install-integrations.sh` wires browser automation, web search, and utility servers into `.mcp.json` for you. Gmail and Calendar come from Claude's own connectors, see the module README. See [`modules/integrations/README.md`](../modules/integrations/README.md). Use the installer for those; use the CLI-client pattern above when you need a bespoke connector.

## Personas

`setup.sh` asks which persona fits your work and uses it to pre-fill `memory/topics/role-and-priorities.md` with role-appropriate starter content. Presets live in `config/personas/` as kit files, so they update cleanly with the rest of the kit.

A persona only seeds that one file and records your choice in `config/user.config.yaml`. It never adds, removes, or changes an agent: every agent stays available whichever persona you pick. To add your own, copy a file in `config/personas/`, rewrite the body, and add its id to the persona prompt in `setup.sh`. See [`config/personas/README.md`](../config/personas/README.md).

## Modules

`modules/` holds opt-in extensions. To enable one, read its `README.md`, run its enable step, and set its flag in `config/user.config.yaml`. To build your own, add a self-contained directory under `modules/` with its own `README.md` and enable step.

## A good change

The best customization is subtractive as often as additive. If an agent, skill, or hook does not earn its place in your work, remove it. A lean kit that fits you beats a full one that does not.
