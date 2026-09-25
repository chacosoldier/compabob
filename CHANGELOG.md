# Changelog

All notable changes to Compabob are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versioning follows
[SemVer](https://semver.org/).

## [Unreleased]

## [1.2.0] - 2026-09-25

Maintenance release: the modules and skills that shipped since 1.1.1, fixes
for bugs found in a full audit, the Claude Code changes since June, and a
smaller kit. Safe to pull with `./update.sh`: your `vault/`, `memory/`,
`config/user.config.yaml`, `.mcp.json`, and `.env` are untouched, and any new
config flags are added for you.

**If you edited kit files**, `update.sh` may ask you to merge the ones this
release also changed: every agent in `.claude/agents/`, `.claude/settings.json`,
`CLAUDE.md`, the `add-agent`, `mcp-debug`, and `memory-debt` skills, `setup.sh`,
`update.sh`, everything in `scripts/` and `docs/`, and the proactive, telegram,
transcribe, dictation, and integrations modules. `git diff --stat v1.1.1 v1.2.0`
lists them all. Personas and the other skills are unchanged.

### Added

- **`dictation` module**: a cleanup endpoint your dictation app (e.g. Handy)
  posts to. It fixes punctuation and fillers, and rewrites words it keeps
  getting wrong using a glossary that grows itself from recurring corrections.
  OpenAI-compatible upstream (Groq by default, Ollama for fully local).
- **`/weekly-review` skill**: end-of-week review of what got done, what
  slipped, decisions, commitments, and next week's top three (#16).
- **`researcher` persona preset** for academia and R&D (#19).
- **Spanish README intro** at `docs/i18n/README.es.md` (#23).
- **Linux and WSL troubleshooting** section in the README (#14).
- **`scripts/migrate-config.sh`**: adds config keys a kit update introduces,
  inside the right block, with a `.bak`; never changes a value you set.
  `update.sh` runs it, and `scripts/init.sh` warns when keys are missing.
- **`scripts/lib/common.sh`**: shared output helpers and `set_config_flag`.
- **`transcribe` module (highly encouraged)** — one-hotkey local call recording +
  transcription. A toggle script drives `ffmpeg` to capture audio and
  `mlx-whisper` to transcribe it on-device: first run records, second run stops,
  transcribes, copies the text to your clipboard, and files a markdown transcript
  (with frontmatter) into `vault/raw/meetings/` for your notes pipeline. Defaults
  to an aggregate device so both sides of a call are captured. No cloud service,
  no API key, audio never leaves the machine. Device names are overridable via
  `TRANSCRIBE_DEVICE_*` env vars (`record.py devices` lists yours); optional
  Hammerspoon/Raycast hotkey binding documented. Opt-in via `transcribe: true`.
- **`crm-merge` module + `/merge-contacts` skill** — folds Google Contacts (Takeout
  vCards), a LinkedIn data export (Connections + messages), and your vault
  `People/` notes into one local source of truth: a SQLite DB, a JSON file, and a
  self-contained offline HTML browser. Identity resolution uses union-find on
  three keys (verified email, LinkedIn slug, normalized name) with a common-name
  collision guard, so duplicates collapse without over-merging generic names.
  Relationship strength (LinkedIn message count) ranks records. No credentials,
  all stdlib, idempotent. Outputs are git-ignored.
- **`lead-pipeline` module + `/build-list` skill** — turns a raw candidate list
  into a ranked, CRM-aware outbound list through staged steps that write one CSV
  per stage (discover → clean → **dedup-against-CRM** → enrich → score → top-N).
  The deterministic stages (`clean`, `dedup`, `score`) run as a stdlib script;
  discovery and enrichment run as assistant steps over optional MCP servers (exa
  free tier minimum; an enrichment provider optional). Dedup tags each lead
  `proceed` (cold), `warm` (you already know someone at the account, route the
  intro), or `skip` (already a known contact), so you never enrich or cold-email
  a relationship. ICP scoring is a tunable JSON rubric (`icp.example.json`).
- **`/chart-tufte` skill** — self-grade rubric for any quantitative chart,
  grounded in Edward Tufte's *Visual Display of Quantitative Information*.
  Nine criteria, ten genres, seven remedies, plus a 114-line
  `references/vdqi-catalogue.md` with named failures (NYT MPG 14.8, TIME
  barrel 59.4) and named exemplars (Minard, Marey, Snow, Playfair). Designed
  to run as the final pass inside `/visual-explainer` whenever the output is
  a chart.
- **`/mcp-debug` skill** — health-check, trace, or audit your configured MCP
  servers when tools fail silently. Three modes: `status` (per-server
  reachability), `trace <tool>` (likely failure mode for one tool), `audit`
  (recommendations for unused / high-error / duplicate servers). Reads
  `~/.claude.json` and `./.mcp.json`; redacts secrets in every output.
- **`/memory-debt` skill** — review and apply memory updates that earlier
  sessions proposed but never wrote. Scans `vault/Daily/`, `vault/Reflections/`,
  and `vault/Journal/` for `- [ ]` proposals from `/reflect`, classifies each
  as PENDING / STALE / OBSOLETE / APPLIED, then in `apply` mode walks through
  approvals one by one. Closes the loop between `/reflect` (proposes) and
  `memory/`.

### Changed

- **Agents follow your model.** Every agent uses `model: inherit` instead of
  `sonnet`, so switching models in Claude Code switches the agents too. On a
  Pro plan, see the README for pinning them back to Sonnet. Scheduled modules
  still run on Sonnet.
- **Install Claude Code with the native installer**
  (`curl -fsSL https://claude.ai/install.sh | bash`); npm stays documented as a
  fallback (Node 22+). Docs links point at code.claude.com.
- **README model section rewritten** (closes #9): Claude Code's default is now
  Opus 5.5 on every paid plan; how to change it per session, per project, or
  globally.
- **Integrations**: pins bumped (`@playwright/mcp` 0.0.82, `scrapling-fetch-mcp`
  0.2.4, `mcp-server-time` 2026.8.18, `exa-mcp-server` 3.4.1, which needs
  Node 20+). Gmail and Calendar now point at Claude's own connectors.
- **SessionStart hook** also runs after `/clear` and in forked sessions.
- **Config template**: flags for `crm_merge` and `lead_pipeline`; persona list
  shows all six.
- **`transcribe` and `dictation`** install their Python dependency into a
  module venv (Homebrew Python refuses a global `pip install`); `record.py`
  switches to its venv on its own, so hotkeys keep working.
- **`update.sh`** says what to do on a local-only branch or detached HEAD
  instead of blaming the network.
- **`scripts/init.sh`** checks for Python 3.10+ and counts only real agents.

### Removed

- **Tool-scope guard hook** (never released): it was not wired into
  `settings.json`, needed `jq`, and matched no context the kit sets.
- **Stub modules** `extra-agents`, `team`, and `whatsapp`, which were README
  files only. Their reasoning now lives in the "Not built" section of
  `modules/README.md`; the roadmap is issue #12.
- **`mcp-server-fetch`** from the integrations catalog (Claude Code's built-in
  WebFetch covers it) and the empty `google` category.
- **Dead config keys**: `preferences.timezone`, `extra_agents`, `team`. Existing
  configs keep them; nothing reads them.

### Fixed

- **Weekly review ran on Saturday on macOS**: launchd counts Sunday as 0, so
  `Weekday 6` was Saturday. Now Friday.
- **Scheduled runs could not find `claude`** under launchd's minimal PATH
  (`proactive`, `telegram`).
- **The agent template registered as a real agent**. It is now
  `.claude/agents/_agent-template.md.template`.
- **`install-integrations.sh` left an empty `.mcp.json`** on runs that added
  nothing.
- **Docs claimed `config/` is git-ignored**; only `config/user.config.yaml` is.
- **`/add-agent` and the customization guide** pointed at
  `_orchestrator-reference.md` as an agent registry; routing lives in
  `CONSTITUTION.md`.
- **Telegram README** said the hook "blocks until you approve"; the hook always
  blocks, and you send with `send.sh` yourself.

## [1.1.1] — 2026-05-24

Bug-fix release from the same-day QA pass. 5 personas × 10 input edge
cases × idempotency × `update.sh` × integrations × `init.sh` × a
pristine Docker Ubuntu run × a headless `claude -p` smoke. 11 findings,
all fixed in this release. Full QA report:
[`docs/qa-findings-2026-05-24.md`](docs/qa-findings-2026-05-24.md).

### Fixed

- **`setup.sh` re-run silently overwrites `memory/topics/role-and-priorities.md`**
  (P1). The "untouched template" guard treated `[the most important thing]`
  as a marker, but that string also lived in `config/personas/generalist.md` —
  so users who started with `generalist`, edited the file, and re-ran
  setup lost their edits. Marker tightened to `[fill in]`, which only
  appears in the shipped template. Spawned
  [`feedback-protective-marker-needs-uniqueness`](https://github.com/chacosoldier/compabob)
  as a memory rule for future template work.
- **`whoami` default for "Your name"** leaked the OS account name into
  `memory/MEMORY.md` if the user hit Enter (e.g. `root` inside Docker).
  Default removed; setup re-prompts until a name is given.
- **Persona seeding ran before placeholder replacement**, so personas
  shipped with `{{USER_NAME}}` still on disk. Order flipped: persona
  first, then placeholders.
- **Piped-mode setup** (`printf ... | ./setup.sh`) swallowed the final
  newline and the integrations prompt collided with EOF. Added an
  explicit newline guard.
- **`install-integrations.sh` printed "Done." on no-op runs** (unknown
  category, empty selection). Now exits non-zero with a clear "nothing
  installed" message.
- **`.mcp.json` was created eagerly** even when no integrations were
  selected, leaving an empty file. Creation deferred until at least one
  integration writes to it.
- **`init.sh` warned instead of failing** when integrations were
  enabled but `.mcp.json` was missing. Now fails loud — a missing MCP
  config with integrations on is a setup bug, not a soft warning.

### Changed

- **`update.sh` output**: now shows the list of pulled commits and a
  clearer "your data lives here" banner, so users see exactly what
  changed and what was preserved.
- **README** — clarified which paths are "yours" (`vault/`, `memory/`,
  `config/user.config.yaml`, `.mcp.json`, `.env`) vs. tracked kit
  content; corrected the walkthrough prompt count; added a YAML-escape
  note for names containing apostrophes.

## [1.1.0] — 2026-05-24

Post-launch hygiene: visible maintenance signals + bit-rot CI.

### Added

- `.github/workflows/smoke.yml` — weekly fresh-clone CI smoke test
  (push, PR, Monday 06:00 UTC, manual). Runs `bash -n` on every shell
  script, executes `setup.sh` non-interactively, then `init.sh`, then
  validates the integrations catalog JSON.
- `.github/FUNDING.yml` — surfaces a Sponsor button (LinkedIn, no
  Sponsors listing); a maintenance signal more than a funding ask.
- README badges row: CI, License, Stars, Last commit.
- README section "How this differs from the other Claude Code things
  you have seen" — short comparison vs. raw Claude Code, awesome lists,
  multi-agent dev-team frameworks, and DIY.
- `CHANGELOG.md` itself (this file).
- Community seeding: 5 `good first issue` tickets (#7–#11), a pinned
  roadmap issue (#12), and a Show-and-tell Discussion thread (#13).

### Fixed

- README modules table claimed `memory-search` was Roadmap; the module
  ships as available. Row rewritten to match `modules/memory-search/README.md`.

## [1.0.0] — 2026-05-20

Initial public release at [github.com/chacosoldier/compabob](https://github.com/chacosoldier/compabob).

### Core

- `CONSTITUTION.md` — the rules every session loads.
- `CLAUDE.md` — project entry point.
- `.claude/agents/` — 8 specialized agents: `daily-copilot`,
  `second-brain`, `analyst`, `crm-relationships`, `comms-meetings`,
  `strategy-advisor`, `principal-engineer`, `first-principles`.
- `.claude/skills/` — slash-command workflows: `/morning-brief`,
  `/meeting-prep`, `/post-call`, `/handover`, `/log-decision`, `/tasks`,
  `/reflect`, `/index-memory`, `/add-agent`, `/system-audit`,
  `/visual-explainer`, `/document-export`.
- `.claude/output-styles/` — the answer-first response style.
- `hooks/` — safety guards (prompt-injection defender, etc.) and
  lifecycle automation.

### User-data layer

- `vault.example/`, `memory.example/`, `config/user.config.yaml.template`,
  `.claude/settings.local.json.template` — seeds that `setup.sh` copies
  into git-ignored `vault/`, `memory/`, `config/` on first run. Updates
  via `./update.sh` cannot touch user data.
- Five persona presets: `generalist`, `consultant`, `engineer`, `sales`,
  `founder` (under `config/personas/`).

### Modules

- `proactive` (available) — scheduled morning brief + weekly review.
- `telegram` (available) — Telegram bot that drafts inbound messages
  for approval; never auto-sends.
- `integrations` (available) — MCP servers via a pinned catalog at
  `scripts/integrations-catalog.json`.
- `linkedin-outreach` (available, added day 1 via PR #1) — one
  invitation card per day from a queue, manual send.
- `memory-search` (available) — keyword (FTS5) index by default,
  semantic via Ollama embeddings if installed.
- `extra-agents` (planned), `team` (deferred), `whatsapp` (won't build).

### Tooling

- `setup.sh` — interactive first-run, idempotent, never overwrites.
- `update.sh` — pulls latest, preserves user data.
- `scripts/init.sh` — per-session health check.
- `scripts/install-integrations.sh` — MCP picker.

### Day-1 PRs merged

- #1 `linkedin-outreach` module.
- #2 `/document-export` skill (PDF, Excel, Word).
- #3 Community health files + social preview image.

### Docs

- `docs/architecture.md`, `docs/onboarding.md`, `docs/customization-guide.md`,
  `docs/how-to-improve-memory.md`.

[Unreleased]: https://github.com/chacosoldier/compabob/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/chacosoldier/compabob/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/chacosoldier/compabob/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/chacosoldier/compabob/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/chacosoldier/compabob/releases/tag/v1.0.0
