from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.extract.cells import (
    _render_cell_prompt,
    build_cell_frame_from_document,
    load_cell_prompt,
    validate_cell_input,
)
from tax_graph.extract.inputs import load_document_input
from tax_graph.extract.structure import split_caption_and_instruction


ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.m20


def _frame(document_id: str):
    raw = ROOT / ".cache" / "raw" / "2025" / f"{document_id}.txt"
    fields = ROOT / ".cache" / "raw" / "2025" / f"{document_id}.fields.json"
    pdf = ROOT / ".cache" / "raw" / "2025" / f"{document_id}.pdf"
    if not all(path.exists() for path in (raw, fields, pdf)):
        pytest.skip(f"local acquired {document_id} artifacts are not present")
    return build_cell_frame_from_document(load_document_input(document_id, year="2025", root=ROOT))


def test_caption_split_is_verbatim_and_fails_closed_for_ambiguous_text() -> None:
    split = split_caption_and_instruction(
        "25 Excluded benefits. If you checked No, enter the smaller amount.",
        "25",
    )
    assert split.caption == "Excluded benefits."
    assert split.cell_instruction == "If you checked No, enter the smaller amount."
    assert split.status == "captioned"

    no_caption = split_caption_and_instruction("6 Enter the smallest of line 3, 4, or 5.", "6")
    assert no_caption.caption is None
    assert no_caption.cell_instruction == "Enter the smallest of line 3, 4, or 5."
    assert no_caption.status == "none"
    assert no_caption.finding is None

    ambiguous = split_caption_and_instruction("(a) A boundary the parser cannot classify. Enter it.", "")
    assert ambiguous.caption is None
    assert ambiguous.cell_instruction == "(a) A boundary the parser cannot classify. Enter it."
    assert ambiguous.status == "ambiguous"
    assert ambiguous.finding == "caption_ambiguous"


def test_real_corpus_caption_distribution_is_measured_and_conservative() -> None:
    frames = [_frame(document_id) for document_id in (
        "form_2441_2025",
        "form_1040_2025",
        "form_6251_2025",
        "schedule_1a_2025",
    )]
    rows = [row for frame in frames for row in frame.rows]
    assert len(rows) == 96
    assert sum(row.metadata["caption_status"] == "captioned" for row in rows) == 12
    assert sum(row.metadata["caption_status"] == "none" for row in rows) == 84
    assert sum(row.metadata["caption_status"] == "ambiguous" for row in rows) == 0
    assert all(not row.metadata["caption_finding"] for row in rows)
    assert all(
        row.label == row.metadata["caption"]
        for row in rows
        if row.metadata["caption_status"] == "captioned"
    )
    assert all(
        row.label == ""
        for row in rows
        if row.metadata["caption_status"] != "captioned"
    )


def test_s58_target_packets_separate_caption_and_instruction() -> None:
    form_2441 = next(row for row in _frame("form_2441_2025").rows if row.line == "25")
    assert form_2441.label == "Excluded benefits."
    assert form_2441.form_face_text == (
        'If you checked "No" on line 22, enter the smaller of line 20 or line 21. '
        "Otherwise, subtract line 24 from the smaller of line 20 or line 21. "
        "If zero or less, enter -0-"
    )
    assert form_2441.instruction_text == ""

    form_1040 = next(row for row in _frame("form_1040_2025").rows if row.line == "15")
    assert form_1040.label == ""
    assert form_1040.form_face_text == (
        "Subtract line 14 from line 11b. If zero or less, enter -0-. "
        "This is your taxable income"
    )
    assert form_1040.instruction_text == ""

    template = load_cell_prompt(root=ROOT)
    packet_2441 = _render_cell_prompt(template, form_2441)
    packet_1040 = _render_cell_prompt(template, form_1040)
    assert "label: Excluded benefits." in packet_2441
    assert "form face text:\nIf you checked \"No\" on line 22" in packet_2441
    assert "label: \n" in packet_1040
    assert "form face text:\nSubtract line 14 from line 11b." in packet_1040


def test_captionless_real_row_is_valid_input_with_named_status() -> None:
    row = next(row for row in _frame("form_1040_2025").rows if row.line == "15")
    assert validate_cell_input(row) == ()
    assert row.metadata["caption_status"] == "none"
