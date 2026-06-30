"""Narrow model calls used by outline-first extraction."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tax_graph.config import get_config_value
from tax_graph.extract.llm_client import LlmClient
from tax_graph.extract.outline import CandidateSpan, OutlineNode
from tax_graph.extract.prompts import closed_operations


class MicroExtractionError(ValueError):
    """Raised when a micro-extraction response violates deterministic constraints."""


def formula_micro_schema(*, root: str | Path | None = None) -> dict[str, Any]:
    """Return the tiny schema for formula operation plans."""
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
                        "citation_span_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
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
) -> dict[str, Any]:
    """Ask a narrow formula question and validate the returned operation plan."""
    settings = config or {}
    model = _micro_model(settings)
    response = client.structured_completion(
        prompt=_formula_prompt(outline_node, spans),
        schema=formula_micro_schema(root=root),
        model=model,
        max_tokens=int(get_config_value(settings, "llm.micro_max_tokens", 8000)),
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
    """Validate operation vocabulary and candidate span references."""
    allowed_operations = set(closed_operations(root=root))
    allowed_spans = {span.span_id for span in spans}
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


def _formula_prompt(outline_node: OutlineNode, spans: list[CandidateSpan]) -> str:
    rendered_spans = "\n".join(
        f"- {span.span_id}: {span.document_id} {span.locator}: {span.text}"
        for span in spans
    )
    return "\n".join(
        [
            "Extract only the formula for this outline node.",
            "Return an operation_plan using the closed operation vocabulary.",
            "Use only candidate span ids for citation_span_ids.",
            "Use stable names: column_d, column_e, column_g, column_h, and line_2_column_<letter>_total.",
            "For Form 8949 column h, represent d - e + g as SUBTRACT then SUM.",
            "For totals lines, create one SUM step per column instead of summing different columns together.",
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
