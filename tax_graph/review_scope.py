"""Deterministic migration of deferred-review entries to scoped objects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import yaml


_ID_TYPES = {
    "document_id": "document",
    "node_id": "node",
    "table_id": "table",
    "edge_id": "edge",
    "rule_id": "rule",
    "citation_id": "citation",
    "decision_id": "decision",
    "routing_id": "routing_edge",
    "trigger_id": "trigger",
    "expectation_id": "expectation",
    "frontier_id": "frontier",
    "field_id": "field",
    "example_id": "example",
    "option_id": "decision_option",
}


@dataclass(frozen=True)
class ReviewScopeMigration:
    """Summary of one deterministic queue migration."""

    queue_path: Path
    changed_entries: tuple[str, ...]
    skipped_entries: tuple[str, ...]


def migrate_review_scope(
    *,
    root: str | Path,
    year: str | int = "2025",
    queue_path: str | Path | None = None,
    output_path: str | Path | None = None,
    refresh: bool = False,
) -> ReviewScopeMigration:
    """Backfill explicit object refs for pending queue entries.

    Existing scopes are preserved byte-for-byte at the object level, while
    unscoped entries are derived only from their cited artifact objects and
    existing queue ids. An entry that cannot resolve to an object fails closed;
    this function never invents a document-wide scope.
    """
    root_path = Path(root).resolve()
    tax_year = int(year)
    source_path = (
        Path(queue_path).resolve()
        if queue_path is not None
        else root_path / "review_queue" / str(tax_year) / "deferred_review.yaml"
    )
    target_path = Path(output_path).resolve() if output_path is not None else source_path
    payload = _load_yaml(source_path)
    if not isinstance(payload, dict) or not isinstance(payload.get("entries"), list):
        raise ValueError(f"invalid deferred review queue: {source_path}")
    if int(payload.get("tax_year", tax_year)) != tax_year:
        raise ValueError(f"queue tax year does not match requested year: {source_path}")

    changed: list[str] = []
    skipped: list[str] = []
    migrated_entries: list[dict[str, Any]] = []
    for raw_entry in payload["entries"]:
        if not isinstance(raw_entry, dict):
            raise ValueError(f"queue entry is not a mapping: {source_path}")
        entry = dict(raw_entry)
        queue_id = str(entry.get("queue_id", ""))
        if not _is_pending(entry):
            skipped.append(queue_id)
        elif entry.get("review_scope") is not None and not refresh:
            _validate_scope(entry["review_scope"], queue_id)
            skipped.append(queue_id)
        else:
            scope = _derive_scope(entry, root_path=root_path, year=tax_year)
            if not scope["object_refs"]:
                raise ValueError(
                    f"cannot derive object scope for pending queue entry {queue_id}; "
                    "document-wide scope is forbidden"
                )
            entry["review_scope"] = scope
            changed.append(queue_id)
        migrated_entries.append(entry)

    migrated = {"tax_year": tax_year, "entries": migrated_entries}
    _write_yaml(target_path, migrated)
    return ReviewScopeMigration(
        queue_path=target_path,
        changed_entries=tuple(changed),
        skipped_entries=tuple(skipped),
    )


def _derive_scope(entry: dict[str, Any], *, root_path: Path, year: int) -> dict[str, Any]:
    queue_id = str(entry.get("queue_id", ""))
    kind = str(entry.get("kind", ""))
    refs: dict[tuple[str, str, str, str], dict[str, str]] = {}

    for node_id in entry.get("expected_nodes", []) or []:
        node_id = str(node_id)
        _add_ref(
            refs,
            object_type="node_instance" if "#" in node_id else "node",
            object_id=node_id,
            source_path=str(entry.get("artifact_dir") or "expected_nodes"),
            role="primary",
        )

    changed_ids = [str(value) for value in entry.get("changed_object_ids", []) or []]
    changed_kinds = [str(value) for value in entry.get("changed_kinds", []) or []]
    for index, object_id in enumerate(changed_ids):
        object_type = _object_type_from_kind(changed_kinds[index] if index < len(changed_kinds) else kind)
        _add_ref(
            refs,
            object_type=object_type,
            object_id=object_id,
            source_path=_first_artifact_path(entry),
            role="primary",
        )

    artifact_paths = [str(path) for path in entry.get("artifact_paths", []) or []]
    review_refs_found = _collect_review_markdown_refs(refs, entry, root_path=root_path)
    if kind == "field_map_review":
        _collect_field_map_refs(refs, entry, root_path=root_path)
    elif kind == "frontier_review":
        _collect_frontier_refs(refs, entry, root_path=root_path)
    elif kind == "decision_review":
        _collect_decision_refs(refs, entry, root_path=root_path)
    elif kind == "authored_worksheet_review" or (
        kind == "promotion_review" and "qdcgt" in queue_id.lower()
    ):
        _collect_worksheet_refs(refs, entry, root_path=root_path)
    elif kind.startswith("intake_"):
        _collect_intake_refs(refs, entry, root_path=root_path)
    else:
        if kind == "extension_promotion" and not review_refs_found:
            _collect_extension_refs(refs, entry, root_path=root_path)
        elif not review_refs_found and not changed_ids and not refs:
            raise ValueError(
                f"cannot derive targeted object scope for pending queue entry {queue_id}; "
                "document-wide scope is forbidden"
            )

    scope_type = _scope_type(kind)
    object_refs = sorted(refs.values(), key=lambda ref: (ref["object_type"], ref["object_id"], ref["source_path"], ref.get("role", "")))
    return {"scope_version": 1, "scope_type": scope_type, "object_refs": object_refs}


def _collect_field_map_refs(
    refs: dict[tuple[str, str, str, str], dict[str, str]],
    entry: dict[str, Any],
    *,
    root_path: Path,
) -> None:
    found = False
    has_primary = False
    for relative_path in entry.get("artifact_paths", []) or []:
        path = root_path / str(relative_path)
        if path.suffix.lower() not in {".yaml", ".yml"}:
            continue
        data = _load_yaml(path)
        if not isinstance(data, dict):
            continue
        for mapping in data.get("mappings", []) or []:
            if not isinstance(mapping, dict):
                continue
            if mapping.get("node_id"):
                _add_ref(refs, "node", str(mapping["node_id"]), str(relative_path), "primary")
                found = True
                has_primary = True
            elif mapping.get("identity_slot"):
                _add_ref(refs, "field", str(mapping["identity_slot"]), str(relative_path), "primary")
                found = True
                has_primary = True
        for disposition in data.get("field_dispositions", []) or []:
            if not isinstance(disposition, dict) or not disposition.get("field_name"):
                continue
            _add_ref(
                refs,
                "field_control",
                str(disposition["field_name"]),
                str(relative_path),
                "primary",
            )
            found = True
            has_primary = True
        for item in data.get("excluded_nodes", []) or []:
            if isinstance(item, dict) and item.get("node_id"):
                _add_ref(refs, "node", str(item["node_id"]), str(relative_path), "excluded")
                found = True
        for item in data.get("frontier_fields", []) or []:
            if isinstance(item, dict) and item.get("frontier_id"):
                _add_ref(refs, "frontier_field", str(item["frontier_id"]), str(relative_path), "frontier")
                found = True
        if not has_primary:
            inventory_path = next(
                (
                    str(candidate)
                    for candidate in entry.get("artifact_paths", []) or []
                    if "/field_inventories/" in str(candidate).replace("\\", "/")
                ),
                str(relative_path),
            )
            document_id = str(data.get("document_id") or entry.get("document_id") or "")
            if document_id:
                _add_ref(refs, "field_inventory", document_id, inventory_path, "primary")


def _collect_frontier_refs(
    refs: dict[tuple[str, str, str, str], dict[str, str]],
    entry: dict[str, Any],
    *,
    root_path: Path,
) -> None:
    summary = str(entry.get("summary", "")).lower()
    document_id = str(entry.get("document_id", ""))
    for relative_path in entry.get("artifact_paths", []) or []:
        path = root_path / str(relative_path)
        if path.name != "frontier-declarations.yaml":
            continue
        data = _load_yaml(path)
        records = data if isinstance(data, list) else data.get("frontiers", []) if isinstance(data, dict) else []
        for item in records:
            if not isinstance(item, dict) or item.get("document_id") != document_id:
                continue
            searchable = " ".join(str(item.get(key, "")) for key in ("frontier_id", "title", "purpose", "line")).lower()
            if "student loan" in summary and "student loan" not in searchable:
                continue
            for key, object_type in (("frontier_id", "frontier"), ("node_id", "node")):
                if item.get(key):
                    role = "primary" if object_type == "frontier" else "frontier"
                    _add_ref(refs, object_type, str(item[key]), str(relative_path), role)


def _collect_extension_refs(
    refs: dict[tuple[str, str, str, str], dict[str, str]],
    entry: dict[str, Any],
    *,
    root_path: Path,
) -> None:
    artifact_dir = entry.get("artifact_dir")
    if not artifact_dir:
        return
    directory = root_path / str(artifact_dir)
    if not directory.is_dir():
        return
    raise ValueError(
        f"extension review {entry.get('queue_id', '')} has no explicit review.md object list"
    )


def _collect_decision_refs(
    refs: dict[tuple[str, str, str, str], dict[str, str]],
    entry: dict[str, Any],
    *,
    root_path: Path,
) -> None:
    """Collect one decision and its declared options, node, and citations."""
    queue_id = str(entry.get("queue_id", ""))
    if queue_id.startswith("routing_review_"):
        _collect_routing_decision_refs(refs, entry, root_path=root_path)
        return

    found = False
    for relative_path in entry.get("artifact_paths", []) or []:
        path = root_path / str(relative_path)
        if path.suffix.lower() not in {".yaml", ".yml"} or path.parent.name != "decisions":
            continue
        data = _load_yaml(path)
        records = data if isinstance(data, list) else data.get("decisions", []) if isinstance(data, dict) else []
        for item in records:
            if not isinstance(item, dict) or not item.get("decision_id"):
                continue
            source_path = path.relative_to(root_path).as_posix()
            _add_ref(refs, "decision", str(item["decision_id"]), source_path, "primary")
            found = True
            if item.get("sets_node"):
                _add_ref(refs, "node", str(item["sets_node"]), source_path, "primary")
            for citation_id in item.get("citation_refs", []) or []:
                _add_ref(refs, "citation", str(citation_id), source_path, "primary")
            for option in item.get("options", []) or []:
                if not isinstance(option, dict) or not option.get("option_id"):
                    continue
                _add_ref(refs, "decision_option", str(option["option_id"]), source_path, "primary")
                for citation_id in option.get("citation_refs", []) or []:
                    _add_ref(refs, "citation", str(citation_id), source_path, "primary")
    if not found:
        raise ValueError(f"decision review {queue_id} has no decision object")


def _collect_routing_decision_refs(
    refs: dict[tuple[str, str, str, str], dict[str, str]],
    entry: dict[str, Any],
    *,
    root_path: Path,
) -> None:
    """Collect the named Schedule D line-20 routing gate and its edges."""
    queue_id = str(entry.get("queue_id", ""))
    match = re.search(r"schedule_d_(\d{4})_line_(\d+)_", queue_id)
    if not match:
        raise ValueError(f"routing decision review {queue_id} has no named gate")
    gate_id = f"schedule_d_{match.group(1)}_line_{match.group(2)}_gate"
    found_gate = False
    for relative_path in entry.get("artifact_paths", []) or []:
        path = root_path / str(relative_path)
        if path.suffix.lower() not in {".yaml", ".yml"}:
            continue
        data = _load_yaml(path)
        records = data if isinstance(data, list) else data.get("nodes", data.get("edges", [])) if isinstance(data, dict) else []
        for item in records:
            if not isinstance(item, dict):
                continue
            source_path = path.relative_to(root_path).as_posix()
            if path.parent.name == "nodes" and item.get("node_id") == gate_id:
                _add_ref(refs, "node", gate_id, source_path, "primary")
                found_gate = True
            if path.parent.name == "edges" and (
                item.get("source") == gate_id or item.get("target") == gate_id
            ):
                _add_ref(refs, "edge", str(item.get("edge_id", "")), source_path, "primary")
    if not found_gate:
        raise ValueError(f"routing decision review {queue_id} has no target node {gate_id}")


def _collect_worksheet_refs(
    refs: dict[tuple[str, str, str, str], dict[str, str]],
    entry: dict[str, Any],
    *,
    root_path: Path,
) -> None:
    """Collect a worksheet's own line nodes and rules used by those nodes."""
    summary = f"{entry.get('queue_id', '')} {entry.get('summary', '')}".lower()
    if "qdcgt" in summary:
        node_pattern = re.compile(r"^form_[^_]+_\d{4}_qdcgt_line_\d+(?:_|$)")
    else:
        node_pattern = re.compile(r"^schedule_d_\d{4}_tax_worksheet_line_\d+(?:_|$)")
    selected_nodes: set[str] = set()
    for relative_path in entry.get("artifact_paths", []) or []:
        path = root_path / str(relative_path)
        if path.parent.name != "nodes" or path.suffix.lower() not in {".yaml", ".yml"}:
            continue
        data = _load_yaml(path)
        records = data if isinstance(data, list) else data.get("nodes", []) if isinstance(data, dict) else []
        source_path = path.relative_to(root_path).as_posix()
        for item in records:
            if isinstance(item, dict) and node_pattern.match(str(item.get("node_id", ""))):
                node_id = str(item["node_id"])
                selected_nodes.add(node_id)
                _add_ref(refs, "node", node_id, source_path, "primary")
    if not selected_nodes:
        raise ValueError(f"worksheet review {entry.get('queue_id', '')} has no line nodes")

    rule_ids: set[str] = set()
    for relative_path in entry.get("artifact_paths", []) or []:
        path = root_path / str(relative_path)
        if path.parent.name != "edges" or path.suffix.lower() not in {".yaml", ".yml"}:
            continue
        data = _load_yaml(path)
        records = data if isinstance(data, list) else data.get("edges", []) if isinstance(data, dict) else []
        for item in records:
            if not isinstance(item, dict) or not (
                item.get("source") in selected_nodes or item.get("target") in selected_nodes
            ):
                continue
            if item.get("rule_id"):
                rule_ids.add(str(item["rule_id"]))
    rule_source_path = next(
        (
            str(path)
            for path in entry.get("artifact_paths", []) or []
            if "/rules/" in str(path).replace("\\", "/")
        ),
        "graph/2025/rules/core.yaml",
    )
    for rule_id in sorted(rule_ids):
        _add_ref(refs, "rule", rule_id, rule_source_path, "primary")


