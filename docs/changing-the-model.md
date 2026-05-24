# Changing the Claude Model

The kit defaults to Claude Sonnet — the best all-round balance of speed, cost, and capability. You can change the model globally per session, or per agent via frontmatter.

## Per-session default

Two ways to set the model for an entire session:

1. **Settings file** — create or edit `.claude/settings.local.json` and add:
   ```json
   {
     "model": "claude-opus-4-20250514"
   }
   ```
   This file is git-ignored (your data, not the kit's), so the setting persists across sessions without touching version control.

2. **CLI flag** — start the session with `claude --model claude-sonnet-4-20250514` to override the file setting for that run.

The precedence is: CLI flag > `settings.local.json` > the kit's `settings.json` default (Sonnet).

## Per-agent model

Set a model for a single agent by adding a `model:` field in its frontmatter. Open `.claude/agents/<agent>.md` and add:

```yaml
---
description: Use for deep strategic analysis and first-principles reasoning.
model: claude-opus-4-20250514
---
```

When the orchestrator routes to that agent, the session model is temporarily swapped to the one specified in its frontmatter. Other agents keep using the session default.

## Trade-offs

| Model   | Best for                              | Cost        | Speed  |
|---------|---------------------------------------|-------------|--------|
| Opus    | Hard reasoning, strategy, long chains | High        | Slow   |
| Sonnet  | Everything else                       | Moderate    | Fast   |
| Haiku   | Cheap classification, quick routing   | Low         | Fastest|

- **Opus** — use for the hardest problems: deep strategic analysis, first-principles reasoning, complex multi-step planning. The extra deliberation is worth the wait. **Warning:** Opus counts against Pro limits much faster than Sonnet.
- **Sonnet** — the daily driver. Fast, capable, good-enost for almost everything. Stick with it unless you specifically need Opus depth or Haiku speed.
- **Haiku** — ideal for cheap, fast classification tasks (tagging, routing, simple extraction). Not suitable for reasoning or generation.

## Worked example

Suppose you want your daily assistant on Sonnet (fast, cheap) but route hard strategic work to Opus.

1. Leave the session default as Sonnet (no change needed — that is what the kit ships with).

2. Edit `.claude/agents/strategy-advisor.md` — add `model: claude-opus-4-20250514` in the frontmatter:
   ```yaml
   ---
   description: Use for competitive analysis, market positioning, and strategic planning.
   model: claude-opus-4-20250514
   ---
   ```

3. Edit `.claude/agents/first-principles.md` — same addition:
   ```yaml
   ---
   description: Use for root-cause analysis, mental models, and first-principles reasoning.
   model: claude-opus-4-20250514
   ---
   ```

4. Edit `.claude/agents/daily-copilot.md` — no model field needed (it will inherit the session's Sonnet default).

Now when the orchestrator routes a question to `strategy-advisor` or `first-principles`, the session briefly switches to Opus. Everything else stays on Sonnet.

## Pro vs Max

If you are on a **Pro** plan, be mindful that Opus draws from your usage limits much faster than Sonnet. A single Opus exchange can consume 3–5× the tokens of a comparable Sonnet exchange. On **Max**, usage-based pricing applies, so you pay per token regardless of model — but Opus tokens are priced higher. Reserve Opus for tasks where its extra depth clearly matters.
