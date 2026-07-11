from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from tax_graph.io.loader import load_yaml
from tax_graph.validate.graph_validator import validate_graph


ROOT = Path(__file__).resolve().parents[1]


def _copy_graph_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(ROOT / "graph", root / "graph")
    shutil.copytree(ROOT / "schemas", root / "schemas")
    return root


def _read_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_yaml(path: Path, value) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


@pytest.mark.m0
def test_loader_normalizes_yaml_dates(tmp_path):
    path = tmp_path / "date.yaml"
    path.write_text("retrieved_date: 2026-06-28\n", encoding="utf-8")

    assert load_yaml(path) == {"retrieved_date": "2026-06-28"}


@pytest.mark.m0
def test_current_2025_graph_validates():
    result = validate_graph("2025", root=ROOT)

    assert result.ok, result.errors


@pytest.mark.m0
def test_validator_catches_duplicate_ids(tmp_path):
    root = _copy_graph_root(tmp_path)
    nodes_file = root / "graph" / "2025" / "nodes" / "capital-gains.yaml"
    nodes = _read_yaml(nodes_file)
    nodes.append(dict(nodes[0]))
    _write_yaml(nodes_file, nodes)

    result = validate_graph("2025", root=root)

    assert not result.ok
    assert any("duplicate node_id form_8949_2025_part_i_line_1_column_d" in error for error in result.errors)


@pytest.mark.m0
def test_validator_catches_dependency_cycles(tmp_path):
    root = _copy_graph_root(tmp_path)
    edges_file = root / "graph" / "2025" / "edges" / "capital-gains.yaml"
    edges = _read_yaml(edges_file)
    edges.append(
        {
            "edge_id": "e_1040_7_back_to_sd_7",
            "source": "form_1040_2025_line_7_capital_gain_loss",
            "target": "schedule_d_2025_line_7_net_st",
            "relationship": "FEEDS",
            "rule_id": "copy_currency_value",
        }
    )
    _write_yaml(edges_file, edges)

    result = validate_graph("2025", root=root)

    assert not result.ok
    assert any("dependency cycle detected" in error for error in result.errors)


@pytest.mark.m0
def test_validator_catches_cross_year_documents(tmp_path):
    root = _copy_graph_root(tmp_path)
    document_file = root / "graph" / "2025" / "documents" / "form-1040.yaml"
    document = _read_yaml(document_file)
    document["tax_year"] = 2024
    _write_yaml(document_file, document)

    result = validate_graph("2025", root=root)

    assert not result.ok
    assert any("tax_year 2024 does not match graph 2025" in error for error in result.errors)


@pytest.mark.m8
def test_validator_flags_inline_magic_number_parameters(tmp_path):
    root = _copy_graph_root(tmp_path)
    rules_file = root / "graph" / "2025" / "rules" / "core.yaml"
    rules = _read_yaml(rules_file)
    for rule in rules:
        if rule["rule_id"] == "sum_currency":
            rule.setdefault("parameters", {})["capital_loss_limit"] = 3000
    _write_yaml(rules_file, rules)

    result = validate_graph("2025", root=root)

    assert not result.ok
    assert any("inline numeric parameter at parameters.capital_loss_limit" in error for error in result.errors)


