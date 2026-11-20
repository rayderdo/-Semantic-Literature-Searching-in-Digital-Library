-- =============================================================================
-- 001_schema.sql — the tables that store the papers and their authors.
--
-- Run automatically by Docker the FIRST time the database starts (see
-- docker-compose.yml). Safe to run again: "IF NOT EXISTS" everywhere, so running
-- it twice changes nothing (it is "idempotent").
--
-- Who fills the tables: Juliette's ingestion (download from OpenAlex, clean, store).
-- Who reads them: the search (Maple), the API (Yasir), and through it the website (Katya).
-- Not here yet: the `embeddings` table (one vector per paper). Its size depends on
-- the embedding model the team chooses; it will be added in 002_embeddings.sql.
-- =============================================================================

-- pgvector: adds the `vector` column type used later for the embeddings.
-- Enabled now so that the database is ready. Source: https://github.com/pgvector/pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- -----------------------------------------------------------------------------
-- works: one row per paper (an OpenAlex "Work").
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS works (
    -- OpenAlex id, e.g. 'W2741809807'. Using OpenAlex's own id as primary key means
    -- the same paper always gets the same row: downloading it again UPDATES the row
    -- instead of creating a duplicate.
    id               TEXT PRIMARY KEY,
    -- DOI, e.g. '10.1234/abc', stored lowercase. NOT unique on purpose: OpenAlex
    -- contains a few duplicate works sharing a DOI, and a UNIQUE rule would make
    -- the whole download fail on them.
    doi              TEXT,
    title            TEXT NOT NULL,       -- a paper without a title is not stored
    abstract         TEXT,                -- plain text (OpenAlex gives it as word -> positions)
    publication_year INTEGER,
    cited_by_count   INTEGER NOT NULL DEFAULT 0,
    type             TEXT,                -- e.g. 'article'
    landing_page_url TEXT,                -- page of the original source (publisher)
    pdf_url          TEXT,                -- direct PDF link when one exists (README FR-08)
    raw_json         JSONB                -- the original OpenAlex record, kept in case
                                          -- we need another field later without re-downloading
);

-- -----------------------------------------------------------------------------
-- authors: one row per author (an OpenAlex "Author").
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS authors (
    id             TEXT PRIMARY KEY,      -- OpenAlex id, e.g. 'A5023888391'
    name           TEXT NOT NULL,
    affiliation    TEXT,                  -- institution shown on the author's papers
    -- Extra information for the author page (README FR-09). Not inside the papers'
    -- data: NULL until an optional extra download fills them.
    works_count    INTEGER,
    cited_by_count INTEGER,
    h_index        INTEGER
);

-- -----------------------------------------------------------------------------
-- work_authors: who wrote which paper ("many-to-many": a paper has several
-- authors, an author has several papers).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS work_authors (
    -- REFERENCES = foreign key: the id must exist in the other table.
    -- ON DELETE CASCADE: deleting a paper (or author) also deletes its links.
    work_id         TEXT NOT NULL REFERENCES works(id)   ON DELETE CASCADE,
    author_id       TEXT NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    author_position INTEGER NOT NULL,     -- 1 = first author, 2 = second...
    PRIMARY KEY (work_id, author_id)      -- an author appears once per paper
);

-- -----------------------------------------------------------------------------
-- Indexes: make the frequent searches fast (like the index at the end of a book).
-- -----------------------------------------------------------------------------
-- "All papers of an author" (author page). The primary key above only helps
-- searches that start with work_id, so author_id needs its own index.
CREATE INDEX IF NOT EXISTS idx_work_authors_author_id ON work_authors (author_id);
-- Recent papers / popular papers (suggestions when no result is relevant, FR-05).
CREATE INDEX IF NOT EXISTS idx_works_publication_year ON works (publication_year);
CREATE INDEX IF NOT EXISTS idx_works_cited_by_count  ON works (cited_by_count DESC);
-- Find a paper by its DOI.
CREATE INDEX IF NOT EXISTS idx_works_doi             ON works (doi);
