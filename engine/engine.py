#!/usr/bin/env python3
"""Minimal deterministic execution engine for a Tax Graph branch.

Loads graph/<year>, takes taxpayer facts (taxpayer_facts.schema.json), traverses
the dependency graph, executes the primitive rules, and emits computed values
plus an audit trace (the requirements-doc "Tax Trace", §5.3).

v0 supports the operations used by the capital-gains slice: COPY, SUM, SUBTRACT.

Usage:  python engine/engine.py <facts.yaml> [tax_year] [target_node_id]
Deps:   pyyaml
"""
from __future__ import annotations
import sys, json, pathlib, datetime
import yaml

try:
    sys.stdout.reconfigure(encoding="utf-8")  # labels carry em-dashes; console may be cp1252
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _normalize(x):
    if isinstance(x, dict):
        return {k: _normalize(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_normalize(v) for v in x]
    if isinstance(x, (datetime.date, datetime.datetime)):
        return x.isoformat()
    return x


def _load_list(d: pathlib.Path):
    objs = []
    for f in sorted(d.glob("*.yaml")):
        data = _normalize(yaml.safe_load(f.read_text(encoding="utf-8")))
        if data is None:
            continue
        objs.extend(data if isinstance(data, list) else [data])
    return objs


class Graph:
    def __init__(self, year, root: pathlib.Path = ROOT):
        g = root / "graph" / str(year)
        self.nodes = {n["node_id"]: n for n in _load_list(g / "nodes")}
        self.rules = {r["rule_id"]: r for r in _load_list(g / "rules")}
        self.incoming: dict[str, list] = {}
        for e in _load_list(g / "edges"):
            self.incoming.setdefault(e["target"], []).append(e)


class Result:
    def __init__(self):
        self.values: dict[str, object] = {}
        self.trace: dict[str, dict] = {}


def _num(v):
    return 0 if v is None else v


def _round(val, rule):
    mode = rule.get("rounding", "none")
    if mode in ("currency", "cents"):
        return round(val, 2)
    if mode == "dollar":
        return round(val)
    return val


class Engine:
    def __init__(self, graph: Graph):
        self.g = graph

    def execute(self, facts: dict) -> Result:
        res = Result()
        self._stack: set[str] = set()
        for nid in self.g.nodes:
            self._eval(nid, facts, res)
        return res

    def _eval(self, nid, facts, res):
        if nid in res.values:
            return res.values[nid]
        if nid in self._stack:
            raise ValueError(f"dependency cycle detected at {nid}")
        self._stack.add(nid)

        incoming = self.g.incoming.get(nid, [])
        if not incoming:
            if nid in facts:
                res.values[nid] = facts[nid]
                res.trace[nid] = {"kind": "input", "value": facts[nid]}
            else:
                res.values[nid] = None
                res.trace[nid] = {"kind": "missing"}
        else:
            rule_ids = {e["rule_id"] for e in incoming if e.get("rule_id")}
            if len(rule_ids) != 1:
                raise ValueError(f"node {nid}: edges must share exactly one rule_id, got {rule_ids}")
            rule = self.g.rules[next(iter(rule_ids))]
            operands = []
            for e in incoming:
                sval = self._eval(e["source"], facts, res)
                operands.append({"node": e["source"], "role": e.get("role"), "value": sval})
            val = _round(self._apply(rule["operation"], operands), rule)
            res.values[nid] = val
            citations = sorted({c for e in incoming for c in e.get("citation_refs", [])})
            res.trace[nid] = {
                "kind": "computed", "rule": rule["rule_id"], "operation": rule["operation"],
                "inputs": operands, "value": val, "citations": citations,
            }
        self._stack.discard(nid)
        return res.values[nid]

    def _apply(self, op, operands):
        if op == "COPY":
            return _num(operands[0]["value"])
        if op == "SUM":
            return sum(_num(o["value"]) for o in operands)
        if op == "SUBTRACT":
            roles = {o["role"]: _num(o["value"]) for o in operands}
            return roles.get("minuend", 0) - roles.get("subtrahend", 0)
        raise NotImplementedError(f"operation {op} not implemented in v0")


def load_facts(path: pathlib.Path) -> dict:
    data = _normalize(yaml.safe_load(path.read_text(encoding="utf-8")))
    return {f["node_id"]: f["value"] for f in data.get("facts", [])}


def render_trace(nid, res, graph, depth=0, role=None):
    t = res.trace.get(nid, {})
    label = graph.nodes.get(nid, {}).get("label", nid)
    if t.get("kind") == "computed":
        tag = f"[{t['operation']}]"
        if t["citations"]:
            tag += " (" + ", ".join(t["citations"]) + ")"
    elif t.get("kind") == "input":
        tag = "(input)"
    else:
        tag = "(MISSING)"
    rolep = f"{role}: " if role else ""
    print(f"{'    ' * depth}{rolep}{label} = {t.get('value')}  {tag}")
    for o in t.get("inputs", []):
        render_trace(o["node"], res, graph, depth + 1, role=o.get("role"))


def main(facts_path, year="2025", target="form_1040_2025_line_7_capital_gain_loss"):
    graph = Graph(year)
    facts = load_facts(pathlib.Path(facts_path))
    res = Engine(graph).execute(facts)

    print("=== computed values ===")
    for nid in graph.nodes:
        print(f"  {nid} = {res.values.get(nid)}")
    print(f"\n=== audit trace: {target} ===")
    render_trace(target, res, graph)
    return res, target


if __name__ == "__main__":
    facts_arg = sys.argv[1] if len(sys.argv) > 1 else "examples/capital_gains_basic/facts.yaml"
    year_arg = sys.argv[2] if len(sys.argv) > 2 else "2025"
    main(facts_arg, year_arg)
