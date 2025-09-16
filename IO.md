# Workflow IO Specification

## 1. Inbound Product Feed (Input)
- **Format**: CSV / JSON lines / API payload bundled per batch.
- **Envelope**:
  - `batch_id`: string UUID assigned by feed adapter.
  - `received_at`: ISO-8601 timestamp.
  - `source`: channel identifier (e.g., `vendor_portal`, `erp_export`).
  - `skus`: array of raw SKU objects.
- **Raw SKU Object Fields**:
  - `sku_id`: vendor-provided identifier (string).
  - `title_raw`: unstructured product title text.
  - `description_raw`: long-form text with HTML / markdown noise.
  - `attributes_raw`: free-form key:value pairs (strings, mixed units).
  - `images`: array of URLs (may be missing/null).
  - `pricing`: object with `price`, `currency`, optional tiered pricing.
  - `inventory`: object with `quantity`, `warehouse`, optional `lead_time`.
  - `category_hint`: optional vendor taxonomy path.
  - `locale`: source language/locale code.
  - `compliance_docs`: optional URLs or IDs for regulatory files.
  - `metadata`: grab-bag extra fields (color text, bullet points, etc.).
- **Assumptions / Constraints**:
  - At least one identifier per SKU (`sku_id` or barcode) is required.
  - Attribute keys may be inconsistent in casing, spacing, or language.
  - Missing critical attributes are tolerated but must be flagged downstream.

## 2. Enriched SKU Payload (Output)
- **Format**: JSON document per SKU (optionally rebatched for PIM API).
- **Core Fields**:
  - `sku_id`: canonical identifier, optionally with internal `sku_hash`.
  - `status`: `ready` | `needs_human_review` | `rejected_duplicate`.
  - `confidence`: numeric 0.0-1.0 overall confidence.
  - `trace_refs`: LangSmith run IDs, Langfuse trace IDs.
- **Normalized Attributes** (`attributes` object):
  - Keys aligned to schema registry (e.g., `brand`, `material`, `dimensions`, `weight_kg`).
  - Units standardized (metric + imperial if required).
  - Each value annotated with `confidence` and optional `evidence` snippet.
- **Gap Flags** (`attribute_gaps`): array of objects capturing missing/ambiguous fields, with severity + recommended action.
- **SEO Content** (`seo_copy` object):
  - `title`: channel-optimized title per locale.
  - `short_description`: bullet-friendly copy with keyword annotations.
  - `long_description`: rich text meeting channel constraints.
  - `keywords`: prioritized keyword list with density targets.
  - `style_tags`: tone/persona metadata.
- **Localized Variants** (`localizations` array):
  - Each entry includes `locale`, localized `seo_copy`, localized attribute labels, compliance notes.
  - `localization_confidence` per locale plus escalation flag if human QA required.
- **Validation Summary** (`validation` object):
  - `schema_checks`: pass/fail results for required fields.
  - `duplicates`: reference to matched SKU IDs if de-duped.
  - `compliance`: status for regulatory checks.
- **Media** (`assets` object): curated image URLs, alt text, derived media where available.
- **Pricing & Inventory**: sanitized pricing, currency, inventory levels with unit harmonization.
- **Audit Trail** (`audit_log` array): ordered events capturing agent outputs, human overrides, timestamps.
- **Delivery Metadata** (`pim_dispatch` object):
  - `destination`: PIM endpoint or channel identifier.
  - `dispatch_status`: `queued` | `success` | `retry_pending`.
  - `last_attempt_at`: timestamp, `retry_count`.

## 3. Human QA Interrupt Package (Conditional Output)
- **Trigger**: Any SKU with low confidence or policy flag.
- **Contents**:
  - `sku_id`, `thread_id`, `current_status`.
  - Snapshot of normalized attributes + gaps + raw evidence.
  - Draft SEO/localized copy with highlight of uncertain segments.
  - Action checklist for reviewer and link to resume thread.

## 4. Analytics Emissions
- **Langfuse Metrics**: throughput per agent, latency, token usage, quality scores.
- **LangSmith Traces**: per-agent run records with input/output payload references, persisted for replay.
- **Data Sink**: structured JSON events or metrics payloads published to telemetry pipeline.

## 5. Error & Dead Letter Outputs
- **Malformed Feed Report**: JSONL of rejected SKUs with validation errors for ingestion retries.
- **Dead Letter Queue Payload**: SKU thread snapshots that exceeded retry policy, stored for manual intervention.
