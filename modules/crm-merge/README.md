# Module: CRM merge

Folds your scattered contact exports into **one local source of truth**: a
SQLite database, a JSON file, and a self-contained HTML browser you can open
offline. No external CRM, no API keys, no data leaving your machine.

It merges three sources, deduping people who appear in more than one:

- **Google Contacts** (from a Google Takeout zip)
- **LinkedIn Connections + message history** (from a LinkedIn data export)
- **Your vault `People/` notes** (optional)

## Why own your contacts

Your network lives split across LinkedIn, your phone, your inbox, and your CRM
vendor, each with a partial, slightly-wrong copy. The moment you want to "email
everyone I know at a fintech" or "check if we already know someone at this
account," you are stitching exports by hand. This module does that stitch once,
locally, and gives you a file you control. It is also the **dedup backbone**
the `lead-pipeline` module needs: you cannot "dedup a prospect list against your
CRM" until you have a clean CRM.

## The hard part it gets right: identity resolution

The same person shows up as `j.smith@acme.com` in Google, `linkedin.com/in/jsmith`
on LinkedIn, and `John Smith.md` in your notes. Naive dedup either misses these
(three rows for one person) or over-merges (every "John Smith" fused into one).

This module uses **union-find on three identity keys** — verified email,
LinkedIn slug, and normalized name — so any shared key links records
transitively into one person. A **common-name guard** stops it merging on a name
that too many records share (the generic-name trap), while exact keys (email,
slug) always merge. This is the entity-resolution problem every CRM-hygiene
project hits, and the part most hand-rolled scripts get wrong.

The merged record keeps the fullest name, the union of emails/phones, and the
strongest relationship signal (LinkedIn message count) to rank who you actually
know well.

## Setup

No credentials. You supply two self-service exports:

1. **Google Takeout** — https://takeout.google.com → select **Contacts**
   (vCard format) → download the zip. Leave it in `~/Downloads` and the script
   finds it, or pass `--takeout-zip <path>`.
2. **LinkedIn export** — LinkedIn → Settings & Privacy → Data privacy →
   *Get a copy of your data* → include **Connections** and **Messages**. Unzip
   it into a folder and pass `--linkedin-dir <folder>`. (LinkedIn emails the
   archive; it can take minutes to a day.)
3. **Vault notes** — optional; defaults to `vault/People/`.

Either source alone works; you do not need all three.

## Use it

```bash
python3 modules/crm-merge/build.py \
  --takeout-zip ~/Downloads/takeout-20260608.zip \
  --linkedin-dir ~/Downloads/linkedin-export \
  --me "Your Full Name" \
  --out data/crm-merge
```

`--me` is how the script tells you from the other party in your LinkedIn
messages, so it can count message frequency per contact. Pass the name(s)
exactly as they appear in the export, comma-separated if you have more than one.

Outputs land in `data/crm-merge/` (git-ignored):

- `contacts.db` — query it with any SQLite tool, or let the `crm-relationships`
  agent read it.
- `contacts.json` — what the `lead-pipeline` module dedups against.
- `browser.html` — open in a browser: search, filter by source, click a person
  for full detail. Fully offline, all data inlined.

Re-run any time. It is idempotent: it rebuilds from scratch, so re-exporting and
re-running keeps your source of truth current.

## Or just ask your assistant

Run the `/merge-contacts` skill in a session and it will check which exports you
have, run the build with the right flags, and report what merged.

## Tuning the merge

If you have an unusually common name in your network and see over-merging, lower
`--name-collision-threshold` (default 30). If distinct people are not merging,
it is almost always because neither shares an email nor a LinkedIn slug and their
names differ; add the missing identifier to one source and re-run.

## Pairs with

- **`crm-relationships` agent** — reads `contacts.db` to answer "who do I know
  at X" and to track interactions.
- **`lead-pipeline` module** — dedups new prospect lists against `contacts.json`
  so you never enrich or cold-email someone you already know.

## A note on privacy

Everything stays local. The HTML browser inlines your data into one file with no
network calls; treat that file like the contact list it is. Outputs are
git-ignored by default so you never commit your network to a repo.
