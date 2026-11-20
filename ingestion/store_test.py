"""NO duplicates
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import psycopg

from ingestion import config, corpus
from ingestion.normalize import normalize_work 
from ingestion.openalex_client import OpenAlexClient, OpenAlexError
from ingestion.repository import count_rows, save_page

#download+clean
def main():
    try:
        with OpenAlexClient(config.OPENALEX_API_KEY) as client:
            raw_papers = next(client.iter_pages(corpus.build_filter(), per_page=3,
                                                sort=corpus.SORT), [])
    except OpenAlexError as exc:
        print("OpenAlex error:", exc)
        return
    papers = [p for p in (normalize_work(r) for r in raw_papers) if p is not None]
    print(f"downloaded {len(raw_papers)} papers, {len(papers)} kept post Clean Operation")
    if not papers:
        print("Nothing to save...")
        return

    try:
        conn = psycopg.connect(config.DATABASE_URL)
    except psycopg.OperationalError:
        print("Cannot reach the database:. Start Docker!!"
              "re open database/start_database.py only then and try again after restarting the kernell")
        return
    
    
    
    #SAVE
    with conn:
        save_page(conn, papers)
        first = count_rows(conn)
        print("2. after saving once :", first)

    
        save_page(conn, papers)
        second = count_rows(conn)
        print("3. after saving twice:", second)
        print("   ->", "IDENTICAL: no duplicates, storing is idempotent (OK)"
              if first == second else "DIFFERENT: problem!")

        # read again
        print("\n4. read back from the database:")
        rows = conn.execute(
            "SELECT id, publication_year, cited_by_count, title, pdf_url FROM works "
            "WHERE id = ANY(%s) ORDER BY cited_by_count DESC",
            ([p.work["id"] for p in papers],)).fetchall()
        for work_id, year, cites, title, pdf in rows:
            print(f"   {work_id} | {year} | {cites} citations | {title[:55]} | pdf: {pdf}")

        #fusion of multiple valus authors 
        first_id = rows[0][0]
        authors = conn.execute(
            "SELECT wa.author_position, a.name, a.affiliation "
            "FROM work_authors wa JOIN authors a ON a.id = wa.author_id "
            "WHERE wa.work_id = %s ORDER BY wa.author_position LIMIT 3", (first_id,)).fetchall()
        print(f"   authors of {first_id}:", authors)


main()
