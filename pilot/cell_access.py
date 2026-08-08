"""Read-only access to the text and cell evidence in the pilot.

The pilot has several source records for one printed anchor: the source
derivation report, the candidate row, and the denominator anchor.  This
module is the only place that chooses which record answers a cell question.
Absence is represented by ``CellText.value is None``.  It is never an empty
string, so a consumer cannot accidentally turn absence into a fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping


@dataclass(frozen=True)
class CellText:
    """One text answer, with typed absence and its selected source field."""

    value: str | None
    source: str | None = None

    @property
    def present(self) -> bool:
        """Return whether the answer contains text."""

        return self.value is not None


@dataclass(frozen=True)
class Cell:
    """Immutable joined view of the records for one printed anchor."""

    anchor: Mapping[str, Any]
    source: Mapping[str, Any]
    candidate: Mapping[str, Any]


def _mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    """Copy one optional mapping so callers cannot mutate the joined view."""

    if value is None:
        return MappingProxyType({})
    return MappingProxyType(dict(value))


def join_rows(
    *,
    anchor: Mapping[str, Any] | None = None,
    source: Mapping[str, Any] | None = None,
    candidate: Mapping[str, Any] | None = None,
) -> Cell:
    """Build the immutable view used by every pilot cell read."""

    return Cell(
        anchor=_mapping(anchor),
        source=_mapping(source),
        candidate=_mapping(candidate),
    )


def _read(record: Mapping[str, Any], field: str) -> CellText:
    """Read one text field, making blank and missing values typed absence."""

    if field not in record:
        return CellText(None)
    value = record[field]
    if value is None or value == "":
        return CellText(None)
    return CellText(str(value), field)


def _first_text(*choices: tuple[Mapping[str, Any], str]) -> CellText:
    """Choose the first present value from a centralized source policy."""

    for record, field in choices:
        result = _read(record, field)
        if result.present:
            return result
    return CellText(None)


def label(cell: Cell) -> CellText:
    """Return the caption only; ``label_after`` is the sole label source."""

    return _read(cell.source, "label_after")


def form_face(cell: Cell) -> CellText:
    """Return the printed form-face text using the fixed source policy."""

    return _first_text(
        (cell.candidate, "form_face_text"),
        (cell.source, "form_face_after"),
        (cell.source, "form_face_before"),
        (cell.anchor, "form_face_text"),
        (cell.anchor, "label"),
    )


def instruction_section(cell: Cell) -> CellText:
    """Return the joined instruction section, if one was recorded."""

    return _first_text(
        (cell.candidate, "instruction_text"),
        (cell.source, "instruction_text"),
        (cell.anchor, "instruction_text"),
    )


def expression(cell: Cell) -> Any:
    """Return the candidate expression, falling back only to source evidence."""

    if "expression" in cell.candidate and cell.candidate["expression"] is not None:
        return cell.candidate["expression"]
    return cell.source.get("expression")


def rendered_wording(cell: Cell) -> CellText:
    """Return the rendered candidate wording or source wording."""

    return _first_text(
        (cell.candidate, "rendered"),
        (cell.source, "rendered"),
    )


def model_outcome(cell: Cell) -> CellText:
    """Return the provider-stated outcome, if the derivation recorded one."""

    return _first_text(
        (cell.candidate, "model_outcome"),
        (cell.source, "model_outcome"),
    )


def findings(cell: Cell) -> tuple[Any, ...]:
    """Return the stored findings from the candidate or source record."""

    for record, field in (
        (cell.candidate, "findings"),
        (cell.source, "findings"),
        (cell.source, "validation_failures"),
    ):
        if field not in record:
            continue
        value = record[field]
        if isinstance(value, list):
            clean = tuple(item for item in value if item not in (None, ""))
            if clean:
                return clean
        elif value not in (None, ""):
            return (value,)
    return ()


def candidate_status(cell: Cell) -> CellText:
    """Return the candidate's raw status without consulting source status."""

    return _first_text(
        (cell.candidate, "candidate_status"),
        (cell.candidate, "status"),
    )


def source_status(cell: Cell) -> CellText:
    """Return the source report's raw status without consulting candidate status."""

    return _first_text(
        (cell.source, "status"),
        (cell.source, "original_status"),
    )


def status(cell: Cell) -> CellText:
    """Return the selected status, preferring the candidate record."""

    return _first_text(
        (cell.candidate, "candidate_status"),
        (cell.candidate, "status"),
        (cell.source, "status"),
        (cell.source, "original_status"),
    )


def node_id(cell: Cell) -> CellText:
    """Return the candidate node id, or source node id when present."""

    return _first_text(
        (cell.candidate, "node_id"),
        (cell.source, "node_id"),
    )


def quote(cell: Cell) -> CellText:
    """Return the stored citation quote from candidate or source evidence."""

    return _first_text(
        (cell.candidate, "quote"),
        (cell.source, "quote"),
    )


def quote_span_id(cell: Cell) -> CellText:
    """Return the stored citation span id from candidate or source evidence."""

    return _first_text(
        (cell.candidate, "quote_span_id"),
        (cell.source, "quote_span_id"),
    )


def review_gap(cell: Cell) -> CellText:
    """Return an explicit review-gap value from candidate or source evidence."""

    return _first_text(
        (cell.candidate, "review_gap"),
        (cell.source, "review_gap"),
    )


def error(cell: Cell) -> CellText:
    """Return the stored candidate or source error text."""

    return _first_text(
        (cell.candidate, "error"),
        (cell.source, "error"),
    )


def graph_node_label(graph: Mapping[str, Any], node_id: str) -> CellText:
    """Read one graph node label through the same typed text boundary."""

    nodes = graph.get("nodes")
    if not isinstance(nodes, Mapping):
        return CellText(None)
    node = nodes.get(node_id)
    if not isinstance(node, Mapping):
        return CellText(None)
    return _read(node, "label")


def graph_operands(graph: Mapping[str, Any], node_id: str) -> tuple[dict[str, Any], ...]:
    """Return direct operands with their stored edge roles and labels."""

    edges_by_target = graph.get("edges_by_target")
    if not isinstance(edges_by_target, Mapping):
        return ()
    result: list[dict[str, Any]] = []
    edges = edges_by_target.get(node_id)
    if not isinstance(edges, list):
        return ()
    for edge in edges:
        if not isinstance(edge, Mapping):
            continue
        source_value = edge.get("source")
        if source_value is None or source_value == "":
            continue
        source = str(source_value)
        role_value = edge.get("role")
        role = "<unnamed>" if role_value in (None, "") else str(role_value)
        label_value = graph_node_label(graph, source)
        result.append(
            {
                "edge_id": "" if edge.get("edge_id") is None else str(edge.get("edge_id")),
                "node_id": source,
                "role": role,
                "label": label_value.value,
            }
        )
    return tuple(result)
