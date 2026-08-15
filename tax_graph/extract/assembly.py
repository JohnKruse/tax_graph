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
from tax_graph.operation_registry import OPERATION_SPECS, assign_operation_roles, operation_roles, operation_spec


_LOOKUP_DEFAULT_ROLES = (
    "single",
    "married_filing_separately",
    "head_of_household",
    "qualifying_surviving_spouse",
)


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
    emitted_edge_ids: set[str] = set()

    for step_index, step in enumerate(steps, 1):
        operation = str(step.get("operation", ""))
        if operation not in allowed_operations:
            raise ValueError(f"unsupported operation: {operation}")
        inputs = _normalize_operation_inputs(operation, step.get("inputs", []))
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
            literal_value = input_item.get("literal_value")
            if literal_value is not None:
                source_id = _literal_id(document, outline_node, input_name)
                if source_id in emitted_nodes:
                    source_id = _literal_id(
                        document,
                        outline_node,
                        input_name,
                        role=input_item.get("role"),
                        branch=input_item.get("branch"),
                        input_index=input_index,
                    )
            else:
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
            elif literal_value is not None and source_id not in emitted_nodes:
                objects.append(
                    _node_object(
                        document,
                        outline_node,
                        source_id,
                        input_name,
                        citation_refs,
                        model,
                        computed=False,
                        constant_value=literal_value,
                        constant_value_type=input_item.get("constant_value_type"),
                    )
                )
                emitted_nodes.add(source_id)
            roles = _edge_roles(operation, input_item, input_index)
            if human_answer and source_id == target_id:
                raise FormulaAssemblyFinding(
                    {
                        "code": "self_referential_source_line",
                        "target_cell_id": target_id,
                        "source_line": input_name,
                        "reason": "source line resolves to the target cell",
                    }
                )
            for role in roles:
                edge_id = f"e_{_slug(source_id)}_to_{_slug(target_id)}_{_slug(role)}"
                if edge_id in emitted_edge_ids:
                    edge_id = f"{edge_id}_{input_index}"
                emitted_edge_ids.add(edge_id)
                edge_data = {
                    "edge_id": edge_id,
                    "source": source_id,
                    "target": target_id,
                    "relationship": "CALCULATES",
                    "rule_id": rule_id,
                    "role": role,
                    "citation_refs": citation_refs,
                }
                if input_item.get("branch") is not None:
                    edge_data["branch"] = str(input_item["branch"])
                objects.append(
                    DraftObject(
                        "edges",
                        edge_data,
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
    """Translate line and printed-constant output into one operation step."""
    if "operation_plan" in plan:
        return list(plan.get("operation_plan", []))

    source_lines = plan.get("source_lines", [])
    inputs: list[dict[str, Any]] = []
    operation = str(plan.get("operation", ""))
    for source_line in source_lines:
        if isinstance(source_line, dict) and "constant" in source_line:
            value = source_line["constant"]
            inputs.append(
                {
                    "name": str(value),
                    "literal_value": value,
                    "constant_value_type": source_line.get("value_type")
                    or _constant_value_type(outline_node.label, value),
                    **(
                        {"role": str(source_line["role"])}
                        if source_line.get("role") is not None
                        else {}
                    ),
                    **(
                        {"branch": str(source_line["branch"])}
                        if source_line.get("branch") is not None
                        else {}
                    ),
                }
            )
            continue
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
            metadata = _source_metadata(operation, source_line)
            inputs.extend({"name": candidate, **metadata} for candidate in candidates)
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
            if _is_unprinted_optional_child(
                document,
                outline_node,
                source_line,
                source_lines=source_lines,
                line_index=line_index,
            ):
                if resolution_events is not None:
                    resolution_events.append(
                        {
                            "source_line": source_line,
                            "resolved_to": [],
                            "reason": "ignored unprinted optional child in an explicit form range",
                        }
                    )
                continue
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
        inputs.append({"name": source_id, **_source_metadata(operation, source_line)})

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


def _is_unprinted_optional_child(
    document: SourceDocumentInput,
    outline_node: OutlineNode,
    source_line: Any,
    *,
    source_lines: list[Any],
    line_index: dict[Any, str] | None,
) -> bool:
    """Accept a skipped letter only inside an explicit printed line range.

    IRS forms commonly say "24a through 24z" while printing only the child
    lines that apply to that form revision.  A missing child in that explicit
    range is a blank optional slot, not a reason to lose the total formula.
    Outside that narrow range the normal fail-closed resolution remains in
    force.
    """
    key = _line_reference_key(document, source_line)
    if key is None or line_index is None:
        return False
    anchor = key[1]
    if len(anchor) < 2 or not anchor[-1].isalpha():
        return False
    prefix = anchor[:-1]
    siblings = [
        str(candidate_key[1])
        for candidate_key in line_index
        if isinstance(candidate_key, tuple)
        and len(candidate_key) == 2
        and candidate_key[0] == key[0]
        and str(candidate_key[1]).startswith(prefix)
        and len(str(candidate_key[1])) == len(prefix) + 1
        and str(candidate_key[1])[-1].isalpha()
    ]
    if len(siblings) < 2:
        return False
    referenced = {
        str(item[1]).strip().lower()
        for item in (
            _line_reference_key(document, value)
            for value in source_lines
        )
        if item is not None and item[0] == key[0]
    }
    if not set(siblings).issubset(referenced):
        return False
    label = " ".join(str(outline_node.label).lower().split())
    return f"{prefix}a through {prefix}z" in label


_EXPANDABLE_OPERATIONS = frozenset(spec.name for spec in OPERATION_SPECS if spec.expandable)


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
    data: dict[str, Any] = {
        "citation_id": citation_id,
        "document_id": span.document_id,
        "locator": span.locator,
        "quoted_text": span.text,
    }
    if span.source_ranges:
        data["source_document_id"] = span.document_id
        data["ranges"] = [dict(item) for item in span.source_ranges]
    return DraftObject(
        "citations",
        data,
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
    constant_value: Any | None = None,
    constant_value_type: str | None = None,
) -> DraftObject:
    data: dict[str, Any] = {
        "node_id": node_id,
        "document_id": document.document_id,
        "label": _label(name),
        "node_type": "computed" if computed else node_type_for_outline(outline_node),
        "value_type": "currency" if computed else infer_value_type(outline_node, document=document),
    }
    if constant_value is not None:
        data.update({
            "node_type": "parameter",
            "value_type": constant_value_type or "currency",
            "constant_value": constant_value,
        })
    if citation_refs:
        data["citation_refs"] = citation_refs
    return DraftObject("nodes", data, "", model, 1.0)


def _source_span_text(span_ids: list[str], spans_by_id: dict[str, CandidateSpan]) -> str:
    return "\n".join(spans_by_id[span_id].text for span_id in span_ids if span_id in spans_by_id)


def _default_role(operation: str, input_index: int) -> str:
    roles = operation_roles(operation, input_index)
    if roles and input_index <= len(roles):
        return roles[input_index - 1]
    return roles[-1] if roles else "addend"


def _edge_roles(operation: str, input_item: dict[str, Any], input_index: int) -> tuple[str, ...]:
    """Return edge roles, expanding a filing-status default branch safely."""
    if operation == "LOOKUP_TABLE":
        role = str(input_item.get("branch") or input_item.get("role") or _default_role(operation, input_index))
    else:
        role = str(input_item.get("role") or _default_role(operation, input_index))
    if operation == "LOOKUP_TABLE" and role == "default":
        return _LOOKUP_DEFAULT_ROLES
    return (role,)


def _normalize_operation_inputs(operation: str, inputs: Any) -> list[dict[str, Any]]:
    """Assign positional roles and move legacy branch labels to ``branch``."""
    if not isinstance(inputs, list):
        raise FormulaAssemblyFinding(
            {"code": "invalid_operand_shape", "operation": operation, "reason": "operation inputs must be a list"}
        )
    spec = operation_spec(operation)
    if spec is None:
        raise FormulaAssemblyFinding(
            {"code": "unsupported_operation", "operation": operation, "reason": f"unsupported operation {operation}"}
        )
    normalized: list[dict[str, Any]] = []
    observed: list[str | None] = []
    for item in inputs:
        if not isinstance(item, dict):
            raise FormulaAssemblyFinding(
                {"code": "invalid_operand_shape", "operation": operation, "reason": "operation input must be an object"}
            )
        copied = dict(item)
        role = copied.get("role")
        if operation != "LOOKUP_TABLE" and copied.get("branch") is None and _looks_like_branch(role):
            copied["branch"] = str(role)
            copied.pop("role", None)
            role = None
        observed.append(str(role) if role is not None else None)
        normalized.append(copied)
    if spec.named_leaf_roles:
        return normalized
    assigned = assign_operation_roles(operation, observed)
    if assigned is None:
        raise FormulaAssemblyFinding(
            {
                "code": "invalid_operand_roles",
                "operation": operation,
                "observed": sorted({role for role in observed if role is not None}),
                "expected": list(spec.roles),
                "reason": f"{operation} operand roles do not preserve computation order",
            }
        )
    for item, role in zip(normalized, assigned, strict=True):
        item["role"] = role
    return normalized


def _source_metadata(operation: str, source_line: Any) -> dict[str, str]:
    """Carry role and branch metadata from a structured printed reference."""
    if not isinstance(source_line, dict):
        return {}
    metadata: dict[str, str] = {}
    if source_line.get("role") is not None:
        role = source_line["role"]
        if not (operation != "LOOKUP_TABLE" and source_line.get("branch") is None and _looks_like_branch(role)):
            metadata["role"] = str(role)
    if source_line.get("branch") is not None:
        metadata["branch"] = str(source_line["branch"])
    elif operation != "LOOKUP_TABLE" and _looks_like_branch(source_line.get("role")):
        metadata["branch"] = str(source_line["role"])
    return metadata


def _looks_like_branch(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = "_".join(value.lower().split())
    return normalized in {
        "default",
        "single",
        "married_filing_separately",
        "married_filing_jointly",
        "head_of_household",
        "qualifying_surviving_spouse",
    }


def _validate_operation_inputs(operation: str, inputs: Any) -> None:
    """Fail closed when an expression cannot preserve operand meaning."""
    normalized = _normalize_operation_inputs(operation, inputs)
    spec = operation_spec(operation)
    assert spec is not None
    if spec.named_leaf_roles and len(normalized) < spec.min_args:
        raise FormulaAssemblyFinding(
            {
                "code": "invalid_operand_arity",
                "operation": operation,
                "observed": len(normalized),
                "expected": spec.min_args,
                "reason": f"{operation} requires at least {spec.min_args} operand(s)",
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


def _literal_id(
    document: SourceDocumentInput,
    outline_node: OutlineNode,
    value: str,
    *,
    role: Any = None,
    branch: Any = None,
    input_index: int | None = None,
) -> str:
    """Return a stable node id for a deterministic literal operand."""
    suffix = f"literal_{value}"
    if role is not None:
        suffix += f"_{role}"
    if branch is not None:
        suffix += f"_{branch}"
    if input_index is not None:
        suffix += f"_{input_index}"
    return _node_id(document.document_id, outline_node.outline_id, suffix)


def _constant_value_type(label: str, value: Any) -> str:
    """Infer a printed constant's schema type from the source wording."""
    text = " ".join(str(label).lower().split())
    value_text = str(value).lower()
    if re.search(rf"(?<![\w.]){re.escape(value_text)}\s*%", text):
        return "percentage"
    if re.search(rf"\(\s*{re.escape(value_text)}\s*\)", text):
        return "percentage"
    if float(value) < 1 and "decimal amount" in text:
        return "percentage"
    return "currency"


def _label(name: str) -> str:
    return name.replace("_", " ").strip().title()


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "item"


def _compact(value: str) -> str:
    """Normalize a human form label for deterministic same-form matching."""
    return re.sub(r"[^a-z0-9]+", "", value.lower())
