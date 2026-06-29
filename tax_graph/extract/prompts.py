"""Prompt assembly for schema-constrained extraction."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from tax_graph.config import get_config_value, project_root
from tax_graph.extract.models import DRAFT_KINDS, ExtractionBatch, RelatedSourceInput, SourceDocumentInput
from tax_graph.io.loader import load_yaml


def load_prompt_template(path: str | Path, *, root: str | Path | None = None) -> str:
    """Load a prompt template relative to the project root."""
    root_path = Path(root).resolve() if root is not None else project_root()
    prompt_path = Path(path)
    if not prompt_path.is_absolute():
        prompt_path = root_path / prompt_path
    return prompt_path.read_text(encoding="utf-8")


def closed_operations(*, root: str | Path | None = None) -> list[str]:
    """Return the closed rule operation vocabulary from the rule schema."""
    root_path = Path(root).resolve() if root is not None else project_root()
    schema = load_yaml(root_path / "schemas" / "rule.schema.json")
    return list(schema["properties"]["operation"]["enum"])


def graph_object_schemas(*, root: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """Load JSON schemas for draft graph objects."""
    root_path = Path(root).resolve() if root is not None else project_root()
    return {
        kind: load_yaml(root_path / "schemas" / f"{kind[:-1]}.schema.json")
        for kind in DRAFT_KINDS
    }


def draft_response_schema(*, root: str | Path | None = None) -> dict[str, Any]:
    """Build the structured-output schema accepted from generator/critic clients."""
    schemas = graph_object_schemas(root=root)
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            **{
                kind: {
                    "type": "array",
                    "items": schemas[kind],
                    "default": [],
                }
                for kind in DRAFT_KINDS
            },
            "provenance": {
                "type": "array",
                "default": [],
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["kind", "object_id", "source_span", "confidence"],
                    "properties": {
                        "kind": {"type": "string", "enum": list(DRAFT_KINDS)},
                        "object_id": {"type": "string"},
                        "source_span": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
            },
        },
        "required": [*DRAFT_KINDS, "provenance"],
    }


def schema_prompt_summary(*, root: str | Path | None = None) -> str:
    """Return a compact human-readable schema summary for prompts."""
    schemas = graph_object_schemas(root=root)
    lines: list[str] = []
    for kind, schema in schemas.items():
        required = ", ".join(schema.get("required", []))
        properties = ", ".join(schema.get("properties", {}).keys())
        schema_name = f"{kind[:-1]}.schema.json"
        lines.append(f"- {schema_name}: required [{required}]; properties [{properties}]")
    return "\n".join(lines)


def field_prompt_summary(fields: dict[str, Any] | None) -> str:
    """Return a compact field-grid summary for prompts."""
    if not fields:
        return "{}"
    by_anchor: dict[str, dict[str, set[str]]] = {}
    unanchored = 0
    for field in fields.get("fields", []):
        anchor = str(field.get("line_anchor", ""))
        if not anchor:
            unanchored += 1
            continue
        entry = by_anchor.setdefault(anchor, {"pages": set(), "x": set(), "y": set()})
        entry["pages"].add(str(field.get("page", "")))
        entry["x"].add(str(field.get("x_cluster", "")))
        entry["y"].add(str(field.get("y_cluster", "")))
    lines = []
    for anchor, entry in sorted(by_anchor.items()):
        lines.append(
            "line {anchor}: pages={pages} x_clusters={x} y_clusters={y}".format(
                anchor=anchor,
                pages=",".join(sorted(entry["pages"])),
                x=",".join(sorted(entry["x"])),
                y=",".join(sorted(entry["y"])),
            )
        )
    if unanchored:
        lines.append(f"unanchored_fields={unanchored}")
    return "\n".join(lines)


def related_source_prompt(document: SourceDocumentInput) -> str:
    """Render bundled source context for prompts."""
    if not document.related_sources:
        return "none"
    rendered = []
    for source in document.related_sources:
        text = _related_source_snippet(source)
        rendered.append(
            "\n".join(
                [
                    f"## {source.relationship}: {source.document_id}",
                    f"kind: {source.kind}",
                    "text:",
                    text,
                    "links:",
                    json.dumps(source.links, indent=2, sort_keys=True),
                ]
            )
        )
    return "\n\n".join(rendered)


def _related_source_snippet(source: RelatedSourceInput, *, max_chars: int = 7000) -> str:
    """Keep extraction prompts focused on instruction lines likely to carry authority."""
    if len(source.text) <= max_chars:
        return source.text

    patterns = [
        r"column\s+\([a-h]\)",
        r"gain\s+or\s+loss",
        r"subtract",
        r"schedule\s+d",
        r"line\s+1b",
        r"line\s+8b",
        r"line\s+2",
        r"line\s+10",
        r"form\s+8949",
    ]
    lines = source.text.splitlines()
    selected: list[str] = []
    seen: set[int] = set()
    for index, line in enumerate(lines):
        if not any(re.search(pattern, line, flags=re.IGNORECASE) for pattern in patterns):
            continue
        for nearby in range(max(0, index - 1), min(len(lines), index + 2)):
            if nearby not in seen:
                selected.append(lines[nearby])
                seen.add(nearby)

    snippet = "\n".join(selected).strip()
    if not snippet:
        snippet = source.text[:max_chars].strip()
    if len(snippet) > max_chars:
        snippet = snippet[:max_chars].rsplit("\n", 1)[0].strip()
    return snippet


def critic_response_schema() -> dict[str, Any]:
    """Build the structured-output schema accepted from the critic client."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["findings"],
        "properties": {
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["kind", "object_id", "agrees", "reason"],
                    "properties": {
                        "kind": {"type": "string", "enum": list(DRAFT_KINDS)},
                        "object_id": {"type": "string"},
                        "agrees": {"type": "boolean"},
                        "reason": {"type": "string"},
                    },
                },
            }
        },
    }


