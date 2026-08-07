"""Tests for the M20-S77 five-rendering comparison pilot."""

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
        assert "generated operation needs review" in item["content"].lower()
        assert "valueerror" not in item["content"].lower()
        assert "payload" not in item["content"].lower()


def test_s78_uses_a_table_math_or_finding_for_non_branch_cells() -> None:
    comparison = _comparison()

    selected = {(item["document_id"], item["line"]): item for item in comparison["selected"]}
    lookup = selected[("form_2441_2025", "8")]["renderings"]["flowchart"]["content"]
    operation = selected[("form_2441_2025", "20")]["renderings"]["flowchart"]["content"]
    subtraction = selected[("form_2441_2025", "23")]

    assert '<table class="lookup-table">' in lookup
    assert "<svg" not in lookup
    assert "line 20 = max(0, min(line 17, line 18, line 19))" in operation
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


def test_s78_reports_vertical_svg_dimensions_and_zero_placeholders() -> None:
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


def test_cli_writes_the_comparison_artifact(tmp_path: Path) -> None:
    output = tmp_path / "m20_s77_renderings.html"

    assert main([str(CANDIDATE), "--output", str(output)]) == 0
    contents = output.read_text(encoding="utf-8")
    assert contents.startswith("<!doctype html>")
    assert "<meta charset=\"utf-8\">" in contents
