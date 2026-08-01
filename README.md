# CSV URL Knowledge Base

A Django web application that turns an uploaded CSV of URLs into a searchable,
semantic knowledge base. It scrapes each page, stores the content in SQLite,
builds vector embeddings, and exposes both a search UI and a REST API.

Built for "listing pages of people" (executives, leadership teams, bios), e.g.
`https://www.oracle.com/in/corporate/executives/`.

---

## Features

- **CSV upload + URL harvesting** — upload a CSV with a `url` column (or one URL
  per line); the backend parses it, scrapes each URL, and stores raw HTML +
  extracted text + metadata in SQLite.
- **Vector database integration** — harvested content is chunked, embedded,
  and stored in a FAISS index persisted to disk. A deterministic TF-IDF
  fallback embedder means the app runs with **no model download**; install
  `sentence-transformers` for higher-quality embeddings.
- **Semantic search UI** — ask natural-language questions; the app retrieves
  the most relevant chunks from FAISS and synthesizes a readable answer using
  the Groq free-tier LLM (if `GROQ_API_KEY` is set) or a local extractive
  summarizer (no API key needed).
- **REST API** — `GET /api/urls/` returns every harvested URL with its HTTP
  status, raw HTML, metadata, and content chunks.Browsable API included.
- **Bonus** — Docker + docker-compose support, structured logging to console
  and rotating files, clean modular project structure, sample CSV.

---

## Tech stack

| Layer | Technology |
|------|-------------|
| Backend | Django 5 + Django REST Framework |
| Database | SQLite (relational store for raw content) |
| Vector DB | FAISS (faiss-cpu) |
| Embeddings | sentence-transformers (optional) or scikit-learn TF-IDF fallback |
| Scraping | requests + BeautifulSoup (lxml) |
| LLM | Groq free-tier API (optional) or local extractive summarizer |
| Packaging | `uv` + `pyproject.toml` |
| Containers | Docker + docker-compose |

---

## Quick start (with `uv`)

```bash
# 1. Install uv (if you don't have it)
pip install uv

# 2. Install dependencies (creates a venv automatically)
uv sync --extra embeddings
#   — or, to skip the heavy embedding model and use the TF-IDF fallback:
# uv sync

# 3. Run database migrations
uv run python manage.py migrate

# 4. Start the dev server
uv run python manage.py runserver
```

Open <http://127.0.0.1:8000/>.

