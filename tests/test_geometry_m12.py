"""M12 node-to-page geometry projection tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.output.geometry import (
    build_node_geometry,
    load_node_geometry,
    resolve_node_geometry,
    validate_node_geometry,
)


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.m12
def test_committed_geometry_is_schema_valid_and_current() -> None:
    assert validate_node_geometry("2025", ROOT) == []
    assert load_node_geometry("2025", ROOT) == build_node_geometry("2025", ROOT)


@pytest.mark.m12
def test_line_16_resolves_to_form_1040_page_two() -> None:
    locations = resolve_node_geometry("form_1040_2025_root_line_16", year="2025", root=ROOT)
    assert len(locations) == 1
    location = locations[0]
    assert location["document_id"] == "form_1040_2025"
    assert location["page"] == 2
    assert location["rect"][2] > location["rect"][0]
    assert location["rect"][3] > location["rect"][1]


@pytest.mark.m12
def test_repeatable_template_resolves_all_printed_slots() -> None:
    locations = resolve_node_geometry(
        "form_8949_2025_part_ii_line_1_column_h", year="2025", root=ROOT
    )
    assert len(locations) == 11
    assert {location["page"] for location in locations} == {2}
