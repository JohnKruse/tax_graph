from __future__ import annotations

import sqlite3
from pathlib import Path

import jsonschema
import pytest

from tax_graph.compile import build_sqlite
from tax_graph.compile.tax_table import load_brackets_from_graph
from tax_graph.drills import run_drills
from tax_graph.io.loader import load_graph, load_yaml
from tax_graph.validate import validate_graph

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.m11
def test_tax_table_schema_validation():
    """Validate compiled tax_table.json against its schema."""
    schemas_dir = ROOT / "schemas"
    tax_table_path = ROOT / "graph" / "2025" / "tax_table.json"
    
    assert tax_table_path.exists()
    data = load_yaml(tax_table_path)
    schema = load_yaml(schemas_dir / "tax_table.schema.json")
    
    # Should not raise any validation error
    jsonschema.validate(data, schema)
    assert data["tax_year"] == 2025
    assert len(data["entries"]) == 2064


@pytest.mark.m11
def test_graph_validation_checks_tax_table():
    """Verify that graph validation checks the tax table schema."""
    result = validate_graph("2025", root=ROOT)
    assert result.ok, result.errors


@pytest.mark.m11
def test_tax_table_sqlite_projection(tmp_path):
    """Compile graph to SQLite and verify tax_table table row count and values."""
    result = build_sqlite("2025", root=ROOT, build_dir=tmp_path)
    assert result.path.exists()

    with sqlite3.connect(result.path) as conn:
        # Check row count
        count = conn.execute("SELECT COUNT(*) FROM tax_table").fetchone()[0]
        assert count == 2064

        # Check range 25,300 to 25,350
        row_mid = conn.execute(
            """
            SELECT single, married_filing_jointly, married_filing_separately, head_of_household
            FROM tax_table
            WHERE income_min = 25300 AND income_max = 25350
            """
        ).fetchone()
        assert row_mid == (2801, 2562, 2801, 2699)

        # Check range 99,950 to 100,000
        row_upper = conn.execute(
            """
            SELECT single, married_filing_jointly, married_filing_separately, head_of_household
            FROM tax_table
            WHERE income_min = 99950 AND income_max = 100000
            """
        ).fetchone()
        assert row_upper == (16909, 11823, 16909, 15170)


@pytest.mark.m11
def test_tax_table_compiler_reads_brackets_from_graph_nodes():
    brackets = load_brackets_from_graph(ROOT, "2025")

    assert brackets["single"][-1] == {"rate": 0.37, "floor": 626350, "cumulative": 188769.75}
    assert brackets["head_of_household"][-1]["floor"] == 626350


@pytest.mark.m11
def test_m11_step2_drills_caught_at_l3():
    """Verify that wrong_standard_deduction and wrong_bracket_value are caught at L3."""
    report = run_drills(year="2025", root=ROOT)
    assert report.ok, report.format_report()
    
    by_id = {outcome.drill_id: outcome for outcome in report.outcomes}
    assert "wrong_standard_deduction" in by_id
    assert "wrong_bracket_value" in by_id
    
    assert by_id["wrong_standard_deduction"].actual_layers == ("L3",)
    assert by_id["wrong_bracket_value"].actual_layers == ("L3",)
