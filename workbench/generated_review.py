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

from workbench.address_verdicts import expression_kind_bucket
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
    non_formula_cells = draft.get("micro_extraction", {}).get("non_formula_cells", [])
    records = [item for item in formula_cells + (non_formula_cells if isinstance(non_formula_cells, list) else []) if isinstance(item, dict)]
    records = _ensure_line_review_records(records, draft.get("outline"), document_id)

    rules = _records(draft.get("rules"))
    edges = _records(draft.get("edges"))
    citations = _citation_index(draft.get("citations"))
    spans = _span_index(draft.get("candidate_spans"))
    instruction_ids_by_line = _instruction_span_index(spans)
    provenance = _provenance(draft.get("metrics"))
    cells_by_anchor = _cells_by_anchor(base.cells)
    generated: list[dict[str, Any]] = []
    for formula in records:
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
        expression = _expression(target, formula, rule, target_edges, base.cells, base_cell)
        rule_citation_ids = [str(value) for value in rule.get("citation_refs", []) or []]
        rule_citations = [citations[value] for value in rule_citation_ids if value in citations]
        record_instruction_ids = [str(value) for value in formula.get("instruction_span_ids", []) or []]
        exact_instruction_ids = instruction_ids_by_line.get(anchor, [])
        instruction_span_ids = (
            exact_instruction_ids
            if instruction_ids_by_line
            else record_instruction_ids
        )
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
            for span_id in instruction_span_ids
            if (span := spans.get(str(span_id))) is not None
        ]
        form_citations = [
            item for item in rule_citations
            if not str(item.get("source_document_id") or item.get("document_id") or "").startswith("instructions_")
        ]
        if not instruction_ids_by_line:
            instruction_citations.extend(
                item for item in rule_citations
                if str(item.get("source_document_id") or item.get("document_id") or "").startswith("instructions_")
            )
        if not rule_citations:
            form_citations = list(base_cell.get("citations") or [])
            form_citations.extend(
                _span_citation(spans[str(span_id)])
                for span_id in formula.get("citation_span_ids", []) or []
                if str(span_id) in spans and spans[str(span_id)].get("relationship") == "source"
            )
        kind = str(expression.get("kind") or "review_gap")
        try:
            risk_bucket = expression_kind_bucket(kind)
        except ValueError:
            risk_bucket = "NOT_REVIEWABLE"
        population_policy = {
            "ARITHMETIC": "computed",
            "COPY": "copied",
            "USER_ENTRY": "user_entered",
            "IMPORTED": "imported",
        }.get(risk_bucket)
        review_gap = str(formula.get("review_gap") or "")
        cell = dict(base_cell)
        cell.update(
            {
                "generated": True,
                "review_source": "draft_only",
                "generated_target_cell_id": target,
                "generated_status": str(formula.get("status") or "review_gap"),
                "generated_model": str(formula.get("model") or provenance["model"]),
                "generated_provider": provenance["provider"],
                "generated_provenance": dict(provenance),
                "expression": expression,
                "operation": str(expression.get("operation") or operation).upper(),
                "inputs": [
                    {
                        "node_id": str(edge.get("source") or ""),
                        "role": str(edge.get("role") or "") or None,
                        "ref": _operand_label(str(edge.get("source") or ""), base.cells),
                        "display_name": _operand_label(str(edge.get("source") or ""), base.cells),
                    }
                    for edge in _effective_edges(str(rule.get("operation") or ""), target_edges)
                    if edge.get("source")
                ],
                "form_citations": form_citations,
                "instruction_citations": instruction_citations,
                "citations": form_citations,
                "review_gap": review_gap or None,
                "risk_bucket": risk_bucket,
                "population_policy": population_policy or "review_gap",
            }
        )
        generated.append(cell)
    if len(generated) != len(records):
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
        "outline": _yaml(draft_dir / "outline.yaml", {}),
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


