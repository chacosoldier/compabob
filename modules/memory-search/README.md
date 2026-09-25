# Module: Memory Search

**Status: available.**

Better retrieval over `memory/` and `vault/`. By default the assistant finds
notes with keyword `Grep`. This module adds a real index so it can retrieve by
*relevance*, and, with Ollama, by *meaning*.

## What it adds

- An index over every note in `memory/` and `vault/`, built by a skill you run.
- **Keyword search, always** (SQLite FTS5): ranked, stemmed full-text search.
  Zero setup, no dependencies, ships with Python. Exact names and IDs rank well.
- **Plus search by meaning, with [Ollama](https://ollama.com)**: if it is
  running with an embedding model, every chunk also gets a vector, and each
  query ranks the notes both ways and merges the two lists (hybrid search).
  "Which vendor is building our new site" finds the note about the agency even
  if it never says "vendor", while an exact name still lands first.
- Each result shows where in the note it came from ("Project > Risks > Budget").
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

Re-run `/index-memory`. It detects Ollama and adds vectors to the keyword
index. If Ollama is off when you search, the search uses keywords only and says
so. The model runs locally; nothing leaves your machine. Full walkthrough:
`docs/how-to-improve-memory.md`.

## Keep it fresh

The index is a snapshot. Re-run `/index-memory` after a burst of note-taking.
To refresh it automatically, schedule the indexer, for example a daily cron
line:

```text
0 7 * * *  cd /path/to/compabob && python3 modules/memory-search/index.py
```

`index.py --keyword` skips the vectors even when Ollama is available.

## How it works

- `index.py` chunks each note at heading boundaries (keeping the heading path)
  and stores the chunks in a local SQLite database at
  `modules/memory-search/generated/index.db` (git-ignored).
- `query.py "<question>"` returns the most relevant chunks. With vectors, it
  merges the keyword ranking and the meaning ranking with reciprocal rank
  fusion. The `second-brain` agent calls it before falling back to `Grep`.
- Python standard library only. Vectors come from a local Ollama over HTTP, so
  there are no Python packages to install. Vector scoring stays fast up to
  roughly 20,000 chunks.

## Disable it

Delete `modules/memory-search/generated/index.db` and set `memory_search: false`
in `config/user.config.yaml`. The assistant falls back to `Grep`.
