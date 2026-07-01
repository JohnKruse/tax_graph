"""MCP stdio server exposing Tax Graph runtime tools."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Any

from mcp.server.fastmcp import FastMCP

from tax_graph.engine import Graph
from tax_graph.io.loader import LoadedGraph, load_graph
from tax_graph.io.sqlite_loader import compiled_db_path, load_sqlite_graph


M2_TOOL_NAMES = (
    "get_document",
    "get_node",
    "get_dependencies",
    "get_downstream_effects",
    "get_citation",
    "execute_tax_tree",
    "list_required_inputs",
    "explain_calculation",
    "export_audit_file",
)

SERVER_INSTRUCTIONS = """Tax Graph MCP server.

Use the graph and engine tools as the source of truth. Never compute tax values yourself.
"""


@dataclass(frozen=True)
class McpGraphContext:
    """Runtime context shared by MCP tool handlers."""

    year: str
    root: Path
    source: str | None
    graph: Graph
    loaded: LoadedGraph
    documents: dict[str, dict[str, Any]]
    citations: dict[str, dict[str, Any]]
    downstream: dict[str, list[dict[str, Any]]]


def build_context(
    *,
    year: str = "2025",
    root: str | Path | None = None,
    source: str | None = None,
) -> McpGraphContext:
    """Load the runtime graph for MCP tools."""
    root_path = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[2]
    graph = Graph(year, root=root_path, source=source)
    loaded = load_sqlite_graph(year, root_path) if graph.source == "sqlite" else load_graph(year, root_path)
    downstream: dict[str, list[dict[str, Any]]] = {}
    for edge in loaded.items("edges"):
        downstream.setdefault(edge["source"], []).append(edge)
    return McpGraphContext(
        year=str(year),
        root=root_path,
        source=source,
        graph=graph,
        loaded=loaded,
        documents={document["document_id"]: document for document in loaded.items("documents")},
        citations={citation["citation_id"]: citation for citation in loaded.items("citations")},
        downstream={node_id: sorted(edges, key=lambda edge: edge["edge_id"]) for node_id, edges in downstream.items()},
    )


def build_mcp_server(
    *,
    year: str = "2025",
    root: str | Path | None = None,
    source: str | None = None,
) -> FastMCP:
    """Create the stdio MCP server with the M2 tool set registered."""
    context = build_context(year=year, root=root, source=source)
    server = FastMCP("tax-graph", instructions=SERVER_INSTRUCTIONS)
    _register_tools(server, context)
    return server


def run_mcp_server(
    *,
    year: str = "2025",
    root: str | Path | None = None,
    source: str | None = None,
) -> None:
    """Run the Tax Graph MCP server over stdio."""
    build_mcp_server(year=year, root=root, source=source).run("stdio")


def _register_tools(server: FastMCP, context: McpGraphContext) -> None:
    @server.tool()
    def get_document(document_id: str) -> dict[str, Any]:
        """Return a document object by id."""
        document = context.documents.get(document_id)
        return {"document_id": document_id, "found": document is not None, "document": document}

    @server.tool()
    def get_node(node_id: str) -> dict[str, Any]:
        """Return a graph node by id."""
        address = _parse_node_address(node_id)
        node = context.graph.nodes.get(address["base_node_id"])
        return {
            "node_id": node_id,
            "base_node_id": address["base_node_id"],
            "row_key": address["row_key"],
            "instance_note": _instance_note(address),
            "found": node is not None,
            "node": node,
        }

    @server.tool()
    def get_dependencies(node_id: str) -> dict[str, Any]:
        """Return upstream dependencies for a node."""
        address = _parse_node_address(node_id)
        edges = context.graph.incoming.get(address["base_node_id"], [])
        return {
            "node_id": node_id,
            "base_node_id": address["base_node_id"],
            "row_key": address["row_key"],
            "instance_note": _instance_note(address),
            "dependencies": [
                {
                    "edge_id": edge["edge_id"],
                    "source": edge["source"],
                    "target": edge["target"],
                    "relationship": edge.get("relationship"),
                    "role": edge.get("role"),
                    "rule_id": edge.get("rule_id"),
                    "citation_refs": edge.get("citation_refs", []),
                }
                for edge in edges
            ],
        }

    @server.tool()
    def get_downstream_effects(node_id: str) -> dict[str, Any]:
        """Return downstream effects for a node."""
        address = _parse_node_address(node_id)
        direct = context.downstream.get(address["base_node_id"], [])
        reachable = _reachable_downstream(address["base_node_id"], context)
        return {
            "node_id": node_id,
            "base_node_id": address["base_node_id"],
            "row_key": address["row_key"],
            "instance_note": _instance_note(address),
            "direct_effects": [_edge_summary(edge) for edge in direct],
            "reachable_node_ids": reachable,
        }

    @server.tool()
    def get_citation(citation_id: str | None = None, query: str | None = None) -> dict[str, Any]:
        """Return a citation by id or search phrase."""
        if citation_id:
            citation = context.citations.get(citation_id)
            return {"citation_id": citation_id, "found": citation is not None, "citation": citation}
        if query:
            return {"query": query, "matches": _search_citations(context, query)}
        return {"error": "citation_id or query is required"}

    @server.tool()
    def execute_tax_tree(facts: dict[str, Any]) -> dict[str, Any]:
        """Execute the graph from taxpayer facts."""
        return _stub("execute_tax_tree", context, facts=facts)

    @server.tool()
    def list_required_inputs(facts: dict[str, Any]) -> dict[str, Any]:
        """List missing required inputs for supplied facts."""
        return _stub("list_required_inputs", context, facts=facts)

    @server.tool()
    def explain_calculation(node_id: str, facts: dict[str, Any] | None = None) -> dict[str, Any]:
        """Explain a node's calculation from an execution trace."""
        return _stub("explain_calculation", context, node_id=node_id, facts=facts)

    @server.tool()
    def export_audit_file(target: str, facts: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return a human-readable audit trace for a target node."""
        return _stub("export_audit_file", context, target=target, facts=facts)


def _stub(tool: str, context: McpGraphContext, **arguments: Any) -> dict[str, Any]:
    return {
        "tool": tool,
        "status": "not_implemented",
        "year": context.year,
        "source": context.graph.source,
        "arguments": arguments,
    }


def _parse_node_address(node_id: str) -> dict[str, str | None]:
    base_node_id, separator, row_key = node_id.partition("#")
    return {"base_node_id": base_node_id, "row_key": row_key if separator else None}


def _instance_note(address: dict[str, str | None]) -> str | None:
    if not address["row_key"]:
        return None
    return "Runtime row instances are addressed with #row_key; the static graph resolves the base node only."


def _edge_summary(edge: dict[str, Any]) -> dict[str, Any]:
    return {
        "edge_id": edge["edge_id"],
        "source": edge["source"],
        "target": edge["target"],
        "relationship": edge.get("relationship"),
        "role": edge.get("role"),
        "rule_id": edge.get("rule_id"),
        "citation_refs": edge.get("citation_refs", []),
    }


def _reachable_downstream(base_node_id: str, context: McpGraphContext) -> list[str]:
    seen: set[str] = set()
    queue = [edge["target"] for edge in context.downstream.get(base_node_id, [])]
    while queue:
        node_id = queue.pop(0)
        if node_id in seen:
            continue
        seen.add(node_id)
        queue.extend(edge["target"] for edge in context.downstream.get(node_id, []))
    return sorted(seen)


def _search_citations(context: McpGraphContext, query: str) -> list[dict[str, Any]]:
    db_path = compiled_db_path(context.year, context.root)
    if db_path.exists():
        try:
            with sqlite3.connect(db_path) as conn:
                rows = conn.execute(
                    """
                    SELECT object_id
                    FROM graph_fts
                    WHERE graph_fts MATCH ? AND kind = 'citations'
                    ORDER BY rank, object_id
                    LIMIT 10
                    """,
                    (query,),
                ).fetchall()
            return [
                {"citation_id": row[0], "citation": context.citations.get(row[0])}
                for row in rows
            ]
        except sqlite3.Error:
            pass

    normalized = query.lower()
    return [
        {"citation_id": citation_id, "citation": citation}
        for citation_id, citation in sorted(context.citations.items())
        if normalized in str(citation.get("quoted_text", "")).lower()
    ]
