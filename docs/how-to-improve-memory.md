# How to improve memory

The assistant's memory compounds on its own as you use it. This is how to make it
sharper, and how to add search-by-meaning.

## The memory you already have

- `memory/MEMORY.md` is a short index, loaded at the start of every session.
- Durable facts live one per file in `memory/topics/`, linked from the index.
- The assistant writes a memory when you tell it to, when the same thing gets
  looked up across sessions, when you correct it, or when a hard problem is
  worth not repeating. See the constitution's Memory System section.

Feed it well: correct mistakes and ask it to remember the correction; run
`/reflect` at the end of a real working session to capture what was learned;
keep `MEMORY.md` short and let detail live in topic files.

## Sharper retrieval: the memory-search module

By default the assistant finds notes with keyword search (`Grep`). That is fine
for a small vault. As `memory/` and `vault/` grow, enable the **memory-search**
module for ranked, and optionally semantic, retrieval.

### Step 1: build the index

Run the `/index-memory` skill, or:

```bash
python3 modules/memory-search/index.py
```

That builds a keyword index (SQLite FTS5: ranked, stemmed, no setup). The
`second-brain` agent uses it automatically from then on. Re-run it after a burst
of note-taking to keep it current.

### Step 2: add search by meaning (optional)

Keyword search still needs the right word. Semantic search finds a note by
*meaning*: ask "what did we decide about pricing" and it finds the note even if
that note never said "pricing".

It needs a local embedding model via [Ollama](https://ollama.com). One time:

```bash
# install Ollama from https://ollama.com, then:
ollama pull nomic-embed-text
```

Re-run `/index-memory`. It detects Ollama and adds a vector to every chunk.
Searches then rank notes both by keywords and by meaning and merge the two
lists, so you gain meaning-level matches without losing exact names. The model
runs locally; nothing leaves your machine.

### Doing it proactively

The index is a snapshot, so refresh it. Either re-run `/index-memory` yourself,
or schedule it. A daily cron line:

```text
0 7 * * *  cd /path/to/compabob && python3 modules/memory-search/index.py
```

memory-search stays opt-in and lightweight on purpose: it is a skill you run,
not a daemon the kit forces on you.

## What a memory worth keeping looks like

The best memories are lessons that would otherwise be learned twice. A few from the
setup this kit is distilled from, each one paid for with a real mistake. They are
good examples of the shape (one fact, the reason, when it applies), and worth
knowing if you write your own hooks:

- **An empty search result is a question, not an answer.** "No note about X" first
  means "check the folder, the spelling, and whether the index is current", and only
  then "X never happened".
- **A check that should never fire needs proof it can fire.** Before trusting "zero
  blocked", feed the guard one case it must block and watch it block.
- **A Stop hook reads the reply from its input, not the transcript.** The hook can
  run before the transcript has the final reply written, so reading the transcript
  checks the previous reply. `hooks/hook-style-gate.py` reads `last_assistant_message`.
- **A hook's `systemMessage` is shown to you, never to the assistant.** To tell the
  assistant something, print it (SessionStart and UserPromptSubmit hooks), or use
  `additionalContext` or a block reason.
- **A hook added to `.claude/settings.json` applies in the session that is already
  running.** Test a new guard in a fresh session before relying on it, but do not
  assume the current one is unaffected.

When the assistant finishes a hard problem, ask: "is there a lesson here that would
save us from repeating this?" If yes, that is a topic file.
