from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from tax_graph.ingest.instruction_promotion import (
    join_instruction_sections,
    section_quote,
)
from tax_graph.ingest.instruction_sections import instruction_document_contexts, mine_instruction_html


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
def test_join_reports_an_expected_document_with_zero_promoted_sections() -> None:
    html = '<h2 id="id509">Instructions for Schedule 1-A Additional Deductions</h2>'
    contexts = instruction_document_contexts(html)

    result = join_instruction_sections(
        (),
        [_address("schedule_1a_2025", "1")],
        source_document_id="instructions_form_1040_2025",
        expected_document_ids=("schedule_1a_2025",),
        expected_contexts={context.document_id: context for context in contexts},
    )

    finding = next(item for item in result.findings if item.reason == "empty_expected_document")
    assert finding.document_id == "schedule_1a_2025"
    assert "anchor=id509" in finding.evidence
    assert finding.observed == "promoted_section_count=0"


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
    contexts = instruction_document_contexts(html_path.read_text(encoding="ascii"))
    assert {context.document_id for context in contexts} == {
        "form_1040_2025",
        "schedule_1_2025",
        "schedule_1a_2025",
        "schedule_2_2025",
        "schedule_3_2025",
    }
    schedule_1a = next(context for context in contexts if context.document_id == "schedule_1a_2025")
    assert schedule_1a.heading.anchor_id == "id509"
    assert not any(
        any("schedule 1-a" in parent.lower() for parent in section.parent_headings)
        for section in sections
    )


@pytest.mark.m18
def test_real_instruction_findings_are_persisted_in_deferred_queue() -> None:
    root = Path(__file__).resolve().parents[1]
    html_path = root / ".cache" / "raw" / "2025" / "instructions_form_1040_2025.html"
    queue_path = root / "review_queue" / "2025" / "deferred_review.yaml"
    if not html_path.exists() or not queue_path.exists():
        pytest.skip("acquired HTML and committed review queue are not available")

    queue = yaml.safe_load(queue_path.read_text(encoding="utf-8"))
    findings = [
        entry
        for entry in queue.get("entries", [])
        if isinstance(entry, dict) and entry.get("kind") == "instruction_join_review"
    ]

    assert len(findings) == 62
    assert all(entry["status"] == "deferred" for entry in findings)
    empty = next(entry for entry in findings if entry["reason"] == "empty_expected_document")
    assert empty["document_id"] == "schedule_1a_2025"
    assert "anchor=id509" in empty["evidence"]
    assert all(entry.get("evidence") for entry in findings)
