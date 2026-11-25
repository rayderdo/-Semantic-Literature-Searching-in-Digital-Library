"""Quick sanity evaluation of the search routes (no human labels needed).

Known-item test: for N random papers, the query is the paper's TITLE and the
"correct answer" is that paper. We measure, for each configuration:
  Recall@k : how often the paper is in the top k
  MRR      : mean of 1/rank (1.0 = always first)
Caveat: the title is also part of the indexed text, so this favours exact-word routes.
It is a regression check and a way to compare settings, not a real relevance study.
Real evaluation = a few queries written by us, with papers judged relevant by hand.
"""

N = 200
K = 10
SEED = 42
CONFIGS = {
    "dense only": dict(routes=("dense",)),
    "sparse only": dict(routes=("sparse",)),
    "keyword only": dict(routes=("keyword",)),
    "dense+sparse+keyword (RRF)": dict(routes=("dense", "sparse", "keyword")),
    # "RRF + rerank": dict(routes=("dense", "sparse", "keyword"), rerank=True),
}

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg

from search import config
from search.retriever import search


def main():
    with psycopg.connect(config.DATABASE_URL) as conn:
        rows = conn.execute("SELECT w.id, w.title FROM works w "
                            "JOIN search_index s ON s.work_id = w.id").fetchall()
        random.Random(SEED).shuffle(rows)
        rows = rows[:N]
        print(f"Known-item test on {len(rows)} papers, k={K}\n")
        for name, kwargs in CONFIGS.items():
            hits, rr = 0, 0.0
            for work_id, title in rows:
                ids = [r["work_id"] for r in search(title, K, conn=conn, **kwargs)["results"]]
                if work_id in ids:
                    hits += 1
                    rr += 1 / (ids.index(work_id) + 1)
            print(f"{name:<30} Recall@{K} = {hits / len(rows):.3f}   MRR = {rr / len(rows):.3f}")


if __name__ == "__main__":
    main()
