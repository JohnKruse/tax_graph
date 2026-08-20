"""Narrow model calls used by outline-first extraction."""

from __future__ import annotations

from pathlib import Path
import difflib
import math
import re
from typing import Any

from tax_graph.config import get_config_value, resolve_llm_model, resolve_llm_seed
from tax_graph.extract.llm_client import LlmClient
from tax_graph.extract.outline import CandidateSpan, OutlineNode
from tax_graph.extract.observability import llm_call_target
from tax_graph.extract.prompts import closed_operations
from tax_graph.operation_registry import operation_roles, operation_spec


class MicroExtractionError(ValueError):
    """Raised when a micro-extraction response violates deterministic constraints."""

    def __init__(
        self,
        message: str,
        *,
        rejected_payload: dict[str, Any] | None = None,
        validation_diagnostic: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.rejected_payload = rejected_payload
        self.validation_diagnostic = validation_diagnostic

    def attach_rejected_payload(self, payload: Any) -> None:
        """Keep the provider payload when deterministic validation rejects it."""
        if isinstance(payload, dict):
            self.rejected_payload = dict(payload)
        else:
            self.rejected_payload = {"raw": repr(payload)}


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
    """Return the one-call discriminated union for an addressable form line."""
    operations = closed_operations(root=root)
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "kind",
            "operation",
            "source_lines",
            "question",
            "options",
            "form",
            "line",
            "box",
            "reason",
            "quote",
        ],
        "properties": {
            "kind": {
                "type": "string",
                "enum": [
                    "computation",
                    "filer_entry",
                    "election",
                    "information_return",
                    "not_derivable",
                ],
            },
            "operation": {
                "type": ["string", "null"],
                "enum": [*operations, None],
                "description": "Required only for kind computation; null otherwise.",
            },
            "source_lines": {
                "type": ["array", "null"],
                "minItems": 1,
                "items": {
                    "anyOf": [
                        {"type": "string", "minLength": 1},
                        {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["form", "line", "role"],
                            "properties": {
                                "form": {"type": "string", "minLength": 1},
                                "line": {"type": "string", "minLength": 1},
                                "role": {"type": ["string", "null"], "minLength": 1},
                            },
                        },
                        {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["constant", "role", "value_type"],
                            "properties": {
                                "constant": {"type": "number"},
                                "role": {"type": ["string", "null"], "minLength": 1},
                                "value_type": {
                                    "type": ["string", "null"],
                                    "enum": ["currency", "integer", "percentage"],
                                },
                            },
                        },
                    ],
                },
                "description": "Printed source references required only for kind computation.",
            },
            "question": {
                "type": ["string", "null"],
                "description": "Question presented to the filer for kind election.",
            },
            "options": {
                "type": ["array", "null"],
                "minItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["label", "downstream_effect", "citation_refs", "option_type"],
                    "properties": {
                        "label": {"type": "string", "minLength": 1},
                        "downstream_effect": {"type": "string", "minLength": 1},
                        "citation_refs": {
                            "type": "array",
                            "minItems": 1,
                            "items": {"type": "string", "minLength": 1},
                        },
                        "option_type": {"type": "string", "enum": ["choice", "escalate"]},
                    },
                },
                "description": "Options required only for kind election; one must be escalate.",
            },
            "form": {
                "type": ["string", "null"],
                "description": "Printed source form named by a filer-supplied input.",
            },
            "line": {
                "type": ["string", "null"],
                "description": "Printed source line, when the named input has one.",
            },
            "box": {
                "type": ["string", "null"],
                "description": "Printed source box for kind information_return.",
            },
            "reason": {
                "type": ["string", "null"],
                "description": (
                    "Why the line cannot be derived from the supplied evidence; "
                    "required only for kind not_derivable."
                ),
            },
            "quote": {"type": "string", "minLength": 1},
        },
    }


FORMULA_RESPONSE_KINDS = frozenset(
    {
        "computation",
        "filer_entry",
        "election",
        "information_return",
        "not_derivable",
    }
)


def formula_response_kind(plan: dict[str, Any]) -> str:
    """Return the normalized kind for a new or legacy fixture response."""
    if "kind" in plan:
        return str(plan.get("kind") or "")
    if plan.get("source_kind") in {"form_line", "filer_entry", "information_return"}:
        return str(plan["source_kind"])
    if "operation_plan" in plan or plan.get("operation") is not None:
        return "computation"
    return ""


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
    try:
        validate_formula_plan(response, spans=spans, root=root, outline_node=outline_node)
    except MicroExtractionError as exc:
        exc.attach_rejected_payload(response)
        raise
    return response


