# Module: Memory Search

**Status: available.**

Better retrieval over `memory/` and `vault/`. By default the assistant finds
notes with keyword `Grep`. This module adds a real index so it can retrieve by
*relevance*, and, with Ollama, by *meaning*.

## What it adds

- An index over every note in `memory/` and `vault/`, built by a skill you run.
- Two backends, chosen automatically:
  - **Keyword (FTS5)**: the default. Ranked, stemmed full-text search. Zero
    setup, no dependencies, ships with Python.
  - **Semantic**: if [Ollama](https://ollama.com) is running with an embedding
    model, retrieval works by meaning: "what did we decide about pricing" finds
    the right note even if it never used the word "pricing".
- The `second-brain` agent queries the index automatically once it exists.

## Enable it

Run the `/index-memory` skill from inside a session, or directly:

```bash
python3 modules/memory-search/index.py
```

That is the whole setup for the keyword backend. The module then reports as
enabled (`memory_search: true` in `config/user.config.yaml`).

## Semantic search (optional)

For search-by-meaning, install [Ollama](https://ollama.com) and pull an
embedding model, once:

```bash
ollama pull nomic-embed-text
```

Re-run `/index-memory`. It detects Ollama and builds a semantic index instead.
The model runs locally; nothing leaves your machine. Full walkthrough:
`docs/how-to-improve-memory.md`.

## Keep it fresh

The index is a snapshot. Re-run `/index-memory` after a burst of note-taking.
To refresh it automatically, schedule the indexer, for example a daily cron
line:

```text
0 7 * * *  cd /path/to/compabob && python3 modules/memory-search/index.py
```

`index.py --keyword` forces the keyword backend even when Ollama is available.

## How it works

- `index.py` chunks each note at heading boundaries and stores the chunks in a
  local SQLite database at `modules/memory-search/generated/index.db`
  (git-ignored).
- `query.py "<question>"` returns the most relevant chunks. The `second-brain`
  agent calls it before falling back to `Grep`.
- Python standard library only. The semantic backend talks to a local Ollama
  over HTTP, so there are no Python packages to install.

## Disable it

Delete `modules/memory-search/generated/index.db` and set `memory_search: false`
in `config/user.config.yaml`. The assistant falls back to `Grep`.
