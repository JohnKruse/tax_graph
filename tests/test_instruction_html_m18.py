from __future__ import annotations

import pytest

from tax_graph.acquire.instruction_html import heading_tree_lines, line_sections, parse_headings


@pytest.mark.m18
def test_instruction_html_parser_preserves_heading_anchors_and_line_tokens():
    html = """
    <h1 id="intro">Instructions for Form 1040</h1>
    <h2 id="id108">Instructions for Schedule 1</h2>
    <h3 id="id113">Lines 2a and 2b</h3>
    <h3 id="id119">Lines 19a, 19b, and 19c</h3>
    <h3 id="id167">Lines 1a Through 1z</h3>
    <h3 id="id200">Line 1 - Taxable <em>income</em></h3>
    <a name="source-anchor"></a><h4>Line 2 - Taxable income</h4>
    """

    headings = parse_headings(html)
    sections = line_sections(html)

    assert headings[1].anchor_id == "id108"
    assert headings[5].text == "Line 1 - Taxable income"
    assert headings[6].anchor_id == "source-anchor"
    assert [(item.heading.anchor_id, item.line_tokens, item.semantic_title) for item in sections] == [
        ("id113", ("2a", "2b"), ""),
        ("id119", ("19a", "19b", "19c"), ""),
        ("id167", ("1a", "1z"), ""),
        ("id200", ("1",), "Taxable income"),
        ("source-anchor", ("2",), "Taxable income"),
    ]
    assert heading_tree_lines(headings) == [
        "- Instructions for Form 1040 [intro]",
        "  - Instructions for Schedule 1 [id108]",
        "    - Lines 2a and 2b [id113]",
        "    - Lines 19a, 19b, and 19c [id119]",
        "    - Lines 1a Through 1z [id167]",
        "    - Line 1 - Taxable income [id200]",
        "      - Line 2 - Taxable income [source-anchor]",
    ]
