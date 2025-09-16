#!/usr/bin/env python3
"""CLI runner for the catalog enrichment workflow."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Iterable, List

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from enrichment.pipeline import (  # noqa: E402
    LANGGRAPH_AVAILABLE,
    ProcessedProduct,
    TRY_LANGGRAPH_ERROR,
    WORKFLOW_STEPS,
    process_pending_products,
)

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
LOGGER = logging.getLogger(__name__)

CATALOG_SIMPLE = ROOT / "catalog" / "simple.json"
CATALOG_ENRICHED = ROOT / "catalog" / "enriched.json"


def format_events(events: Iterable[dict]) -> str:
    return "\n".join(
        f"  - {event['timestamp']} | {event['step']}: {event['message']}"
        for event in events
    )


def print_text(processed: List[ProcessedProduct]) -> None:
    print("Workflow steps:", " → ".join(WORKFLOW_STEPS))
    for result in processed:
        print(f"\nSKU {result.sku} processed. Workflow events:")
        print(format_events(result.serializable_events()))
        print("Enriched payload:")
        print(json.dumps(result.enriched, indent=2))


def print_json(processed: List[ProcessedProduct]) -> None:
    payload = {
        "workflow_steps": list(WORKFLOW_STEPS),
        "processed": [
            {
                "sku": result.sku,
                "events": result.serializable_events(),
                "original": result.original,
                "enriched": result.enriched,
            }
            for result in processed
        ],
    }
    print(json.dumps(payload, indent=2))


def stream_events(processed: List[ProcessedProduct]) -> None:
    start = {"type": "start", "workflow_steps": list(WORKFLOW_STEPS)}
    print(json.dumps(start))
    sys.stdout.flush()
    for result in processed:
        for event in result.serializable_events():
            print(json.dumps({"type": "event", "sku": result.sku, "event": event}))
            sys.stdout.flush()
        print(json.dumps({"type": "enriched", "sku": result.sku, "enriched": result.enriched}))
        sys.stdout.flush()
    print(json.dumps({"type": "done", "count": len(processed)}))
    sys.stdout.flush()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run catalog enrichment workflow")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all pending products instead of only the most recent",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run pipeline without writing to enriched catalog",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json", "stream"),
        default="text",
        help="Output format",
    )
    args = parser.parse_args()

    if not LANGGRAPH_AVAILABLE:
        warning = "LangGraph not installed; falling back to sequential execution."
        if TRY_LANGGRAPH_ERROR:
            warning += f" ({TRY_LANGGRAPH_ERROR})"
        LOGGER.warning(warning)

    if args.dry_run:
        LOGGER.info("Running in dry-run mode; enriched results will not be persisted.")
        original_enriched = json.loads(CATALOG_ENRICHED.read_text(encoding="utf-8")) if CATALOG_ENRICHED.exists() else []
    else:
        original_enriched = None

    processed = process_pending_products(
        str(CATALOG_SIMPLE),
        str(CATALOG_ENRICHED),
        process_all=args.all,
    )

    if args.dry_run and original_enriched is not None:
        CATALOG_ENRICHED.write_text(json.dumps(original_enriched, indent=2) + "\n", encoding="utf-8")

    if not processed:
        print("No new products to process.")
        return 0

    if args.format == "text":
        print_text(processed)
    elif args.format == "json":
        print_json(processed)
    else:
        stream_events(processed)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
