#!/usr/bin/env python3
"""Compabob: memory-search indexer.

Builds a local search index over memory/ and vault/ so the assistant can retrieve
notes by relevance, not just exact keyword. If Ollama is running with an embedding
model the index is semantic (search by meaning); otherwise it falls back to
SQLite FTS5 (fast ranked keyword search). Python standard library only.

  usage: python3 modules/memory-search/index.py [--keyword]
         --keyword   force the keyword (FTS5) backend even if Ollama is available
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
    except Exception:
        return False


def embed(text: str) -> list:
    body = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/embeddings", data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)["embedding"]


def chunk_file(path: Path) -> list:
    """Split a markdown file into (heading, body) chunks at heading boundaries."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    chunks, heading, buf = [], "", []

    def flush():
        body = "\n".join(buf).strip()
        if body:
            for i in range(0, len(body), MAX_CHUNK_CHARS):
                chunks.append((heading, body[i:i + MAX_CHUNK_CHARS]))

    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            flush()
            heading = line.lstrip("#").strip()
            buf = []
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


def build_keyword(docs: list) -> None:
    DB_PATH.unlink(missing_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT)")
    con.execute("INSERT INTO meta VALUES('backend','keyword')")
    con.execute("CREATE VIRTUAL TABLE chunks USING fts5("
                "path, heading, body, tokenize='porter')")
    con.executemany("INSERT INTO chunks(path,heading,body) VALUES(?,?,?)", docs)
    con.commit()
    con.close()


def build_semantic(docs: list) -> None:
    DB_PATH.unlink(missing_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT)")
    con.execute("INSERT INTO meta VALUES('backend','semantic')")
    con.execute("CREATE TABLE chunks(path TEXT, heading TEXT, body TEXT, vec TEXT)")
    done = 0
    for path, heading, body in docs:
        text = f"{heading}\n{body}" if heading else body
        try:
            vec = json.dumps(embed(text))
        except Exception as exc:
            print(f"  warn: skipped a chunk of {path} ({exc})")
            continue
        con.execute("INSERT INTO chunks VALUES(?,?,?,?)", (path, heading, body, vec))
        done += 1
        print(f"  embedded {done}/{len(docs)}", end="\r")
    print()
    con.commit()
    con.close()


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
    force_keyword = "--keyword" in sys.argv[1:]
    GEN_DIR.mkdir(parents=True, exist_ok=True)

    docs = gather()
    if not docs:
        print("Nothing to index. Run ./setup.sh first so memory/ and vault/ exist.")
        return 1

    use_semantic = (not force_keyword) and ollama_has_embed_model()
    if not use_semantic and not fts5_available():
        print("This Python's SQLite has no FTS5, and Ollama is not available, so "
              "no index can be built. Install Ollama (see "
              "docs/how-to-improve-memory.md) or use a Python with FTS5.")
        return 1

    if use_semantic:
        print(f"Ollama found. Building a semantic index ({len(docs)} chunks). "
              "First run can take a minute...")
        build_semantic(docs)
        backend = "semantic (search by meaning)"
    else:
        print(f"Building a keyword index ({len(docs)} chunks)...")
        build_keyword(docs)
        backend = "keyword (FTS5 ranked search)"

    mark_enabled()
    print(f"Done. Indexed {len(docs)} chunks from memory/ and vault/.")
    print(f"Backend: {backend}.")
    print(f"Index:   {DB_PATH.relative_to(PROJECT_DIR)}")
    if not use_semantic and not force_keyword:
        print("Tip: install Ollama for semantic search. See docs/how-to-improve-memory.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
