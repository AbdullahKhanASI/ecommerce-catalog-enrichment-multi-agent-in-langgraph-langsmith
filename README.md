# E-commerce Catalog Enrichment & SEO Writer

Multi-agent workflow that ingests raw SKUs, normalizes attributes, generates SEO/localized copy, and publishes enriched catalog entries. The system uses LangGraph for agent orchestration, exposes a FastAPI backend, and ships with a Next.js frontend for submitting products and reviewing results in real time.

## Stack

- **Backend:** Python 3.12, FastAPI, LangGraph, LangSmith, OpenAI SDK
- **Frontend:** Next.js 14, React 18, streaming API route for workflow updates
- **Data:** JSON catalogs (`catalog/simple.json`, `catalog/enriched.json`) persisted on disk
- **Tooling:** Docker Compose for full stack, Pytest, LangSmith tracing (optional)

## Prerequisites

- Python 3.12+
- Node.js 18+
- Docker & Docker Compose (for containerized workflow)
- OpenAI API key (for enrichment prompts)
- LangSmith credentials (optional; disable tracing if unavailable)

## 1. Clone & Configure

```bash
git clone <repo-url>
cd ecommerce-catalog-enrichment-multi-agent-system-langgraph
cp .env.example .env
```

Update `.env` with the credentials your workflow needs:

- `OPENAI_API_KEY`
- `LANGSMITH_API_KEY` (optional, required only if `LANGCHAIN_TRACING_V2=true`)
- `LANGCHAIN_TRACING_V2`, `LANGCHAIN_ENDPOINT`, `LANGSMITH_PROJECT` Get from smith.langchain.com
- Any other provider-specific settings your runbooks require

## 2. Run with Docker (Recommended)

```bash
docker-compose up --build
```

- FastAPI backend mounts `catalog/` so enriched products persist.
- Next.js frontend is available at `http://localhost:3000`.
- Submit a product via the UI to see workflow events and enriched output streamed live.

Stop the stack with `docker-compose down`.

## 3. Local Development (without Docker)

### Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

The backend exposes Swagger docs at `http://localhost:8000/docs` and streams enrichment updates at `POST /api/enrich/stream`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000` to access the dashboard. The Next.js API route will proxy requests to `http://localhost:8000`. If your backend runs elsewhere, set `BACKEND_URL` (server-side) and/or `NEXT_PUBLIC_API_URL` (client-side) before starting the dev server.

## 4. CLI Workflow Runner

Process pending SKUs directly from the command line:

```bash
python scripts/run_enrichment.py --format text      # stream events to stdout
python scripts/run_enrichment.py --format json      # structured JSON output
python scripts/run_enrichment.py --format stream    # NDJSON for consumers
```

Use `--all` to process every pending SKU, or omit it to process only the latest addition in `catalog/simple.json`.

## 5. Tests

Install dev dependencies (via `pip install -e .`) and run:

```bash
pytest
```

Unit tests cover normalization logic and file persistence. Extend the `tests/` directory for graph-level or API tests as the project grows.

## 6. Optional: Enrichment Quality Scoring

Once the workflow generates outputs, you can ask OpenAI GPT-5 to rate them:

```bash
OPENAI_API_KEY=... python scripts/rate_enrichment.py
```

The script reads both catalog files and prints JSON ratings per SKU. Requires the OpenAI Python SDK (installed automatically via `pip install -e .`).

## Project Layout

```
catalog/            # Raw & enriched product JSON catalogs
frontend/           # Next.js application (API route + dashboard UI)
scripts/            # CLI runner, quality scoring helper
src/api/            # FastAPI app entrypoint & request models
src/enrichment/     # LangGraph workflow, I/O helpers, status events
tests/              # Pytest suite
```

## Troubleshooting

- **LangGraph warning:** install `langgraph` (already included in `pyproject.toml`) or ensure the virtualenv is active.
- **LangSmith 403:** verify API key, project name, and tracing flags in `.env`.
- **Docker backend can’t reach OpenAI/LangSmith:** confirm network egress and environment variables inside the container (`docker compose exec backend env`).
- **Frontend fetch failures in Docker:** check `BACKEND_URL` set in `docker-compose.yml` so the Next.js server calls the FastAPI service by container name.

## Continuous Integration

GitHub Actions (`.github/workflows/ci.yml`) runs on every push and pull request:

1. **Backend Tests** — installs Python dependencies and executes `pytest`.
2. **Frontend Build** — installs Node dependencies and runs `npm run build` to ensure the Next.js app compiles.
3. **Docker Smoke Test** — builds the backend and frontend images to catch Dockerfile regressions.

Pipelines will fail if any step breaks, keeping main deployable. Configure repository secrets if you introduce checks that require external credentials.
