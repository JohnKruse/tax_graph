"""Verify Tax Graph parameter nodes against PolicyEngine US parameters."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tax_graph.engine import Graph
from tax_graph.io.loader import load_yaml


@dataclass
class DiffResult:
    node_id: str
    status: str
    pe_path: str | None = None
    pe_version: str | None = None
    tax_graph_value: Any = None
    pe_value: Any = None
    reason: str | None = None


@dataclass
class DiffReport:
    year: str
    results: list[DiffResult]

    @property
    def agree(self) -> int:
        return sum(1 for r in self.results if r.status == "agree")

    @property
    def disagree(self) -> int:
        return sum(1 for r in self.results if r.status == "disagree")

    @property
    def unmapped(self) -> int:
        return sum(1 for r in self.results if r.status == "unmapped")

    def format_report(self) -> str:
        lines = [
            f"=== PolicyEngine parameter diff ({self.year}) ===",
            f"  total nodes checked: {len(self.results)}",
            f"  agree: {self.agree}",
            f"  disagree: {self.disagree}",
            f"  unmapped: {self.unmapped}",
        ]
        if self.disagree > 0:
            lines.append("\n=== Disagreements ===")
            for r in self.results:
                if r.status == "disagree":
                    lines.append(f"  - {r.node_id}: {r.reason}")
                    lines.append(f"      PE ({r.pe_version}) path {r.pe_path} = {r.pe_value}")
                    lines.append(f"      Tax Graph value = {r.tax_graph_value}")
        return "\n".join(lines) + "\n"


def compare_parameter_diff(
    year: str,
    root: Path,
    offline_fixture: Path | None = None,
) -> DiffReport:
    """Run parameter diff between tax graph and PolicyEngine."""
    mapping_path = root / "graph" / str(year) / "policyengine-mapping.yaml"
    if not mapping_path.exists():
        raise FileNotFoundError(f"Mapping file not found: {mapping_path}")

    mapping_data = load_yaml(mapping_path)
    entries = mapping_data.get("entries", [])
    
    graph = Graph(year, root=root)

    pe_version = "offline-fixture"
    pe_fetcher = None

    if offline_fixture:
        with open(offline_fixture, "r") as f:
            fixture_data = json.load(f)
        def fetch_pe(path: str) -> Any:
            return fixture_data.get(path)
        pe_fetcher = fetch_pe
    else:
        try:
            import policyengine_us
            from policyengine_us import parameters
            pe_version = getattr(policyengine_us, "__version__", "unknown")
            def fetch_pe(path: str) -> Any:
                obj = parameters
                for part in path.split("."):
                    obj = getattr(obj, part)
                return obj(year)
            pe_fetcher = fetch_pe
        except ImportError:
            raise RuntimeError("policyengine-us is not installed. Install it or use an offline fixture.")

    results = []

    for entry in entries:
        node_id = entry["node_id"]
        status = entry["status"]

        if status == "unmapped":
            results.append(DiffResult(node_id=node_id, status="unmapped"))
            continue

        pe_path = entry["policyengine_path"]
        node = graph.nodes.get(node_id)
        if not node:
            results.append(DiffResult(node_id=node_id, status="disagree", reason="node not in graph"))
            continue

        tg_value = node.get("constant_value")
        
        try:
            pe_value = pe_fetcher(pe_path)
        except Exception as exc:
            results.append(DiffResult(
                node_id=node_id, 
                status="disagree", 
                pe_path=pe_path, 
                pe_version=pe_version,
                tax_graph_value=tg_value,
                pe_value=None,
                reason=f"PE fetch error: {exc}"
            ))
            continue

        agree = _compare_values(tg_value, pe_value)
        if agree:
            results.append(DiffResult(node_id=node_id, status="agree", pe_path=pe_path, pe_version=pe_version, tax_graph_value=tg_value, pe_value=pe_value))
        else:
            results.append(DiffResult(node_id=node_id, status="disagree", pe_path=pe_path, pe_version=pe_version, tax_graph_value=tg_value, pe_value=pe_value, reason="value mismatch"))

    return DiffReport(year=year, results=results)


def _compare_values(tg_val: Any, pe_val: Any) -> bool:
    if isinstance(tg_val, (int, float)) and isinstance(pe_val, (int, float)):
        return abs(tg_val - pe_val) < 1e-6
    if isinstance(tg_val, list) and isinstance(pe_val, list):
        if len(tg_val) != len(pe_val):
            return False
        for tg_item, pe_item in zip(tg_val, pe_val):
            if isinstance(tg_item, dict) and isinstance(pe_item, dict):
                # Check rates and floors if they exist
                for key in ["rate", "floor"]:
                    if key in tg_item and key in pe_item:
                        if abs(float(tg_item[key]) - float(pe_item[key])) > 1e-6:
                            return False
            else:
                if tg_item != pe_item:
                    return False
        return True
    return str(tg_val) == str(pe_val)
