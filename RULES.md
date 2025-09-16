# Project Rules & Operating Guidelines

## General Principles
- Prioritize data integrity, transparency, and reproducibility for all agent outputs.
- Treat every SKU thread as auditable: persist context, decisions, confidence, and human interventions.
- Optimize for safe, deterministic orchestration before pursuing advanced prompt creativity.

## Repository & Code Standards
- Language: Python ≥ 3.10. Follow PEP 8 with `ruff` and `black` linters enforced via pre-commit.
- Keep modules single-responsibility; place shared utilities under `src/` according to proposed layout.
- Use typed function signatures (`typing`, `pydantic`) for all agent IO contracts.
- Configuration via `.env` + `configs/*.yaml`; never commit secrets.
- Document significant modules with concise docstrings and rare inline comments to explain non-obvious logic.

## Agent & Graph Design
- Define each agent node as a LangGraph tool with explicit input/output schemas and confidence scoring.
- Supervisor must support map-reduce execution: batch fan-out limited by configurable concurrency; merge step validates completeness before progressing.
- All agents must return structured payloads (JSON) with `status`, `confidence`, and `evidence` fields.
- Implement deterministic retry policies: max attempts, backoff, and fallback prompts for low confidence.
- Persist per-SKU thread state after every node transition to enable resume, human QA interrupts, and audit replay.

## Data Handling & Security
- Validate incoming feeds against schema registry; quarantine malformed payloads.
- Hash or mask PII before logging or exporting traces.
- Enforce role-based access for human QA tools and PIM publishing credentials.
- Maintain localization glossaries and taxonomy data as versioned assets; updates require review.

## Testing & Quality Assurance
- No code merges without passing unit + integration tests and updated evaluation metrics.
- Maintain golden datasets for attribute extraction, dedupe decisions, SEO copy style, and localization quality; refresh quarterly or when taxonomy changes.
- Require regression evaluation runs before deploying prompt or model updates.
- Document manual QA steps for interrupt handling and ensure sign-off on all low-confidence overrides.

## Observability & Metrics
- Instrument every agent with LangSmith tracing, linking thread IDs to runs.
- Push latency, success/failure counts, token usage, and human QA rate to Langfuse; alert on regressions.
- Maintain dashboards tracking throughput, attribute coverage, copy acceptance, localization SLA, and human rework rate.

## Workflow & Collaboration
- Work in feature branches, open PRs with linked task IDs, and require at least one peer review.
- Update `PLAN.md` and `TASKS.md` when scope changes; keep commit history clean with conventional commits.
- Capture architectural decisions in ADRs under `docs/`.
- Coordinate deployments with runbooks; announce major prompt/model changes to stakeholders.
