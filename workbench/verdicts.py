"""Schema'd, append-only review verdict emission."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema
import yaml


@dataclass(frozen=True)
class ReviewVerdict:
    """One human decision emitted for later pipeline application."""

    payload: dict[str, Any]
    path: Path | None = None

    @property
    def verdict_id(self) -> str:
        return str(self.payload["verdict_id"])


def emit_verdict(
    *,
    root: str | Path,
    year: str | int,
    queue_id: str,
    manifest_hash: str,
    verdict_id: str,
    reviewer_id: str,
    human_minutes: float,
    verdict: str,
    reviewed_at: str | None = None,
    reason: str | None = None,
    object_ref: dict[str, str] | None = None,
    source_override: dict[str, Any] | None = None,
    output_path: str | Path | None = None,
) -> ReviewVerdict:
    """Write one new verdict file; never overwrite an existing verdict."""
    payload: dict[str, Any] = {
        "verdict_id": verdict_id,
        "tax_year": int(year),
        "queue_id": queue_id,
        "manifest_hash": manifest_hash,
        "reviewer_id": reviewer_id,
        "reviewed_at": reviewed_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "human_minutes": human_minutes,
        "verdict": verdict,
    }
    if object_ref:
        payload["object_ref"] = dict(object_ref)
    if reason:
        payload["reason"] = reason
    if source_override:
        payload["source_override"] = dict(source_override)
    payload["content_hash"] = verdict_content_hash(payload)
    validate_verdict(payload, schema_path=Path(root).resolve() / "schemas" / "review_verdict.schema.json")

    path = Path(output_path) if output_path is not None else Path(root).resolve() / "review_verdicts" / str(year) / f"{verdict_id}.yaml"
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=False)
    text.encode("ascii")
    try:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
    except FileExistsError as exc:
        raise FileExistsError(f"verdict is append-only and already exists: {path}") from exc
    return ReviewVerdict(payload=payload, path=path)


def load_verdict(path: str | Path, *, schema_path: str | Path | None = None) -> ReviewVerdict:
    """Load, schema-validate, and content-hash-check one verdict file."""
    verdict_path = Path(path).resolve()
    try:
        payload = yaml.safe_load(verdict_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot read verdict {verdict_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"verdict must be a mapping: {verdict_path}")
    schema = Path(schema_path) if schema_path is not None else verdict_path.parents[2] / "schemas" / "review_verdict.schema.json"
    validate_verdict(payload, schema_path=schema)
    if verdict_content_hash(payload) != payload["content_hash"]:
        raise ValueError(f"verdict content hash mismatch: {verdict_path}")
    if verdict_path.stem != str(payload["verdict_id"]):
        raise ValueError(f"verdict filename does not match verdict_id: {verdict_path}")
    return ReviewVerdict(payload=dict(payload), path=verdict_path)


def validate_verdict(payload: dict[str, Any], *, schema_path: str | Path) -> None:
    """Validate the public verdict schema and human-review constraints."""
    try:
        schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
        jsonschema.validate(payload, schema, format_checker=jsonschema.FormatChecker())
    except (OSError, json.JSONDecodeError, jsonschema.SchemaError) as exc:
        raise ValueError(f"cannot load review verdict schema: {exc}") from exc
    except jsonschema.ValidationError as exc:
        raise ValueError(f"invalid review verdict: {exc.message}") from exc
    if str(payload.get("reviewer_id", "")).strip().lower() in {"agent", "codex", "worker", "system"}:
        raise ValueError("reviewer_id must identify the human reviewer")
    if payload.get("verdict") != "confirmed" and not str(payload.get("reason", "")).strip():
        raise ValueError("a non-confirmed verdict requires a reason")
    if payload.get("verdict") == "source_pathology":
        override = payload.get("source_override")
        if not isinstance(override, dict) or not str(override.get("provenance", "")).strip():
            raise ValueError("source_pathology requires marked source provenance")


def verdict_content_hash(payload: dict[str, Any]) -> str:
    """Hash the canonical verdict payload excluding its self-hash."""
    unsigned = {key: value for key, value in payload.items() if key != "content_hash"}
    canonical = json.dumps(unsigned, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
