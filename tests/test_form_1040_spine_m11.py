from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from tax_graph.compile import build_sqlite
from tax_graph.engine import Engine, Graph, load_facts
from tax_graph.frontier.build import build_frontier_registry, load_frontier_registry
from tax_graph.validate import validate_graph


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "taxable_income_basic"


@pytest.mark.m11
def test_form_1040_spine_computes_taxable_income_on_yaml_and_sqlite(tmp_path):
    facts = load_facts(EXAMPLE / "facts.yaml")
    expected = yaml.safe_load((EXAMPLE / "expected.yaml").read_text(encoding="utf-8"))["expected"]

    # Shipped-content parity: exclude any locally installed user extension so
    # yaml and the compiled sqlite compare the same objects (hermetic in the
    # normal dev state, where the M14 pilot extension is present).
    yaml_result = Engine(Graph(2025, root=ROOT, source="yaml", include_extensions=False)).execute(facts)

    build_root = tmp_path / "project"
    shutil.copytree(ROOT / "graph", build_root / "graph", ignore=shutil.ignore_patterns("_drafts"))
    (build_root / "config").mkdir()
    (build_root / "config" / "tax-graph.config.yaml").write_text("", encoding="utf-8")
    build_sqlite("2025", root=build_root)
    sqlite_result = Engine(Graph(2025, root=build_root, source="sqlite")).execute(facts)

    assert sqlite_result.values == yaml_result.values
    for node_id, want in expected.items():
        assert yaml_result.values[node_id] == want
    assert yaml_result.trace["form_1040_2025_root_line_11a"]["operation"] == "SUBTRACT"
    assert yaml_result.trace["form_1040_2025_root_line_15"]["operation"] == "MAX"


@pytest.mark.m11
def test_form_1040_spine_preserves_capital_gains_parity():
    facts = load_facts(ROOT / "examples" / "capital_gains_basic" / "facts.yaml")

    result = Engine(Graph(2025, root=ROOT, source="yaml")).execute(facts)

    assert result.values["form_1040_2025_line_7_capital_gain_loss"] == 2000


@pytest.mark.m11
def test_form_1040_spine_zero_floors_taxable_income():
    facts = load_facts(EXAMPLE / "facts.yaml")
    facts["form_1040_2025_deduction_method"] = "itemized"
    facts["schedule_a_2025_root_line_16_amount"] = 200000

    result = Engine(Graph(2025, root=ROOT, source="yaml")).execute(facts)

    assert result.values["form_1040_2025_root_line_15_pre_floor"] < 0
    assert result.values["form_1040_2025_root_line_12e"] == 200000
    assert result.values["form_1040_2025_root_line_15"] == 0


@pytest.mark.m11
def test_form_1040_spine_validate_and_frontier_build_are_green(tmp_path):
    assert validate_graph("2025", root=ROOT).ok

    root = tmp_path / "project"
    shutil.copytree(ROOT / "graph", root / "graph")
    shutil.copytree(ROOT / "schemas", root / "schemas")
    shutil.copytree(ROOT / "config", root / "config")
    shutil.copytree(ROOT / "data", root / "data")

    registry = build_frontier_registry("2025", root=root).registry
    loaded = load_frontier_registry("2025", root=root)
    refs = {
        entry["frontier_id"]: entry
        for entry in registry["frontiers"]
        if entry["kind"] == "form_reference" and entry["target"].get("document_id") == "form_1040_2025"
    }

    assert loaded == registry
    assert refs["ref_cite_span_schedule_1_2025_0044_to_form_1040_2025"]["status"] == "modeled"
    assert refs["ref_cite_span_schedule_1a_2025_0064_to_form_1040_2025"]["status"] == "modeled"
    assert refs["ref_cite_span_schedule_b_2025_0009_to_form_1040_2025"]["status"] == "modeled"
