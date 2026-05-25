---
name: memory-debt
description: Review and apply pending memory updates that earlier sessions proposed but never wrote. Use `/memory-debt` to see what is pending, `/memory-debt apply` to resolve it interactively.
---

# Memory Debt Resolution

You are a memory hygiene tool. Your job is to find suggested memory updates that earlier sessions proposed (typically in `vault/Daily/<date>.md` under a `## Reflection` heading, written by `/reflect`), verify they are still valid, and apply them with the user's approval.

Pairs with `/reflect`: `/reflect` proposes memory writes; `/memory-debt` collects the ones that never got applied and closes the loop.

## Mode detection

Check args:
- No args or `review` — Review Mode (show pending items).
- `apply` — Apply Mode (resolve all pending items interactively).

## Review Mode (default)

### 1. Scan reflection sources

Read in this order, stopping when at least one returns content:

1. `vault/Daily/*.md` — every file with a `## Reflection` section or a `## Suggested Memory Updates` section.
2. `vault/Reflections/*.md` — older convention.
3. `vault/Journal/*.md` — alternate convention.

For each file, extract:
- "Suggested Memory Updates" entries (each starts with `- [ ]` or `- [x]`).
- Free-text proposals under a `## Memory` or `## Memory Debt` heading.

### 2. Classify each unchecked item

For every `- [ ]` entry:
1. Read the target file mentioned in the proposal. If no target is named, default to `memory/topics/<slug>.md` derived from the proposal title.
2. Search for the proposed content (exact match first, then semantic — keywords from the proposal).
3. Classify as:
   - **APPLIED** — content already exists in the target file. Tick the diary entry to `- [x]` silently.
   - **PENDING** — content not found, proposal is < 3 days old.
   - **STALE** — content not found, proposal is 3+ days old.
   - **OBSOLETE** — target file does not exist, or the project state contradicts the proposal.

### 3. Present summary

```
## Memory Debt Report

| # | Date | Target | Suggestion | Status | Age |
|---|---|---|---|---|---|
| 1 | YYYY-MM-DD | memory/topics/<slug>.md | <one-line summary> | PENDING | 1d |

**Totals**: X pending, Y stale, Z already applied (silent fixes), W obsolete
```

## Apply Mode (`/memory-debt apply`)

### 1. Run Review Mode first
Build the full pending/stale/obsolete list.

### 2. Interactive resolution

For each PENDING or STALE item (oldest first), present:
1. The original suggestion (from the diary).
2. The target file's current relevant section (so the user sees what changes).
3. The exact text to add or modify.

Ask: **Apply / Skip / Edit / Obsolete**.

### 3. Execute approved changes

For each approved item:
1. Read the target file.
2. Apply the change (`Edit` or append).
3. If the target file is new and lives at `memory/topics/<slug>.md`, also add a one-line pointer to `memory/MEMORY.md` so the index stays current.
4. Update the diary entry from `- [ ]` to `- [x]`.

### 4. Report

Final summary: X applied, Y skipped, Z marked obsolete, W silent fixes.

## Constraints

- **Never auto-apply.** Always present each item for approval before modifying any file.
- **Read before writing.** If the content already exists, mark APPLIED silently — never duplicate.
- **MEMORY.md line cap.** If the constitution sets a limit (commonly ~200 lines), and writing the proposal would breach it, suggest a topic file in `memory/topics/` and a one-line index pointer instead of inlining.
- **Diary edits are minimal.** Only flip checkboxes and update Memory Debt table status. Never rewrite proposal text.
- **Oldest first.** Process chronologically so the longest-overdue debt clears first.

## Quality checklist

- [ ] All reflection sources scanned (`vault/Daily/`, `vault/Reflections/`, `vault/Journal/`).
- [ ] Each proposal's target file is actually read before classifying.
- [ ] No duplicate content is written.
- [ ] Diary checkboxes are updated after each application.
- [ ] `memory/MEMORY.md` stays under any configured line cap.
