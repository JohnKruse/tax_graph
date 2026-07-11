"""MCP stdio server exposing Tax Graph runtime tools."""

from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import dataclass
import datetime as _dt
from io import StringIO
from pathlib import Path
import sqlite3
from typing import Any

from mcp.server.fastmcp import FastMCP

from tax_graph import __version__
from tax_graph.engine import Engine, Graph, MISSING, Result, TABLE_FACTS_KEY, render_trace
from tax_graph.io.loader import LoadedGraph, load_graph
from tax_graph.io.sqlite_loader import compiled_db_path, load_sqlite_graph
from tax_graph.mcp.lifecycle import ParentWatchdog


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
MCP_TOOL_NAMES = M2_TOOL_NAMES + ("export_return_record", "export_filled_form_bundle", "get_verification")

SERVER_INSTRUCTIONS = """Tax Graph MCP server.

Use the graph and engine tools as the source of truth.

1. Never compute tax values yourself; call execute_tax_tree for computed values.
2. Never assert a tax rule without returning the citation that supports it.
3. At a decision node, present the available options, including the escape hatch, and never choose
   for the filer yourself.
4. Report missing inputs, unsupported cases, and unresolved paths rather than guessing.
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
    decisions: dict[str, dict[str, Any]]
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
        decisions={decision["decision_id"]: decision for decision in loaded.items("decisions")},
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
    """Run the server and release all SQLite readers on every shutdown path."""
    watchdog = ParentWatchdog()
    watchdog.start()
    try:
        build_mcp_server(year=year, root=root, source=source).run("stdio")
    finally:
        watchdog.close()


def _register_tools(server: FastMCP, context: McpGraphContext) -> None:
    @server.tool()
    def get_document(document_id: str) -> dict[str, Any]:
        """Return a document object by id."""
        document = context.documents.get(document_id)
        verification = _verification_summary(document_id, context)
        return {
            "document_id": document_id,
            "found": document is not None,
            "document": document,
            "decisions": _decisions_for_document(context, document_id),
            "verification": verification,
        }

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
            "decisions": _decisions_for_node(context, address["base_node_id"]),
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
        result = _execute(context, facts)
        return {
            "year": context.year,
            "source": context.graph.source,
            "values": _json_safe(result.values),
            "missing_required_inputs": result.missing_required_inputs,
            "trace": _json_safe(result.trace),
        }

    @server.tool()
    def list_required_inputs(facts: dict[str, Any]) -> dict[str, Any]:
        """List missing required inputs for supplied facts."""
        fact_values = _coerce_facts(facts)
        return {
            "missing_required_inputs": Engine(context.graph).list_required_inputs(fact_values),
        }

    @server.tool()
    def explain_calculation(node_id: str, facts: dict[str, Any] | None = None) -> dict[str, Any]:
        """Explain a node's calculation from an execution trace."""
        address = _parse_node_address(node_id)
        trace_id = _trace_id(address)
        result = _execute(context, facts or {})
        trace = result.trace.get(trace_id)
        citation_ids = trace.get("citations", []) if trace else []
        rule_id = trace.get("rule") if trace else None
        return {
            "node_id": node_id,
            "base_node_id": address["base_node_id"],
            "row_key": address["row_key"],
            "instance_note": _instance_note(address),
            "node": context.graph.nodes.get(address["base_node_id"]),
            "trace": _json_safe(trace),
            "rule": context.graph.rules.get(rule_id) if rule_id else None,
            "citations": [context.citations[citation_id] for citation_id in citation_ids if citation_id in context.citations],
        }

    @server.tool()
    def export_audit_file(
        target: str,
        facts: dict[str, Any] | None = None,
        return_id: str = "mcp_return",
        output_root: str | None = None,
    ) -> dict[str, Any]:
        """Return a human-readable audit trace for a target node."""
        address = _parse_node_address(target)
        result = _execute(context, facts or {})
        buffer = StringIO()
        with redirect_stdout(buffer):
            render_trace(_trace_id(address), result, context.graph)
        from tax_graph.output import resolve_return_root

        _resolved_id, return_root = resolve_return_root(
            project_root=context.root,
            facts_document=_facts_document_for_record(facts or {}, context.year),
            return_id=return_id,
            output_root=output_root,
        )
        audit_path = return_root / "audit.txt"
        audit_path.write_text(buffer.getvalue(), encoding="utf-8", newline="\n")
        return {
            "target": target,
            "base_node_id": address["base_node_id"],
            "row_key": address["row_key"],
            "audit_text": buffer.getvalue(),
            "path": str(audit_path),
        }

    @server.tool()
    def export_return_record(
        facts: dict[str, Any],
        target: str = "form_1040_2025_line_7_capital_gain_loss",
        generated_date: str | None = None,
        tax_graph_version: str | None = None,
        return_id: str = "mcp_return",
        output_root: str | None = None,
    ) -> dict[str, Any]:
        """Return a Markdown memo plus structured carryforward block."""
        from tax_graph.output import resolve_return_root
        from tax_graph.record import build_return_record, render_carryforward_yaml, render_memo

        result = _execute(context, facts)
        record = build_return_record(
            facts_document=_facts_document_for_record(facts, context.year),
            result=result,
            graph=context.graph,
            tax_year=context.year,
            tax_graph_version=tax_graph_version or __version__,
            generated_date=generated_date or _dt.date.today().isoformat(),
            target_node=target,
        )
        _resolved_id, return_root = resolve_return_root(
            project_root=context.root,
            facts_document=_facts_document_for_record(facts, context.year),
            return_id=return_id,
            output_root=output_root,
        )
        memo_text = render_memo(record)
        memo_path = return_root / f"return_record_{context.year}.md"
        carryforward_path = return_root / f"return_record_{context.year}.carryforward.yaml"
        memo_path.write_text(memo_text, encoding="utf-8", newline="\n")
        carryforward_path.write_text(
            render_carryforward_yaml(record.carryforward_block), encoding="utf-8", newline="\n"
        )
        return {
            "target": target,
            "memo_text": memo_text,
            "carryforward_block": record.carryforward_block.to_dict(),
            "paths": {"memo": str(memo_path), "carryforward": str(carryforward_path)},
        }

    @server.tool()
    def export_filled_form_bundle(
        facts: dict[str, Any],
        return_id: str = "mcp_return",
        output_root: str | None = None,
    ) -> dict[str, Any]:
        """Write official filled PDFs and an OTS sidecar under one return root."""
        from tax_graph.output import export_filing_bundle, resolve_return_root

        facts_document = _facts_document_for_record(facts, context.year)
        _resolved_id, return_root = resolve_return_root(
            project_root=context.root,
            facts_document=facts_document,
            return_id=return_id,
            output_root=output_root,
        )
        result = _execute(context, facts)
        bundle = export_filing_bundle(
            facts_document=facts_document,
            result=result,
            year=context.year,
            project_root=context.root,
            return_root=return_root,
        )
        return {"return_root": str(return_root), **bundle}

    @server.tool()
    def get_verification(document_id: str) -> dict[str, Any]:
        """Return the generated verification summary for one document."""
        return _verification_summary(document_id, context)


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


