from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from tax_graph.drills import run_drills
from tax_graph.io.loader import LoadedGraph, load_graph
from tax_graph.verify import check_graph_properties


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.m8
def test_live_graph_property_checks_pass():
    report = check_graph_properties(load_graph("2025", ROOT))

    assert report.ok, report.issues


@pytest.mark.m8
def test_swapped_subtract_roles_are_caught_by_properties():
    graph = _copy_graph(load_graph("2025", ROOT))
    edges = {edge["edge_id"]: edge for edge in graph.items("edges")}
    edges["e_8949_part_ii_d_to_d_minus_e"]["role"] = "subtrahend"
    edges["e_8949_part_ii_e_to_d_minus_e"]["role"] = "minuend"

    report = check_graph_properties(graph)

    assert not report.ok
    assert any(issue.check_id == "table_d_minus_e_relation" for issue in report.issues)


@pytest.mark.m8
def test_dropped_adjustment_addend_is_caught_by_table_relation():
    graph = _copy_graph(load_graph("2025", ROOT))
    graph.objects["edges"] = [
        edge
        for edge in graph.items("edges")
        if edge.get("edge_id") != "e_8949_part_ii_g_to_h"
    ]

    report = check_graph_properties(graph)

    assert not report.ok
    assert any(issue.check_id == "table_h_metamorphic" for issue in report.issues)


@pytest.mark.m8
def test_swapped_role_drill_names_property_layer(tmp_path):
    catalog = tmp_path / "catalog.yaml"
    catalog.write_text(
        yaml.safe_dump(
            [
                {
                    "id": "swap_roles",
                    "taxonomy": "F3",
                    "description": "Swap subtract operands.",
                    "mutation": {
                        "kind": "swap_edge_roles",
                        "edge_ids": [
                            "e_8949_part_ii_d_to_d_minus_e",
                            "e_8949_part_ii_e_to_d_minus_e",
                        ],
                    },
                    "expected_layers": ["L3"],
                }
            ],
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    report = run_drills(year="2025", root=ROOT, catalog=catalog)

    assert report.ok, report.format_report()
    assert report.outcomes[0].actual_layers == ("L3",)
    assert any(finding.check == "table_d_minus_e_relation" for finding in report.outcomes[0].findings)


def _copy_graph(graph: LoadedGraph) -> LoadedGraph:
    return LoadedGraph(
        year=graph.year,
        root=graph.root,
        graph_dir=graph.graph_dir,
        objects=deepcopy(graph.objects),
    )
