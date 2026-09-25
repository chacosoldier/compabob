---
name: system-audit
description: Health check of the assistant's own setup, agents, hooks, skills, settings, memory, and vault structure. Use for "/system-audit", "is everything wired up", or after changing the configuration.
---

# System Audit

Verify the assistant's own configuration is intact and consistent. Run it after customizing the kit, or any time something feels off.

## Checks

1. **Setup complete.** Search the repo for unfilled placeholders, the pattern `setup.sh` fills (double braces around capitals, e.g. the assistant-name token). Any hit outside `docs/` or a `.template` file means setup did not finish. Report each one.
2. **Agents.** Every file in `.claude/agents/` (except `_`-prefixed ones) has valid frontmatter with `name`, `description`, and `tools`. The `description` says *when* to use the agent. Flag any agent with an empty or vague description (routing will suffer).
3. **Hooks.** Every hook referenced in `.claude/settings.json` exists on disk. Run `bash scripts/init.sh` and report its result.
4. **Skills.** Every directory in `.claude/skills/` has a `SKILL.md` with `name` and `description` frontmatter.
5. **Settings.** `.claude/settings.json` is valid JSON. `settings.local.json` exists (created by `setup.sh`).
6. **Memory.** `memory/MEMORY.md` exists and its links into `memory/topics/` resolve.
7. **Vault.** `vault/` has the expected folders and `vault/00-Home.md` exists.
8. **Modules.** For each enabled module, its own check passes (see the module's README).

## Output

A short verdict first: all green, or N issues. Then a checklist with PASS / WARN / FAIL per item, and for each FAIL the concrete fix. End with the single most important thing to fix, if anything.
