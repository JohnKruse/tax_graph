"""Tests for the generated three-column review panel pilot.

These tests intentionally exercise the real M20-S68 candidate workspace.  A
toy graph would not prove that the panel preserves the 157-anchor denominator,
the held-back rows, or the graph edge roles found in the corpus.
"""

from __future__ import annotations

import os
from pathlib import Path
import re

from review_panel import _flow_tree_html, build_panel, main, render_html


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


def test_rendered_html_has_one_panel_per_anchor_and_nonempty_hole_columns() -> None:
    html = render_html(_real_panel())

    assert html.count('<article class="review-panel"') == 157
    assert 'data-flow-mode="diagram"' in html
    assert 'data-flow-mode="chain"' in html
    assert 'data-hole="true"' in html
    assert "No promoted graph operation." in html
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
    assert "Graph terminology to report (not changed)" in html


def test_cli_writes_the_self_contained_artifact(tmp_path: Path) -> None:
    output = tmp_path / "review_panel.html"
    assert main([str(CANDIDATE), "--output", str(output)]) == 0
    contents = output.read_text(encoding="utf-8")
    assert contents.startswith("<!doctype html>")
    assert "<meta charset=\"utf-8\">" in contents
