"""Settings of the semantic search (Maple). Values can be overridden in .env."""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT / ".env")


def _get(name, default):
    value = os.getenv(name, "").strip().strip('"').strip("'")
    return value if value else default


DATABASE_URL = _get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/semantic_search")

# --- Embedding model -----------------------------------------------------------
# BGE-M3 gives, from ONE forward pass, a dense vector (semantic meaning) and sparse
# lexical weights (which words matter). Both are used by the multi-route recall.
# https://huggingface.co/BAAI/bge-m3
EMBEDDING_MODEL_NAME = _get("EMBEDDING_MODEL_NAME", "BAAI/bge-m3")
EMBEDDING_DIM = int(_get("EMBEDDING_DIM", "1024"))          # must match 002_search_index.sql
SPARSE_DIM = 250002                                         # BGE-M3 vocabulary size
MAX_LENGTH = int(_get("EMBEDDING_MAX_LENGTH", "512"))       # tokens; title+abstract fit
BATCH_SIZE = int(_get("EMBEDDING_BATCH_SIZE", "32"))
DEVICE = _get("EMBEDDING_DEVICE", "")                       # "", "cuda" or "cpu" ("" = auto)

# --- Re-ranking (optional second stage) -----------------------------------------
RERANKER_MODEL_NAME = _get("RERANKER_MODEL_NAME", "BAAI/bge-reranker-v2-m3")
RERANK_DEFAULT = _get("SEARCH_RERANK", "0") == "1"          # slow on CPU, fast on GPU

# --- Multi-route recall + fusion -------------------------------------------------
CANDIDATES_PER_ROUTE = int(_get("SEARCH_CANDIDATES", "100"))
RRF_K = int(_get("SEARCH_RRF_K", "60"))                     # Cormack et al. 2009
ROUTE_WEIGHTS = {
    "dense": float(_get("SEARCH_WEIGHT_DENSE", "1.0")),
    "sparse": float(_get("SEARCH_WEIGHT_SPARSE", "1.0")),
    "keyword": float(_get("SEARCH_WEIGHT_KEYWORD", "1.0")),
}
# Below this best dense cosine similarity, the results are flagged as "low confidence"
# and popular papers are suggested instead (README FR-05). Tune on real queries.
MIN_SIMILARITY = float(_get("SEARCH_MIN_SIMILARITY", "0.40"))
