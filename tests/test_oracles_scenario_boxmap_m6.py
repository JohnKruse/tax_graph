from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from tax_graph.engine import Graph
from tax_graph.oracles.box_map import box_map_from_dict, load_box_map, load_ots_label_inventory, validate_box_map
from tax_graph.oracles.scenario import (
    CapitalGainScenario,
    render_ots_8949_csv,
    render_ots_input_text,
    render_tax_graph_facts_yaml,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "oracles"


def _scenario() -> CapitalGainScenario:
    return CapitalGainScenario(
        scenario_id="m6_single_lot_gain",
        tax_year="2025",
        filing_status="single",
        description="Fake LT lot",
        date_acquired="01/15/2024",
        date_sold="06/01/2025",
        proceeds=12000,
        cost=10000,
    )


@pytest.mark.m6
def test_scenario_renders_tax_graph_facts_golden():
    expected = (FIXTURES / "expected_tax_graph_facts.yaml").read_text(encoding="utf-8")

    assert render_tax_graph_facts_yaml(_scenario()) == expected


@pytest.mark.m6
def test_scenario_renders_ots_input_golden():
    expected = (FIXTURES / "expected_ots_input.txt").read_text(encoding="utf-8")

    assert render_ots_input_text(_scenario()) == expected


@pytest.mark.m6
def test_scenario_renders_ots_8949_csv_golden():
    expected = (FIXTURES / "expected_ots_8949.csv").read_text(encoding="utf-8")

    assert render_ots_8949_csv(_scenario()) == expected


@pytest.mark.m6
def test_tax_graph_renderer_rejects_unmodeled_adjustment():
    scenario = replace(_scenario(), adjustment=25)

    with pytest.raises(ValueError, match="does not model 8949 adjustments"):
        render_tax_graph_facts_yaml(scenario)


@pytest.mark.m6
def test_box_map_validates_against_graph_and_inventory():
    box_map = load_box_map(ROOT / "oracles" / "box_map_2025.yaml")
    labels = load_ots_label_inventory(ROOT / box_map.label_inventory)

    report = validate_box_map(box_map, Graph("2025", root=ROOT, source="yaml"), labels)

    assert report.ok


@pytest.mark.m6
def test_box_map_validation_fails_on_unknown_node_id():
    graph = Graph("2025", root=ROOT, source="yaml")
    labels = load_ots_label_inventory(ROOT / "oracles" / "ots_label_inventory_2025.txt")
    box_map = box_map_from_dict(
        {
            "tax_year": 2025,
            "boxes": [{"node_id": "missing_node", "ots_label": "L7a"}],
        }
    )

    report = validate_box_map(box_map, graph, labels)

    assert "unknown Tax Graph node_id: missing_node" in report.errors


@pytest.mark.m6
def test_box_map_validation_fails_on_unknown_ots_label():
    graph = Graph("2025", root=ROOT, source="yaml")
    labels = load_ots_label_inventory(ROOT / "oracles" / "ots_label_inventory_2025.txt")
    box_map = box_map_from_dict(
        {
            "tax_year": 2025,
            "boxes": [
                {
                    "node_id": "form_1040_2025_line_7_capital_gain_loss",
                    "ots_label": "NO_SUCH_LABEL",
                }
            ],
        }
    )

    report = validate_box_map(box_map, graph, labels)

    assert "unknown OTS label: NO_SUCH_LABEL" in report.errors
