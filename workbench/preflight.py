"""Fail-closed review-manifest preflight and coverage reporting."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable

import yaml

from workbench.artifacts import ArtifactBundle, GRAPH_OBJECT_KINDS, load_artifact_bundle
from workbench.manifest import ManifestError, build_manifest
from workbench.semantics import SUPPORTED_OPERATIONS, SemanticFormatError


GRAPH_TYPES = frozenset(kind[:-1] if kind.endswith("s") else kind for kind in GRAPH_OBJECT_KINDS)


@dataclass(frozen=True)
class PreflightIssue:
    """One actionable reason the review workbench must not start."""

    code: str
    message: str
    queue_id: str | None = None

    def render(self) -> str:
        """Return a stable, command-line-friendly issue message."""
        prefix = f"{self.code}"
        if self.queue_id:
            prefix += f" [{self.queue_id}]"
        return f"{prefix}: {self.message}"


class PreflightError(ValueError):
    """Raised when one or more fail-closed preflight checks fail."""

    def __init__(self, issues: Iterable[PreflightIssue]):
        self.issues = tuple(issues)
        super().__init__("review preflight failed:\n" + "\n".join(f"- {item.render()}" for item in self.issues))


def run_preflight(
    root: str | Path,
    year: str | int,
    *,
    db_path: str | Path | None = None,
    geometry_path: str | Path | None = None,
    queue_path: str | Path | None = None,
    pdf_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Build and validate the review projection, returning coverage counts."""
    root_path = Path(root).resolve()
    try:
        bundle = load_artifact_bundle(
            root_path,
            year,
            db_path=db_path,
            geometry_path=geometry_path,
            queue_path=queue_path,
            pdf_dir=pdf_dir,
        )
        manifest = build_manifest(
            root_path,
            year,
            db_path=db_path,
            geometry_path=geometry_path,
            queue_path=queue_path,
            pdf_dir=pdf_dir,
        )
    except (ManifestError, SemanticFormatError) as exc:
        raise PreflightError((PreflightIssue("manifest_build_failed", str(exc)),)) from exc
    return preflight_manifest(manifest, bundle)


def preflight_manifest(manifest: dict[str, Any], bundle: ArtifactBundle) -> dict[str, Any]:
    """Validate a built manifest against its public source artifacts."""
    issues: list[PreflightIssue] = []
    pending = {
        str(entry.get("queue_id", "")): entry
        for entry in bundle.review_queue.get("entries", [])
        if isinstance(entry, dict) and _pending(entry)
    }
    manifest_entries = {
        str(entry.get("queue_id", "")): entry
        for entry in manifest.get("entries", [])
        if isinstance(entry, dict)
    }

    for queue_id in sorted(pending):
        entry = manifest_entries.get(queue_id)
        if not entry or not entry.get("units"):
            issues.append(PreflightIssue("zero_units", "pending entry resolves to zero review units", queue_id))

    for queue_id, entry in sorted(pending.items()):
        for ref in entry.get("review_scope", {}).get("object_refs", []) or []:
            if not isinstance(ref, dict) or not _required(ref):
                continue
            object_type = str(ref.get("object_type", ""))
            object_id = str(ref.get("object_id", ""))
            matches = _resolve_objects(ref, bundle)
            if object_type in GRAPH_TYPES | {"node_instance", "decision_option"} and len(matches) != 1:
                issues.append(PreflightIssue(
                    "ambiguous_object",
                    f"required {object_type} {object_id} resolves to {len(matches)} source objects",
                    queue_id,
                ))
            elif object_type not in GRAPH_TYPES | {"node_instance", "decision_option"}:
                source = bundle.root / str(ref.get("source_path", ""))
                if not source.is_file():
                    issues.append(PreflightIssue(
                        "ambiguous_object", f"required {object_type} {object_id} has no resolvable artifact", queue_id
                    ))

    geometry_keys = Counter(_geometry_key(item) for item in bundle.geometry.get("entries", []) if isinstance(item, dict))
    for key, count in sorted(geometry_keys.items(), key=lambda item: str(item[0])):
        if count > 1:
            issues.append(PreflightIssue(
                "ambiguous_geometry", f"geometry reference {key!r} occurs {count} times"
            ))

    for rule in bundle.graph.objects("rules"):
        operation = str(rule.get("operation", "")).upper()
        if operation not in SUPPORTED_OPERATIONS:
            issues.append(PreflightIssue(
                "missing_formatter",
                f"rule {rule.get('rule_id', '<unknown>')} uses unsupported operation {operation or '<missing>'}",
            ))

    for queue_id, entry in sorted(pending.items()):
        if entry.get("kind") in {"promotion_review", "extension_promotion"}:
            refs = entry.get("review_scope", {}).get("object_refs", []) or []
            changed = entry.get("changed_object_ids", []) or []
            primary = [ref for ref in refs if isinstance(ref, dict) and _required(ref)]
            if not changed and not primary:
                issues.append(PreflightIssue(
                    "promotion_scope_missing", "promotion review cannot identify its changed object set", queue_id
                ))
        if entry.get("kind") == "field_map_review":
            issues.extend(_field_map_issues(entry, bundle.root))

    pdf_ids = {pdf.path.stem for pdf in bundle.pdfs}
    for queue_id, entry in sorted(manifest_entries.items()):
        citation_refs: dict[str, dict[str, Any]] = {}
        for unit in entry.get("units", []) or []:
            for value in unit.get("citation_refs", []) or []:
                citation_refs.setdefault(str(value), {"object_type": "citation", "object_id": str(value)})
            for ref in unit.get("object_refs", []) or []:
                if isinstance(ref, dict) and ref.get("object_type") == "citation":
                    citation_refs[str(ref.get("object_id"))] = ref
        for citation_id, ref in sorted(citation_refs.items()):
            matches = _resolve_objects(ref, bundle)
            if len(matches) != 1:
                issues.append(PreflightIssue(
                    "citation_unresolved", f"citation {citation_id} resolves to {len(matches)} artifacts", queue_id
                ))
                continue
            citation = matches[0]
            document_id = str(citation.get("source_document_id") or citation.get("document_id") or "")
            if not citation.get("locator") or document_id not in pdf_ids:
                issues.append(PreflightIssue(
                    "citation_unresolved",
                    f"citation {citation_id} lacks a source PDF or locator",
                    queue_id,
                ))

    if issues:
        raise PreflightError(issues)
    return coverage_report(manifest)


