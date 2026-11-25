# My part: project foundation, database and data ingestion (Juliette)
## What is done 

I have set up the project foundation and ingestion of the database into usable tables for papers and authors (shared PostgreSQL database running in Docker app, dowloadable from internet)
For now I have only selected 25 000 computer science related work from openalex and cleaned them, then stored them as explained just before



### What you guys need to do prior to launching the code :

**Anaconda** (i used spyder for my whole part) : https://www.anaconda.com/download |
**Docker Desktop** (runs the database in the background) :  https://www.docker.com/products/docker-desktop/ |
**The project** : code from GitHub repository of Alina
**semantic_search.dump** : 25,000 papers, ready to import (no need to download them again as i used my personal key to create this document) 

### What to do, in this order to alunch the code!!!

I asked claude to create a tutorial if it doesnt work please tell me i will do one myself 

1. **Open Docker Desktop** and wait until it says "Engine running".
   Open Docker before Spyder!!!
2. **Open Spyder**, then Projects -> New Project... -> Existing directory and choose the
   project folder.
3. **Install the libraries** In Spyder's console (bottom right) : ask claude or deepseek for that... Then Consoles -> Restart kernel to have a cleaned base 
4. **Start the database:** open **database/start_database.py`** run. Wait until the command is done!! 
5. **Import the papers:** put **semantic_search.dump** in the project folder (next to
   **docker-compose.yml**), open **database/share_database.py**, write **ACTION = "import"**,
   save and run
6. **Check:** run **database/check_data.py**



## Project overview

Juliette : DONE:
1. Foundation: Docker database, settings, libraries 
2. Database tables (`works`, `authors`, `work_authors`) 
3. Ingestion: download + clean + store 25,000 papers 

**TO DO:**
4. Embeddings: one vector per paper : Maple
5. Search: question -> closest papers, similar papers : Maple
6. API endpoints : Yasir
7. Website : Katya

## Input and output of my part

**Input:** the OpenAlex API (free, needs a personal key in `.env`)
Requirements:
- Computer Science papers
- English
- type "article" 
- [2018;2025]
- with abstract 
=APP 1,234,299 papers, so I kept only the 25 000 most cited ones

**Output:** 3 tables in the database (claude schema)

```
works (25,000 papers)                       authors (78,568)
  id  ◄──────────────┐                ┌──►   id
  title              │                │      name
  abstract           │                │      affiliation
  publication_year   │                │
  cited_by_count     │                │
  doi                │                │
  landing_page_url   │                │
  pdf_url            │                │
  type, raw_json     │                │
                     │                │
             work_authors (121,988 links: who wrote which paper)
               work_id ───┘                │
               author_id ──────────────────┘
               author_position (1 = first author)
```

## Numbers for understanding the actual scale (can be modified)

Papers = 25 000
Authors = 78 568
Links paper-author = 121 988 
Cost = $0.025 (OpenAlex)
Papers with an abstract = 100 % 
Papers with a PDF link = 61.7 % 
Duplicate papers = 0 (--> I ran the same download twice and got the same numbers) 

Original record is saved in the raw_json file !! (so we can alsways take it back to the beginning)

Not all abstract are the same length (55 = less than 100 characters)
Do we want to keep the most cited one from this time period? older ones will be cites more logically...

Some works have no auhtors published (no author id in OpenALex)

