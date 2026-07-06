"""Year-over-year delta seam: diff a draft re-extraction against the live graph.

The year N+1 workflow (design: docs/extraction-verification.md Section 6):
re-extract a form, structurally diff the drafts against the promoted graph,
and route only the changed objects back up the verification ladder. Objects
are associated to a document via their ``document_id`` field when present,
falling back to a document-id substring match on the object id (the repo id
convention embeds the document id).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from tax_graph.engine import Graph
from tax_graph.extract.models import DRAFT_KINDS, ID_FIELDS


_GRAPH_KIND_ATTRS = {
    "nodes": "nodes",
    "rules": "rules",
    "citations": "citations",
    "decisions": "decisions",
    "tables": "tables",
}


@dataclass(frozen=True)
class DraftDelta:
    """Structural diff between a draft batch and the promoted live graph."""

    document_id: str
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Whether the re-extraction matches the promoted graph exactly."""
        return not (self.added or self.removed or self.changed)


def diff_drafts_against_live(
    document_id: str,
    *,
    year: str | int,
    root: str | Path,
    graph: Graph | None = None,
    drafts_dir: str | Path | None = None,
) -> DraftDelta:
    """Diff `_drafts/<document_id>` objects against the live graph's objects."""
    root_path = Path(root).resolve()
    draft_dir = (
        Path(drafts_dir)
        if drafts_dir is not None
        else root_path / "graph" / str(year) / "_drafts" / document_id
    )
    live = graph or Graph(str(year), root=root_path, source="yaml")

    added: list[str] = []
    removed: list[str] = []
    changed: list[str] = []
    for kind in DRAFT_KINDS:
        draft_objects = _load_draft_objects(draft_dir / f"{kind}.yaml", kind)
        live_objects = _live_document_objects(live, kind, document_id)
        draft_ids = set(draft_objects)
        live_ids = set(live_objects)
        added.extend(f"{kind}/{obj_id}" for obj_id in sorted(draft_ids - live_ids))
        removed.extend(f"{kind}/{obj_id}" for obj_id in sorted(live_ids - draft_ids))
        for obj_id in sorted(draft_ids & live_ids):
            if _canonical(draft_objects[obj_id]) != _canonical(live_objects[obj_id]):
                changed.append(f"{kind}/{obj_id}")
    return DraftDelta(document_id=document_id, added=added, removed=removed, changed=changed)


def render_delta(delta: DraftDelta) -> str:
    """Render the delta report for the CLI."""
    lines = [
        f"=== draft delta - {delta.document_id} ===",
        f"  added: {len(delta.added)}",
        f"  removed: {len(delta.removed)}",
        f"  changed: {len(delta.changed)}",
    ]
    for label, items in (("added", delta.added), ("removed", delta.removed), ("changed", delta.changed)):
        for item in items:
            lines.append(f"  {label}: {item}")
    if delta.ok:
        lines.append("  re-extraction matches the promoted graph")
    return "\n".join(lines) + "\n"


def _load_draft_objects(path: Path, kind: str) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    id_field = ID_FIELDS[kind]
    return {str(item[id_field]): item for item in payload if isinstance(item, dict) and id_field in item}


def _live_document_objects(graph: Graph, kind: str, document_id: str) -> dict[str, dict[str, Any]]:
    if kind == "edges":
        collection = {
            edge["edge_id"]: edge
            for edges in graph.incoming.values()
            for edge in edges
        }
    else:
        collection = getattr(graph, _GRAPH_KIND_ATTRS[kind], {}) or {}
    matched: dict[str, dict[str, Any]] = {}
    for obj_id, data in collection.items():
        if not isinstance(data, dict):
            continue
        if data.get("document_id") == document_id or document_id in str(obj_id):
            matched[str(obj_id)] = data
    return matched


def _canonical(data: dict[str, Any]) -> str:
    return yaml.safe_dump(data, sort_keys=True)