def validate_formula_plan(
    plan: dict[str, Any],
    *,
    spans: list[CandidateSpan],
    root: str | Path | None = None,
    outline_node: OutlineNode | None = None,
) -> None:
    """Validate the formula union and retain legacy fixture compatibility."""
    allowed_operations = set(closed_operations(root=root))
    allowed_spans = {span.span_id for span in spans}
    kind = formula_response_kind(plan)
    if "kind" in plan:
        if kind not in FORMULA_RESPONSE_KINDS:
            raise MicroExtractionError(f"unsupported formula response kind: {kind}")
        _validate_quote(plan, spans)
        if kind == "computation":
            if plan.get("operation") not in allowed_operations:
                raise MicroExtractionError(f"unsupported operation: {plan.get('operation')}")
            source_lines = plan.get("source_lines")
            if not isinstance(source_lines, list) or not source_lines:
                raise MicroExtractionError("computation source_lines must be a non-empty list")
            for source_line in source_lines:
                _validate_source_line(source_line)
            _validate_source_line_arity(str(plan["operation"]), len(source_lines))
            if any(plan.get(name) is not None for name in ("question", "options", "form", "line", "box", "reason")):
                raise MicroExtractionError("computation response contains non-computation fields")
            return
        if kind == "filer_entry":
            _require_null_fields(plan, ("operation", "source_lines", "question", "options", "reason"))
            _validate_filer_entry_source(plan)
            return
        if kind == "information_return":
            _require_non_empty_string(plan, "form")
            _require_non_empty_string(plan, "box")
            _require_null_fields(plan, ("operation", "source_lines", "question", "options", "line", "reason"))
            if not _is_information_return_box(str(plan["box"])):
                raise MicroExtractionError("information_return box must be a printed box number")
            return
        if kind == "election":
            _require_non_empty_string(plan, "question")
            _validate_election_options(plan.get("options"), allowed_spans)
            _require_null_fields(plan, ("operation", "source_lines", "form", "line", "box", "reason"))
            return
        _require_non_empty_string(plan, "reason")
        _require_null_fields(plan, ("operation", "source_lines", "question", "options", "form", "line", "box"))
        return

    # The source classifier was a separate pre-S111 call. Accept its shape in
    # deterministic fixtures so the old source-resolution guards remain useful;
    # live formula calls use the union above.
    if "source_kind" in plan:
        validate_non_formula_source(plan, spans=spans)
        return

    if "operation_plan" not in plan:
        operation = plan.get("operation")
        source_lines = plan.get("source_lines")
        if operation is None or source_lines is None:
            raise MicroExtractionError(
                "operation and source_lines must both be populated for a computation"
            )
        if operation not in allowed_operations:
            raise MicroExtractionError(f"unsupported operation: {operation}")
        if not isinstance(source_lines, list) or not source_lines:
            raise MicroExtractionError("source_lines must be a non-empty list")
        for source_line in source_lines:
            _validate_source_line(source_line)
        _validate_source_line_arity(str(operation), len(source_lines))
        _validate_quote(plan, spans)
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


def _validate_quote(plan: dict[str, Any], spans: list[CandidateSpan]) -> None:
    """Require a response quote to be verbatim from the supplied evidence."""
    quote = plan.get("quote")
    if not isinstance(quote, str) or not quote.strip():
        raise MicroExtractionError("quote must be a non-empty string")
    if not any(_quote_matches(quote, span.text) for span in spans):
        raise MicroExtractionError(
            "quote does not match the supplied form or instruction evidence",
            validation_diagnostic=_closest_quote_diagnostic(quote, spans),
        )


