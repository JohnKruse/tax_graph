from __future__ import annotations

import subprocess
import sys

import pytest


@pytest.mark.m0
def test_cli_validate_succeeds():
    result = subprocess.run(
        [sys.executable, "-m", "tax_graph.cli", "validate", "2025"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "graph integrity OK" in result.stdout


@pytest.mark.m0
def test_cli_run_reports_line_7_value():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tax_graph.cli",
            "run",
            "--facts",
            "examples/capital_gains_basic/facts.yaml",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "form_1040_2025_line_7_capital_gain_loss = 2000" in result.stdout
