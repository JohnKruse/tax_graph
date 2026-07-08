"""Promote vetted draft objects into the live graph."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import yaml


PROMOTABLE_KINDS = ("documents", "nodes", "tables", "rules", "edges", "citations", "decisions")


@dataclass(frozen=True)
class PromotionResult:
    """Filesystem summary for one promoted draft document."""

    document_id: str
    paths: dict[str, Path]


def promote_draft_document(
    document_id: str,
    *,
    year: str | int = "2025",
    root: str | Path | None = None,
    kinds: tuple[str, ...] = PROMOTABLE_KINDS,
    documents_override: dict[str, Any] | None = None,
) -> PromotionResult:
    """Copy one draft document's authored objects into live graph YAML files."""
    root_path = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[1]
    graph_dir = root_path / "graph" / str(year)
    draft_dir = graph_dir / "_drafts" / document_id
    if not draft_dir.is_dir():
        raise FileNotFoundError(f"draft directory not found for {document_id}: {draft_dir}")

    file_stem = _document_file_stem(document_id)
    written: dict[str, Path] = {}
    for kind in kinds:
        source_path = draft_dir / f"{kind}.yaml"
        if not source_path.exists():
            continue
        payload = yaml.safe_load(source_path.read_text(encoding="utf-8"))
        if kind == "documents":
            payload = _normalize_document_payload(document_id, payload, documents_override)
        elif payload is None:
            continue
        target_path = graph_dir / kind / f"{file_stem}.yaml"
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=False),
            encoding="utf-8",
            newline="\n",
        )
        written[kind] = target_path
    return PromotionResult(document_id=document_id, paths=written)


def _normalize_document_payload(
    document_id: str,
    payload: Any,
    override: dict[str, Any] | None,
) -> dict[str, Any]:
    if isinstance(payload, list):
        matches = [item for item in payload if isinstance(item, dict) and item.get("document_id") == document_id]
        if len(matches) != 1:
            raise ValueError(f"expected exactly one document object for {document_id}")
        document = dict(matches[0])
    elif isinstance(payload, dict):
        document = dict(payload)
    else:
        raise ValueError(f"invalid document payload for {document_id}")
    if override:
        document.update(override)
    return document


def _document_file_stem(document_id: str) -> str:
    stem = re.sub(r"_20[0-9]{2}$", "", document_id)
    stem = stem.removeprefix("instructions_")
    return stem.replace("_", "-")
