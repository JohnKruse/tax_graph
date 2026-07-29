"""Helpers for legacy producer-side deferred-review queue writes.

The workbench no longer reads a committed deferred queue. These helpers remain
for build-time producers that need to emit a temporary review finding while the
address-keyed derived review projection is assembled.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import yaml


def upsert_deferred_review_entry(
    *,
    root: str | Path,
    year: str | int,
    entry: dict[str, Any],
) -> Path:
    """Insert or replace one temporary producer finding by ``queue_id``."""
    return upsert_deferred_review_entries(root=root, year=year, entries=(entry,))


def upsert_deferred_review_entries(
    *,
    root: str | Path,
    year: str | int,
    entries: Iterable[dict[str, Any]],
) -> Path:
    """Write temporary producer findings without making them review identity."""
    new_entries = tuple(dict(entry) for entry in entries)
    root_path = Path(root).resolve()
    queue_path = root_path / "review_queue" / str(year) / "deferred_review.yaml"
    payload = _load_yaml(queue_path)
    existing_entries = payload.get("entries") if isinstance(payload, dict) else []
    updated = [item for item in existing_entries if isinstance(item, dict)] if isinstance(existing_entries, list) else []
    for entry in new_entries:
        queue_id = str(entry["queue_id"])
        replacement = dict(entry)
        for index, item in enumerate(updated):
            if str(item.get("queue_id")) == queue_id:
                updated[index] = replacement
                break
        else:
            updated.append(replacement)
    _write_yaml(queue_path, {"tax_year": int(year), "entries": updated})
    return queue_path


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)