@pytest.mark.m7
def test_validator_allows_registered_frontier_edge(tmp_path):
    root = _copy_graph_root(tmp_path)
    edges_file = root / "graph" / "2025" / "edges" / "capital-gains.yaml"
    edges = _read_yaml(edges_file)
    edges.append(
        {
            "edge_id": "e_8949_part_ii_total_to_sd_9_frontier",
            "source": "form_8949_2025_part_ii_line_2_line_2_column_h_total",
            "target": "schedule_d_2025_line_9_frontier",
            "relationship": "FEEDS",
            "rule_id": "copy_currency_value",
        }
    )
    _write_yaml(edges_file, edges)
    frontier = {
        "tax_year": 2025,
        "provenance": {
            "generated_by": "test",
            "soi_year": 2023,
            "soi_source_url": "https://www.irs.gov/statistics",
            "soi_note": "sample-based estimate",
        },
        "frontiers": [
            {
                "frontier_id": "deferred_schedule_d_2025_28_rate_gain_worksheet",
                "kind": "deferred_branch",
                "source": {"document_id": "schedule_d_2025"},
                "target": {
                    "document_id": "schedule_d_2025",
                    "line": "18",
                    "node_id": "schedule_d_2025_28_rate_gain_worksheet_frontier",
                },
                "target_url": "https://www.irs.gov/pub/irs-pdf/f1040sd.pdf",
                "citation_ref": "cite_schedule_d_line18_28pct",
                "status": "declared",
                "weight": 24000000,
            },
            {
                "frontier_id": "deferred_schedule_d_2025_unrecaptured_1250_worksheet",
                "kind": "deferred_branch",
                "source": {"document_id": "schedule_d_2025"},
                "target": {
                    "document_id": "schedule_d_2025",
                    "line": "19",
                    "node_id": "schedule_d_2025_unrecaptured_1250_worksheet_frontier",
                },
                "target_url": "https://www.irs.gov/pub/irs-pdf/f1040sd.pdf",
                "citation_ref": "cite_schedule_d_line19_1250",
                "status": "declared",
                "weight": 24000000,
            },
                {
                    "frontier_id": "flow_test_to_schedule_d_line_9",
                "kind": "outbound_flow",
                "source": {
                    "document_id": "form_8949_2025",
                    "node_id": "form_8949_2025_part_ii_line_2_line_2_column_h_total",
                },
                "target": {
                    "document_id": "schedule_d_2025",
                    "line": "9",
                },
                "target_url": "https://www.irs.gov/pub/irs-pdf/f1040sd.pdf",
                "citation_ref": "cite_8949_line2_totals",
                "status": "declared",
                    "weight": 24000000,
                },
                {
                    "frontier_id": "deferred_schedule_1_2025_student_loan_interest_deduction_worksheet",
                    "kind": "deferred_branch",
                    "source": {"document_id": "schedule_1_2025"},
                    "target": {
                        "document_id": "schedule_1_2025",
                        "line": "21",
                        "node_id": "schedule_1_2025_student_loan_interest_deduction_worksheet_frontier",
                    },
                    "target_url": "https://www.irs.gov/pub/irs-prior/f1040s1--2025.pdf",
                    "citation_ref": "cite_span_schedule_1_2025_0061",
                    "status": "declared",
                    "weight": 74000000,
                }
        ],
    }
    _write_yaml(root / "graph" / "2025" / "frontier.yaml", frontier)

    result = validate_graph("2025", root=root)

    assert result.ok, result.errors


@pytest.mark.m7
def test_validator_rejects_unregistered_dangling_edge(tmp_path):
    root = _copy_graph_root(tmp_path)
    (root / "graph" / "2025" / "frontier.yaml").unlink()
    edges_file = root / "graph" / "2025" / "edges" / "capital-gains.yaml"
    edges = _read_yaml(edges_file)
    edges.append(
        {
            "edge_id": "e_8949_part_ii_total_to_missing_sd_9",
            "source": "form_8949_2025_part_ii_line_2_line_2_column_h_total",
            "target": "schedule_d_2025_line_9_frontier",
            "relationship": "FEEDS",
            "rule_id": "copy_currency_value",
        }
    )
    _write_yaml(edges_file, edges)

    result = validate_graph("2025", root=root)

    assert not result.ok
    assert any("missing target schedule_d_2025_line_9_frontier" in error for error in result.errors)


@pytest.mark.m7
def test_validator_rejects_malformed_frontier_entry(tmp_path):
    root = _copy_graph_root(tmp_path)
    frontier = {
        "tax_year": 2025,
        "provenance": {
            "generated_by": "test",
            "soi_year": 2023,
            "soi_source_url": "https://www.irs.gov/statistics",
            "soi_note": "sample-based estimate",
        },
        "frontiers": [
            {
                "frontier_id": "flow_missing_citation",
                "kind": "outbound_flow",
                "source": {"document_id": "form_8949_2025"},
                "target": {"document_id": "schedule_d_2025", "line": "9"},
                "target_url": "https://www.irs.gov/pub/irs-pdf/f1040sd.pdf",
                "citation_ref": "cite_missing",
                "status": "declared",
                "weight": 24000000,
            }
        ],
    }
    _write_yaml(root / "graph" / "2025" / "frontier.yaml", frontier)

    result = validate_graph("2025", root=root)

    assert not result.ok
    assert any("frontier flow_missing_citation -> missing citation cite_missing" in error for error in result.errors)
