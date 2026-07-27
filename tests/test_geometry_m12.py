"""M12 node-to-page geometry projection tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.output.geometry import (
    _validate_page_bounds,
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


@pytest.mark.m17
def test_page_geometry_is_captured_per_document_page() -> None:
    geometry = load_node_geometry("2025", ROOT)
    pages = {
        (item["document_id"], item["page"]): item
        for item in geometry["pages"]
    }
    assert pages[("form_13614_c_2025", 1)]["width"] == 792.0
    assert pages[("form_13614_c_2025", 1)]["height"] == 612.0
    assert pages[("form_13614_c_2025", 6)]["width"] == 612.0
    assert pages[("form_13614_c_2025", 6)]["height"] == 792.0
    assert all(item["rotation"] in {0, 90, 180, 270} for item in geometry["pages"])


@pytest.mark.m17
def test_page_bounds_validator_fails_closed() -> None:
    geometry = {
        "pages": [{
            "document_id": "form_a_2025",
            "page": 1,
            "width": 612.0,
            "height": 792.0,
            "rotation": 0,
        }],
        "entries": [{
            "document_id": "form_a_2025",
            "page": 1,
            "field_name": "field_a",
            "rect": [600.0, 780.0, 620.0, 800.0],
        }],
    }
    errors = _validate_page_bounds(geometry)
    assert len(errors) == 1
    assert "outside page box" in errors[0]
