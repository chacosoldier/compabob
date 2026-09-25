---
name: reflect
description: End-of-session reflection, extract what was learned and what should change, and propose memory updates. Use for "/reflect", "what did we learn", or at the close of a substantial work session.
---

# Reflect

Turn a session into durable improvement. Distinct from `/handover` (which persists *state* for next time); this extracts *learning*.

## Steps

1. **Review the session.** What was the goal? What actually happened?
2. **Extract learnings** in three buckets:
   - **What worked**: an approach worth repeating.
   - **What broke**: an error, a wrong assumption, a dead end. Note the root cause, not just the symptom.
   - **What to change**: a concrete adjustment to how the assistant or the workflow operates.
3. **Propose memory writes.** For anything that meets the constitution's memory bar (a repeated lookup, a behavioral correction, a costly debugging lesson), draft a `memory/topics/<slug>.md` entry and the one-line `MEMORY.md` index pointer. Show them; do not write without approval.
4. **Write the diary entry** (optional) to `vault/Daily/YYYY-MM-DD.md` under a `## Reflection` heading.

## Output

A short reflection: the single most useful thing learned, then the three buckets, then the proposed memory writes for approval. No padding, no "overall".
