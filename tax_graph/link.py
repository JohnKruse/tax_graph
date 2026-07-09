"""Resolve reviewed outbound-flow declarations into live graph edges."""

from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from typing import Any

import yaml

from tax_graph.flow_dispositions import load_flow_dispositions
from tax_graph.io.loader import LoadedGraph, load_graph


@dataclass(frozen=True)
class LinkResult:
    """Summary of a LINK pass."""

    path: Path
    realized: list[dict[str, Any]]
    unresolved: list[dict[str, Any]]
    rejected: list[dict[str, Any]]


def link_outbound_flows(
    year: str | int = "2025",
    root: str | Path | None = None,
    *,
    write: bool = True,
) -> LinkResult:
    """Resolve draft outbound-flow declarations against the promoted live graph."""
    root_path = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[1]
    graph = load_graph(year, root_path)
    dispositions = load_flow_dispositions(year, root=root_path)
    nodes = {node["node_id"]: node for node in graph.items("nodes") if "node_id" in node}
    non_link_edge_ids = {
        edge["edge_id"]
        for edge in graph.items("edges")
        if "edge_id" in edge and not str(edge["edge_id"]).startswith("link_")
    }
    non_link_pairs = {
        (edge.get("source"), edge.get("target"))
        for edge in graph.items("edges")
        if not str(edge.get("edge_id", "")).startswith("link_")
    }
    target_index = _target_line_index(graph)
    flows = _load_outbound_flows(graph.graph_dir)

    realized: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for flow in flows:
        disposition = dispositions.get(str(flow.get("flow_id") or ""))
        if disposition and str(disposition.get("disposition")) == "rejected":
            rejected.append(
                {
                    "flow_id": flow.get("flow_id"),
                    "document_id": flow.get("source_document_id"),
                    "reason": disposition.get("reason"),
                    "resolution": disposition.get("resolution"),
                }
            )
            continue
        source_node_id = _resolve_flow_source_node(flow, nodes)
        target_node_id = _resolve_flow_target_node(flow, target_index)
        if not source_node_id or not target_node_id:
            unresolved.append(
                {
                    "flow_id": flow.get("flow_id"),
                    "source_node_id": source_node_id or flow.get("source_node_id"),
                    "target_document_id": flow.get("target_document_id"),
                    "target_line": str(flow.get("target_line")),
                }
            )
            continue
        edge = {
            "edge_id": _unique_edge_id(f"link_{flow.get('flow_id')}", non_link_edge_ids),
            "source": source_node_id,
            "target": target_node_id,
            "relationship": "FEEDS",
            "rule_id": "copy_currency_value",
            "citation_refs": _citation_refs_for_source(nodes[source_node_id]),
        }
        if (edge["source"], edge["target"]) not in non_link_pairs:
            realized.append(edge)
            non_link_edge_ids.add(edge["edge_id"])

    realized = sorted(realized, key=lambda edge: edge["edge_id"])
    rejected = sorted(rejected, key=lambda item: str(item.get("flow_id") or ""))
    path = graph.graph_dir / "edges" / "linked-outbound.yaml"
    if write:
        _write_yaml(path, realized)
    return LinkResult(path=path, realized=realized, unresolved=unresolved, rejected=rejected)


def _load_outbound_flows(graph_dir: Path) -> list[dict[str, Any]]:
    flows: list[dict[str, Any]] = []
    drafts_dir = graph_dir / "_drafts"
    if not drafts_dir.exists():
        return flows
    for path in sorted(drafts_dir.glob("*/outbound_flows.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        flows.extend(
            flow
            for flow in data
            if str(flow.get("source_document_id")) != str(flow.get("target_document_id"))
        )
    return flows


def _resolve_flow_source_node(flow: dict[str, Any], nodes: dict[str, dict[str, Any]]) -> str | None:
    raw_source = str(flow.get("source_node_id", ""))
    if raw_source in nodes:
        return raw_source
    outline_id = str(flow.get("source_outline_id", ""))
    part = "part_ii" if "part_ii" in outline_id else "part_i" if "part_i" in outline_id else ""
    if not part:
        part = "part_ii" if "part_ii" in raw_source else "part_i" if "part_i" in raw_source else ""
    for node_id, node in sorted(nodes.items()):
        if (
            node.get("document_id") == flow.get("source_document_id")
            and node.get("role") == "total"
            and node.get("column") == "h"
            and (not part or part in node_id)
        ):
            return node_id
    return None


def _resolve_flow_target_node(
    flow: dict[str, Any],
    target_index: dict[tuple[str, str, str], str],
) -> str | None:
    document_id = str(flow.get("target_document_id"))
    line = str(flow.get("target_line")).lower()
    raw_source = str(flow.get("source_node_id", ""))
    column = _column_from_node_id(raw_source) or "h"
    return target_index.get((document_id, line, column)) or target_index.get((document_id, line, ""))


def _target_line_index(graph: LoadedGraph) -> dict[tuple[str, str, str], str]:
    index: dict[tuple[str, str, str], str] = {}
    for node in graph.items("nodes"):
        line = _line_from_label(str(node.get("label", ""))) or _line_from_node_id(str(node.get("node_id", "")))
        if not line:
            continue
        column = str(node.get("column") or _column_from_node_id(str(node.get("node_id", ""))) or "")
        key = (str(node.get("document_id")), line, column)
        index.setdefault(key, str(node.get("node_id")))
        index.setdefault((str(node.get("document_id")), line, ""), str(node.get("node_id")))
    return index


def _line_from_label(label: str) -> str | None:
    match = re.search(r"\bline\s+([0-9]+[a-z]?)\b", label, flags=re.IGNORECASE)
    return match.group(1).lower() if match else None


def _line_from_node_id(node_id: str) -> str | None:
    match = re.search(r"_line_([0-9]+[a-z]?)", node_id, flags=re.IGNORECASE)
    return match.group(1).lower() if match else None


def _column_from_node_id(node_id: str) -> str | None:
    match = re.search(r"_column_([a-z])(?:_|$)", node_id, flags=re.IGNORECASE)
    return match.group(1).lower() if match else None


def _citation_refs_for_source(node: dict[str, Any]) -> list[str]:
    refs = list(node.get("citation_refs") or [])
    return refs or ["cite_8949_line2_totals"]


def _unique_edge_id(raw: str, used: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", raw.lower()).strip("_")
    edge_id = base or "link_edge"
    suffix = 2
    while edge_id in used:
        edge_id = f"{base}_{suffix}"
        suffix += 1
    return edge_id


def _write_yaml(path: Path, value: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8", newline="\n")
