"""Try the search: open in Spyder, change QUERY, click Run.  Or:
    python search/search_demo.py "graph neural networks for molecules"
"""

QUERY = "detecting fake news on social media with deep learning"
K = 10
RERANK = False         # True = more precise ordering (cross-encoder), slower on CPU
SIMILAR_TO_FIRST = True

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from search.retriever import search, similar_works


def show(works):
    for w in works:
        authors = ", ".join(a["name"] for a in w["authors"][:3])
        if len(w["authors"]) > 3:
            authors += " et al."
        routes = " ".join(f"{r}#{v['rank']}" for r, v in w.get("routes", {}).items())
        print(f"{w['rank']:>2}. [{w['score']:.4f}] {w['title']}  ({w['publication_year']})")
        print(f"      {authors or 'no author'} | cited {w['cited_by_count']} | {routes}")


def main():
    query = " ".join(sys.argv[1:]) or QUERY
    out = search(query, K, rerank=RERANK)
    print(f"Query: {out['query']}")
    print(f"Candidates per route: {out['candidates']}  |  best cosine: {out['best_similarity']}"
          f"  |  time: {out['timing_ms']}")
    if out["low_confidence"]:
        print("(low confidence: no paper is really close; suggestions are also returned)")
    show(out["results"])
    if SIMILAR_TO_FIRST and out["results"]:
        first = out["results"][0]
        print(f"\nMore like '{first['title'][:70]}':")
        show(similar_works(first["work_id"], 5))


if __name__ == "__main__":
    main()
