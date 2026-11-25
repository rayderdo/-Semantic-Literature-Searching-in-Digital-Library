"""Turn text into vectors with BGE-M3 (dense + sparse), and optionally re-rank.

The model is loaded once (first call) and then reused: loading takes ~10-30 s.
Documents and queries are encoded with the SAME model and settings (README step 4).
"""

from __future__ import annotations

import hashlib
from functools import lru_cache

import numpy as np

from search import config


def document_text(title: str, abstract: str | None) -> str:
    """The text embedded for one paper: title, then abstract."""
    return f"{title}\n{abstract}" if abstract else title


def text_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _device() -> str:
    if config.DEVICE:
        return config.DEVICE
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"


# Only the files needed by PyTorch inference. Without this, FlagEmbedding downloads the
# whole model repository (bge-m3 also contains a 2.2 GB ONNX copy we never use).
_MODEL_FILES = ["*.json", "*.txt", "*.model", "pytorch_model.bin", "*.safetensors",
                "colbert_linear.pt", "sparse_linear.pt"]


def local_model_path(model_name: str) -> str:
    """Local folder of the model, downloaded once into the Hugging Face cache.
    Set HF_ENDPOINT=https://hf-mirror.com in .env if huggingface.co is slow/blocked."""
    import os
    if os.path.exists(model_name):
        return model_name
    from huggingface_hub import snapshot_download
    return snapshot_download(repo_id=model_name, allow_patterns=_MODEL_FILES)


class Embedder:
    def __init__(self, model_name: str = config.EMBEDDING_MODEL_NAME):
        from FlagEmbedding import BGEM3FlagModel   # heavy import: only when needed
        self.model_name = model_name
        self.device = _device()
        self.model = BGEM3FlagModel(local_model_path(model_name),
                                    use_fp16=self.device == "cuda", devices=[self.device])

    def encode(self, texts: list[str], batch_size: int = config.BATCH_SIZE,
               max_length: int = config.MAX_LENGTH):
        """Return (dense, sparse).
        dense  : float32 array (n, 1024), each row L2-normalised (so dot = cosine)
        sparse : list of {token_id: weight} dicts
        """
        out = self.model.encode(texts, batch_size=batch_size, max_length=max_length,
                                return_dense=True, return_sparse=True,
                                return_colbert_vecs=False)
        dense = np.asarray(out["dense_vecs"], dtype=np.float32).reshape(len(texts), -1)
        dense /= np.linalg.norm(dense, axis=1, keepdims=True).clip(min=1e-12)
        sparse = [{int(t): float(w) for t, w in lw.items() if float(w) > 0}
                  for lw in out["lexical_weights"]]
        return dense, sparse

    def encode_query(self, query: str):
        dense, sparse = self.encode([query], batch_size=1)
        return dense[0], sparse[0]


class Reranker:
    """Cross-encoder: reads (query, paper) together, more precise but slower."""

    def __init__(self, model_name: str = config.RERANKER_MODEL_NAME):
        from FlagEmbedding import FlagReranker
        device = _device()
        self.model = FlagReranker(local_model_path(model_name), use_fp16=device == "cuda",
                                  devices=[device])

    def score(self, query: str, texts: list[str]) -> list[float]:
        if not texts:
            return []
        scores = self.model.compute_score([[query, t] for t in texts],
                                          max_length=config.MAX_LENGTH, normalize=True)
        return [float(s) for s in np.atleast_1d(scores)]


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    return Embedder()


@lru_cache(maxsize=1)
def get_reranker() -> Reranker:
    return Reranker()


# --- pgvector text formats ------------------------------------------------------
def to_pg_vector(vec) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


def to_pg_sparsevec(weights: dict[int, float], dim: int = config.SPARSE_DIM) -> str:
    # pgvector sparsevec indices are 1-based: '{1:0.5,7:0.2}/250002'
    items = ",".join(f"{i + 1}:{w:.6f}" for i, w in sorted(weights.items()))
    return "{" + items + "}/" + str(dim)
