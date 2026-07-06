"""Run seeded-defect drills against the verification ladder.

The runner mutates an in-memory copy of the live graph, executes the currently
available ladder checks, and records which layer caught each injected defect.
Step 1 ships a narrow L3 arithmetic stub for the promoted Form 8949 slice; M8
Step 3 replaces that with generated engine-executed property checks.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import re
from pathlib import Path
from typing import Any

import yaml

from tax_graph.io.loader import LoadedGraph, load_graph
from tax_graph.validate.graph_validator import validate_loaded_graph


DEFAULT_CATALOG = Path(__file__).with_name("drill_catalog.yaml")


@dataclass(frozen=True)
class DrillSpec:
    """One seeded mutation and its expected ladder attribution."""

    drill_id: str
    taxonomy: str
    description: str
    mutation: dict[str, Any]
    expected_layers: tuple[str, ...]
    expectation: str = "caught"


@dataclass(frozen=True)
class LayerFinding:
    """A single finding reported by one verification layer."""

    layer: str
    check: str
    message: str


@dataclass(frozen=True)
class DrillOutcome:
    """Result of one seeded-defect drill."""

    drill_id: str
    taxonomy: str
    expectation: str
    expected_layers: tuple[str, ...]
    actual_layers: tuple[str, ...]
    status: str
    ok: bool
    findings: tuple[LayerFinding, ...]


@dataclass(frozen=True)
class DrillReport:
    """A complete run of the seeded-defect catalog."""

    year: str
    outcomes: tuple[DrillOutcome, ...]

    @property
    def ok(self) -> bool:
        """Return whether every drill met its expected attribution."""
        return all(outcome.ok for outcome in self.outcomes)

    def format_report(self) -> str:
        """Render a concise command-line report."""
        result = "PASS" if self.ok else "FAIL"
        lines = [
            "=== drill report ===",
            f"  tax_year: {self.year}",
            f"  drills: {len(self.outcomes)}",
            f"  result: {result}",
        ]
        for outcome in self.outcomes:
            expected = ",".join(outcome.expected_layers) if outcome.expected_layers else "-"
            actual = ",".join(outcome.actual_layers) if outcome.actual_layers else "-"
            lines.append(
                f"  - {outcome.drill_id}: {outcome.status} "
                f"expected={expected} actual={actual}"
            )
            if not outcome.ok:
                for finding in outcome.findings:
                    lines.append(f"    - {finding.layer}/{finding.check}: {finding.message}")
        return "\n".join(lines)


def load_catalog(path: str | Path | None = None) -> list[DrillSpec]:
    """Load a drill catalog YAML file."""
    catalog_path = Path(path) if path is not None else DEFAULT_CATALOG
    data = yaml.safe_load(catalog_path.read_text(encoding="utf-8")) or []
    specs: list[DrillSpec] = []
    for item in data:
        specs.append(
            DrillSpec(
                drill_id=item["id"],
                taxonomy=item["taxonomy"],
                description=item.get("description", ""),
                mutation=dict(item.get("mutation") or {}),
                expected_layers=tuple(item.get("expected_layers") or ()),
                expectation=item.get("expectation", "caught"),
            )
        )
    return specs


def run_drills(
    *,
    year: str | int = "2025",
    root: str | Path | None = None,
    catalog: str | Path | None = None,
) -> DrillReport:
    """Run all seeded-defect drills in a catalog."""
    baseline = load_graph(year, root)
    outcomes = tuple(_run_one(baseline, spec) for spec in load_catalog(catalog))
    return DrillReport(year=baseline.year, outcomes=outcomes)


def _run_one(baseline: LoadedGraph, spec: DrillSpec) -> DrillOutcome:
    mutated = _copy_graph(baseline)
    _apply_mutation(mutated, spec.mutation)
    findings = tuple(_run_layers(baseline, mutated))
    actual_layers = tuple(sorted({finding.layer for finding in findings}))
    status, ok = _classify(spec, actual_layers)
    return DrillOutcome(
        drill_id=spec.drill_id,
        taxonomy=spec.taxonomy,
        expectation=spec.expectation,
        expected_layers=spec.expected_layers,
        actual_layers=actual_layers,
        status=status,
        ok=ok,
        findings=findings,
    )


def _copy_graph(graph: LoadedGraph) -> LoadedGraph:
    return LoadedGraph(
        year=graph.year,
        root=graph.root,
        graph_dir=graph.graph_dir,
        objects=deepcopy(graph.objects),
    )


def _classify(spec: DrillSpec, actual_layers: tuple[str, ...]) -> tuple[str, bool]:
    if spec.expectation == "no_effect":
        return ("no_effect", True) if not actual_layers else ("unexpected_catch", False)
    if not actual_layers:
        return "miss", False
    if set(actual_layers).intersection(spec.expected_layers):
        return "caught", True
    return "wrong_layer", False


def _apply_mutation(graph: LoadedGraph, mutation: dict[str, Any]) -> None:
    kind = mutation.get("kind")
    if kind == "swap_edge_roles":
        edges = _objects_by_id(graph, "edges", "edge_id")
        edge_ids = mutation.get("edge_ids", [])
        if len(edge_ids) != 2:
            raise ValueError("swap_edge_roles requires exactly two edge_ids")
        first = edges[edge_ids[0]]
        second = edges[edge_ids[1]]
        first["role"], second["role"] = second.get("role"), first.get("role")
        return
    if kind == "change_rule_operation":
        _objects_by_id(graph, "rules", "rule_id")[mutation["rule_id"]]["operation"] = mutation["operation"]
        return
    if kind == "remove_edge":
        _remove_object(graph, "edges", "edge_id", mutation["edge_id"])
        return
    if kind == "delete_node":
        _remove_object(graph, "nodes", "node_id", mutation["node_id"])
        return
    if kind == "change_node_label":
        _objects_by_id(graph, "nodes", "node_id")[mutation["node_id"]]["label"] = mutation["label"]
        return
    if kind == "retarget_edge":
        _objects_by_id(graph, "edges", "edge_id")[mutation["edge_id"]]["target"] = mutation["target"]
        return
    if kind == "corrupt_citation_quote":
        _objects_by_id(graph, "citations", "citation_id")[mutation["citation_id"]]["quoted_text"] = mutation[
            "quoted_text"
        ]
        return
    if kind == "add_phantom_node":
        graph.objects.setdefault("nodes", []).append(dict(mutation["node"]))
        return
    if kind == "drop_table_total":
        table = _objects_by_id(graph, "tables", "table_id")[mutation["table_id"]]
        table["totals"] = [
            total for total in table.get("totals", []) if total.get("column_id") != mutation["column_id"]
        ]
        return
    if kind == "annotate_confidence":
        return
    if kind == "add_rule_parameter":
        rule = _objects_by_id(graph, "rules", "rule_id")[mutation["rule_id"]]
        rule.setdefault("parameters", {})[mutation["parameter"]] = mutation["value"]
        return
    if kind == "no_op":
        return
    raise ValueError(f"unsupported drill mutation: {kind}")


def _run_layers(baseline: LoadedGraph, mutated: LoadedGraph) -> list[LayerFinding]:
    findings: list[LayerFinding] = []
    findings.extend(_validator_findings(mutated))
    findings.extend(_citation_quote_findings(baseline, mutated))
    findings.extend(_structural_delta_findings(baseline, mutated))
    findings.extend(_property_stub_findings(mutated))
    findings.extend(_link_delta_findings(baseline, mutated))
    return findings


def _validator_findings(graph: LoadedGraph) -> list[LayerFinding]:
    result = validate_loaded_graph(graph)
    return [LayerFinding("L0", "validator", error) for error in result.errors]


def _citation_quote_findings(baseline: LoadedGraph, mutated: LoadedGraph) -> list[LayerFinding]:
    baseline_citations = _objects_by_id(baseline, "citations", "citation_id")
    findings: list[LayerFinding] = []
    for citation in mutated.items("citations"):
        citation_id = citation.get("citation_id")
        if citation_id not in baseline_citations:
            continue
        if citation.get("quoted_text") != baseline_citations[citation_id].get("quoted_text"):
            findings.append(
                LayerFinding(
                    "L0",
                    "citation_integrity",
                    f"citation {citation_id} quoted_text changed from baseline",
                )
            )
    return findings


def _structural_delta_findings(baseline: LoadedGraph, mutated: LoadedGraph) -> list[LayerFinding]:
    findings: list[LayerFinding] = []
    baseline_nodes = _objects_by_id(baseline, "nodes", "node_id")
    mutated_nodes = _objects_by_id(mutated, "nodes", "node_id")
    for node_id in sorted(set(baseline_nodes) - set(mutated_nodes)):
        findings.append(LayerFinding("L1", "node_inventory", f"node {node_id} missing from mutated graph"))
    for node_id in sorted(set(mutated_nodes) - set(baseline_nodes)):
        findings.append(LayerFinding("L1", "node_inventory", f"node {node_id} is not in baseline inventory"))
    for node_id in sorted(set(baseline_nodes).intersection(mutated_nodes)):
        before = _line_anchor_signature(baseline_nodes[node_id])
        after = _line_anchor_signature(mutated_nodes[node_id])
        if before != after:
            findings.append(
                LayerFinding(
                    "L1",
                    "line_inventory",
                    f"node {node_id} line anchor changed from {before or '-'} to {after or '-'}",
                )
            )

    baseline_tables = _objects_by_id(baseline, "tables", "table_id")
    mutated_tables = _objects_by_id(mutated, "tables", "table_id")
    for table_id in sorted(set(baseline_tables).intersection(mutated_tables)):
        before = _table_total_columns(baseline_tables[table_id])
        after = _table_total_columns(mutated_tables[table_id])
        if before != after:
            findings.append(
                LayerFinding(
                    "L1",
                    "table_inventory",
                    f"table {table_id} totals changed from {before} to {after}",
                )
            )
    return findings


def _property_stub_findings(graph: LoadedGraph) -> list[LayerFinding]:
    findings: list[LayerFinding] = []
    rules = _objects_by_id(graph, "rules", "rule_id")
    if rules.get("sum_currency", {}).get("operation") != "SUM":
        findings.append(LayerFinding("L3", "op_semantics_stub", "sum_currency operation is not SUM"))
    if rules.get("subtract_currency", {}).get("operation") != "SUBTRACT":
        findings.append(LayerFinding("L3", "op_semantics_stub", "subtract_currency operation is not SUBTRACT"))

    nodes = _objects_by_id(graph, "nodes", "node_id")
    incoming = _incoming_edges(graph)
    for table in graph.items("tables"):
        table_id = table.get("table_id")
        table_nodes = [node for node in nodes.values() if node.get("table_id") == table_id]
        by_column = {node.get("column"): node["node_id"] for node in table_nodes if node.get("role") == "row_template"}
        d_node = by_column.get("d")
        e_node = by_column.get("e")
        g_node = by_column.get("g")
        d_minus_e_node = by_column.get("d_minus_e")
        h_node = by_column.get("h")
        if d_node and e_node and d_minus_e_node:
            findings.extend(_check_subtract_shape(d_minus_e_node, d_node, e_node, incoming))
        if d_minus_e_node and g_node and h_node:
            findings.extend(_check_h_sum_shape(h_node, d_minus_e_node, g_node, incoming))
    return findings


def _check_subtract_shape(
    target: str,
    d_node: str,
    e_node: str,
    incoming: dict[str, list[dict[str, Any]]],
) -> list[LayerFinding]:
    edges = incoming.get(target, [])
    roles = {(edge.get("source"), edge.get("role"), edge.get("rule_id")) for edge in edges}
    expected = {
        (d_node, "minuend", "subtract_currency"),
        (e_node, "subtrahend", "subtract_currency"),
    }
    if expected.issubset(roles):
        return []
    return [
        LayerFinding(
            "L3",
            "op_semantics_stub",
            f"{target} does not model column d minus column e with correct SUBTRACT roles",
        )
    ]


def _check_h_sum_shape(
    target: str,
    d_minus_e_node: str,
    g_node: str,
    incoming: dict[str, list[dict[str, Any]]],
) -> list[LayerFinding]:
    edges = incoming.get(target, [])
    roles = {(edge.get("source"), edge.get("role"), edge.get("rule_id")) for edge in edges}
    expected = {
        (d_minus_e_node, "addend", "sum_currency"),
        (g_node, "addend", "sum_currency"),
    }
    if expected.issubset(roles):
        return []
    return [
        LayerFinding(
            "L3",
            "op_semantics_stub",
            f"{target} does not sum column d-minus-e and column g into column h",
        )
    ]


def _link_delta_findings(baseline: LoadedGraph, mutated: LoadedGraph) -> list[LayerFinding]:
    baseline_edges = _objects_by_id(baseline, "edges", "edge_id")
    mutated_edges = _objects_by_id(mutated, "edges", "edge_id")
    findings: list[LayerFinding] = []
    for edge_id in sorted(set(baseline_edges).intersection(mutated_edges)):
        before = baseline_edges[edge_id]
        after = mutated_edges[edge_id]
        if before.get("relationship") != "FEEDS":
            continue
        if before.get("target") != after.get("target"):
            findings.append(
                LayerFinding(
                    "L5",
                    "link_reconcile",
                    f"FEEDS edge {edge_id} target changed from {before.get('target')} to {after.get('target')}",
                )
            )
    return findings


def _objects_by_id(graph: LoadedGraph, kind: str, id_field: str) -> dict[str, dict[str, Any]]:
    return {obj[id_field]: obj for obj in graph.items(kind) if id_field in obj}


def _remove_object(graph: LoadedGraph, kind: str, id_field: str, object_id: str) -> None:
    graph.objects[kind] = [obj for obj in graph.items(kind) if obj.get(id_field) != object_id]


def _incoming_edges(graph: LoadedGraph) -> dict[str, list[dict[str, Any]]]:
    incoming: dict[str, list[dict[str, Any]]] = {}
    for edge in graph.items("edges"):
        incoming.setdefault(edge.get("target", ""), []).append(edge)
    return incoming


_LINE_RE = re.compile(r"\bline[_ ]([0-9]+[a-z]?)\b", re.IGNORECASE)


def _line_anchor_signature(node: dict[str, Any]) -> tuple[str, ...]:
    text = " ".join(
        str(node.get(field, ""))
        for field in ("node_id", "label", "description")
    )
    return tuple(sorted({match.group(1).lower() for match in _LINE_RE.finditer(text)}))


def _table_total_columns(table: dict[str, Any]) -> tuple[str, ...]:
    return tuple(sorted(total.get("column_id", "") for total in table.get("totals", []) or []))
