"""Narrow model calls used by outline-first extraction."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tax_graph.config import get_config_value
from tax_graph.extract.llm_client import LlmClient
from tax_graph.extract.outline import CandidateSpan, OutlineNode
from tax_graph.extract.observability import llm_call_target
from tax_graph.extract.prompts import closed_operations


class MicroExtractionError(ValueError):
    """Raised when a micro-extraction response violates deterministic constraints."""


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
                            "required": ["form", "line"],
                            "properties": {
                                "form": {"type": "string", "minLength": 1},
                                "line": {"type": "string", "minLength": 1},
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
    with llm_call_target(target_cell_id):
        response = client.structured_completion(
            prompt=_table_formula_prompt(outline_node, spans) if table_mode else _formula_prompt(outline_node, spans),
            schema=_table_formula_schema(root=root) if table_mode else formula_micro_schema(root=root),
            model=model,
            max_tokens=_micro_max_tokens(settings),
            temperature=_optional_float(get_config_value(settings, "llm.temperature", 0)),
            purpose="tax_graph_micro_formula",
        )
    validate_formula_plan(response, spans=spans, root=root)
    return response


def validate_formula_plan(
    plan: dict[str, Any],
    *,
    spans: list[CandidateSpan],
    root: str | Path | None = None,
) -> None:
    """Validate a human-language answer or a legacy test-plan response."""
    allowed_operations = set(closed_operations(root=root))
    allowed_spans = {span.span_id for span in spans}
    if "operation_plan" not in plan:
        operation = plan.get("operation")
        if operation not in allowed_operations:
            raise MicroExtractionError(f"unsupported operation: {operation}")
        source_lines = plan.get("source_lines")
        if not isinstance(source_lines, list) or not source_lines:
            raise MicroExtractionError("source_lines must be a non-empty list")
        for source_line in source_lines:
            if isinstance(source_line, str):
                if not source_line.strip():
                    raise MicroExtractionError("source_lines contains an empty line")
            elif isinstance(source_line, dict):
                if not str(source_line.get("form", "")).strip() or not str(source_line.get("line", "")).strip():
                    raise MicroExtractionError("cross-form source line requires form and line")
            else:
                raise MicroExtractionError("source_lines item must be a line string or form/line object")
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
        for span_id in step.get("citation_span_ids", []):
            if span_id not in allowed_spans:
                raise MicroExtractionError(f"unknown citation span id: {span_id}")


def _formula_prompt(
    outline_node: OutlineNode,
    spans: list[CandidateSpan],
) -> str:
    form_spans = [span for span in spans if span.relationship == "source"]
    instruction_spans = [span for span in spans if span.relationship != "source"]
    rendered_form = "\n".join(span.text for span in form_spans[:1]) or "(not available)"
    rendered_instructions = "\n".join(span.text for span in instruction_spans[:6]) or "(not available)"
    return "\n".join(
        [
            "Answer the human question for one form line.",
            "Which printed lines does this line use, and what operation combines them?",
            "Return operation, source_lines, and quote.",
            "Use the form's printed line numbers in source_lines, never internal ids.",
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


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _micro_model(settings: dict[str, Any]) -> str:
    model = get_config_value(settings, "llm.micro_model")
    if model:
        return str(model)
    fallback = get_config_value(settings, "llm.model", "configured-llm")
    return str(fallback or "configured-llm")


def _micro_max_tokens(settings: dict[str, Any]) -> int:
    """Return the bounded per-cell response cap.

    The extraction setting is authoritative. The old llm setting remains a
    compatibility fallback for tests and copied configs, but the default is the
    M20 canary cap rather than the whole-document response budget.
    """
    value = get_config_value(settings, "extraction.micro_max_tokens")
    if value is None:
        value = get_config_value(settings, "llm.micro_max_tokens", 4000)
    return int(value)
