# My part: embeddings and multi-route search (Maple)

## What is done

Steps 4 and 5 of the project overview:

4. **Embeddings**: every paper in the database gets a vector representation (one per paper).
5. **Search**: a natural-language question returns the top-k most relevant papers, plus
   "more like this paper" and suggestions when nothing relevant is found.

Tested end to end on a local database with 1,000 papers (same OpenAlex filter as Juliette's
corpus). The full 25,000 papers are still to be embedded, once the dump is imported.

## In one picture

```
 ┌──────────── Juliette ────────────┐     ┌──────────────────── Maple ─────────────────────┐     ┌── Yasir / Katya ──┐
 works, authors, work_authors  ───────►  build_index.py  ──►  search_index table
                                                                      │
                          user question ──────────────►  search(query, k)  ──►  top-k papers  ───►  API  ──►  website
                          a paper id    ──────────────►  similar_works(id) ──►  similar papers
```

## Part 1 — Embeddings (`search/build_index.py`)

**What it does:** reads every paper, turns its text into numbers that capture its meaning,
and stores them so the search can compare papers with a question.

**Input:** the `works` table (Juliette): `id`, `title`, `abstract`.
The text embedded for a paper is `title + new line + abstract` (max 512 tokens).

**Model:** [BGE-M3](https://huggingface.co/BAAI/bge-m3) (free, runs on our own computer, no API key).
One pass of the model gives two things:

| Representation | What it is | Good at |
|---|---|---|
| dense vector | 1,024 numbers describing the meaning | synonyms, paraphrases, "same idea, other words" |
| sparse vector | a weight for each important word of the text | exact important terms |

**Output:** a new table, `search_index` (created by `database/sql/002_search_index.sql`), one row per paper:

| Column | Content |
|---|---|
| `work_id` | = `works.id` (e.g. `W2741809807`) |
| `dense` | dense vector, `vector(1024)` (pgvector) |
| `sparse` | sparse vector, `sparsevec(250002)` (pgvector) |
| `tsv` | PostgreSQL full-text version of title (weight A) + abstract (weight B) |
| `model`, `text_hash` | which model was used and on which text, to know when to re-embed |
| `updated_at` | date of the embedding |

Indexes (HNSW for the vectors, GIN for the full text) make the search fast.

The table is separate from `works` on purpose: importing the works dump again never deletes
the embeddings, and re-embedding never changes Juliette's tables.

**Good to know**
- Resumable: running it again only embeds new papers or papers whose title/abstract changed.
- Speed: ~18 papers/s on a laptop GPU (RTX 4060) → about 23 min for 25,000 papers. Much slower on CPU.
- Only one person needs to run it, then export the dump: everyone gets the embeddings by importing it.

## Part 2 — Multi-route search (`search/retriever.py`)

**What it does:** finds the papers that best answer a question, by looking for them in three
different ways ("routes") and merging the three lists.

**Input:**
- the user's question in natural language, e.g. `"graph neural networks for drug discovery"`
- `k` = how many papers to return (default 10)
- optional: `year_from`, `year_to` (publication year filter)

**How:**

1. The question is turned into a dense and a sparse vector with the **same** model as the papers.
2. Three routes each return their 100 best candidates:

   | Route | Compares | Finds |
   |---|---|---|
   | dense | cosine similarity of the dense vectors | papers with the same meaning |
   | sparse | inner product of the sparse vectors | papers sharing important words |
   | keyword | PostgreSQL full-text search (any word of the question can match, title counts more) | exact terms, acronyms, names |

3. **Fusion (RRF, Reciprocal Rank Fusion):** each paper gets
   `score = Σ 1 / (60 + its rank in each route)`. A paper found high by several routes wins.
   Only ranks are used, so the different score scales of the routes do not matter.
4. Optional **rerank**: a second model (bge-reranker-v2-m3) reads the question and each of the 50 best
   papers together and re-orders them. More precise, slower. Off by default, not tested yet.
5. The metadata and authors of the top-k papers are read from Juliette's tables.

**Output:** a dictionary (JSON-ready):

```
{
  "query": "graph neural networks for drug discovery",
  "results": [ top-k papers, best first ],
  "low_confidence": false,      true when no paper is really close to the question
  "suggestions": [],            most-cited papers, given when low_confidence is true (FR-05)
  "best_similarity": 0.68,      best cosine similarity of the dense route
  "candidates": {"dense": 100, "sparse": 100, "keyword": 100},
  "timing_ms": {...}
}
```

Each paper in `results`:

```
rank, score, work_id, title, abstract, publication_year, cited_by_count, doi, type,
landing_page_url, pdf_url,
authors: [{id, name, affiliation, position}, ...]       ordered, 1 = first author
routes:  {"dense": {"rank": 3, "score": 0.71}, "keyword": {...}}   which routes found it
```

`score` is a ranking score, not a probability of relevance.

**Other functions:**

| Function | Input | Output | Requirement |
|---|---|---|---|
| `similar_works(work_id, k)` | a paper id | the k papers closest to it (dense + sparse routes, RRF) | FR-05 "more like this paper" |
| `popular_works(k)` | — | the k most-cited papers | FR-05 suggestions |

Full details for the API (parameters, settings in `.env`): [`search/README.md`](../search/README.md).

## Test results (1,000 papers)

| Test | Result |
|---|---|
| `"BERT pre-training of language models"` | pre-trained language model papers, found by all 3 routes |
| `"graph neural networks"`, years 2021-2022 | GNN surveys from 2022 only (filter works) |
| `"chocolate cake recipe"` / `"how to grow tomatoes"` | best similarity 0.33 / 0.38 → `low_confidence` + suggestions |
| Speed of one search (model loaded) | ~50 ms to embed the question + ~60 ms for the 3 routes |
| First search after starting | ~25 s more (the model is loaded once) |
| Known-item test (title as question, 200 papers) | found in the top 10 every time; fusion has the best MRR (0.998) |

The known-item test is too easy on 1,000 papers to compare the routes; it will be re-run on the
25,000 papers to tune the route weights.

## How to run

1. Database running, papers imported (Juliette's guide).
2. Install: PyTorch (with CUDA if you have an NVIDIA GPU, see pytorch.org), then
   `%pip install -r requirements.txt`. Needs Python ≥ 3.10.
3. Run `search/build_index.py` (first time: downloads the model, ~2.3 GB).
4. Run `search/search_demo.py`, change `QUERY` at the top to try other questions.
5. Optional: `search/evaluate.py` to compare the routes.

If the model download is slow or blocked, add `HF_ENDPOINT=https://hf-mirror.com` to `.env`.

## Files

| File | Role |
|---|---|
| `database/sql/002_search_index.sql` | creates the `search_index` table and its indexes |
| `search/config.py` | settings (model, number of candidates, route weights, threshold) |
| `search/embedder.py` | loads BGE-M3, turns text into dense + sparse vectors; reranker |
| `search/setup_schema.py` | creates `search_index` in an existing database |
| `search/build_index.py` | Part 1: embeds the papers |
| `search/retriever.py` | Part 2: `search`, `similar_works`, `popular_works` |
| `search/search_demo.py` | try a question |
| `search/evaluate.py` | compare the routes |

## TO DO

- Import the 25,000-paper dump and embed all papers, then export a new dump with the embeddings.
- Tune the route weights and the `low_confidence` threshold (0.40) on the full corpus.
- Test the reranker and decide whether to turn it on.
- The keyword route uses PostgreSQL `ts_rank`, close to BM25 but not exactly BM25.
