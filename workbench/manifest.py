"""Build the deterministic, structure-only review manifest projection."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

from workbench.artifacts import ArtifactBundle, GRAPH_OBJECT_KINDS, load_artifact_bundle
from workbench.schema import validate_review_manifest
from workbench.semantics import FormattedSemantics, format_scope_semantics


class ManifestError(ValueError):
    """Raised when published artifacts cannot produce a scoped manifest."""


@dataclass(frozen=True)
class ManifestResult:
    """Result of writing a generated manifest."""

    payload: dict[str, Any]
    path: Path | None


def build_manifest(
    root: str | Path,
    year: str | int,
    *,
    db_path: str | Path | None = None,
    geometry_path: str | Path | None = None,
    queue_path: str | Path | None = None,
    pdf_dir: str | Path | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Project pending review entries into a stable schema-valid manifest.

    The projection only copies identifiers and relationships from published
    artifacts. It does not compute tax values or invent analog geometry.
    """
    root_path = Path(root).resolve()
    bundle = load_artifact_bundle(
        root_path,
        year,
        db_path=db_path,
        geometry_path=geometry_path,
        queue_path=queue_path,
        pdf_dir=pdf_dir,
    )
    payload = _build_payload(bundle, root_path, db_path=db_path, geometry_path=geometry_path, queue_path=queue_path)
    validate_review_manifest(payload)
    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return payload


def write_manifest(
    root: str | Path,
    year: str | int,
    *,
    output_path: str | Path,
    db_path: str | Path | None = None,
    geometry_path: str | Path | None = None,
    queue_path: str | Path | None = None,
    pdf_dir: str | Path | None = None,
) -> ManifestResult:
    """Build and write a manifest, returning both its payload and path."""
    path = Path(output_path).resolve()
    payload = build_manifest(
        root,
        year,
        db_path=db_path,
        geometry_path=geometry_path,
        queue_path=queue_path,
        pdf_dir=pdf_dir,
        output_path=path,
    )
    return ManifestResult(payload=payload, path=path)


