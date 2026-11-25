"""STEP 4 — EMBEDDINGS: one dense + one sparse vector (+ a full-text vector) per paper.
Open in Spyder and click Run, or:  python search/build_index.py

Needs: Docker Desktop open, database started, papers imported (check_data.py).
Resumable: only papers that are new, or whose title/abstract changed, are embedded.
Stopping it (red square) keeps what is already saved; run again to continue.
25,000 papers: ~10-15 min on a laptop GPU (RTX 4060), a few hours on CPU.
"""

LIMIT = None        # e.g. 200 for a quick test, None = every paper
REBUILD = False     # True = embed every paper again (e.g. after changing the model)

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg

from search import config
from search.embedder import (document_text, get_embedder, text_hash,
                             to_pg_sparsevec, to_pg_vector)
from search.setup_schema import setup

CHUNK = 256   # papers embedded + saved per database transaction

UPSERT = """
INSERT INTO search_index (work_id, model, text_hash, dense, sparse, tsv, updated_at)
VALUES (%(id)s, %(model)s, %(hash)s, %(dense)s::vector, %(sparse)s::sparsevec,
        setweight(to_tsvector('english', %(title)s), 'A') ||
        setweight(to_tsvector('english', coalesce(%(abstract)s, '')), 'B'),
        now())
ON CONFLICT (work_id) DO UPDATE SET
    model = EXCLUDED.model, text_hash = EXCLUDED.text_hash, dense = EXCLUDED.dense,
    sparse = EXCLUDED.sparse, tsv = EXCLUDED.tsv, updated_at = now()
"""


def papers_to_embed(conn, model, rebuild=False, limit=None):
    rows = conn.execute("""
        SELECT w.id, w.title, w.abstract, s.text_hash, s.model
        FROM works w LEFT JOIN search_index s ON s.work_id = w.id
        ORDER BY w.cited_by_count DESC, w.id
    """).fetchall()
    todo = []
    for work_id, title, abstract, old_hash, old_model in rows:
        text = document_text(title, abstract)
        h = text_hash(text)
        if rebuild or old_hash != h or old_model != model:
            todo.append({"id": work_id, "title": title, "abstract": abstract,
                         "text": text, "hash": h})
    return todo[:limit] if limit else todo


def build(conn, limit=None, rebuild=False, verbose=True):
    setup(conn)
    model_name = config.EMBEDDING_MODEL_NAME
    todo = papers_to_embed(conn, model_name, rebuild, limit)
    if not todo:
        if verbose:
            print("Everything is already embedded.")
        return 0
    if verbose:
        print(f"Embedding {len(todo):,} papers with {model_name}...", flush=True)
    embedder = get_embedder()
    if verbose:
        print("  device:", embedder.device, flush=True)
    start, done = time.time(), 0
    for i in range(0, len(todo), CHUNK):
        chunk = todo[i:i + CHUNK]
        dense, sparse = embedder.encode([p["text"] for p in chunk])
        params = [dict(p, model=model_name, dense=to_pg_vector(d), sparse=to_pg_sparsevec(s))
                  for p, d, s in zip(chunk, dense, sparse)]
        with conn.transaction(), conn.cursor() as cur:
            cur.executemany(UPSERT, params)
        done += len(chunk)
        if verbose:
            rate = done / (time.time() - start)
            print(f"  {done:,}/{len(todo):,}  ({rate:.0f} papers/s, "
                  f"~{(len(todo) - done) / rate / 60:.1f} min left)", flush=True)
    return done


def main():
    with psycopg.connect(config.DATABASE_URL) as conn:
        n = build(conn, LIMIT, REBUILD)
        total = conn.execute("SELECT count(*) FROM search_index").fetchone()[0]
    print(f"DONE: {n:,} papers embedded, {total:,} in search_index.")


if __name__ == "__main__":
    main()