### Without `uv` (plain venv)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[embeddings]"
python manage.py migrate
python manage.py runserver
```

---

## Using the app

1. **Upload a CSV** on the dashboard. Use `sample_urls.csv` (Oracle / Microsoft
   / Google leadership pages) or your own. The CSV must have a `url` column
   (case-insensitive) or be a bare list of URLs, one per line.
2. The app scrapes each URL, stores content in SQLite, and rebuilds the FAISS
   index. Counts on the dashboard update automatically.
3. Go to **Search** and ask a question, e.g. *"Who is the CEO of Oracle?"*.
4. Browse the **API** at <http://127.0.0.1:8000/api/urls/>.

---

## Configuration

Copy `.env.example` to `.env` and edit as needed:

| Variable | Default | Purpose |
|----------|---------|---------|
| `DJANGO_SECRET_KEY` | dev key | Django secret key (change in production) |
| `DJANGO_DEBUG` | `True` | Debug mode |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Allowed hosts |
| `GROQ_API_KEY` | (empty) | Optional Groq API key for LLM answers |
| `GROQ_MODEL` | `llama-3.1-8b-instant` | Groq model name |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | sentence-transformers model |
| `SCRAPER_TIMEOUT` | `20` | Per-URL scrape timeout (seconds) |
| `SCRAPER_MAX_PAGES` | `50` | Max URLs processed per upload |

---

## REST API

### `GET /api/urls/`

Returns a paginated list of harvested URLs.

```json
{
  "count": 3,
  "results": [
    {
      "id": 1,
      "url": "https://www.oracle.com/in/corporate/executives/",
      "source_file": "sample_urls.csv",
      "http_status": 200,
      "status": "done",
      "title": "Executive Leadership | Oracle India",
      "meta_description": "View Oracle's executive leadership.",
      "raw_html": "<!DOCTYPE html>...",
      "extracted_text": "Executive Leadership ...",
      "content_hash": "a1b2c3...",
      "error_message": "",
      "chunks": [
        {"chunk_index": 0, "text": "...", "token_count": 180}
      ],
      "created_at": "2026-07-31T...",
      "updated_at": "2026-07-31T..."
    }
  ]
}
```

- `GET /api/urls/{id}/` — single URL detail.
- Browsable HTML API at `/api/urls/`.

---

## Docker

```bash
docker compose up --build
```

The app is served on <http://localhost:8000>. SQLite, the FAISS index, and
logs are volume-mounted so data persists across container restarts.

---

## Project structure

```
.
├── pyproject.toml              # uv / project metadata + dependencies
├── Dockerfile                  # multi-stage build with uv
├── docker-compose.yml
├── manage.py
├── sample_urls.csv             # sample input (Oracle/Microsoft/Google)
├── .env.example
├── kb_project/                 # Django project (settings, urls, wsgi/asgi)
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
└── kbapp/                      # The application
    ├── models.py               # HarvestedURL, ContentChunk
    ├── views.py                # Web (HTML) views
    ├── api_views.py            # DRF viewset
    ├── api_urls.py             # /api/ routes
    ├── serializers.py
    ├── admin.py
    ├── urls.py                 # Web routes
    ├── services/               # Business logic (modular)
    │   ├── csv_parser.py
    │   ├── scraper.py
    │   ├── chunker.py
    │   ├── embedder.py
    │   ├── vector_store.py     # FAISS wrapper
    │   ├── llm.py              # Groq + local fallback
    │   └── pipeline.py         # orchestration
    ├── management/commands/rebuild_index.py
    ├── templates/kbapp/        # base, index, search, detail
    └── static/kbapp/styles.css
```

---



**Demo Video**
[![Demo Video](https://github.com/AmalprasadK1998/Knowledge-Base-from-CSV-URLs/blob/main/screenshots/2.jpeg)](https://www.youtube.com/watch?v=AOlXfQ-IHsc)


## Management commands

```bash
# Rebuild the FAISS index from all successfully scraped URLs
python manage.py rebuild_index
```

---

## How retrieval works

1. **Scrape** — `requests` fetches each URL; `BeautifulSoup` (lxml) extracts the
   title, meta description, and a clean text dump (scripts/nav/footer removed).
2. **Chunk** — a recursive character splitter with sentence-aware boundaries
   slices each page into ~1000-character overlapping chunks.
3. **Embed** — chunks are embedded with `sentence-transformers` (if installed)
   or a deterministic hashed TF-IDF embedder (always available).
4. **Index** — embeddings are stored in a `faiss.IndexFlatL2` persisted to
   `vector_store/index.faiss`, with a JSON sidecar mapping row ids to chunks.
5. **Search** — the query is embedded the same way; FAISS returns the nearest
   chunks by L2 distance; the LLM (Groq or local) synthesizes an answer from
   the top chunks.

---

## Notes & trade-offs

**For my convenience, I used google AI studio API key and its free tier models.** `GOOGLE_API_KEY`

- **No JS rendering.** These executive-listing pages are server-rendered, so
  `requests` + `lxml` is sufficient. For JS-heavy sites, swap in Playwright.
- **TF-IDF fallback** keeps the app runnable in restricted environments; install
  `sentence-transformers` (`uv sync --extra embeddings`) for better retrieval.
- **Groq is optional.** Without `GROQ_API_KEY`, the local extractive
  summarizer ranks sentences by embedding similarity + query overlap.
- **Synchronous pipeline** is fine for the sample scale (dozens of URLs). For
  larger batches, wrap `run_pipeline` in a Celery task.
