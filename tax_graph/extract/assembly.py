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
    line_kinds: dict[Any, str] | None = None,
    line_children: dict[Any, list[str]] | None = None,
    resolution_events: list[dict[str, Any]] | None = None,
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
        line_kinds=line_kinds,
        line_children=line_children,
        resolution_events=resolution_events,
    )
    objects: list[DraftObject] = []
    node_ids_by_name: dict[str, str] = {}
    emitted_nodes: set[str] = set()
    emitted_citations: set[str] = set()

    for step_index, step in enumerate(steps, 1):
        operation = str(step.get("operation", ""))
        if operation not in allowed_operations:
            raise ValueError(f"unsupported operation: {operation}")
        inputs = step.get("inputs", [])
        _validate_operation_inputs(operation, inputs)

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
        rendered = render_expression(
            operation,
            _line_label(outline_node.line_anchor),
            [
                {
                    "name": str(item.get("name", "")),
                    "role": str(item.get("role") or _default_role(operation, index)),
                }
                for index, item in enumerate(inputs, 1)
                if isinstance(item, dict)
            ],
        )
        objects.append(
            DraftObject(
                "rules",
                {
                    "rule_id": rule_id,
                    "operation": operation,
                    "description": rendered,
                    "citation_refs": citation_refs,
                },
                _source_span_text(span_ids, spans_by_id),
                model,
                1.0,
            )
        )

        for input_index, input_item in enumerate(inputs, 1):
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
    line_kinds: dict[Any, str] | None,
    line_children: dict[Any, list[str]] | None,
    resolution_events: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Translate line-number output into one deterministic operation step."""
    if "operation_plan" in plan:
        return list(plan.get("operation_plan", []))

    source_lines = plan.get("source_lines", [])
    inputs: list[dict[str, str]] = []
    operation = str(plan.get("operation", ""))
    for source_line in source_lines:
        source_id = _resolve_source_line(document, source_line, line_index=line_index)
        source_key = _line_reference_key(document, source_line)
        candidates = _line_ref_candidates(
            document,
            source_line,
            line_index=line_index,
            line_children=line_children,
        )
        is_heading = bool(source_key and line_kinds and line_kinds.get(source_key) == "heading")
        expand = bool(candidates) and (source_id is None or is_heading)
        if expand and (len(candidates) == 1 or (is_heading and operation in _EXPANDABLE_OPERATIONS)):
            inputs.extend({"name": candidate} for candidate in candidates)
            if resolution_events is not None:
                resolution_events.append(
                    {
                        "source_line": source_line,
                        "resolved_to": list(candidates),
                        "reason": "resolved through deterministic lettered child lines",
                    }
                )
            continue
        if source_id is None:
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
        inputs.append({"name": source_id})

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
    key = _line_reference_key(document, source_line)
    if key is None:
        return None
    index = line_index or {}
    for candidate in (key, key[1]):
        if candidate in index:
            return index[candidate]
    if key[0] == document.document_id.lower() and line_index is None:
        return _slug(f"{document.document_id}_root_line_{key[1]}")
    return None


def _line_ref_candidates(
    document: SourceDocumentInput,
    source_line: Any,
    *,
    line_index: dict[Any, str] | None,
    line_children: dict[Any, list[str]] | None = None,
) -> list[str]:
    """Return lettered children when a bare parent reference cannot be chosen."""
    if not isinstance(source_line, (str, dict)):
        return []
    key = _line_reference_key(document, source_line)
    if key is None:
        return []
    form, anchor = key
    if line_children and key in line_children:
        return sorted(set(line_children[key]))
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


_EXPANDABLE_OPERATIONS = frozenset({"SUM", "MIN", "MAX", "AND", "OR"})


def _line_reference_key(
    document: SourceDocumentInput,
    source_line: Any,
) -> tuple[str, str] | None:
    """Normalize a model's printed line reference to a form/anchor key."""
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
    return form, anchor


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
    if operation == "COPY":
        return "source"
    if operation == "SUBTRACT":
        return "minuend" if input_index == 1 else "subtrahend"
    if operation == "DIVIDE":
        return "numerator" if input_index == 1 else "denominator"
    if operation in {"MULTIPLY"}:
        return "multiplicand" if input_index == 1 else "multiplier"
    if operation in {"NEGATE", "ABS", "ROUND"}:
        return "amount"
    if operation in {"MIN", "MAX", "AND", "OR"}:
        return "candidate"
    if operation == "REQUIRE_INPUT":
        return "input"
    return "addend"


