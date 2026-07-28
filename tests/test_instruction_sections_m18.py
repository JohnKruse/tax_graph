from __future__ import annotations

import pytest

from tax_graph.ingest.instruction_sections import instruction_document_contexts, mine_instruction_html


@pytest.mark.m18
def test_mine_instruction_html_emits_typed_blocks_and_stable_spans():
    html = """
    <h2 id="root">Instructions</h2>
    <h3 id="line-1">Line 1</h3>
    <h4 id="title-1">Taxable income details</h4>
    <p>Enter the amount from Form W-2.</p>
    <p><strong>Exception.</strong> Do not include excluded wages.</p>
    <ul><li>Example 1: use the corrected amount.</li></ul>
    <h3 id="line-2">Line 2</h3>
    <table><tr><td>Worksheet values</td></tr></table>
    <p>See the Schedule 1 instructions.</p>
    """

    sections = mine_instruction_html(html, document_id="instructions_form_1040_2025")

    assert [section.line_tokens for section in sections] == [("1",), ("2",)]
    first = sections[0]
    assert first.semantic_title == "Taxable income details"
    assert [block.block_type for block in first.blocks] == [
        "paragraph",
        "exception",
        "example",
    ]
    assert first.blocks[0].text == "Enter the amount from Form W-2."
    assert first.source_start < first.blocks[0].source_start < first.source_end
    assert first.source_end == sections[1].source_start
    assert [block.block_type for block in sections[1].blocks] == ["worksheet", "cross_reference"]
    assert all(block.source_start < block.source_end for section in sections for block in section.blocks)


@pytest.mark.m18
def test_document_context_inventory_exposes_schedule_1a_without_line_sections() -> None:
    html = (
        '<h2 id="id509">Instructions for Schedule 1-A Additional Deductions</h2>'
        '<h3 id="part-i">Part I Modified Adjusted Gross Income (MAGI) Amount</h3>'
    )

    contexts = instruction_document_contexts(html)

    assert [(context.document_id, context.heading.anchor_id) for context in contexts] == [
        ("schedule_1a_2025", "id509")
    ]
    assert mine_instruction_html(html, document_id="instructions_form_1040_2025") == ()