def _collect_intake_refs(
    refs: dict[tuple[str, str, str, str], dict[str, str]],
    entry: dict[str, Any],
    *,
    root_path: Path,
) -> None:
    """Collect only the concrete intake records named by the review kind."""
    kind = str(entry.get("kind", ""))
    directory_type = {
        "intake_expectation_review": ("expectations", "expectation_id", "expectation"),
        "intake_routing_review": ("routing_edges", "routing_id", "routing_edge"),
        "intake_trigger_review": ("triggers", "trigger_id", "trigger"),
    }.get(kind)
    if directory_type is None:
        raise ValueError(f"unknown intake review kind {kind}")
    directory, id_key, object_type = directory_type
    found = False
    for relative_path in entry.get("artifact_paths", []) or []:
        path = root_path / str(relative_path)
        if path.parent.name != directory or path.suffix.lower() not in {".yaml", ".yml"}:
            continue
        data = _load_yaml(path)
        records = data if isinstance(data, list) else data.get(directory, []) if isinstance(data, dict) else []
        source_path = path.relative_to(root_path).as_posix()
        for item in records:
            if isinstance(item, dict) and item.get(id_key):
                _add_ref(refs, object_type, str(item[id_key]), source_path, "primary")
                found = True
    if not found:
        raise ValueError(f"intake review {entry.get('queue_id', '')} has no concrete objects")


