"""Helpers for the committed deferred-review queue."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def upsert_deferred_review_entry(
    *,
    root: str | Path,
    year: str | int,
    entry: dict[str, Any],
) -> Path:
    """Insert or replace one deferred-review entry by ``queue_id``."""
    root_path = Path(root).resolve()
    queue_path = root_path / "review_queue" / str(year) / "deferred_review.yaml"
    payload = _load_yaml(queue_path)
    if not isinstance(payload, dict):
        payload = {}
    entries = payload.get("entries")
    if not isinstance(entries, list):
        entries = []
    queue_id = str(entry["queue_id"])
    updated = [item for item in entries if isinstance(item, dict) and str(item.get("queue_id")) != queue_id]
    updated.append(dict(entry))
    updated.sort(key=lambda item: str(item.get("queue_id") or ""))
    _write_yaml(
        queue_path,
        {
            "tax_year": int(year),
            "entries": updated,
        },
    )
    return queue_path


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=False), encoding="utf-8", newline="\n")
