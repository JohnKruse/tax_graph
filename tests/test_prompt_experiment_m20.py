"""M20-S24 regression tests for the experiment/pipeline tree contract."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tax_graph.extract.cells import expression_schema, render


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "experiments") not in sys.path:
    sys.path.insert(0, str(ROOT / "experiments"))

import prompt_experiment  # noqa: E402


def test_prompt_experiment_uses_shared_tree_schema_and_renderer() -> None:
    assert prompt_experiment.expression_schema is expression_schema
    assert prompt_experiment.render is render
    tree = {"op": "MAX", "args": [{"op": "SUBTRACT", "args": [{"line": "11b"}, {"line": "14"}]}, {"const": 0}]}
    assert prompt_experiment.render(tree) == "max(line 11b - line 14, 0)"

