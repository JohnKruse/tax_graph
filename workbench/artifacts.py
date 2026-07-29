"""Read-only loaders for the review workbench artifact contract.

This module intentionally uses only Python stdlib plus the public YAML and
JSON Schema formats. In particular, it does not import ``tax_graph`` or any
pipeline implementation module. The workbench can therefore inspect a
published artifact set without sharing the pipeline's object model.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping
from urllib.parse import quote

import jsonschema
import yaml


GRAPH_OBJECT_KINDS = (
    "documents",
    "nodes",
    "tables",
    "edges",
    "rules",
    "citations",
    "decisions",
    "routing_edges",
    "triggers",
    "expectations",
)


class ArtifactError(ValueError):
    """Base error for an unreadable or inconsistent published artifact."""


class ArtifactValidationError(ArtifactError):
    """Raised when a public artifact does not satisfy its schema."""


@dataclass(frozen=True)
class PdfArtifact:
    """Metadata for one source PDF, without importing a PDF renderer."""

    path: Path
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class SqliteGraphArtifact:
    """The read-only projection of a compiled graph SQLite artifact."""

    path: Path
    tax_year: int
    schema_version: int
    content_hash: str
    objects_by_kind: Mapping[str, tuple[dict[str, Any], ...]]
    tax_table: tuple[dict[str, Any], ...]

    def objects(self, kind: str) -> tuple[dict[str, Any], ...]:
        """Return public graph objects of one compiled kind."""
        if kind not in GRAPH_OBJECT_KINDS:
            raise KeyError(f"unknown graph object kind: {kind}")
        return self.objects_by_kind.get(kind, ())

    def find(self, kind: str, object_id: str) -> dict[str, Any] | None:
        """Find one object by the kind-specific id stored in its JSON."""
        for obj in self.objects(kind):
            if any(
                str(obj.get(key)) == object_id
                for key in (
                    "document_id",
                    "node_id",
                    "table_id",
                    "edge_id",
                    "rule_id",
                    "citation_id",
                    "decision_id",
                    "routing_id",
                    "trigger_id",
                    "expectation_id",
                )
            ):
                return obj
        return None


@dataclass(frozen=True)
class ArtifactBundle:
    """All artifact views needed by the workbench for one tax year."""

    root: Path
    tax_year: int
    graph: SqliteGraphArtifact
    geometry: dict[str, Any]
    review_queue: dict[str, Any]
    drafts: Mapping[str, Mapping[str, Any]]
    metrics: Mapping[str, dict[str, Any]]
    nversion_reports: Mapping[str, dict[str, Any]]
    mined_examples: Mapping[str, dict[str, Any]]
    pdfs: tuple[PdfArtifact, ...]


def load_sqlite_graph(path: str | Path) -> SqliteGraphArtifact:
    """Read a compiled graph using SQLite's read-only URI mode."""
    db_path = Path(path).resolve()
    if not db_path.is_file():
        raise FileNotFoundError(f"compiled graph not found: {db_path}")

    # URI mode is intentional: a review session must not create or modify a
    # database as a side effect of opening it.
    uri = f"file:{quote(db_path.as_posix(), safe='/')}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True) as conn:
            metadata = {
                str(key): str(value)
                for key, value in conn.execute("SELECT key, value FROM metadata")
            }
            try:
                tax_year = int(metadata["tax_year"])
                schema_version = int(metadata["schema_version"])
                content_hash = metadata["content_hash"]
            except (KeyError, TypeError, ValueError) as exc:
                raise ArtifactError(f"invalid graph metadata in {db_path}") from exc

            present_tables = {
                str(row[0])
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            objects: dict[str, tuple[dict[str, Any], ...]] = {}
            for kind in GRAPH_OBJECT_KINDS:
                if kind not in present_tables:
                    objects[kind] = ()
                    continue
                rows = conn.execute(
                    f"SELECT object_json FROM {kind} ORDER BY rowid"
                ).fetchall()
                objects[kind] = tuple(_decode_object(row[0], db_path) for row in rows)

            tax_rows: tuple[dict[str, Any], ...] = ()
            if "tax_table" in present_tables:
                columns = [str(row[1]) for row in conn.execute("PRAGMA table_info(tax_table)")]
                tax_rows = tuple(
                    dict(zip(columns, row, strict=True))
                    for row in conn.execute("SELECT * FROM tax_table ORDER BY rowid")
                )
    except sqlite3.Error as exc:
        raise ArtifactError(f"cannot read compiled graph {db_path}: {exc}") from exc

    return SqliteGraphArtifact(
        path=db_path,
        tax_year=tax_year,
        schema_version=schema_version,
        content_hash=content_hash,
        objects_by_kind=objects,
        tax_table=tax_rows,
    )


def load_geometry(path: str | Path, *, schema_path: str | Path | None = None) -> dict[str, Any]:
    """Load and validate the published node-to-page geometry projection."""
    return _load_json_schema_artifact(path, schema_path=schema_path, label="node geometry")


def load_review_queue(path: str | Path, *, schema_path: str | Path | None = None) -> dict[str, Any]:
    """Load and validate an explicitly supplied legacy deferred-review fixture."""
    return _load_yaml_schema_artifact(path, schema_path=schema_path, label="review queue")


def load_pdf(path: str | Path) -> PdfArtifact:
    """Load source-PDF metadata without rasterizing or altering the file."""
    pdf_path = Path(path).resolve()
    if not pdf_path.is_file():
        raise FileNotFoundError(f"source PDF not found: {pdf_path}")
    digest = hashlib.sha256()
    with pdf_path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return PdfArtifact(path=pdf_path, size_bytes=pdf_path.stat().st_size, sha256=digest.hexdigest())


def load_drafts(root: str | Path, year: str | int) -> dict[str, dict[str, Any]]:
    """Load draft-directory files as path-keyed artifact data.

    YAML and JSON files are decoded; review Markdown/HTML is retained as text.
    The returned keys are workspace-relative paths so an artifact can be shown
    to a reviewer without relying on a pipeline module or a hidden path map.
    """
    root_path = Path(root).resolve()
    draft_dirs = _draft_directories(root_path, str(year))
    result: dict[str, dict[str, Any]] = {}
    for draft_dir in draft_dirs:
        relative_dir = draft_dir.relative_to(root_path).as_posix()
        files: dict[str, Any] = {}
        for path in sorted(item for item in draft_dir.iterdir() if item.is_file()):
            files[path.name] = _load_loose_file(path)
        result[relative_dir] = files
    return result


def load_metrics(root: str | Path, year: str | int) -> dict[str, dict[str, Any]]:
    """Return validated-by-shape metrics artifacts keyed by workspace path."""
    return _load_named_draft_files(root, year, "metrics.yaml")


def load_nversion_reports(root: str | Path, year: str | int) -> dict[str, dict[str, Any]]:
    """Return N-version report artifacts keyed by workspace path."""
    return _load_named_draft_files(root, year, "nversion.yaml")


def load_mined_examples(root: str | Path, year: str | int) -> dict[str, dict[str, Any]]:
    """Return mined-example artifacts keyed by workspace path."""
    return _load_named_draft_files(root, year, "example_mining.yaml")


def load_artifact_bundle(
    root: str | Path,
    year: str | int,
    *,
    db_path: str | Path | None = None,
    pdf_dir: str | Path | None = None,
    geometry_path: str | Path | None = None,
    queue_path: str | Path | None = None,
) -> ArtifactBundle:
    """Load the complete published artifact view for one tax year."""
    root_path = Path(root).resolve()
    tax_year = int(year)
    schema_dir = root_path / "schemas"
    graph = load_sqlite_graph(
        db_path
        if db_path is not None
        else root_path / "build" / f"tax_graph_{tax_year}.sqlite"
    )
    geometry = load_geometry(
        geometry_path
        if geometry_path is not None
        else root_path / "graph" / str(tax_year) / "node_geometry.json",
        schema_path=schema_dir / "node_geometry.schema.json",
    )
    # The generated deferred queue is retired. Keep an explicit path override for
    # isolated legacy-artifact fixtures, but never make the deleted live file a
    # workbench dependency.
    queue = (
        load_review_queue(queue_path, schema_path=schema_dir / "deferred_review_queue.schema.json")
        if queue_path is not None
        else {"tax_year": tax_year, "entries": []}
    )
    pdf_root = Path(pdf_dir) if pdf_dir is not None else root_path / ".cache" / "raw" / str(tax_year)
    pdfs = tuple(load_pdf(path) for path in sorted(pdf_root.glob("*.pdf"))) if pdf_root.is_dir() else ()
    return ArtifactBundle(
        root=root_path,
        tax_year=tax_year,
        graph=graph,
        geometry=geometry,
        review_queue=queue,
        drafts=load_drafts(root_path, tax_year),
        metrics=load_metrics(root_path, tax_year),
        nversion_reports=load_nversion_reports(root_path, tax_year),
        mined_examples=load_mined_examples(root_path, tax_year),
        pdfs=pdfs,
    )


def _load_json_schema_artifact(
    path: str | Path,
    *,
    schema_path: str | Path | None,
    label: str,
) -> dict[str, Any]:
    artifact_path = Path(path).resolve()
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactError(f"cannot read {label} {artifact_path}: {exc}") from exc
    _validate_payload(payload, schema_path=schema_path, label=label, path=artifact_path)
    if not isinstance(payload, dict):
        raise ArtifactValidationError(f"{label} must be a mapping: {artifact_path}")
    return payload


def _load_yaml_schema_artifact(
    path: str | Path,
    *,
    schema_path: str | Path | None,
    label: str,
) -> dict[str, Any]:
    artifact_path = Path(path).resolve()
    try:
        payload = yaml.safe_load(artifact_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ArtifactError(f"cannot read {label} {artifact_path}: {exc}") from exc
    _validate_payload(payload, schema_path=schema_path, label=label, path=artifact_path)
    if not isinstance(payload, dict):
        raise ArtifactValidationError(f"{label} must be a mapping: {artifact_path}")
    return payload


def _validate_payload(
    payload: Any,
    *,
    schema_path: str | Path | None,
    label: str,
    path: Path,
) -> None:
    if schema_path is None:
        return
    schema_file = Path(schema_path)
    try:
        schema = json.loads(schema_file.read_text(encoding="utf-8"))
        jsonschema.validate(payload, schema)
    except (OSError, json.JSONDecodeError, jsonschema.SchemaError) as exc:
        raise ArtifactError(f"cannot load {label} schema {schema_file}: {exc}") from exc
    except jsonschema.ValidationError as exc:
        raise ArtifactValidationError(f"invalid {label} {path}: {exc.message}") from exc


def _decode_object(raw: Any, path: Path) -> dict[str, Any]:
    try:
        value = json.loads(str(raw))
    except json.JSONDecodeError as exc:
        raise ArtifactError(f"invalid object JSON in {path}") from exc
    if not isinstance(value, dict):
        raise ArtifactError(f"object JSON is not a mapping in {path}")
    return value


def _draft_directories(root: Path, year: str) -> list[Path]:
    candidates = [root / "graph" / year / "_drafts"]
    extension_root = root / "graph_ext" / year
    if extension_root.is_dir():
        candidates.extend(path for path in extension_root.rglob("_drafts") if path.is_dir())
    return sorted(
        path
        for parent in candidates
        if parent.is_dir()
        for path in parent.iterdir()
        if path.is_dir()
    )


def _load_named_draft_files(root: str | Path, year: str | int, filename: str) -> dict[str, dict[str, Any]]:
    root_path = Path(root).resolve()
    result: dict[str, dict[str, Any]] = {}
    for draft_dir in _draft_directories(root_path, str(year)):
        path = draft_dir / filename
        if path.is_file():
            value = _load_loose_file(path)
            if isinstance(value, dict):
                result[path.relative_to(root_path).as_posix()] = value
    return result


def _load_loose_file(path: Path) -> Any:
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            return yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise ArtifactError(f"cannot read artifact {path}: {exc}") from exc
    if path.suffix.lower() == ".json":
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ArtifactError(f"cannot read artifact {path}: {exc}") from exc
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ArtifactError(f"cannot read artifact {path}: {exc}") from exc
