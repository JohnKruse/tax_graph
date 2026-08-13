"""Measure the deterministic before/after face-extent policy."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
from typing import Any, Iterable

import yaml

from tax_graph.acquire.manifest import load_manifest
from tax_graph.extract.cells import (
    build_cell_frame_from_document,
    compare_form_face_text_with_extent,
)
from tax_graph.extract.inputs import load_document_input


FACE_EXTENT_KINDS = frozenset({"tax_form", "schedule", "source_document"})
# The 696-row S102 face corpus excludes the review-cycle Form 2441 face.
FACE_EXTENT_EXCLUSIONS = frozenset({"form_2441_2025"})
_ABSORBED_BLOCK_RE = re.compile(
    r"\b(?:note\.|otherwise\b|go\s+to\s+line\b|skip\s+lines?\b|also\s+enter\b)",
    re.IGNORECASE,
)
_ABRUPT_FACE_ENDS = frozenset(
    {"and", "box", "leave", "line", "must", "or", "than", "the"}
)
_STRUCTURAL_SUFFIX_RE = re.compile(
    r"^(?:"
    r"[0-9]+[a-z]?\s*(?:[.)]?\s*(?:\(\s*\)|_+|field\b)|\*?\s*$)"
    r"|[\"']?\s*field\b"
    r")",
    re.IGNORECASE,
)
_EMBEDDED_ANCHOR_SUFFIX_RE = re.compile(r"^[0-9]+[a-z]?\s+(?=[a-z])", re.IGNORECASE)
_ROUTING_SUFFIX_RE = re.compile(
    r"^(?:note\.|if\b|otherwise\b|go\b|skip\b|also\s+enter\b)",
    re.IGNORECASE,
)


def _normalized(value: Any) -> str:
    """Normalize whitespace for deterministic face comparisons."""
    return " ".join(str(value or "").split()).strip().casefold()


def _classification(before: str, after: str) -> tuple[str, str]:
    """Classify one changed face with a visible boundary-quality reason.

    Containment is necessary but not sufficient: a printed row number can
    occur inside the prose, and the shorter bracket can stop there. Such a
    face is reported as truncated rather than being accepted because it is a
    substring. The checks are deliberately textual and deterministic; they
    are a measurement aid, not a semantic approval.
    """
    old = _normalized(before)
    new = _normalized(after)
    if old == new:
        return "neutral", "same_normalized_face"
    if not new or new not in old:
        return "truncated", "not_contained_in_legacy_face"
    start = old.find(new)
    suffix = old[start + len(new) :].strip()
    tail = re.findall(r"[A-Za-z]+$", new)
    tail_word = tail[-1].casefold() if tail else ""
    if _EMBEDDED_ANCHOR_SUFFIX_RE.match(suffix):
        return "truncated", "embedded_anchor_before_prose"
    if tail_word in _ABRUPT_FACE_ENDS and not _STRUCTURAL_SUFFIX_RE.match(suffix):
        return "truncated", "abrupt_clause_end"
    if _STRUCTURAL_SUFFIX_RE.match(suffix):
        return "improved", "printed_field_scaffold_removed"
    if _ROUTING_SUFFIX_RE.match(suffix):
        return "improved", "routing_tail_removed"
    return "improved", "strict_substring"


def _absorbed_block(before: str, after: str) -> bool:
    """Detect a removed routing/note block in the old face projection."""
    old = _normalized(before)
    new = _normalized(after)
    if not old or not new or old == new or new not in old:
        return False
    removed = old.replace(new, " ", 1)
    return bool(_ABSORBED_BLOCK_RE.search(removed))


def _default_document_ids(root: Path, year: str) -> list[str]:
    """Return the deterministic 696-row face corpus for one tax year."""
    manifest = load_manifest(root=root)
    return [
        entry.document_id
        for entry in manifest.documents
        if entry.document_id not in FACE_EXTENT_EXCLUSIONS
        and (entry.is_region or entry.kind in FACE_EXTENT_KINDS)
    ]


def build_face_extent_report(
    *,
    root: str | Path,
    year: str | int = "2025",
    document_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Build a complete deterministic before/after face report.

    The report is a measurement artifact. It never writes graph state and it
    never treats a shorter bracket as safe merely because it is shorter.
    """
    root_path = Path(root).resolve()
    year_text = str(year)
    ids = list(document_ids) if document_ids is not None else _default_document_ids(root_path, year_text)
    records: list[dict[str, Any]] = []
    absorbed_before: list[dict[str, Any]] = []
    absorbed_residual: list[dict[str, Any]] = []

    for document_id in ids:
        document = load_document_input(document_id, year=year_text, root=root_path)
        frame = build_cell_frame_from_document(document)
        for row in frame.rows:
            extent = row.metadata.get("clause_extent") or {}
            comparison = compare_form_face_text_with_extent(
                str(row.metadata.get("form_face_before") or row.form_face_text),
                row.line,
                bracket_text=str(
                    extent.get("bracket_text") or extent.get("bracket_face") or ""
                ),
            )
            before = str(comparison["before_face"] or "")
            after = str(comparison["after_face"] or "")
            changed = before != after
            classification, classification_reason = _classification(before, after)
            record = {
                "document_id": document_id,
                "line": row.line,
                "label": row.label,
                "before": before,
                "after": after,
                "changed": changed,
                "classification": classification,
                "classification_reason": classification_reason,
                "bracket_available": bool(extent.get("bracket_available")),
                "selection_reason": str(extent.get("selection_reason") or ""),
            }
            records.append(record)
            if _absorbed_block(before, after):
                absorbed_before.append(record)
                if _ABSORBED_BLOCK_RE.search(_normalized(after)):
                    absorbed_residual.append(record)

    changed = [record for record in records if record["changed"]]
    classification_counts = {
        name: sum(record["classification"] == name for record in changed)
        for name in ("improved", "neutral", "truncated")
    }
    return {
        "year": year_text,
        "documents": sorted(set(record["document_id"] for record in records)),
        "excluded_documents": sorted(FACE_EXTENT_EXCLUSIONS),
        "counts": {
            "rows": len(records),
            "bracket_available": sum(record["bracket_available"] for record in records),
            "changed": len(changed),
            "classification": classification_counts,
            "absorbed_block_rows_before": len(absorbed_before),
            "absorbed_block_rows_residual": len(absorbed_residual),
        },
        "absorbed_block_rows_before": absorbed_before,
        "absorbed_block_rows_residual": absorbed_residual,
        "rows": records,
    }


def main() -> int:
    """Write the report to a caller-selected path."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--year", default="2025")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_face_extent_report(root=args.root, year=args.year)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        yaml.safe_dump(report, sort_keys=False, allow_unicode=False),
        encoding="ascii",
    )
    print(f"face extent report written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
