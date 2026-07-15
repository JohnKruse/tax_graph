"""Resolve reviewed outbound-flow declarations into live graph edges."""

from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from typing import Any

import yaml

from tax_graph.flow_dispositions import load_flow_dispositions
from tax_graph.io.loader import LoadedGraph, load_graph
from tax_graph.addressing import AddressArtifacts, load_address_artifacts


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
    addresses = load_address_artifacts(year, root_path)
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
        source_node_id = _resolve_flow_source_node(flow, nodes, addresses)
        target_node_id = _resolve_flow_target_node(flow, addresses)
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
    if write and not unresolved:
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


def _resolve_flow_source_node(
    flow: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
    artifacts: AddressArtifacts,
) -> str | None:
    raw_source = str(flow.get("source_node_id", ""))
    if raw_source in nodes:
        return raw_source
    flow_id = str(flow.get("flow_id", ""))
    claims = [item for item in artifacts.references if item.get("reference_id") == flow_id and item.get("status") == "exact"]
    if len(claims) != 1:
        return None
    bound = {
        item["node_id"] for item in artifacts.node_bindings
        if item["address_id"] == claims[0]["source_address_id"] and item["status"] == "exact"
    }
    if len(bound) == 1 and next(iter(bound)) in nodes:
        return next(iter(bound))
    return None


def _resolve_flow_target_node(
    flow: dict[str, Any],
    artifacts: AddressArtifacts,
) -> str | None:
    document_id = str(flow.get("target_document_id"))
    line = str(flow.get("target_line")).lower()
    match = artifacts.resolve(document_id=document_id, official_ref=line, control_role="amount")
    if match.state != "exact" or match.address is None:
        return None
    nodes = {item["node_id"] for item in artifacts.node_bindings if item["address_id"] == match.address.address_id and item["status"] == "exact"}
    return next(iter(nodes)) if len(nodes) == 1 else None


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
