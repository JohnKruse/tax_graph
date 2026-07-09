import pytest
from pathlib import Path
from typer.testing import CliRunner

from tax_graph.cli import app
from tax_graph.verify.parameter_diff import compare_parameter_diff


@pytest.mark.m11
def test_parameter_diff_offline_fixture(tmp_path):
    root = Path(__file__).resolve().parents[1]
    fixture_path = root / "tests" / "fixtures" / "pe_2025_parameters.json"
    
    report = compare_parameter_diff("2025", root=root, offline_fixture=fixture_path)
    
    assert report.year == "2025"
    assert report.disagree == 1, "Expected exactly 1 disagreement due to the seeded HoH bug in the fixture"
    
    disagreements = [r for r in report.results if r.status == "disagree"]
    assert len(disagreements) == 1
    assert disagreements[0].node_id == "form_1040_2025_brackets_hoh"
    assert "value mismatch" in disagreements[0].reason

    # The mapping should have 20 nodes total (5 std ded, 10 qdcgt, 5 brackets)
    assert len(report.results) == 20
    assert report.agree == 19
    assert report.unmapped == 0


@pytest.mark.m11
def test_parameter_diff_cli_offline():
    runner = CliRunner()
    root = Path(__file__).resolve().parents[1]
    fixture_path = root / "tests" / "fixtures" / "pe_2025_parameters.json"
    
    result = runner.invoke(app, [
        "verify", "parameter-diff",
        "--year", "2025",
        "--root", str(root),
        "--offline-fixture", str(fixture_path),
    ])
    
    # We expect a non-zero exit code because there is 1 disagreement
    assert result.exit_code == 1
    assert "=== PolicyEngine parameter diff (2025) ===" in result.stdout
    assert "disagree: 1" in result.stdout
    assert "form_1040_2025_brackets_hoh: value mismatch" in result.stdout
