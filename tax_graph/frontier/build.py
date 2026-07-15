"""Build and load the derived frontier registry."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from pathlib import Path
from typing import Any

import yaml

from tax_graph.acquire.manifest import load_manifest
from tax_graph.flow_dispositions import load_flow_dispositions
from tax_graph.frontier.soi import SoiCounts, load_form_id_map, load_soi_counts
from tax_graph.io.loader import LoadedGraph, load_graph
from tax_graph.addressing import load_address_artifacts
from tax_graph.link import _resolve_flow_target_node


@dataclass(frozen=True)
class FrontierBuildResult:
    """Result of a deterministic frontier build."""

    path: Path
    registry: dict[str, Any]


def build_frontier_registry(
    year: str | int = "2025",
    root: str | Path | None = None,
    *,
    write: bool = True,
) -> FrontierBuildResult:
    """Build the derived frontier registry for one tax year."""
    root_path = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[2]
    graph = load_graph(year, root_path)
    soi = load_soi_counts(root_path)
    manifest = load_manifest(root=root_path)
    manifest_urls = {entry.document_id: entry.url for entry in manifest.documents}
    label_map = load_form_id_map(root_path)

    entries = []
    entries.extend(_outbound_flow_entries(graph, soi, manifest_urls))
    entries.extend(_reference_entries(graph, soi, manifest_urls, label_map))
    entries.extend(_deferred_branch_entries(graph, soi, manifest_urls))
    entries = _dedupe_entries(entries)

    registry = {
        "tax_year": int(graph.year),
        "provenance": {
            "generated_by": "tax_graph.frontier.build",
            "soi_year": soi.soi_year,
            "soi_source_url": soi.source_url,
            "soi_note": soi.note,
        },
        "frontiers": entries,
    }
    path = graph.graph_dir / "frontier.yaml"
    if write:
        _write_yaml(path, registry)
    return FrontierBuildResult(path=path, registry=registry)


def load_frontier_registry(year: str | int = "2025", root: str | Path | None = None) -> dict[str, Any]:
    """Load ``graph/<year>/frontier.yaml`` or return an empty registry."""
    root_path = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[2]
    path = root_path / "graph" / str(year) / "frontier.yaml"
    if not path.exists():
        return {"tax_year": int(year), "provenance": {}, "frontiers": []}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {"tax_year": int(year), "frontiers": []}


def summarize_frontier(year: str | int = "2025", root: str | Path | None = None) -> dict[str, Any]:
    """Summarize worklist and coverage from the current frontier registry."""
    root_path = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[2]
    registry = load_frontier_registry(year, root_path)
    if not registry.get("frontiers"):
        registry = build_frontier_registry(year, root_path).registry
    graph = load_graph(year, root_path)
    soi = load_soi_counts(root_path)
    modeled_docs = {doc["document_id"] for doc in graph.items("documents") if "document_id" in doc}
    manifest_docs = {entry.document_id for entry in load_manifest(root=root_path).documents}
    worklist = sorted(
        [entry for entry in registry.get("frontiers", []) if entry.get("status") == "declared"],
        key=lambda entry: (-(entry.get("weight") or 0), entry["frontier_id"]),
    )
    return {
        "tax_year": int(year),
        "worklist": worklist,
        "coverage": _coverage_summary(
            soi=soi,
            modeled_docs=modeled_docs,
            in_scope_docs={doc for doc in manifest_docs if doc in soi.counts},
        ),
        "provenance": registry.get("provenance", {}),
    }


def render_frontier_summary(summary: dict[str, Any], *, json_output: bool = False) -> str:
    """Render a frontier summary for CLI output."""
    if json_output:
        return json.dumps(summary, indent=2, sort_keys=True) + "\n"
    coverage = summary["coverage"]
    lines = ["=== frontier worklist ==="]
    if summary["worklist"]:
        for entry in summary["worklist"]:
            target = entry.get("target", {})
            address = target.get("document_id", "-")
            if target.get("line"):
                address += f" line {target['line']}"
            lines.append(
                f"  {address}: {entry['kind']} from {entry['source'].get('document_id', '-')} "
                f"(weight {entry.get('weight') or 'unknown'}, {entry['status']})"
            )
    else:
        lines.append("  -")
    lines.append("")
    lines.append(
        f"covers ~{coverage['full_universe_percent']:.1f}% of filer-weighted form usage "
        f"({coverage['modeled_weight']} / {coverage['full_universe_weight']})"
    )
    lines.append(
        f"covers ~{coverage['in_scope_percent']:.1f}% of in-scope filer-weighted form usage "
        f"({coverage['in_scope_modeled_weight']} / {coverage['in_scope_weight']})"
    )
    provenance = summary.get("provenance", {})
    if provenance:
        lines.append(
            "SOI provenance: "
            f"{provenance.get('soi_year')} {provenance.get('soi_source_url')} "
            f"({provenance.get('soi_note')})"
        )
    return "\n".join(lines) + "\n"


def _outbound_flow_entries(
    graph: LoadedGraph,
    soi: SoiCounts,
    manifest_urls: dict[str, str],
) -> list[dict[str, Any]]:
    flows = _load_outbound_flows(graph.graph_dir)
    dispositions = load_flow_dispositions(graph.year, root=graph.root)
    nodes = {node["node_id"]: node for node in graph.items("nodes") if "node_id" in node}
    citations = {citation["citation_id"]: citation for citation in graph.items("citations") if "citation_id" in citation}
    live_edges = {(edge.get("source"), edge.get("target")) for edge in graph.items("edges")}
    addresses = load_address_artifacts(graph.year, graph.root)
    entries = []
    for flow in flows:
        target_document_id = str(flow.get("target_document_id"))
        target_line = str(flow.get("target_line"))
        source_node_id = _resolve_flow_source_node(flow, nodes)
        target_node_id = _resolve_flow_target_node(flow, addresses)
        status = "unmodeled"
        disposition = dispositions.get(str(flow.get("flow_id") or ""))
        if target_document_id in manifest_urls or target_document_id in {doc.get("document_id") for doc in graph.items("documents")}:
            status = "declared"
        if source_node_id and target_node_id and (source_node_id, target_node_id) in live_edges:
            status = "modeled"
        if disposition and str(disposition.get("disposition")) == "rejected":
            status = "rejected"
        citation_ref = _best_flow_citation(source_node_id, nodes, citations)
        entries.append(
            _compact(
                {
                    "frontier_id": _slug(flow.get("flow_id") or f"flow_{source_node_id}_to_{target_document_id}_{target_line}"),
                    "kind": "outbound_flow",
                    "source": {
                        "document_id": str(flow.get("source_document_id")),
                        "node_id": source_node_id or str(flow.get("source_node_id")),
                        "flow_id": _slug(str(flow.get("flow_id", ""))),
                    },
                    "target": _compact(
                        {
                            "document_id": target_document_id,
                            "line": target_line,
                            "node_id": target_node_id,
                        }
                    ),
                    "target_url": _target_url(target_document_id, manifest_urls, graph),
                    "citation_ref": citation_ref,
                    "status": status,
                    "weight": soi.counts.get(target_document_id),
                    "disposition": disposition.get("disposition") if disposition else None,
                    "disposition_reason": disposition.get("reason") if disposition else None,
                }
            )
        )
    return entries


def _coverage_summary(
    *,
    soi: SoiCounts,
    modeled_docs: set[str],
    in_scope_docs: set[str],
) -> dict[str, Any]:
    modeled_weight = sum(weight for doc, weight in soi.counts.items() if doc in modeled_docs)
    full_weight = sum(soi.counts.values())
    in_scope_weight = sum(weight for doc, weight in soi.counts.items() if doc in in_scope_docs)
    in_scope_modeled = sum(weight for doc, weight in soi.counts.items() if doc in modeled_docs and doc in in_scope_docs)
    return {
        "modeled_weight": modeled_weight,
        "full_universe_weight": full_weight,
        "full_universe_percent": _percent(modeled_weight, full_weight),
        "in_scope_modeled_weight": in_scope_modeled,
        "in_scope_weight": in_scope_weight,
        "in_scope_percent": _percent(in_scope_modeled, in_scope_weight),
    }


def _percent(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 1)


def _reference_entries(
    graph: LoadedGraph,
    soi: SoiCounts,
    manifest_urls: dict[str, str],
    label_map: dict[str, str],
) -> list[dict[str, Any]]:
    entries = []
    document_ids = {doc.get("document_id") for doc in graph.items("documents")}
    for citation in graph.items("citations"):
        text = " ".join(str(citation.get(field, "")) for field in ("quoted_text", "locator", "url"))
        for label, document_id in label_map.items():
            if label not in text:
                continue
            if document_id == citation.get("document_id"):
                continue
            status = "modeled" if document_id in document_ids else "declared" if document_id in manifest_urls else "unmodeled"
            entries.append(
                {
                    "frontier_id": _slug(f"ref_{citation['citation_id']}_to_{document_id}"),
                    "kind": "form_reference",
                    "source": {
                        "document_id": citation.get("document_id"),
                        "citation_id": citation["citation_id"],
                    },
                    "target": {"document_id": document_id},
                    "target_url": _target_url(document_id, manifest_urls, graph),
                    "citation_ref": citation["citation_id"],
                    "status": status,
                    "weight": soi.counts.get(document_id),
                }
            )
        pub_id = _publication_id(text)
        if pub_id:
            entries.append(
                {
                    "frontier_id": _slug(f"ref_{citation['citation_id']}_to_{pub_id}"),
                    "kind": "pub_reference",
                    "source": {
                        "document_id": citation.get("document_id"),
                        "citation_id": citation["citation_id"],
                    },
                    "target": {"external_id": pub_id},
                    "target_url": str(citation.get("url") or "https://www.irs.gov/publications"),
                    "citation_ref": citation["citation_id"],
                    "status": "unmodeled",
                    "weight": None,
                }
            )
    return entries


def _load_outbound_flows(graph_dir: Path) -> list[dict[str, Any]]:
    flows = []
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


def _deferred_branch_entries(
    graph: LoadedGraph,
    soi: SoiCounts,
    manifest_urls: dict[str, str],
) -> list[dict[str, Any]]:
    path = graph.graph_dir / "frontier-declarations.yaml"
    if not path.exists():
        return []
    citations = {citation["citation_id"] for citation in graph.items("citations") if "citation_id" in citation}
    documents = {document["document_id"] for document in graph.items("documents") if "document_id" in document}
    entries = []
    for item in yaml.safe_load(path.read_text(encoding="utf-8")) or []:
        document_id = str(item["document_id"])
        citation_ref = str(item["citation_ref"])
        if document_id not in documents:
            raise ValueError(f"frontier declaration {item.get('frontier_id')} references unknown document {document_id}")
        if citation_ref not in citations:
            raise ValueError(f"frontier declaration {item.get('frontier_id')} references unknown citation {citation_ref}")
        entries.append(
            {
                "frontier_id": _slug(item.get("frontier_id") or f"deferred_{document_id}_line_{item.get('line')}"),
                "kind": "deferred_branch",
                "source": {"document_id": document_id},
                "target": _compact(
                    {
                        "document_id": document_id,
                        "line": str(item.get("line")) if item.get("line") is not None else None,
                        "node_id": item.get("node_id"),
                    }
                ),
                "target_url": str(item.get("target_url") or _target_url(document_id, manifest_urls, graph)),
                "citation_ref": citation_ref,
                "status": str(item.get("status") or "declared"),
                "weight": soi.counts.get(document_id),
                "title": item.get("title"),
                "purpose": item.get("purpose"),
            }
        )
    return entries


def _resolve_flow_source_node(flow: dict[str, Any], nodes: dict[str, dict[str, Any]]) -> str | None:
    raw_source = str(flow.get("source_node_id", ""))
    if raw_source in nodes:
        return raw_source
    outline_id = str(flow.get("source_outline_id", ""))
    part = "part_ii" if "part_ii" in outline_id else "part_i" if "part_i" in outline_id else ""
    if not part:
        part = "part_ii" if "part_ii" in raw_source else "part_i" if "part_i" in raw_source else ""
    for node_id, node in nodes.items():
        if (
            node.get("document_id") == flow.get("source_document_id")
            and node.get("role") == "total"
            and node.get("column") == "h"
            and (not part or part in node_id)
        ):
            return node_id
    return None


def _best_flow_citation(
    source_node_id: str | None,
    nodes: dict[str, dict[str, Any]],
    citations: dict[str, dict[str, Any]],
) -> str:
    if source_node_id and nodes.get(source_node_id, {}).get("citation_refs"):
        return str(nodes[source_node_id]["citation_refs"][0])
    if "cite_8949_line2_totals" in citations:
        return "cite_8949_line2_totals"
    if citations:
        return sorted(citations)[0]
    raise ValueError("frontier outbound flow needs at least one citation")


def _line_index(graph: LoadedGraph) -> dict[tuple[str, str], str]:
    index = {}
    for node in graph.items("nodes"):
        line = _line_from_label(str(node.get("label", "")))
        if line:
            index.setdefault((node.get("document_id"), line), node.get("node_id"))
    return {(str(doc), str(line)): str(node) for (doc, line), node in index.items() if doc and line and node}


def _line_from_label(label: str) -> str | None:
    match = re.search(r"\bline\s+([0-9]+[a-z]?)\b", label, flags=re.IGNORECASE)
    return match.group(1).lower() if match else None


def _publication_id(text: str) -> str | None:
    match = re.search(r"\bPublication\s+([0-9]+)\b|\bPub\.\s*([0-9]+)\b", text, flags=re.IGNORECASE)
    if not match:
        return None
    number = match.group(1) or match.group(2)
    return f"publication_{number}"


def _target_url(document_id: str, manifest_urls: dict[str, str], graph: LoadedGraph) -> str:
    if document_id in manifest_urls:
        return manifest_urls[document_id]
    for doc in graph.items("documents"):
        if doc.get("document_id") == document_id and doc.get("source_url"):
            return str(doc["source_url"])
    return "https://www.irs.gov/forms-pubs"


def _dedupe_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {entry["frontier_id"]: entry for entry in entries}
    return [by_id[key] for key in sorted(by_id)]


def _compact(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item is not None}


def _slug(value: Any) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")
    return slug or "frontier"


def _write_yaml(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8", newline="\n")
