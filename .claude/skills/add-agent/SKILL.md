---
name: add-agent
description: Scaffold a new specialized agent for this assistant. Use for "/add-agent", "create a new agent", or "I want an agent that does X".
---

# Add Agent

Create a new agent so the assistant grows with the user's work. This is the main way to customize the kit.

## Steps

1. **Ask four things** (one short round of questions, not an interrogation):
   - **Name** — kebab-case, e.g. `recruiting` or `product-research`.
   - **Purpose and triggers** — what it owns, and the phrases or domains that should route to it. This becomes the `description`, which is what actually drives routing.
   - **Tools** — the minimum it needs (4 to 6). Advice-only agents get read tools only: `Read, Glob, Grep, WebFetch, WebSearch`.
   - **Model**: `inherit` is the default (the agent follows the session's model); pin `sonnet` for a cheap, high-volume agent or `opus` for one that always needs hard reasoning.
2. **Check for overlap.** Read the existing agents in `.claude/agents/`. If the new agent overlaps an existing one, say so and suggest either editing the existing agent or sharpening both descriptions so routing stays clean.
3. **Scaffold.** Copy `.claude/agents/_agent-template.md.template` to `.claude/agents/<name>.md` and fill it in: frontmatter, Purpose, When to use / when not to, Output format, Safety.
4. **Register it.** Add a one-line routing rule for the new agent to the Agent Architecture & Routing section of `CONSTITUTION.md`. (`_orchestrator-reference.md` describes coordination patterns; it is not a list of agents.)
5. **Test routing.** Suggest two or three prompts that should land on the new agent, and one that should *not* (to confirm it does not over-trigger).

## Principles

- The `description` is the routing signal. Write it as "Use for X, Y, Z", and name what it is *not* for.
- Keep the tool list minimal. An agent with every tool routes badly.
- One agent, one job. If it needs a paragraph to describe, it is two agents.
