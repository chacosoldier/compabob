# Orchestrator Reference

How the main session coordinates the agent fleet. Primary routing rules live in `CONSTITUTION.md`; this file holds the detail.

> The canonical agent list and what each one is for lives in `CONSTITUTION.md` (Agent Architecture & Routing). It is not repeated here, so there is one source of truth to keep current. This file covers how the main session coordinates the fleet once a request has been routed.

## Routing

Match the request against each agent's `description`, not its name. The rules of thumb in `CONSTITUTION.md` cover the common cases. For ambiguous requests, ask one clarifying question rather than guessing.

When two agents seem equally plausible, prefer the narrower-scoped one. It will redirect if wrong; the broader one will absorb the task without flagging the boundary.

### Negative routing (disambiguation)

| Phrase | Looks like | Routes to | Why |
|--------|-----------|-----------|-----|
| "challenge this plan" | a coaching ask | `strategy-advisor` | An artifact is being brought for critique |
| "what's wrong with this code" | `strategy-advisor` | `principal-engineer` | Engineering critique, not strategic |
| "what's wrong with this plan" | `principal-engineer` | `strategy-advisor` | Strategic critique, not engineering |
| "what does this concept really mean" | `strategy-advisor` | `first-principles` | Abstract reasoning, not a decision |
| "save this to the vault" | the originating agent | `second-brain` | Advice-only agents request persistence |

## Pipeline patterns

**Parallel fan-out, main-session fan-in** (most common): spawn two independent agents at once, wait for both, synthesize, present.

**Sequential chain**: spawn agent A, pass its output to agent B, present.

The rule: agents produce data, the main session produces insight.

## Handoff rules

- Always pass the date range used in any query so downstream agents match it.
- When passing data to an output step, provide structured tables, not prose.
- Include the query or source used so a downstream agent can verify.
- Advice-only agents (`strategy-advisor`, `principal-engineer`, `first-principles`) never write files. When their output should persist, the main session hands it to `second-brain`.
- Verification goes to `skeptic`, never back to the agent that produced the finding. Give it the claims and the files, not your conclusion, so its check is independent.

## Error handling

All agents follow `error-handling.md` for classification, retries, fallbacks, and recovery. This file defines the topology; that file defines what happens when a handoff fails.
