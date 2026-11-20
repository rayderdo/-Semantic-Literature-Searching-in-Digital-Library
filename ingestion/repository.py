"""
STORE cleaned papers in PostgreSQL
"""

from psycopg.types.json import Jsonb

SAVE_AUTHOR = """
INSERT INTO authors (id, name, affiliation)
"""

SAVE_WORK = """
INSERT INTO works (id, doi, title, abstract, publication_year, cited_by_count, type, landing_page_url, pdf_url, raw_json)
"""

SAVE_LINK = """
INSERT INTO work_authors (work_id, author_id, author_position)
"""

#papers ckeaned from nomalize.py 
#multiple authors => 1 
def save_page(conn, papers):
    authors = {}
    for paper in papers:
        for author in paper.authors:
            known = authors.get(author["id"])
            if known is None:
                authors[author["id"]] = dict(author)
            elif known["affiliation"] is None and author["affiliation"]:
                known["affiliation"] = author["affiliation"]
    works = [dict(paper.work, raw_json=Jsonb(paper.work["raw_json"])) for paper in papers]
    links = [link for paper in papers for link in paper.links]

    with conn.transaction(): 
        with conn.cursor() as cur:
            cur.executemany(SAVE_AUTHOR, list(authors.values()))
            cur.executemany(SAVE_WORK, works)
            cur.executemany(SAVE_LINK, links)

#numbers check what is stored 
def count_rows(conn):
    row = conn.execute("""
        SELECT (SELECT count(*) FROM works),
               (SELECT count(*) FROM authors),
               (SELECT count(*) FROM work_authors),
               (SELECT count(*) FROM works WHERE abstract IS NOT NULL),
               (SELECT count(*) FROM works w
                 WHERE NOT EXISTS (SELECT 1 FROM work_authors wa WHERE wa.work_id = w.id))
    """).fetchone()
    names = ["works", "authors", "work_authors", "works_with_abstract", "works_without_author"]
    return dict(zip(names, row))
