#!/usr/bin/env python3
"""Compabob: memory-search query.

Searches the index built by index.py and prints the most relevant chunks, best
match first. With a hybrid index it ranks the chunks twice, once by keywords
(FTS5) and once by meaning (Ollama vectors), and merges the two lists with
reciprocal rank fusion: a chunk near the top of either list rises. If Ollama is
not answering at query time, it falls back to keywords alone and says so.
The second-brain agent calls this before falling back to Grep.
Python standard library only.

  usage: python3 modules/memory-search/query.py "your question" [k]
         k   how many results to return (default 5)

Vector scoring is plain Python over every chunk, which stays fast up to roughly
20,000 chunks (a very large vault).
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
RRF_K = 60  # the standard constant; larger values flatten the gap between ranks


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


def keyword_ranking(con, query: str, n: int) -> list:
    terms = re.findall(r"\w+", query.lower())
    if not terms:
        return []
    match = " OR ".join(f'"{t}"' for t in terms)
    return [r[0] for r in con.execute(
        "SELECT rowid FROM fts WHERE fts MATCH ? ORDER BY rank LIMIT ?", (match, n))]


def vector_ranking(con, query: str, n: int) -> list:
    qvec = embed(query)
    scored = [(cosine(qvec, json.loads(vec)), doc_id)
              for doc_id, vec in con.execute("SELECT id, vec FROM vecs")]
    scored.sort(reverse=True)
    return [doc_id for _, doc_id in scored[:n]]


def fuse(rankings: list, k: int) -> list:
    """Reciprocal rank fusion: score = sum over lists of 1 / (RRF_K + rank)."""
    scores = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, 1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (RRF_K + rank)
    return sorted(scores, key=scores.get, reverse=True)[:k]


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
    try:
        row = con.execute("SELECT v FROM meta WHERE k='backend'").fetchone()
        backend = row[0] if row else "keyword"
        if not con.execute("SELECT 1 FROM sqlite_master WHERE name='docs'").fetchone():
            print("This index was built by an older version. Rebuild it with the "
                  "/index-memory skill (or: python3 modules/memory-search/index.py).", file=sys.stderr)
            return 1
        rankings, used = [], []
        if backend in ("keyword", "hybrid"):
            rankings.append(keyword_ranking(con, query, 2 * k))
            used.append("keyword")
        if backend in ("hybrid", "semantic"):
            try:
                rankings.append(vector_ranking(con, query, 2 * k))
                used.append("meaning")
            except Exception:  # noqa: BLE001 - any Ollama failure means: no vectors
                print("note: Ollama did not answer, so this search used keywords only.", file=sys.stderr)
        ids = fuse(rankings, k)
        rows = {r[0]: r[1:] for r in con.execute(
            f"SELECT id, path, heading, body FROM docs WHERE id IN ({','.join('?' * len(ids))})", ids)} if ids else {}
    finally:
        con.close()

    if not ids:
        print(f"No matches for: {query}")
        return 0
    print(f"Top {len(ids)} matches for \"{query}\" ({' + '.join(used)}):")
    for doc_id in ids:
        path, heading, body = rows[doc_id]
        loc = path + (f"  ›  {heading}" if heading else "")
        print(f"\n- {loc}\n  {' '.join(body[:260].split())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
