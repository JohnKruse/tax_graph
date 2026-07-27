"""Validate authored Tax Graph YAML and taxpayer fact documents.

Validation has two layers: JSON Schema checks for each object and graph-level
integrity checks that JSON Schema cannot express, such as unique ids,
cross-reference resolution, tax-year consistency, and dependency cycles.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Mapping

from tax_graph.documents import DOCUMENT_CLASSES
from tax_graph.io.loader import GRAPH_KINDS, LoadedGraph, load_graph, load_yaml
from tax_graph.output.field_maps import validate_field_maps
from tax_graph.output.geometry import validate_node_geometry
from tax_graph.verify.completeness import check_loaded_graph_field_completeness

try:
    import jsonschema

    HAVE_JSONSCHEMA = True
except ImportError:  # pragma: no cover - dependency is declared for normal use.
    jsonschema = None
    HAVE_JSONSCHEMA = False


@dataclass(frozen=True)
class ValidationResult:
    """Result of validating one tax-year graph."""

    year: str
    counts: dict[str, int]
    jsonschema_enabled: bool
    errors: list[str]

    @property
    def ok(self) -> bool:
        """Whether validation found no errors."""
        return not self.errors

    def format_report(self) -> str:
        """Render the command-line validation report."""
        counts_text = " ".join(f"{kind}={count}" for kind, count in self.counts.items())
        lines = [
            f"tax year {self.year}: {counts_text}",
            f"jsonschema: {'ON' if self.jsonschema_enabled else 'SKIPPED (not installed)'}",
        ]
        if self.errors:
            lines.append(f"\n{len(self.errors)} INTEGRITY ERROR(S):")
            lines.extend(f"  - {error}" for error in self.errors)
        else:
            lines.append("graph integrity OK - all references resolve")
        return "\n".join(lines)


def validate_graph(
    year: str | int = "2025",
    root: str | Path | None = None,
    *,
    field_grids: Mapping[str, Mapping[str, Any]] | None = None,
    mef_line_inventory: Mapping[str, list[str]] | None = None,
) -> ValidationResult:
    """Validate schema conformance and graph integrity for one tax year."""
    return validate_loaded_graph(
        load_graph(year, root),
        field_grids=field_grids,
        mef_line_inventory=mef_line_inventory,
    )


def validate_loaded_graph(
    graph: LoadedGraph,
    *,
    field_grids: Mapping[str, Mapping[str, Any]] | None = None,
    mef_line_inventory: Mapping[str, list[str]] | None = None,
) -> ValidationResult:
    """Validate a loaded graph, including in-memory mutated drill graphs."""
    schemas_dir = graph.root / "schemas"
    errors: list[str] = []

    _validate_schemas(graph, schemas_dir, errors)
    _validate_unique_ids(graph, errors)
    _validate_references_and_years(graph, errors)
    _validate_document_classes(graph, errors)
    _validate_frontier_registry(graph, schemas_dir, errors)
    _validate_flow_dispositions(graph, schemas_dir, errors)
    _validate_tables(graph, errors)
    _validate_intake_inventory(graph, schemas_dir, errors)
    _validate_no_inline_magic_numbers(graph, errors)
    _validate_field_grid_completeness(graph, field_grids, mef_line_inventory, errors)
    _validate_acyclic_dependencies(graph, errors)
    _validate_tax_table(graph, schemas_dir, errors)
    errors.extend(
        validate_field_maps(
            graph.year,
            graph.root,
            node_ids=(node.get("node_id", "") for node in graph.items("nodes")),
            frontier_ids=(entry.get("frontier_id", "") for entry in _load_frontier_entries(graph)),
            check_exposed_pdfs=True,
        )
    )
    errors.extend(validate_node_geometry(graph.year, graph.root))

    return ValidationResult(
        year=graph.year,
        counts=graph.counts(),
        jsonschema_enabled=HAVE_JSONSCHEMA,
        errors=errors,
    )


def validate_taxpayer_facts_document(
    facts_document: Mapping[str, Any],
    graph: LoadedGraph,
    *,
    schemas_dir: str | Path | None = None,
) -> list[str]:
    """Validate table-shaped taxpayer facts against a loaded graph.

    Scalar fact node references remain runtime inputs. Repeatable-table facts
    need graph context because their values are keyed by table column id.
    """

    errors: list[str] = []
    schema_root = Path(schemas_dir) if schemas_dir is not None else graph.root / "schemas"
    if HAVE_JSONSCHEMA:
        try:
            jsonschema.validate(dict(facts_document), load_yaml(schema_root / "taxpayer_facts.schema.json"))
        except jsonschema.ValidationError as exc:
            preview = json.dumps(facts_document, default=str)[:120]
            errors.append(f"[schema/taxpayer_facts] {exc.message} :: {preview}")

    tables = {table["table_id"]: table for table in graph.items("tables") if "table_id" in table}
    seen_dependent_keys: set[str] = set()
    for dependent in facts_document.get("dependents", []) or []:
        row_key = str(dependent.get("row_key", "<unknown>"))
        if row_key in seen_dependent_keys:
            errors.append(f"facts dependents row {row_key} -> duplicate row_key")
        seen_dependent_keys.add(row_key)
    for table_fact in facts_document.get("tables", []) or []:
        table_id = table_fact.get("table_id", "<unknown>")
        table = tables.get(table_id)
        if table is None:
            errors.append(f"facts table {table_id} -> missing table definition")
            continue
        columns = {column["column_id"]: column for column in table.get("columns", []) if "column_id" in column}
        input_columns = {column_id for column_id, column in columns.items() if column.get("kind") == "input"}
        computed_columns = {column_id for column_id, column in columns.items() if column.get("kind") == "computed"}
        seen_row_keys: set[str] = set()
        for row in table_fact.get("rows", []) or []:
            row_key = row.get("row_key", "<unknown>")
            if row_key in seen_row_keys:
                errors.append(f"facts table {table_id} row {row_key} -> duplicate row_key within table")
            seen_row_keys.add(row_key)
            for column_id in (row.get("columns") or {}):
                if column_id in computed_columns:
                    errors.append(
                        f"facts table {table_id} row {row_key} column {column_id} -> computed columns cannot be supplied"
                    )
                elif column_id not in input_columns:
                    errors.append(f"facts table {table_id} row {row_key} column {column_id} -> unknown input column")
    return errors


def _validate_schemas(graph: LoadedGraph, schemas_dir: Path, errors: list[str]) -> None:
    if not HAVE_JSONSCHEMA:
        return

    schemas = {
        schema_name: load_yaml(schemas_dir / f"{schema_name}.schema.json")
        for schema_name, _, _ in GRAPH_KINDS.values()
    }
    for subdir, (schema_name, _, _) in GRAPH_KINDS.items():
        for obj in graph.items(subdir):
            try:
                jsonschema.validate(obj, schemas[schema_name])
            except jsonschema.ValidationError as exc:
                preview = json.dumps(obj, default=str)[:120]
                errors.append(f"[schema/{subdir}] {exc.message} :: {preview}")


def _validate_unique_ids(graph: LoadedGraph, errors: list[str]) -> None:
    for subdir, (_, _, id_field) in GRAPH_KINDS.items():
        seen: set[str] = set()
        duplicates: set[str] = set()
        for obj in graph.items(subdir):
            obj_id = obj.get(id_field)
            if not obj_id:
                continue
            if obj_id in seen:
                duplicates.add(obj_id)
            seen.add(obj_id)
        for duplicate in sorted(duplicates):
            errors.append(f"{subdir} -> duplicate {id_field} {duplicate}")


def _validate_references_and_years(graph: LoadedGraph, errors: list[str]) -> None:
    expected_year = int(graph.year)
    documents = {doc["document_id"]: doc for doc in graph.items("documents") if "document_id" in doc}
    nodes = {node["node_id"]: node for node in graph.items("nodes") if "node_id" in node}
    rules = {rule["rule_id"]: rule for rule in graph.items("rules") if "rule_id" in rule}
    citations = {cite["citation_id"]: cite for cite in graph.items("citations") if "citation_id" in cite}
    frontier_entries = _load_frontier_entries(graph)

    for doc in graph.items("documents"):
        doc_id = doc.get("document_id", "<unknown>")
        if doc.get("tax_year") != expected_year:
            errors.append(f"document {doc_id} -> tax_year {doc.get('tax_year')} does not match graph {graph.year}")

    for node in graph.items("nodes"):
        node_id = node.get("node_id", "<unknown>")
        document_id = node.get("document_id")
        if document_id not in documents:
            errors.append(f"node {node_id} -> missing document {document_id}")
        elif documents[document_id].get("tax_year") != expected_year:
            errors.append(f"node {node_id} -> document {document_id} is outside tax year {graph.year}")
        _check_citation_refs("node", node_id, node.get("citation_refs", []), citations, errors)

    for edge in graph.items("edges"):
        edge_id = edge.get("edge_id", "<unknown>")
        source = edge.get("source")
        target = edge.get("target")
        if source not in nodes:
            if not _frontier_allows_edge(edge, missing_node=source, missing_side="source", graph=graph, frontier_entries=frontier_entries):
                errors.append(f"edge {edge_id} -> missing source {source}")
        if target not in nodes:
            if not _frontier_allows_edge(edge, missing_node=target, missing_side="target", graph=graph, frontier_entries=frontier_entries):
                errors.append(f"edge {edge_id} -> missing target {target}")
        if source in nodes and target in nodes:
            source_year = _node_tax_year(nodes[source], documents)
            target_year = _node_tax_year(nodes[target], documents)
            if source_year != expected_year or target_year != expected_year:
                errors.append(f"edge {edge_id} -> crosses outside tax year {graph.year}")
        rule_id = edge.get("rule_id")
        if rule_id and rule_id not in rules:
            errors.append(f"edge {edge_id} -> missing rule {rule_id}")
        _check_citation_refs("edge", edge_id, edge.get("citation_refs", []), citations, errors)

    for citation in graph.items("citations"):
        citation_id = citation.get("citation_id", "<unknown>")
        document_id = citation.get("document_id")
        if document_id not in documents:
            errors.append(f"citation {citation_id} -> missing document {document_id}")
        elif documents[document_id].get("tax_year") != expected_year:
            errors.append(f"citation {citation_id} -> document {document_id} is outside tax year {graph.year}")

    for decision in graph.items("decisions"):
        decision_id = decision.get("decision_id", "<unknown>")
        _check_citation_refs("decision", decision_id, decision.get("citation_refs", []), citations, errors)

    for routing in graph.items("routing_edges"):
        routing_id = routing.get("routing_id", "<unknown>")
        _check_citation_refs("routing_edge", routing_id, routing.get("citation_refs", []), citations, errors)
        if routing.get("status") == "modeled" and routing.get("target") not in nodes:
            errors.append(f"routing_edge {routing_id} -> missing target {routing.get('target')}")

    for trigger in graph.items("triggers"):
        trigger_id = trigger.get("trigger_id", "<unknown>")
        _check_citation_refs("trigger", trigger_id, trigger.get("citation_refs", []), citations, errors)
        if trigger.get("status", "modeled") == "modeled" and trigger.get("entry_point") not in nodes:
            errors.append(f"trigger {trigger_id} -> missing entry_point {trigger.get('entry_point')}")

    for expectation in graph.items("expectations"):
        expectation_id = expectation.get("expectation_id", "<unknown>")
        _check_citation_refs("expectation", expectation_id, expectation.get("citation_refs", []), citations, errors)


def _validate_document_classes(graph: LoadedGraph, errors: list[str]) -> None:
    """Require every document to carry a valid role-axis class."""
    allowed = set(DOCUMENT_CLASSES)
    for document in graph.items("documents"):
        document_id = str(document.get("document_id", "<unknown>"))
        document_class = document.get("document_class")
        if not document_class:
            errors.append(f"document {document_id} -> missing document_class")
        elif document_class not in allowed:
            errors.append(
                f"document {document_id} -> invalid document_class {document_class}; "
                f"expected one of {', '.join(DOCUMENT_CLASSES)}"
            )


def _validate_frontier_registry(graph: LoadedGraph, schemas_dir: Path, errors: list[str]) -> None:
    registry_path = graph.graph_dir / "frontier.yaml"
    if not registry_path.exists():
        return
    registry = load_yaml(registry_path)
    if HAVE_JSONSCHEMA:
        try:
            jsonschema.validate(registry, load_yaml(schemas_dir / "frontier.schema.json"))
        except jsonschema.ValidationError as exc:
            preview = json.dumps(registry, default=str)[:120]
            errors.append(f"[schema/frontier] {exc.message} :: {preview}")
    citations = {cite["citation_id"] for cite in graph.items("citations") if "citation_id" in cite}
    seen: set[str] = set()
    for entry in registry.get("frontiers", []) or []:
        frontier_id = entry.get("frontier_id", "<unknown>")
        if frontier_id in seen:
            errors.append(f"frontier -> duplicate frontier_id {frontier_id}")
        seen.add(frontier_id)
        if not entry.get("target_url"):
            errors.append(f"frontier {frontier_id} -> missing target_url")
        citation_ref = entry.get("citation_ref")
        if not citation_ref:
            errors.append(f"frontier {frontier_id} -> missing citation_ref")
        elif citation_ref not in citations:
            errors.append(f"frontier {frontier_id} -> missing citation {citation_ref}")


def _load_frontier_entries(graph: LoadedGraph) -> list[dict[str, Any]]:
    registry_path = graph.graph_dir / "frontier.yaml"
    if not registry_path.exists():
        return []
    registry = load_yaml(registry_path) or {}
    return list(registry.get("frontiers", []) or [])


def _validate_flow_dispositions(graph: LoadedGraph, schemas_dir: Path, errors: list[str]) -> None:
    path = graph.graph_dir / "flow-dispositions.yaml"
    if not path.exists():
        return
    payload = load_yaml(path)
    if HAVE_JSONSCHEMA:
        try:
            jsonschema.validate(payload, load_yaml(schemas_dir / "flow_dispositions.schema.json"))
        except jsonschema.ValidationError as exc:
            preview = json.dumps(payload, default=str)[:120]
            errors.append(f"[schema/flow_dispositions] {exc.message} :: {preview}")
    seen: set[str] = set()
    for entry in payload.get("entries", []) or []:
        flow_id = str(entry.get("flow_id", "<unknown>"))
        if flow_id in seen:
            errors.append(f"flow dispositions -> duplicate flow_id {flow_id}")
        seen.add(flow_id)


def _frontier_allows_edge(
    edge: Mapping[str, Any],
    *,
    missing_node: Any,
    missing_side: str,
    graph: LoadedGraph,
    frontier_entries: list[dict[str, Any]],
) -> bool:
    missing = str(missing_node)
    nodes = {node["node_id"] for node in graph.items("nodes") if "node_id" in node}
    for entry in frontier_entries:
        if entry.get("status") == "modeled":
            continue
        if not entry.get("target_url") or not entry.get("citation_ref"):
            continue
        source = entry.get("source") or {}
        target = entry.get("target") or {}
        if target.get("node_id") == missing or source.get("node_id") == missing:
            return True
        if missing_side == "target" and edge.get("source") == source.get("node_id"):
            doc_id, line = _infer_document_line(missing, graph)
            if doc_id == target.get("document_id") and line == str(target.get("line")):
                return True
        if missing_side == "source" and edge.get("target") in nodes:
            doc_id, line = _infer_document_line(missing, graph)
            if doc_id == target.get("document_id") and line == str(target.get("line")):
                return True
    return False


def _infer_document_line(node_id: str, graph: LoadedGraph) -> tuple[str | None, str | None]:
    document_ids = sorted(
        [doc["document_id"] for doc in graph.items("documents") if "document_id" in doc],
        key=len,
        reverse=True,
    )
    document_id = next((candidate for candidate in document_ids if node_id.startswith(candidate)), None)
    match = re.search(r"_line_([0-9]+[a-z]?)", node_id, flags=re.IGNORECASE)
    line = match.group(1).lower() if match else None
    return document_id, line


def _validate_tables(graph: LoadedGraph, errors: list[str]) -> None:
    documents = {doc["document_id"]: doc for doc in graph.items("documents") if "document_id" in doc}
    nodes = {node["node_id"]: node for node in graph.items("nodes") if "node_id" in node}
    citations = {cite["citation_id"]: cite for cite in graph.items("citations") if "citation_id" in cite}
    for table in graph.items("tables"):
        table_id = table.get("table_id", "<unknown>")
        document_id = table.get("document_id")
        if document_id not in documents:
            errors.append(f"table {table_id} -> missing document {document_id}")
        _check_citation_refs("table", table_id, table.get("citation_refs", []), citations, errors)
        columns = table.get("columns", []) or []
        totals = table.get("totals", []) or []
        column_ids = _duplicate_values(columns, "column_id")
        for duplicate in column_ids:
            errors.append(f"table {table_id} -> duplicate column_id {duplicate}")
        total_column_ids = _duplicate_values(totals, "column_id")
        for duplicate in total_column_ids:
            errors.append(f"table {table_id} -> duplicate total column_id {duplicate}")

        row_columns = {column.get("column_id") for column in columns}
        for column in columns:
            column_id = column.get("column_id", "<unknown>")
            node_id = column.get("template_node")
            _validate_table_member(
                table_id=table_id,
                column_id=column_id,
                node_id=node_id,
                expected_role="row_template",
                expected_document=document_id,
                nodes=nodes,
                errors=errors,
                owner=f"column {column_id}",
            )
        for total in totals:
            column_id = total.get("column_id", "<unknown>")
            if column_id not in row_columns:
                errors.append(f"table {table_id} total {column_id} -> total column is not a row column")
            _validate_table_member(
                table_id=table_id,
                column_id=column_id,
                node_id=total.get("total_node"),
                expected_role="total",
                expected_document=document_id,
                nodes=nodes,
                errors=errors,
                owner=f"total {column_id}",
            )


def _validate_intake_inventory(graph: LoadedGraph, schemas_dir: Path, errors: list[str]) -> None:
    """Enforce both-direction completeness for the bounded intake inventory."""
    path = graph.graph_dir / "intake-inventory.yaml"
    if not path.exists():
        return
    payload = load_yaml(path) or {}
    if HAVE_JSONSCHEMA:
        try:
            jsonschema.validate(payload, load_yaml(schemas_dir / "intake_inventory.schema.json"))
        except jsonschema.ValidationError as exc:
            preview = json.dumps(payload, default=str)[:120]
            errors.append(f"[schema/intake_inventory] {exc.message} :: {preview}")

    expected_routes: set[tuple[str, str]] = set()
    for document in payload.get("information_returns", []) or []:
        document_type = str(document.get("document_type", ""))
        boxes = document.get("boxes", []) or []
        for box in boxes:
            key = (document_type, str(box.get("box_id", "")))
            if key in expected_routes:
                errors.append(f"intake inventory -> duplicate box {document_type}/{key[1]}")
            expected_routes.add(key)

    actual_routes: dict[tuple[str, str], list[dict[str, Any]]] = {}
    bounded_types = {document_type for document_type, _box_id in expected_routes}
    for route in graph.items("routing_edges"):
        key = (str(route.get("source_document_type", "")), str(route.get("source_box", "")))
        if key[0] in bounded_types:
            actual_routes.setdefault(key, []).append(route)
    for key in sorted(expected_routes):
        count = len(actual_routes.get(key, []))
        if count != 1:
            errors.append(
                f"intake inventory -> {key[0]}/{key[1]} has {count} routing entries; expected exactly one"
            )
    for key in sorted(set(actual_routes) - expected_routes):
        errors.append(f"intake routing -> {key[0]}/{key[1]} is absent from the inventory")

    expected_triggers: set[str] = set()
    for item in payload.get("trigger_items", []) or []:
        trigger_id = str(item.get("trigger_id", ""))
        if trigger_id in expected_triggers:
            errors.append(f"intake inventory -> duplicate trigger {trigger_id}")
        expected_triggers.add(trigger_id)
    actual_triggers = {
        str(trigger.get("trigger_id", "")): trigger
        for trigger in graph.items("triggers")
    }
    for trigger_id in sorted(expected_triggers):
        if trigger_id not in actual_triggers:
            errors.append(f"intake inventory -> missing trigger record {trigger_id}")
    for trigger_id in sorted(set(actual_triggers) - expected_triggers):
        errors.append(f"intake trigger -> {trigger_id} is absent from the bounded inventory")


def _validate_table_member(
    *,
    table_id: str,
    column_id: str,
    node_id: Any,
    expected_role: str,
    expected_document: Any,
    nodes: dict[str, dict[str, Any]],
    errors: list[str],
    owner: str,
) -> None:
    node = nodes.get(node_id)
    if node is None:
        errors.append(f"table {table_id} {owner} -> missing node {node_id}")
        return
    if node.get("table_id") != table_id:
        errors.append(f"table {table_id} {owner} -> node {node_id} has table_id {node.get('table_id')}")
    if node.get("column") != column_id:
        errors.append(f"table {table_id} {owner} -> node {node_id} has column {node.get('column')}")
    if node.get("role") != expected_role:
        errors.append(f"table {table_id} {owner} -> node {node_id} has role {node.get('role')}")
    if expected_document and node.get("document_id") != expected_document:
            errors.append(f"table {table_id} {owner} -> node {node_id} belongs to document {node.get('document_id')}")


_STRUCTURAL_NUMERIC_PARAMETER_KEYS = {
    "increment",
    "precision",
    "scale",
}


def _validate_no_inline_magic_numbers(graph: LoadedGraph, errors: list[str]) -> None:
    """Flag IRS-sourced numeric constants embedded directly in rule parameters."""
    for rule in graph.items("rules"):
        rule_id = rule.get("rule_id", "<unknown>")
        _check_parameter_value(
            rule_id=rule_id,
            path=("parameters",),
            key=None,
            value=rule.get("parameters", {}),
            errors=errors,
        )


def _validate_field_grid_completeness(
    graph: LoadedGraph,
    field_grids: Mapping[str, Mapping[str, Any]] | None,
    mef_line_inventory: Mapping[str, list[str]] | None,
    errors: list[str],
) -> None:
    if not field_grids and not mef_line_inventory:
        return
    report = check_loaded_graph_field_completeness(
        graph,
        field_grids or {},
        mef_line_inventory=mef_line_inventory,
    )
    for issue in report.issues:
        errors.append(f"field grid {issue.document_id}/{issue.field_name} -> {issue.reason}")


def _check_parameter_value(
    *,
    rule_id: str,
    path: tuple[str, ...],
    key: str | None,
    value: Any,
    errors: list[str],
) -> None:
    if isinstance(value, Mapping):
        for child_key, child_value in value.items():
            _check_parameter_value(
                rule_id=rule_id,
                path=path + (str(child_key),),
                key=str(child_key),
                value=child_value,
                errors=errors,
            )
        return
    if isinstance(value, list):
        for index, child_value in enumerate(value):
            _check_parameter_value(
                rule_id=rule_id,
                path=path + (str(index),),
                key=key,
                value=child_value,
                errors=errors,
            )
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return
    if key in _STRUCTURAL_NUMERIC_PARAMETER_KEYS:
        return
    dotted_path = ".".join(path)
    errors.append(
        f"rule {rule_id} -> inline numeric parameter at {dotted_path}: "
        f"{value} must be a cited parameter node"
    )


def _duplicate_values(objects: list[dict[str, Any]], field: str) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for obj in objects:
        value = obj.get(field)
        if not value:
            continue
        if value in seen:
            duplicates.add(str(value))
        seen.add(value)
    return sorted(duplicates)


def _check_citation_refs(
    owner_kind: str,
    owner_id: str,
    citation_refs: list[str],
    citations: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    for citation_ref in citation_refs:
        if citation_ref not in citations:
            errors.append(f"{owner_kind} {owner_id} -> missing citation {citation_ref}")


def _node_tax_year(node: dict[str, Any], documents: dict[str, dict[str, Any]]) -> int | None:
    document = documents.get(node.get("document_id"))
    return document.get("tax_year") if document else None


def _validate_acyclic_dependencies(graph: LoadedGraph, errors: list[str]) -> None:
    nodes = {node["node_id"] for node in graph.items("nodes") if "node_id" in node}
    adjacency: dict[str, list[str]] = {node_id: [] for node_id in nodes}
    for edge in graph.items("edges"):
        source = edge.get("source")
        target = edge.get("target")
        if source in nodes and target in nodes:
            adjacency[source].append(target)

    visiting: set[str] = set()
    visited: set[str] = set()
    path: list[str] = []
    cycles: set[tuple[str, ...]] = set()

    def visit(node_id: str) -> None:
        if node_id in visited:
            return
        if node_id in visiting:
            start = path.index(node_id)
            cycle = tuple(path[start:] + [node_id])
            cycles.add(cycle)
            return

        visiting.add(node_id)
        path.append(node_id)
        for next_node in adjacency.get(node_id, []):
            visit(next_node)
        path.pop()
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in sorted(nodes):
        visit(node_id)

    for cycle in sorted(cycles):
        errors.append("dependency cycle detected: " + " -> ".join(cycle))


def _validate_tax_table(graph: LoadedGraph, schemas_dir: Path, errors: list[str]) -> None:
    path = graph.graph_dir / "tax_table.json"
    if not path.exists():
        errors.append(f"tax table -> missing compiled data resource: {path}")
        return
    try:
        data = load_yaml(path)
    except Exception as exc:
        errors.append(f"tax table -> failed to load JSON/YAML: {exc}")
        return
    if HAVE_JSONSCHEMA:
        try:
            jsonschema.validate(data, load_yaml(schemas_dir / "tax_table.schema.json"))
        except jsonschema.ValidationError as exc:
            preview = json.dumps(data, default=str)[:120]
            errors.append(f"[schema/tax_table] {exc.message} :: {preview}")
