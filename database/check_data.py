"""look at what is in the database
"""

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
DATABASE_URL = os.environ["DATABASE_URL"]


def one(conn, sql):
    return conn.execute(sql).fetchone()[0]


try:
    conn = psycopg.connect(DATABASE_URL)
except psycopg.OperationalError:
    raise RuntimeError("re open Docker"
                       "re open database/start_database.py only then and try again after restarting the kernell") from None

with conn:
    works = one(conn, "SELECT count(*) FROM works")
    if works == 0:
        print("The database is empty: import the dump (database/share_database.py).")
    else:
        print(f"works (papers)       {works:>7,}")
        print(f"authors              {one(conn, 'SELECT count(*) FROM authors'):>7,}")
        print(f"work_authors (links) {one(conn, 'SELECT count(*) FROM work_authors'):>7,}")