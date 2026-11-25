"""STEP 5 — SEARCH: natural-language question -> the top-k most relevant papers.

Multi-route recall ("hybrid search"), each route returns its own candidate list:
  1. dense   : BGE-M3 dense vector,  cosine similarity     (meaning, synonyms, paraphrases)
  2. sparse  : BGE-M3 lexical weights, inner product       (important words, learned weights)
  3. keyword : PostgreSQL full-text search, ts_rank        (exact terms, acronyms, names)
The lists are merged with Reciprocal Rank Fusion (RRF):
      score(paper) = sum over routes of  weight_route / (RRF_K + rank_in_route)
RRF only uses ranks, so the routes' scores do not need to be on the same scale.
Optionally, a cross-encoder (bge-reranker-v2-m3) re-orders the best fused candidates.

Public functions (used by the API):
  search(query, k=10, ...)        -> dict with "results" (README FR-01/02/03/10)
  similar_works(work_id, k=10)    -> "more like this paper" (FR-05)
  popular_works(k=10)             -> suggestions when nothing relevant is found (FR-05)
Every result is a plain dict (JSON-ready) with the paper metadata and its authors.
"""

from __future__ import annotations

import time
from contextlib import contextmanager

import psycopg

from search import config
from search.embedder import (document_text, get_embedder, get_reranker,
                             to_pg_sparsevec, to_pg_vector)

ROUTES = ("dense", "sparse", "keyword")


# --- helpers ----------------------------------------------------------------------
@contextmanager
def _connection(conn):
    if conn is not None:
        yield conn
    else:
        with psycopg.connect(config.DATABASE_URL) as new_conn:
            yield new_conn


def _filters(year_from, year_to, exclude_id=None):
    """SQL WHERE fragment (on works w) + its parameters."""
    parts, params = ["TRUE"], {}
    if year_from is not None:
        parts.append("w.publication_year >= %(year_from)s")
        params["year_from"] = year_from
    if year_to is not None:
        parts.append("w.publication_year <= %(year_to)s")
        params["year_to"] = year_to
    if exclude_id is not None:
        parts.append("w.id <> %(exclude_id)s")
        params["exclude_id"] = exclude_id
    return " AND ".join(parts), params


def _tune_hnsw(conn, n):
    """Let HNSW look at enough neighbours (and keep searching when filters drop rows)."""
    conn.execute(f"SET LOCAL hnsw.ef_search = {max(40, min(1000, 2 * n))}")
    try:
        with conn.transaction():   # pgvector >= 0.8 only; ignored on older versions
            conn.execute("SET LOCAL hnsw.iterative_scan = relaxed_order")
    except psycopg.Error:
        pass


def _ranked(rows):
    """[(work_id, score)] -> sorted best first."""
    return sorted(((r[0], float(r[1])) for r in rows), key=lambda x: -x[1])


# --- the 3 recall routes ------------------------------------------------------------
def dense_route(conn, dense_vec, n, where, params):
    rows = conn.execute(f"""
        SELECT s.work_id, 1 - (s.dense <=> %(q)s::vector) AS score
        FROM search_index s JOIN works w ON w.id = s.work_id
        WHERE {where}
        ORDER BY s.dense <=> %(q)s::vector
        LIMIT %(n)s""", dict(params, q=to_pg_vector(dense_vec), n=n)).fetchall()
    return _ranked(rows)


def sparse_route(conn, sparse_weights, n, where, params):
    if not sparse_weights:
        return []
    rows = conn.execute(f"""
        SELECT s.work_id, -(s.sparse <#> %(q)s::sparsevec) AS score
        FROM search_index s JOIN works w ON w.id = s.work_id
        WHERE {where} AND s.sparse IS NOT NULL
        ORDER BY s.sparse <#> %(q)s::sparsevec
        LIMIT %(n)s""", dict(params, q=to_pg_sparsevec(sparse_weights), n=n)).fetchall()
    return [(w, s) for w, s in _ranked(rows) if s > 0]


def _or_tsquery(conn, text):
    """'graph neural networks' -> 'graph' | 'neural' | 'network'  (any word can match;
    papers matching more / rarer words, in the title, rank higher)."""
    lexemes = conn.execute("SELECT tsvector_to_array(to_tsvector('english', %s))",
                           (text,)).fetchone()[0] or []
    quoted = ["'" + lx.replace("\\", "\\\\").replace("'", "''") + "'" for lx in lexemes]
    return " | ".join(quoted)