def coverage_report(manifest: dict[str, Any]) -> dict[str, Any]:
    """Count review units by kind, document, object type, and geometry state."""
    kinds: Counter[str] = Counter()
    documents: Counter[str] = Counter()
    objects: Counter[str] = Counter()
    geometry: Counter[str] = Counter()
    total = 0
    for entry in manifest.get("entries", []) or []:
        for unit in entry.get("units", []) or []:
            total += 1
            kinds[str(unit.get("review_kind", "unknown"))] += 1
            location = unit.get("official_location")
            if isinstance(location, dict):
                geometry["located"] += 1
                documents[str(location.get("document_id", "unknown"))] += 1
            else:
                geometry["unlocated"] += 1
                documents["unlocated"] += 1
            for ref in unit.get("object_refs", []) or []:
                if isinstance(ref, dict):
                    objects[str(ref.get("object_type", "unknown"))] += 1
    return {
        "entries": len(manifest.get("entries", []) or []),
        "units": total,
        "by_kind": dict(sorted(kinds.items())),
        "by_document": dict(sorted(documents.items())),
        "by_object": dict(sorted(objects.items())),
        "by_geometry": dict(sorted(geometry.items())),
    }


def _field_map_issues(entry: dict[str, Any], root: Path) -> list[PreflightIssue]:
    queue_id = str(entry.get("queue_id", ""))
    actual = {
        (str(ref.get("object_type", "")), str(ref.get("object_id", "")), str(ref.get("role", "primary")))
        for ref in entry.get("review_scope", {}).get("object_refs", []) or []
        if isinstance(ref, dict)
    }
    expected: set[tuple[str, str, str]] = set()
    for relative in entry.get("artifact_paths", []) or []:
        path = root / str(relative)
        if path.suffix.lower() not in {".yaml", ".yml"} or not path.is_file():
            continue
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or "mappings" not in payload:
            continue
        for item in payload.get("mappings", []) or []:
            if item.get("node_id"):
                expected.add(("node", str(item["node_id"]), "primary"))
            elif item.get("identity_slot"):
                expected.add(("field", str(item["identity_slot"]), "primary"))
        for item in payload.get("field_dispositions", []) or []:
            if item.get("field_name"):
                expected.add(("field_control", str(item["field_name"]), "primary"))
        for item in payload.get("excluded_nodes", []) or []:
            if item.get("node_id"):
                expected.add(("node", str(item["node_id"]), "excluded"))
        for item in payload.get("frontier_fields", []) or []:
            if item.get("frontier_id"):
                expected.add(("frontier_field", str(item["frontier_id"]), "frontier"))
        if not any(role == "primary" for _, _, role in expected):
            document_id = str(payload.get("document_id") or entry.get("document_id") or "")
            expected.add(("field_inventory", document_id, "primary"))
    missing = sorted(expected - actual)
    if not missing:
        return []
    preview = ", ".join(f"{kind}:{object_id} ({role})" for kind, object_id, role in missing[:5])
    suffix = f" and {len(missing) - 5} more" if len(missing) > 5 else ""
    return [PreflightIssue(
        "field_map_incomplete", f"field-map scope omits {preview}{suffix}", queue_id
    )]


