"""Helpers for committed outbound-flow disposition artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


FLOW_DISPOSITIONS_FILENAME = "flow-dispositions.yaml"


def flow_dispositions_path(*, year: str | int, root: str | Path) -> Path:
    """Return the year-scoped flow-disposition artifact path."""
    root_path = Path(root).resolve()
    return root_path / "graph" / str(year) / FLOW_DISPOSITIONS_FILENAME


def load_flow_dispositions(
    year: str | int = "2025",
    root: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Load flow dispositions keyed by ``flow_id``."""
    root_path = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[1]
    path = flow_dispositions_path(year=year, root=root_path)
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = payload.get("entries")
    if not isinstance(entries, list):
        return {}
    dispositions: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        flow_id = str(entry.get("flow_id") or "").strip()
        if not flow_id:
            continue
        dispositions[flow_id] = dict(entry)
    return dispositions
