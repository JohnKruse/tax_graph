from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from tax_graph.ingest.instruction_promotion import (
    join_instruction_sections,
    section_quote,
)
from tax_graph.ingest.instruction_sections import mine_instruction_html


def _address(document_id: str, token: str, suffix: str = "amount", *, refs=None):
    return SimpleNamespace(
        address_id=f"2025/document={document_id.removesuffix('_2025')}/line={token}/control={suffix}",
        document_id=document_id,
        kind="option" if suffix != "amount" else "control",
        official_ref=token,
        raw={"citation_refs": list(refs or [])},
    )


@pytest.mark.m18
def test_join_expands_multi_line_sections_and_preserves_title() -> None:
    html = (
        '<h2 id="root">Line Instructions for Forms 1040 and 1040-SR</h2>'
        '<h3 id="lines-4">Lines 4a, 4b, and 4c - IRA Distributions</h3>'
        '<p>Enter the distribution amount.</p>'
    )
    sections = mine_instruction_html(html, document_id="instructions_form_1040_2025")
    addresses = [_address("form_1040_2025", token) for token in ("4a", "4b", "4c")]

    result = join_instruction_sections(
        sections,
        addresses,
        source_document_id="instructions_form_1040_2025",
    )

    assert not result.findings
    assert len(result.joins) == 1
    join = result.joins[0]
    assert set(join.address_ids) == {item.address_id for item in addresses}
    assert join.section.semantic_title == "IRA Distributions"
    assert section_quote(join.section) == "Enter the distribution amount."
    assert "- 4a:" not in join.quoted_text


@pytest.mark.m18
def test_join_fails_closed_for_unresolved_context_and_missing_address() -> None:
    sections = mine_instruction_html(
        '<h2 id="unknown">Other instructions</h2>'
        '<h3 id="line-9">Line 9 - Unknown</h3>'
        '<p>Enter a value.</p>',
        document_id="instructions_form_1040_2025",
    )
    result = join_instruction_sections(
        sections,
        [_address("form_1040_2025", "8")],
        source_document_id="instructions_form_1040_2025",
    )

    assert not result.joins
    assert result.findings[0].reason == "unresolved_document_context"
    assert result.findings[0].as_dict()["queue_id"].startswith("instruction_join_")


@pytest.mark.m18
def test_real_1040_sections_have_stable_anchor_locators_and_source_quotes() -> None:
    root = Path(__file__).resolve().parents[1]
    html_path = root / ".cache" / "raw" / "2025" / "instructions_form_1040_2025.html"
    if not html_path.exists():
        pytest.skip("acquired 1040 HTML is not available")
    sections = mine_instruction_html(html_path.read_text(encoding="ascii"), document_id="instructions_form_1040_2025")
    assert len(sections) == 143
    assert all(section.heading.anchor_id for section in sections)
    assert all(section_quote(section) for section in sections)
    assert sum(bool(section.semantic_title) for section in sections) == 86
