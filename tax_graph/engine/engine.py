"""Minimal deterministic execution engine for a Tax Graph branch.

The engine loads authored graph data, evaluates dependencies in deterministic
order, executes primitive operations, and records a trace for every node. A
missing required input is represented by the ``MISSING`` sentinel and
propagates through dependent computations rather than being coerced to zero.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tax_graph.engine.operations import MISSING, apply_operation, is_missing, round_value
from tax_graph.io.loader import load_graph, load_yaml


ROOT = Path(__file__).resolve().parents[2]


class Graph:
    """Executable view of a loaded tax graph."""

    def __init__(self, year: str | int, root: str | Path = ROOT):
        loaded = load_graph(year, root)
        self.year = loaded.year
        self.root = loaded.root
        self.nodes = {node["node_id"]: node for node in loaded.items("nodes")}
        self.rules = {rule["rule_id"]: rule for rule in loaded.items("rules")}
        self.incoming: dict[str, list[dict[str, Any]]] = {}
        for edge in loaded.items("edges"):
            self.incoming.setdefault(edge["target"], []).append(edge)


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
        result = Result()
        self._stack: set[str] = set()
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
        return sorted(
            node_id
            for node_id, node in self.g.nodes.items()
            if node.get("required") == "required"
            and not self.g.incoming.get(node_id)
            and (node_id not in facts or facts[node_id] is None)
        )

    def _eval(self, node_id: str, facts: dict[str, Any], result: Result) -> Any:
        if node_id in result.values:
            return result.values[node_id]
        if node_id in self._stack:
            raise ValueError(f"dependency cycle detected at {node_id}")
        self._stack.add(node_id)

        incoming = self.g.incoming.get(node_id, [])
        if not incoming:
            value = self._eval_input(node_id, facts, result)
        else:
            value = self._eval_computed(node_id, incoming, facts, result)

        self._stack.discard(node_id)
        return value

    def _eval_input(self, node_id: str, facts: dict[str, Any], result: Result) -> Any:
        node = self.g.nodes[node_id]
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

        raw_value = apply_operation(rule["operation"], operands, rule)
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


def load_facts(path: str | Path) -> dict[str, Any]:
    """Load normalized taxpayer facts as a node-id to value mapping."""
    data = load_yaml(path)
    return {fact["node_id"]: fact["value"] for fact in data.get("facts", [])}


def render_trace(node_id: str, result: Result, graph: Graph, depth: int = 0, role: str | None = None) -> None:
    """Print a readable trace for a computed node."""
    trace = result.trace.get(node_id, {})
    label = graph.nodes.get(node_id, {}).get("label", node_id)
    if trace.get("kind") == "computed":
        tag = f"[{trace['operation']}]"
        if trace["citations"]:
            tag += " (" + ", ".join(trace["citations"]) + ")"
    elif trace.get("kind") == "input":
        tag = "(input)"
    elif trace.get("kind") == "blank":
        tag = "(blank)"
    else:
        tag = "(MISSING)"

    role_prefix = f"{role}: " if role else ""
    print(f"{'    ' * depth}{role_prefix}{label} = {trace.get('value')}  {tag}")
    for operand in trace.get("inputs", []):
        render_trace(operand["node"], result, graph, depth + 1, role=operand.get("role"))
