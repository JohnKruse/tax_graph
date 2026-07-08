"""Both-direction field-grid completeness checks.

The field grid is authoritative geometry from the AcroForm itself. This module
checks direction two of the structural ladder: every entry field is either
mapped to a graph node/table column or explicitly recorded as not modeled.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence

from tax_graph.io.loader import LoadedGraph


@dataclass(frozen=True)
class CompletenessIssue:
    """One unmapped AcroForm field."""

    document_id: str
    field_name: str
    reason: str


@dataclass(frozen=True)
class CompletenessReport:
    """Completeness result for one or more documents."""

    issues: tuple[CompletenessIssue, ...]

    @property
    def ok(self) -> bool:
        """Return whether every field was mapped or explicitly not modeled."""
        return not self.issues


def check_loaded_graph_field_completeness(
    graph: LoadedGraph,
    field_grids: Mapping[str, Mapping[str, Any]],
    mef_line_inventory: Mapping[str, Sequence[str]] | None = None,
) -> CompletenessReport:
    """Check field-grid completeness for authored graph documents."""
    documents = {doc["document_id"]: doc for doc in graph.items("documents") if "document_id" in doc}
    nodes = list(graph.items("nodes"))
    tables = list(graph.items("tables"))
    issues: list[CompletenessIssue] = []
    for document_id, fields in field_grids.items():
        document = documents.get(document_id, {})
        report = check_field_grid_completeness(
            document_id=document_id,
            fields=fields,
            nodes=nodes,
            tables=tables,
            not_modeled_fields=document.get("not_modeled_fields", []) or [],
        )
        issues.extend(report.issues)
    for document_id, line_anchors in (mef_line_inventory or {}).items():
        document = documents.get(document_id, {})
        issues.extend(
            _mef_inventory_issues(
                document_id=document_id,
                line_anchors=line_anchors,
                nodes=nodes,
                not_modeled_fields=document.get("not_modeled_fields", []) or [],
            )
        )
    return CompletenessReport(tuple(issues))


def check_field_grid_completeness(
    *,
    document_id: str,
    fields: Mapping[str, Any] | None,
    nodes: Sequence[Mapping[str, Any]],
    tables: Sequence[Mapping[str, Any]] = (),
    not_modeled_fields: Sequence[Mapping[str, Any]] = (),
) -> CompletenessReport:
    """Check one document's AcroForm fields against nodes and not-modeled records."""
    if not fields:
        return CompletenessReport(())
    context = _MappingContext(document_id=document_id, fields=fields, nodes=nodes, tables=tables)
    issues: list[CompletenessIssue] = []
    for field in fields.get("fields", []) or []:
        field_name = str(field.get("field_name", ""))
        if not field_name:
            continue
        parsed = _parse_field(field, context)
        if _field_maps_to_node(parsed, context):
            continue
        if _field_is_not_modeled(parsed, not_modeled_fields):
            continue
        issues.append(
            CompletenessIssue(
                document_id=document_id,
                field_name=field_name,
                reason=_unmapped_reason(parsed),
            )
        )
    return CompletenessReport(tuple(issues))


@dataclass(frozen=True)
class _MappingContext:
    document_id: str
    fields: Mapping[str, Any]
    nodes: Sequence[Mapping[str, Any]]
    tables: Sequence[Mapping[str, Any]]


@dataclass(frozen=True)
class _ParsedField:
    field: Mapping[str, Any]
    field_name: str
    line_anchor: str
    table_part: str | None
    table_line: str | None
    table_column: str | None


def _parse_field(field: Mapping[str, Any], context: _MappingContext) -> _ParsedField:
    field_name = str(field.get("field_name", ""))
    table_part, table_line = _table_part_line(field_name)
    table_column = None
    if table_part and table_line:
        table_column = _table_column(field, context)
    return _ParsedField(
        field=field,
        field_name=field_name,
        line_anchor=str(field.get("line_anchor", "")).lower(),
        table_part=table_part,
        table_line=table_line,
        table_column=table_column,
    )


def _field_maps_to_node(parsed: _ParsedField, context: _MappingContext) -> bool:
    if parsed.table_part and parsed.table_line and parsed.table_column:
        return _table_field_maps_to_node(parsed, context)
    if parsed.line_anchor and not _addressable_anchor(parsed.line_anchor):
        return True
    if parsed.line_anchor:
        return any(
            node.get("document_id") == context.document_id and _node_mentions_line(node, parsed.line_anchor)
            for node in context.nodes
        )
    return False


