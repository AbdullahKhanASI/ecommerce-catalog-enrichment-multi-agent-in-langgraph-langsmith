"""Helpers for reading/writing catalog data."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Dict, Any


def load_json_array(path: Path) -> List[Dict[str, Any]]:
    """Return a list parsed from a JSON array file."""
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected list in {path}, found {type(data).__name__}")
    return data


def write_json_array(path: Path, records: Iterable[Dict[str, Any]]) -> None:
    """Write iterable of dicts as JSON array with trailing newline."""
    array = list(records)
    path.write_text(json.dumps(array, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_unique_records(path: Path, *, existing: List[Dict[str, Any]], new_records: Iterable[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
    """Append new records keyed by ``key`` without duplicating existing entries."""
    seen = {record[key] for record in existing if key in record}
    appended: List[Dict[str, Any]] = list(existing)
    for record in new_records:
        identifier = record.get(key)
        if identifier is None:
            raise ValueError(f"Record missing key '{key}': {record}")
        if identifier in seen:
            continue
        appended.append(record)
        seen.add(identifier)
    write_json_array(path, appended)
    return appended
