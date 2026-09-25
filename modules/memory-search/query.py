#!/usr/bin/env python3
"""Compabob: memory-search query.

Searches the index built by index.py and prints the most relevant chunks, best
match first. The second-brain agent calls this before falling back to Grep.
Python standard library only.

  usage: python3 modules/memory-search/query.py "your question" [k]
         k   how many results to return (default 5)
"""
import json
import math
import re
import sqlite3
import sys
import urllib.request
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent
DB_PATH = MODULE_DIR / "generated" / "index.db"
OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"


def embed(text: str) -> list:
    body = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/embeddings", data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)["embedding"]


def cosine(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def keyword_query(con, query: str, k: int) -> list:
    terms = re.findall(r"\w+", query.lower())
    if not terms:
        return []
    match = " OR ".join(terms)
    rows = con.execute(
        "SELECT path, heading, snippet(chunks,2,'','','…',14) "
        "FROM chunks WHERE chunks MATCH ? ORDER BY rank LIMIT ?",
        (match, k)).fetchall()
    return list(rows)


def semantic_query(con, query: str, k: int) -> list:
    qvec = embed(query)
    scored = []
    for path, heading, body, vec in con.execute(
            "SELECT path,heading,body,vec FROM chunks"):
        score = cosine(qvec, json.loads(vec))
        snippet = " ".join(body[:260].split())
        scored.append((score, path, heading, snippet))
    scored.sort(reverse=True, key=lambda r: r[0])
    return [(p, h, s) for _, p, h, s in scored[:k]]


def main() -> int:
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print('usage: query.py "your question" [k]', file=sys.stderr)
        return 1
    query = sys.argv[1]
    k = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 5

    if not DB_PATH.exists():
        print("No memory-search index yet. Build it with the /index-memory skill "
              "(or: python3 modules/memory-search/index.py).", file=sys.stderr)
        return 1

    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT v FROM meta WHERE k='backend'").fetchone()
    backend = row[0] if row else "keyword"
    try:
        if backend == "semantic":
            results = semantic_query(con, query, k)
        else:
            results = keyword_query(con, query, k)
    finally:
        con.close()

    if not results:
        print(f"No matches for: {query}")
        return 0
    print(f"Top {len(results)} matches for \"{query}\" ({backend}):")
    for path, heading, snippet in results:
        loc = path + (f"  ›  {heading}" if heading else "")
        print(f"\n- {loc}\n  {snippet}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
