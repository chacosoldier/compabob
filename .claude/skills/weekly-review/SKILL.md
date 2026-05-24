---
name: weekly-review
description: End-of-week review — what got done, what slipped, decisions made, and next week's top 3 priorities. Use for "/weekly-review", "end-of-week review", "what happened this week", or on the last working day of the week.
---

# Weekly Review

Produce a terse end-of-week summary that captures what changed and what is still owed.

## Steps

1. **Determine the Week.** Confirm the ISO week (e.g. `2026-W21`). Use `date` or the `inject-now` hook.

2. **Gather inputs.** Read:
   - `vault/Daily/` — all daily notes from Monday through today (or the last 7 days). Pull `## Priorities`, `## Completed`, and any `## Reflection` sections.
   - `vault/Decisions/` — any decision records dated this week.
   - `memory/topics/` — entries modified this week (check `memory/MEMORY.md` for the index).
   - If meeting notes exist in `vault/`, scan recent ones for open action items.

3. **Synthesize five sections:**

   - **Done** — what was completed (shipped, merged, decided, closed).
   - **Slipped** — what was planned but not done; carry-forward items.
   - **Decisions** — key decisions made (link to `vault/Decisions/` files).
   - **Owed to others** — commitments the user owes to someone else.
   - **Owed to self** — commitments the user made to themselves.

4. **Propose top 3 priorities for next week.** Base them on the slip-list and the most consequential pending commitments. One sentence each.

5. **Write to vault** (optional). Ask the user; if they approve, write to `vault/Weekly/YYYY-WW.md`.

## Output

Lead with one sentence summarising the week. Then:

```
## Weekly Review — YYYY-WW

**Done**
- ...

**Slipped**
- ...

**Decisions**
- ...

**Owed to others**
- ...

**Owed to self**
- ...

### Next week's top 3
1. ...
2. ...
3. ...
```

Terse and scannable. Omit any empty section. End with no closing line.