def keyword_route(conn, query, n, where, params):
    tsquery = _or_tsquery(conn, query)
    if not tsquery:
        return []
    rows = conn.execute(f"""
        WITH q AS (SELECT to_tsquery('simple', %(tsq)s) AS q)
        SELECT s.work_id, ts_rank(s.tsv, q.q, 1) AS score
        FROM search_index s JOIN works w ON w.id = s.work_id, q
        WHERE s.tsv @@ q.q AND {where}
        ORDER BY score DESC
        LIMIT %(n)s""", dict(params, tsq=tsquery, n=n)).fetchall()
    return _ranked(rows)


# --- fusion ---------------------------------------------------------------------------
def rrf_fuse(route_lists: dict[str, list[tuple[str, float]]], weights=None, k=None):
    """Reciprocal Rank Fusion. Returns [(work_id, rrf_score, {route: {rank, score}})]."""
    weights = weights or config.ROUTE_WEIGHTS
    k = config.RRF_K if k is None else k
    fused: dict[str, list] = {}
    for route, items in route_lists.items():
        w = weights.get(route, 1.0)
        for rank, (work_id, score) in enumerate(items, start=1):
            entry = fused.setdefault(work_id, [0.0, {}])
            entry[0] += w / (k + rank)
            entry[1][route] = {"rank": rank, "score": round(score, 4)}
    return sorted(((wid, s, r) for wid, (s, r) in fused.items()), key=lambda x: -x[1])


# --- metadata -------------------------------------------------------------------------
def fetch_works(conn, work_ids):
    """Paper metadata + ordered authors, for the given ids (order kept)."""
    if not work_ids:
        return []
    rows = conn.execute("""
        SELECT w.id, w.title, w.abstract, w.publication_year, w.cited_by_count, w.doi,
               w.type, w.landing_page_url, w.pdf_url,
               coalesce(json_agg(json_build_object('id', a.id, 'name', a.name,
                                                   'affiliation', a.affiliation,
                                                   'position', wa.author_position)
                                 ORDER BY wa.author_position)
                        FILTER (WHERE a.id IS NOT NULL), '[]'::json) AS authors
        FROM works w
        LEFT JOIN work_authors wa ON wa.work_id = w.id
        LEFT JOIN authors a ON a.id = wa.author_id
        WHERE w.id = ANY(%s)
        GROUP BY w.id""", (list(work_ids),)).fetchall()
    cols = ["work_id", "title", "abstract", "publication_year", "cited_by_count", "doi",
            "type", "landing_page_url", "pdf_url", "authors"]
    by_id = {r[0]: dict(zip(cols, r)) for r in rows}
    return [by_id[i] for i in work_ids if i in by_id]


