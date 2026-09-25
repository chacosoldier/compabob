---
name: post-call
description: Capture a debrief right after a meeting or call: what was decided, what was committed, and what changed. Use for "/post-call", "debrief the call with X", or "I just got off a call with Y".
---

# Post-Call Debrief

Close the loop that `/meeting-prep` opens. Turn a finished conversation into durable vault state.

## Steps

1. **Gather.** Ask the user for the raw account of the call, or work from notes or a transcript they provide.
2. **Extract** four things:
   - **Decisions**: what was actually decided.
   - **Action items**: who owes what, by when. Run these through the `second-brain` task intake gate so they do not duplicate existing tasks.
   - **New information**: anything that changes what the vault knows about a person, account, or project.
   - **Follow-up**: the next touchpoint, if any.
3. **Update the vault.**
   - Write or update the meeting note `vault/Meetings/YYYY-MM-DD-<slug>.md`.
   - Update each attendee's `vault/People/<Name>.md`: append to `## Interactions`, refresh their current focus.
   - Update the relevant project or pipeline note.
4. **Confirm** the changes with the user before writing anything that overwrites existing content.

## Output

A short summary first: the one decision or change that matters most. Then the meeting note content for review. Then the list of vault files that will be created or updated, for approval.
