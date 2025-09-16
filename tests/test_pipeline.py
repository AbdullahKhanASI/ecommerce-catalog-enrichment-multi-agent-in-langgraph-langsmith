from __future__ import annotations

import json
from pathlib import Path

import pytest

from enrichment.pipeline import enrich_product, process_pending_products


@pytest.fixture()
def temp_catalog(tmp_path: Path) -> tuple[Path, Path]:
    simple = tmp_path / "simple.json"
    enriched = tmp_path / "enriched.json"
    simple.write_text(
        json.dumps(
            [
                {
                    "sku": "TEMP-1",
                    "name": "Test Bottle",
                    "description": "Keeps liquids hot.",
                    "attributes": {"capacity": "12 oz"},
                    "price": 10.0,
                    "currency": "USD",
                    "category": "Test",
                }
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    enriched.write_text("[]\n", encoding="utf-8")
    return simple, enriched


def test_enrich_product_converts_capacity_units():
    product = {
        "sku": "TEMP-2",
        "name": "Bottle",
        "description": "",  # only used if attribute missing
        "attributes": {"capacity": "20 oz"},
        "price": 12.5,
        "currency": "USD",
        "category": "Outdoors",
    }

    result = enrich_product(product)
    capacity = result.enriched["normalized_attributes"]["capacity"]

    assert capacity["unit"] == "ml"
    assert pytest.approx(capacity["value"], rel=1e-3) == 591.47
    assert result.enriched["seo"]["title"].startswith("Bottle | ")


def test_process_pending_products_appends_enriched_records(temp_catalog: tuple[Path, Path]):
    simple, enriched = temp_catalog

    processed = process_pending_products(str(simple), str(enriched), process_all=True)

    assert len(processed) == 1
    assert processed[0].sku == "TEMP-1"

    saved = json.loads(enriched.read_text(encoding="utf-8"))
    assert len(saved) == 1
    assert saved[0]["sku"] == "TEMP-1"

    repeat = process_pending_products(str(simple), str(enriched), process_all=True)
    assert repeat == []
