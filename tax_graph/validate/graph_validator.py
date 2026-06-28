"""Validate authored Tax Graph YAML.

Validation has two layers: JSON Schema checks for each object and graph-level
integrity checks that JSON Schema cannot express, such as unique ids,
cross-reference resolution, tax-year consistency, and dependency cycles.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from tax_graph.io.loader import GRAPH_KINDS, LoadedGraph, load_graph, load_yaml

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


def validate_graph(year: str | int = "2025", root: str | Path | None = None) -> ValidationResult:
    """Validate schema conformance and graph integrity for one tax year."""
    graph = load_graph(year, root)
    schemas_dir = graph.root / "schemas"
    errors: list[str] = []

    _validate_schemas(graph, schemas_dir, errors)
    _validate_unique_ids(graph, errors)
    _validate_references_and_years(graph, errors)
    _validate_acyclic_dependencies(graph, errors)

    return ValidationResult(
        year=graph.year,
        counts=graph.counts(),
        jsonschema_enabled=HAVE_JSONSCHEMA,
        errors=errors,
    )


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
            errors.append(f"edge {edge_id} -> missing source {source}")
        if target not in nodes:
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
