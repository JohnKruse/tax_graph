"""Shared YAML loading utilities for authored graph data.

The loader keeps graph objects as ordered lists so validation can catch
duplicate ids before any later dictionary indexing would collapse them.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


GRAPH_KINDS: dict[str, tuple[str, bool, str]] = {
    "documents": ("document", False, "document_id"),
    "nodes": ("node", True, "node_id"),
    "edges": ("edge", True, "edge_id"),
    "rules": ("rule", True, "rule_id"),
    "citations": ("citation", True, "citation_id"),
    "decisions": ("decision", True, "decision_id"),
}


@dataclass(frozen=True)
class LoadedGraph:
    """Authored graph objects for a single tax year."""

    year: str
    root: Path
    graph_dir: Path
    objects: dict[str, list[dict[str, Any]]]

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


def load_graph(year: str | int = "2025", root: str | Path | None = None) -> LoadedGraph:
    """Load authored graph YAML for a tax year without indexing by ids."""
    graph_year = str(year)
    project_root = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[2]
    graph_dir = project_root / "graph" / graph_year
    if not graph_dir.is_dir():
        raise FileNotFoundError(f"no graph dir for {graph_year}")

    objects = {
        subdir: load_kind(graph_dir, subdir, is_list)
        for subdir, (_, is_list, _) in GRAPH_KINDS.items()
    }
    return LoadedGraph(year=graph_year, root=project_root, graph_dir=graph_dir, objects=objects)
