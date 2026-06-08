---
name: build-list
description: Build a ranked, CRM-deduped outbound prospect list from an ICP description. Use for "/build-list", "find me leads matching X", "build a prospect list for Y", or when the user wants a scored outbound list. Orchestrates discovery + the lead-pipeline module + enrichment.
---

# Build List

Turn an ICP description into a ranked, deduped, CRM-aware outbound list using the
`lead-pipeline` module. You run the judgement/IO steps (discover, enrich); the
script runs the deterministic steps (clean, dedup, score). The cardinal rule:

> **Dedup against the CRM before enriching.** Never spend enrichment effort or
> credits on accounts the user already knows. Known accounts become warm intros.

## Preconditions

- A CRM to dedup against: `data/crm-merge/contacts.json`. If it is missing, tell
  the user to run `/merge-contacts` first (dedup is the whole point); offer to
  proceed without it only if they insist, noting every lead will be `proceed`.
- An ICP rubric at `modules/lead-pipeline/icp.json`. If only `icp.example.json`
  exists, copy it and adjust it to the user's request before scoring.

## Steps

1. **Read the ICP from the request.** Pull out: industry/segment, geography,
   company-size band, and target buyer titles. Confirm anything ambiguous in one
   short question rather than guessing.

2. **Discover candidates → raw CSV.** Use the web-search MCP (e.g. exa
   `web_search_exa` / `linkedin_search_exa`) to find matching accounts. Write a
   CSV to `reports/lead-pipeline/00-raw.csv` with whatever you found across these
   columns: `company, domain, contact_name, contact_email, title, country`
   (partial rows are fine; later stages fill gaps). If no search MCP is
   available, ask the user for a raw CSV and skip to step 3.

3. **Clean** (script):
   ```bash
   python3 modules/lead-pipeline/pipeline.py clean \
     --in reports/lead-pipeline/00-raw.csv \
     --out reports/lead-pipeline/01-cleaned.csv --country <codes>
   ```

4. **Dedup against the CRM** (script):
   ```bash
   python3 modules/lead-pipeline/pipeline.py dedup \
     --in reports/lead-pipeline/01-cleaned.csv \
     --crm data/crm-merge/contacts.json \
     --out reports/lead-pipeline/02-deduped.csv
   ```
   Report the split: how many `proceed` (cold), `warm` (known account, route via
   `crm_known_contact`), `skip` (already known, drop from outbound).

5. **Enrich the survivors only.** For rows tagged `proceed` or `warm` that lack a
   domain / email / decision-maker, enrich with whatever you have, in this order:
   - web search MCP for the company domain + LinkedIn (high hit-rate, cheap),
   - an enrichment provider MCP (e.g. Clay) for verified emails — check remaining
     credits first, and only for rows still missing an email,
   - public business registries for named decision-makers at small firms when
     enrichment misses.
   Never enrich `skip` rows. Write the enriched result back to
   `reports/lead-pipeline/02-deduped.csv` (or a `02b-enriched.csv`).

6. **Score** (script):
   ```bash
   python3 modules/lead-pipeline/pipeline.py score \
     --in reports/lead-pipeline/02-deduped.csv \
     --icp modules/lead-pipeline/icp.json \
     --out reports/lead-pipeline/03-scored.csv --top 50
   ```

7. **Hand back** the ranked top-N (path `reports/lead-pipeline/04-top-*.csv`),
   the disposition split, and the tier distribution. Call out the `warm`
   accounts explicitly: those are the highest-value, lowest-risk plays.

## Guardrails

- Do not send anything. This builds a list; outreach is a separate, reviewed step
  (see the `linkedin-outreach` module).
- Respect data-protection law and platform terms. Flag if the user's target list
  looks like scraped personal data being repurposed for cold mail.
- If a stage's numbers look wrong (e.g. zero `skip`/`warm` with a populated CRM),
  inspect the stage CSV before continuing — that is why each stage is a file.
- Be honest about enrichment misses; report the hit-rate rather than fabricating
  emails.