def _instruction_span_index(spans: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    """Rebuild line ownership from draft spans without importing the pipeline."""
    result: dict[str, list[str]] = {}
    current_document = ""
    current_lines: set[str] = set()
    current_level: int | None = None
    for span_id, span in spans.items():
        if str(span.get("relationship") or "") == "source":
            continue
        document_id = str(span.get("document_id") or "")
        if document_id != current_document:
            current_document = document_id
            current_lines = set()
            current_level = None
        text = str(span.get("text") or "").strip()
        line_heading = re.match(r"^(#{1,6})\s*(?:\*\*)?lines?\s+(.+?)\s*$", text, re.IGNORECASE)
        if line_heading:
            prefix = re.split(r"\s+-\s+|\s*:\s+", line_heading.group(2), maxsplit=1)[0]
            current_lines = {
                token.lower()
                for token in re.findall(r"\b[0-9]+[a-z]?\b", prefix, re.IGNORECASE)
            }
            current_level = len(line_heading.group(1))
            for line in current_lines:
                result.setdefault(line, []).append(span_id)
            continue
        heading = re.match(r"^\s*(#{1,6})\s+", text)
        if heading:
            if current_level is not None and len(heading.group(1)) <= current_level:
                current_lines = set()
                current_level = None
            for line in current_lines:
                result.setdefault(line, []).append(span_id)
            continue
        table_line = re.match(r"^\s*\|\s*(?:\*\*)?([0-9]+[a-z]?)\.", text, re.IGNORECASE)
        owned_lines = {table_line.group(1).lower()} if table_line else current_lines
        for line in owned_lines:
            result.setdefault(line, []).append(span_id)
    return result


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
    cells: list[dict[str, Any]],
    target_cell: dict[str, Any],
) -> dict[str, Any]:
    operation = str(rule.get("operation") or "").upper()
    if not operation:
        return _source_expression(formula, target, target_cell)
    effective_edges = _effective_edges(operation, edges)
    target_ref = _normalize_anchor(target_cell.get("official_ref")) or _normalize_anchor(formula.get("line_anchor"))
    operand_records = [
        {
            "node_id": str(edge.get("source") or ""),
            "role": str(edge.get("role") or "") or None,
            "ref": _operand_label(str(edge.get("source") or ""), cells),
            "display_name": _operand_label(str(edge.get("source") or ""), cells),
        }
        for edge in effective_edges
        if edge.get("source")
    ]
    rendered = _render_expression(operation, target_ref, operand_records)
    expression: dict[str, Any] = {
        "kind": _expression_kind(operation),
        "operation": operation,
        "text": rendered,
        "operands": [
            {
                "kind": "reference",
                "label": item["ref"],
                "text": item["ref"],
                "ref": {"object_type": "node", "object_id": item["node_id"], "display_label": item["ref"]},
            }
            for item in operand_records
        ],
    }
    if formula.get("status") != "complete":
        expression["kind"] = "review_gap"
        expression["reason"] = str(formula.get("review_gap") or "generated expression is incomplete")
    return expression


def _source_expression(formula: dict[str, Any], target: str, target_cell: dict[str, Any]) -> dict[str, Any]:
    """Build a review expression for a non-computed source declaration."""
    source_kind = str(formula.get("source_kind") or "")
    form = str(formula.get("form") or "").strip()
    line = str(formula.get("line") or "").strip()
    box = str(formula.get("box") or "").strip()
    target_ref = _normalize_anchor(target_cell.get("official_ref")) or _normalize_anchor(formula.get("line_anchor"))
    if source_kind == "filer_entry":
        return {
            "kind": "input" if formula.get("status") == "complete" else "review_gap",
            "text": f"line {target_ref} = entered by filer",
            "source": {"kind": "input", "text": "entered by filer"},
        }
    if source_kind in {"form_line", "information_return"} and form and (line or box):
        source_label = _source_label(source_kind, form, line, box)
        kind = "cross_form_fetch" if _compact(form) not in _compact(str(target_cell.get("document_id") or "")) else "copy"
        if formula.get("status") != "complete":
            kind = "review_gap"
        return {
            "kind": kind,
            "text": f"line {target_ref} = {source_label}",
            "source": {"kind": "reference", "label": source_label, "text": source_label},
        }
    return {
        "kind": "review_gap",
        "text": f"line {target_ref} = unresolved source",
        "reason": str(formula.get("review_gap") or "source declaration is unresolved"),
    }


