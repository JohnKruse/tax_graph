"""Box-map loading and validation for OTS differential tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class BoxMapping:
    """Mapping from a Tax Graph node to an OTS output label."""

    node_id: str
    ots_label: str
    rounding: str = "whole_dollar"
    condition: str | None = None


@dataclass(frozen=True)
class GuardBox:
    """OTS output label that must stay inert for a fenced scenario."""

    guard_id: str
    ots_label: str
    expected: int | float | None = 0
    allow_absent: bool = True


@dataclass(frozen=True)
class BoxMap:
    """Box-map data for one tax year."""

    tax_year: str
    boxes: tuple[BoxMapping, ...]
    guards: tuple[GuardBox, ...] = ()
    label_inventory: str | None = None


@dataclass(frozen=True)
class BoxMapValidationReport:
    """Validation result for a box map."""

    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        """Return whether validation found no errors."""

        return not self.errors


def load_box_map(path: str | Path) -> BoxMap:
    """Load a box map YAML file."""

    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return box_map_from_dict(data)


def box_map_from_dict(data: dict[str, Any]) -> BoxMap:
    """Build a ``BoxMap`` from parsed YAML data."""

    return BoxMap(
        tax_year=str(data["tax_year"]),
        label_inventory=data.get("ots_label_inventory"),
        boxes=tuple(
            BoxMapping(
                node_id=str(item["node_id"]),
                ots_label=str(item["ots_label"]),
                rounding=str(item.get("rounding", "whole_dollar")),
                condition=item.get("condition"),
            )
            for item in data.get("boxes", [])
        ),
        guards=tuple(
            GuardBox(
                guard_id=str(item["guard_id"]),
                ots_label=str(item["ots_label"]),
                expected=item.get("expected", 0),
                allow_absent=bool(item.get("allow_absent", True)),
            )
            for item in data.get("guards", [])
        ),
    )


def load_ots_label_inventory(path: str | Path) -> set[str]:
    """Load an OTS output-label inventory fixture."""

    labels: set[str] = set()
    for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        labels.add(line.split()[0])
    return labels


def validate_box_map(box_map: BoxMap, graph: Any, ots_labels: set[str]) -> BoxMapValidationReport:
    """Validate both sides of a box map."""

    errors: list[str] = []
    seen_nodes: set[str] = set()
    seen_boxes: set[tuple[str, str]] = set()
    for box in box_map.boxes:
        if box.node_id in seen_nodes:
            errors.append(f"duplicate Tax Graph node mapping: {box.node_id}")
        seen_nodes.add(box.node_id)
        pair = (box.node_id, box.ots_label)
        if pair in seen_boxes:
            errors.append(f"duplicate box mapping: {box.node_id} -> {box.ots_label}")
        seen_boxes.add(pair)
        if box.node_id not in graph.nodes:
            errors.append(f"unknown Tax Graph node_id: {box.node_id}")
        if box.ots_label not in ots_labels:
            errors.append(f"unknown OTS label: {box.ots_label}")
        if box.rounding != "whole_dollar":
            errors.append(f"unsupported rounding policy for {box.node_id}: {box.rounding}")
        if box.condition not in {None, "tax_graph_negative", "tax_graph_present", "sdtw_applies"}:
            errors.append(f"unsupported condition for {box.node_id}: {box.condition}")

    seen_guards: set[str] = set()
    for guard in box_map.guards:
        if guard.guard_id in seen_guards:
            errors.append(f"duplicate guard_id: {guard.guard_id}")
        seen_guards.add(guard.guard_id)
        if guard.ots_label not in ots_labels:
            errors.append(f"unknown OTS guard label: {guard.ots_label}")

    return BoxMapValidationReport(errors=tuple(errors))
