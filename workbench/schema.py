"""Validation helpers for the review workbench's public projection schemas."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema


class SchemaValidationError(ValueError):
    """Raised when a workbench projection does not satisfy its public schema."""


_SCHEMA_NAMES = {
    "review_manifest": "review_manifest.schema.json",
    "review_unit": "review_unit.schema.json",
    "review_expression": "review_expression.schema.json",
    "session_state": "session_state.schema.json",
}


def load_schema(name: str, *, schema_dir: str | Path | None = None) -> dict[str, Any]:
    """Load one M15 schema by its stable logical name."""
    try:
        filename = _SCHEMA_NAMES[name]
    except KeyError as exc:
        raise KeyError(f"unknown workbench schema: {name}") from exc
    path = Path(schema_dir) if schema_dir is not None else Path(__file__).resolve().parents[1] / "schemas"
    try:
        schema = json.loads((path / filename).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SchemaValidationError(f"cannot load workbench schema {filename}: {exc}") from exc
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except jsonschema.SchemaError as exc:
        raise SchemaValidationError(f"invalid workbench schema {filename}: {exc.message}") from exc
    return schema


def validate_projection(
    payload: Any,
    name: str,
    *,
    schema_dir: str | Path | None = None,
) -> None:
    """Validate one manifest, unit, expression, or session projection."""
    schema = load_schema(name, schema_dir=schema_dir)
    try:
        jsonschema.validate(
            payload,
            schema,
            format_checker=jsonschema.FormatChecker(),
        )
    except jsonschema.ValidationError as exc:
        raise SchemaValidationError(f"invalid {name}: {exc.message}") from exc


def validate_review_manifest(payload: Any, *, schema_dir: str | Path | None = None) -> None:
    """Validate a generated review manifest."""
    validate_projection(payload, "review_manifest", schema_dir=schema_dir)


def validate_review_unit(payload: Any, *, schema_dir: str | Path | None = None) -> None:
    """Validate one scoped review unit."""
    validate_projection(payload, "review_unit", schema_dir=schema_dir)


def validate_review_expression(payload: Any, *, schema_dir: str | Path | None = None) -> None:
    """Validate one recursive semantic expression tree."""
    validate_projection(payload, "review_expression", schema_dir=schema_dir)


def validate_session_state(payload: Any, *, schema_dir: str | Path | None = None) -> None:
    """Validate non-authoritative resume state for one queue entry."""
    validate_projection(payload, "session_state", schema_dir=schema_dir)
