# VDQI catalogue — named failures, named exemplars, quantitative anchors

Reference depth for the `chart-tufte` skill. The SKILL.md handles the rubric (9 criteria, 10 genres, 7 remedies). This file holds the *comparison libraries* that make assessment diagnostic.

When grading a chart, the SKILL.md says "name the failure." This file holds the names. When recommending a redesign, the SKILL.md says "point to an exemplar." This file holds the exemplars.

All citations are page numbers in Edward Tufte, *The Visual Display of Quantitative Information*, 2nd ed., Graphics Press, 2001 (referred to below as VDQI).

---

## Named failures — comparison library

Compare a flagged chart to one of these. Saying "this is essentially the 1979 TIME barrel — lie factor likely 50+" is more diagnostic than "looks distorted."

| Source | Date | Failure mode | Tufte's metric | VDQI p. |
|---|---|---|---|---|
| New York Times, "Fuel Economy Standards" | 1978-08-09 | 1-D quantity drawn as 2-D shrinking-road area; date sizes held constant while road narrowed | **Lie factor 14.8** (53% data change rendered as 783% visual change) | 57-58 |
| TIME, "IN THE BARREL" | 1979-04-09 | Oil prices drawn on 3-D barrels of varying volume | **Lie factor 9.4 (area) / 59.4 (volume)** — Tufte calls it "a record" | 62, 71 |
| Washington Post, "OPEC Benchmark Prices" | 1979-03-28 | Varying-size oil derricks for 1-D price data | **Lie factor 9.5** (708% data → 6,700% visual) | 62 |
| LA Times, "The Shrinking Family Doctor" | 1979-08-05 | 2-D area + perspective + wrong horizontal spacing for 1-D ratio data | **Lie factor 2.8** | 69 |
| New York Times, "Commission Payments to Travel Agents" | 1978-08-08 | Half-year values plotted at full-year intervals — "the lie repeated four times over" | — | 54 |
| Day Mines, Inc., Annual Report | 1974 | Hidden baseline at approximately -$4.2M concealed the 1970 loss | — | 54 |
| NSF, *Science Indicators*, Nobel Prizes chart | 1976 | Irregular x-axis: seven 10-year intervals followed by one 4-year interval, faking a decline | — | 60 |
| New York Times, OPEC Oil Prices | 1978-12-19 | Five different vertical scales on one chart; the same value renders **15.1× different** depending on which axis you read | — | 61 |
| New York Times, "NY State Total Budget Expenditures" | 1976-02-01 | Fake 3-D rendering plus raw (un-deflated) dollars to suggest explosive growth | — | 66-68 |
| Fiorina, *Congress: Keystone of the Washington Establishment* | 1977 | No deflation of monetary series, plus tall-thin aspect ratio (2.7:1 taller than wide) | — | 66 |
| Satet, *Les Graphiques* | 1932 | Men of varying body sizes representing export growth (area encoding for 1-D data) | — | 69 |
| Pittsburgh Civic Commission report | 1911 | Buildings sized by height alone, ignoring area effect | — | 55 |
| Dewey & Dakin, *Cycles: The Science of Prediction* | 1947 | "Solar Radiation and Stock Prices" — implied causation between unrelated series | Tufte: "a silly theory means a silly graphic" | 15 |

### How to use this table

When `chart-tufte` flags a problem, scan this table for the closest match.

- 1-D data drawn as area or volume → **NYT MPG (14.8)** for area, **TIME barrel (59.4)** for volume.
- Hidden or shifted baseline → **Day Mines (1974)**.
- Inconsistent x-axis intervals → **NSF Nobel Prizes (1976)**.
- Multiple y-axis scales on one chart → **NYT OPEC (1978-12-19, 15.1× variation)**.
- Un-deflated monetary series → **Fiorina (1977)**.
- Implied causation between independent series → **Dewey & Dakin (1947)**.

State the comparison verbatim in the grade output: "This resembles the 1979 LA Times shrinking-family-doctor — lie factor 2.8."

---

## Named exemplars — success library

When proposing a redesign, point at a specific exemplar to emulate. "This data calls for the Marey treatment" is concrete; "use direct labels" is generic.

