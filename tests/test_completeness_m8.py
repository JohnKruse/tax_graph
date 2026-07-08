from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from tax_graph.drills import run_drills
from tax_graph.io.loader import LoadedGraph, load_graph
from tax_graph.validate.graph_validator import validate_loaded_graph
from tax_graph.verify import check_loaded_graph_field_completeness


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.m8
def test_promoted_8949_field_grid_completeness_passes():
    graph = load_graph("2025", ROOT)

    report = check_loaded_graph_field_completeness(
        graph,
        {"form_8949_2025": _form_8949_field_grid()},
    )

    assert report.ok, report.issues


@pytest.mark.m8
def test_field_grid_completeness_flags_deleted_template_node():
    graph = _copy_graph(load_graph("2025", ROOT))
    graph.objects["nodes"] = [
        node
        for node in graph.items("nodes")
        if node.get("node_id") != "form_8949_2025_part_ii_line_1_column_d"
    ]

    report = check_loaded_graph_field_completeness(
        graph,
        {"form_8949_2025": _form_8949_field_grid()},
    )

    assert not report.ok
    assert any("f2_06" in issue.field_name for issue in report.issues)
    assert any("column d" in issue.reason for issue in report.issues)


@pytest.mark.m8
def test_validator_accepts_field_grids_and_reports_unmapped_fields():
    graph = _copy_graph(load_graph("2025", ROOT))
    graph.objects["nodes"] = [
        node
        for node in graph.items("nodes")
        if node.get("node_id") != "form_8949_2025_part_ii_line_1_column_d"
    ]

    result = validate_loaded_graph(graph, field_grids={"form_8949_2025": _form_8949_field_grid()})

    assert not result.ok
    assert any("field grid form_8949_2025" in error for error in result.errors)


@pytest.mark.m8
def test_optional_mef_inventory_cross_check_uses_same_mapping_contract():
    graph = load_graph("2025", ROOT)

    report = check_loaded_graph_field_completeness(
        graph,
        {"form_8949_2025": _form_8949_field_grid()},
        mef_line_inventory={"form_8949_2025": ["1", "10", "99"]},
    )

    assert not report.ok
    assert any(issue.field_name == "mef_line_99" for issue in report.issues)
    assert not any(issue.field_name == "mef_line_1" for issue in report.issues)
    assert not any(issue.field_name == "mef_line_10" for issue in report.issues)


@pytest.mark.m8
def test_not_modeled_records_are_required_for_unmapped_fields():
    graph = _copy_graph(load_graph("2025", ROOT))
    for document in graph.items("documents"):
        if document.get("document_id") == "form_8949_2025":
            document["not_modeled_fields"] = []

    report = check_loaded_graph_field_completeness(
        graph,
        {"form_8949_2025": _form_8949_field_grid()},
    )

    assert not report.ok
    assert any("f1_01" in issue.field_name for issue in report.issues)
    assert any("f2_03" in issue.field_name for issue in report.issues)
    assert any("f2_91" in issue.field_name for issue in report.issues)


@pytest.mark.m8
def test_field_grid_completeness_ignores_letter_only_subline_fields():
    graph = _copy_graph(load_graph("2025", ROOT))
    report = check_loaded_graph_field_completeness(
        graph,
        {
            "form_8949_2025": {
                "fields": [
                    {"field_name": "subline_letter_only", "line_anchor": "z"},
                    {"field_name": "anchored_line_10", "line_anchor": "10"},
                ]
            }
        },
    )

    assert not any(issue.field_name == "subline_letter_only" for issue in report.issues)


@pytest.mark.m8
def test_deleted_node_drill_can_be_attributed_to_field_completeness(tmp_path):
    catalog = tmp_path / "catalog.yaml"
    catalog.write_text(
        yaml.safe_dump(
            [
                {
                    "id": "delete_table_node_for_completeness",
                    "taxonomy": "F1",
                    "description": "Delete a node that the field grid maps to.",
                    "mutation": {
                        "kind": "delete_node",
                        "node_id": "form_8949_2025_part_ii_line_1_column_d",
                    },
                    "expected_layers": ["L1"],
                }
            ],
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    report = run_drills(
        year="2025",
        root=ROOT,
        catalog=catalog,
        field_grids={"form_8949_2025": _form_8949_field_grid()},
    )

    assert report.ok, report.format_report()
    assert any(finding.check == "field_grid_completeness" for finding in report.outcomes[0].findings)


def _copy_graph(graph: LoadedGraph) -> LoadedGraph:
    return LoadedGraph(
        year=graph.year,
        root=graph.root,
        graph_dir=graph.graph_dir,
        objects=deepcopy(graph.objects),
    )


def _form_8949_field_grid() -> dict:
    return {
        "fields": [
            {"field_name": "topmostSubform[0].Page1[0].f1_01[0]", "page": 1, "x_cluster": 25},
            {"field_name": "topmostSubform[0].Page1[0].c1_1[0]", "page": 1, "x_cluster": 50},
            _table_field(part=2, row=1, index=1, x_cluster=25),
            _table_field(part=2, row=1, index=2, x_cluster=175),
            _table_field(part=2, row=1, index=3, x_cluster=225),
            _table_field(part=2, row=1, index=4, x_cluster=275),
            _table_field(part=2, row=1, index=5, x_cluster=350),
            _table_field(part=2, row=1, index=6, x_cluster=400),
            _table_field(part=2, row=1, index=7, x_cluster=450),
            _table_field(part=2, row=1, index=8, x_cluster=500),
            {
                "field_name": "topmostSubform[0].Page2[0].f2_91[0]",
                "line_anchor": "10",
                "page": 2,
                "x_cluster": 275,
            },
        ]
    }


def _table_field(*, part: int, row: int, index: int, x_cluster: int) -> dict:
    return {
        "field_name": (
            f"topmostSubform[0].Page{part}[0].Table_Line1_Part{part}[0]"
            f".Row{row}[0].f{part}_{index + 2:02d}[0]"
        ),
        "page": part,
        "x_cluster": x_cluster,
        "y_cluster": 400,
    }
