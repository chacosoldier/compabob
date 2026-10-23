---
name: design-precheck
description: "Pre-check a build plan before any work starts: a parallel pre-mortem by three advisors, the serious findings folded into the plan, and the result written as the '## Pre-mortem' section that hooks/hook-plan-premortem.py requires before a high-stakes plan can leave plan mode. Use when that hook blocks ExitPlanMode, or on \"pre-check this plan before I build it\" and \"/design-precheck\". \"Design\" means a system or build plan, not visual design. A pre-mortem on a personal decision (a job, a hire, a spend) is /council or the strategy-advisor agent."
argument-hint: "[plan file path or pasted plan]"
---

# Design Precheck

Kill or shrink a build while it is still a plan. The pre-mortem hook only checks the section's shape; this skill makes its content real. Never hand-type the section to get past the hook.

## 1. Find the plan

- In plan mode: the plan file Claude Code named under `~/.claude/plans/`.
- Otherwise: the file path or pasted text. Outside plan mode, return the section in chat and add it to the plan file once the work enters plan mode.

Note which hook triggers the plan fires (irreversible, wide blast radius, weeks of work); pass them to every advisor.

## 2. Close open decisions first (one round, at most four questions)

Advisors attacking a plan that rests on an unmade decision produce findings about the guess, not the plan. List the decisions the plan leaves open whose answer would change its shape: who uses the result, the data source, what done means, what is out of scope. If any exist and the user is present, ask them in ONE AskUserQuestion call, each with your recommended answer as the first option, and fold the answers in. Anything still open goes to the advisors as a stated assumption.

## 3. Fan out, in parallel, in ONE message

Give every advisor the plan text (and its path), the triggers it fired, and the common failure patterns below. Each returns at most five findings, one line each: `SEVERITY (FATAL|HIGH|MED) | failure mode | concrete trigger | what to change in the plan`, then a one-word verdict. Judgment only, no rewrites.

| Seat | Agent | Brief |
|---|---|---|
| Pre-mortem (mandatory) | `strategy-advisor` | "Six months from now this plan failed. List the top failure modes and what we would wish we had done differently." Attack adoption and value: who uses it, which step depends on someone doing something by hand, what already covers it. |
| Mechanics | `principal-engineer` | Read the files the plan names; cite file:line. Attack state (first run, re-runs, partial failure), anything that fails silently, untrusted input reaching a script or a model, sends or secrets. Skip this seat when the plan builds nothing technical. |
| Dissenter | `skeptic` (mode DISSENT) | Assigned position: don't build this as specified. Argue that the smallest version, or something that already exists (name it), gets most of the value, and that the definition of done can pass while the goal fails. |

Common failure patterns (give them to every advisor): nobody actually uses the result; a check that grades its own output; a list or registry that rots when nobody updates it; a definition of done that can pass while the result gets worse; value that depends on a manual step the user will not take; an automated step that reads untrusted text.

## 4. Synthesize (you, not another agent)

1. Merge duplicates. A failure mode raised by two or more advisors ranks first.
2. Before a FATAL reshapes the plan, confirm it with one read of the cited file. The attractive finding is the riskiest.
3. Fold every FATAL and HIGH into the plan body itself (scope, steps, definition of done), not only into the section. A MED is folded or recorded as accepted.
4. Verdict: BUILD (no FATAL), RESHAPE (FATALs folded, the plan changed shape), or DONT-BUILD as specified (the fix would be a different project). On DONT-BUILD, stop and ask the user; do not leave plan mode with the old plan.

## 5. Write the section

Append this to the plan, filled in, as the last edit before ExitPlanMode:

```markdown
## Pre-mortem (strategy-advisor via /design-precheck)

Verdict: RESHAPE. Advisors: strategy-advisor (pre-mortem), principal-engineer (mechanics), skeptic (dissent). Six months from now this plan failed because:

- **[FATAL] <failure mode>**: <concrete trigger>. Fold: <what changed in the plan>. (strategy-advisor, skeptic)
- **[HIGH] <failure mode>**: <concrete trigger>. Fold: <what changed in the plan>. (principal-engineer)
- **[MED] <failure mode>**: <concrete trigger>. Accepted: <why it was not folded>. (skeptic)

Unresolved dissent: <the dissenter's strongest point the plan did not concede, and why>, or none.
```

What the hook checks, so the section never fails on shape:
- The heading starts `## Pre-mortem` (two hashes).
- At least three list items before the next `## ` heading: `- ` bullets or `1.` numbered items. Use `###` for any sub-heading inside. Accepted MED risks count; never invent a failure mode to reach three.
- The word `strategy-advisor` appears in the section (the heading carries it).

After the edit, call ExitPlanMode again: the hook reads the plan as it is at that moment.
