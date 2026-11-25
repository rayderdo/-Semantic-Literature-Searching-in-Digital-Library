"""Create the search_index table in an EXISTING database (safe to run several times).
A brand-new database gets it automatically from database/sql/002_search_index.sql.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg

from search import config

SQL_FILE = config.PROJECT / "database" / "sql" / "002_search_index.sql"


def setup(conn):
    conn.execute(SQL_FILE.read_text(encoding="utf-8"))
    version = conn.execute("SELECT extversion FROM pg_extension WHERE extname='vector'").fetchone()
    return version[0] if version else None


def main():
    with psycopg.connect(config.DATABASE_URL) as conn:
        version = setup(conn)
    print(f"search_index table ready (pgvector {version}).")


if __name__ == "__main__":
    main()
