# Changelog

All notable changes to Compabob are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versioning follows
[SemVer](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/chacosoldier/compabob/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/chacosoldier/compabob/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/chacosoldier/compabob/releases/tag/v1.0.0