def _collect_review_markdown_refs(
    refs: dict[tuple[str, str, str, str], dict[str, str]],
    entry: dict[str, Any],
    *,
    root_path: Path,
) -> bool:
    """Read explicit ``kind/object_id`` bullets from an extraction review."""
    candidates: list[Path] = []
    artifact_dir = entry.get("artifact_dir")
    if artifact_dir:
        candidates.append(root_path / str(artifact_dir) / "review.md")
    for relative_path in entry.get("artifact_paths", []) or []:
        path = root_path / str(relative_path)
        if path.name == "review.md":
            candidates.append(path)

    found = False
    pattern = re.compile(r"^\s*-\s+(documents|nodes|tables|edges|rules|citations|decisions|routing_edges|triggers|expectations)/([^\s]+)")
    directory_types = {
        "documents": "document",
        "nodes": "node",
        "tables": "table",
        "edges": "edge",
        "rules": "rule",
        "citations": "citation",
        "decisions": "decision",
        "routing_edges": "routing_edge",
        "triggers": "trigger",
        "expectations": "expectation",
    }
    seen: set[Path] = set()
    for path in candidates:
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        for line in path.read_text(encoding="utf-8").splitlines():
            match = pattern.match(line)
            if not match:
                continue
            directory, object_id = match.groups()
            _add_ref(
                refs,
                directory_types[directory],
                object_id,
                path.relative_to(root_path).as_posix(),
                "primary",
            )
            found = True
    return found


