# Architecture

How the kit is put together, and the principles behind it. Read this once to understand why things are where they are; you do not need it to use the kit.

## The shape

```
CONSTITUTION.md      The behavior contract. Loaded every session via CLAUDE.md.
.claude/agents/      Specialized agents. The main session routes work to them.
.claude/skills/      Slash-command workflows. Repeatable procedures.
.claude/output-styles/  How responses are shaped (answer-first).
hooks/               Deterministic guards and lifecycle scripts.
memory/              Durable facts, carried across sessions.
vault/               The Obsidian knowledge base.
modules/             Opt-in extensions.
```

## Your data vs the kit

A hard line runs through the directory tree, and it is what makes the kit safe to update:

- **The kit** (version-controlled, updates from upstream): `CONSTITUTION.md`, `CLAUDE.md`, `.claude/agents/`, `.claude/skills/`, `.claude/output-styles/`, `hooks/`, `modules/`, `scripts/`, `docs/`, and the `*.example` seeds.
- **Your data** (git-ignored, never touched by an update): `vault/`, `memory/`, `config/user.config.yaml`, `.mcp.json`, `.env`, and `.claude/settings.local.json`. `setup.sh` creates these from the `*.example` seeds on first run.

Kit files contain no personal placeholders. `setup.sh` personalizes only the seed copies. `update.sh` pulls new kit versions and physically cannot reach your data, because your data is not in git. This separation is deliberate: it lets the kit improve over time without ever putting a user's knowledge base at risk.

## Three kinds of thing

The kit separates three concerns. Keeping them distinct is what keeps it coherent as it grows.

- **The constitution and skills** define *what to do*: instructions, procedures, conventions.
- **The agents** do the *intelligent coordination*: they read context, make judgment calls, decide.
- **The hooks** are *deterministic execution*: they always do the same thing, with no judgment. A guard either fires or it does not.

When you add something, ask which of the three it is. A judgment call belongs in an agent. A fixed rule belongs in a hook. A repeatable procedure belongs in a skill.

## Agent routing

There is no manual agent picker. The main session reads each agent's `description` and routes the request to the best match. This is why descriptions matter more than names: the description is the routing signal.

- A good description says *when* to use the agent and what it is *not* for.
- If routing goes wrong, the fix is almost always a sharper description, not new code.
- Agents are scoped: each gets only the tools its job needs. An agent with every tool routes unpredictably.

The main session orchestrates multi-step work: it calls agents, passes their output between them, and synthesizes. Agents produce data; the main session produces the answer. Advice-only agents (`strategy-advisor`, `principal-engineer`, `first-principles`) never write or send; when their output should persist, it goes to `second-brain`.

## The hook lifecycle

Hooks run at fixed points in a session and cannot be talked out of their job by a clever prompt. The kit wires these:

- **SessionStart** → `hook-session-start.sh` injects the memory index, a handover note under a week old, and one-line notices: setup still pending or unfinished (so the assistant offers `/setup`), a one-time first-hour nudge after setup, kit updates since the last session, kit files edited locally, today's scheduled output, recent scheduled-run failures, an oversized `MEMORY.md`, missing config keys.
- **UserPromptSubmit** → `hook-inject-now.sh` injects the current time, and tells scheduled runs that nobody is watching.
- **PreToolUse(Bash)** → `hook-block-dangerous.py` and `hook-comms-guard.py` block destructive commands and un-approved sends.
- **PreToolUse(Read)** → `hook-protect-secrets.py` blocks reading credential files.
- **PreToolUse(ExitPlanMode)** → `hook-plan-premortem.py` holds a high-stakes plan (irreversible, wide blast radius, or weeks of work) until it has a pre-mortem from `strategy-advisor`. The `/design-precheck` skill writes that section properly.
- **PostToolUse** → `prompt-injection-defender/` flags injected instructions in tool output, MCP tools included, and skips the kit's own files.
- **Stop** → `hook-style-gate.py` checks each reply for em dashes and paragraph walls. It reads the reply from the hook's input (`last_assistant_message`), because the transcript can lag one reply behind. `style_gate:` in `config/user.config.yaml` sets it to `warn` (default), `block`, or `off`.

Rules that can be checked by a script belong in a hook, not in more prose: a hook runs every time, while a sentence in the constitution competes with everything else in context.

Hooks fail open: a hook that errors never breaks the session. The guards are defense-in-depth, not the only line of defense.

## Permissions

`.claude/settings.json` decides what asks first. Reading is free. Writing inside `vault/`, `memory/` and `.tmp/` (the user's own notes, the assistant's memory, the handover note) and to `config/user.config.yaml` is allowed without a prompt, so the core loop of saving and finding notes runs smoothly. Every shell command asks, in every permission mode, because `ask` rules win over `allow`. Editing a kit file asks in Manual mode; in Auto mode Claude Code's classifier decides. The guard hooks run regardless of these rules: a send or a secret read is blocked even if a prompt was approved.

## Memory

`memory/MEMORY.md` is a short index, loaded every session. Durable facts live one-per-file in `memory/topics/`, linked from the index and read only when relevant. This keeps the always-loaded context small while keeping detail available. The bar for writing a memory is deliberately high (see the constitution): memory is for what the files and git history do not already capture.

## Principles worth keeping

If you extend the kit, these are what keep it sound:

- **Description-driven routing.** Selection is by description, not name. Write descriptions as "use for X, Y, Z".
- **Scoped tools.** Four to six tools per agent. Less is sharper.
- **Strict schemas for deterministic work.** Where a workflow must produce structured output, validate with a schema, not a hope.
- **Draft, never auto-send.** Anything leaving the machine is shown to the human first. The `comms-guard` hook backs this up.
- **Answer first.** Every response leads with the conclusion. See `.claude/output-styles/direct.md`.
- **Honest data labels.** `[ACTUAL]`, `[PROJECTED]`, `[ASSUMPTION]`, `[DATA GAP]`. Never dress an estimate as a measurement.
- **Fail open on guards, fail loud on data.** A broken hook should not break the session; a missing number should never become a guessed one.

## What the kit leaves out on purpose

The setup this kit is distilled from has more machinery. These stay out because they need daily tuning, depend on one person's data, or would be one more thing a new user has to understand:

- **An improvement queue that builds and merges changes overnight.** Powerful, but it needs a maintainer reading its output every morning.
- **Scored approval prompts** (a risk number on every go or no-go question). The weights only mean something once calibrated on one person's past decisions.
- **Telemetry hooks** that log every tool call and skill use. Useful for tuning a fleet of skills; noise for one person starting out.
- **Heavier guards** (a gate that blocks replies asking questions the assistant could answer itself, a combined "untrusted input plus private data plus a send" gate for unattended runs). The kit's guards cover the common cases; add these when your setup runs unattended a lot.
- **Life-domain agents** (health, money, coaching). The kit is for work; `/add-agent` builds one when you want it.

