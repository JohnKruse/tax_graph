from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tax_graph.cli import drill_run_command
from tax_graph.drills import run_drills


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.m8
def test_default_drill_catalog_catches_expected_layers():
    report = run_drills(year="2025", root=ROOT)

    assert report.ok, report.format_report()
    by_id = {outcome.drill_id: outcome for outcome in report.outcomes}
    assert by_id["swap_8949_subtract_roles"].actual_layers == ("L3",)
    assert "L0" in by_id["delete_required_table_node"].actual_layers
    assert "L1" in by_id["delete_required_table_node"].actual_layers
    assert "L5" in by_id["retarget_outbound_flow_line_off"].actual_layers
    assert by_id["confidence_inflation_no_effect"].status == "no_effect"
    assert by_id["inline_magic_number_parameter"].actual_layers == ("L0",)
    assert by_id["wrong_capital_loss_limit_parameter"].actual_layers == ("L3",)
    assert by_id["wrong_carryover_split"].actual_layers == ("L3",)
    assert by_id["carryover_ignores_limit"].actual_layers == ("L3",)
    assert by_id["wrong_sdtw_25_rate_parameter"].actual_layers == ("L3",)
    assert by_id["wrong_sdtw_breakpoint_parameter"].actual_layers == ("L3",)


@pytest.mark.m8
def test_uncatchable_drill_reports_miss(tmp_path):
    catalog = tmp_path / "catalog.yaml"
    catalog.write_text(
        yaml.safe_dump(
            [
                {
                    "id": "synthetic_uncatchable",
                    "taxonomy": "F3",
                    "description": "No mutation but expected to be caught.",
                    "mutation": {"kind": "no_op"},
                    "expected_layers": ["L3"],
                }
            ],
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    report = run_drills(year="2025", root=ROOT, catalog=catalog)

    assert not report.ok
    assert report.outcomes[0].status == "miss"
    assert report.outcomes[0].actual_layers == ()


@pytest.mark.m8
def test_drill_run_command_prints_report(capsys):
    exit_code = drill_run_command(year="2025", root=ROOT)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "drill report" in captured.out
    assert "result: PASS" in captured.out
    assert "swap_8949_subtract_roles" in captured.out
