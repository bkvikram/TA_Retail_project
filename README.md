# Retail Pricing Feed Manager

A single-page web application for a multi-country retail chain to upload store pricing feeds
(CSV) and to search/edit pricing records. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for
the context diagram, solution architecture, design decisions, non-functional requirements, and
assumptions.

**Stack:** Python 3.11 / FastAPI / SQLAlchemy (async) / PostgreSQL / React (Vite) / Docker Compose.

## Project layout

```
backend/            FastAPI service
  app/
    models.py        SQLAlchemy models (PricingRecord, PricingAuditLog, UploadJob)
    schemas.py        Pydantic request/response schemas
    routers/           /api/uploads, /api/pricing endpoints
    services/           CSV ingestion (streaming, batched upsert)
    auth.py             API-key auth dependency (dev stand-in for OAuth2/OIDC)
  tests/                pytest suite (SQLite in-memory)
frontend/            React SPA (Vite)
  src/
    components/         UploadPanel, SearchFilters, PricingTable
    api/client.js        fetch wrapper for the backend API
sample_data/          Example CSV feed for manual testing
docs/ARCHITECTURE.md  Design deliverables
docker-compose.yml     postgres + backend + frontend
```

## Running with Docker Compose (recommended)

```bash
docker compose up --build
```

- Frontend: http://localhost:8080
- Backend API docs (Swagger): http://localhost:8000/docs
- Postgres: localhost:5432 (user/password/db: `retail`/`retail`/`retail_pricing`)

## Running locally without Docker

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Point at a local Postgres, or use SQLite for a zero-dependency smoke test:
export DATABASE_URL="sqlite+aiosqlite:///./dev.db"
uvicorn app.main:app --reload --port 8000
```

Copy `backend/.env.example` to `backend/.env` and adjust `DATABASE_URL`/`API_KEY` for a real
Postgres instance. Tables are created automatically on startup for this reference implementation;
production deployments should manage schema changes with Alembic migrations instead (see
docs/ARCHITECTURE.md - Design Decisions).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:5173 (Vite proxies `/api/*` to `http://127.0.0.1:8000`).

### Running tests

```bash
cd backend
source .venv/bin/activate
pytest -v
```

8 tests cover: CSV upload + upsert semantics, row-level validation errors, search filtering, and
edit-with-audit-log behavior.

## Using the app

1. Open the frontend. Upload [sample_data/sample_pricing_feed.csv](sample_data/sample_pricing_feed.csv)
   (or any CSV with columns `Store ID, SKU, Product Name, Price, Date`) via the Upload panel.
2. The upload returns immediately with a job id and polls status until ingestion completes,
   showing inserted/updated/error row counts.
3. Use the Search panel to filter by store, SKU, product name (partial match), price range, or
   date range.
4. Click **Edit** on any row to change the product name or price, then **Save**. Each change is
   recorded in the audit log (`GET /api/pricing/{id}/history`).

## Authentication (dev mode)

Requests require `X-API-Key: dev-local-api-key` (see `backend/app/config.py`) and an
`X-User-Id` header identifying the editor, both sent automatically by the SPA. This is a
placeholder for the OAuth2/OIDC + IdP integration described in docs/ARCHITECTURE.md.
