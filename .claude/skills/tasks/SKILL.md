---
name: tasks
description: Show a single aggregated task view pulled from across the vault and the brief queue. Use for "/tasks", "what are my open tasks", "what's overdue", or "/tasks done [id]" to complete one.
---

# Tasks

One view of everything open, gathered from where tasks actually live.

## Sources

- `- [ ]` checkboxes anywhere in `vault/` (meeting notes, project notes, daily notes).
- `memory/topics/brief-queue.md`: items captured via "remember this".
- Follow-ups tracked by the `comms-meetings` agent.

## Steps

1. **Collect** open `- [ ]` items via `Grep` across `vault/`. Record each item's source file.
2. **Group by urgency**: Overdue, Due today, This week, Next week, Someday (no date).
3. **Deduplicate**: if the same task appears in two places, show it once and note both sources.
4. **Present** the grouped list. Each line: the task, its due date if any, and a link to its source file.

## Commands

- `/tasks`: full refresh and grouped view.
- `/tasks done [text or id]`: find the matching `- [ ]`, change it to `- [x]` with a completion date, confirm.
- `/tasks add [text]`: add a task; route it through the `second-brain` intake gate so it does not duplicate an existing one.

## Output

Overdue first, always. If nothing is overdue, say so plainly. Keep it a scannable list, not prose.
