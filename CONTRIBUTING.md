# Contributing & Extending

This kit is built to be changed. "Contributing" here means two things: making it yours, and (optionally) sending improvements upstream.

## Making it yours

The kit assumes you will edit it. Nothing here is sacred.

- **Agents**: edit any file in `.claude/agents/`. Add a new one with the `/add-agent` skill, or copy `.claude/agents/_agent-template.md`.
- **Skills**: each directory in `.claude/skills/` is one slash command. Copy an existing one to make a new workflow.
- **Hooks**: `hooks/` holds safety guards and lifecycle scripts. They are wired in `.claude/settings.json`. Add, remove, or disable any of them.
- **Constitution**: `CONSTITUTION.md` is the behavior contract. Change it to match how you actually work.

Read [docs/customization-guide.md](docs/customization-guide.md) for the how-to.

## Design principles

If you extend the kit, keep these intact so it stays coherent:

1. **Description-driven routing.** An agent or skill is selected by its `description`, not its name. Write descriptions that say *when* to use the thing, not just what it is.
2. **Scoped tools.** Give each agent the smallest set of tools it needs. Four to six is a good ceiling.
3. **Draft, never auto-send.** Anything that leaves the machine (email, message, post) gets shown to the human first. The `comms-guard` hook enforces this. Do not route around it.
4. **Strict schemas for deterministic work.** When a workflow must produce structured output, validate it with a schema, not just a prompt.
5. **Honest data labels.** Mark numbers as `[ACTUAL]`, `[PROJECTED]`, `[ASSUMPTION]`, or `[DATA GAP]`. Never present an estimate as a measurement.
6. **One fact per memory file.** The memory system works because each file is small and single-purpose. Keep it that way.

## Sending improvements upstream

PRs are welcome. The kit is actively maintained, though reviews are best-effort since it is maintained alongside other work.

Good PRs:

- Fix something broken on a platform the author could not test (Windows, Linux distros).
- Generalize something that was still too specific to one job or industry.
- Add a genuinely reusable agent or skill, with no personal or company data in it.

Before opening a PR:

- Run `bash scripts/init.sh` and confirm it passes.
- Confirm no real names, emails, credentials, or company-specific data are in your diff. Example data must be invented, not anonymized from real data.
- Keep one change per PR.

## Code of conduct

Be decent. Assume good faith. Critique ideas, not people. The full policy is in [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Security

Found a security issue? Do not open a public issue. Follow [.github/SECURITY.md](.github/SECURITY.md) to report it privately.
