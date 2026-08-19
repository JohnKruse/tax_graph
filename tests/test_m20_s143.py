"""M20-S143 tests for narrowest-owner instruction projection."""

from __future__ import annotations

from pathlib import Path

import pytest

from workbench import generated_review
from workbench.generated_review import build_generated_document_cells


ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    not (ROOT / "graph" / "2025" / "_drafts").exists(),
    reason="live review drafts are required: fresh checkouts carry no _drafts",
)


@pytest.mark.m20
def test_instruction_span_index_puts_narrow_owner_before_family() -> None:
    spans = {
        "span_family": {
            "span_id": "span_family",
            "document_id": "instructions_form_1040_2025",
            "relationship": "instructions",
            "owner_lines": ["8a", "8b", "8c"],
            "text": "## Lines 8a Through 8c\n\nEnter the amount.",
        },
        "span_line_8b": {
            "span_id": "span_line_8b",
            "document_id": "instructions_form_1040_2025",
            "relationship": "instructions",
            "owner_lines": ["8b"],
            "text": "#### Line 8b\n\nEnter the amount from the worksheet.",
        },
    }

    index = generated_review._instruction_span_index(spans)

    assert index["8b"] == ["span_line_8b", "span_family"]
    assert index["8a"] == ["span_family"]


@pytest.mark.m20
def test_instruction_span_index_prefers_content_when_owner_width_ties() -> None:
    spans = {
        "span_heading_stub": {
            "span_id": "span_heading_stub",
            "document_id": "instructions_form_1040_2025",
            "relationship": "instructions",
            "owner_lines": ["1"],
            "text": "#### Line 1\n\n",
        },
        "span_content": {
            "span_id": "span_content",
            "document_id": "instructions_form_1040_2025",
            "relationship": "instructions",
            "owner_lines": ["1"],
            "text": "# State and Local Income Tax Refund Worksheet\n\nComplete the worksheet.",
        },
    }

    index = generated_review._instruction_span_index(spans)

    assert index["1"] == ["span_content", "span_heading_stub"]


@pytest.mark.m20
def test_s143_projects_narrow_owner_first_and_scopes_schedule_1() -> None:
    schedule_1 = build_generated_document_cells(ROOT, 2025, "schedule_1_2025").cells
    by_anchor = {
        str(cell.get("official_ref") or "").lower(): cell
        for cell in schedule_1
        if cell.get("instruction_citations")
    }

    line_8j = by_anchor["8j"]["instruction_citations"]
    assert line_8j[0]["citation_id"].endswith("section_0077__line_8j")
    assert line_8j[1]["citation_id"] == "span_instructions_form_1040_2025_section_0067"
    assert "Activity not engaged in for profit income" in line_8j[0]["quoted_text"]

    line_24z = by_anchor["24z"]["instruction_citations"]
    assert line_24z[0]["citation_id"].endswith("section_0121__line_24z")
    assert line_24z[1]["citation_id"] == "span_instructions_form_1040_2025_section_0109"
    assert "Leave line 24z blank" in line_24z[0]["quoted_text"]

    line_1 = by_anchor["1"]["instruction_citations"]
    assert [item["citation_id"] for item in line_1] == [
        "span_instructions_form_1040_2025_section_0068",
        "span_instructions_form_1040_2025_section_0139__line_1",
        "span_instructions_form_1040_2025_section_0060__line_1",
    ]
    assert line_1[0]["quoted_text"].startswith(
        "# **State and Local Income Tax Refund WorksheetSchedule 1, Line 1**"
    )