# --- public API -----------------------------------------------------------------------
def search(query: str, k: int = 10, *, year_from: int | None = None,
           year_to: int | None = None, routes=ROUTES, rerank: bool | None = None,
           candidates: int = config.CANDIDATES_PER_ROUTE, weights: dict | None = None,
           conn=None) -> dict:
    """Return the k most relevant papers for a natural-language query.

    routes    : any subset of ("dense", "sparse", "keyword")
    rerank    : True = re-order the top fused candidates with the cross-encoder
    candidates: how many papers each route recalls before fusion
    """
    query = (query or "").strip()
    rerank = config.RERANK_DEFAULT if rerank is None else rerank
    timing, t0 = {}, time.perf_counter()
    if not query:
        return {"query": query, "results": [], "low_confidence": True,
                "best_similarity": None, "candidates": {},
                "suggestions": popular_works(k, conn=conn, year_from=year_from,
                                             year_to=year_to), "timing_ms": {}}

    dense_vec = sparse_w = None
    if "dense" in routes or "sparse" in routes:
        embedder = get_embedder()            # loads the model on the very first call
        t = time.perf_counter()
        dense_vec, sparse_w = embedder.encode_query(query)
        timing["encode"] = (time.perf_counter() - t) * 1000

    where, params = _filters(year_from, year_to)
    with _connection(conn) as c, c.transaction():
        _tune_hnsw(c, candidates)
        lists, t = {}, time.perf_counter()
        if "dense" in routes:
            lists["dense"] = dense_route(c, dense_vec, candidates, where, params)
        if "sparse" in routes:
            lists["sparse"] = sparse_route(c, sparse_w, candidates, where, params)
        if "keyword" in routes:
            lists["keyword"] = keyword_route(c, query, candidates, where, params)
        timing["recall"] = (time.perf_counter() - t) * 1000

        fused = rrf_fuse(lists, weights)
        pool = fused[: max(k, 50)] if rerank else fused[:k]
        works = fetch_works(c, [wid for wid, _, _ in pool])

        info = {wid: (s, r) for wid, s, r in pool}
        results = []
        for w in works:
            s, r = info[w["work_id"]]
            w["score"] = round(s, 6)
            w["rrf_score"] = round(s, 6)
            w["routes"] = r
            results.append(w)

        if rerank and results:
            t = time.perf_counter()
            scores = get_reranker().score(
                query, [document_text(w["title"], w["abstract"]) for w in results])
            for w, s in zip(results, scores):
                w["rerank_score"] = round(s, 6)
                w["score"] = w["rerank_score"]
            results.sort(key=lambda w: -w["score"])
            timing["rerank"] = (time.perf_counter() - t) * 1000
        results = results[:k]
        for i, w in enumerate(results, start=1):
            w["rank"] = i

        best_cos = lists.get("dense", [(None, 1.0)])[0][1] if lists.get("dense") else 0.0
        low = not results or ("dense" in lists and best_cos < config.MIN_SIMILARITY)
        out = {"query": query, "results": results, "low_confidence": low,
               "best_similarity": round(best_cos, 4) if "dense" in lists else None,
               "candidates": {r: len(v) for r, v in lists.items()},
               "suggestions": popular_works(k, conn=c, year_from=year_from,
                                            year_to=year_to) if low else []}
    timing["total"] = (time.perf_counter() - t0) * 1000
    out["timing_ms"] = {key: round(v, 1) for key, v in timing.items()}
    return out


def similar_works(work_id: str, k: int = 10, *, candidates: int = config.CANDIDATES_PER_ROUTE,
                  conn=None) -> list[dict]:
    """'More like this paper': papers closest to a given paper (dense + sparse, RRF)."""
    with _connection(conn) as c, c.transaction():
        row = c.execute("SELECT dense::text, sparse::text FROM search_index WHERE work_id = %s",
                        (work_id,)).fetchone()
        if row is None:
            return []
        dense_txt, sparse_txt = row
        where, params = _filters(None, None, exclude_id=work_id)
        _tune_hnsw(c, candidates)
        lists = {"dense": _ranked(c.execute(f"""
            SELECT s.work_id, 1 - (s.dense <=> %(q)s::vector)
            FROM search_index s JOIN works w ON w.id = s.work_id WHERE {where}
            ORDER BY s.dense <=> %(q)s::vector LIMIT %(n)s""",
            dict(params, q=dense_txt, n=candidates)).fetchall())}
        if sparse_txt:
            lists["sparse"] = _ranked(c.execute(f"""
                SELECT s.work_id, -(s.sparse <#> %(q)s::sparsevec)
                FROM search_index s JOIN works w ON w.id = s.work_id
                WHERE {where} AND s.sparse IS NOT NULL
                ORDER BY s.sparse <#> %(q)s::sparsevec LIMIT %(n)s""",
                dict(params, q=sparse_txt, n=candidates)).fetchall())
        fused = rrf_fuse(lists)[:k]
        works = fetch_works(c, [wid for wid, _, _ in fused])
        info = {wid: (s, r) for wid, s, r in fused}
        for i, w in enumerate(works, start=1):
            w["rank"], w["score"], w["routes"] = i, round(info[w["work_id"]][0], 6), \
                info[w["work_id"]][1]
        return works


def popular_works(k: int = 10, *, year_from=None, year_to=None, conn=None) -> list[dict]:
    """Most-cited papers: suggestions when the search finds nothing relevant."""
    where, params = _filters(year_from, year_to)
    with _connection(conn) as c:
        ids = [r[0] for r in c.execute(
            f"SELECT w.id FROM works w WHERE {where} ORDER BY w.cited_by_count DESC LIMIT %(n)s",
            dict(params, n=k)).fetchall()]
        return fetch_works(c, ids)
