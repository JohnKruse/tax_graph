"""Shared YAML loading utilities for authored graph data.

The loader keeps graph objects as ordered lists so validation can catch
duplicate ids before any later dictionary indexing would collapse them.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


GRAPH_KINDS: dict[str, tuple[str, bool, str]] = {
    "documents": ("document", False, "document_id"),
    "nodes": ("node", True, "node_id"),
    "tables": ("table", True, "table_id"),
    "edges": ("edge", True, "edge_id"),
    "rules": ("rule", True, "rule_id"),
    "citations": ("citation", True, "citation_id"),
    "decisions": ("decision", True, "decision_id"),
    # Intake is a relevance layer in the same graph.  These are additive
    # object kinds and deliberately do not participate in engine traversal.
    "routing_edges": ("routing_edge", True, "routing_id"),
    "triggers": ("trigger", True, "trigger_id"),
    "expectations": ("expectation", True, "expectation_id"),
}


@dataclass(frozen=True)
class LoadedGraph:
    """Authored graph objects for a single tax year."""

    year: str
    root: Path
    graph_dir: Path
    objects: dict[str, list[dict[str, Any]]]
    base_content_hash: str = ""
    extension_hashes: dict[str, str] | None = None
    extension_metadata: dict[str, dict[str, Any]] | None = None

    def items(self, kind: str) -> list[dict[str, Any]]:
        """Return objects for a graph kind such as ``nodes`` or ``edges``."""
        return self.objects.get(kind, [])

    def counts(self) -> dict[str, int]:
        """Return object counts by graph kind."""
        return {kind: len(items) for kind, items in self.objects.items()}


def normalize_yaml_value(value: Any) -> Any:
    """Normalize YAML parser output into schema-friendly Python values."""
    if isinstance(value, dict):
        return {key: normalize_yaml_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_yaml_value(item) for item in value]
    if isinstance(value, (_dt.date, _dt.datetime)):
        return value.isoformat()
    return value


def load_yaml(path: str | Path) -> Any:
    """Load a YAML file and normalize values used by JSON Schema validation."""
    yaml_path = Path(path)
    return normalize_yaml_value(yaml.safe_load(yaml_path.read_text(encoding="utf-8")))


def load_kind(graph_dir: Path, subdir: str, is_list: bool) -> list[dict[str, Any]]:
    """Load all YAML objects for one graph subdirectory."""
    objects: list[dict[str, Any]] = []
    for yaml_file in sorted((graph_dir / subdir).glob("*.yaml")):
        data = load_yaml(yaml_file)
        if data is None:
            continue
        if is_list:
            objects.extend(data)
        else:
            objects.append(data)
    return objects


def load_graph(
    year: str | int = "2025",
    root: str | Path | None = None,
    *,
    include_extensions: bool = True,
    extension_root: str | Path | None = None,
) -> LoadedGraph:
    """Load authored graph YAML and an optional local extension overlay.

    The shipped graph is loaded first and receives ``gate: project`` in the
    in-memory representation. Accepted extension objects live below
    ``graph_ext/<year>/<document_id>`` and must explicitly carry
    ``gate: user``. Object identity collisions with the shipped graph or with
    another extension are hard errors; draft directories are never loaded.
    """
    graph_year = str(year)
    project_root = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[2]
    graph_dir = project_root / "graph" / graph_year
    if not graph_dir.is_dir():
        raise FileNotFoundError(f"no graph dir for {graph_year}")

    objects = {
        subdir: [_with_gate(obj, "project") for obj in load_kind(graph_dir, subdir, is_list)]
        for subdir, (_, is_list, _) in GRAPH_KINDS.items()
    }
    base_hash = graph_content_hash(graph_dir)
    extension_hashes: dict[str, str] = {}
    extension_metadata: dict[str, dict[str, Any]] = {}
    if include_extensions:
        overlay = _extension_root(project_root, extension_root)
        extension_objects, extension_hashes, extension_metadata = load_extension_objects(
            graph_year,
            project_root,
            overlay,
            objects,
        )
        for kind, items in extension_objects.items():
            objects[kind].extend(items)
    return LoadedGraph(
        year=graph_year,
        root=project_root,
        graph_dir=graph_dir,
        objects=objects,
        base_content_hash=base_hash,
        extension_hashes=extension_hashes,
        extension_metadata=extension_metadata,
    )


def graph_content_hash(graph_dir: str | Path) -> str:
    """Return a deterministic hash for the shipped graph directory.

    Drafts and Python cache files are excluded. The relative path is included
    so a moved or replaced authored object cannot silently reuse a hash.
    """
    return _hash_files(Path(graph_dir), exclude_names={"_drafts", "__pycache__"})


def extension_content_hash(extension_dir: str | Path) -> str:
    """Return the hash of accepted graph YAML in one extension directory."""
    path = Path(extension_dir)
    files = []
    for kind in GRAPH_KINDS:
        candidate = path / f"{kind}.yaml"
        if candidate.exists():
            files.append(candidate)
    return _hash_files(path, explicit_files=files)


def load_extension_objects(
    year: str | int,
    root: str | Path,
    extension_root: str | Path,
    base_objects: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, str], dict[str, dict[str, Any]]]:
    """Load accepted extension documents and enforce the overlay contract."""
    del root  # Kept in the signature to make the provenance boundary explicit.
    year_dir = Path(extension_root) / str(year)
    extension_objects = {kind: [] for kind in GRAPH_KINDS}
    extension_hashes: dict[str, str] = {}
    extension_metadata: dict[str, dict[str, Any]] = {}
    if not year_dir.is_dir():
        return extension_objects, extension_hashes, extension_metadata

    shipped_ids = {
        (kind, str(obj.get(id_field)))
        for kind, (_, _, id_field) in GRAPH_KINDS.items()
        for obj in base_objects[kind]
        if obj.get(id_field)
    }
    seen_ids: set[tuple[str, str]] = set()
    for document_dir in sorted(path for path in year_dir.iterdir() if path.is_dir() and path.name != "_drafts"):
        document_id = document_dir.name
        graph_files = [document_dir / f"{kind}.yaml" for kind in GRAPH_KINDS if (document_dir / f"{kind}.yaml").exists()]
        if not graph_files:
            continue
        actual_hash = extension_content_hash(document_dir)
        metadata_path = document_dir / "extension.json"
        if not metadata_path.exists():
            raise ValueError(f"extension metadata is missing: {metadata_path}")
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"extension metadata must be an object: {metadata_path}")
        metadata: dict[str, Any] = dict(payload)
        stamped_hash = str(metadata.get("content_hash") or "")
        if stamped_hash != actual_hash:
            raise ValueError(
                f"extension content hash mismatch for {document_id}: "
                f"stamped {stamped_hash or '<missing>'}, actual {actual_hash}"
            )
        if str(metadata.get("document_id") or document_id) != document_id:
            raise ValueError(f"extension metadata document_id mismatch: {metadata_path}")
        if metadata.get("gate") not in {None, "user"}:
            raise ValueError(f"extension metadata must carry gate: user: {metadata_path}")
        extension_hashes[document_id] = actual_hash
        extension_metadata[document_id] = metadata

        for kind, (_, is_list, id_field) in GRAPH_KINDS.items():
            path = document_dir / f"{kind}.yaml"
            if not path.exists():
                continue
            payload = load_yaml(path)
            if payload is None:
                items = []
            elif is_list or kind == "documents":
                if not isinstance(payload, list):
                    if kind == "documents" and isinstance(payload, dict):
                        items = [payload]
                    else:
                        raise ValueError(f"extension {document_id} {kind}.yaml must contain a list")
                else:
                    items = payload
            else:
                if not isinstance(payload, dict):
                    raise ValueError(f"extension {document_id} {kind}.yaml must contain an object")
                items = [payload]
            for item in items:
                gate = item.get("gate")
                if gate != "user":
                    raise ValueError(
                        f"extension {document_id} {kind}/{item.get(id_field)} must carry gate: user"
                    )
                object_id = str(item.get(id_field) or "")
                identity = (kind, object_id)
                if not object_id:
                    raise ValueError(f"extension {document_id} {kind} object is missing {id_field}")
                if identity in shipped_ids:
                    raise ValueError(f"extension object collision with shipped graph: {kind}/{object_id}")
                if identity in seen_ids:
                    raise ValueError(f"extension object collision: {kind}/{object_id}")
                seen_ids.add(identity)
                extension_objects[kind].append(item)
    return extension_objects, extension_hashes, extension_metadata


def extension_root_for_project(root: str | Path) -> Path:
    """Return the default local extension overlay root."""
    return Path(root).resolve() / "graph_ext"


def _extension_root(root: Path, configured: str | Path | None) -> Path:
    if configured is None:
        try:
            from tax_graph.config import get_config_value, load_config

            configured = get_config_value(load_config(root=root), "project.paths.graph_ext_dir", "graph_ext")
        except Exception:
            configured = "graph_ext"
    candidate = Path(configured)
    return candidate if candidate.is_absolute() else root / candidate


def _with_gate(value: dict[str, Any], gate: str) -> dict[str, Any]:
    copied = dict(value)
    copied.setdefault("gate", gate)
    return copied


def _hash_files(
    root: Path,
    *,
    explicit_files: list[Path] | None = None,
    exclude_names: set[str] | None = None,
) -> str:
    excluded = exclude_names or set()
    files = explicit_files
    if files is None:
        files = [
            path
            for path in root.rglob("*")
            if path.is_file() and not any(part in excluded for part in path.relative_to(root).parts)
        ]
    digest = hashlib.sha256()
    for path in sorted(files, key=lambda candidate: candidate.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        content = path.read_bytes()
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()
