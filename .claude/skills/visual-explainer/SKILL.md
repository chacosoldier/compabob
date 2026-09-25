---
name: visual-explainer
description: Generate a single self-contained HTML page that visually explains a system, a plan, a comparison, or a set of data. Use for "/visual-explainer", "make a diagram of", "show this visually", or when a complex table or architecture would land better as a styled page.
---

# Visual Explainer

Produce one standalone HTML file that explains something clearly. Good for architecture overviews, plan reviews, before/after comparisons, timelines, and dashboards.

## Steps

1. **Clarify the subject and the audience.** What is being explained, and who reads it? That sets the depth.
2. **Choose the form**: a flow diagram, a comparison table, a timeline, a layered architecture, a metric dashboard.
3. **Build one self-contained `.html` file**:
   - All CSS inline in a `<style>` block. No external stylesheets, no CDN links, no network dependencies. The file must open correctly offline by double-clicking it.
   - Readable typography, generous spacing, a restrained palette.
   - Content-first: the explanation carries the page, decoration supports it.
4. **Grade any chart.** If the page holds a quantitative chart (bar, line, scatter, area), run `/chart-tufte` on it and fix what it flags before saving.
5. **Save** to `reports/` (create the directory if needed) as `YYYY-MM-DD-<slug>.html`.
6. **Tell the user** the path so they can open it.

## Principles

- Self-contained or it does not count. One file, opens offline.
- The page answers a question. Lead with that answer, same as any other output.
- Prefer this over a large ASCII table (four or more rows, or three or more columns).
