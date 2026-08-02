"""M20-S31 tests for document-agnostic formula selection and empty reports."""

from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.extract.outline import OutlineNode
from tax_graph.extract.outline_pipeline import _formula_outline_nodes


pytestmark = pytest.mark.m20


def test_schedule_d_formula_selection_keeps_all_three_formula_lines() -> None:
    schedule_d = OutlineNode(
        outline_id="schedule_d",
        kind="section",
        label="Schedule D - Capital Gains and Losses",
        children=[
            OutlineNode(
                outline_id="line_7",
                kind="line",
                line_anchor="7",
                label="Combine lines 1a through 6 in column (h).",
            ),
            OutlineNode(
                outline_id="line_15",
                kind="line",
                line_anchor="15",
                label="Combine lines 8a through 14 in column (h).",
            ),
            OutlineNode(
                outline_id="line_16",
                kind="line",
                line_anchor="16",
                label="Combine lines 7 and 15.",
            ),
            OutlineNode(
                outline_id="line_18",
                kind="line",
                line_anchor="18",
                label="28% rate gain or loss.",
            ),
        ],
    )

    selected = _formula_outline_nodes([schedule_d])

    assert [node.line_anchor for node in selected] == ["7", "15", "16"]


def test_s31_test_file_is_ascii_only() -> None:
    path = Path(__file__)
    path.read_text(encoding="ascii")
