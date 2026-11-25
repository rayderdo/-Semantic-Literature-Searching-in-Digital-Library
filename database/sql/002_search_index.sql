-- =============================================================================
-- 002_search_index.sql — what the semantic search needs (Maple).
--
-- One row per paper, holding the 3 representations used by the multi-route recall:
--   dense  : BGE-M3 dense embedding (1024 dims), compared with cosine similarity
--   sparse : BGE-M3 lexical weights (one weight per vocabulary token), inner product
--   tsv    : PostgreSQL full-text vector (title weight A, abstract weight B), keyword route
--
-- Kept in a SEPARATE table (not new columns on `works`) so that re-importing the
-- works dump never loses the embeddings, and re-embedding never touches `works`.
--
-- Run automatically by Docker on a NEW database. For a database that already
-- exists, run search/setup_schema.py (same SQL, safe to run several times).
-- Needs pgvector >= 0.7 (sparsevec type); the pgvector/pgvector:pg16 image has it.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS search_index (
    -- = works.id. No FOREIGN KEY on purpose: importing the works dump
    -- (pg_restore --clean drops and re-creates `works`) would fail because of it.
    -- The search always JOINs with `works`, so a leftover row is simply ignored.
    work_id    TEXT PRIMARY KEY,
    model      TEXT NOT NULL,                 -- e.g. 'BAAI/bge-m3'
    text_hash  TEXT NOT NULL,                 -- md5 of the embedded text: re-embed only if it changed
    dense      vector(1024) NOT NULL,         -- L2-normalised
    sparse     sparsevec(250002),             -- BGE-M3 vocabulary size
    tsv        tsvector NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Approximate nearest neighbour indexes (HNSW). Source: https://github.com/pgvector/pgvector#hnsw
CREATE INDEX IF NOT EXISTS idx_search_dense  ON search_index USING hnsw (dense vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_search_sparse ON search_index USING hnsw (sparse sparsevec_ip_ops);
-- Full-text index for the keyword route.
CREATE INDEX IF NOT EXISTS idx_search_tsv    ON search_index USING gin (tsv);