def _ensure_line_review_records(records: list[dict[str, Any]], outline: Any, document_id: str) -> list[dict[str, Any]]:
    """Keep the generated review denominator complete when older drafts lack source records."""
    if document_id != "form_1040_2025" or not isinstance(outline, dict):
        return records
    seen = {_normalize_anchor(item.get("line_anchor")) for item in records}
    children = outline.get("children", []) or []
    for item in _outline_lines(children):
        if not isinstance(item, dict):
            continue
        if item.get("kind") != "line" or not item.get("line_anchor"):
            continue
        anchor = _normalize_anchor(item.get("line_anchor"))
        if not any(char.isdigit() for char in anchor) or anchor in seen:
            continue
        records.append(
            {
                "target_cell_id": f"{document_id}_root_line_{anchor}",
                "line_anchor": anchor,
                "label": str(item.get("label") or ""),
                "status": "review_gap",
                "review_gap": "non-computed source extraction has not been generated",
                "source_kind": None,
                "form": "",
                "line": "",
                "box": "",
                "quote": "",
                "instruction_span_ids": [],
            }
        )
        seen.add(anchor)
    return records


def _outline_lines(items: list[Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        result.append(item)
        result.extend(_outline_lines(item.get("children", []) or []))
    return result


def _effective_edges(operation: str, edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply positional roles only to legacy generated records with missing roles."""
    defaults = {
        "COPY": ("source",),
        "SUBTRACT": ("minuend", "subtrahend"),
        "DIVIDE": ("numerator", "denominator"),
        "MULTIPLY": ("multiplicand", "multiplier"),
        "NEGATE": ("amount",),
        "REQUIRE_INPUT": ("input",),
    }.get(operation, ())
    result = []
    for index, edge in enumerate(edges):
        item = dict(edge)
        if defaults and (not item.get("role") or str(item.get("role")) == "addend") and index < len(defaults):
            item["role"] = defaults[index]
        result.append(item)
    return result


def _expression_kind(operation: str) -> str:
    return {"REQUIRE_INPUT": "input"}.get(operation, operation.lower())


def _render_expression(operation: str, target: str, operands: list[dict[str, Any]]) -> str:
    labels = [str(item.get("ref") or "unresolved source") for item in operands]
    by_role = {str(item.get("role")): label for item, label in zip(operands, labels, strict=False)}
    if operation == "COPY" and labels:
        return f"line {target} = {labels[0]}"
    if operation == "SUM" and labels:
        return f"line {target} = " + " + ".join(labels)
    if operation == "SUBTRACT" and {"minuend", "subtrahend"} <= set(by_role):
        return f"line {target} = {by_role['minuend']} - {by_role['subtrahend']}"
    if operation == "DIVIDE" and {"numerator", "denominator"} <= set(by_role):
        return f"line {target} = {by_role['numerator']} / {by_role['denominator']}"
    if operation == "REQUIRE_INPUT":
        return f"line {target} = entered by filer"
    if operation in {"MIN", "MAX"}:
        return f"line {target} = {operation.lower()}(" + ", ".join(labels) + ")"
    return f"line {target} = {operation.lower()}(" + ", ".join(labels) + ")"


def _operand_label(node_id: str, cells: list[dict[str, Any]]) -> str:
    match = next((cell for cell in cells if str(cell.get("node_id") or "") == node_id), None)
    if match:
        ref = _normalize_anchor(match.get("official_ref"))
        if ref:
            return f"line {ref}"
        name = str(match.get("display_name") or "").strip()
        if name:
            return name
    match = re.search(r"_line_([0-9]+[a-z]?)(?:_|$)", node_id.lower())
    return f"line {match.group(1)}" if match else node_id.replace("_", " ")


def _source_label(source_kind: str, form: str, line: str, box: str) -> str:
    form_label = form.replace("_", " ").strip().title()
    if source_kind == "information_return" and box:
        return f"{form_label} box {box}"
    return f"{form_label}, line {line}" if line else form_label


def _compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _span_citation(span: dict[str, Any]) -> dict[str, Any]:
    return {
        "citation_id": span.get("span_id"),
        "quoted_text": span.get("text"),
        "locator": span.get("locator"),
        "url": None,
        "retrieved_date": None,
        "source_document_id": span.get("document_id"),
        "resolved": True,
    }
