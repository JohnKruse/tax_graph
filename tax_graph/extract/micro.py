"""Narrow model calls used by outline-first extraction."""

from __future__ import annotations

from pathlib import Path
import math
from typing import Any

from tax_graph.config import get_config_value, resolve_llm_model, resolve_llm_seed
from tax_graph.extract.llm_client import LlmClient
from tax_graph.extract.outline import CandidateSpan, OutlineNode
from tax_graph.extract.observability import llm_call_target
from tax_graph.extract.prompts import closed_operations
from tax_graph.operation_registry import assign_operation_roles, operation_spec


class MicroExtractionError(ValueError):
    """Raised when a micro-extraction response violates deterministic constraints."""


def non_formula_micro_schema() -> dict[str, Any]:
    """Return the schema for a non-computed line's source classification."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["source_kind", "form", "line", "box", "quote"],
        "properties": {
            "source_kind": {
                "type": "string",
                "enum": ["form_line", "information_return", "filer_entry"],
            },
            "form": {"type": "string"},
            "line": {"type": "string"},
            "box": {"type": "string"},
            "quote": {"type": "string", "minLength": 1},
        },
    }


def formula_micro_schema(*, root: str | Path | None = None) -> dict[str, Any]:
    """Return the schema for a human-language formula answer."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["operation", "source_lines", "quote"],
        "properties": {
            "operation": {"type": "string", "enum": closed_operations(root=root)},
            "source_lines": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "anyOf": [
                        {"type": "string", "minLength": 1},
                        {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["form", "line", "role", "branch"],
                            "properties": {
                                "form": {"type": "string", "minLength": 1},
                                "line": {"type": "string", "minLength": 1},
                                "role": {"type": ["string", "null"], "minLength": 1},
                                "branch": {"type": ["string", "null"], "minLength": 1},
                            },
                        },
                        {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["constant", "role", "branch", "value_type"],
                            "properties": {
                                "constant": {"type": "number"},
                                "role": {"type": ["string", "null"], "minLength": 1},
                                "branch": {"type": ["string", "null"], "minLength": 1},
                                "value_type": {
                                    "type": ["string", "null"],
                                    "enum": ["currency", "integer", "percentage", None],
                                },
                            },
                        },
                    ],
                },
            },
            "quote": {"type": "string", "minLength": 1},
        },
    }