def _resolve_objects(ref: dict[str, Any], bundle: ArtifactBundle) -> tuple[dict[str, Any], ...]:
    object_type = str(ref.get("object_type", ""))
    object_id = str(ref.get("object_id", ""))
    lookup_type = "node" if object_type == "node_instance" else object_type
    lookup_id = object_id.split("#", 1)[0] if object_type == "node_instance" else object_id
    artifact_path = str(ref.get("source_path") or ref.get("artifact_path") or "").replace("\\", "/")
    if "/_drafts/" in artifact_path:
        draft_dir = artifact_path.rsplit("/", 1)[0]
        files = bundle.drafts.get(draft_dir, {})
        filename = f"{lookup_type}s.yaml"
        payload = files.get(filename, [])
        items = payload if isinstance(payload, list) else []
        key = _id_key(lookup_type)
        if lookup_type == "decision_option":
            return tuple(
                option
                for decision in files.get("decisions.yaml", []) or []
                if isinstance(decision, dict)
                for option in decision.get("options", []) or []
                if isinstance(option, dict) and str(option.get("option_id")) == lookup_id
            )
        return tuple(item for item in items if isinstance(item, dict) and key and str(item.get(key)) == lookup_id)
    source_path = bundle.root / artifact_path if artifact_path else None
    key = _id_key(lookup_type)
    if source_path is not None and source_path.is_file() and key and lookup_type == "decision_option":
        try:
            if source_path.suffix.lower() in {".yaml", ".yml"}:
                payload = yaml.safe_load(source_path.read_text(encoding="utf-8"))
            elif source_path.suffix.lower() == ".json":
                payload = json.loads(source_path.read_text(encoding="utf-8"))
            else:
                payload = None
        except (OSError, ValueError, yaml.YAMLError):
            payload = None
        source_matches = tuple(
            item for item in _walk_mappings(payload)
            if str(item.get(key)) == lookup_id
        )
        if source_matches:
            return source_matches
    if lookup_type == "decision_option":
        return tuple(
            option
            for decision in bundle.graph.objects("decisions")
            for option in decision.get("options", []) or []
            if isinstance(option, dict) and str(option.get("option_id")) == lookup_id
        )
    plural = f"{lookup_type}s"
    if plural not in GRAPH_OBJECT_KINDS:
        return ()
    key = _id_key(lookup_type)
    return tuple(
        item for item in bundle.graph.objects(plural)
        if key and str(item.get(key)) == lookup_id
    )


def _id_key(object_type: str) -> str | None:
    return {
        "document": "document_id", "node": "node_id", "table": "table_id",
        "edge": "edge_id", "rule": "rule_id", "citation": "citation_id",
        "decision": "decision_id", "decision_option": "option_id", "routing_edge": "routing_id",
        "trigger": "trigger_id", "expectation": "expectation_id",
    }.get(object_type)


def _walk_mappings(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_mappings(child)


def _geometry_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return (
        item.get("node_id"), item.get("identity_slot"), item.get("field_name"),
        item.get("document_id"), item.get("page"), tuple(item.get("rect", []) or []),
    )


def _pending(entry: dict[str, Any]) -> bool:
    return str(entry.get("status", "")) == "pending" or str(entry.get("review_status", "")) == "pending"


def _required(ref: dict[str, Any]) -> bool:
    return str(ref.get("role", "primary")) in {"primary", "expected"}
