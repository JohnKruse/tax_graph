"""Engine-executed property checks derived from operation semantics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import random
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from tax_graph.engine import Engine
from tax_graph.engine.engine import TABLE_FACTS_KEY
from tax_graph.engine.operations import MISSING, is_missing
from tax_graph.io.loader import LoadedGraph

if TYPE_CHECKING:
    from tax_graph.extract.models import ExtractionBatch


DRAFT_KINDS = ("nodes", "edges", "rules", "citations", "decisions", "tables")


@dataclass(frozen=True)
class PropertyIssue:
    """One failed op-semantics property."""

    check_id: str
    object_id: str
    reason: str
    layer: str = "L3"


@dataclass(frozen=True)
class PropertyReport:
    """Result of running generated property checks."""

    issues: tuple[PropertyIssue, ...]

    @property
    def ok(self) -> bool:
        """Return whether every generated property passed."""
        return not self.issues


def check_graph_properties(
    graph: LoadedGraph,
    *,
    samples: int = 3,
    seed: int = 8675309,
) -> PropertyReport:
    """Run generated operation properties over a loaded graph."""
    issues: list[PropertyIssue] = []
    executable = _ExecutableGraph(graph)
    for index in range(samples):
        facts = _sample_facts(graph, seed=seed + index)
        try:
            result = Engine(executable).execute(facts)
        except Exception as exc:
            issues.append(PropertyIssue("property_execution", "graph", str(exc)))
            break
        issues.extend(_trace_operation_issues(result.trace))
        issues.extend(_table_relation_issues(graph, result.values))
    return PropertyReport(tuple(_dedupe_issues(issues)))


def check_draft_batch_properties(
    batch: "ExtractionBatch",
    *,
    root: str | Path | None = None,
    samples: int = 3,
    seed: int = 8675309,
) -> PropertyReport:
    """Run generated property checks over one extraction draft batch."""
    objects = {kind: [] for kind in DRAFT_KINDS}
    for kind in DRAFT_KINDS:
        objects[kind] = [item.data for item in batch.items(kind)]
    graph = LoadedGraph(
        year=batch.year,
        root=Path(root).resolve() if root is not None else Path.cwd(),
        graph_dir=Path(root).resolve() if root is not None else Path.cwd(),
        objects=objects,
    )
    return check_graph_properties(graph, samples=samples, seed=seed)


class _ExecutableGraph:
    """Engine-compatible view of a ``LoadedGraph``."""

    def __init__(self, graph: LoadedGraph):
        self.year = graph.year
        self.root = graph.root
        self.source = "loaded"
        self.documents = {
            document["document_id"]: document
            for document in sorted(graph.items("documents"), key=lambda item: item.get("document_id", ""))
            if "document_id" in document
        }
        self.citations = {
            citation["citation_id"]: citation
            for citation in sorted(graph.items("citations"), key=lambda item: item.get("citation_id", ""))
            if "citation_id" in citation
        }
        self.decisions = {
            decision["decision_id"]: decision
            for decision in sorted(graph.items("decisions"), key=lambda item: item.get("decision_id", ""))
            if "decision_id" in decision
        }
        self.nodes = {
            node["node_id"]: node
            for node in sorted(graph.items("nodes"), key=lambda item: item.get("node_id", ""))
            if "node_id" in node
        }
        self.tables = {
            table["table_id"]: table
            for table in sorted(graph.items("tables"), key=lambda item: item.get("table_id", ""))
            if "table_id" in table
        }
        self.rules = {
            rule["rule_id"]: rule
            for rule in sorted(graph.items("rules"), key=lambda item: item.get("rule_id", ""))
            if "rule_id" in rule
        }
        self.incoming: dict[str, list[dict[str, Any]]] = {}
        for edge in sorted(graph.items("edges"), key=lambda item: item.get("edge_id", "")):
            if edge.get("target"):
                self.incoming.setdefault(edge["target"], []).append(edge)


def _sample_facts(graph: LoadedGraph, *, seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    facts: dict[str, Any] = {}
    incoming_targets = {edge.get("target") for edge in graph.items("edges")}
    for node in graph.items("nodes"):
        node_id = node.get("node_id")
        if not node_id or node_id in incoming_targets or node.get("role") == "row_template":
            continue
        if node.get("table_id"):
            continue
        if node.get("value_type") == "currency":
            facts[node_id] = rng.randint(-300, 700)
    table_facts = []
    for table in graph.items("tables"):
        row = {"row_key": "prop_1", "columns": {}}
        for column in table.get("columns", []) or []:
            if column.get("kind") != "input":
                continue
            row["columns"][column["column_id"]] = _sample_column_value(column["column_id"], rng)
        table_facts.append({"table_id": table["table_id"], "rows": [row]})
    if table_facts:
        facts[TABLE_FACTS_KEY] = table_facts
    return facts


def _sample_column_value(column_id: str, rng: random.Random) -> int:
    if column_id == "d":
        return rng.randint(1000, 5000)
    if column_id == "e":
        return rng.randint(100, 900)
    if column_id == "g":
        return rng.choice([-75, 25, 125])
    return rng.randint(-200, 700)


def _trace_operation_issues(trace: Mapping[str, Mapping[str, Any]]) -> list[PropertyIssue]:
    issues: list[PropertyIssue] = []
    for object_id, entry in trace.items():
        operation = entry.get("operation")
        if operation == "COPY":
            issues.extend(_copy_issues(object_id, entry))
        elif operation == "SUM":
            issues.extend(_sum_issues(object_id, entry))
        elif operation == "SUBTRACT":
            issues.extend(_subtract_issues(object_id, entry))
    return issues


def _copy_issues(object_id: str, entry: Mapping[str, Any]) -> list[PropertyIssue]:
    inputs = entry.get("inputs", []) or []
    if len(inputs) != 1:
        return [
            PropertyIssue(
                "copy_identity",
                object_id,
                f"COPY expects exactly one input, got {len(inputs)}",
            )
        ]
    if _values_equal(entry.get("value"), inputs[0].get("value")):
        return []
    return [
        PropertyIssue(
            "copy_identity",
            object_id,
            f"COPY value {entry.get('value')} does not equal input {inputs[0].get('value')}",
        )
    ]


def _sum_issues(object_id: str, entry: Mapping[str, Any]) -> list[PropertyIssue]:
    inputs = entry.get("inputs", []) or []
    if any(operand.get("role") not in (None, "addend") for operand in inputs):
        return [PropertyIssue("sum_roles", object_id, "SUM inputs must be addends")]
    values = [operand.get("value") for operand in inputs]
    if any(is_missing(value) for value in values):
        return []
    expected = sum(0 if value is None else value for value in values)
    if _values_equal(entry.get("value"), expected):
        return []
    return [
        PropertyIssue(
            "sum_permutation_identity",
            object_id,
            f"SUM value {entry.get('value')} does not equal addend total {expected}",
        )
    ]


def _subtract_issues(object_id: str, entry: Mapping[str, Any]) -> list[PropertyIssue]:
    inputs = entry.get("inputs", []) or []
    by_role = {operand.get("role"): operand.get("value") for operand in inputs}
    if set(by_role) != {"minuend", "subtrahend"} or len(inputs) != 2:
        return [
            PropertyIssue(
                "subtract_roles",
                object_id,
                "SUBTRACT requires exactly one minuend and one subtrahend",
            )
        ]
    minuend = by_role["minuend"]
    subtrahend = by_role["subtrahend"]
    if is_missing(minuend) or is_missing(subtrahend):
        return []
    expected = (0 if minuend is None else minuend) - (0 if subtrahend is None else subtrahend)
    antisymmetry = (0 if subtrahend is None else subtrahend) - (0 if minuend is None else minuend)
    if not _values_equal(expected, -antisymmetry):
        return [PropertyIssue("subtract_antisymmetry", object_id, "SUBTRACT antisymmetry failed")]
    if _values_equal(entry.get("value"), expected):
        return []
    return [
        PropertyIssue(
            "subtract_roles",
            object_id,
            f"SUBTRACT value {entry.get('value')} does not equal minuend minus subtrahend {expected}",
        )
    ]


def _table_relation_issues(graph: LoadedGraph, values: Mapping[str, Any]) -> list[PropertyIssue]:
    issues: list[PropertyIssue] = []
    nodes = {node["node_id"]: node for node in graph.items("nodes") if "node_id" in node}
    for table in graph.items("tables"):
        if "row-band grouping" in str(table.get("description", "")).lower():
            continue
        columns = _table_columns(table)
        d_node = columns.get("d")
        e_node = columns.get("e")
        g_node = columns.get("g")
        h_node = columns.get("h")
        d_minus_e_node = _computed_table_node(nodes, table.get("table_id"), "d_minus_e")
        if not d_node or not e_node or not g_node or not h_node:
            continue
        row_key = "prop_1"
        d_value = values.get(f"{d_node}#{row_key}", MISSING)
        e_value = values.get(f"{e_node}#{row_key}", MISSING)
        g_value = values.get(f"{g_node}#{row_key}", MISSING)
        h_value = values.get(f"{h_node}#{row_key}", MISSING)
        if d_minus_e_node:
            d_minus_e_value = values.get(f"{d_minus_e_node}#{row_key}", MISSING)
            expected = _number(d_value) - _number(e_value)
            if not _values_equal(d_minus_e_value, expected):
                issues.append(
                    PropertyIssue(
                        "table_d_minus_e_relation",
                        f"{d_minus_e_node}#{row_key}",
                        f"column d-minus-e value {d_minus_e_value} does not equal d-e {expected}",
                    )
                )
        expected_h = _number(d_value) - _number(e_value) + _number(g_value)
        if not _values_equal(h_value, expected_h):
            issues.append(
                PropertyIssue(
                    "table_h_metamorphic",
                    f"{h_node}#{row_key}",
                    f"column h value {h_value} does not equal d-e+g {expected_h}",
                )
            )
        issues.extend(_table_total_issues(table, values, row_key=row_key))
    return issues


def _table_total_issues(table: Mapping[str, Any], values: Mapping[str, Any], *, row_key: str) -> list[PropertyIssue]:
    columns = _table_columns(table)
    issues: list[PropertyIssue] = []
    for total in table.get("totals", []) or []:
        column_id = total.get("column_id")
        template_node = columns.get(column_id)
        total_node = total.get("total_node")
        if not template_node or not total_node:
            continue
        instance_value = values.get(f"{template_node}#{row_key}", MISSING)
        total_value = values.get(total_node, MISSING)
        if not _values_equal(total_value, instance_value):
            issues.append(
                PropertyIssue(
                    "table_total_sum",
                    str(total_node),
                    f"table total {total_value} does not equal instance sum {instance_value}",
                )
            )
    return issues


def _table_columns(table: Mapping[str, Any]) -> dict[str, str]:
    return {
        column["column_id"]: column["template_node"]
        for column in table.get("columns", []) or []
        if column.get("column_id") and column.get("template_node")
    }


def _computed_table_node(nodes: Mapping[str, Mapping[str, Any]], table_id: Any, column_id: str) -> str | None:
    for node_id, node in nodes.items():
        if node.get("table_id") == table_id and node.get("column") == column_id and node.get("role") == "row_template":
            return node_id
    return None


def _number(value: Any) -> int | float:
    if value is MISSING:
        return 0
    return 0 if value is None else value


def _values_equal(left: Any, right: Any) -> bool:
    if is_missing(left) or is_missing(right):
        return left is right
    try:
        return round(float(left), 6) == round(float(right), 6)
    except (TypeError, ValueError):
        return left == right


def _dedupe_issues(issues: Sequence[PropertyIssue]) -> list[PropertyIssue]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[PropertyIssue] = []
    for issue in issues:
        key = (issue.check_id, issue.object_id, issue.reason)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(issue)
    return deduped
