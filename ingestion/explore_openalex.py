"""
Explore OpenAlex before downloading everything.  Open in Spyder, click Run.

COUNT: how many papers match the corpus settings in corpus.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingestion import config, corpus 
from ingestion.openalex_client import OpenAlexClient, OpenAlexError  

COST_PER_REQUEST = 0.0001  #$$$

#make preview readable
def short(value, length=90):
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    return text if len(text) <= length else text[:length] + "..."


def main():
    if not config.OPENALEX_API_KEY:
        print("OPENALEX_API_KEY is empty: enter your personnal key in .env"
              "(OPENALEX_API_KEY=your-key), save then run again.")
        return

    filters = corpus.build_filter()
    print("Filter sent to OpenAlex:\n ", filters)

    try:
        with OpenAlexClient(config.OPENALEX_API_KEY, config.OPENALEX_BASE_URL) as client:
            n = client.count(filters)
            kept = min(n, corpus.MAX_PAPERS)
            pages = -(-kept // 100)              # divide by 100, rounded up
            print(f"\n1. COUNT: {n:,} papers match the filter")
            print(f"   we keep the {kept:,} most-cited (MAX_PAPERS in corpus.py)")
            print(f"   full download = about {pages:,} requests = ${pages * COST_PER_REQUEST:.2f}")

            print(f"\nDONE: {client.requests_made} requests "
                  f"(${client.requests_made * COST_PER_REQUEST:.4f}). "
                  f"Budget left today: ${client.last_budget_left}")
    except OpenAlexError as exc:
        print("\nOpenAlex error:", exc)


main()
