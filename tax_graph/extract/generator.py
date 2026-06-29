"""Generate draft graph objects from rendered source text."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tax_graph.config import get_config_value
from tax_graph.extract.llm_client import LlmClient
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
        max_tokens=int(get_config_value(settings, "llm.max_tokens", 8000)),
        temperature=_optional_float(get_config_value(settings, "llm.temperature", 0)),
        purpose="tax_graph_draft",
    )
    return parse_generator_response(response, document=document, model=model, root=root)


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
                    extracted_by=model,
                    confidence=float(metadata.get("confidence", 0)),
                )
            )

    return ExtractionBatch(document_id=document.document_id, year=document.year, objects=objects)


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


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
