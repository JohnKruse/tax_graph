"""Deterministic assembly from micro-extraction results."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from tax_graph.extract.models import DraftObject, ExtractionBatch, SourceDocumentInput
from tax_graph.extract.outline import (
    CandidateSpan,
    OutboundFlow,
    OutlineNode,
    infer_value_type,
    node_type_for_outline,
)
from tax_graph.extract.prompts import closed_operations


def assemble_formula_plan(
    document: SourceDocumentInput,
    outline_node: OutlineNode,
    plan: dict[str, Any],
    spans: list[CandidateSpan],
    *,
    model: str = "micro-extraction",
    root: str | Path | None = None,
) -> ExtractionBatch:
    """Convert an intermediate operation plan into canonical draft objects."""
    allowed_operations = set(closed_operations(root=root))
    spans_by_id = {span.span_id: span for span in spans}
    objects: list[DraftObject] = []
    node_ids_by_name: dict[str, str] = {}
    emitted_nodes: set[str] = set()
    emitted_citations: set[str] = set()

    for step_index, step in enumerate(plan.get("operation_plan", []), 1):
        operation = str(step.get("operation", ""))
        if operation not in allowed_operations:
            raise ValueError(f"unsupported operation: {operation}")

        span_ids = [str(span_id) for span_id in step.get("citation_span_ids", [])]
        citation_refs = []
        for span_id in span_ids:
            span = spans_by_id[span_id]
            citation_id = f"cite_{_slug(span_id)}"
            citation_refs.append(citation_id)
            if citation_id not in emitted_citations:
                objects.append(_citation_object(citation_id, span, model))
                emitted_citations.add(citation_id)

        raw_output_name = str(step.get("output", f"step_{step_index}"))
        output_name = _normalized_output_name(step, raw_output_name)
        target_id = _node_id(document.document_id, outline_node.outline_id, output_name)
        node_ids_by_name[raw_output_name] = target_id
        node_ids_by_name[output_name] = target_id
        if target_id not in emitted_nodes:
            objects.append(
                _node_object(
                    document,
                    outline_node,
                    target_id,
                    output_name,
                    citation_refs,
                    model,
                    computed=True,
                )
            )
            emitted_nodes.add(target_id)

        rule_id = f"rule_{_slug(target_id)}_{operation.lower()}"
        objects.append(
            DraftObject(
                "rules",
                {
                    "rule_id": rule_id,
                    "operation": operation,
                    "description": f"Compute {output_name} for {outline_node.label}.",
                    "citation_refs": citation_refs,
                },
                _source_span_text(span_ids, spans_by_id),
                model,
                1.0,
            )
        )

        for input_index, input_item in enumerate(step.get("inputs", []), 1):
            input_name = str(input_item.get("name", f"input_{input_index}"))
            source_id = node_ids_by_name.get(input_name)
            if source_id is None:
                source_id = _node_id(document.document_id, outline_node.outline_id, input_name)
                node_ids_by_name[input_name] = source_id
                if source_id not in emitted_nodes:
                    objects.append(
                        _node_object(
                            document,
                            outline_node,
                            source_id,
                            input_name,
                            citation_refs,
                            model,
                            computed=False,
                        )
                    )
                    emitted_nodes.add(source_id)
            role = str(input_item.get("role") or _default_role(operation, input_index))
            objects.append(
                DraftObject(
                    "edges",
                    {
                        "edge_id": f"e_{_slug(source_id)}_to_{_slug(target_id)}_{_slug(role)}",
                        "source": source_id,
                        "target": target_id,
                        "relationship": "CALCULATES",
                        "rule_id": rule_id,
                        "role": role,
                        "citation_refs": citation_refs,
                    },
                    _source_span_text(span_ids, spans_by_id),
                    model,
                    1.0,
                )
            )

    return ExtractionBatch(document_id=document.document_id, year=document.year, objects=objects)


def realize_outbound_flows(
    flows: list[OutboundFlow],
    *,
    target_node_ids: dict[tuple[str, str], str],
    spans: list[CandidateSpan] | None = None,
    model: str = "outbound-linker",
    rule_id: str = "copy_currency_value",
) -> list[DraftObject]:
    """Realize outbound flow declarations into edges when targets exist."""
    objects: list[DraftObject] = []
    spans_by_id = {span.span_id: span for span in spans or []}
    emitted_citations: set[str] = set()
    for flow in flows:
        target_node_id = target_node_ids.get((flow.target_document_id, flow.target_line))
        if not target_node_id:
            continue
        citation_refs = [f"cite_{_slug(span_id)}" for span_id in flow.citation_span_ids]
        for span_id, citation_id in zip(flow.citation_span_ids, citation_refs, strict=False):
            span = spans_by_id.get(span_id)
            if span and citation_id not in emitted_citations:
                objects.append(_citation_object(citation_id, span, model))
                emitted_citations.add(citation_id)
        objects.append(
            DraftObject(
                "edges",
                {
                    "edge_id": _slug(f"e_{flow.source_node_id}_to_{target_node_id}"),
                    "source": flow.source_node_id,
                    "target": target_node_id,
                    "relationship": "FEEDS",
                    "rule_id": rule_id,
                    "citation_refs": citation_refs,
                },
                "",
                model,
                flow.confidence,
            )
        )
    return objects


def _citation_object(citation_id: str, span: CandidateSpan, model: str) -> DraftObject:
    return DraftObject(
        "citations",
        {
            "citation_id": citation_id,
            "document_id": span.document_id,
            "locator": span.locator,
            "quoted_text": span.text,
        },
        span.text,
        model,
        1.0,
    )


def _node_object(
    document: SourceDocumentInput,
    outline_node: OutlineNode,
    node_id: str,
    name: str,
    citation_refs: list[str],
    model: str,
    *,
    computed: bool,
) -> DraftObject:
    data: dict[str, Any] = {
        "node_id": node_id,
        "document_id": document.document_id,
        "label": _label(name),
        "node_type": "computed" if computed else node_type_for_outline(outline_node),
        "value_type": "currency" if computed else infer_value_type(outline_node, document=document),
    }
    if citation_refs:
        data["citation_refs"] = citation_refs
    return DraftObject("nodes", data, "", model, 1.0)


def _source_span_text(span_ids: list[str], spans_by_id: dict[str, CandidateSpan]) -> str:
    return "\n".join(spans_by_id[span_id].text for span_id in span_ids if span_id in spans_by_id)


def _default_role(operation: str, input_index: int) -> str:
    if operation == "SUBTRACT":
        return "minuend" if input_index == 1 else "subtrahend"
    if operation == "DIVIDE":
        return "numerator" if input_index == 1 else "denominator"
    return "addend"


def _normalized_output_name(step: dict[str, Any], fallback: str) -> str:
    operation = str(step.get("operation", ""))
    if operation == "SUBTRACT":
        inputs = step.get("inputs", [])
        if _has_input(inputs, "column_d", "minuend") and _has_input(inputs, "column_e", "subtrahend"):
            return "column_d_minus_e"
    return fallback


def _has_input(inputs: Any, name: str, role: str) -> bool:
    if not isinstance(inputs, list):
        return False
    for input_index, input_item in enumerate(inputs, 1):
        if not isinstance(input_item, dict):
            continue
        input_role = input_item.get("role") or _default_role("SUBTRACT", input_index)
        if input_item.get("name") == name and input_role == role:
            return True
    return False


def _node_id(document_id: str, outline_id: str, name: str) -> str:
    return _slug(f"{document_id}_{outline_id}_{name}")


def _label(name: str) -> str:
    return name.replace("_", " ").strip().title()


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "item"
