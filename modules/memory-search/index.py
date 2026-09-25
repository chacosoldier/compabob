#!/usr/bin/env python3
"""Compabob: memory-search indexer.

Builds a local search index over memory/ and vault/ so the assistant can retrieve
notes by relevance. It always builds a keyword index (SQLite FTS5: exact names,
IDs, and terms rank well). When Ollama is running with an embedding model it also
stores a vector per chunk, and query.py fuses both rankings (hybrid search):
meaning-level matches without losing exact-term matches. Standard library only.

Each chunk carries its heading path ("Project > Risks > Budget"), so a result
says where in the note it came from.

  usage: python3 modules/memory-search/index.py [--keyword]
         --keyword   skip the vectors even if Ollama is available
"""
import json
import sqlite3
import sys
import urllib.request
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = MODULE_DIR.parent.parent
GEN_DIR = MODULE_DIR / "generated"
DB_PATH = GEN_DIR / "index.db"
CONFIG = PROJECT_DIR / "config" / "user.config.yaml"
SOURCES = ["memory", "vault"]
OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
MAX_CHUNK_CHARS = 2000


def ollama_has_embed_model() -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=3) as resp:
            tags = json.load(resp)
        return any(m.get("name", "").split(":")[0] == EMBED_MODEL
                   for m in tags.get("models", []))
    except Exception:  # noqa: BLE001 - any Ollama failure means: no vectors
        return False


def embed(text: str) -> list:
    body = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/embeddings", data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)["embedding"]


def chunk_file(path: Path) -> list:
    """Split a markdown file into (heading path, body) chunks at heading boundaries.

    The heading path is the breadcrumb of enclosing headings, e.g. "Plan > Risks".
    Lines inside fenced code blocks are never treated as headings.
    """
    text = path.read_text(encoding="utf-8", errors="ignore")
    chunks, stack, buf, in_fence = [], [], [], False

    def flush():
        body = "\n".join(buf).strip()
        if body:
            crumb = " > ".join(title for _, title in stack)
            for i in range(0, len(body), MAX_CHUNK_CHARS):
                chunks.append((crumb, body[i:i + MAX_CHUNK_CHARS]))

    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        level = len(line) - len(line.lstrip("#"))
        if not in_fence and 1 <= level <= 6 and line[level:level + 1] == " ":
            flush()
            buf = []
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, line[level:].strip()))
        else:
            buf.append(line)
    flush()
    return chunks


def gather() -> list:
    docs = []
    for src in SOURCES:
        root = PROJECT_DIR / src
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.md")):
            rel = str(path.relative_to(PROJECT_DIR))
            for heading, body in chunk_file(path):
                docs.append((rel, heading, body))
    return docs


def fts5_available() -> bool:
    try:
        sqlite3.connect(":memory:").execute("CREATE VIRTUAL TABLE t USING fts5(x)")
        return True
    except sqlite3.OperationalError:
        return False


def build(docs: list, with_vectors: bool, with_fts: bool) -> int:
    """Write the index. Returns how many chunks got a vector."""
    DB_PATH.unlink(missing_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT)")
    con.execute("CREATE TABLE docs(id INTEGER PRIMARY KEY, path TEXT, heading TEXT, body TEXT)")
    con.executemany("INSERT INTO docs(path,heading,body) VALUES(?,?,?)", docs)
    if with_fts:
        con.execute("CREATE VIRTUAL TABLE fts USING fts5(path, heading, body, tokenize='porter')")
        con.execute("INSERT INTO fts(rowid,path,heading,body) SELECT id,path,heading,body FROM docs")
    embedded = 0
    if with_vectors:
        con.execute("CREATE TABLE vecs(id INTEGER PRIMARY KEY, vec TEXT)")
        rows = con.execute("SELECT id,path,heading,body FROM docs").fetchall()
        for doc_id, path, heading, body in rows:
            try:
                vec = embed(f"{heading}\n{body}" if heading else body)
            except Exception as exc:  # noqa: BLE001 - any Ollama failure means: no vectors
                print(f"  warn: no vector for a chunk of {path} ({exc})")
                continue
            con.execute("INSERT INTO vecs VALUES(?,?)", (doc_id, json.dumps(vec)))
            embedded += 1
            print(f"  embedded {embedded}/{len(rows)}", end="\r")
        print()
    backend = "hybrid" if with_fts and embedded else ("semantic" if embedded else "keyword")
    con.execute("INSERT INTO meta VALUES('backend',?)", (backend,))
    con.commit()
    con.close()
    return embedded


def mark_enabled() -> None:
    """Flip memory_search to true in the user config, if it exists."""
    if not CONFIG.exists():
        return
    lines = CONFIG.read_text(encoding="utf-8").splitlines()
    out, flipped = [], False
    for ln in lines:
        if not flipped and ln.lstrip().startswith("memory_search:") and "false" in ln:
            out.append(ln.replace("false", "true", 1))
            flipped = True
        else:
            out.append(ln)
    if flipped:
        CONFIG.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> int:
    skip_vectors = "--keyword" in sys.argv[1:]
    GEN_DIR.mkdir(parents=True, exist_ok=True)

    docs = gather()
    if not docs:
        print("Nothing to index. Run ./setup.sh first so memory/ and vault/ exist.")
        return 1

    with_vectors = (not skip_vectors) and ollama_has_embed_model()
    with_fts = fts5_available()
    if not with_fts and not with_vectors:
        print("This Python's SQLite has no FTS5, and Ollama is not available, so "
              "no index can be built. Install Ollama (see "
              "docs/how-to-improve-memory.md) or use a Python with FTS5.")
        return 1

    if with_vectors:
        print(f"Ollama found. Indexing {len(docs)} chunks with keywords and vectors. "
              "The first run can take a minute...")
    else:
        print(f"Indexing {len(docs)} chunks (keyword)...")
    embedded = build(docs, with_vectors, with_fts)

    mark_enabled()
    backend = "hybrid (keyword + meaning)" if with_fts and embedded else (
        "semantic (meaning only; this SQLite has no FTS5)" if embedded else "keyword (FTS5 ranked search)")
    print(f"Done. Indexed {len(docs)} chunks from memory/ and vault/.")
    print(f"Backend: {backend}.")
    print(f"Index:   {DB_PATH.relative_to(PROJECT_DIR)}")
    if not with_vectors and not skip_vectors:
        print("Tip: install Ollama to add search by meaning. See docs/how-to-improve-memory.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