| Graphic | Creator / Year | Tufte's praise | What to copy |
|---|---|---|---|
| Napoleon's March on Russia | Charles Joseph Minard, 1869 | "It may well be the best statistical graphic ever drawn." | Stack 6 variables (army size, x, y, direction, temperature, date) in one image so the reader is "hardly aware they are looking into a world of four or five dimensions." |
| Cholera map of Broad Street | Dr. John Snow, 1854 | "Graphical analysis testifies about the data far more efficiently than calculation." | Place events on geography; let the spatial cluster reveal cause. |
| Paris-Lyon train schedule | E.J. Marey, 1885 | "Giving a context and order to complexity ... aesthetic balance." | Slope = speed; intersections = time + place. Mute grid to a soft gray so data dominates. |
| *Commercial and Political Atlas* | William Playfair, 1786 | Playfair "invented or improved upon nearly all the fundamental graphical designs." | Eliminate non-data detail; use data-based grids that serve rather than fight the data. |
| NYC Weather History | NYT, 1981-01-11 | "Successfully organizes a large collection of numbers, makes comparisons ... tells a story." | 181 numbers per square inch density; reserve full-page graphics for genuinely rich material (VDQI p.30, 164). |
| Map of 1.3 Million Galaxies | Seldner et al., 1977 | "No other method for the display of statistical information is so powerful." | 110,000+ numbers per square inch (a record); varying greys rather than colors (VDQI p.166). |
| Atlas of Cancer Mortality | Hoover et al., 1975 | "Attention has been directed toward exploring the substantive content of the data rather than methodology." | Massive data in small space via small multiples on a geographic base. |
| LA Air Pollutants small multiples | McRae et al., 1979 | "Inevitably comparative, deftly multivariate, efficient in interpretation." | Repeat one design across panels; shift only the data, never the encoding. |
| Thermal Conductivity of Cu/W | Ho, Powell, Liley, 1974 | "Effectively organizes a vast amount of data ... enforcing comparisons." | Double-functioning marks: coordinate labels ARE the data values. |
| "Living" Histogram | Joiner, 1975 | "The data form the data measure." | Use the data as its own mark (photos of students arranged by height). |
| Japanese Beetle Life Cycle | L. H. Newman, 1965 | "Ingeniously mixes space and time on the horizontal axis." | Encode space + time on the same axis when they correlate. |
| Hannibal Campaign Map | Minard, 1869 | "Refined use of color ... calm, transparent colors." | Transparent flow colors layered over a visible base grid. |
| Lambert's evaporation rate | J.H. Lambert, 1765 | "Most remarkable early ... non-analogical relational graphic." | Plot abstract quantity vs abstract quantity (the modern scatter plot). |
| Consumer Reports reliability | 1982 | "Particularly ingenious mix of table and graphic." | Hybrid table-graphic for multi-variable comparison. |

### How to use this table

When the grader recommends a remedy, name the closest exemplar:

- "Many series, comparable y-axis" → **McRae LA Air Pollutants** (small multiples).
- "Multi-variable on one image" → **Minard's March** (stack 6 variables).
- "Event data on geography" → **Snow's cholera map**.
- "Time-table hybrid" → **Marey Paris-Lyon schedule**.
- "Many numbers in small space" → **NYT NYC Weather History** (181 nrs/in²).
- "Table beats chart" → **Consumer Reports 1982 hybrid**.

---

## Quantitative anchors

Quick-reference numbers cited by page. Use these as concrete targets, not vague ideals.

- **Lie factor** = (visual change %) / (data change %). Acceptable range **0.95-1.05** (VDQI p.57). Worst recorded cases: 14.8 (NYT MPG), 9.4 area / 59.4 volume (TIME barrel).
- **Data-ink ratio** = data-ink / total-ink, equivalently `1.0 - proportion erasable without data loss` (VDQI p.93). Typical default charts: 0.1-0.2. Tufte's redesigns: edit toward ~1.0 (VDQI p.136).
- **Data density** = entries / unit area. 0.15 numbers per square inch is "overwrought" (VDQI p.162). Aim for at least a few per square inch for ordinary work. Tufte's record exemplars reach 110,000-250,000 per square inch (VDQI pp.166-168).
- **Dimensionality** (VDQI p.71): "The number of information-carrying dimensions depicted should not exceed the number of dimensions in the data." 1-D quantity → 1-D encoding (length or position). Never area for 1-D, never volume for 2-D.
- **Tables vs charts**: for ≤20 numbers, default to a table (VDQI p.56). "A table is nearly always better than a dumb pie chart."
- **Aspect ratio**: graphics should generally be wider than tall — "move toward horizontal graphics about 50 percent wider than tall" (VDQI p.190). Golden Rectangle ≈ 1.618 (VDQI p.189).
- **Redundant-ink budget**: in one worked redesign Tufte erased approximately 65% of original ink with zero data loss (VDQI p.101). Most production charts have plenty to give back.
- **Monetary time series**: deflate to real (constant-year) units before plotting. VDQI calls out Fiorina (VDQI p.66) for failing to do this.

---

## Decision tree — from data to genre

Walk this top to bottom on any chart request. Stop at the first match.

1. **≤20 numbers?** → Table (C9). Stop.
2. **Distribution (single variable)?** → Quartile plot (C1).
3. **Two quantitative variables, single series?** → Range-frame scatter (C2). Optional dot-dash marginals (C3).
4. **Many series with same x-axis?** → Small multiples (C5). One panel per series, identical encoding.
5. **Time series, single variable?** → Thin line chart (C10). Direct endpoint label. No legend. No gridlines. Range-frame axes.
6. **Before/after across many categories?** → Slopegraph.
7. **Geographic event data?** → Dotted map on geography (Snow exemplar).
8. **Word-scale, inline?** → Sparkline.

If none of the above fit, you're likely in a genre Tufte didn't endorse. Reconsider whether a chart is the right answer at all.

---

## Reference

Edward Tufte, *The Visual Display of Quantitative Information*, 2nd ed., Graphics Press, 2001. ISBN 978-0961392147. All page numbers cited above refer to this edition.
