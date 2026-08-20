"""Explain one persisted extraction cell without running extraction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tax_graph.extract.assembly import _line_reference_key, _resolve_source_line
from tax_graph.extract.models import SourceDocumentInput
from tax_graph.io.loader import load_yaml


def explain_cell(
    draft_root: str | Path,
    *,
    document_id: str,
    year: str | int,
    line: str,
) -> dict[str, Any]:
    """Return the five persisted evidence layers for one draft cell.

    This reader deliberately loads only the draft YAML.  It does not acquire
    source documents, construct an LLM client, or regenerate any artifact.
    """
    root = Path(draft_root)
    outline = _mapping(root / "outline.yaml")
    micro = _mapping(root / "micro_extraction.yaml")
    spans = _sequence(root / "candidate_spans.yaml")
    anchor = str(line).strip().lower()
    node = _find_outline_node(outline.get("children", []), anchor)
    if node is None:
        raise ValueError(f"line {line!r} is not present in {root / 'outline.yaml'}")

    target_cell_id = f"{document_id}_{node.get('outline_id', '')}"
    model_record, record_source = _find_cell_record(micro, target_cell_id, anchor)
    finding = _find_finding(micro, target_cell_id, anchor)
    source_line = _planned_source_line(model_record, finding)
    document = SourceDocumentInput(
        document_id=document_id,
        kind="tax_form",
        year=str(year),
        url="",
        text="",
        text_path=root / "outline.yaml",
    )
    line_index = _outline_line_index(document_id, outline.get("children", []))
    key = _line_reference_key(document, source_line) if source_line is not None else None
    resolved = _resolve_source_line(document, source_line, line_index=line_index) if source_line is not None else None
    lookup_keys = []
    if key is not None:
        lookup_keys = [key, key[1]]
    matched_key = next((candidate for candidate in lookup_keys if candidate in line_index), None)
    instruction_ids = list((model_record or {}).get("instruction_span_ids") or [])
    instruction_spans = _instruction_spans(spans, instruction_ids, document_id, anchor)

    return {
        "cell": {
            "document_id": document_id,
            "line": anchor,
            "target_cell_id": target_cell_id,
        },
        "form_face": {
            "outline_id": node.get("outline_id"),
            "label": node.get("label", ""),
            "page": node.get("page"),
        },
        "instruction": {
            "spans": instruction_spans,
        },
        "model": {
            "record_source": record_source,
            "record": model_record,
        },
        "finding": finding,
        "resolver": {
            "planned_operand": source_line,
            "computed_key": list(key) if key is not None else None,
            "computed_key_text": repr(key),
            "searched": "outline index",
            "lookup_keys": [list(item) if isinstance(item, tuple) else item for item in lookup_keys],
            "matched_key": list(matched_key) if isinstance(matched_key, tuple) else matched_key,
            "resolved_source_id": resolved,
            "found": resolved is not None,
        },
    }


def format_explanation(explanation: dict[str, Any]) -> str:
    """Render one explanation as five readable, machine-quotable sections."""
    labels = (
        ("form-face", "form_face"),
        ("instruction", "instruction"),
        ("model plan or outcome", "model"),
        ("finding", "finding"),
        ("resolver", "resolver"),
    )
    lines = [
        f"=== explain-cell: {explanation['cell']['document_id']} line {explanation['cell']['line']} ==="
    ]
    for title, key in labels:
        lines.append(f"=== {title} ===")
        lines.append(json.dumps(explanation[key], indent=2, sort_keys=True, ensure_ascii=True))
    return "\n".join(lines) + "\n"


def _mapping(path: Path) -> dict[str, Any]:
    value = load_yaml(path)
    if not isinstance(value, dict):
        raise ValueError(f"expected a mapping in {path}")
    return value


def _sequence(path: Path) -> list[dict[str, Any]]:
    value = load_yaml(path)
    if not isinstance(value, list):
        raise ValueError(f"expected a list in {path}")
    return [item for item in value if isinstance(item, dict)]


def _find_outline_node(nodes: list[Any], anchor: str) -> dict[str, Any] | None:
    for item in nodes:
        if not isinstance(item, dict):
            continue
        if str(item.get("line_anchor", "")).strip().lower() == anchor:
            return item
        found = _find_outline_node(item.get("children", []), anchor)
        if found is not None:
            return found
    return None


def _find_cell_record(
    micro: dict[str, Any],
    target_cell_id: str,
    anchor: str,
) -> tuple[dict[str, Any] | None, str | None]:
    for name in ("formula_cells", "non_formula_cells", "outcomes"):
        for item in micro.get(name, []) or []:
            if not isinstance(item, dict):
                continue
            if item.get("target_cell_id") == target_cell_id or str(item.get("line_anchor", "")).lower() == anchor:
                return item, f"micro_extraction.{name}"
    return None, None


def _find_finding(micro: dict[str, Any], target_cell_id: str, anchor: str) -> dict[str, Any] | None:
    for name in ("findings", "unresolved_line_refs"):
        for item in micro.get(name, []) or []:
            if not isinstance(item, dict):
                continue
            if item.get("target_cell_id") == target_cell_id or str(item.get("line_anchor", "")).lower() == anchor:
                return item
    return None


def _planned_source_line(
    model_record: dict[str, Any] | None,
    finding: dict[str, Any] | None,
) -> Any:
    if finding is not None and finding.get("source_line") is not None:
        return finding["source_line"]
    if model_record is not None and model_record.get("form") and model_record.get("line"):
        return {"form": model_record["form"], "line": model_record["line"]}
    return None


def _instruction_spans(
    spans: list[dict[str, Any]],
    instruction_ids: list[str],
    document_id: str,
    anchor: str,
) -> list[dict[str, Any]]:
    by_id = {str(item.get("span_id")): item for item in spans}
    selected = [by_id[span_id] for span_id in instruction_ids if span_id in by_id]
    if selected:
        return [
            {
                "span_id": item.get("span_id"),
                "locator": item.get("locator"),
                "text": item.get("text", ""),
            }
            for item in selected
        ]
    return [
        {
            "span_id": item.get("span_id"),
            "locator": item.get("locator"),
            "text": item.get("text", ""),
        }
        for item in spans
        if item.get("relationship") == "instructions"
        and item.get("owner_document_id") == document_id
        and anchor in {str(value).lower() for value in item.get("owner_lines", [])}
    ]


def _outline_line_index(document_id: str, nodes: list[Any]) -> dict[tuple[str, str], str]:
    index: dict[tuple[str, str], str] = {}

    def visit(items: list[Any]) -> None:
        for item in items:
            if not isinstance(item, dict):
                continue
            anchor = str(item.get("line_anchor", "")).strip().lower()
            outline_id = str(item.get("outline_id", "")).strip()
            if anchor and outline_id:
                index[(document_id.lower(), anchor)] = f"{document_id}_{outline_id}"
            visit(item.get("children", []))

    visit(nodes)
    return index
