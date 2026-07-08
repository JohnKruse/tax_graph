from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.extract.inputs import load_document_input
from tax_graph.extract.outline import build_outline_tree


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_RAW = ROOT / "tests" / "fixtures" / "m10_batch_bundle" / "raw"


@pytest.mark.m10
@pytest.mark.parametrize(
    ("document_id", "instruction_id", "title_fragment", "expected_outline_ids"),
    [
        ("schedule_1_2025", "instructions_form_1040_2025", "SCHEDULE 1", {"part_i", "part_ii"}),
        ("schedule_1a_2025", "instructions_form_1040_2025", "SCHEDULE 1-A", {"part_i", "part_ii", "part_iii"}),
        ("schedule_2_2025", "instructions_form_1040_2025", "SCHEDULE 2", {"part_i", "part_ii"}),
        ("schedule_3_2025", "instructions_form_1040_2025", "SCHEDULE 3", {"part_i", "part_ii"}),
        ("schedule_a_2025", "instructions_schedule_a_2025", "SCHEDULE A", {"root_line_1"}),
        ("schedule_b_2025", "instructions_schedule_b_2025", "SCHEDULE B", {"part_i", "part_ii", "part_iii"}),
        ("form_6251_2025", "instructions_form_6251_2025", "Form 6251", {"part_i", "part_ii"}),
    ],
)
def test_batch_fixture_bundle_loads_related_instructions_and_outline(document_id, instruction_id, title_fragment, expected_outline_ids):
    document = load_document_input(document_id, year="2025", root=ROOT, raw_store=FIXTURE_RAW)
    outline = build_outline_tree(document)

    assert document.text_path.name == f"{document_id}.txt"
    assert title_fragment in document.text
    assert document.fields_path is not None
    assert document.related_sources and document.related_sources[0].document_id == instruction_id
    assert document.related_sources[0].text_path.name == f"{instruction_id}.txt"
    assert "Future Developments" in document.related_sources[0].text
    outline_ids = {node.outline_id for node in outline.children}
    assert expected_outline_ids <= outline_ids


@pytest.mark.m10
def test_schedule_b_fixture_outline_keeps_interest_and_dividend_lists_as_tables():
    document = load_document_input("schedule_b_2025", year="2025", root=ROOT, raw_store=FIXTURE_RAW)
    outline = build_outline_tree(document)
    by_section = {section.outline_id: section for section in outline.children if section.kind == "section"}

    part_i = {node.line_anchor: node for node in by_section["part_i"].children}
    part_ii = {node.line_anchor: node for node in by_section["part_ii"].children}

    assert part_i["1"].kind == "transaction_table"
    assert part_i["2"].kind == "totals"
    assert part_ii["5"].kind == "transaction_table"
    assert part_ii["6"].kind == "totals"
