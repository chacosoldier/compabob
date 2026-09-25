---
name: handover
description: Write a handover note before ending a working session so the next session picks up with full context. Use for "/handover", "wrap up", or "write a handover before I stop".
---

# Handover

Persist session context so the next session starts oriented instead of cold.

## Steps

1. **Summarize the session**: what was worked on, what was decided, what was finished.
2. **Capture the open thread**: what is in progress, the exact next step, and any state that matters (a branch name, a file mid-edit, a blocked decision).
3. **Note anything fragile**: a test that is failing, an assumption not yet verified, a thing that will break if forgotten.
4. **Write** the note to `.tmp/handover.md`. The `hook-session-start.sh` hook reads this file at the start of the next session and injects it automatically.

## Format

```
# Handover: <date> <time>

## Done this session
- ...

## In progress
- [the open thread, with the exact next step]

## Watch out for
- [anything fragile or unverified]

## Next step
[one sentence: what to do first next session]
```

After writing, confirm in one line: "Handover saved to .tmp/handover.md." If durable facts surfaced (not session state, but lasting knowledge), also propose memory writes per the constitution.
