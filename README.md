# Semantic Literature Search in Digital Library

A web application that helps students and researchers discover relevant literature through semantic search. Instead of relying only on exact keyword matches, the system aims to retrieve works whose content is conceptually related to a natural-language query.

**Project status:** Academic team project — development in progress.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Problem Statement](#problem-statement)
- [Key Features](#key-features)
- [How Semantic Search Works](#how-semantic-search-works)
- [Functional Requirements](#functional-requirements)
- [Application Pages](#application-pages)
- [System Architecture](#system-architecture)
- [Data Sources and APIs](#data-sources-and-apis)
- [Technology Stack](#technology-stack)
- [Getting Started](#getting-started)
- [Team](#team)

---

## Project Overview

The project aims to develop a digital library web platform that aggregates literature from multiple sources and helps users discover relevant materials through semantic search.

The platform is intended to support different types of textual materials, including:

- Academic publications and research papers
- Books
- Articles
- Theses
- Reports
- Other relevant textual materials

For each available work, the application may display bibliographic metadata such as its title, authors, publication year, abstract or description, citation information, and a link to the original source. Users will also be able to navigate to author information and discover related works.

---

## Problem Statement

Traditional keyword-based search can miss relevant publications when a user's query and a document express the same idea using different words, synonyms, or paraphrases.

The project addresses this limitation by using semantic representations of text. This should allow the application to retrieve literature based on meaning and conceptual similarity, rather than depending exclusively on literal keyword matches.

---

## Key Features

- Natural-language search interface
- Semantic retrieval of literature based on the meaning of a query
- Relevance-ranked search results, where supported by the search pipeline
- Similar-work discovery (e.g. "more like this paper")
- Detailed pages for individual works
- Author pages with available author information
- Links to original records and PDF files when available
- Clear handling of empty results and external API errors

---

## How Semantic Search Works

The planned semantic retrieval workflow consists of the following steps:

1. **Text preparation** — Prepare publication text, such as titles and abstracts, for processing.
2. **Embedding generation** — Convert the prepared literature content into numerical vectors (embeddings) using an embedding model.
3. **Vector storage** — Store each embedding together with an identifier that links it to the corresponding work or text segment.
4. **Query processing** — Convert the user's natural-language query into an embedding using the same model and compatible encoding settings.
5. **Similarity calculation** — Compare the query vector with stored vectors using cosine similarity.
6. **Ranking and retrieval** — Sort candidates by similarity and return the most relevant works with their available metadata and source links.

Cosine similarity is used as a measure of vector similarity; a higher score indicates closer vector directions, but it should not be interpreted as a probability of relevance.

> The exact embedding provider, model, vector dimensions, storage implementation, and retrieval parameters will be documented once finalized.

---

## Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | The system shall allow users to enter a natural-language query through the search interface. | Must |
| FR-02 | The system shall display search results ranked by relevance when relevance-ranked results are supported by the API. | Must |
| FR-03 | The system shall display the title, author(s), publication year, and available description for each search result. | Must |
| FR-04 | The system shall allow users to open a detailed page for a selected work. | Must |
| FR-05 | The system shall display "more like this paper" results and suggest papers when no relevant results are found. | Must |
| FR-06 | The system shall provide a Home page with a search interface as its primary element. | Must |
| FR-07 | The Home page shall provide navigation to the main pages and search functionality. | Must |
| FR-08 | The system shall provide a PDF link when a usable PDF URL is available. | Should |
| FR-09 | The author page shall display the author's name and available additional information, such as affiliation or research topics. | Must |
| FR-10 | The system shall perform semantic search by comparing the embedding vector of the user's natural-language query with pre-generated embedding vectors of indexed literature content, allowing retrieval of relevant works based on semantic meaning rather than exact keyword matches. | Must |

---

## Application Pages

The planned web application contains four main pages:

1. **Home page** — the main search interface and navigation.
2. **Search page** — the user's query and the list of ranked literature results.
3. **Work entity page** — detailed information about a selected publication or other work.
4. **Author entity page** — available information about an author and navigation to their works.

---

## System Architecture

The application is planned as a web platform with several cooperating components:

- **Frontend** — Provides the user interface, search experience, result presentation, and navigation between pages.
- **Backend** — Handles application logic, communication with external APIs, and data processing.
- **Literature data source** — Supplies bibliographic records and related metadata.
- **Semantic retrieval component** — Generates or requests embeddings, compares query and content vectors, and returns ranked candidates.
- **Database and storage** — Stores normalized work and author information, source identifiers, and the data required to connect search results to their original records.

> The architecture and implementation details may evolve during development. Final diagrams and technical decisions should be documented in [`docs/architecture.md`](docs/architecture.md).

---

## Data Sources and APIs

### OpenAlex

OpenAlex is the planned primary source for scholarly metadata. It provides information about works, authors, topics, institutions, and citations.

### Embedding API

An external embedding API is being considered for converting literature text and user queries into vectors. The project presentation discusses possible providers and models, including OpenAI embeddings, Cohere, Voyage, and BGE-M3 through a hosted provider.

> The final provider and model have not yet been fixed in this README. They should be added here after the team makes its implementation decision.

### Other datasets

Open Library dumps and the Goodbooks-10k dataset were also considered as possible sources for book-related data. Their use in the final implementation is subject to the team's scope and data-integration decisions.

---

## Technology Stack

The project presentation identifies PHP as a backend option and discusses PostgreSQL and MongoDB for data storage. React, Next.js, TypeScript, and CSS approaches were considered for the frontend.

Because some technology choices are still under consideration, this section distinguishes options from confirmed implementation decisions. Update it as the team finalizes the stack.

| Component | Technology / option |
|-----------|---------------------|
| Backend | PHP (presented backend option) |
| Frontend | React / Next.js (considered options) |
| Frontend language | JavaScript / TypeScript (considered options) |
| Database | PostgreSQL and/or MongoDB (under consideration) |
| Literature metadata | OpenAlex API |
| Semantic search | Embedding API and cosine similarity |

---

## Getting Started

The implementation setup instructions will be added when the team finalizes the application stack and creates the corresponding frontend and backend projects.

In the meantime, to get the project files:

```bash
git clone <repository-url>
cd semantic-literature-search
```

> For now, there are no confirmed dependency installation or run commands. Once the application is implemented, this section should include prerequisites, environment variable configuration, database setup, and commands to start the frontend and backend.

---

## Team

Academic team project developed as part of the Content Management and Digital Library course.

- **Alina Blinova** — Analyst
- **Juliette Rey** — Back-End
- **Ekaterina Malinkina** — Front-End
- **Imam Muhammad Yasir** — Back-End
- **Maple** — Back-End
