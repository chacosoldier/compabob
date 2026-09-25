---
name: meeting-prep
description: "Prepare for an upcoming meeting: who is attending, the history, open items, and the decision the meeting needs to reach. Use for /meeting-prep, \"prep me for my meeting with X\", or \"what do I need to know before the call with Y\". To capture what happened after the meeting, use /post-call."
---

# Meeting Prep

Build a prep brief so the user walks into a meeting fully oriented.

## Steps

1. **Identify the meeting.** Get the title, time, and attendees. If a calendar integration is enabled, read the event; otherwise ask the user.
2. **Attendees.** For each person, read `vault/People/<Name>.md`: their role, company, the relationship state, and the last interaction. If a person has no note, note that and offer to create a stub.
3. **History.** Search `vault/Meetings/` for prior meetings with the same people or on the same topic. Pull the key takeaways and any decisions.
4. **Open items.** List action items and commitments still open from past interactions, in both directions.
5. **Purpose.** Name the decision or outcome this meeting needs to produce. If it is unclear, that is the first thing to flag.

## Output

```
## Meeting Prep: [title], [date/time]

**Decision this meeting needs to reach**: [...]

**Attendees**
- [Name] ([role], [company]): [relationship state, last contact]

**Context** (from prior meetings)
- ...

**Open items**
- [ ] ... (owed by whom)

**Suggested talking points**
- ...

**Watch out for**
- [anything sensitive, unresolved, or political]
```

Offer to save the brief to `vault/Meetings/YYYY-MM-DD-<slug>.md`. After the meeting, use `/post-call` to close the loop.
