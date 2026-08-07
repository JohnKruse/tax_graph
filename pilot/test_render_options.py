"""Tests for the M20-S80 rendering comparison pilot."""

from __future__ import annotations

import os
from pathlib import Path

from render_options import FIXED_CELLS, build_comparison, build_panel, main, render_html


CANDIDATE = Path(os.environ.get("M20_S77_CANDIDATE", r"C:\tmp\m20_s68_candidate"))


def _comparison() -> dict:
    if not CANDIDATE.is_dir():
        raise AssertionError(f"required real candidate workspace is missing: {CANDIDATE}")
    return build_comparison(build_panel(CANDIDATE))


def test_all_five_renderings_cover_the_full_denominator() -> None:
    comparison = _comparison()

    assert comparison["denominator"] == 157
    for name, metric in comparison["metrics"].items():
        assert metric["attempted"] == 157, name
        assert metric["produced"] == 157, name
        assert metric["failures"] == 0, comparison["failures"][name]


def test_fixed_cells_are_the_same_across_all_options_and_line_25_is_absent() -> None:
    comparison = _comparison()

    assert tuple(tuple(item.split(" line ")) for item in comparison["fixed_cells"]) == FIXED_CELLS
    hole = comparison["selected"][-1]
    assert hole["document_id"] == "form_2441_2025"
    assert hole["line"] == "25"
    assert hole["hole"] is True
    for item in hole["renderings"].values():
        assert "line 25" in item["content"].lower()
        assert "review finding" in item["content"].lower()
        assert "lookup table inputs must be named leaf values with roles" in item["content"].lower()
        assert "valueerror" not in item["content"].lower()
        assert "payload" not in item["content"].lower()


def test_s79_uses_a_table_chain_math_or_finding_for_non_branch_cells() -> None:
    comparison = _comparison()

    selected = {(item["document_id"], item["line"]): item for item in comparison["selected"]}
    lookup = selected[("form_2441_2025", "8")]["renderings"]["flowchart"]["content"]
    operation = selected[("form_2441_2025", "20")]["renderings"]["flowchart"]["content"]
    subtraction = selected[("form_2441_2025", "23")]

    assert '<table class="lookup-table">' in lookup
    assert "<svg" not in lookup
    assert '<div class="operation-chain">' in operation
    assert operation.count('class="chain-box"') == 2
    assert "min(line 17, line 18, line 19)" in operation
    assert "max(amount, 0)" in operation
    assert "<svg" not in operation
    assert subtraction["renderings"]["flowchart"]["content"].find(
        "line 23 = line 15 - line 22"
    ) >= 0
    english = subtraction["renderings"]["english"]["content"]
    assert english == "line 23: Subtract line 22 from line 15."
    assert "minuend" not in english.lower()
    assert "subtrahend" not in english.lower()


def test_renderings_do_not_leak_graph_ids_or_specialist_terms() -> None:
    comparison = _comparison()
    forbidden = ("_root_", "taxpayer_2025_", "node_")
    banned_terms = ("floor", "ceiling", "clamp", "truncate")

    for items in comparison["inventory"].values():
        for item in items:
            content = item["content"].lower()
            assert not any(token in content for token in forbidden), item
            assert not any(token in content for token in banned_terms), item


def test_flowchart_and_registry_english_are_real_renderings() -> None:
    comparison = _comparison()
    flow = comparison["selected"][0]["renderings"]["flowchart"]["content"]
    english = comparison["selected"][0]["renderings"]["english"]["content"]

    assert "<svg" in flow
    assert "<polygon" in flow
    assert "Yes" in flow
    assert "No" in flow
    assert "Choose between two values using a comparison." in english


def test_s79_branch_has_separate_inputs_tables_arms_and_rejoin() -> None:
    comparison = _comparison()
    flow = comparison["selected"][0]["renderings"]["flowchart"]["content"]

    assert flow.count('<polygon class="svg-diamond"') == 1
    assert flow.count('<rect class="svg-table-node"') == 2
    assert "line 17 &lt;= threshold?" in flow
    assert "line 17 * 0.26" in flow
    assert "line 17 * 0.28" in flow
    assert "amount - offset" in flow
    assert "line 18" in flow
    assert 'data-connector-starts-unique="true"' in flow
    assert 'data-edge-labels-outside-nodes="true"' in flow


def test_html_contains_the_five_side_by_side_options_and_measurements() -> None:
    html = render_html(_comparison())

    assert html.count('<article class="cell-card">') == 5
    assert html.count("class=\"rendering-card") == 25
    assert "Five generated renderings of the same cells" in html
    assert "157/157" in html
    assert "All five renderers produced output for every printed anchor." in html
    assert "form_2441_2025_root_line_20" not in html
    assert "form_2441_2025_zero_floor" not in html
    assert "&lt;div class=\"" not in html
    assert "&lt;table class=\"" not in html
    assert "valueerror" not in html.lower()
    assert "&#x27;kind&#x27;" not in html
    assert "connector start points and directions unique: checked" in html
    assert "edge labels outside every other node box: checked" in html


def test_s80_makes_svg_and_lookup_table_previews_openable_without_network() -> None:
    html = render_html(_comparison())

    assert html.count('class="preview-trigger"') == 2
    assert html.count('class="preview-content"') == 2
    assert html.count("Click to enlarge") == 2
    assert '<dialog class="rendering-lightbox" id="rendering-lightbox"' in html
    assert "data-lightbox-close" in html
    assert "dialog.showModal()" in html
    assert "dialog.close()" in html
    assert "event.target === dialog" in html
    assert 'event.key === "Escape"' in html
    assert "<script src=" not in html
    assert "<link " not in html
    assert "http://" not in html
    assert "https://" not in html


def test_s79_reports_vertical_svg_dimensions_and_zero_placeholders() -> None:
    comparison = _comparison()

    for name, metric in comparison["metrics"].items():
        assert metric["empty_or_placeholder"] == 0, name

    dimensions = comparison["metrics"]["flowchart"]["svg_dimensions"]
    assert dimensions
    assert all(item["width"] <= 320 for item in dimensions)
    assert all(item["viewbox_width"] <= 320 for item in dimensions)
    assert all(item["height"] > 0 for item in dimensions)
    line_18 = next(item for item in dimensions if item["line"] == "18")
    assert line_18["height"] > line_18["width"]
    assert comparison["geometry_checks"] == {
        "svg_count": 3,
        "connector_start_directions_unique": True,
        "edge_labels_outside_nodes": True,
    }


def test_cli_writes_the_comparison_artifact(tmp_path: Path) -> None:
    output = tmp_path / "m20_s77_renderings.html"

    assert main([str(CANDIDATE), "--output", str(output)]) == 0
    contents = output.read_text(encoding="utf-8")
    assert contents.startswith("<!doctype html>")
    assert "<meta charset=\"utf-8\">" in contents
