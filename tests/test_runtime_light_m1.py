from __future__ import annotations

import json
import subprocess
import sys

import pytest


@pytest.mark.m1
def test_runtime_commands_do_not_import_build_time_modules():
    script = """
import json
import sys
from tax_graph.cli import run_command, validate_command

validate_code = validate_command(year="2025")
run_code = run_command(facts="examples/capital_gains_basic/facts.yaml")
loaded = [name for name in ("fitz", "mistralai") if name in sys.modules]
print(json.dumps({"validate_code": validate_code, "run_code": run_code, "loaded": loaded}))
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload == {"validate_code": 0, "run_code": 0, "loaded": []}
