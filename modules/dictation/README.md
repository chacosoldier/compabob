# Module: Dictation (cleanup + a glossary that learns)

Dictate anywhere on your machine and get back clean text in **your** vocabulary.
A local dictation app captures speech to text; this module sits in front of the
language-cleanup step, fixing punctuation and fillers and rewriting the words it
keeps getting wrong (your name, your company, your jargon) into the spellings you
actually use. A nightly loop watches the corrections it makes and folds the
recurring ones into a glossary, so it gets more right over time without you
maintaining a word list by hand.

Raw speech-to-text is the highest-friction, lowest-fidelity context you feed an
assistant: it mangles proper nouns and drops the punctuation that carries
meaning. This module is the cheapest fix. It is opt-in like everything here.

## How it works

Your dictation app does the speech-to-text locally, then POSTs the raw
transcript to an **OpenAI-compatible cleanup endpoint** for a final pass. This
module *is* that endpoint:

- `proxy.py` listens on `127.0.0.1:8765` (`POST /v1/chat/completions` +
  `GET /health`). It takes your transcript, prepends `prompts/cleanup.md` plus
  your rendered `glossary.yaml`, forwards it to an upstream LLM you configure,
  and returns the cleaned text. It **never blocks the paste**: if the upstream
  is down, the key is missing, or the kill switch is off, it hands back the raw
  transcript unchanged. Every request is logged to `data/dictation/calls.jsonl`.
- `learn.py` reads that log, diffs `raw → cleaned` for 1-to-1 word
  substitutions, and once a substitution recurs enough (4× by default, ≥90%
  consistent) it appends it to `glossary.yaml.corrections` so the proxy applies
  it directly from then on. The proxy reads the glossary fresh on every request,
  so promotions take effect with no restart.

## Prerequisites

```bash
pip3 install pyyaml                      # the only dependency
```

A local dictation app that supports an OpenAI-compatible post-processing
endpoint. The reference is **[Handy](https://github.com/cjpais/Handy)** (free,
open source, local STT on macOS/Windows/Linux), but anything with the same hook
works.

An upstream cleanup model. Two good options:

- **Groq** (default): free API key at <https://console.groq.com>. Fast and
  high quality. Cloud — see Privacy below.
- **Ollama** (local, no key, text never leaves your machine):
  `ollama pull llama3.1:8b`, then point the upstream at
  `http://localhost:11434/v1`.

## Set it up

```bash
cp modules/dictation/.env.example modules/dictation/.env
cp modules/dictation/glossary.example.yaml modules/dictation/glossary.yaml
```

Edit `.env` and set `DICTATION_UPSTREAM_KEY` (for Groq) or switch the
`DICTATION_UPSTREAM_BASE/MODEL` block to Ollama. Then start the proxy:

```bash
python3 modules/dictation/proxy.py
curl -s http://127.0.0.1:8765/health      # -> {"status": "ok"}
```

### Point your dictation app at the proxy

In Handy's settings, set the AI / LLM post-processing endpoint to an
OpenAI-compatible base URL of **`http://127.0.0.1:8765/v1`**. The model name and
API key fields can be anything (the proxy ignores them and uses your `.env`).
Handy sends `reasoning_effort:"none"`, which some models reject; the proxy drops
that field structurally, so it just works.

## Glossary format

`glossary.yaml` (gitignored — it is your personal vocabulary) has three keys:

```yaml
version: 0              # int, bumped by learn.py on every promotion
terms:                  # canonical spellings to PREFER for similar-sounding words
  - Acme Corp
  - PostgreSQL
corrections:            # explicit wrong -> right mappings (strongest signal)
  - wrong: [sequel, sea quel]   # one or more observed mis-transcriptions (lowercased)
    right: SQL
    source: seed                 # "seed" (you) | "learned" (learn.py)
    occurrences: 0
    added: "2026-01-01T00:00:00" # set by learn.py on promotion
```

- `terms` you maintain by hand. `corrections` you can also hand-edit, but
  `learn.py` grows them for you.
- `learn.py` only ever **appends** `source: learned` corrections; it never
  rewrites your `terms` or `seed` entries. A learned correction is added only
  when its `right` is not already a correction target and it clears
  `LEARN_MIN_OCCURRENCES` + `LEARN_MIN_CONSISTENCY` (in `.env`).

## Use the learning loop

```bash
python3 modules/dictation/learn.py --report     # candidate table, no writes
python3 modules/dictation/learn.py --dry-run    # what it would promote, no writes
python3 modules/dictation/learn.py              # promote + prune old log rows
```

Set `DICTATION_AUTO_PROMOTE=0` to make it propose-only (log candidates to
`data/dictation/promotions.log`, never touch the glossary). It learns from the
*model's own* corrections, not from your post-edits, so the manual escape hatch
is always editing `glossary.yaml` directly.

## Schedule it (optional)

```bash
bash modules/dictation/install.sh
```

This GENERATES the scheduler files (a KeepAlive launchd job for the proxy, a
nightly one for `learn.py`) under `modules/dictation/generated/` and prints the
command to activate them. It never touches your scheduler on its own. macOS uses
launchd; Linux gets a cron line for the learning loop plus a note on running the
proxy as a background service.

## Enable it

1. Do the setup above and confirm `/health` responds.
2. Point your dictation app at `http://127.0.0.1:8765/v1`.
3. Set `dictation: true` in `config/user.config.yaml` so `/system-audit` checks it.

## Known issues

- **Cleanup looks like it did nothing.** That is the fail-open path: a missing
  key or an unreachable upstream returns the raw transcript at HTTP 200. Check
  `data/dictation/calls.jsonl` — a `"success": false` row tells you the upstream
  failed. The proxy logs the upstream error to stderr (`reports/dictation/proxy.err`
  if scheduled).
- **Turn cleanup off without uninstalling.** Set `DICTATION_ENABLED=0` in `.env`;
  the proxy becomes a pure pass-through with zero LLM calls. No restart needed.
- **Wrong words still slip through.** They will until `learn.py` sees them enough
  times, or you add them to `glossary.yaml` by hand. Lower `LEARN_MIN_OCCURRENCES`
  if you want faster (noisier) learning.

## A note on privacy

`proxy.py` binds to `127.0.0.1` only. Your raw and cleaned text are written to
`data/dictation/calls.jsonl`, which is gitignored; `learn.py` prunes rows older
than `LEARN_RETENTION_DAYS` (30 by default). The cleanup text **is** sent to
whatever upstream you configure: the default Groq is a cloud service, so your
dictation passes through it. If that matters, use the Ollama option and nothing
leaves your machine. Your `glossary.yaml` is also gitignored — treat the names
and jargon in it as personal data.
