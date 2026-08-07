"""Tests for the generated two-column review panel pilot.

These tests intentionally exercise the real M20-S68 candidate workspace.  A
toy graph would not prove that the panel preserves the 157-anchor denominator,
the held-back rows, or the graph edge roles found in the corpus.
"""

from __future__ import annotations

import os
from pathlib import Path
import re

from review_panel import _flow_tree_html, _math_text, build_panel, main, render_html


CANDIDATE = Path(
    os.environ.get(
        "M20_S73_CANDIDATE",
        r"C:\Users\devbox\AppData\Local\Temp\claude\C--Users-devbox-projects-tax-graph\6e1d97d0-c72d-4855-a055-e0c64f6224f8\scratchpad\cand_s71",
    )
)


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
    assert panel["text_presence"] == {"caption": 8, "instruction": 84, "operation": 65}
    assert panel["text_absence"] == {"caption": 149, "instruction": 73, "operation": 92}
    assert panel["instruction_coverage"] == {
        "row_count": 153,
        "present": 84,
        "absent": 69,
        "documents": {
            "form_1040_2025": {"row_count": 59, "present": 42, "absent": 17},
            "form_2441_2025": {"row_count": 33, "present": 18, "absent": 15},
            "form_6251_2025": {"row_count": 61, "present": 24, "absent": 37},
        },
    }
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


def test_flow_stops_at_referenced_lines_and_reports_arrow_size() -> None:
    panel = _real_panel()
    refund = _by_anchor(panel, "form_1040_2025", "34")
    tree = refund["graph"]["tree"]

    assert refund["flow_arrows"] == 6
    assert panel["max_flow_arrows"] == 17
    assert panel["flow_arrow_distribution"] == {4: 9, 5: 2, 6: 1, 16: 2, 17: 1}
    assert tree["operands"][0]["tree"] == {
        "kind": "reference",
        "node_id": "form_1040_2025_root_line_33",
        "line": "33",
        "label": tree["operands"][0]["tree"]["label"],
    }
    assert tree["operands"][2]["tree"]["operands"][0]["tree"]["line"] == "33"


def test_repeated_operation_subtrees_render_once_then_as_reference() -> None:
    leaf = {"kind": "reference", "line": "20", "node_id": "hidden_line_20"}
    shared = {
        "kind": "operation",
        "operation": "MIN",
        "operands": [{"role": "candidate", "tree": leaf}],
    }
    tree = {
        "kind": "operation",
        "operation": "IF",
        "operands": [
            {"role": "when_true", "tree": shared},
            {"role": "when_false", "tree": shared},
        ],
    }

    html = _flow_tree_html(tree)

    assert html.count("<strong>MIN</strong>") == 1
    assert html.count("same expression as above") == 1
    assert "hidden_line_20" not in html
    assert "line 20" in html


def test_role_printing_suppresses_only_positionally_implied_roles() -> None:
    tree = {
        "kind": "operation",
        "operation": "SUM",
        "operands": [
            {"role": "addend", "tree": {"kind": "reference", "line": "1"}},
            {"role": "future_role", "tree": {"kind": "reference", "line": "2"}},
        ],
    }

    assert _math_text(tree) == "SUM(line 1, future_role=line 2)"
    rendered = _flow_tree_html(tree)
    assert 'class="tree-role">addend</span>' not in rendered
    assert 'class="tree-role">future_role</span>' in rendered


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


def test_skipped_anchor_keeps_candidate_instruction_evidence() -> None:
    panel = _real_panel()
    row = _by_anchor(panel, "form_1040_2025", "1a")

    assert row["status"] == "skipped"
    assert row["instruction"] is not None
    assert row["hole"] is True
    assert row["graph"] is None


def test_rendered_html_has_two_lossless_columns_and_named_holes() -> None:
    html = render_html(_real_panel())

    assert html.count('<article class="review-panel"') == 157
    assert html.count('<section class="column expression-column">') == 157
    assert html.count('<section class="column flow-column">') == 157
    assert 'data-two-column-layout="true"' in html
    assert "Generated two-column review panel" in html
    assert "Generated three-column review panel" not in html
    assert "source-column" not in html
    assert "operation-column" not in html
    assert 'data-flow-mode="diagram"' in html
    assert 'data-flow-mode="chain"' in html
    assert 'data-hole="true"' in html
    assert "No promoted flow." in html
    assert "LOOKUP_TABLE arguments must be named leaf operands with a role" in html
    assert "form_2441_2025_zero_floor" in html
    assert "captions 8 present / 149 absent" in html
    assert "instruction rows 84 present / 73 absent" in html
    assert "candidate instruction coverage 84/153 present" in html
    assert "form_1040_2025 42/59" in html
    assert "form_2441_2025 18/33" in html
    assert "form_6251_2025 24/61" in html
    assert "instruction sections 17 present" not in html
    flow_columns = re.findall(
        r'<section class="column flow-column">(.*?)</section>',
        html,
        flags=re.DOTALL,
    )
    assert len(flow_columns) == 157
    assert all("form_1040_2025_root_line_33" not in section for section in flow_columns)
    assert all("form_1040_2025_zero_floor" not in section for section in flow_columns)
    assert all('data-edge-labels-outside-nodes="true"' in section or "No promoted flow." in section for section in flow_columns)
    assert all('data-node-boxes-overlap-free="true"' in section or "No promoted flow." in section for section in flow_columns)
    assert all("flow-edge-moderator" not in section or "flow-edge-label" in section for section in flow_columns)
    assert "Graph terminology to report (not changed)" in html

    line_18_start = html.index('data-anchor="form_6251_2025#anchor=41:line=18"')
    line_18 = html[line_18_start:]
    line_18 = line_18[: line_18.index('<article class="review-panel"', 1)]
    assert "threshold" in line_18
    assert "filing status" in line_18
    assert "239100" in line_18
    assert "119550" in line_18


def test_flow_geometry_is_reported_and_moderator_roles_are_textual() -> None:
    panel = _real_panel()

    assert panel["flow_geometry"]["svg_count"] == 65
    assert panel["flow_geometry"]["connector_start_directions_unique"] is True
    assert panel["flow_geometry"]["edge_labels_outside_nodes"] is True
    assert panel["flow_geometry"]["node_boxes_overlap_free"] is True
    assert panel["flow_geometry"]["moderator_arrows"] > 0
    assert panel["flow_geometry"]["moderator_arrows_without_labels"] == 0
    assert len(panel["flow_svg_dimensions"]) == 65
    assert all(item["width"] == 620.0 and item["height"] > 0 for item in panel["flow_svg_dimensions"])


def test_real_candidate_keeps_informative_roles_and_drops_redundant_tags() -> None:
    html = render_html(_real_panel())
    for role in ("addend", "minuend", "subtrahend", "multiplier", "multiplicand"):
        assert f'class="tree-role">{role}</span>' not in html
    for role in ("key", "threshold", "condition", "when_true", "when_false"):
        assert f'class="tree-role">{role}</span>' in html


def test_cli_writes_the_self_contained_artifact(tmp_path: Path) -> None:
    output = tmp_path / "review_panel.html"
    assert main([str(CANDIDATE), "--output", str(output)]) == 0
    contents = output.read_text(encoding="utf-8")
    assert contents.startswith("<!doctype html>")
    assert "<meta charset=\"utf-8\">" in contents
