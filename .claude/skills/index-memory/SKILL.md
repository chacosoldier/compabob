---
name: index-memory
description: Build or refresh the local memory-search index over memory/ and vault/, so retrieval finds notes by relevance. Use for "/index-memory", "reindex my memory", "rebuild the search index".
---

# Index Memory

Builds the local search index that the memory-search module uses. Run it after a
burst of note-taking, or on a schedule.

## Steps

1. Run the indexer:
   `python3 modules/memory-search/index.py`
2. Report back: how many chunks were indexed, and which backend it used.
   **Hybrid** means keyword search plus search by meaning (Ollama with an
   embedding model is running). **Keyword** means FTS5 ranked search alone, the
   zero-setup default.
3. If it used the keyword backend and the user wants search by meaning, point
   them to `docs/how-to-improve-memory.md` for the one-time Ollama setup.

Once the index exists, the `second-brain` agent queries it automatically when
retrieving notes. To keep it current, re-run this skill, or schedule it (see
`modules/memory-search/README.md`).
