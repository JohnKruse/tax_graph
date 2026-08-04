"""Apply human review verdict artifacts to the pipeline-owned graph."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from tax_graph.addressing import load_address_artifacts
from tax_graph.io.loader import load_graph


_ID_FIELDS = {
    "documents": "document_id",
    "nodes": "node_id",
    "tables": "table_id",
    "edges": "edge_id",
    "rules": "rule_id",
    "citations": "citation_id",
    "decisions": "decision_id",
}
_REVIEWABLE_KINDS = {"documents", "nodes", "decisions"}
_ADDRESS_JUDGEMENTS = frozenset({"confirmed", "questioned", "rejected"})
_ADDRESS_JUDGEMENT_ALIASES = {
    "approved": "confirmed",
    "problem": "questioned",
    "pipeline_defect": "rejected",
    "source_pathology": "rejected",
}


def _canonical_address_judgement(value: Any) -> str:
    """Normalize the address-ledger vocabulary without guessing unknown tokens."""
    token = str(value or "").strip()
    return _ADDRESS_JUDGEMENT_ALIASES.get(token, token)


def _node_review_fields(judgement: str) -> dict[str, Any]:
    """Return the node flags for one explicit reviewer observation."""
    if judgement == "confirmed":
        return {"human_confirmed": True, "verification_tier": "human-confirmed"}
    if judgement == "questioned":
        return {"human_confirmed": False, "verification_tier": "human-questioned"}
    if judgement == "rejected":
        return {"human_confirmed": False, "verification_tier": "human-rejected"}
    raise ValueError(f"unsupported address judgement: {judgement or '<missing>'}")


@dataclass(frozen=True)
class ApplyResult:
    """Summary of one verdict-application run."""

    applied: tuple[str, ...]
    confirmed: tuple[str, ...]
    pipeline_defects: tuple[str, ...]
    source_pathologies: tuple[str, ...]
    queue_path: Path
    provenance_path: Path
    questioned: tuple[str, ...] = ()
    rejected: tuple[str, ...] = ()


@dataclass(frozen=True)
class AddressApplyResult:
    """Report one address-ledger projection without hiding skipped records."""

    applied: tuple[str, ...]
    would_apply: tuple[str, ...]
    stale: tuple[str, ...]
    unresolved: tuple[str, ...]
    ambiguous: tuple[str, ...]
    unsupported_judgements: tuple[str, ...]
    reports: tuple[dict[str, Any], ...]
    dry_run: bool


def apply_address_verdicts(
    year: str | int = "2025",
    *,
    root: str | Path,
    ledger_path: str | Path | None = None,
    dry_run: bool = True,
    current_units: list[dict[str, Any]] | None = None,
) -> AddressApplyResult:
    """Project address-keyed verdicts onto bound graph nodes fail-closed.

    The address ledger records the content that a reviewer saw.  A verdict can
    reach a graph node only when the canonical address resolves to exactly one
    node, the current review projection has exactly one matching unit, and its
    content fingerprint is unchanged.  ``dry_run`` defaults to true so a caller
    must explicitly opt into graph writes.  Writes reuse ``_apply_graph_review``
    rather than maintaining a second flag applier.
    """
    from workbench.address_verdicts import load_address_verdicts, unit_address, unit_fingerprint
    from workbench.derived_reviews import build_derived_cell_units

    root_path = Path(root).resolve()
    tax_year = int(year)
    path = (
        Path(ledger_path).resolve()
        if ledger_path is not None
        else root_path / "review_verdicts" / str(tax_year) / "address_verdicts.jsonl"
    )
    records = load_address_verdicts(path)
    if not records:
        return AddressApplyResult((), (), (), (), (), (), (), dry_run)
    graph = load_graph(tax_year, root=root_path, include_extensions=False)
    artifacts = load_address_artifacts(tax_year, root_path)
    units = (
        list(current_units)
        if current_units is not None
        else build_derived_cell_units(root_path, tax_year)
    )
    units_by_address: dict[str, list[dict[str, Any]]] = {}
    for unit in units:
        address = unit_address(unit)
        if address:
            units_by_address.setdefault(address, []).append(unit)
    nodes_by_id = {
        str(node.get("node_id")): node
        for node in graph.items("nodes")
        if node.get("node_id")
    }
    node_paths = _node_artifact_paths(root_path, tax_year)
    applied: list[str] = []
    would_apply: list[str] = []
    stale: list[str] = []
    unresolved: list[str] = []
    ambiguous: list[str] = []
    unsupported: list[str] = []
    reports: list[dict[str, Any]] = []

    for record in records:
        verdict_id = str(record["verdict_id"])
        address_id = str(record["address"])
        report: dict[str, Any] = {
            "verdict_id": verdict_id,
            "address": address_id,
            "judgement": str(record.get("judgement") or ""),
            "status": "unresolved",
            "address_resolution": "missing",
            "address_matches": [],
            "node_binding_resolution": "missing",
            "node_ids": [],
            "node_artifact_path": None,
            "reviewed_fingerprint": str(record.get("content_fingerprint") or ""),
            "current_fingerprint": None,
            "field_changes": [],
        }
        reports.append(report)
        if int(record.get("tax_year", 0)) != tax_year:
            report["status"] = "tax_year_mismatch"
            unresolved.append(verdict_id)
            continue

        resolution = artifacts.resolve(address_id=address_id)
        report["address_resolution"] = resolution.state
        report["address_matches"] = [item.address_id for item in resolution.matches]
        if resolution.state != "exact":
            report["status"] = "address_" + resolution.state
            (ambiguous if resolution.state == "ambiguous" else unresolved).append(verdict_id)
            continue

        node_ids = sorted({
            str(binding.get("node_id"))
            for binding in artifacts.node_bindings
            if str(binding.get("address_id")) == address_id and binding.get("node_id")
        })
        report["node_ids"] = node_ids
        report["node_binding_resolution"] = (
            "missing" if not node_ids else "exact" if len(node_ids) == 1 else "ambiguous"
        )
        if len(node_ids) != 1:
            report["status"] = "node_binding_" + report["node_binding_resolution"]
            (ambiguous if len(node_ids) > 1 else unresolved).append(verdict_id)
            continue

        node_id = node_ids[0]
        node = nodes_by_id.get(node_id)
        artifact_path = node_paths.get(node_id)
        report["node_artifact_path"] = artifact_path
        if node is None or artifact_path is None:
            report["status"] = "node_missing"
            unresolved.append(verdict_id)
            continue

        matching_units = units_by_address.get(address_id, [])
        if len(matching_units) != 1:
            report["status"] = "current_content_" + ("missing" if not matching_units else "ambiguous")
            (ambiguous if len(matching_units) > 1 else unresolved).append(verdict_id)
            continue
        current_fingerprint = unit_fingerprint(matching_units[0])
        report["current_fingerprint"] = current_fingerprint
        if current_fingerprint != str(record["content_fingerprint"]):
            report["status"] = "stale"
            stale.append(verdict_id)
            continue

        judgement = _canonical_address_judgement(record.get("judgement"))
        if judgement not in _ADDRESS_JUDGEMENTS:
            report["status"] = "unsupported_judgement"
            report["supported_judgements"] = sorted(_ADDRESS_JUDGEMENTS)
            report["message"] = (
                "The address ledger and current review surface do not define a node flag mapping "
                f"for judgement {judgement!r}; no graph write was made."
            )
            unsupported.append(verdict_id)
            continue

        report["field_changes"] = _address_field_changes(node, record)
        if dry_run:
            report["status"] = "would_apply"
            would_apply.append(verdict_id)
        else:
            _apply_address_graph_review(
                root_path,
                artifact_path,
                node_id,
                _address_review_payload(record),
            )
            report["status"] = "applied"
            applied.append(verdict_id)

    return AddressApplyResult(
        tuple(applied),
        tuple(would_apply),
        tuple(stale),
        tuple(unresolved),
        tuple(ambiguous),
        tuple(unsupported),
        tuple(reports),
        dry_run,
    )


def _node_artifact_paths(root: Path, year: int) -> dict[str, str]:
    """Return unique node-id to graph-file paths for the shared applier."""
    paths: dict[str, set[str]] = {}
    for path in sorted((root / "graph" / str(year) / "nodes").glob("*.yaml")):
        payload = _load_yaml(path)
        objects = payload if isinstance(payload, list) else [payload]
        relative = path.relative_to(root).as_posix()
        for obj in objects:
            if isinstance(obj, dict) and obj.get("node_id"):
                paths.setdefault(str(obj["node_id"]), set()).add(relative)
    return {
        node_id: next(iter(candidates))
        for node_id, candidates in paths.items()
        if len(candidates) == 1
    }


def _address_review_payload(record: dict[str, Any]) -> dict[str, Any]:
    """Adapt an address-ledger record to the existing graph review payload."""
    judgement = _canonical_address_judgement(record.get("judgement"))
    node_fields = _node_review_fields(judgement)
    review: dict[str, Any] = {
        "reviewer_id": str(record["reviewer_id"]),
        "reviewed_at": str(record["reviewed_at"]),
        "human_minutes": 0.0,
        "verdict": judgement,
        "human_confirmed": node_fields["human_confirmed"],
        "verification_tier": node_fields["verification_tier"],
    }
    comment = str(record.get("comment") or "").strip()
    if comment:
        review["reason"] = comment
    return review


def _address_field_changes(node: dict[str, Any], record: dict[str, Any]) -> list[dict[str, Any]]:
    """Describe the three node fields the existing applier would write."""
    review = _address_review_payload(record)
    desired = {
        "human_confirmed": review["human_confirmed"],
        "verification_tier": review["verification_tier"],
        "human_review": {
            key: value
            for key, value in review.items()
            if key not in {"human_confirmed", "verification_tier"}
        },
    }
    return [
        {
            "field": field,
            "before": node.get(field),
            "after": value,
            "changed": node.get(field) != value,
        }
        for field, value in desired.items()
    ]


def _apply_address_graph_review(
    root: Path,
    artifact_path: str,
    node_id: str,
    review: dict[str, Any],
) -> None:
    """Invoke the existing bounded graph-review applier for one node."""
    entry = {
        "artifact_paths": [artifact_path],
        "expected_nodes": [node_id],
    }
    verdict = {
        "object_ref": {
            "artifact_path": artifact_path,
            "object_kind": "nodes",
            "object_id": node_id,
        },
    }
    _apply_graph_review(root, entry, verdict, review)


def apply_verdicts(
    year: str | int = "2025",
    *,
    root: str | Path,
    verdict_dir: str | Path | None = None,
    manifest_path: str | Path | None = None,
) -> ApplyResult:
    """Validate and apply all new verdict files for one tax year.

    This is the only pipeline command that can turn a human verdict into
    ``human_confirmed: true``. A worker-authored graph or queue artifact never
    receives that bit directly.
    """
    root_path = Path(root).resolve()
    tax_year = int(year)
    queue_path = root_path / "review_queue" / str(tax_year) / "deferred_review.yaml"
    queue = _load_yaml(queue_path)
    _validate_schema(queue, root_path / "schemas" / "deferred_review_queue.schema.json", queue_path)
    entries = {str(item["queue_id"]): item for item in queue.get("entries", [])}
    provenance_path = root_path / "review_provenance" / str(tax_year) / "applied.yaml"
    provenance = _load_yaml(provenance_path) if provenance_path.exists() else {"tax_year": tax_year, "entries": []}
    applied_by_id = {str(item.get("verdict_id")): item for item in provenance.get("entries", [])}
    verdict_root = Path(verdict_dir).resolve() if verdict_dir is not None else root_path / "review_verdicts" / str(tax_year)
    paths = sorted(verdict_root.glob("*.yaml")) if verdict_root.is_dir() else []
    new_paths: list[Path] = []
    for path in paths:
        verdict = _load_verdict(path, root_path)
        previous = applied_by_id.get(str(verdict["verdict_id"]))
        if previous is None:
            new_paths.append(path)
        elif previous.get("content_hash") != verdict["content_hash"]:
            raise ValueError(f"already-applied verdict was edited: {path}")
    paths = new_paths
    manifest = None
    if paths:
        saved_manifest = (
            Path(manifest_path).resolve()
            if manifest_path is not None
            else root_path / ".workbench_state" / str(tax_year) / "review_manifest.json"
        )
        manifest = _load_and_verify_manifest(saved_manifest, root_path, tax_year)

    applied: list[str] = []
    confirmed: list[str] = []
    defects: list[str] = []
    pathologies: list[str] = []
    questioned: list[str] = []
    rejected: list[str] = []
    for path in paths:
        verdict = _load_verdict(path, root_path)
        verdict_id = str(verdict["verdict_id"])
        queue_id = str(verdict["queue_id"])
        if int(verdict["tax_year"]) != tax_year:
            raise ValueError(f"verdict tax year mismatch: {path}")
        if verdict["manifest_hash"] != manifest["manifest_hash"]:
            raise ValueError(f"verdict references a stale review manifest: {path}")
        if queue_id not in entries:
            raise ValueError(f"verdict references unknown queue entry {queue_id}: {path}")
        entry = entries[queue_id]
        _validate_scoped_object_ref(entry, verdict, path)
        if entry.get("verdict_id") and entry.get("verdict_hash") != verdict["content_hash"]:
            raise ValueError(f"queue/verdict hash mismatch for {queue_id}")
        kind = str(verdict["verdict"])
        review = {
            "reviewer_id": str(verdict["reviewer_id"]),
            "reviewed_at": str(verdict["reviewed_at"]),
            "human_minutes": float(verdict["human_minutes"]),
            "verdict": kind,
        }
        review_note = str(verdict.get("reason") or verdict.get("comment") or "").strip()
        if review_note:
            review["reason"] = review_note
        entry.update(
            {
                "verdict_id": verdict_id,
                "verdict": kind,
                "verdict_reason": review_note,
                "reviewer_id": review["reviewer_id"],
                "reviewed_at": review["reviewed_at"],
                "human_minutes": review["human_minutes"],
                "verdict_hash": verdict["content_hash"],
            }
        )
        if kind == "confirmed":
            _apply_graph_review(root_path, entry, verdict, review)
            entry.update({"status": "confirmed", "review_status": "confirmed", "human_confirmed": True, "verification_tier": "human-confirmed"})
            confirmed.append(queue_id)
        elif kind == "questioned":
            review.update(_node_review_fields(kind))
            _apply_graph_review(root_path, entry, verdict, review)
            entry.update({"status": "questioned", "review_status": "questioned", "human_confirmed": False, "verification_tier": "human-questioned"})
            questioned.append(queue_id)
        elif kind == "rejected":
            review.update(_node_review_fields(kind))
            _apply_graph_review(root_path, entry, verdict, review)
            entry.update({"status": "rejected", "review_status": "rejected", "human_confirmed": False, "verification_tier": "human-rejected"})
            rejected.append(queue_id)
        elif kind == "pipeline_defect":
            entry.update({"status": "pending_reextract", "review_status": "pending_reextract", "human_confirmed": False})
            defects.append(queue_id)
        else:
            entry.update({"status": "source_pathology", "review_status": "source_pathology", "human_confirmed": False, "source_override": dict(verdict["source_override"])})
            pathologies.append(queue_id)
        applied.append(verdict_id)
        record = dict(verdict)
        record["queue_id"] = queue_id
        provenance.setdefault("entries", []).append(record)
        applied_by_id[verdict_id] = record

    if applied:
        queue["entries"] = sorted(entries.values(), key=lambda item: str(item.get("queue_id", "")))
        _write_yaml(queue_path, queue)
        provenance["entries"] = sorted(provenance.get("entries", []), key=lambda item: str(item.get("verdict_id", "")))
        _write_yaml(provenance_path, provenance)
    return ApplyResult(
        tuple(applied), tuple(confirmed), tuple(defects), tuple(pathologies),
        queue_path, provenance_path,
        questioned=tuple(questioned), rejected=tuple(rejected),
    )


def _load_verdict(path: Path, root: Path) -> dict[str, Any]:
    payload = _load_yaml(path)
    if not isinstance(payload, dict):
        raise ValueError(f"verdict must be a mapping: {path}")
    _validate_schema(payload, root / "schemas" / "review_verdict.schema.json", path)
    if path.stem != str(payload.get("verdict_id")):
        raise ValueError(f"verdict filename does not match verdict_id: {path}")
    if _content_hash(payload) != payload.get("content_hash"):
        raise ValueError(f"verdict content hash mismatch: {path}")
    reviewer = str(payload.get("reviewer_id") or "").lower()
    if reviewer in {"agent", "codex", "worker", "system"}:
        raise ValueError("reviewer_id must identify the human reviewer")
    return payload


def _load_and_verify_manifest(path: Path, root: Path, tax_year: int) -> dict[str, Any]:
    """Load the reviewed projection and verify every pinned source artifact."""
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read saved review manifest {path}: {exc}") from exc
    _validate_schema(manifest, root / "schemas" / "review_manifest.schema.json", path)
    if int(manifest.get("tax_year", 0)) != tax_year:
        raise ValueError(f"review manifest tax year mismatch: {path}")
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    canonical = json.dumps(unsigned, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    actual_manifest_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if actual_manifest_hash != manifest.get("manifest_hash"):
        raise ValueError(f"review manifest content hash mismatch: {path}")
    for artifact in manifest.get("source_artifacts", []) or []:
        source = _safe_root_path(root, str(artifact.get("path", "")))
        if source is None or not source.is_file():
            raise ValueError(f"review manifest source artifact is missing or unsafe: {artifact.get('path')}")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest != artifact.get("content_hash"):
            raise ValueError(f"review manifest source artifact changed: {artifact.get('path')}")
    return manifest


def _validate_scoped_object_ref(entry: dict[str, Any], verdict: dict[str, Any], path: Path) -> None:
    """Refuse a verdict target outside its queue entry's declared review scope."""
    object_ref = verdict.get("object_ref")
    if not isinstance(object_ref, dict):
        return
    target_id = str(object_ref.get("object_id") or "")
    target_path = str(object_ref.get("artifact_path") or "").replace("\\", "/")
    target_kind = str(object_ref.get("object_kind") or "")
    matches = []
    for ref in entry.get("review_scope", {}).get("object_refs", []) or []:
        if not isinstance(ref, dict) or str(ref.get("object_id") or "") != target_id:
            continue
        source_path = str(ref.get("source_path") or "").replace("\\", "/")
        if target_path and source_path != target_path:
            continue
        expected_kind = Path(source_path).parent.name if source_path else f"{ref.get('object_type', '')}s"
        if target_kind and target_kind != expected_kind:
            continue
        matches.append(ref)
    if len(matches) != 1:
        raise ValueError(f"verdict object_ref is outside the queue review scope: {path}")


