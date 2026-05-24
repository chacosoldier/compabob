# Persona presets

A persona preset is a starting point for **one file**: `memory/topics/role-and-priorities.md`.
When you run `setup.sh` it asks which persona best describes your work, then
seeds that file with role-appropriate starter content so the assistant has
something real to reason about on day one instead of an empty template.

## What a preset does, and does not

- **Does**: pre-fill `memory/topics/role-and-priorities.md` with sections and
  example brackets tuned to your kind of work, and record which preset you chose
  in `config/user.config.yaml` (`persona.preset`).
- **Does not**: add, remove, hide, or change any agent, skill, or hook. Every
  agent stays available to every persona. A preset only *nudges* where to start;
  the "Where the assistant helps most" section is advice, not a restriction.

It is applied once, at setup. If you have already edited
`role-and-priorities.md`, re-running setup will **not** overwrite your edits.

## The presets

| Preset | For |
|--------|-----|
| `generalist` | Knowledge work broadly. The neutral default. |
| `consultant` | Client-facing delivery, proposals, stakeholder work. |
| `engineer` | Shipping software and owning technical decisions. |
| `sales` | Pipeline, deals, accounts, quota. |
| `founder` | Running a business: strategy, fundraising, hiring, product. |
| `researcher` | Academia and R&D: literature surveys, paper drafting, experiments. |

## Add your own

Copy any file in this directory, rename it `<your-id>.md`, set the `id` and
`label` in the frontmatter, and rewrite the body. The body becomes
`role-and-priorities.md` verbatim, with one substitution: `<WHAT_YOU_WORK_ON>`
is replaced by the free-text answer setup collects. Then add your id to the
persona prompt in `setup.sh`.