def assemble_generator_prompt(
    document: SourceDocumentInput,
    *,
    config: dict[str, Any] | None = None,
    root: str | Path | None = None,
) -> str:
    """Assemble a deterministic generator prompt for one rendered document."""
    settings = config or {}
    template_path = get_config_value(
        settings,
        "extraction.prompts.generator",
        "prompts/extract_generator.md",
    )
    template = load_prompt_template(template_path, root=root)
    return template.format(
        document_id=document.document_id,
        document_kind=document.kind,
        tax_year=document.year,
        source_url=document.url,
        operations=", ".join(closed_operations(root=root)),
        schemas=schema_prompt_summary(root=root),
        source_text=document.text,
        fields=field_prompt_summary(document.fields),
        links=json.dumps(document.links, indent=2, sort_keys=True),
        related_sources=related_source_prompt(document),
    )


def assemble_critic_prompt(
    document: SourceDocumentInput,
    *,
    batch: ExtractionBatch | None = None,
    config: dict[str, Any] | None = None,
    root: str | Path | None = None,
) -> str:
    """Assemble the independent critic prompt."""
    settings = config or {}
    template_path = get_config_value(
        settings,
        "extraction.prompts.critic",
        "prompts/extract_critic.md",
    )
    template = load_prompt_template(template_path, root=root)
    return template.format(
        document_id=document.document_id,
        document_kind=document.kind,
        tax_year=document.year,
        source_url=document.url,
        operations=", ".join(closed_operations(root=root)),
        schemas=schema_prompt_summary(root=root),
        source_text=document.text,
        fields=field_prompt_summary(document.fields),
        links=json.dumps(document.links, indent=2, sort_keys=True),
        related_sources=related_source_prompt(document),
        draft_objects=draft_object_prompt_summary(batch),
    )


def draft_object_prompt_summary(batch: ExtractionBatch | None) -> str:
    """Return the draft objects in a compact critic-readable form."""
    if batch is None:
        return "none"
    lines = []
    for obj in batch.objects:
        lines.append(f"- {obj.kind}/{obj.object_id}: {json.dumps(obj.data, sort_keys=True)}")
    return "\n".join(lines)
