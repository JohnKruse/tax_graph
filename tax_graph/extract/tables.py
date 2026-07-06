"""Deterministic repeatable-table grouping for outline-first extraction."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import re
from typing import Any

from tax_graph.extract.models import DraftObject, SourceDocumentInput
from tax_graph.extract.outline import OutlineNode, OutlineTree


COLUMN_RE = re.compile(r"\(([a-z])\)", re.IGNORECASE)
ROW_FIELD_RE = re.compile(
    r"Table_Line(?P<line>[0-9]+)_Part(?P<part>[0-9]+)\[\d+\]\.Row(?P<row>[0-9]+)",
    re.IGNORECASE,
)
ROW_COLUMN_RE = re.compile(r"_column_([a-z])$")
TOTAL_COLUMN_RE = re.compile(r"_line_2_column_([a-z])_total$")


@dataclass(frozen=True)
class FieldTableGeometry:
    """Repeated physical row-band signal from the AcroForm field grid."""

    part: str
    line_anchor: str
    row_count: int
    columns: tuple[str, ...]
    repeated: bool


def assemble_table_subunits(
    document: SourceDocumentInput,
    outline: OutlineTree,
    objects: list[DraftObject],
    *,
    model: str = "deterministic-table-detector",
) -> list[DraftObject]:
    """Emit repeatable-table objects when geometry and totals cue agree.

    The detector is deliberately conservative: repeated row geometry alone is
    not enough, and a totals cue that does not reconcile with row-template
    columns flags the related draft objects instead of emitting a table.
    """

    geometries = _field_table_geometries(document)
    tables: list[DraftObject] = []
    for section, row_node, totals_node in _table_candidates(outline.children):
        part = section.outline_id if section else _part_for_page(row_node.page)
        geometry = geometries.get((part, str(row_node.line_anchor or "")))
        if geometry is None or not geometry.repeated:
            continue

        related_outline_ids = [row_node.outline_id]
        if totals_node:
            related_outline_ids.append(totals_node.outline_id)
        if totals_node is None:
            _flag_related_objects(
                objects,
                document_id=document.document_id,
                outline_ids=related_outline_ids,
                reason="repeatable table geometry has no resolvable totals cue",
            )
            continue

        table = _assemble_one_table(
            document=document,
            section=section,
            row_node=row_node,
            totals_node=totals_node,
            geometry=geometry,
            objects=objects,
            model=model,
        )
        if table is not None:
            tables.append(table)
    return tables


def _assemble_one_table(
    *,
    document: SourceDocumentInput,
    section: OutlineNode | None,
    row_node: OutlineNode,
    totals_node: OutlineNode,
    geometry: FieldTableGeometry,
    objects: list[DraftObject],
    model: str,
) -> DraftObject | None:
    node_objects = {obj.object_id: obj for obj in objects if obj.kind == "nodes"}
    row_columns = _row_template_columns(document.document_id, row_node.outline_id, node_objects)
    cue_columns = _cue_columns(totals_node.label)
    total_nodes = _total_nodes(document.document_id, totals_node.outline_id, node_objects)

    expected_columns = set(row_columns)
    cue_column_set = set(cue_columns)
    geometry_columns = set(geometry.columns)
    missing_from_cue = expected_columns - cue_column_set
    extra_in_cue = cue_column_set - expected_columns
    missing_from_grid = cue_column_set - geometry_columns
    missing_total_nodes = cue_column_set - set(total_nodes)

    if not row_columns:
        _flag_related_objects(
            objects,
            document_id=document.document_id,
            outline_ids=[row_node.outline_id, totals_node.outline_id],
            reason="repeatable table row-template columns were not resolved",
        )
        return None
    if missing_from_cue or extra_in_cue or missing_from_grid or missing_total_nodes:
        details = []
        if missing_from_cue:
            details.append("missing cue columns " + ",".join(sorted(missing_from_cue)))
        if extra_in_cue:
            details.append("unexpected cue columns " + ",".join(sorted(extra_in_cue)))
        if missing_from_grid:
            details.append("cue columns absent from field grid " + ",".join(sorted(missing_from_grid)))
        if missing_total_nodes:
            details.append("missing total nodes " + ",".join(sorted(missing_total_nodes)))
        _flag_related_objects(
            objects,
            document_id=document.document_id,
            outline_ids=[row_node.outline_id, totals_node.outline_id],
            reason="repeatable table totals cue mismatch: " + "; ".join(details),
        )
        return None

    table_id = _slug(f"{document.document_id}_{row_node.outline_id}")
    _mark_row_template_nodes(
        objects,
        document_id=document.document_id,
        outline_id=row_node.outline_id,
        table_id=table_id,
        row_columns=row_columns,
    )
    _mark_total_nodes(total_nodes, table_id=table_id)

    ordered_columns = [column for column in _column_order(row_node, geometry) if column in row_columns]
    citation_refs = _citation_refs_for_outlines(
        objects,
        document_id=document.document_id,
        outline_ids=[row_node.outline_id, totals_node.outline_id],
    )
    source_span = _source_span_for_outlines(
        objects,
        document_id=document.document_id,
        outline_ids=[row_node.outline_id, totals_node.outline_id],
    )
    return DraftObject(
        "tables",
        {
            "table_id": table_id,
            "document_id": document.document_id,
            "line_anchor": _line_anchor_label(section, row_node),
            "columns": [
                {
                    "column_id": column,
                    "label": f"Column ({column})",
                    "kind": "computed" if row_columns[column].data.get("node_type") == "computed" else "input",
                    "template_node": row_columns[column].object_id,
                }
                for column in ordered_columns
            ],
            "totals": [
                {"column_id": column, "total_node": total_nodes[column].object_id}
                for column in ordered_columns
                if column in total_nodes
            ],
            **({"citation_refs": citation_refs} if citation_refs else {}),
            "description": f"Repeatable table detected from {geometry.row_count} printed row slots and totals cue.",
        },
        source_span,
        model,
        1.0,
    )


def _field_table_geometries(document: SourceDocumentInput) -> dict[tuple[str, str], FieldTableGeometry]:
    rows: dict[tuple[str, str], dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    for field in (document.fields or {}).get("fields", []):
        match = ROW_FIELD_RE.search(str(field.get("field_name", "")))
        if not match:
            continue
        key = (_part_id(int(match.group("part"))), match.group("line"))
        rows[key][int(match.group("row"))].append(int(field.get("x_cluster", 0)))

    geometries: dict[tuple[str, str], FieldTableGeometry] = {}
    for (part, line_anchor), row_fields in rows.items():
        signatures = [tuple(sorted(set(values))) for _row, values in sorted(row_fields.items()) if values]
        signature_counts = Counter(signatures)
        repeated_signature, repeated_count = signature_counts.most_common(1)[0]
        columns = tuple(chr(ord("a") + index) for index, _value in enumerate(repeated_signature))
        geometries[(part, line_anchor)] = FieldTableGeometry(
            part=part,
            line_anchor=line_anchor,
            row_count=len(signatures),
            columns=columns,
            repeated=repeated_count >= 2,
        )
    return geometries


def _table_candidates(
    nodes: list[OutlineNode],
    *,
    parent: OutlineNode | None = None,
) -> list[tuple[OutlineNode | None, OutlineNode, OutlineNode | None]]:
    candidates: list[tuple[OutlineNode | None, OutlineNode, OutlineNode | None]] = []
    for index, node in enumerate(nodes):
        if node.kind == "transaction_table":
            candidates.append((parent, node, _following_totals_node(nodes, index)))
        if node.children:
            candidates.extend(_table_candidates(node.children, parent=node))
    return candidates


def _following_totals_node(siblings: list[OutlineNode], row_index: int) -> OutlineNode | None:
    for sibling in siblings[row_index + 1 :]:
        if sibling.kind == "totals":
            return sibling
        if sibling.kind == "transaction_table":
            return None
    return None


def _row_template_columns(
    document_id: str,
    outline_id: str,
    node_objects: dict[str, DraftObject],
) -> dict[str, DraftObject]:
    prefix = _slug(f"{document_id}_{outline_id}") + "_"
    columns: dict[str, DraftObject] = {}
    for obj in node_objects.values():
        if not obj.object_id.startswith(prefix):
            continue
        match = ROW_COLUMN_RE.search(obj.object_id)
        if match:
            columns[match.group(1)] = obj
    return columns


def _total_nodes(
    document_id: str,
    outline_id: str,
    node_objects: dict[str, DraftObject],
) -> dict[str, DraftObject]:
    prefix = _slug(f"{document_id}_{outline_id}") + "_"
    totals: dict[str, DraftObject] = {}
    for obj in node_objects.values():
        if not obj.object_id.startswith(prefix):
            continue
        match = TOTAL_COLUMN_RE.search(obj.object_id)
        if match:
            totals[match.group(1)] = obj
    return totals


def _cue_columns(label: str) -> list[str]:
    if "add" not in label.lower() or "amount" not in label.lower():
        return []
    return _unique(match.group(1).lower() for match in COLUMN_RE.finditer(label))


def _column_order(row_node: OutlineNode, geometry: FieldTableGeometry) -> list[str]:
    return _unique([*geometry.columns, *row_node.columns])


def _mark_row_template_nodes(
    objects: list[DraftObject],
    *,
    document_id: str,
    outline_id: str,
    table_id: str,
    row_columns: dict[str, DraftObject],
) -> None:
    prefix = _slug(f"{document_id}_{outline_id}") + "_"
    for obj in objects:
        if obj.kind != "nodes" or not obj.object_id.startswith(prefix):
            continue
        column = _single_letter_column(obj.object_id)
        obj.data["table_id"] = table_id
        obj.data["role"] = "row_template"
        obj.data["column"] = column if column in row_columns else _column_suffix(obj.object_id)


def _mark_total_nodes(total_nodes: dict[str, DraftObject], *, table_id: str) -> None:
    for column, obj in total_nodes.items():
        obj.data["table_id"] = table_id
        obj.data["column"] = column
        obj.data["role"] = "total"


def _single_letter_column(node_id: str) -> str | None:
    match = ROW_COLUMN_RE.search(node_id)
    return match.group(1) if match else None


def _column_suffix(node_id: str) -> str:
    if "_column_" not in node_id:
        return "computed"
    return _slug(node_id.rsplit("_column_", 1)[1])


def _citation_refs_for_outlines(
    objects: list[DraftObject],
    *,
    document_id: str,
    outline_ids: list[str],
) -> list[str]:
    refs: set[str] = set()
    prefixes = [_slug(f"{document_id}_{outline_id}") + "_" for outline_id in outline_ids]
    for obj in objects:
        if not any(obj.object_id.startswith(prefix) for prefix in prefixes):
            continue
        refs.update(str(ref) for ref in obj.data.get("citation_refs", []) or [])
    return sorted(refs)


def _source_span_for_outlines(
    objects: list[DraftObject],
    *,
    document_id: str,
    outline_ids: list[str],
) -> str:
    prefixes = [_slug(f"{document_id}_{outline_id}") + "_" for outline_id in outline_ids]
    spans = [
        obj.source_span
        for obj in objects
        if obj.source_span and any(obj.object_id.startswith(prefix) for prefix in prefixes)
    ]
    return "\n".join(_unique(spans))


def _flag_related_objects(
    objects: list[DraftObject],
    *,
    document_id: str,
    outline_ids: list[str],
    reason: str,
) -> None:
    prefixes = [_slug(f"{document_id}_{outline_id}") + "_" for outline_id in outline_ids]
    for obj in objects:
        if any(obj.object_id.startswith(prefix) for prefix in prefixes):
            obj.flag(reason)


def _line_anchor_label(section: OutlineNode | None, row_node: OutlineNode) -> str:
    section_label = section.label if section else ""
    if section_label:
        return f"{section_label} line {row_node.line_anchor}"
    return f"line {row_node.line_anchor}"


def _part_for_page(page: int | None) -> str:
    return _part_id(page or 1)


def _part_id(part_number: int) -> str:
    return "part_" + _roman(part_number)


def _roman(value: int) -> str:
    numerals = [
        (1000, "m"),
        (900, "cm"),
        (500, "d"),
        (400, "cd"),
        (100, "c"),
        (90, "xc"),
        (50, "l"),
        (40, "xl"),
        (10, "x"),
        (9, "ix"),
        (5, "v"),
        (4, "iv"),
        (1, "i"),
    ]
    remaining = value
    result = []
    for amount, numeral in numerals:
        while remaining >= amount:
            result.append(numeral)
            remaining -= amount
    return "".join(result) or "i"


def _unique(values) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return seen


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "item"