def _add_ref(
    refs: dict[tuple[str, str, str, str], dict[str, str]],
    object_type: str,
    object_id: str,
    source_path: str,
    role: str,
) -> None:
    object_id = str(object_id).strip()
    if not object_id:
        return
    key = (object_type, object_id, source_path, role)
    refs[key] = {
        "object_type": object_type,
        "object_id": object_id,
        "source_path": source_path,
        "role": role,
    }


def _object_type_from_kind(kind: str) -> str:
    normalized = kind.strip().lower()
    return {
        "outbound_flow": "flow",
        "flow": "flow",
        "node": "node",
        "nodes": "node",
        "edge": "edge",
        "edges": "edge",
        "decision": "decision",
        "decisions": "decision",
    }.get(normalized, normalized.rstrip("s") or "object")


def _scope_type(kind: str) -> str:
    if kind == "field_map_review":
        return "field_map"
    if kind in {"promotion_review", "authored_worksheet_review"}:
        return "promotion"
    if kind == "decision_review":
        return "decision"
    if kind == "frontier_review":
        return "frontier"
    if kind.startswith("intake_"):
        return "intake"
    if kind == "irs_example_review":
        return "example"
    if kind == "extension_promotion":
        return "extension"
    return "object"


def _first_artifact_path(entry: dict[str, Any]) -> str:
    paths = entry.get("artifact_paths") or []
    return str(paths[0]) if paths else str(entry.get("artifact_dir") or "queue")


def _is_pending(entry: dict[str, Any]) -> bool:
    return str(entry.get("status", "")) == "pending" or str(entry.get("review_status", "")) == "pending"


def _validate_scope(scope: Any, queue_id: str) -> None:
    if not isinstance(scope, dict) or scope.get("scope_version") != 1 or not scope.get("object_refs"):
        raise ValueError(f"invalid or empty review_scope for queue entry {queue_id}")


def _load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot read review artifact {path}: {exc}") from exc


def _load_json(path: Path) -> Any:
    import json

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read review artifact {path}: {exc}") from exc


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
        newline="\n",
    )
