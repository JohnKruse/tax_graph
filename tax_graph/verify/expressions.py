"""Compare generated expression drafts with the protected live graph."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

import yaml

from tax_graph.addressing import AddressError, CanonicalAddress, load_address_artifacts
from tax_graph.config import get_config_value, load_config, project_root
from tax_graph.io.loader import load_graph, load_yaml
from workbench.address_verdicts import normalize_expression


@dataclass
class _CanonicalAddressBridge:
    """Resolve generated endpoint ids through committed address bindings."""

    live_node_ids: set[str]
    node_documents: dict[str, str]
    addresses: tuple[CanonicalAddress, ...]
    nodes_by_address: dict[str, tuple[str, ...]]
    document_aliases: dict[str, tuple[str, ...]]
    cache: dict[str, str] = field(default_factory=dict)
    states: dict[str, str] = field(default_factory=dict)

    def map(self, endpoint: str) -> str:
        """Return a bound live node id when the generated id resolves exactly."""
        value = str(endpoint)
        if value in self.cache:
            return self.cache[value]
        if value in self.live_node_ids:
            self.cache[value] = value
            self.states[value] = "already_canonical"
            return value

        address_ids = _generated_address_ids(value, self.addresses, self.document_aliases)
        node_ids = sorted({node_id for address_id in address_ids for node_id in self.nodes_by_address.get(address_id, ())})
        if len(node_ids) == 1:
            result = node_ids[0]
            self.cache[value] = result
            self.states[value] = "mapped"
            return result
        self.states[value] = "ambiguous" if len(node_ids) > 1 else "unresolved"
        self.cache[value] = value
        return value

    def report(self) -> dict[str, Any]:
        """Return deterministic bridge diagnostics for the agreement report."""
        counts = defaultdict(int)
        for state in self.states.values():
            counts[state] += 1
        return {
            "available": True,
            "endpoints_seen": len(self.states),
            "mapped": int(counts["mapped"]),
            "already_canonical": int(counts["already_canonical"]),
            "unresolved": int(counts["unresolved"]),
            "ambiguous": int(counts["ambiguous"]),
        }


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
    bridge = _build_canonical_bridge(root_path, str(year), graph.items("nodes"))
    generated = _draft_expressions(root_path, str(year), graph_dir=graph_dir, bridge=bridge)
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
    coverage = _coverage_metrics(rows)
    accuracy = _accuracy_metrics(rows)
    for document_id, rendered in rendered_by_document.items():
        document_rows = [row for row in rows if row["document_id"] == document_id]
        rendered["coverage"] = _coverage_metrics(document_rows)
        rendered["accuracy"] = _accuracy_metrics(document_rows)
    return {
        "schema_version": 2,
        "measurement": "m20_s8",
        "tax_year": int(year),
        "protected_live_graph": True,
        "generated_draft_root": (
            (Path(str(graph_dir)) if graph_dir is not None else Path(get_config_value(load_config(root=root_path), "project.paths.graph_dir", "graph")))
            / str(year)
            / "_drafts"
        ).as_posix(),
        "totals": totals,
        "coverage": coverage,
        "accuracy": accuracy,
        "identity_bridge": bridge.report() if bridge is not None else {"available": False},
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


def _draft_expressions(
    root: Path,
    year: str,
    *,
    graph_dir: str | Path | None,
    bridge: _CanonicalAddressBridge | None = None,
) -> dict[str, dict[str, Any]]:
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
                target = bridge.map(str(edge["target"])) if bridge is not None else str(edge["target"])
                grouped[target].append(edge)
        for target, target_edges in grouped.items():
            rule_ids = sorted({str(edge["rule_id"]) for edge in target_edges})
            operations = sorted({str(rules_by_id[rule_id].get("operation", "")) for rule_id in rule_ids if rule_id in rules_by_id})
            result[target] = {
                "document_id": bridge.node_documents.get(target, node_documents.get(target, draft_dir.name)) if bridge is not None else node_documents.get(target, draft_dir.name),
                "operation": operations[0] if len(operations) == 1 else "MULTIPLE" if operations else "MISSING",
                "operands": [_operand(edge, bridge=bridge) for edge in sorted(target_edges, key=lambda edge: str(edge.get("edge_id", "")))],
                "rule_ids": rule_ids,
            }
    return result


def _operand(edge: dict[str, Any], *, bridge: _CanonicalAddressBridge | None = None) -> dict[str, Any]:
    source = str(edge.get("source", ""))
    if bridge is not None:
        source = bridge.map(source)
    operand = {"ref": source}
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


def _build_canonical_bridge(
    root: Path,
    year: str,
    nodes: list[dict[str, Any]],
) -> _CanonicalAddressBridge | None:
    """Build a bridge from generated ids to live nodes through address artifacts."""
    try:
        artifacts = load_address_artifacts(year, root)
    except (AddressError, FileNotFoundError, OSError, ValueError):
        return None
    nodes_by_address: dict[str, list[str]] = defaultdict(list)
    for binding in artifacts.node_bindings:
        if str(binding.get("role", "value")) != "value":
            continue
        node_id = str(binding.get("node_id", ""))
        address_id = str(binding.get("address_id", ""))
        if node_id and address_id:
            nodes_by_address[address_id].append(node_id)
    aliases: dict[str, set[str]] = defaultdict(set)
    for address in artifacts.addresses:
        if not address.path or address.path[0].kind != "document":
            continue
        token = address.path[0].token
        for alias in _document_aliases(token):
            aliases[alias].add(address.document_id)
    return _CanonicalAddressBridge(
        live_node_ids={str(node.get("node_id", "")) for node in nodes if node.get("node_id")},
        node_documents={str(node["node_id"]): str(node.get("document_id", "")) for node in nodes if node.get("node_id")},
        addresses=artifacts.addresses,
        nodes_by_address={key: tuple(sorted(set(value))) for key, value in nodes_by_address.items()},
        document_aliases={key: tuple(sorted(value)) for key, value in aliases.items()},
    )


def _generated_address_ids(
    endpoint: str,
    addresses: tuple[CanonicalAddress, ...],
    document_aliases: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    """Resolve the stable semantic parts of a generated id to address ids."""
    match = re.match(r"(?P<prefix>.+)_(?P<year>[0-9]{4})_(?P<tail>.+)$", endpoint)
    if not match:
        return ()
    prefix = _compact(match.group("prefix"))
    document_ids = document_aliases.get(prefix, ())
    if not document_ids:
        return ()
    tail = match.group("tail")

    table_match = re.search(r"(?:^|_)p(?P<part>[0-9]+)_line_(?P<line>[0-9]+)(?P<column>[a-h])(?:_|$)", tail)
    if table_match:
        part_number = table_match.group("part")
        line = table_match.group("line")
        column = table_match.group("column")
        candidates = []
        for address in addresses:
            if address.document_id not in document_ids or address.control_role not in {"amount", "text", "description"}:
                continue
            path = {component.kind: component.token for component in address.path}
            table = path.get("table", "")
            if not table.endswith(f"line_{line}"):
                continue
            if not table.startswith("part_"):
                continue
            if path.get("column") != column:
                continue
            if not table.split("_", 2)[1:2] == ("i" if part_number == "1" else "ii" if part_number == "2" else "",):
                continue
            candidates.append(address.address_id)
        return tuple(sorted(candidates))

    line_match = re.search(r"(?:^|_)line_(?P<ref>[0-9]+[a-z]?|[a-z])(?:_|$)", tail)
    if line_match:
        ref = line_match.group("ref")
        return tuple(sorted(
            address.address_id
            for address in addresses
            if address.document_id in document_ids
            and address.official_ref == ref
            and address.control_role == "amount"
        ))

    box_match = re.search(r"(?:^|)(?:box|val)_(?P<ref>[0-9]+[a-z]?)(?:_|$)", tail)
    if box_match:
        ref = box_match.group("ref")
        return tuple(sorted(
            address.address_id
            for address in addresses
            if address.document_id in document_ids and address.official_ref == ref
        ))
    return ()


def _document_aliases(token: str) -> tuple[str, ...]:
    """Return generated-prefix aliases without a form-specific lookup table."""
    aliases = {_compact(token)}
    if token.startswith("form_"):
        aliases.add("f" + _compact(token[5:]))
    return tuple(sorted(aliases))


def _compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _coverage_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    live_count = sum(row["live"] is not None for row in rows)
    paired_count = sum(row["live"] is not None and row["generated"] is not None for row in rows)
    return {
        "live_expressions": live_count,
        "paired_expressions": paired_count,
        "unpaired_live_expressions": live_count - paired_count,
        "rate": paired_count / live_count if live_count else 0.0,
    }


def _accuracy_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    paired = [row for row in rows if row["live"] is not None and row["generated"] is not None]
    operation_agreement = sum(row["live"]["operation"] == row["generated"]["operation"] for row in paired)
    expression_agreement = sum(row["category"] == "expression_agreement" for row in paired)
    return {
        "paired_expressions": len(paired),
        "operation_agreement": operation_agreement,
        "expression_agreement": expression_agreement,
        "operation_rate": operation_agreement / len(paired) if paired else 0.0,
        "expression_rate": expression_agreement / len(paired) if paired else 0.0,
    }
