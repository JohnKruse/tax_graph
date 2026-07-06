from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.extract.inputs import load_document_input
from tax_graph.extract.outline import build_outline_tree


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_RAW = ROOT / "tests" / "fixtures" / "schedule_d_bundle" / "raw"


@pytest.mark.m9
def test_schedule_d_fixture_bundle_loads_with_related_instructions():
    document = load_document_input("schedule_d_2025", year="2025", root=ROOT, raw_store=FIXTURE_RAW)
    instructions = document.related_sources[0]

    assert document.document_id == "schedule_d_2025"
    assert document.fields_path is not None
    assert "SCHEDULE D Capital Gains and Losses" in document.text
    assert "Instructions for Schedule D (Form 1040)" in instructions.text
    assert "Future Developments" in instructions.text
    assert "Line 21" in instructions.text
    anchors = {field["line_anchor"] for field in document.fields["fields"]}
    assert {"1b", "2", "3", "8b", "9", "10", "21"} <= anchors


@pytest.mark.m9
def test_schedule_d_outline_has_parts_row_bands_and_line_21():
    document = load_document_input("schedule_d_2025", year="2025", root=ROOT, raw_store=FIXTURE_RAW)
    outline = build_outline_tree(document)
    by_section = {section.outline_id: section for section in outline.children if section.kind == "section"}

    assert {"part_i", "part_ii", "part_iii"} <= set(by_section)
    part_i = {node.line_anchor: node for node in by_section["part_i"].children}
    part_ii = {node.line_anchor: node for node in by_section["part_ii"].children}
    part_iii = {node.line_anchor: node for node in by_section["part_iii"].children}

    assert {part_i[line].kind for line in ["1b", "2", "3"]} == {"transaction_table"}
    assert {part_ii[line].kind for line in ["8b", "9", "10"]} == {"transaction_table"}
    assert part_iii["21"].kind == "line"
    assert "smaller of" in part_iii["21"].label
