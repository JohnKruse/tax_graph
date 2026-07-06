"""Load SOI form-count weights for frontier prioritization."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SoiCounts:
    """SOI return-count weights and provenance."""

    soi_year: int
    source_url: str
    retrieved_date: str
    note: str
    counts: dict[str, int]


def load_soi_counts(root: str | Path, soi_year: int | None = None) -> SoiCounts:
    """Load the committed SOI return-count reference file."""
    root_path = Path(root).resolve()
    data_dir = root_path / "data" / "soi"
    path = data_dir / f"form_counts_{soi_year}.yaml" if soi_year else _latest_counts_file(data_dir)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    provenance = data.get("provenance", {})
    return SoiCounts(
        soi_year=int(provenance["soi_year"]),
        source_url=str(provenance["source_url"]),
        retrieved_date=str(provenance["retrieved_date"]),
        note=str(provenance["note"]),
        counts={str(key): int(value) for key, value in (data.get("counts") or {}).items()},
    )


def load_form_id_map(root: str | Path) -> dict[str, str]:
    """Load SOI label to graph document-id mappings."""
    path = Path(root).resolve() / "data" / "soi" / "form_id_map.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    labels = data.get("labels") or {}
    return {str(label): str(value["document_id"]) for label, value in labels.items()}


def parse_soi_label_counts(rows: list[dict[str, Any]], label_field: str, count_field: str, mapping: dict[str, str]) -> dict[str, int]:
    """Parse tabular SOI rows into graph document-id counts.

    This is used by the optional acquisition helper and is intentionally
    simple: tests feed normalized rows, while awkward IRS spreadsheets can be
    curated into the committed YAML with the same provenance block.
    """
    counts: dict[str, int] = {}
    for row in rows:
        label = str(row.get(label_field, "")).strip()
        document_id = mapping.get(label)
        if not document_id:
            continue
        raw_count = str(row.get(count_field, "")).replace(",", "").strip()
        if not raw_count:
            continue
        counts[document_id] = int(float(raw_count))
    return counts


def _latest_counts_file(data_dir: Path) -> Path:
    candidates = sorted(data_dir.glob("form_counts_*.yaml"))
    if not candidates:
        raise FileNotFoundError(f"no SOI count files found under {data_dir}")
    return candidates[-1]
