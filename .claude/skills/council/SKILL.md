---
name: council
description: "Advisor panel plus a mandatory dissenter for a high-stakes decision. Runs strategy-advisor and first-principles in parallel with a third advisor assigned to argue against the leaning option, then writes a recommendation that must answer each dissent point. Use on 'should I X' or 'deciding between Y and Z' when the call is hard to reverse (a job, a hire, a big spend, a strategy bet) and the user wants real challenge rather than agreement. For one sparring view on a smaller or reversible call, use the strategy-advisor agent alone; to record the outcome afterwards, use /log-decision."
---

# Council with a mandatory dissenter

A panel of advisors plus one advisor whose only job is to argue the other side, then a synthesis that has to engage that dissent point by point. The point is anti-sycophancy: on the decisions where the user most needs to hear they might be wrong, never hand back one agreeable viewpoint.

## Stakes gate

- Run it when the decision is hard to reverse or expensive to get wrong: career moves, hiring or firing, a large spend or commitment, a strategy bet.
- Invoked explicitly as `/council <topic>`: always run.
- For a reversible or small call ("should I reply today or tomorrow"), do not convene the panel. Answer with the `strategy-advisor` agent alone.

## Steps

### 1. Recall

Check whether the user has decided something similar before: search `vault/Decisions/` (where `/log-decision` writes) and memory for the topic. Treat what you find as a prior, never as this decision's answer. If nothing turns up, say so in the synthesis and continue.

### 2. Frame

- The decision in one sentence.
- The options, or the binary, stated explicitly.
- What would change the recommendation: the one uncertainty that matters most.
- The user's current leaning, if they gave one.

If the real alternatives, the binding constraint, or the timeframe are missing, ask one or two questions before spawning anything.

### 3. Panel (three Agent calls in ONE message, blind to each other)

Send all three in a single message so they run in parallel, each with the framed decision, the recall, and its own brief, and nothing about the others' output. Pass `model: "sonnet"` on each call to keep a council run affordable on any plan; drop it if the user wants the panel on their session's model.

- **`strategy-advisor`**: decision frame, pre-mortem, a steelman of each option.
- **`first-principles`**: what is actually known and at what confidence, base rates, a short scenario tree.
- **Dissenter** (a second `strategy-advisor` call): assign a concrete opposing persona grounded in THIS decision, never a generic devil's advocate. Examples: "the CFO who wants to kill this spend", "you, two years from now, regretting this", "the co-founder who thinks this is a distraction". Brief: "Your only job is the strongest case AGAINST <the leaning option, or the default option if there is no leaning>. Concrete claims with reasons. No hedging, no praise, no restating the plan. You are the only dissenting voice on this panel."

Append to every brief: "Reasoning only. Do not spawn sub-agents, send messages, write files, or run commands. Return your case as text."

### 4. Synthesis (you, in this order)

1. **Recommendation**, answer first: the call, your confidence, and the single biggest reason.
2. **`## Dissent`**, never empty: the two or three strongest points against, as concrete claims from the dissenter. Fill it even when the panel agreed; a unanimous panel is the case that most needs a forced opposing view.
3. **Engagement**: rebut or concede each dissent point by name. "The cost point is real; here is the tripwire that would flip me" or "point 2 is decisive, so the recommendation is conditional on X." A rebuttal, not a list.
4. **Tripwires and gaps**: what would change the call, and what is still unknown.

### 5. Close the loop

Once the user decides, offer `/log-decision` to record the decision, the reasoning, and a date to check how it turned out. The next council on a similar topic finds it in step 1.

## Constraints

- Panelists reason only: no writes, sends, commands, or nested agents.
- The dissenter seat is never empty, even when everyone agrees.
- Cost: three subagent calls plus the synthesis. Worth it for a decision that matters; overkill for everything else.
