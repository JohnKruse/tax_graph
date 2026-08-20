"""M20-S154 tests for real review-surface marker matching."""

from __future__ import annotations

from pathlib import Path
import re

from tax_graph.core_refusal_gate import evaluate_core_refusals


ROOT = Path(__file__).resolve().parents[1]


def test_real_corpus_gate_demonstrates_both_surfacing_directions() -> None:
    """Check both outcomes against the stored review HTML, including Schedule 1 line 1."""
    report = evaluate_core_refusals(root=ROOT, year="2025")

    schedule_one = [
        item
        for item in report.candidates
        if item.document_id == "schedule_1_2025" and item.line == "1"
    ]
    assert schedule_one
    assert all(item.surfaced for item in schedule_one)
    schedule_one_html = (
        ROOT / "graph" / "2025" / "_drafts" / "schedule_1_2025" / "review.html"
    ).read_text(encoding="ascii")
    assert (
        'data-object="obj-nodes-schedule-1-2025-section-1-part-i-additional-income-line-1"'
        in schedule_one_html
    )

    form_1040 = [
        item
        for item in report.candidates
        if item.document_id == "form_1040_2025" and item.line == "31"
    ]
    assert form_1040
    assert all(not item.surfaced for item in form_1040)
    form_1040_html = (ROOT / "graph" / "2025" / "_drafts" / "form_1040_2025" / "review.html").read_text(
        encoding="ascii"
    )
    assert 'data-object="obj-nodes-form-1040-2025' in form_1040_html
    assert not re.search(
        r'data-object="obj-nodes-form-1040-2025(?:-[a-z0-9]+)*-line-31(?:-|\")',
        form_1040_html,
    )


def test_instruction_documents_are_not_reviewable_cell_candidates() -> None:
    """Instruction booklets have no printed lines, so no FORM-LINE candidate can surface.

    This assertion was broader when written on 2026-08-20: it required that an
    instructions document contribute no candidates at all.  That pinned an
    over-broad filter which dropped 16 unmodeled frontier refusals and 4
    worksheet refusals owned by instructions_form_1040_2025, none of them
    form-line candidates.  A refused worksheet still has to reach a human
    whichever document's instructions spawned it, so the exclusion now keys on
    the candidate's kind rather than the owner's.
    """
    report = evaluate_core_refusals(root=ROOT, year="2025")
    owned = [
        item
        for item in report.candidates
        if item.owner_document_id == "instructions_form_1040_2025"
    ]

    assert not any(
        item.kind in {"derive_cell_status", "formula_review_gap", "not_derivable_outcome"}
        for item in owned
    )
    assert owned, "instruction-owned worksheet and frontier refusals must survive the filter"
    assert {item.kind for item in owned} <= {"worksheet_refusal", "frontier_refusal"}
