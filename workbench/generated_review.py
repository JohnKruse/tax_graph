"""Project draft-only generated formula cells into the review workbench.

This module is a read-only workbench projection.  It never promotes draft
objects and it never edits the graph.  The form geometry remains the physical
spine; generated draft records only replace the content shown for the small
formula-cell review slice.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import yaml

from workbench.cell_inventory import DocumentCells, build_document_cells


GENERATED_REVIEW_DOCUMENTS = frozenset({
    "form_1040_2025",
    "schedule_1_2025",
    "schedule_a_2025",
})


def build_generated_document_cells(
    root: str | Path,
    year: str | int,
    document_id: str,
    *,
    geometry_entries: list[dict[str, Any]] | None = None,
    page_geometry: list[dict[str, Any]] | None = None,
    include_inputs: bool = True,
) -> DocumentCells:
    """Return the generated formula-cell slice over the physical form cells."""
    base = build_document_cells(
        root,
        year,
        document_id,
        geometry_entries=geometry_entries,
        page_geometry=page_geometry,
        include_inputs=include_inputs,
    )
    if document_id not in GENERATED_REVIEW_DOCUMENTS:
        return base
    draft = _load_draft(Path(root), year, document_id)
    formula_cells = draft.get("micro_extraction", {}).get("formula_cells", [])
    if not isinstance(formula_cells, list):
        raise ValueError(f"generated draft has no formula_cells list: {document_id}")
    if not formula_cells:
        raise ValueError(f"generated draft has no formula cells: {document_id}")

    rules = _records(draft.get("rules"))
    edges = _records(draft.get("edges"))
    citations = _citation_index(draft.get("citations"))
    spans = _span_index(draft.get("candidate_spans"))
    provenance = _provenance(draft.get("metrics"))
    cells_by_anchor = _cells_by_anchor(base.cells)
    generated: list[dict[str, Any]] = []
    for formula in formula_cells:
        if not isinstance(formula, dict):
            continue
        anchor = _normalize_anchor(formula.get("line_anchor"))
        matches = cells_by_anchor.get(anchor, [])
        if not matches:
            # Some legacy address rows carry a stale official_ref, while the
            # geometry label still contains the printed line.  Use that label
            # only as a projection fallback; do not rewrite the address artifact.
            marker = re.compile(rf"(?:^|\s){re.escape(anchor)}\s*-\s*f1_", re.IGNORECASE)
            matches = [
                item for item in base.cells
                if marker.search(str(item.get("display_name") or ""))
                or marker.search(str(item.get("geometry_label") or ""))
            ]
        if not matches:
            raise ValueError(f"generated line has no physical cell: {document_id}:{anchor}")
        target = str(formula.get("target_cell_id") or "")
        base_cell = _choose_cell(matches, target)
        target_rules = [
            item for item in rules
            if str(item.get("rule_id") or "").startswith(f"rule_{target}_")
        ]
        target_edges = [
            item for item in edges
            if str(item.get("target") or "") == target
        ]
        rule = target_rules[0] if target_rules else {}
        operation = str(rule.get("operation") or "REVIEW_GAP").lower()
        expression = _expression(target, formula, rule, target_edges)
        rule_citation_ids = [str(value) for value in rule.get("citation_refs", []) or []]
        rule_citations = [citations[value] for value in rule_citation_ids if value in citations]
        instruction_citations = [
            {
                "citation_id": span_id,
                "quoted_text": span.get("text"),
                "locator": span.get("locator"),
                "url": None,
                "retrieved_date": None,
                "source_document_id": span.get("document_id"),
                "resolved": True,
            }
            for span_id in formula.get("instruction_span_ids", []) or []
            if (span := spans.get(str(span_id))) is not None
        ]
        form_citations = [
            item for item in rule_citations
            if not str(item.get("source_document_id") or item.get("document_id") or "").startswith("instructions_")
        ]
        instruction_citations.extend(
            item for item in rule_citations
            if str(item.get("source_document_id") or item.get("document_id") or "").startswith("instructions_")
        )
        review_gap = str(formula.get("review_gap") or "")
        cell = dict(base_cell)
        cell.update(
            {
                "generated": True,
                "review_source": "draft_only",
                "generated_target_cell_id": target,
                "generated_status": str(formula.get("status") or "review_gap"),
                "generated_model": provenance["model"],
                "generated_provider": provenance["provider"],
                "generated_provenance": dict(provenance),
                "expression": expression,
                "operation": operation,
                "inputs": [
                    {
                        "node_id": str(edge.get("source") or ""),
                        "role": str(edge.get("role") or "") or None,
                    }
                    for edge in target_edges
                    if edge.get("source")
                ],
                "form_citations": form_citations,
                "instruction_citations": instruction_citations,
                "citations": form_citations,
                "review_gap": review_gap or None,
            }
        )
        generated.append(cell)
    if len(generated) != len(formula_cells):
        raise ValueError(f"generated draft cells were not projected: {document_id}")
    generated.sort(key=lambda item: (int(item.get("order", 0)), str(item.get("cell_id"))))
    return DocumentCells(
        document_id=base.document_id,
        cells=generated,
        pages=base.pages,
        page_geometry=base.page_geometry,
    )


def _load_draft(root: Path, year: str | int, document_id: str) -> dict[str, Any]:
    draft_dir = root / "graph" / str(year) / "_drafts" / document_id
    if not draft_dir.is_dir():
        raise ValueError(f"generated draft directory is missing: {draft_dir}")
    return {
        "micro_extraction": _yaml(draft_dir / "micro_extraction.yaml", {}),
        "rules": _yaml(draft_dir / "rules.yaml", []),
        "edges": _yaml(draft_dir / "edges.yaml", []),
        "citations": _yaml(draft_dir / "citations.yaml", []),
        "candidate_spans": _yaml(draft_dir / "candidate_spans.yaml", []),
        "metrics": _yaml(draft_dir / "metrics.yaml", {}),
    }


def _yaml(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return default if value is None else value


def _records(value: Any) -> list[dict[str, Any]]:
    return [item for item in value or [] if isinstance(item, dict)]


def _citation_index(value: Any) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("citation_id")): dict(item)
        for item in _records(value)
        if item.get("citation_id")
    }


def _span_index(value: Any) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("span_id")): dict(item)
        for item in _records(value)
        if item.get("span_id")
    }


def _provenance(metrics: Any) -> dict[str, str]:
    data = metrics if isinstance(metrics, dict) else {}
    calls = _records(data.get("llm_calls"))
    call = next((item for item in calls if item.get("outcome") == "success"), calls[0] if calls else {})
    return {
        "model": str(call.get("resolved_model") or call.get("requested_model") or (data.get("models_used") or ["unknown"])[0]),
        "provider": str(call.get("resolved_provider") or (data.get("providers_used") or ["unknown"])[0]),
        "stage": "draft_micro_extraction",
    }


def _normalize_anchor(value: Any) -> str:
    return re.sub(r"^line\s+", "", str(value or "").strip().lower())


def _cells_by_anchor(cells: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for cell in cells:
        anchor = _normalize_anchor(cell.get("official_ref"))
        if anchor:
            result.setdefault(anchor, []).append(cell)
    return result


def _choose_cell(matches: list[dict[str, Any]], target: str) -> dict[str, Any]:
    exact = [item for item in matches if str(item.get("node_id") or "") == target]
    return exact[0] if exact else matches[0]


def _expression(
    target: str,
    formula: dict[str, Any],
    rule: dict[str, Any],
    edges: list[dict[str, Any]],
) -> dict[str, Any]:
    operation = str(rule.get("operation") or "review_gap").lower()
    expression: dict[str, Any] = {
        "kind": operation,
        "operation": operation.upper(),
        "target_cell_id": target,
        "description": str(rule.get("description") or formula.get("label") or ""),
        "operands": [
            {
                "node_id": str(edge.get("source") or ""),
                "role": str(edge.get("role") or "") or None,
            }
            for edge in edges
            if edge.get("source")
        ],
    }
    if formula.get("status") != "complete":
        expression["kind"] = "review_gap"
    return expression
