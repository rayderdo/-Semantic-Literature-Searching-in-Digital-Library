# search/ — embeddings and multi-route recall (Maple)

Input: the `works` table (Juliette). Output: `search(query, k)` returns the top-k papers
with their metadata and authors, ready for the API (Yasir) and the website (Katya).

## How it works

```
                       ┌─ dense   : BGE-M3 1024-d vector, cosine (pgvector HNSW) ──┐
 query ─ BGE-M3 ───────┤                                                           ├─ RRF ─ (rerank) ─ top-k
                       ├─ sparse  : BGE-M3 lexical weights, inner product (sparsevec)
 query ─ text ─────────└─ keyword : PostgreSQL full-text, ts_rank (title > abstract) ┘
```

* **Model:** [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3), run locally (free). One pass gives
  the dense vector AND the sparse weights. Embedded text = `title + "\n" + abstract`, max 512 tokens.
* **Storage:** table `search_index` (`database/sql/002_search_index.sql`): `dense vector(1024)`,
  `sparse sparsevec(250002)`, `tsv tsvector`, plus `model` and `text_hash`. Kept apart from
  `works`, so re-importing the works dump never deletes the embeddings.
* **Recall:** each route returns its 100 best candidates (`SEARCH_CANDIDATES`).
* **Fusion:** Reciprocal Rank Fusion, `score = Σ weight / (60 + rank)`. Uses ranks only, so the
  routes' different score scales do not matter.
* **Rerank (optional):** `bge-reranker-v2-m3` cross-encoder re-orders the 50 best fused papers.
  Better ordering, ~1 s on GPU, several seconds on CPU. Off by default (`SEARCH_RERANK=1` to enable).
* **Keyword route:** the query words are OR-ed (any word can match), not AND-ed, so long
  natural-language questions still find papers. It is PostgreSQL `ts_rank`, close to but not
  exactly BM25.

## Run it (in order)

1. Database running and papers imported (see `database/README.md`).
2. Install the libraries (once): `%pip install -r requirements.txt` — for a GPU, install
   PyTorch with CUDA first, see <https://pytorch.org/get-started/locally/>.
   The search libraries need **Python ≥ 3.10** (tested with 3.12, torch 2.6 + CUDA 12.4).
3. `search/build_index.py` — embeds every paper. First run downloads the model (~2.3 GB).
   25,000 papers: ~10-15 min on an RTX 4060, hours on CPU. Resumable; re-run after new papers.
   **Only one person needs to do this:** then export the dump (`share_database.py`,
   `ACTION = "export"`) and everyone imports it with the embeddings included.
4. `search/search_demo.py` — change `QUERY`, run.
5. `search/evaluate.py` — compares the routes (known-item test).

The search still needs the model on the machine that answers queries (to embed the
question), but the CPU is enough for one short query (~0.1-0.5 s).

## API for the backend

```python
from search.retriever import search, similar_works, popular_works

out = search("graph neural networks for drug discovery", k=10,
             year_from=2020, year_to=None,       # optional filters
             rerank=False,                        # optional second stage
             routes=("dense", "sparse", "keyword"))
out["results"]        # list of papers, best first
out["low_confidence"] # True if no paper is really close (best cosine < SEARCH_MIN_SIMILARITY)
out["suggestions"]    # most-cited papers, filled when low_confidence (FR-05)

similar_works("W2741809807", k=10)   # "more like this paper" (FR-05)
popular_works(k=10)                  # most-cited papers
```

One result:

```json
{
  "rank": 1, "score": 0.0489, "rrf_score": 0.0489,
  "work_id": "W2741809807", "title": "...", "abstract": "...",
  "publication_year": 2019, "cited_by_count": 1234, "doi": "10.1145/...",
  "type": "article", "landing_page_url": "https://...", "pdf_url": "https://... or null",
  "authors": [{"id": "A50...", "name": "...", "affiliation": "...", "position": 1}],
  "routes": {"dense": {"rank": 1, "score": 0.71}, "keyword": {"rank": 3, "score": 0.42}}
}
```

`routes` shows which recall routes found the paper and at which rank (useful to explain or
debug results). `score` is the RRF score, or the rerank score (0-1) when `rerank=True`.
Neither is a probability of relevance.

All functions accept `conn=` (an open psycopg connection) to reuse a connection in a server.

## Settings (`.env`, all optional)

| Variable | Default | Meaning |
|---|---|---|
| `EMBEDDING_MODEL_NAME` | `BAAI/bge-m3` | change = run `build_index.py` again (it notices) |
| `EMBEDDING_DEVICE` | auto | `cuda` or `cpu` |
| `EMBEDDING_BATCH_SIZE` | 32 | lower it if the GPU runs out of memory |
| `SEARCH_CANDIDATES` | 100 | candidates per route before fusion |
| `SEARCH_WEIGHT_DENSE/SPARSE/KEYWORD` | 1.0 | route weights in RRF |
| `SEARCH_RERANK` | 0 | 1 = rerank by default |
| `SEARCH_MIN_SIMILARITY` | 0.40 | below = low confidence + suggestions |
| `HF_ENDPOINT` | — | e.g. `https://hf-mirror.com` if huggingface.co is blocked |
