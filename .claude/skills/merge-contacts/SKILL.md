---
name: merge-contacts
description: Merge the user's contact exports (Google Takeout, LinkedIn export, vault People notes) into one local CRM. Use for "/merge-contacts", "build my CRM", "dedup my contacts", or when another workflow needs a clean contacts source of truth.
---

# Merge Contacts

Build the user's local CRM source of truth with the `crm-merge` module. The
module does the work; your job is to find their exports, run it with the right
flags, and report what merged. Never invent data, never call an external CRM.

## Steps

1. **Find the exports.** Check, in order:
   - A Google Takeout zip in `~/Downloads` (name contains "takeout" or
     "google"). The script auto-finds the newest one, but confirm it exists.
   - A LinkedIn export folder (contains `Connections.csv`, ideally
     `messages.csv`). Ask the user for the path if you cannot find it.
   - `vault/People/` for per-person notes (optional).
   If none exist, point the user at the setup steps in
   `modules/crm-merge/README.md` (both exports are self-service downloads) and stop.

2. **Get their name** for message-frequency counting. Ask how their name appears
   in LinkedIn messages (the "me" side), or read it from `config/user.config.yaml`.

3. **Run the build:**
   ```bash
   python3 modules/crm-merge/build.py \
     --takeout-zip <path-or-omit-to-autofind> \
     --linkedin-dir <folder> \
     --me "<their name>" \
     --out data/crm-merge
   ```
   Omit any source they do not have; one source alone is fine.

4. **Report** the counts the script prints: total unique people, how many appear
   in 2+ sources (the high-confidence merges), and how many link to a vault note.
   Flag if a source loaded zero records, since that usually means a wrong path.

5. **Point them onward.** Tell them `data/crm-merge/browser.html` is openable in
   any browser, and that `contacts.json` is what `/build-list` dedups against.

## Watch out for

- **Over-merging on a common name:** if the user says distinct people got fused,
  lower `--name-collision-threshold` and re-run.
- **Zero LinkedIn messages counted:** the `--me` name probably does not match the
  export. Check the `FROM`/`TO` values in `messages.csv` and pass the exact form.
- **Privacy:** outputs are git-ignored; do not commit them or paste contact data
  into anything outward-facing.
