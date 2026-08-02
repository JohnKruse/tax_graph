"""M20-S31 tests for document-agnostic formula selection and empty reports."""

from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.extract.outline import OutlineNode
from tax_graph.extract.outline_pipeline import _formula_outline_nodes
from experiments.derive_cells_s25 import run_documents


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


def test_harness_marks_zero_attempt_document_empty_with_outline_inventory(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "experiments.derive_cells_s25.persist_instruction_frame",
        lambda **_: (tmp_path / "frame.yaml", tmp_path / "coverage.yaml"),
    )
    monkeypatch.setattr(
        "experiments.derive_cells_s25.run_real_document",
        lambda **_: {
            "rows_attempted": 0,
            "row_status_counts": {"derived": 0, "repaired": 0, "gapped": 0, "errored": 0},
            "outline_node_count": 31,
            "line_anchor_count": 24,
            "validation": {"validator_failures_by_kind": {}},
        },
    )

    reports = run_documents(
        root=tmp_path / "repo",
        year="2025",
        document_ids=["schedule_d_2025"],
        output_dir=tmp_path / "output",
    )

    assert reports == [
        {
            "document_id": "schedule_d_2025",
            "status": "empty",
            "reason": "document outline produced no derivation rows",
            "rows_attempted": 0,
            "derived": 0,
            "repaired": 0,
            "gapped": 0,
            "errored": 0,
            "outline_node_count": 31,
            "line_anchor_count": 24,
            "validator_failures_by_kind": {},
        }
    ]


def test_cell_prompt_distinguishes_same_form_and_cross_form_operands() -> None:
    prompt = Path(__file__).resolve().parents[1] / "prompts" / "derive_cells.md"
    text = " ".join(prompt.read_text(encoding="ascii").split())

    assert 'For a sibling line on this same form, use only {"line": "7"}' in text
    assert 'Use {"form": "form_XXXX_2025", "line": "7"} only for a line on another form.' in text