def _build_payload(
    bundle: ArtifactBundle,
    root: Path,
    *,
    db_path: str | Path | None,
    geometry_path: str | Path | None,
    queue_path: str | Path | None,
) -> dict[str, Any]:
    graph_index = _graph_index(bundle)
    pdf_hashes = {pdf.path.stem: pdf.sha256 for pdf in bundle.pdfs}
    geometry = bundle.geometry.get("entries", [])
    entries: list[dict[str, Any]] = []
    source_paths: set[Path] = set()
    source_paths.update(
        {
            bundle.graph.path,
            _default_or_given(root / "graph" / str(bundle.tax_year) / "node_geometry.json", geometry_path),
            _default_or_given(
                root / "review_queue" / str(bundle.tax_year) / "deferred_review.yaml",
                queue_path,
            ),
        }
    )
    source_paths.update(pdf.path for pdf in bundle.pdfs)

    for queue_entry in bundle.review_queue.get("entries", []):
        if not isinstance(queue_entry, dict) or not _pending(queue_entry):
            continue
        queue_id = str(queue_entry.get("queue_id", ""))
        scope = queue_entry.get("review_scope")
        if not isinstance(scope, dict) or not isinstance(scope.get("object_refs"), list):
            raise ManifestError(f"pending queue entry {queue_id} has no review scope")
        refs = [ref for ref in scope["object_refs"] if isinstance(ref, dict)]
        if not refs:
            raise ManifestError(f"pending queue entry {queue_id} has an empty review scope")
        units: list[dict[str, Any]] = []
        for ref_index, scope_ref in enumerate(refs):
            artifact_path = str(scope_ref.get("source_path", ""))
            if artifact_path:
                source_paths.add(root / artifact_path)
            object_ref = _manifest_ref(scope_ref, graph_index)
            object_data = _find_object(graph_index, scope_ref)
            semantics = _semantics(scope_ref, graph_index)
            locations = _locations(scope_ref, geometry, pdf_hashes)
            if not locations:
                locations = [None]
            for location_index, location in enumerate(locations):
                unit_id = _unit_id(queue_id, ref_index, location_index, scope_ref)
                units.append(
                    _unit(
                        queue_entry,
                        unit_id=unit_id,
                        scope_ref=scope_ref,
                        object_ref=object_ref,
                        object_data=object_data,
                        graph_index=graph_index,
                        semantics=semantics,
                        location=location,
                        required=_required(scope_ref),
                    )
                )
        if not units:
            raise ManifestError(f"pending queue entry {queue_id} produced zero units")
        entries.append(
            {
                "queue_id": queue_id,
                "review_kind": str(queue_entry.get("kind", "object")),
                "status": str(queue_entry.get("status") or queue_entry.get("review_status") or "pending"),
                "summary": str(queue_entry.get("summary", "Review scoped artifacts.")),
                "units": units,
            }
        )

    source_artifacts = _source_artifacts(root, source_paths)
    body = {
        "schema_version": 1,
        "tax_year": bundle.tax_year,
        "source_artifacts": source_artifacts,
        "entries": entries,
    }
    canonical = json.dumps(body, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {**body, "manifest_hash": hashlib.sha256(canonical).hexdigest()}


def _unit(
    queue_entry: dict[str, Any],
    *,
    unit_id: str,
    scope_ref: dict[str, Any],
    object_ref: dict[str, Any],
    object_data: dict[str, Any] | None,
    graph_index: dict[tuple[str, str], dict[str, Any]],
    semantics: FormattedSemantics | None,
    location: dict[str, Any] | None,
    required: bool,
) -> dict[str, Any]:
    object_type = str(scope_ref.get("object_type", "object"))
    object_id = str(scope_ref.get("object_id", ""))
    review_kind = str(queue_entry.get("kind", "object"))
    citations = sorted(set(_citation_refs(object_data)) | set(_expression_citations(semantics)))
    unit: dict[str, Any] = {
        "queue_id": str(queue_entry.get("queue_id", "")),
        "unit_id": unit_id,
        "review_kind": review_kind,
        "required": required,
        "object_refs": [object_ref],
        "official_location": location,
        "analog_placement": None,
        "semantic_class": semantics.semantic_class if semantics else _semantic_class(review_kind, scope_ref, object_data),
        "summary": semantics.summary if semantics else str(queue_entry.get("summary", "Review scoped artifacts.")),
        "expression": semantics.expression if semantics else {"kind": "reference", "ref": object_ref},
        "coverage": {"state": "pending", "required_for_confirm": required},
    }
    if citations:
        unit["citation_refs"] = citations
    source_refs = _source_refs(object_data, object_type, graph_index=graph_index)
    if source_refs:
        unit["source_refs"] = source_refs
    witnesses = [str(value) for value in queue_entry.get("machine_witnesses", []) or []]
    if witnesses:
        unit["witness_refs"] = witnesses
    if queue_entry.get("verification_tier"):
        unit["trust"] = str(queue_entry["verification_tier"])
    changed = [str(value) for value in queue_entry.get("changed_object_ids", []) or []]
    if changed:
        unit["promotion_diff_refs"] = changed
    return unit


def _manifest_ref(scope_ref: dict[str, Any], graph_index: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    object_type = str(scope_ref.get("object_type", ""))
    object_id = str(scope_ref.get("object_id", ""))
    if not object_type or not object_id:
        raise ManifestError("review scope contains an incomplete object reference")
    result: dict[str, Any] = {"object_type": object_type, "object_id": object_id}
    if scope_ref.get("source_path"):
        result["artifact_path"] = str(scope_ref["source_path"])
    object_data = graph_index.get((object_type, object_id))
    label = _display_label(object_data, object_id)
    if label:
        result["display_label"] = label
    return result


def _locations(
    scope_ref: dict[str, Any],
    geometry: Iterable[dict[str, Any]],
    pdf_hashes: dict[str, str],
) -> list[dict[str, Any]]:
    object_type = str(scope_ref.get("object_type", ""))
    object_id = str(scope_ref.get("object_id", ""))
    base_id = object_id.split("#", 1)[0]
    matches: list[dict[str, Any]] = []
    for entry in geometry:
        if not isinstance(entry, dict):
            continue
        node_match = object_type in {"node", "node_instance"} and entry.get("node_id") == base_id
        field_match = object_type in {"field", "field_inventory"} and (
            entry.get("identity_slot") == object_id or entry.get("field_name") == object_id
        )
        if not (node_match or field_match):
            continue
        document_id = str(entry.get("document_id", ""))
        source_hash = pdf_hashes.get(document_id)
        if not source_hash:
            continue
        location: dict[str, Any] = {
            "document_id": document_id,
            "source_pdf_hash": source_hash,
            "page": int(entry["page"]),
            "rect": [float(value) for value in entry["rect"]],
        }
        locator = entry.get("field_name") or entry.get("slot") or entry.get("identity_slot")
        if locator:
            location["locator_text"] = str(locator)
        matches.append(location)
    return matches


def _graph_index(bundle: ArtifactBundle) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for kind in GRAPH_OBJECT_KINDS:
        object_type = kind[:-1] if kind.endswith("s") else kind
        for obj in bundle.graph.objects(kind):
            object_id = _object_id(object_type, obj)
            if object_id:
                result[(object_type, object_id)] = obj
            if object_type == "decision":
                for option in obj.get("options", []) or []:
                    if isinstance(option, dict) and option.get("option_id"):
                        result[("decision_option", str(option["option_id"]))] = option
    return result


def _object_id(object_type: str, obj: dict[str, Any]) -> str | None:
    key = {
        "document": "document_id",
        "node": "node_id",
        "table": "table_id",
        "edge": "edge_id",
        "rule": "rule_id",
        "citation": "citation_id",
        "decision": "decision_id",
        "routing_edge": "routing_id",
        "trigger": "trigger_id",
        "expectation": "expectation_id",
    }.get(object_type)
    value = obj.get(key) if key else None
    return str(value) if value is not None else None


def _find_object(
    graph_index: dict[tuple[str, str], dict[str, Any]],
    scope_ref: dict[str, Any],
) -> dict[str, Any] | None:
    return graph_index.get((str(scope_ref.get("object_type", "")), str(scope_ref.get("object_id", ""))))


def _semantics(
    scope_ref: dict[str, Any],
    graph_index: dict[tuple[str, str], dict[str, Any]],
) -> FormattedSemantics | None:
    return format_scope_semantics(scope_ref, graph_index)


def _citation_refs(object_data: dict[str, Any] | None) -> list[str]:
    if not isinstance(object_data, dict):
        return []
    return sorted({str(value) for value in object_data.get("citation_refs", []) or []})


def _expression_citations(semantics: FormattedSemantics | None) -> list[str]:
    """Collect citations from every level of a formatted expression tree."""
    if semantics is None:
        return []
    citations: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            citations.update(str(item) for item in value.get("citation_refs", []) or [])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(semantics.expression)
    return sorted(citations)


def _source_refs(
    object_data: dict[str, Any] | None,
    object_type: str,
    graph_index: dict[tuple[str, str], dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    if object_type != "edge" or not isinstance(object_data, dict):
        return []
    refs: list[dict[str, Any]] = []
    for direction, key in (("source", "source"), ("target", "target")):
        value = object_data.get(key)
        if value:
            ref: dict[str, Any] = {
                "direction": direction,
                "object_type": "node",
                "object_id": str(value),
            }
            if graph_index is not None:
                ref["display_label"] = _display_label(
                    graph_index.get(("node", str(value))),
                    str(value),
                )
            refs.append(ref)
    return refs


def _semantic_class(review_kind: str, scope_ref: dict[str, Any], object_data: dict[str, Any] | None) -> str:
    object_type = str(scope_ref.get("object_type", ""))
    role = str(scope_ref.get("role", ""))
    if review_kind.startswith("field_map") or object_type in {"field", "field_inventory"}:
        return "field_map"
    if review_kind.startswith("intake") or object_type in {"routing_edge", "trigger", "expectation"}:
        return "contract"
    if review_kind.startswith("decision") or object_type in {"decision", "decision_option"}:
        return "decision"
    if review_kind.startswith("frontier") or role in {"frontier", "excluded"} or object_type.startswith("frontier"):
        return "frontier"
    if review_kind.startswith("irs_example") or object_type == "node_instance":
        return "example"
    if object_type == "citation":
        return "citation"
    if object_type == "rule" and isinstance(object_data, dict):
        operation = str(object_data.get("operation", "")).upper()
        if operation in {"LOOKUP_TABLE", "LOOKUP_BRACKET"}:
            return "lookup"
        if operation in {"IF_ELSE", "MAX", "MIN"}:
            return "branch"
    return "calculation"


def _display_label(object_data: dict[str, Any] | None, fallback: str) -> str:
    if not isinstance(object_data, dict):
        return fallback
    for key in ("label", "title", "question", "description", "relationship"):
        value = object_data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return fallback


def _required(scope_ref: dict[str, Any]) -> bool:
    return str(scope_ref.get("role", "primary")) in {"primary", "expected"}


def _pending(entry: dict[str, Any]) -> bool:
    return str(entry.get("status", "")) == "pending" or str(entry.get("review_status", "")) == "pending"


def _unit_id(queue_id: str, ref_index: int, location_index: int, scope_ref: dict[str, Any]) -> str:
    raw = f"{queue_id}_ref_{ref_index:04d}_loc_{location_index:02d}_{scope_ref.get('object_id', 'object')}"
    return re.sub(r"[^a-z0-9_]", "_", raw.lower()).strip("_")


def _source_artifacts(root: Path, paths: Iterable[Path]) -> list[dict[str, str]]:
    files: set[Path] = set()
    for path in {item.resolve() for item in paths}:
        if path.is_file():
            files.add(path)
        elif path.is_dir():
            files.update(item.resolve() for item in path.rglob("*") if item.is_file())
        else:
            raise ManifestError(f"review source artifact does not exist: {path}")

    artifacts: list[dict[str, str]] = []
    for path in sorted(files):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            relative = path.as_posix()
        artifacts.append({"path": relative, "content_hash": digest})
    return artifacts


def _default_or_given(default: Path, given: str | Path | None) -> Path:
    return Path(given).resolve() if given is not None else default.resolve()
