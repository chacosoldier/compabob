---
name: log-decision
description: Record a strategic decision with its reasoning, the alternatives considered, and a date to review the outcome. Use for "/log-decision", "log this decision", or after a significant choice is made.
---

# Log Decision

Capture a decision while the reasoning is fresh, so it can be reviewed honestly later. The point is calibration: a decision logged with its expected outcome can be checked against what actually happened.

## Steps

1. **Gather** the decision: what was decided, when, and by whom.
2. **Capture the reasoning**: the key factors, and the single most important one.
3. **Capture the alternatives**: what else was on the table, and why it lost. "Do nothing" counts.
4. **State the expected outcome** and a **review date** (usually 30 to 90 days out).
5. **Write** to `vault/Decisions/YYYY-MM-DD-<slug>.md`.

## Format

```
---
title: [decision]
date: YYYY-MM-DD
review_on: YYYY-MM-DD
status: open
tags: [decision]
---

# [Decision]

**Decision**: [what was decided]

**Why**: [the reasoning, most important factor first]

**Alternatives considered**:
- [option]: rejected because [...]

**Expected outcome**: [what success looks like, concretely]

**Review on <review-date>**: _(left blank until the review)_
```

## Reviewing

When `/log-decision review` is run, list decisions whose `review_on` date has passed, and for each ask: did it work out? Fill in the review section and set `status` to `validated`, `mixed`, or `wrong`. Honest reviews are the whole value.