def _table_formula_schema(*, root: str | Path | None = None) -> dict[str, Any]:
    """Return the legacy column formula schema for the table-only path."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["operation_plan"],
        "properties": {
            "operation_plan": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["output", "operation", "inputs", "citation_span_ids"],
                    "properties": {
                        "output": {"type": "string"},
                        "operation": {"type": "string", "enum": closed_operations(root=root)},
                        "inputs": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["name"],
                                "properties": {
                                    "name": {"type": "string"},
                                    "role": {"type": "string"},
                                },
                            },
                        },
                        "citation_span_ids": {"type": "array", "items": {"type": "string"}},
                    },
                },
            }
        },
    }


def extract_formula_plan(
    *,
    outline_node: OutlineNode,
    spans: list[CandidateSpan],
    client: LlmClient,
    config: dict[str, Any] | None = None,
    root: str | Path | None = None,
    target_cell_id: str | None = None,
    table_mode: bool = False,
) -> dict[str, Any]:
    """Ask one human-shaped formula question and validate its answer."""
    settings = config or {}
    model = _micro_model(settings)
    request: dict[str, Any] = {
        "prompt": _table_formula_prompt(outline_node, spans) if table_mode else _formula_prompt(outline_node, spans),
        "schema": _table_formula_schema(root=root) if table_mode else formula_micro_schema(root=root),
        "model": model,
        "max_tokens": _micro_max_tokens(settings),
        "temperature": _optional_float(get_config_value(settings, "llm.temperature")),
        "purpose": "tax_graph_micro_formula",
    }
    seed = resolve_llm_seed(settings)
    if seed is not None:
        request["seed"] = seed
    with llm_call_target(target_cell_id):
        response = client.structured_completion(**request)
    validate_formula_plan(response, spans=spans, root=root, outline_node=outline_node)
    return response


def validate_formula_plan(
    plan: dict[str, Any],
    *,
    spans: list[CandidateSpan],
    root: str | Path | None = None,
    outline_node: OutlineNode | None = None,
) -> None:
    """Validate a human-language answer with line or printed-constant operands."""
    allowed_operations = set(closed_operations(root=root))
    allowed_spans = {span.span_id for span in spans}
    if "operation_plan" not in plan:
        operation = plan.get("operation")
        if operation not in allowed_operations:
            raise MicroExtractionError(f"unsupported operation: {operation}")
        source_lines = plan.get("source_lines")
        if not isinstance(source_lines, list) or not source_lines:
            raise MicroExtractionError("source_lines must be a non-empty list")
        observed_roles: list[str | None] = []
        for source_line in source_lines:
            if isinstance(source_line, str):
                if not source_line.strip():
                    raise MicroExtractionError("source_lines contains an empty line")
            elif isinstance(source_line, dict):
                if "constant" in source_line:
                    _validate_printed_constant(source_line)
                elif not str(source_line.get("form", "")).strip() or not str(source_line.get("line", "")).strip():
                    raise MicroExtractionError("cross-form source line requires form and line")
                _validate_source_metadata(source_line)
                role, _ = _source_role_and_branch(str(operation), source_line)
                observed_roles.append(role)
            else:
                raise MicroExtractionError(
                    "source_lines item must be a line string, form/line object, or constant object"
                )
            if isinstance(source_line, str):
                observed_roles.append(None)
        _validate_source_line_arity(str(operation), observed_roles)
        quote = plan.get("quote")
        if not isinstance(quote, str) or not quote.strip():
            raise MicroExtractionError("quote must be a non-empty string")
        if not any(_quote_matches(quote, span.text) for span in spans):
            raise MicroExtractionError("quote does not match the supplied form or instruction evidence")
        return

    # Keep the old intermediate shape readable for deterministic fixtures and
    # already-authored Schedule D/table test clients. Live micro calls use the
    # human-language shape above and never ask the model for these names.
    steps = plan.get("operation_plan", [])
    if not isinstance(steps, list) or not steps:
        raise MicroExtractionError("operation_plan must be a non-empty list")
    for step in steps:
        if not isinstance(step, dict):
            raise MicroExtractionError("operation_plan step is not an object")
        operation = step.get("operation")
        if operation not in allowed_operations:
            raise MicroExtractionError(f"unsupported operation: {operation}")
        inputs = step.get("inputs", [])
        _validate_operation_inputs(str(operation), inputs)
        for span_id in step.get("citation_span_ids", []):
            if span_id not in allowed_spans:
                raise MicroExtractionError(f"unknown citation span id: {span_id}")


def extract_non_formula_source(
    *,
    outline_node: OutlineNode,
    spans: list[CandidateSpan],
    client: LlmClient,
    config: dict[str, Any] | None = None,
    target_cell_id: str | None = None,
) -> dict[str, Any]:
    """Ask where a non-computed line gets its value, without requesting ids."""
    settings = config or {}
    model = _micro_model(settings)
    request: dict[str, Any] = {
        "prompt": _non_formula_prompt(outline_node, spans),
        "schema": non_formula_micro_schema(),
        "model": model,
        "max_tokens": _micro_max_tokens(settings),
        "temperature": _optional_float(get_config_value(settings, "llm.temperature")),
        "purpose": "tax_graph_micro_source",
    }
    seed = resolve_llm_seed(settings)
    if seed is not None:
        request["seed"] = seed
    with llm_call_target(target_cell_id):
        response = client.structured_completion(**request)
    validate_non_formula_source(response, spans=spans)
    return response


def validate_non_formula_source(plan: dict[str, Any], *, spans: list[CandidateSpan]) -> None:
    """Validate the closed source classification and verbatim evidence."""
    if plan.get("source_kind") not in {"form_line", "information_return", "filer_entry"}:
        raise MicroExtractionError(f"unsupported source_kind: {plan.get('source_kind')}")
    for key in ("form", "line", "box"):
        if not isinstance(plan.get(key), str):
            raise MicroExtractionError(f"{key} must be a string")
    quote = plan.get("quote")
    if not isinstance(quote, str) or not quote.strip():
        raise MicroExtractionError("quote must be a non-empty string")
    if not any(_quote_matches(quote, span.text) for span in spans):
        raise MicroExtractionError("quote does not match the supplied form or instruction evidence")


def _formula_prompt(
    outline_node: OutlineNode,
    spans: list[CandidateSpan],
) -> str:
    form_spans = [span for span in spans if span.relationship == "source"]
    instruction_spans = [span for span in spans if span.relationship != "source"]
    rendered_form = "\n".join(span.text for span in form_spans[:40]) or "(not available)"
    rendered_instructions = "\n".join(span.text for span in instruction_spans[:6]) or "(not available)"
    return "\n".join(
        [
            "Answer the human question for one form line.",
            "Which printed lines does this line use, and what operation combines them?",
            "Return operation, source_lines, and quote.",
            "Use the form's printed line numbers in source_lines, never internal ids.",
            "For a printed numeric constant, include {\"constant\": number} in source_lines, not a fake line number.",
            "Set value_type to currency for dollar amounts and percentage for rates or decimal factors.",
            "role means operand position, such as condition, threshold, when_true, when_false, amount, or brackets.",
            "branch is separate from role and means branch selection; use default for an unqualified branch and full filing-status names otherwise.",
            "For repeated filing-status values or table rows, repeat the operand role and set branch for each row.",
            "For SUBTRACT and DIVIDE, source_lines are in computation order: the value being reduced comes first.",
            "",
            f"target line label: {outline_node.label}",
            "",
            "form face line:",
            rendered_form,
            "",
            "instruction text:",
            rendered_instructions,
        ]
    )


def _non_formula_prompt(outline_node: OutlineNode, spans: list[CandidateSpan]) -> str:
    """Ask the human question for a line that is not a formula."""
    form_spans = [span for span in spans if span.relationship == "source"]
    instruction_spans = [span for span in spans if span.relationship != "source"]
    rendered_form = "\n".join(span.text for span in form_spans[:40]) or "(not available)"
    rendered_instructions = "\n".join(span.text for span in instruction_spans[:8]) or "(not available)"
    return "\n".join(
        [
            "Answer the human question for one non-computed form line.",
            "Where does this value come from: another form line, an information return box, or the filer?",
            "Return source_kind, form, line, box, and quote.",
            "Use printed references only. Never return internal node ids or field names.",
            "Use source_kind form_line for another form or line, information_return for W-2/1099 boxes, and filer_entry when the filer supplies the value.",
            "If the source is not clear, return filer_entry only when the instructions say the filer enters it; otherwise return the closest explicit source and let deterministic resolution fail closed.",
            "",
            f"target line label: {outline_node.label}",
            "",
            "form face line:",
            rendered_form,
            "",
            "instruction text:",
            rendered_instructions,
        ]
    )


def _table_formula_prompt(outline_node: OutlineNode, spans: list[CandidateSpan]) -> str:
    """Ask the retained table-specific path about column formulas."""
    rendered_spans = "\n".join(
        f"- {span.span_id}: {span.document_id} {span.locator}: {span.text}"
        for span in spans
    )
    return "\n".join(
        [
            "Extract the column formula for this table row or total.",
            "Return an operation_plan using the closed operation vocabulary.",
            "Use only candidate span ids for citation_span_ids.",
            "Use stable names: column_d, column_e, column_g, column_h, and line_2_column_<letter>_total.",
            "For column h, represent d - e + g as SUBTRACT then SUM.",
            "For totals lines, create one SUM step per column.",
            "",
            f"outline_id: {outline_node.outline_id}",
            f"kind: {outline_node.kind}",
            f"label: {outline_node.label}",
            f"columns: {outline_node.columns}",
            "",
            "candidate_spans:",
            rendered_spans,
        ]
    )


def _quote_matches(quote: str, source: str) -> bool:
    """Compare evidence after folding line-break whitespace only."""
    normalize = lambda value: " ".join(str(value).split())
    return normalize(quote) in normalize(source) or normalize(source) in normalize(quote)


def _validate_printed_constant(source_line: dict[str, Any]) -> None:
    """Validate one explicit numeric constant operand from the printed form."""
    value = source_line.get("constant")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise MicroExtractionError("printed constant must be a finite number")
    _validate_source_metadata(source_line)
    value_type = source_line.get("value_type")
    if value_type is not None and value_type not in {"currency", "integer", "percentage"}:
        raise MicroExtractionError("printed constant value_type is unsupported")


def _validate_source_metadata(source_line: dict[str, Any]) -> None:
    """Validate the two independent operand metadata axes."""
    for key in ("role", "branch"):
        value = source_line.get(key)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise MicroExtractionError(f"printed source {key} must be a non-empty string")


def _source_role_and_branch(operation: str, source_line: dict[str, Any]) -> tuple[str | None, str | None]:
    """Read new metadata while tolerating the prior lookup-role spelling."""
    role = source_line.get("role")
    branch = source_line.get("branch")
    if operation != "LOOKUP_TABLE" and branch is None and _looks_like_branch(role):
        return None, str(role)
    return (str(role) if role is not None else None, str(branch) if branch is not None else None)


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


def _validate_source_line_arity(operation: str, observed_roles: list[str | None]) -> None:
    spec = operation_spec(operation)
    if spec is None:
        raise MicroExtractionError(f"unsupported operation: {operation}")
    if spec.named_leaf_roles:
        if len(observed_roles) < spec.min_args:
            wording = "exactly" if spec.max_args == spec.min_args else "at least"
            raise MicroExtractionError(f"{operation} requires {wording} {spec.min_args} source line(s)")
        return
    assigned = assign_operation_roles(operation, observed_roles)
    if assigned is None:
        count = len(observed_roles)
        if count < spec.min_args and not spec.role_variants:
            wording = "exactly" if spec.max_args == spec.min_args else "at least"
            raise MicroExtractionError(f"{operation} requires {wording} {spec.min_args} source line(s)")
        raise MicroExtractionError(f"{operation} operand roles do not preserve computation order")


def _validate_operation_inputs(operation: str, inputs: Any) -> None:
    if not isinstance(inputs, list):
        raise MicroExtractionError("operation inputs must be a list")
    spec = operation_spec(operation)
    if spec is None:
        raise MicroExtractionError(f"unsupported operation: {operation}")
    if spec.named_leaf_roles:
        if len(inputs) < spec.min_args:
            wording = "exactly" if spec.max_args == spec.min_args else "at least"
            raise MicroExtractionError(f"{operation} requires {wording} {spec.min_args} operand(s)")
        return
    observed: list[str | None] = []
    for index, item in enumerate(inputs, 1):
        if not isinstance(item, dict):
            raise MicroExtractionError("operation input must be an object")
        role = item.get("role")
        observed.append(str(role) if role is not None else None)
    if assign_operation_roles(operation, observed) is None:
        raise MicroExtractionError(
            f"{operation} operand roles do not preserve computation order"
        )


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _micro_model(settings: dict[str, Any]) -> str:
    return resolve_llm_model(settings, "micro")


def _micro_max_tokens(settings: dict[str, Any]) -> int:
    """Return the bounded per-cell response cap.

    The extraction setting is authoritative. The micro model is an explicit
    configuration contract, and the default is the M20 canary cap rather than
    the whole-document response budget.
    """
    value = get_config_value(settings, "extraction.micro_max_tokens")
    if value is None:
        value = get_config_value(settings, "llm.micro_max_tokens", 4000)
    return int(value)
