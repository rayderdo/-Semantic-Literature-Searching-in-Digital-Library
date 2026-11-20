"""STEP 7 — THE INGESTION: download -> clean -> store, page by page.  Open in Spyder, click Run.
Needs: Docker Desktop open, database started (database/start_database.py), key in .env.

HOW TO USE: change LIMIT below, save (Cmd+S), click Run.
  1. LIMIT = 100    a sample of 100 papers (1 request)
  2. LIMIT = 100    again: check_data.py must show the SAME numbers (no duplicates)
  3. LIMIT = None   the whole corpus = the MAX_PAPERS most-cited papers of corpus.py
                    (25,000 -> about 250 requests, $0.03, a few minutes)
To stop a long run: the red square in the IPython console. Pages already saved stay
saved; running again simply updates them (never duplicates).
"""

#nb of papers to download
#i tried for multiple values 50, 100, and none 
#none takes quite some time to run (i think like 7 min ish)
#we need to determine this value!
LIMIT = None      


import sys 
import time 
from pathlib import Path 

#root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg 

from ingestion import config, corpus
from ingestion.normalize import normalize_work 
from ingestion.openalex_client import OpenAlexClient, OpenAlexError
from ingestion.repository import save_page

COST_PER_REQUEST = 0.0001  


def main():
    if not config.OPENALEX_API_KEY:
        print("OPENALEX_API_KEY is empty in .env.")
        return
    target = min(LIMIT or corpus.MAX_PAPERS, corpus.MAX_PAPERS)

    try:
        conn = psycopg.connect(config.DATABASE_URL)
    except psycopg.OperationalError:
        print("Cannot reach the database, try again.")
        return

    # flush=True: show the message right away, before the long download starts
    print(f"Downloading {target:,} papers, please wait...", flush=True)
    start = time.time()
    downloaded = saved = 0
    try:
        with conn, OpenAlexClient(config.OPENALEX_API_KEY) as client:
            for raw_page in client.iter_pages(corpus.build_filter(),
                                              per_page=min(100, target), sort=corpus.SORT):
                raw_page = raw_page[: target - downloaded]
                papers = [p for p in (normalize_work(r) for r in raw_page) if p is not None]
                if papers:
                    save_page(conn, papers)
                downloaded += len(raw_page)
                saved += len(papers)
                if downloaded >= target:
                    break
    except OpenAlexError as exc:
        print("\nOpenAlex error:", exc)
        print("Pages already saved are kept. Run again later to complete.")
        return

    print(f"DONE: {saved:,} papers saved in {time.time() - start:.0f} s "
          f"({downloaded - saved} skipped: no title/abstract).")


main()
