# database/sql/

Database schema (next step). Every `.sql` file in this folder is run automatically by Docker,
in alphabetical order (`001_...sql`, `002_...sql`), the **first** time the database starts.
Other files (like this README) are ignored by Docker.

After changing a `.sql` file here, the database must be re-created (this deletes its data).