def _apply_graph_review(root: Path, entry: dict[str, Any], verdict: dict[str, Any], review: dict[str, Any]) -> None:
    object_ref = verdict.get("object_ref") if isinstance(verdict.get("object_ref"), dict) else {}
    explicit_path = object_ref.get("artifact_path")
    candidates = [explicit_path] if explicit_path else entry.get("artifact_paths", [])
    expected_nodes = {str(value) for value in entry.get("expected_nodes", [])}
    changed_paths: set[Path] = set()
    for relative in candidates:
        path = _safe_root_path(root, str(relative))
        if path is None or not path.is_file() or "_drafts" in path.parts:
            continue
        kind = str(object_ref.get("object_kind") or path.parent.name)
        if kind not in _REVIEWABLE_KINDS:
            continue
        payload = _load_yaml(path)
        was_list = isinstance(payload, list)
        objects = payload if was_list else [payload]
        id_field = _ID_FIELDS[kind]
        target_id = str(object_ref.get("object_id") or "")
        bounded = bool(target_id) or (kind == "nodes" and bool(expected_nodes))
        matches: list[dict[str, Any]] = []
        for obj in objects:
            if not isinstance(obj, dict):
                continue
            if target_id and str(obj.get(id_field)) != target_id:
                continue
            if not target_id and kind == "nodes" and expected_nodes and str(obj.get(id_field)) not in expected_nodes:
                continue
            matches.append(obj)
        # Fail closed: one human verdict may not silently confirm a whole
        # multi-object file. Human confirmation must be BOUNDED to the object
        # the reviewer actually looked at - a specific object_ref.object_id or
        # (for nodes) the queue entry's expected_nodes set. Otherwise a single
        # click would inflate an entire file's tier to human-confirmed.
        if len(matches) > 1 and not bounded:
            raise ValueError(
                f"refusing to human-confirm {len(matches)} objects in {path} from one "
                f"verdict without object_ref.object_id or the queue entry's expected_nodes"
            )
        for obj in matches:
            human_confirmed = bool(review.get("human_confirmed", True))
            verification_tier = str(
                review.get("verification_tier")
                or ("human-confirmed" if human_confirmed else "human-reviewed")
            )
            obj["human_confirmed"] = human_confirmed
            obj["verification_tier"] = verification_tier
            obj["human_review"] = {
                key: value
                for key, value in review.items()
                if key not in {"human_confirmed", "verification_tier"}
            }
        if matches:
            _write_yaml(path, objects if was_list else objects[0])
            changed_paths.add(path)
    # The sidecar is the durable audit link for field maps, citations, edges,
    # extension drafts, and any other review object that is not schema-shaped as
    # a node/document/decision.
    del changed_paths


def _safe_root_path(root: Path, relative: str) -> Path | None:
    candidate = Path(relative)
    if candidate.is_absolute():
        return None
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return None
    return resolved


def _validate_schema(payload: Any, schema_path: Path, source: Path) -> None:
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.validate(payload, schema, format_checker=jsonschema.FormatChecker())
    except (OSError, json.JSONDecodeError, jsonschema.SchemaError) as exc:
        raise ValueError(f"cannot load schema for {source}: {exc}") from exc
    except jsonschema.ValidationError as exc:
        raise ValueError(f"invalid artifact {source}: {exc.message}") from exc


def _content_hash(payload: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "content_hash"}
    canonical = json.dumps(unsigned, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot read YAML artifact {path}: {exc}") from exc


def _write_yaml(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=False)
    text.encode("ascii")
    path.write_text(text, encoding="utf-8", newline="\n")
