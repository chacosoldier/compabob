---
name: reflect
description: "End-of-session reflection: what was learned, what should change, and proposed memory updates, recorded as unchecked items in today's daily note. Use for /reflect, \"what did we learn\", or at the close of a substantial work session. It proposes; /memory-debt applies what is still open later. To save where the work stands for next time, use /handover."
---

# Reflect

Turn a session into durable improvement. Distinct from `/handover` (which persists *state* for next time); this extracts *learning*.

## Steps

1. **Review the session.** What was the goal? What actually happened?
2. **Extract learnings** in three buckets:
   - **What worked**: an approach worth repeating.
   - **What broke**: an error, a wrong assumption, a dead end. Note the root cause, not just the symptom.
   - **What to change**: a concrete adjustment to how the assistant or the workflow operates.
3. **Propose memory writes.** For anything that meets the constitution's memory bar (a repeated lookup, a behavioral correction, a costly debugging lesson), draft a `memory/topics/<slug>.md` entry and the one-line `MEMORY.md` index pointer. Show them; do not write without approval. Write the approved ones now.
4. **Record the rest, always.** Append to `vault/Daily/YYYY-MM-DD.md` (create it if needed) a `## Reflection` section with the three buckets, then every proposal that was not written yet as an unchecked item, so it is never lost:

   ```markdown
   ## Suggested Memory Updates
   - [ ] <what to remember, one line> (target: memory/topics/<slug>.md)
   ```

   Approved and written proposals go in as `- [x]`. `/memory-debt` scans exactly this section later and applies what is still open.

## Output

A short reflection: the single most useful thing learned, then the three buckets, then the proposed memory writes for approval. No padding, no "overall".
