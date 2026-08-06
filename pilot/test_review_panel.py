"""Tests for the generated three-column review panel pilot.

These tests intentionally exercise the real M20-S68 candidate workspace.  A
toy graph would not prove that the panel preserves the 157-anchor denominator,
the held-back rows, or the graph edge roles found in the corpus.
"""

from __future__ import annotations

from pathlib import Path

from review_panel import build_panel, main, render_html


CANDIDATE = Path(r"C:\tmp\m20_s68_candidate")
TEST_OUTPUT = Path(
    r"C:\Users\devbox\.codex\visualizations\2026\08\06\019fd7ff-15d7-7d62-8122-8cb2b270f6a6"
) / "m20_s69_review_panel_test.html"


def _real_panel() -> dict:
    if not CANDIDATE.is_dir():
        raise AssertionError(f"required real candidate workspace is missing: {CANDIDATE}")
    return build_panel(CANDIDATE)


def _by_anchor(panel: dict, document_id: str, line: str) -> dict:
    matches = [
        item
        for item in panel["panels"]
        if item["document_id"] == document_id and item["line"] == line
    ]
    assert len(matches) == 1
    return matches[0]


def test_real_candidate_preserves_all_anchors_and_reports_flow_split() -> None:
    panel = _real_panel()

    assert panel["denominator"] == 157
    assert panel["documents"] == ["form_1040_2025", "form_2441_2025", "form_6251_2025"]
    assert sum(panel["flow_modes"].values()) == 157
    assert panel["holes"] == 92
    assert {
        item["node_id"]
        for item in panel["graph_jargon_nodes"]
        if item["document_id"] == "form_2441_2025"
    } >= {
        "form_2441_2025_zero_floor",
        "form_2441_2025_root_line_26_pre_floor",
    }


def test_operation_projection_keeps_rule_and_edge_roles() -> None:
    panel = _real_panel()
    lookup = _by_anchor(panel, "form_2441_2025", "8")
    assert lookup["graph"]["operation"] == "LOOKUP_TABLE"
    assert lookup["graph"]["rule_ids"] == ["rule_form_2441_2025_root_line_8_candidate"]
    assert lookup["graph"]["operands"][0]["role"] == "key"
    assert lookup["graph"]["operands"][0]["node_id"] == "form_2441_2025_root_line_7"
    assert lookup["flow_mode"] == "diagram"

    subtract = _by_anchor(panel, "form_1040_2025", "15")
    assert subtract["graph"]["operation"] == "MAX"
    assert [item["role"] for item in subtract["graph"]["operands"]] == ["candidate", "candidate"]
    assert subtract["flow_mode"] == "chain"


def test_held_back_rows_are_visible_holes_with_findings() -> None:
    panel = _real_panel()
    for document_id, line, expected in (
        ("form_2441_2025", "25", "LOOKUP_TABLE arguments must be named leaf operands with a role"),
        ("form_6251_2025", "27", "expression references its own line 27"),
    ):
        row = _by_anchor(panel, document_id, line)
        assert row["hole"] is True
        assert row["graph"] is None
        assert any(expected in str(item) for item in row["findings"])


def test_rendered_html_has_one_panel_per_anchor_and_nonempty_hole_columns() -> None:
    html = render_html(_real_panel())

    assert html.count('<article class="review-panel"') == 157
    assert 'data-flow-mode="diagram"' in html
    assert 'data-flow-mode="chain"' in html
    assert 'data-hole="true"' in html
    assert "No promoted graph operation." in html
    assert "LOOKUP_TABLE arguments must be named leaf operands with a role" in html
    assert "form_2441_2025_zero_floor" in html
    assert "Graph terminology to report (not changed)" in html


def test_cli_writes_the_self_contained_artifact() -> None:
    try:
        assert main([str(CANDIDATE), "--output", str(TEST_OUTPUT)]) == 0
        contents = TEST_OUTPUT.read_text(encoding="utf-8")
        assert contents.startswith("<!doctype html>")
        assert "<meta charset=\"utf-8\">" in contents
    finally:
        if TEST_OUTPUT.is_file():
            TEST_OUTPUT.unlink()