def _trace_id(address: dict[str, str | None]) -> str:
    if address["row_key"]:
        return f"{address['base_node_id']}#{address['row_key']}"
    return str(address["base_node_id"])


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


def _verification_summary(document_id: str, context: McpGraphContext) -> dict[str, Any]:
    from tax_graph.verify.record import verification_summary_for_document

    return verification_summary_for_document(document_id, year=context.year, root=context.root)


def _decisions_for_document(context: McpGraphContext, document_id: str) -> list[dict[str, Any]]:
    decisions = []
    for decision in context.decisions.values():
        citation_document_ids = {
            context.citations[citation_id]["document_id"]
            for citation_id in decision.get("citation_refs", [])
            if citation_id in context.citations
        }
        if document_id in citation_document_ids:
            decisions.append(decision)
    return sorted(decisions, key=lambda decision: decision["decision_id"])


def _decisions_for_node(context: McpGraphContext, node_id: str) -> list[dict[str, Any]]:
    return sorted(
        [
            decision
            for decision in context.decisions.values()
            if decision.get("sets_node") == node_id
        ],
        key=lambda decision: decision["decision_id"],
    )


def _execute(context: McpGraphContext, facts: dict[str, Any]) -> Result:
    return Engine(context.graph).execute(_coerce_facts(facts))


def _coerce_facts(facts: dict[str, Any]) -> dict[str, Any]:
    if "facts" not in facts:
        coerced = dict(facts)
        if "tables" in coerced:
            coerced[TABLE_FACTS_KEY] = coerced.pop("tables")
        if "filing_status" in coerced and "taxpayer_2025_filing_status" not in coerced:
            coerced["taxpayer_2025_filing_status"] = coerced["filing_status"]
        return coerced
    coerced = {
        fact["node_id"]: fact.get("value")
        for fact in facts.get("facts", [])
        if isinstance(fact, dict) and "node_id" in fact
    }
    if facts.get("filing_status") and "taxpayer_2025_filing_status" not in coerced:
        coerced["taxpayer_2025_filing_status"] = facts["filing_status"]
    if facts.get("tables"):
        coerced[TABLE_FACTS_KEY] = facts["tables"]
    return coerced


def _facts_document_for_record(facts: dict[str, Any], year: str) -> dict[str, Any]:
    if "facts" in facts:
        document = dict(facts)
        document.setdefault("tax_year", int(year))
        document.setdefault("facts", [])
        document.setdefault("tables", [])
        return document
    table_facts = facts.get(TABLE_FACTS_KEY) or facts.get("tables") or []
    return {
        "tax_year": int(year),
        "filing_status": facts.get("filing_status"),
        "facts": [
            {"node_id": node_id, "value": value}
            for node_id, value in sorted(facts.items())
            if node_id not in {TABLE_FACTS_KEY, "tables", "filing_status", "taxpayer_2025_filing_status"}
        ],
        "tables": table_facts,
    }


def _json_safe(value: Any) -> Any:
    if value is MISSING:
        return "MISSING"
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value
