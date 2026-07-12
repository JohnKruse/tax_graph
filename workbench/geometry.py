"""Independent geometry indexing and hit testing for the workbench."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence


Rect = tuple[float, float, float, float]


@dataclass(frozen=True)
class GeometryHit:
    """One overlay entry hit by a point or selection rectangle."""

    layer: str
    entry: dict[str, Any]

    @property
    def node_id(self) -> str | None:
        """Return the static node id, if this is a resolved provenance anchor."""
        value = self.entry.get("node_id")
        return str(value) if value is not None else None


class GeometryIndex:
    """Split the published projection into field, provenance, and gap layers."""

    def __init__(self, geometry: dict[str, Any]) -> None:
        self._entries = tuple(dict(entry) for entry in geometry.get("entries", []))
        self.field_entries = tuple(self._entries)
        self.provenance_entries = tuple(entry for entry in self._entries if entry.get("node_id"))
        self.gap_entries = tuple(entry for entry in self._entries if not entry.get("node_id"))

    def hits(
        self,
        *,
        page: int,
        rect: Sequence[float],
    ) -> tuple[GeometryHit, ...]:
        """Return all field and provenance overlays intersecting a selection."""
        selection = _rect(rect)
        hits: list[GeometryHit] = []
        for layer, entries in (
            ("provenance", self.provenance_entries),
            ("field", self.field_entries),
        ):
            for entry in entries:
                if int(entry.get("page", -1)) == page and _intersects(selection, _entry_rect(entry)):
                    hits.append(GeometryHit(layer=layer, entry=entry))
        return tuple(hits)

    def at(self, *, page: int, x: float, y: float) -> tuple[GeometryHit, ...]:
        """Return overlays containing one page-space point."""
        return self.hits(page=page, rect=(x, y, x, y))

    def anchors_for_node(self, node_id: str) -> tuple[dict[str, Any], ...]:
        """Return every official-form anchor for one static node id."""
        return tuple(entry for entry in self.provenance_entries if entry.get("node_id") == node_id)

    def gaps_for_page(self, page: int) -> tuple[dict[str, Any], ...]:
        """Return identity-only or otherwise unresolved regions on a page."""
        return tuple(entry for entry in self.gap_entries if int(entry.get("page", -1)) == page)


def _entry_rect(entry: dict[str, Any]) -> Rect:
    return _rect(entry.get("rect", ()))


def _rect(values: Sequence[float]) -> Rect:
    if len(values) != 4:
        raise ValueError("geometry rectangles require four coordinates")
    x0, y0, x1, y1 = (float(value) for value in values)
    return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)


def _intersects(left: Rect, right: Rect) -> bool:
    return not (
        left[2] < right[0]
        or right[2] < left[0]
        or left[3] < right[1]
        or right[3] < left[1]
    )