def _validate_operation_inputs(operation: str, inputs: Any) -> None:
    """Fail closed when an expression cannot preserve operand meaning."""
    if not isinstance(inputs, list):
        raise FormulaAssemblyFinding(
            {"code": "invalid_operand_shape", "operation": operation, "reason": "operation inputs must be a list"}
        )
    exact_arity = {
        "COPY": 1,
        "NEGATE": 1,
        "ABS": 1,
        "ROUND": 1,
        "REQUIRE_INPUT": 1,
        "NOT": 1,
        "SUBTRACT": 2,
        "DIVIDE": 2,
        "MULTIPLY": 2,
        "COMPARE": 2,
        "IF": 2,
        "IF_ELSE": 4,
    }
    expected_roles = {
        "COPY": {"source"},
        "NEGATE": {"amount"},
        "ABS": {"amount"},
        "ROUND": {"amount"},
        "REQUIRE_INPUT": {"input"},
        "NOT": {"operand"},
        "SUBTRACT": {"minuend", "subtrahend"},
        "DIVIDE": {"numerator", "denominator"},
        "MULTIPLY": {"multiplicand", "multiplier"},
        "COMPARE": {"left", "right"},
        "IF": {"condition", "when_true"},
        "IF_ELSE": {"condition", "threshold", "when_true", "when_false"},
        "MIN": {"candidate"},
        "MAX": {"candidate"},
        "AND": {"candidate"},
        "OR": {"candidate"},
    }
    expected = exact_arity.get(operation)
    if expected is not None and len(inputs) != expected:
        raise FormulaAssemblyFinding(
            {
                "code": "invalid_operand_arity",
                "operation": operation,
                "observed": len(inputs),
                "expected": expected,
                "reason": f"{operation} requires exactly {expected} operand(s)",
            }
        )
    roles = expected_roles.get(operation)
    if roles is None:
        return
    observed = {
        str(item.get("role") or _default_role(operation, index))
        for index, item in enumerate(inputs, 1)
        if isinstance(item, dict)
    }
    if operation in {"MIN", "MAX", "AND", "OR"}:
        valid = observed == roles
    else:
        valid = observed == roles
    if not valid:
        raise FormulaAssemblyFinding(
            {
                "code": "invalid_operand_roles",
                "operation": operation,
                "observed": sorted(observed),
                "expected": sorted(roles),
                "reason": f"{operation} operand roles do not preserve computation order",
            }
        )


def _line_label(anchor: Any) -> str:
    value = str(anchor or "").strip()
    return f"line {value}" if value else "this line"


def _operand_label(name: str) -> str:
    """Turn an internal source name into a reviewer-safe short label."""
    value = str(name or "").strip()
    match = re.search(r"(?:^|_)line_([0-9]+[a-z]?)(?:_|$)", value.lower())
    if match:
        return f"line {match.group(1)}"
    if value.startswith("column_"):
        return value.replace("_minus_", " minus ").replace("column_", "column ")
    return value.replace("_", " ") or "unresolved source"


def render_expression(operation: str, target: str, inputs: list[dict[str, Any]]) -> str:
    """Render one structured expression in the form shown to humans and models."""
    labels = [_operand_label(str(item.get("name", ""))) for item in inputs]
    roles = {str(item.get("role", "")): label for item, label in zip(inputs, labels, strict=False)}
    op = str(operation).upper()
    if op == "COPY" and labels:
        return f"{target} = {labels[0]}"
    if op == "SUM" and labels:
        return f"{target} = " + " + ".join(labels)
    if op == "SUBTRACT" and {"minuend", "subtrahend"} <= set(roles):
        return f"{target} = {roles['minuend']} - {roles['subtrahend']}"
    if op == "DIVIDE" and {"numerator", "denominator"} <= set(roles):
        return f"{target} = {roles['numerator']} / {roles['denominator']}"
    if op == "MULTIPLY" and {"multiplicand", "multiplier"} <= set(roles):
        return f"{target} = {roles['multiplicand']} * {roles['multiplier']}"
    if op in {"MIN", "MAX"} and labels:
        return f"{target} = {op.lower()}(" + ", ".join(labels) + ")"
    if op == "NEGATE" and labels:
        return f"{target} = -{labels[0]}"
    if op == "REQUIRE_INPUT":
        return f"{target} = entered by filer"
    return f"{target} = {op.lower()}(" + ", ".join(labels) + ")"


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