def _table_field_maps_to_node(parsed: _ParsedField, context: _MappingContext) -> bool:
    table = _matching_table(parsed, context)
    if table is None:
        return False
    template_node = None
    for column in table.get("columns", []) or []:
        if column.get("column_id") == parsed.table_column:
            template_node = column.get("template_node")
            break
    if not template_node:
        return False
    return any(node.get("node_id") == template_node for node in context.nodes)


def _matching_table(parsed: _ParsedField, context: _MappingContext) -> Mapping[str, Any] | None:
    wanted_part = _roman_part(parsed.table_part)
    for table in context.tables:
        if table.get("document_id") != context.document_id:
            continue
        line_anchor = str(table.get("line_anchor", "")).lower()
        if f"part {wanted_part}" in line_anchor and f"line {parsed.table_line}" in line_anchor:
            return table
    return None


def _field_is_not_modeled(
    parsed: _ParsedField,
    records: Sequence[Mapping[str, Any]],
) -> bool:
    for record in records:
        if _not_modeled_record_matches(parsed, record):
            return True
    return False


def _not_modeled_record_matches(parsed: _ParsedField, record: Mapping[str, Any]) -> bool:
    field_name = record.get("field_name")
    if field_name and parsed.field_name == field_name:
        return True
    pattern = record.get("field_name_pattern")
    if pattern and re.search(str(pattern), parsed.field_name):
        return True
    line_anchor = str(record.get("line_anchor", "")).lower()
    if line_anchor and parsed.line_anchor == line_anchor:
        return True
    table_columns = {str(column).lower() for column in record.get("table_columns", []) or []}
    if parsed.table_column and parsed.table_column in table_columns:
        return True
    return False


def _mef_inventory_issues(
    *,
    document_id: str,
    line_anchors: Sequence[str],
    nodes: Sequence[Mapping[str, Any]],
    not_modeled_fields: Sequence[Mapping[str, Any]],
) -> list[CompletenessIssue]:
    issues: list[CompletenessIssue] = []
    for line_anchor in line_anchors:
        anchor = str(line_anchor).lower()
        if any(node.get("document_id") == document_id and _node_mentions_line(node, anchor) for node in nodes):
            continue
        parsed = _ParsedField(
            field={"line_anchor": anchor},
            field_name=f"mef_line_{anchor}",
            line_anchor=anchor,
            table_part=None,
            table_line=None,
            table_column=None,
        )
        if _field_is_not_modeled(parsed, not_modeled_fields):
            continue
        issues.append(
            CompletenessIssue(
                document_id=document_id,
                field_name=f"mef_line_{anchor}",
                reason=f"MeF line inventory line {anchor} has no node or not_modeled record",
            )
        )
    return issues


def _unmapped_reason(parsed: _ParsedField) -> str:
    if parsed.table_part and parsed.table_line:
        column = parsed.table_column or "unknown"
        return f"AcroForm table field has no node or not_modeled record for column {column}"
    if parsed.line_anchor:
        return f"AcroForm field line {parsed.line_anchor} has no node or not_modeled record"
    return "AcroForm field has no line/table mapping or not_modeled record"


_TABLE_RE = re.compile(r"Table_Line(?P<line>[0-9]+)_Part(?P<part>[0-9]+)", re.IGNORECASE)


def _table_part_line(field_name: str) -> tuple[str | None, str | None]:
    match = _TABLE_RE.search(field_name)
    if not match:
        return None, None
    return match.group("part"), match.group("line")


def _table_column(field: Mapping[str, Any], context: _MappingContext) -> str | None:
    table_part, table_line = _table_part_line(str(field.get("field_name", "")))
    if not table_part or not table_line:
        return None
    x_cluster = field.get("x_cluster")
    clusters = sorted(
        {
            item.get("x_cluster")
            for item in context.fields.get("fields", []) or []
            if _table_part_line(str(item.get("field_name", ""))) == (table_part, table_line)
            and item.get("x_cluster") is not None
        }
    )
    if x_cluster not in clusters:
        return None
    index = clusters.index(x_cluster)
    if index >= 26:
        return None
    return chr(ord("a") + index)


def _roman_part(part: str | None) -> str:
    return {"1": "i", "2": "ii"}.get(str(part), str(part).lower())


def _node_mentions_line(node: Mapping[str, Any], anchor: str) -> bool:
    normalized = anchor.lower().replace("-", "_")
    haystacks = [
        str(node.get("node_id", "")).lower(),
        str(node.get("label", "")).lower(),
        str(node.get("description", "")).lower(),
    ]
    return any(f"line_{normalized}" in value or f"line {anchor}" in value for value in haystacks)


def _addressable_anchor(anchor: str) -> bool:
    return any(ch.isdigit() for ch in anchor)
