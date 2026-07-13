"""Apply human review verdict artifacts to the pipeline-owned graph."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema
import yaml


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


@dataclass(frozen=True)
class ApplyResult:
    """Summary of one verdict-application run."""

    applied: tuple[str, ...]
    confirmed: tuple[str, ...]
    pipeline_defects: tuple[str, ...]
    source_pathologies: tuple[str, ...]
    queue_path: Path
    provenance_path: Path


def apply_verdicts(
    year: str | int = "2025",
    *,
    root: str | Path,
    verdict_dir: str | Path | None = None,
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

    applied: list[str] = []
    confirmed: list[str] = []
    defects: list[str] = []
    pathologies: list[str] = []
    for path in paths:
        verdict = _load_verdict(path, root_path)
        verdict_id = str(verdict["verdict_id"])
        queue_id = str(verdict["queue_id"])
        if int(verdict["tax_year"]) != tax_year:
            raise ValueError(f"verdict tax year mismatch: {path}")
        if queue_id not in entries:
            raise ValueError(f"verdict references unknown queue entry {queue_id}: {path}")
        if verdict_id in applied_by_id:
            previous = applied_by_id[verdict_id]
            if previous.get("content_hash") != verdict["content_hash"]:
                raise ValueError(f"already-applied verdict was edited: {path}")
            continue
        entry = entries[queue_id]
        if entry.get("verdict_id") and entry.get("verdict_hash") != verdict["content_hash"]:
            raise ValueError(f"queue/verdict hash mismatch for {queue_id}")
        kind = str(verdict["verdict"])
        review = {
            "reviewer_id": str(verdict["reviewer_id"]),
            "reviewed_at": str(verdict["reviewed_at"]),
            "human_minutes": float(verdict["human_minutes"]),
            "verdict": kind,
        }
        if verdict.get("reason"):
            review["reason"] = str(verdict["reason"])
        entry.update(
            {
                "verdict_id": verdict_id,
                "verdict": kind,
                "verdict_reason": str(verdict.get("reason") or ""),
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
    return ApplyResult(tuple(applied), tuple(confirmed), tuple(defects), tuple(pathologies), queue_path, provenance_path)


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
            obj["human_confirmed"] = True
            obj["verification_tier"] = "human-confirmed"
            obj["human_review"] = dict(review)
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
