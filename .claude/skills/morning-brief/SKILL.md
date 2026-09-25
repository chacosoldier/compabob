---
name: morning-brief
description: "Start-of-day briefing: priorities, what is due, what is owed, today's meetings, and anything overdue. Use for /morning-brief, \"brief me\", or at the start of the first session of the day. For the full list of open tasks, use /tasks."
---

# Morning Brief

Produce one scannable briefing that tells the user what matters today.

## Steps

1. **Date.** Confirm today's date (the `inject-now` hook provides it).
2. **Priorities.** Read today's daily note `vault/Daily/YYYY-MM-DD.md` if it exists, and yesterday's for anything carried over. Pull the `## Priorities` section.
3. **Tasks.** Scan the vault and `memory/topics/brief-queue.md` for items due today or overdue. The `crm-relationships` and `comms-meetings` agents can supply follow-ups owed and owing.
4. **Meetings.** If a calendar integration is enabled, list today's meetings with one line of context each. If not, say so and skip.
5. **Brief queue.** Include anything captured via the `daily-copilot` "remember this" flow for today, then clear those entries.
6. **Synthesize.**

## Output

Lead with the single most important thing about today, in one sentence. Then:

```
## Morning Brief: <date>

**Today's focus**: [the one thing]

**Priorities**
- ...

**Due / overdue**
- ...

**Meetings**
- HH:MM  [title]: [one line of context]

**Owed to you / owed by you**
- ...
```

Keep it short. If a section is empty, omit it rather than padding. End with no closing line.
