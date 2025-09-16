#!/usr/bin/env python3
"""Utility to ask OpenAI GPT-5 to rate enrichment quality."""
from __future__ import annotations

import json
import os
from pathlib import Path
from textwrap import dedent

try:
    from openai import OpenAI  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependency: install the OpenAI Python SDK (pip install openai)."
    ) from exc

ROOT = Path(__file__).resolve().parents[1]
SIMPLE_PATH = ROOT / "catalog" / "simple.json"
ENRICHED_PATH = ROOT / "catalog" / "enriched.json"


def load_catalog(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):  # pragma: no cover - defensive
        raise ValueError("Expected a list of records")
    return data


def main() -> int:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Set OPENAI_API_KEY before running this script.")

    simple = load_catalog(SIMPLE_PATH)
    enriched = load_catalog(ENRICHED_PATH)

    enriched_by_sku = {record["sku"]: record for record in enriched}

    evaluation_payload = []
    for product in simple:
        sku = product.get("sku")
        enriched_record = enriched_by_sku.get(sku)
        if not enriched_record:
            continue
        evaluation_payload.append(
            {
                "sku": sku,
                "input": product,
                "output": enriched_record,
            }
        )

    if not evaluation_payload:
        raise SystemExit("No enriched products to evaluate.")

    client = OpenAI(api_key=api_key)

    prompt = dedent(
        """
        You are a catalog QA analyst. Rate the enrichment quality for each SKU on a scale of 1-5
        considering attribute normalization, SEO copy relevance, and overall completeness.
        Respond with JSON containing an array under `ratings` where each entry has:
          - sku
          - score (1-5)
          - justification (1-2 sentences)
        """
    ).strip()

    response = client.chat.completions.create(
        model="gpt-5",
        temperature=0.2,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(evaluation_payload)},
        ],
    )

    content = response.choices[0].message.content if response.choices else None
    if not content:
        raise SystemExit("No content returned from GPT-5.")

    print(content)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
