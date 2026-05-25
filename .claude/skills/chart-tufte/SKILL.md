---
name: chart-tufte
description: Self-grade rubric for any quantitative chart, grounded in Edward Tufte's *Visual Display of Quantitative Information*. Run as a final pass inside `visual-explainer` (or any chart-emitting workflow) before showing the chart to the user. Strips chartjunk, checks lie factor, picks the right genre, names the failure modes from VDQI's catalogue.
---

# Chart Tufte

A chart is good when it shows the data, helps the viewer reason about it, and does not lie. Tufte spent a career formalising this. This skill collapses his principles into a self-grade pass that runs on any chart the assistant is about to emit.

**Read [references/vdqi-catalogue.md](references/vdqi-catalogue.md) first** when grading. It holds the named-failures library (NYT MPG 14.8, TIME barrel 59.4, etc.) and the named-exemplars library (Minard, Marey, Playfair, Snow). The catalogue is what makes assessment diagnostic instead of generic.

## When to invoke

- **Automatically** — as the final step inside `visual-explainer` whenever the output is a *quantitative* chart (bar, line, scatter, area, dot, range-frame). Skip for diagrams (architecture, sequence, flow); those are different beasts.
- **Explicitly** — `/chart-tufte <chart-spec>` to score a chart produced elsewhere.

## The rubric (run before emitting)

Score each on 0-10. Stop and revise if any score drops below 5.

1. **Data-ink ratio** — does every pixel of ink represent data? Borders, gridlines, redundant legends are non-data ink. Target: tend toward 1.0; typical for default-styled charts is 0.1-0.2 (VDQI p.136).
2. **Lie factor** — `(visual change %) / (data change %)`. Acceptable range 0.95-1.05. Cite a VDQI named failure if it is worse: TIME's barrel chart hit 59.4, NYT's MPG hit 14.8.
3. **Data density** — numbers per square inch. Below 0.15 is overwrought (a single bar showing one number is the canonical sin). High-density alternatives: small multiples, range-frame scatters, tables.
4. **Chartjunk count** — does the chart contain any of the four named species?
   - **Moiré** — vibrating cross-hatch patterns.
   - **The dreaded grid** — gridlines drawn darker than the data.
   - **The duck** — visual gimmick that overwhelms the data (3D pies, gradient-shaded bars).
   - **Decoration** — clip art, icons, mascots in the chart frame.
   Each chartjunk species costs points.
5. **Genre fit** — is this the right *shape* for this data?
   - ≤20 numbers → table, not chart
   - Many series → small multiples (one panel per series)
   - 2 quantitative variables → range-frame scatter (axis only spans data min-max)
   - Distribution → quartile plot, not bar of mean
   - Time series → thin line + direct endpoint labels, no legend
6. **Dimensionality discipline** — does the chart use more dimensions than the data has? A 3D pie chart on 1D data is dishonest by construction. Penalise.
7. **Direct labelling** — are series labelled at their endpoint or inline, not via a separate legend? Legends force the reader's eye to bounce.
8. **Range-frame discipline** — does the axis span only the data range, not 0 to some arbitrary max?
9. **Comparability** — if multiple panels: same y-scale where comparison matters; different scales only when local shape is the question.

## Remedies (when the rubric flags problems)

- **B1 — fix lie factor**: redraw with proportional scaling. State the new lie factor in the chart caption.
- **B2 — erase non-data ink**: remove borders, drop gridlines, kill the legend if direct labelling fits.
- **B3 — increase data density**: switch to small multiples if you have ≥3 panels of comparable data.
- **B4 — pick the right genre** (see C1-C10 below).
- **B5 — name the failure**: if the chart resembles a VDQI named failure (NYT MPG 14.8, TIME barrel 59.4, LA Times shrinking-doctor 2.8, USA Today 3D bar chart, Playfair's wheat decline), say so before showing.
- **B6 — fix dimensionality**: 1D data → 1D chart; never 3D unless the third dimension is *in* the data.
- **B7 — deflate currency over time**: if plotting dollars across years, deflate to a common year (state which) before plotting. Failing to do this is a silent lie factor.

## Genre playbook (C1-C10)

- **C1 — quartile plot** for distributions (5-number summary, no whiskers gimmick).
- **C2 — range-frame scatter** for two quantitative variables (axes span data range only).
- **C3 — dot-dash marginals** on a range frame to show density on each axis.
- **C4 — paired bars** for two-group comparison on one categorical axis.
- **C5 — small multiples** for many series (1 panel per series, same x-axis, often same y-axis).
- **C6 — sparkline** for inline time series at word-scale.
- **C7 — slopegraph** for before/after comparison across many categories.
- **C8 — stem-and-leaf table** when the goal is the actual numbers, not the shape.
- **C9 — table** when ≤20 numbers and structure matters.
- **C10 — thin line chart** for time series, direct endpoint label, no legend, no gridlines.

## Exemplars to emulate

- Minard's *Napoleon's March* (1869) — six variables, one image, time + space + temperature + casualties.
- Playfair's wheat-vs-wages (1822) — currency deflated, dual y-axis used honestly.
- Modern NYT inflation charts — direct labels, no gridlines, deflated currency.
- Tufte's own sparkline-in-prose pattern — chart as part of the sentence.

## Output

A six-line block:

```
Tufte self-grade
  Data-ink ratio: 7/10
  Lie factor: 1.02 (acceptable; not in catalogue)
  Chartjunk: 0 species
  Genre fit: C10 (thin line) — correct for the data
  Verdict: ship
  Notes: (any remedies applied during pass)
```

If the verdict is not `ship`, revise the chart and re-grade before emitting.

## Integration with `visual-explainer`

Two integration points:

1. **At plan time** — when `visual-explainer`'s aesthetic step picks a visual palette, ALSO pick a Tufte genre (C1-C10). Record both. Never combine the *aesthetic* with the *genre*.
2. **At emit time** — run this rubric over the rendered HTML/SVG before opening it in the browser. If any score < 5, revise. Block on `verdict != ship`.

## VDQI page references (for citations)

- Data-ink ratio definition + targets: p.93, 136
- Lie factor formula + named failures: pp.55-80
- Chartjunk taxonomy (moiré / grid / duck / decoration): pp.107-121
- Small multiples: pp.170-175
- Range frame: pp.130-133
- Sparklines (later book *Beautiful Evidence*, but cited in the canon)

Edward Tufte, *The Visual Display of Quantitative Information*, 2nd ed., Graphics Press, 2001.
