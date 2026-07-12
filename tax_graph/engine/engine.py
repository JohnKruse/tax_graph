"""Minimal deterministic execution engine for a Tax Graph branch.

The engine loads authored graph data, evaluates dependencies in deterministic
order, executes primitive operations, and records a trace for every node. A
missing required input is represented by the ``MISSING`` sentinel and
propagates through dependent computations rather than being coerced to zero.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sqlite3
from typing import Any

from tax_graph.engine.operations import MISSING, apply_operation, is_missing, round_value
from tax_graph.frontier.build import load_frontier_registry
from tax_graph.io.loader import extension_root_for_project, load_graph, load_yaml
from tax_graph.io.sqlite_loader import compiled_db_path, load_sqlite_graph


ROOT = Path(__file__).resolve().parents[2]
TABLE_FACTS_KEY = "#tables"


class Graph:
    """Executable view of a loaded tax graph."""

    def __init__(
        self,
        year: str | int,
        root: str | Path = ROOT,
        source: str | None = None,
        *,
        include_extensions: bool = True,
    ):
        """``include_extensions=False`` loads ONLY the shipped graph - the option
        exists for shipped-content parity checks (yaml vs sqlite must compare
        the same objects even when a local user extension is installed)."""
        graph_source = _resolve_source(year, root, source)
        loaded = (
            load_sqlite_graph(year, root)
            if graph_source == "sqlite"
            else load_graph(year, root, include_extensions=include_extensions)
        )
        self.year = loaded.year
        self.root = loaded.root
        self.source = graph_source
        self.base_content_hash = loaded.base_content_hash
        self.extension_hashes = dict(loaded.extension_hashes or {})
        self.extension_metadata = dict(loaded.extension_metadata or {})
        self.documents = {
            document["document_id"]: _with_runtime_gate(document)
            for document in sorted(loaded.items("documents"), key=lambda item: item["document_id"])
        }
        self.citations = {
            citation["citation_id"]: _with_runtime_gate(citation)
            for citation in sorted(loaded.items("citations"), key=lambda item: item["citation_id"])
        }
        self.decisions = {
            decision["decision_id"]: _with_runtime_gate(decision)
            for decision in sorted(loaded.items("decisions"), key=lambda item: item["decision_id"])
        }
        self.nodes = {
            node["node_id"]: _with_runtime_gate(node)
            for node in sorted(loaded.items("nodes"), key=lambda item: item["node_id"])
        }
        self.tables = {
            table["table_id"]: _with_runtime_gate(table)
            for table in sorted(loaded.items("tables"), key=lambda item: item["table_id"])
        }
        self.frontiers = list(load_frontier_registry(year, self.root).get("frontiers", []) or [])
        self.rules = {
            rule["rule_id"]: _with_runtime_gate(rule)
            for rule in sorted(loaded.items("rules"), key=lambda item: item["rule_id"])
        }
        self.tax_table = _load_tax_table_resource(graph_source, self.year, self.root, loaded.graph_dir)
        self.incoming: dict[str, list[dict[str, Any]]] = {}
        for edge in sorted(loaded.items("edges"), key=lambda item: item["edge_id"]):
            self.incoming.setdefault(edge["target"], []).append(edge)

    def provenance_for_node(self, node_id: str) -> dict[str, Any] | None:
        """Return the gate and artifact hash for one static node."""
        node = self.nodes.get(node_id)
        if node is None:
            return None
        document_id = str(node.get("document_id") or "")
        gate = str(node.get("gate") or "project")
        return {
            "gate": gate,
            "document_id": document_id,
            "artifact_hash": self.extension_hashes.get(document_id, self.base_content_hash),
            "verification_tier": self.extension_metadata.get(document_id, {}).get("verification_tier")
            if gate == "user"
            else None,
        }


def _resolve_source(year: str | int, root: str | Path, source: str | None) -> str:
    if source in (None, "auto"):
        db_path = compiled_db_path(year, root)
        if _has_extensions(year, root):
            return "yaml"
        return "sqlite" if _compiled_artifact_is_stamped(db_path) else "yaml"
    normalized = str(source).lower()
    if normalized not in {"yaml", "sqlite"}:
        raise ValueError(f"unsupported graph source: {source}")
    if normalized == "sqlite" and _has_extensions(year, root):
        # Extensions are deliberately not compiled. Loading the YAML overlay
        # keeps an explicit ``--source sqlite`` request safe and honest.
        return "yaml"
    return normalized


def _has_extensions(year: str | int, root: str | Path) -> bool:
    root_path = Path(root).resolve()
    try:
        from tax_graph.config import get_config_value, load_config

        configured = get_config_value(load_config(root=root_path), "project.paths.graph_ext_dir", "graph_ext")
        overlay = Path(configured)
        if not overlay.is_absolute():
            overlay = root_path / overlay
    except Exception:
        overlay = extension_root_for_project(root_path)
    year_dir = overlay / str(year)
    return any(path.is_dir() and path.name != "_drafts" for path in year_dir.iterdir()) if year_dir.is_dir() else False


def _compiled_artifact_is_stamped(path: Path) -> bool:
    """Return whether an existing SQLite artifact has the M14 hash stamp.

    Auto mode treats an older unstamped artifact as stale and uses authored
    YAML. Explicit ``source=sqlite`` still raises in the loader so a caller
    cannot accidentally rely on an unverifiable artifact.
    """
    if not path.exists():
        return False
    try:
        with sqlite3.connect(path) as conn:
            row = conn.execute("SELECT value FROM metadata WHERE key = 'content_hash'").fetchone()
        return bool(row and row[0])
    except sqlite3.Error:
        return False


def _with_runtime_gate(value: dict[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    copied.setdefault("gate", "project")
    return copied


@dataclass
class Result:
    """Computed values, trace, and missing required inputs."""

    values: dict[str, Any] = field(default_factory=dict)
    trace: dict[str, dict[str, Any]] = field(default_factory=dict)
    missing_required_inputs: list[str] = field(default_factory=list)


class Engine:
    """Evaluate a Tax Graph deterministically from supplied facts."""

    def __init__(self, graph: Graph):
        self.g = graph

    def execute(self, facts: dict[str, Any]) -> Result:
        """Evaluate all graph nodes and return values plus an audit trace."""
        facts = _normalize_facts(facts)
        result = Result()
        self._stack: set[str] = set()
        self._instance_stack: set[str] = set()
        self._table_rows = _table_rows_by_id(facts.get(TABLE_FACTS_KEY, []))
        for node_id in self.g.nodes:
            self._eval(node_id, facts, result)
        result.missing_required_inputs = sorted(
            node_id
            for node_id, trace in result.trace.items()
            if trace.get("kind") == "missing_required"
        )
        return result

    def list_required_inputs(self, facts: dict[str, Any]) -> list[str]:
        """List missing required leaf inputs for the supplied facts."""
        facts = _normalize_facts(facts)
        missing = [
            node_id
            for node_id, node in self.g.nodes.items()
            if node.get("required") == "required"
            and node.get("role") != "row_template"
            and not self.g.incoming.get(node_id)
            and (node_id not in facts or facts[node_id] is None)
        ]
        table_rows = _table_rows_by_id(facts.get(TABLE_FACTS_KEY, []))
        for table_id, rows in table_rows.items():
            table = self.g.tables.get(table_id)
            if not table:
                continue
            for column in table.get("columns", []):
                if column.get("kind") != "input":
                    continue
                node_id = column["template_node"]
                node = self.g.nodes.get(node_id, {})
                if node.get("required") != "required":
                    continue
                for row in rows:
                    row_key = row["row_key"]
                    row_columns = row.get("columns") or {}
                    if column["column_id"] not in row_columns or row_columns.get(column["column_id"]) is None:
                        missing.append(_instance_id(node_id, row_key))
        return sorted(missing)

    def _eval(self, node_id: str, facts: dict[str, Any], result: Result) -> Any:
        if node_id in result.values:
            return result.values[node_id]
        if node_id in self._stack:
            raise ValueError(f"dependency cycle detected at {node_id}")
        self._stack.add(node_id)

        incoming = self.g.incoming.get(node_id, [])
        node = self.g.nodes[node_id]
        if node.get("table_id") and node.get("role") == "total":
            value = self._eval_table_total(node_id, facts, result)
        elif node.get("table_id") and node.get("role") == "row_template":
            value = self._eval_table_template(node_id, result)
        elif not incoming:
            value = self._eval_input(node_id, facts, result)
        else:
            value = self._eval_computed(node_id, incoming, facts, result)

        self._stack.discard(node_id)
        return value

    def _eval_input(self, node_id: str, facts: dict[str, Any], result: Result) -> Any:
        node = self.g.nodes[node_id]
        if "constant_value" in node:
            value = node["constant_value"]
            result.values[node_id] = value
            result.trace[node_id] = {
                "kind": "parameter" if node.get("node_type") == "parameter" else "constant",
                "value": value,
                "citations": sorted(node.get("citation_refs", [])),
            }
            return value
        if node_id in facts and not (node.get("required") == "required" and facts[node_id] is None):
            value = facts[node_id]
            result.values[node_id] = value
            result.trace[node_id] = {"kind": "input", "value": value}
            return value

        if node.get("required") == "required":
            result.values[node_id] = MISSING
            result.trace[node_id] = {"kind": "missing_required", "value": MISSING}
            return MISSING

        result.values[node_id] = None
        result.trace[node_id] = {"kind": "blank", "value": None}
        return None

    def _eval_computed(
        self,
        node_id: str,
        incoming: list[dict[str, Any]],
        facts: dict[str, Any],
        result: Result,
    ) -> Any:
        rule_ids = {edge["rule_id"] for edge in incoming if edge.get("rule_id")}
        if len(rule_ids) != 1:
            raise ValueError(f"node {node_id}: edges must share exactly one rule_id, got {rule_ids}")

        rule = self.g.rules[next(iter(rule_ids))]
        operands = []
        for edge in incoming:
            if edge["source"] not in self.g.nodes:
                frontier = _frontier_for_missing_source(edge, self.g)
                if frontier is not None:
                    result.values[node_id] = MISSING
                    result.trace[node_id] = _unresolved_trace(edge, frontier)
                    return MISSING
            source_value = self._eval(edge["source"], facts, result)
            source_node = self.g.nodes[edge["source"]]
            operands.append(
                {
                    "node": edge["source"],
                    "role": edge.get("role"),
                    "value": source_value,
                    "required": source_node.get("required"),
                }
            )

        raw_value = apply_operation(rule["operation"], operands, rule, context={"tax_table": self.g.tax_table})
        value = round_value(raw_value, rule)
        result.values[node_id] = value
        citations = sorted({citation for edge in incoming for citation in edge.get("citation_refs", [])})
        result.trace[node_id] = {
            "kind": "missing" if is_missing(value) else "computed",
            "rule": rule["rule_id"],
            "operation": rule["operation"],
            "inputs": operands,
            "value": value,
            "citations": citations,
        }
        return value

    def _eval_table_template(self, node_id: str, result: Result) -> Any:
        result.values[node_id] = None
        result.trace[node_id] = {
            "kind": "table_template",
            "value": None,
            "table_id": self.g.nodes[node_id].get("table_id"),
            "column": self.g.nodes[node_id].get("column"),
        }
        return None

    def _eval_table_total(self, node_id: str, facts: dict[str, Any], result: Result) -> Any:
        node = self.g.nodes[node_id]
        table_id = node["table_id"]
        column_id = node["column"]
        table = self.g.tables.get(table_id)
        rows = self._table_rows.get(table_id, [])
        if not table:
            result.values[node_id] = MISSING
            result.trace[node_id] = {
                "kind": "missing",
                "value": MISSING,
                "note": f"missing table {table_id}",
            }
            return MISSING
        template_node = _template_node_for_column(table, column_id)
        if template_node is None:
            result.values[node_id] = MISSING
            result.trace[node_id] = {
                "kind": "missing",
                "value": MISSING,
                "note": f"missing template column {column_id}",
            }
            return MISSING
        if not rows:
            result.values[node_id] = 0
            result.trace[node_id] = {
                "kind": "table_total",
                "operation": "SUM",
                "inputs": [],
                "instances": [],
                "value": 0,
                "citations": sorted(table.get("citation_refs", [])),
                "note": "no instances supplied",
            }
            return 0

        operands = []
        for row in rows:
            row_key = row["row_key"]
            value = self._eval_table_instance(template_node, row, table, facts, result)
            operands.append(
                {
                    "node": _instance_id(template_node, row_key),
                    "role": "addend",
                    "value": value,
                    "required": self.g.nodes[template_node].get("required"),
                }
            )
        rule = self.g.rules.get("sum_currency", {"rule_id": "sum_currency", "operation": "SUM", "rounding": "currency"})
        raw_value = apply_operation("SUM", operands, rule, context={"tax_table": self.g.tax_table})
        value = round_value(raw_value, rule)
        result.values[node_id] = value
        result.trace[node_id] = {
            "kind": "missing" if is_missing(value) else "table_total",
            "rule": rule["rule_id"],
            "operation": "SUM",
            "inputs": operands,
            "instances": [operand["node"] for operand in operands],
            "value": value,
            "citations": sorted(table.get("citation_refs", [])),
        }
        return value

    def _eval_table_instance(
        self,
        node_id: str,
        row: dict[str, Any],
        table: dict[str, Any],
        facts: dict[str, Any],
        result: Result,
    ) -> Any:
        row_key = row["row_key"]
        instance_id = _instance_id(node_id, row_key)
        if instance_id in result.values:
            return result.values[instance_id]
        if instance_id in self._instance_stack:
            raise ValueError(f"dependency cycle detected at {instance_id}")
        self._instance_stack.add(instance_id)
        try:
            node = self.g.nodes[node_id]
            column_id = node.get("column")
            column = _column_definition(table, node_id)
            if column and column.get("kind") == "input":
                return self._eval_table_input(node_id, column_id, row, result)
            return self._eval_table_computed(node_id, row, table, facts, result)
        finally:
            self._instance_stack.discard(instance_id)

    def _eval_table_input(
        self,
        node_id: str,
        column_id: str | None,
        row: dict[str, Any],
        result: Result,
    ) -> Any:
        row_key = row["row_key"]
        instance_id = _instance_id(node_id, row_key)
        columns = row.get("columns") or {}
        node = self.g.nodes[node_id]
        if column_id in columns and not (node.get("required") == "required" and columns[column_id] is None):
            value = columns[column_id]
            result.values[instance_id] = value
            result.trace[instance_id] = {
                "kind": "table_input",
                "value": value,
                "base_node_id": node_id,
                "row_key": row_key,
                "column": column_id,
            }
            return value
        if node.get("required") == "required":
            result.values[instance_id] = MISSING
            result.trace[instance_id] = {
                "kind": "missing_required",
                "value": MISSING,
                "base_node_id": node_id,
                "row_key": row_key,
                "column": column_id,
            }
            return MISSING
        result.values[instance_id] = None
        result.trace[instance_id] = {
            "kind": "blank",
            "value": None,
            "base_node_id": node_id,
            "row_key": row_key,
            "column": column_id,
        }
        return None

    def _eval_table_computed(
        self,
        node_id: str,
        row: dict[str, Any],
        table: dict[str, Any],
        facts: dict[str, Any],
        result: Result,
    ) -> Any:
        row_key = row["row_key"]
        instance_id = _instance_id(node_id, row_key)
        incoming = self.g.incoming.get(node_id, [])
        rule_ids = {edge["rule_id"] for edge in incoming if edge.get("rule_id")}
        if len(rule_ids) != 1:
            raise ValueError(f"node {node_id}: edges must share exactly one rule_id, got {rule_ids}")

        rule = self.g.rules[next(iter(rule_ids))]
        operands = []
        for edge in incoming:
            source_node = self.g.nodes[edge["source"]]
            if source_node.get("table_id") == table["table_id"] and source_node.get("role") == "row_template":
                source_value = self._eval_table_instance(edge["source"], row, table, facts, result)
                source_id = _instance_id(edge["source"], row_key)
            else:
                source_value = self._eval(edge["source"], facts, result)
                source_id = edge["source"]
            operands.append(
                {
                    "node": source_id,
                    "role": edge.get("role"),
                    "value": source_value,
                    "required": source_node.get("required"),
                }
            )

        raw_value = apply_operation(rule["operation"], operands, rule, context={"tax_table": self.g.tax_table})
        value = round_value(raw_value, rule)
        result.values[instance_id] = value
        citations = sorted({citation for edge in incoming for citation in edge.get("citation_refs", [])})
        result.trace[instance_id] = {
            "kind": "missing" if is_missing(value) else "table_computed",
            "rule": rule["rule_id"],
            "operation": rule["operation"],
            "inputs": operands,
            "value": value,
            "citations": citations,
            "base_node_id": node_id,
            "row_key": row_key,
        }
        return value


def load_facts_document(path: str | Path) -> dict[str, Any]:
    """Load normalized taxpayer facts while preserving fact provenance."""
    data = load_yaml(path)
    if data is None:
        return {"facts": [], "tables": []}
    data.setdefault("facts", [])
    data.setdefault("tables", [])
    return data


def load_facts(path: str | Path) -> dict[str, Any]:
    """Load normalized taxpayer facts as a node-id to value mapping."""
    data = load_facts_document(path)
    facts = {fact["node_id"]: fact["value"] for fact in data.get("facts", [])}
    if data.get("filing_status"):
        facts["taxpayer_2025_filing_status"] = data["filing_status"]
    if data.get("tables"):
        facts[TABLE_FACTS_KEY] = data["tables"]
    return facts


def _normalize_facts(facts: dict[str, Any]) -> dict[str, Any]:
    """Accept public fact aliases used by YAML fixtures and direct callers."""
    if "filing_status" not in facts or "taxpayer_2025_filing_status" in facts:
        return facts
    normalized = dict(facts)
    normalized["taxpayer_2025_filing_status"] = normalized["filing_status"]
    return normalized


def render_trace(node_id: str, result: Result, graph: Graph, depth: int = 0, role: str | None = None) -> None:
    """Print a readable trace for a computed node."""
    trace = result.trace.get(node_id, {})
    base_node_id = trace.get("base_node_id") or _base_node_id(node_id)
    label = graph.nodes.get(base_node_id, {}).get("label", node_id)
    if trace.get("row_key"):
        label = f"{label}#{trace['row_key']}"
    if trace.get("kind") in {"computed", "table_computed", "table_total"}:
        tag = f"[{trace['operation']}]"
        if trace.get("citations"):
            tag += " (" + ", ".join(trace["citations"]) + ")"
    elif trace.get("kind") in {"input", "table_input"}:
        tag = "(input)"
    elif trace.get("kind") == "blank":
        tag = "(blank)"
    elif trace.get("kind") == "table_template":
        tag = "(table template)"
    elif trace.get("kind") == "parameter":
        tag = "(parameter)"
        if trace.get("citations"):
            tag += " (" + ", ".join(trace["citations"]) + ")"
    elif trace.get("kind") == "constant":
        tag = "(constant)"
    elif trace.get("kind") == "unresolved":
        tag = "(UNRESOLVED)"
    else:
        tag = "(MISSING)"

    role_prefix = f"{role}: " if role else ""
    note = f" - {trace['note']}" if trace.get("note") else ""
    print(f"{'    ' * depth}{role_prefix}{label} = {trace.get('value')}  {tag}{note}")
    for operand in trace.get("inputs", []):
        render_trace(operand["node"], result, graph, depth + 1, role=operand.get("role"))


def _table_rows_by_id(table_facts: Any) -> dict[str, list[dict[str, Any]]]:
    rows_by_table: dict[str, list[dict[str, Any]]] = {}
    for table_fact in table_facts or []:
        table_id = table_fact.get("table_id")
        if not table_id:
            continue
        rows_by_table.setdefault(table_id, []).extend(table_fact.get("rows", []) or [])
    return rows_by_table


def _instance_id(node_id: str, row_key: str) -> str:
    return f"{node_id}#{row_key}"


def _base_node_id(node_id: str) -> str:
    return node_id.partition("#")[0]


def _template_node_for_column(table: dict[str, Any], column_id: str) -> str | None:
    for column in table.get("columns", []) or []:
        if column.get("column_id") == column_id:
            return column.get("template_node")
    return None


def _column_definition(table: dict[str, Any], node_id: str) -> dict[str, Any] | None:
    for column in table.get("columns", []) or []:
        if column.get("template_node") == node_id:
            return column
    return None


def _frontier_for_missing_source(edge: dict[str, Any], graph: Graph) -> dict[str, Any] | None:
    source = edge.get("source")
    doc_id, line = _infer_document_line(str(source), graph)
    for entry in graph.frontiers:
        if entry.get("status") == "modeled":
            continue
        entry_source = entry.get("source") or {}
        entry_target = entry.get("target") or {}
        if entry_source.get("node_id") == source:
            return entry
        if entry_target.get("node_id") == source:
            return entry
        if doc_id == entry_target.get("document_id") and line == str(entry_target.get("line")):
            return entry
    return None


def _unresolved_trace(edge: dict[str, Any], frontier: dict[str, Any]) -> dict[str, Any]:
    target = frontier.get("target") or {}
    target_document_id = target.get("document_id") or target.get("external_id")
    address = target_document_id or "unknown frontier"
    if target.get("line"):
        address = f"{address} line {target['line']}"
    return {
        "kind": "unresolved",
        "value": MISSING,
        "inputs": [
            {
                "node": edge.get("source"),
                "role": edge.get("role"),
                "value": MISSING,
                "required": "frontier",
            }
        ],
        "frontier_id": frontier.get("frontier_id"),
        "target": target,
        "target_url": frontier.get("target_url"),
        "citation_ref": frontier.get("citation_ref"),
        "citations": [frontier.get("citation_ref")] if frontier.get("citation_ref") else [],
        "extend_command": f"tax-graph extend {target_document_id}" if target_document_id else None,
        "target_tier": "T1",
        "proposed_provenance": {"gate": "user", "verification_tier": "T1"},
        "note": f"depends on {address}, not yet modeled, see {frontier.get('target_url')}",
    }


def _infer_document_line(node_id: str, graph: Graph) -> tuple[str | None, str | None]:
    document_ids = sorted(graph.documents, key=len, reverse=True)
    document_id = next((candidate for candidate in document_ids if node_id.startswith(candidate)), None)
    import re

    match = re.search(r"_line_([0-9]+[a-z]?)", node_id, flags=re.IGNORECASE)
    line = match.group(1).lower() if match else None
    return document_id, line


def _load_tax_table_resource(graph_source: str, year: str, root: Path, graph_dir: Path) -> list[dict[str, Any]]:
    if graph_source == "sqlite":
        path = compiled_db_path(year, root)
        if path.exists():
            with sqlite3.connect(path) as conn:
                rows = conn.execute(
                    """
                    SELECT
                        income_min,
                        income_max,
                        single,
                        married_filing_jointly,
                        married_filing_separately,
                        head_of_household,
                        qualifying_surviving_spouse
                    FROM tax_table
                    ORDER BY income_min, income_max
                    """
                ).fetchall()
            return [
                {
                    "income_min": row[0],
                    "income_max": row[1],
                    "taxes": {
                        "single": row[2],
                        "married_filing_jointly": row[3],
                        "married_filing_separately": row[4],
                        "head_of_household": row[5],
                        "qualifying_surviving_spouse": row[6],
                    },
                }
                for row in rows
            ]

    path = graph_dir / "tax_table.json"
    if not path.exists():
        return []
    data = load_yaml(path) or {}
    return list(data.get("entries", []) or [])
