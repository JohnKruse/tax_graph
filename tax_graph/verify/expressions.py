"""Compare generated expression drafts with the protected live graph."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from tax_graph.config import get_config_value, load_config, project_root
from tax_graph.io.loader import load_graph, load_yaml
from workbench.address_verdicts import normalize_expression


def build_expression_agreement_report(
    *,
    year: str | int = "2025",
    root: str | Path | None = None,
    graph_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Build a per-document expression agreement report without mutating graph data."""
    root_path = Path(root).resolve() if root is not None else project_root()
    graph = load_graph(year, root=root_path, include_extensions=False)
    live = _live_expressions(graph.items("nodes"), graph.items("edges"), graph.items("rules"))
    generated = _draft_expressions(root_path, str(year), graph_dir=graph_dir)
    rows: list[dict[str, Any]] = []
    for target in sorted(set(live) | set(generated)):
        live_expression = live.get(target)
        generated_expression = generated.get(target)
        if live_expression is None:
            category = "extra_in_draft"
        elif generated_expression is None:
            category = "missing_in_draft"
        elif live_expression["operation"] != generated_expression["operation"]:
            category = "operation_disagreement"
        elif _normalized_operands(live_expression) != _normalized_operands(generated_expression):
            category = "operation_agreement_operands_differ"
        else:
            category = "expression_agreement"
        rows.append(
            {
                "document_id": _document_id(target, live_expression, generated_expression),
                "target": target,
                "category": category,
                "live": live_expression,
                "generated": generated_expression,
            }
        )

    by_document: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        by_document[row["document_id"]][row["category"]] += 1
    categories = (
        "expression_agreement",
        "operation_agreement_operands_differ",
        "operation_disagreement",
        "missing_in_draft",
        "extra_in_draft",
    )
    rendered_by_document = {
        document_id: {category: int(counts.get(category, 0)) for category in categories}
        for document_id, counts in sorted(by_document.items())
    }
    totals = {category: sum(item[category] for item in rendered_by_document.values()) for category in categories}
    return {
        "schema_version": 1,
        "tax_year": int(year),
        "protected_live_graph": True,
        "generated_draft_root": (
            (Path(str(graph_dir)) if graph_dir is not None else Path(get_config_value(load_config(root=root_path), "project.paths.graph_dir", "graph")))
            / str(year)
            / "_drafts"
        ).as_posix(),
        "totals": totals,
        "by_document": rendered_by_document,
        "rows": rows,
    }


def write_expression_agreement_report(
    report: dict[str, Any],
    *,
    root: str | Path | None = None,
    output_path: str | Path | None = None,
) -> Path:
    """Write the deterministic agreement report as ASCII YAML."""
    root_path = Path(root).resolve() if root is not None else project_root()
    path = Path(output_path) if output_path is not None else root_path / "output" / "m20_s7_expression_agreement.yaml"
    if not path.is_absolute():
        path = root_path / path
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(report, sort_keys=False, allow_unicode=False)
    text.encode("ascii")
    path.write_text(text, encoding="ascii", newline="\n")
    return path


def _live_expressions(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    rules: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    computed = {str(node["node_id"]): node for node in nodes if node.get("node_type") == "computed"}
    rules_by_id = {str(rule["rule_id"]): rule for rule in rules}
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        target = str(edge.get("target", ""))
        if target in computed and edge.get("rule_id"):
            incoming[target].append(edge)
    result: dict[str, dict[str, Any]] = {}
    for target, node in computed.items():
        target_edges = sorted(incoming.get(target, []), key=lambda edge: str(edge.get("edge_id", "")))
        rule_ids = sorted({str(edge["rule_id"]) for edge in target_edges})
        operations = sorted({str(rules_by_id[rule_id].get("operation", "")) for rule_id in rule_ids if rule_id in rules_by_id})
        result[target] = {
            "document_id": str(node.get("document_id", "")),
            "operation": operations[0] if len(operations) == 1 else "MULTIPLE" if operations else "MISSING",
            "operands": [_operand(edge) for edge in target_edges],
            "rule_ids": rule_ids,
        }
    return result


def _draft_expressions(root: Path, year: str, *, graph_dir: str | Path | None) -> dict[str, dict[str, Any]]:
    configured = Path(graph_dir) if graph_dir is not None else Path(get_config_value(load_config(root=root), "project.paths.graph_dir", "graph"))
    draft_root = configured if configured.is_absolute() else root / configured
    draft_root = draft_root / year / "_drafts"
    result: dict[str, dict[str, Any]] = {}
    if not draft_root.is_dir():
        return result
    for draft_dir in sorted(path for path in draft_root.iterdir() if path.is_dir()):
        rules = _load_list(draft_dir / "rules.yaml")
        rules_by_id = {str(rule.get("rule_id")): rule for rule in rules if rule.get("rule_id")}
        edges = _load_list(draft_dir / "edges.yaml")
        nodes = _load_list(draft_dir / "nodes.yaml")
        node_documents = {str(node.get("node_id")): str(node.get("document_id", "")) for node in nodes if node.get("node_id")}
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for edge in edges:
            if edge.get("target") and edge.get("rule_id"):
                grouped[str(edge["target"])].append(edge)
        for target, target_edges in grouped.items():
            rule_ids = sorted({str(edge["rule_id"]) for edge in target_edges})
            operations = sorted({str(rules_by_id[rule_id].get("operation", "")) for rule_id in rule_ids if rule_id in rules_by_id})
            result[target] = {
                "document_id": node_documents.get(target, draft_dir.name),
                "operation": operations[0] if len(operations) == 1 else "MULTIPLE" if operations else "MISSING",
                "operands": [_operand(edge) for edge in sorted(target_edges, key=lambda edge: str(edge.get("edge_id", "")))],
                "rule_ids": rule_ids,
            }
    return result


def _operand(edge: dict[str, Any]) -> dict[str, Any]:
    operand = {"ref": str(edge.get("source", ""))}
    if edge.get("role") is not None:
        operand["role"] = str(edge["role"])
    return operand


def _normalized_operands(expression: dict[str, Any]) -> Any:
    return normalize_expression(
        {
            "kind": str(expression.get("operation", "")).lower(),
            "operands": expression.get("operands", []),
        }
    )


def _document_id(target: str, live: dict[str, Any] | None, generated: dict[str, Any] | None) -> str:
    if live and live.get("document_id"):
        return str(live["document_id"])
    if generated and generated.get("document_id"):
        return str(generated["document_id"])
    return target.split("_2025_", 1)[0] if "_2025_" in target else "unknown"


def _load_list(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    value = load_yaml(path)
    return value if isinstance(value, list) else []