def _closest_quote_diagnostic(
    quote: str,
    spans: list[CandidateSpan],
) -> dict[str, Any] | None:
    """Return inspectable nearest-span evidence without changing quote validity."""
    if not spans:
        return None
    normalize = lambda value: " ".join(str(value).split())
    normalized_quote = normalize(quote)
    candidates: list[tuple[float, int, CandidateSpan, difflib.Match]] = []
    for span in spans:
        normalized_source = normalize(span.text)
        match = difflib.SequenceMatcher(
            None,
            normalized_quote,
            normalized_source,
            autojunk=False,
        ).find_longest_match(0, len(normalized_quote), 0, len(normalized_source))
        ratio = difflib.SequenceMatcher(
            None,
            normalized_quote,
            normalized_source,
            autojunk=False,
        ).ratio()
        candidates.append((ratio, match.size, span, match))
    ratio, _size, span, match = max(candidates, key=lambda item: (item[0], item[1]))
    normalized_source = normalize(span.text)
    return {
        "span_id": span.span_id,
        "span_text": span.text,
        "normalized_quote": normalized_quote,
        "normalized_span_text": normalized_source,
        "similarity": round(ratio, 6),
        "longest_common_substring": {
            "quote_offset": match.a,
            "span_offset": match.b,
            "length": match.size,
            "text": normalized_quote[match.a:match.a + match.size],
        },
    }


def _validate_source_line(source_line: Any) -> None:
    """Validate one printed line, cross-form line, or printed constant."""
    if isinstance(source_line, str):
        if not source_line.strip():
            raise MicroExtractionError("source_lines contains an empty line")
        return
    if isinstance(source_line, dict):
        if "constant" in source_line:
            _validate_printed_constant(source_line)
            return
        if not str(source_line.get("form", "")).strip() or not str(source_line.get("line", "")).strip():
            raise MicroExtractionError("cross-form source line requires form and line")
        return
    raise MicroExtractionError(
        "source_lines item must be a line string, form/line object, or constant object"
    )


def _require_null_fields(plan: dict[str, Any], names: tuple[str, ...]) -> None:
    """Require union fields outside the selected branch to be explicit nulls."""
    for name in names:
        if plan.get(name) is not None:
            raise MicroExtractionError(f"{name} must be null for kind {plan.get('kind')}")


def _require_non_empty_string(plan: dict[str, Any], name: str) -> None:
    """Require a non-empty string in a selected union branch."""
    value = plan.get(name)
    if not isinstance(value, str) or not value.strip():
        raise MicroExtractionError(f"{name} must be a non-empty string for kind {plan.get('kind')}")


def _validate_filer_entry_source(plan: dict[str, Any]) -> None:
    """Validate optional printed source identity on a filer-supplied outcome."""
    values = {name: plan.get(name) for name in ("form", "line", "box")}
    for name, value in values.items():
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise MicroExtractionError(f"{name} must be null or a non-empty string for kind filer_entry")
    if any(value is not None for value in values.values()) and values["form"] is None:
        raise MicroExtractionError("filer_entry source identity requires form")
    if values["box"] is not None and not _is_information_return_box(str(values["box"])):
        raise MicroExtractionError("filer_entry box must be a printed box number")


def _is_information_return_box(value: str) -> bool:
    """Return whether a source box is a printed numeric or alphanumeric box."""
    return bool(re.fullmatch(r"[0-9]+[a-z]?", value.strip(), re.IGNORECASE))


def _validate_election_options(options: Any, allowed_spans: set[str]) -> None:
    """Validate model-generated election choices and their evidence references."""
    if not isinstance(options, list) or not options:
        raise MicroExtractionError("election options must be a non-empty list")
    has_escalate = False
    for option in options:
        if not isinstance(option, dict):
            raise MicroExtractionError("election option must be an object")
        for name in ("label", "downstream_effect"):
            value = option.get(name)
            if not isinstance(value, str) or not value.strip():
                raise MicroExtractionError(f"election option {name} must be non-empty")
        if option.get("option_type") not in {"choice", "escalate"}:
            raise MicroExtractionError("election option_type must be choice or escalate")
        refs = option.get("citation_refs")
        if not isinstance(refs, list) or not refs or not all(
            isinstance(ref, str) and ref in allowed_spans for ref in refs
        ):
            raise MicroExtractionError("election option citation_refs must name supplied evidence spans")
        has_escalate = has_escalate or option["option_type"] == "escalate"
    if not has_escalate:
        raise MicroExtractionError("election options must include an escalate option")


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
    try:
        validate_non_formula_source(response, spans=spans)
    except MicroExtractionError as exc:
        exc.attach_rejected_payload(response)
        raise
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
        raise MicroExtractionError(
            "quote does not match the supplied form or instruction evidence",
            validation_diagnostic=_closest_quote_diagnostic(quote, spans),
        )


