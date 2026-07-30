"""Generate draft graph objects from rendered source text."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tax_graph.config import get_config_value
from tax_graph.extract.llm_client import LlmClient, response_telemetry
from tax_graph.extract.models import DRAFT_KINDS, ID_FIELDS, DraftObject, ExtractionBatch, SourceDocumentInput
from tax_graph.extract.prompts import assemble_generator_prompt, closed_operations, draft_response_schema


class ExtractionError(ValueError):
    """Raised when an extraction response violates deterministic constraints."""


def generate_drafts(
    document: SourceDocumentInput,
    *,
    client: LlmClient,
    config: dict[str, Any] | None = None,
    root: str | Path | None = None,
) -> ExtractionBatch:
    """Call the generator model and parse schema-pure draft objects."""
    settings = config or {}
    model = get_config_value(settings, "llm.model", "configured-llm")
    response = client.structured_completion(
        prompt=assemble_generator_prompt(document, config=settings, root=root),
        schema=draft_response_schema(root=root),
        model=model,
        max_tokens=int(get_config_value(settings, "llm.max_tokens", 24000)),
        temperature=_optional_float(get_config_value(settings, "llm.temperature", 0)),
        purpose="tax_graph_draft",
    )
    batch = parse_generator_response(response, document=document, model=str(model), root=root)
    complete_expression_roles(batch)
    return batch


def parse_generator_response(
    response: dict[str, Any],
    *,
    document: SourceDocumentInput,
    model: str,
    root: str | Path | None = None,
) -> ExtractionBatch:
    """Parse and validate the generator response into draft objects."""
    allowed_operations = set(closed_operations(root=root))
    provenance = _provenance_map(response.get("provenance", []))
    telemetry = response_telemetry(response)
    resolved_model = telemetry.resolved_model if telemetry and telemetry.resolved_model else model
    objects: list[DraftObject] = []

    for kind in DRAFT_KINDS:
        for item in response.get(kind, []):
            if not isinstance(item, dict):
                raise ExtractionError(f"{kind} item is not an object")
            data = dict(item)
            inline_provenance = data.pop("provenance", None)
            object_id = str(data.get(ID_FIELDS[kind], ""))
            if not object_id:
                raise ExtractionError(f"{kind} item is missing {ID_FIELDS[kind]}")
            if kind == "rules" and data.get("operation") not in allowed_operations:
                raise ExtractionError(f"rule {object_id} uses unsupported operation {data.get('operation')}")

            metadata = provenance.get((kind, object_id), _inline_provenance(inline_provenance))
            objects.append(
                DraftObject(
                    kind=kind,
                    data=data,
                    source_span=str(metadata.get("source_span", "")),
                    extracted_by=str(resolved_model),
                    confidence=float(metadata.get("confidence", 0)),
                    requested_model=str(model),
                    resolved_model=telemetry.resolved_model if telemetry else None,
                )
            )

    return ExtractionBatch(
        document_id=document.document_id,
        year=document.year,
        objects=objects,
        llm_calls=[telemetry] if telemetry else [],
    )


def _provenance_map(items: Any) -> dict[tuple[str, str], dict[str, Any]]:
    mapped: dict[tuple[str, str], dict[str, Any]] = {}
    if not isinstance(items, list):
        return mapped
    for item in items:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind", ""))
        object_id = str(item.get("object_id", ""))
        if kind and object_id:
            mapped[(kind, object_id)] = item
    return mapped


def _inline_provenance(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def complete_expression_roles(batch: ExtractionBatch) -> None:
    """Fill omitted deterministic roles on generated CALCULATES edges.

    The model is allowed to omit optional schema properties, but an expression
    cannot be scored or replayed without the operand position.  This is a
    generator-boundary normalization, not an artifact edit: explicit model
    roles are preserved and only roles that follow from the closed operation
    vocabulary and edge order are filled.  Operations with context-dependent
    lookup roles remain unfilled and are routed by the existing fail-closed
    check.
    """
    operations = {
        obj.object_id: str(obj.data.get("operation", ""))
        for obj in batch.items("rules")
    }
    edges_by_rule: dict[str, list[DraftObject]] = {}
    for edge in batch.items("edges"):
        if edge.data.get("relationship") != "CALCULATES":
            continue
        rule_id = str(edge.data.get("rule_id", ""))
        edges_by_rule.setdefault(rule_id, []).append(edge)

    for rule_id, edges in edges_by_rule.items():
        operation = operations.get(rule_id, "")
        for index, edge in enumerate(edges):
            if str(edge.data.get("role", "")).strip():
                continue
            role = _inferred_operand_role(operation, index)
            if role:
                edge.data["role"] = role


def _inferred_operand_role(operation: str, index: int) -> str | None:
    """Return the safe positional role for one closed operation."""
    roles: dict[str, tuple[str, ...]] = {
        "SUM": ("addend",),
        "SUBTRACT": ("minuend", "subtrahend"),
        "MULTIPLY": ("multiplicand", "multiplier"),
        "DIVIDE": ("numerator", "denominator"),
        "MIN": ("candidate",),
        "MAX": ("candidate",),
        "NEGATE": ("amount",),
        "ABS": ("amount",),
        "ROUND": ("amount",),
        "LOOKUP_BRACKET": ("amount", "brackets"),
        "IF": ("condition", "when_true"),
        "IF_ELSE": ("condition", "threshold", "when_true", "when_false"),
        "AND": ("candidate",),
        "OR": ("candidate",),
        "NOT": ("operand",),
        "COMPARE": ("left", "right"),
        "REQUIRE_INPUT": ("input",),
    }.get(operation, ())
    if not roles:
        return None
    if index < len(roles):
        return roles[index]
    if operation in {"SUBTRACT", "MULTIPLY", "DIVIDE", "AND", "OR"}:
        return roles[-1]
    if operation in {"SUM", "MIN", "MAX"}:
        return roles[0]
    return None


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
