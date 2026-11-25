# database/

The project database: PostgreSQL 16 + pgvector, run with Docker.
Open Docker Desktop first, then run the scripts in Spyder.

| File | What it does |
|---|---|
| `start_database.py` | Starts the database (run it each time you restart your computer). |
| `share_database.py` | Imports or exports the dump file (`ACTION = "import"` or `"export"`). |
| `check_data.py` | Shows how many papers, authors and links are in the database. |
| `reset_database.py` | Deletes the whole database (asks you to type yes). |
| `sql/001_schema.sql` | Creates the tables, automatically, the first time the database starts. |

Settings (port, password) are in `.env`. Full guide: [`docs/README_JulietteINGESTIONandDATABASE.md`](../docs/README_JulietteINGESTIONandDATABASE.md), section 2.