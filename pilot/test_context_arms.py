"""Tests for the isolated M20-S88 context-arm pilot."""

from __future__ import annotations

from types import SimpleNamespace

from tax_graph.extract.cells import CellFrame, CellRecord
from tax_graph.extract.inputs import load_document_input

from context_arms import (
    KNOWN_MISSED_FORMULAS,
    _raw_heading_region,
    build_arm_frame,
    score_arm,
)


def test_fixed_scoring_set_has_the_handoff_shape() -> None:
    assert len(KNOWN_MISSED_FORMULAS) == 32
    assert sum(document_id == "form_1040_2025" for document_id, _ in KNOWN_MISSED_FORMULAS) == 5
    assert sum(document_id == "form_2441_2025" for document_id, _ in KNOWN_MISSED_FORMULAS) == 2
    assert sum(document_id == "form_6251_2025" for document_id, _ in KNOWN_MISSED_FORMULAS) == 25


def test_raw_region_handles_run_together_line_heading() -> None:
    region = _raw_heading_region(
        "before\n**Line 2dDepletion**\nEnter the amount.\nafter\n",
        line="2d",
        radius=1,
    )
    assert region is not None
    assert region.line_start == 1
    assert region.line_end == 3
    assert "Line 2dDepletion" in region.text
    assert "Enter the amount" in region.text


def test_all_anchor_arm_frame_keeps_legacy_telemetry_outside_routing_metadata() -> None:
    document = load_document_input("form_1040_2025", year="2025", root=".")
    frames = [build_arm_frame(document, arm)[0] for arm in ("A", "B", "C")]

    assert [len(frame.rows) for frame in frames] == [59, 59, 59]
    for frame in frames:
        missed = next(row for row in frame.rows if row.line == "6b")
        assert missed.metadata["pilot_original_legacy_selector_admitted"] is False
        assert "selector_admitted" not in missed.metadata
        assert "selector_skip_reason" not in missed.metadata
    assert "selector_admitted" not in frames[0].rows[0].metadata


def test_score_reports_recovery_regression_and_quote_owner() -> None:
    result = CellFrame.from_rows(
        [
            CellRecord(
                form="form_1040_2025",
                line="6b",
                form_face_text="Enter amount from line 5.",
                instruction_text="",
                status="derived",
                quote="Enter amount from line 5.",
            ),
            CellRecord(
                form="form_1040_2025",
                line="12e",
                form_face_text="",
                instruction_text="Line 1 text.",
                status="error",
                error="provider failure",
            ),
        ]
    )
    instruction_frame = SimpleNamespace(
        sections=[
            SimpleNamespace(document_id="form_1040_2025", line="12e", text="Line 12e text."),
            SimpleNamespace(document_id="form_1040_2025", line="6b", text="Other text."),
        ]
    )
    baseline = {
        ("form_1040_2025", "6b", 0): {"status": "derived"},
        ("form_1040_2025", "12e", 0): {"status": "derived"},
    }

    scored = score_arm(result, instruction_frame=instruction_frame, baseline_rows=baseline)

    assert scored["recovery"]["recovered_count"] == 1
    assert scored["regressions"]["count"] == 1
    assert scored["regressions"]["rows"][0]["line"] == "12e"
    assert scored["misattribution"]["counts"] == {"form_face": 1}