def _formula_prompt(
    outline_node: OutlineNode,
    spans: list[CandidateSpan],
) -> str:
    form_spans = [span for span in spans if span.relationship == "source"]
    instruction_spans = [span for span in spans if span.relationship != "source"]
    rendered_form = "\n".join(
        f"- {span.span_id}: {span.text}" for span in form_spans[:40]
    ) or "(not available)"
    rendered_instructions = "\n".join(
        f"- {span.span_id}: {span.text}" for span in instruction_spans[:6]
    ) or "(not available)"
    return "\n".join(
        [
            "Answer one addressable form line from the evidence packet below.",
            "Answer only from the supplied evidence. Do not use outside knowledge or infer a rule the packet does not state.",
            "If the evidence does not say enough to classify or derive the line, return kind not_derivable and explain why.",
            "Return exactly one kind: computation, filer_entry, election, information_return, or not_derivable.",
            "Set every field that does not belong to the selected kind to null. For filer_entry, "
            "form, line, and box are source identity fields: populate the ones explicitly named "
            "by the evidence instead of dropping them.",
            "For computation, return the closed operation, printed source_lines, and the verbatim quote.",
            "Use the form's printed line numbers in source_lines, never internal ids.",
            "For a printed numeric constant, include {\"constant\": number} in source_lines, not a fake line number.",
            "Set value_type to currency for dollar amounts and percentage for rates or decimal factors.",
            "For lookup branches, include the branch role on the constant object; use default for an unqualified branch and full filing-status names otherwise.",
            "For SUBTRACT and DIVIDE, source_lines are in computation order: the value being reduced comes first.",
            "For filer_entry, use the kind only when the evidence says the filer enters or supplies the value; do not invent a calculation. If the evidence names a source form, line, or box, copy those printed values into form, line, and box. A W-2 box is a filer-supplied input and remains filer_entry.",
            "For information_return, return the printed form and box that the evidence names.",
            "For election, return the question and substantive options grounded in the evidence. Every option must include citation_refs using the supplied span ids, and one option_type must be escalate.",
            "For not_derivable, give a concise evidence-grounded reason.",
            "Wording such as add line, subtract line, amount from line, amount of line, smallest of line, or enter an amount can be examples of computation, but these phrases are not routing rules; read the supplied face and instructions.",
            "",
            f"target line label: {outline_node.label}",
            "",
            "form face evidence:",
            rendered_form,
            "",
            "instruction evidence:",
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
    role = source_line.get("role")
    if role is not None and (not isinstance(role, str) or not role.strip()):
        raise MicroExtractionError("printed constant role must be a non-empty string")
    value_type = source_line.get("value_type")
    if value_type is not None and value_type not in {"currency", "integer", "percentage"}:
        raise MicroExtractionError("printed constant value_type is unsupported")


def _validate_source_line_arity(operation: str, count: int) -> None:
    spec = operation_spec(operation)
    if spec is None:
        raise MicroExtractionError(f"unsupported operation: {operation}")
    if not spec.accepts_count(count):
        wording = "exactly" if spec.max_args == spec.min_args else "at least"
        raise MicroExtractionError(f"{operation} requires {wording} {spec.min_args} source line(s)")


def _validate_operation_inputs(operation: str, inputs: Any) -> None:
    if not isinstance(inputs, list):
        raise MicroExtractionError("operation inputs must be a list")
    spec = operation_spec(operation)
    if spec is None:
        raise MicroExtractionError(f"unsupported operation: {operation}")
    if not spec.accepts_count(len(inputs)):
        wording = "exactly" if spec.max_args == spec.min_args else "at least"
        raise MicroExtractionError(f"{operation} requires {wording} {spec.min_args} operand(s)")
    if spec.named_leaf_roles or len(spec.roles) <= 1:
        return
    roles = operation_roles(operation, len(inputs))
    observed = []
    for index, item in enumerate(inputs, 1):
        if not isinstance(item, dict):
            raise MicroExtractionError("operation input must be an object")
        observed.append(str(item.get("role") or roles[index - 1]))
    if observed != list(roles):
        raise MicroExtractionError(
            f"{operation} operand roles must be {', '.join(roles)} in computation order"
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
