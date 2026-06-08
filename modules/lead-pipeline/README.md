# Module: Lead pipeline

Turns a raw list of candidate accounts into a **ranked, deduped, CRM-aware
outbound list** through staged steps, writing one CSV per stage so you can
inspect or hand-fix the work at any point.

```
discover  ->  clean  ->  dedup-against-CRM  ->  enrich  ->  score  ->  top-N
 (assistant)  (script)      (script)          (assistant)  (script)
```

The teachable insight, and the reason this beats a one-shot "find me leads"
prompt:

> **Dedup against your CRM before you enrich.** You never spend enrichment
> credits on a company you already know, and you never cold-email a person who
> is already a relationship or an open deal. The known accounts become *warm*
> intros instead of cold ones.

This is the workflow most teams do by hand in a spreadsheet. Here it is a
resumable pipeline.

## How the work splits

Two of the steps need judgement and live tools, so your **assistant** runs them
with MCP servers. Three steps are pure logic, so a **script** (`pipeline.py`)
runs them deterministically:

| Stage | Who | What |
|-------|-----|------|
| discover | assistant (web search MCP) | find candidate accounts, write a raw CSV |
| **clean** | `pipeline.py clean` | normalize, drop junk, dedup within the list |
| **dedup** | `pipeline.py dedup` | tag each row `proceed` / `warm` / `skip` vs your CRM |
| enrich | assistant (enrichment MCP / public registry) | fill domains, emails, decision-maker names |
| **score** | `pipeline.py score` | ICP fit score + A/B/C tier + ranked top-N |

The `/build-list` skill orchestrates the whole chain. You can also run the
script stages by hand.

## The three dispositions

`pipeline.py dedup` compares each lead against your CRM (the `contacts.json`
that the `crm-merge` module produces) and tags it:

- **`skip`** — you already know this exact person (email match). Do not
  cold-outreach; they are a relationship, not a lead.
- **`warm`** — you know *someone else* at this account (matched by corporate
  email domain or company name). Do not cold-email a stranger here; route the
  approach through the contact you already have. The matched contact's name is
  written to the `crm_known_contact` column.
- **`proceed`** — genuinely cold, no match. Fair game for outbound.

Free webmail domains (gmail, gmx, ...) are ignored as account signals so a
personal email never fakes a company match.

## Setup

1. **Build your CRM first** (so dedup has something to match against):
   ```bash
   python3 modules/crm-merge/build.py --out data/crm-merge   # see that module's README
   ```
   You can skip this, but then every lead is `proceed` and you lose the whole
   point of the pipeline.

2. **Define your ICP.** Copy the rubric and edit it for your market:
   ```bash
   cp modules/lead-pipeline/icp.example.json modules/lead-pipeline/icp.json
   ```
   It is plain JSON: target countries, buyer-title keywords, and how many points
   each signal is worth. Tune the numbers to your taste.

3. **Optional, for richer discovery/enrichment**, enable MCP servers via
   `bash scripts/install-integrations.sh`:
   - **exa** (`search` category) — web/firmographic discovery. Free tier exists.
     This is the minimum useful add-on.
   - An enrichment provider (e.g. a Clay MCP) — verified emails and
     decision-maker names. Optional; uses your own account/credits.

   No MCP at all still works: bring your own raw CSV and the script stages clean,
   dedup, and score it.

## Use it (by hand)

Starting from a raw CSV with any of these columns (`company`, `domain`,
`contact_name`, `contact_email`, `title`, `country`; extras are preserved):

```bash
python3 modules/lead-pipeline/pipeline.py clean \
  --in raw.csv --out reports/lead-pipeline/01-cleaned.csv --country DE,BR

python3 modules/lead-pipeline/pipeline.py dedup \
  --in reports/lead-pipeline/01-cleaned.csv \
  --crm data/crm-merge/contacts.json \
  --out reports/lead-pipeline/02-deduped.csv

python3 modules/lead-pipeline/pipeline.py score \
  --in reports/lead-pipeline/02-deduped.csv \
  --icp modules/lead-pipeline/icp.json \
  --out reports/lead-pipeline/03-scored.csv --top 50
```

Each stage prints a summary (rows in/out, disposition split, tier distribution)
and writes its CSV to `reports/lead-pipeline/` (git-ignored). The enrich step
goes between `dedup` and `score`: enrich only the `proceed` and `warm` rows, so
you never pay to enrich a `skip`.

## Or just ask your assistant

```
/build-list  fintech companies in Germany, 10-200 employees, head of revenue
```

The skill runs discovery, calls the script for clean + dedup, enriches the
survivors with whatever MCP you have, scores, and hands you the ranked top-N
plus the disposition breakdown.

## On enrichment quality (set expectations)

Enrichment hit-rate varies sharply by market. In well-covered regions (DE, US,
UK, BR, CA) expect a strong majority of `proceed` rows to come back with a
verified email or a named decision-maker. In thinner markets, expect to fall
back to public business registries or manual research for the long tail. Scope
your list to the markets that enrich well first, or budget more time for the
rest. Check your enrichment provider's remaining credits before a bulk run.

## A note on outbound responsibility

This module builds a list; it does not send anything. Respect GDPR/CAN-SPAM and
platform terms when you act on it. The `warm` tag exists precisely so your best
accounts get a real, consented intro rather than a cold blast.

## Pairs with

- **`crm-merge` module** — produces the `contacts.json` this dedups against.
- **`linkedin-outreach` module** — feed `warm` and high-tier `proceed` rows into
  your connection queue.
- **`crm-relationships` agent** — for `warm` rows, ask it who your existing
  contact at the account is and how to route the intro.
