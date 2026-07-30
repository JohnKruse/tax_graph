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


class FormulaAssemblyFinding(ValueError):
    """Raised when a model line reference cannot be resolved safely."""

    def __init__(self, finding: dict[str, Any]):
        self.finding = finding
        super().__init__(str(finding.get("reason", "formula assembly finding")))


def assemble_formula_plan(
    document: SourceDocumentInput,
    outline_node: OutlineNode,
    plan: dict[str, Any],
    spans: list[CandidateSpan],
    *,
    model: str = "micro-extraction",
    root: str | Path | None = None,
    line_index: dict[Any, str] | None = None,
) -> ExtractionBatch:
    """Convert an intermediate operation plan into canonical draft objects."""
    allowed_operations = set(closed_operations(root=root))
    spans_by_id = {span.span_id: span for span in spans}
    human_answer = "operation_plan" not in plan
    steps = _steps_for_plan(
        document,
        outline_node,
        plan,
        spans,
        line_index=line_index,
    )
    objects: list[DraftObject] = []
    node_ids_by_name: dict[str, str] = {}
    emitted_nodes: set[str] = set()
    emitted_citations: set[str] = set()

    for step_index, step in enumerate(steps, 1):
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
        target_id = (
            _canonical_target_id(document, outline_node)
            if human_answer
            else _node_id(document.document_id, outline_node.outline_id, output_name)
        )
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
            source_id = input_name if human_answer else node_ids_by_name.get(input_name)
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
            if human_answer and source_id == target_id:
                raise FormulaAssemblyFinding(
                    {
                        "code": "self_referential_source_line",
                        "target_cell_id": target_id,
                        "source_line": input_name,
                        "reason": "source line resolves to the target cell",
                    }
                )
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


def _steps_for_plan(
    document: SourceDocumentInput,
    outline_node: OutlineNode,
    plan: dict[str, Any],
    spans: list[CandidateSpan],
    *,
    line_index: dict[Any, str] | None,
) -> list[dict[str, Any]]:
    """Translate line-number output into one deterministic operation step."""
    if "operation_plan" in plan:
        return list(plan.get("operation_plan", []))

    source_lines = plan.get("source_lines", [])
    inputs: list[dict[str, str]] = []
    for source_line in source_lines:
        source_id = _resolve_source_line(document, source_line, line_index=line_index)
        if source_id is None:
            candidates = _line_ref_candidates(document, source_line, line_index=line_index)
            code = "ambiguous_parent_source_line" if candidates else "unresolved_source_line"
            raise FormulaAssemblyFinding(
                {
                    "code": code,
                    "target_cell_id": _canonical_target_id(document, outline_node),
                    "source_line": source_line,
                    "candidates": candidates,
                    "reason": (
                        "bare source line is ambiguous because only lettered child lines exist"
                        if candidates
                        else "source line is not present in the deterministic outline index"
                    ),
                }
            )
        inputs.append({"name": source_id, "role": "addend"})

    quote = str(plan.get("quote", ""))
    citation_span_ids = [
        span.span_id
        for span in spans
        if _quote_matches(quote, span.text)
    ][:1]
    output = f"line_{outline_node.line_anchor}" if outline_node.line_anchor else outline_node.outline_id
    return [
        {
            "output": output,
            "operation": str(plan.get("operation", "")),
            "inputs": inputs,
            "citation_span_ids": citation_span_ids,
        }
    ]


def _resolve_source_line(
    document: SourceDocumentInput,
    source_line: Any,
    *,
    line_index: dict[Any, str] | None,
) -> str | None:
    """Resolve a printed line through the supplied outline index only."""
    if isinstance(source_line, str):
        form = document.document_id
        anchor = source_line.strip().lower().removeprefix("line ").strip()
    elif isinstance(source_line, dict):
        form = str(source_line.get("form", "")).strip().lower()
        anchor = str(source_line.get("line", "")).strip().lower().removeprefix("line ").strip()
    else:
        return None
    if not anchor:
        return None
    current_form = document.document_id.lower()
    normalized_form = re.sub(r"[^a-z0-9]+", "", form)
    normalized_current = re.sub(r"[^a-z0-9]+", "", current_form)
    current_stem = current_form.removesuffix(f"_{document.year}")
    same_form_alias = normalized_form in {"", _compact(current_form), _compact(current_stem)}
    if "form1040" in normalized_form and "form1040" in normalized_current:
        same_form_alias = True
    if same_form_alias:
        form = current_form
    elif not form.endswith(f"_{document.year}"):
        form = f"{form}_{document.year}"

    index = line_index or {}
    for key in ((form, anchor), anchor):
        if key in index:
            return index[key]
    if form == current_form and line_index is None:
        return _slug(f"{document.document_id}_root_line_{anchor}")
    return None


def _line_ref_candidates(
    document: SourceDocumentInput,
    source_line: Any,
    *,
    line_index: dict[Any, str] | None,
) -> list[str]:
    """Return lettered children when a bare parent reference cannot be chosen."""
    if not isinstance(source_line, (str, dict)):
        return []
    raw_form = source_line if isinstance(source_line, str) else source_line.get("form", "")
    raw_anchor = source_line if isinstance(source_line, str) else source_line.get("line", "")
    anchor = str(raw_anchor).strip().lower().removeprefix("line ").strip()
    form = str(raw_form or document.document_id).strip().lower()
    current_form = document.document_id.lower()
    if _compact(form) in {_compact(current_form), _compact(current_form.removesuffix(f"_{document.year}"))}:
        form = current_form
    index = line_index or {}
    candidates = [
        value
        for key, value in index.items()
        if isinstance(key, tuple)
        and len(key) == 2
        and key[0] == form
        and str(key[1]).startswith(anchor)
        and len(str(key[1])) == len(anchor) + 1
        and str(key[1])[-1].isalpha()
    ]
    return sorted(set(candidates))


def _canonical_target_id(document: SourceDocumentInput, outline_node: OutlineNode) -> str:
    """Return the stable outline-derived id for the formula cell."""
    return _slug(f"{document.document_id}_{outline_node.outline_id}")


def _quote_matches(quote: str, source: str) -> bool:
    normalize = lambda value: " ".join(str(value).split())
    return normalize(quote) in normalize(source) or normalize(source) in normalize(quote)


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


def _compact(value: str) -> str:
    """Normalize a human form label for deterministic same-form matching."""
    return re.sub(r"[^a-z0-9]+", "", value.lower())
