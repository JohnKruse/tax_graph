"""MCP stdio server exposing Tax Graph runtime tools."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from tax_graph.engine import Graph


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


def build_context(
    *,
    year: str = "2025",
    root: str | Path | None = None,
    source: str | None = None,
) -> McpGraphContext:
    """Load the runtime graph for MCP tools."""
    root_path = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[2]
    graph = Graph(year, root=root_path, source=source)
    return McpGraphContext(year=str(year), root=root_path, source=source, graph=graph)


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
        return _stub("get_document", context, document_id=document_id)

    @server.tool()
    def get_node(node_id: str) -> dict[str, Any]:
        """Return a graph node by id."""
        return _stub("get_node", context, node_id=node_id)

    @server.tool()
    def get_dependencies(node_id: str) -> dict[str, Any]:
        """Return upstream dependencies for a node."""
        return _stub("get_dependencies", context, node_id=node_id)

    @server.tool()
    def get_downstream_effects(node_id: str) -> dict[str, Any]:
        """Return downstream effects for a node."""
        return _stub("get_downstream_effects", context, node_id=node_id)

    @server.tool()
    def get_citation(citation_id: str | None = None, query: str | None = None) -> dict[str, Any]:
        """Return a citation by id or search phrase."""
        return _stub("get_citation", context, citation_id=citation_id, query=query)

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
