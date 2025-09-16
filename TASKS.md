# Work Breakdown Structure (Simplified Scope)

## Phase 0 – Foundations
- [ ] T0.1 Lock down JSON schema for `./catalog/simple.json` entries and enriched payload shape for `./catalog/enriched.json`.
- [ ] T0.2 Scaffold project folders (`src/`, `scripts/`, `catalog/`, `frontend/`) and initialize git + basic tooling (ruff, black, pytest).
- [ ] T0.3 Create sample seed data in `./catalog/simple.json` and empty `./catalog/enriched.json` with array placeholder.

## Phase 1 – Python Enrichment Workflow
- [ ] T1.1 Implement lightweight file-ingestion service that detects newly appended products in `./catalog/simple.json`.
- [ ] T1.2 Build enrichment pipeline function (attribute normalization + SEO stub + localization placeholder) that returns enriched payload.
- [ ] T1.3 Persist enriched products by appending unique entries into `./catalog/enriched.json` with idempotency guard.
- [ ] T1.4 Capture step-by-step workflow status (ingest → extract → validate → copywrite → localize → publish) for streaming to UI.
- [ ] T1.5 Add structured logging and JSON trace snapshots per run for debugging.

## Phase 2 – CLI/Script Trigger
- [ ] T2.1 Write `scripts/run_enrichment.py` to process pending products and print summary + status stream to console.
- [ ] T2.2 Add CLI flags for `--all` vs `--latest` product processing and optional dry run.
- [ ] T2.3 Document usage in README snippet including virtualenv instructions.

## Phase 3 – Next.js Frontend
- [ ] T3.1 Bootstrap Next.js app inside `frontend/` with Tailwind or minimal styling.
- [ ] T3.2 Create product submission form that writes new product to `./catalog/simple.json` (via API route) and triggers backend workflow.
- [ ] T3.3 Implement API route that invokes enrichment pipeline and streams workflow stage updates (Server-Sent Events or web socket).
- [ ] T3.4 Build UI component showing original product input alongside enriched output card once available.
- [ ] T3.5 Add live status timeline/console that reflects streamed workflow stages in real time.

## Phase 4 – Testing & QA
- [ ] T4.1 Unit tests for enrichment helpers (normalization, SEO stub, localization placeholder).
- [ ] T4.2 Integration test covering end-to-end run: append product to simple catalog, execute script, verify enriched entry produced.
- [ ] T4.3 Frontend component tests (React Testing Library) for form submission flow and streaming display stub.
- [ ] T4.4 Manual QA checklist documenting script run and UI workflow demonstration.

## Phase 5 – Packaging & Docs
- [ ] T5.1 Write developer setup guide plus instructions for running the script and Next.js frontend.
- [ ] T5.2 Provide sample `.env.example` for any keys needed (LLM provider, etc.).
- [ ] T5.3 Capture follow-up backlog items (advanced agents, analytics integration) in project notes.
