"""M20-S91 tests for printed-bracket clause extent."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from tax_graph.extract.cells import clean_form_face_text_with_extent, build_cell_frame_from_document
from tax_graph.extract.inputs import load_document_input
from tax_graph.extract.models import SourceDocumentInput
from tax_graph.extract.outline_pipeline import _bracketed_source_text


ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.m20


def test_bracketed_source_text_joins_wrapped_clause_and_drops_dot_leaders() -> None:
    text = (
        "2a Prior row 2a\n"
        "b Correct clause starts here\n"
        ". . . .\n"
        "and continues on the next source row 2b\n"
        "2c Next row 2c\n"
    )
    document = SourceDocumentInput(
        document_id="form_test_2025",
        kind="tax_form",
        year="2025",
        url="https://example.test/form.pdf",
        text=text,
        text_path=ROOT / "tests" / "fixtures" / "form_test.txt",
        fields={
            "fields": [],
            "line_anchors": [
                {"anchor": "2a", "text_offset": text.index("2a")},
                {"anchor": "2b", "text_offset": text.index("2b")},
                {"anchor": "2c", "text_offset": text.index("2c")},
            ],
        },
    )

    assert _bracketed_source_text(
        document,
        anchor="2b",
        anchor_offset=text.index("2b"),
    ) == "Correct clause starts here and continues on the next source row"


def test_bracket_selection_repairs_weak_face_but_preserves_good_face() -> None:
    selected, diagnostic = clean_form_face_text_with_extent(
        "b Tax refund from Schedule 1 2b ( )",
        "2b",
        bracket_text="Tax refund from Schedule 1",
    )
    assert selected == "Tax refund from Schedule 1"
    assert diagnostic["method"] == "bracket"
    assert diagnostic["disagreement"] == "bracket_longer"

    selected, diagnostic = clean_form_face_text_with_extent(
        "35 Add lines 17, 32, and 33 35",
        "35",
        bracket_text="Add lines 17, 32, and 33 through 37 and go to line 38",
    )
    assert selected == "35 Add lines 17, 32, and 33"
    assert diagnostic["method"] == "fallback"
    assert diagnostic["disagreement"] == "bracket_longer"


def test_real_corpus_repairs_all_42_weak_packets_and_reports_both_directions() -> None:
    document_ids = [
        "form_1040_2025",
        "form_2441_2025",
        "form_6251_2025",
        "schedule_1_2025",
        "schedule_1a_2025",
        "schedule_2_2025",
        "schedule_3_2025",
        "schedule_a_2025",
        "schedule_b_2025",
        "schedule_d_2025",
        "form_8949_2025",
    ]
    required = [
        ROOT / ".cache" / "raw" / "2025" / f"{document_id}.{suffix}"
        for document_id in document_ids
        for suffix in ("txt", "fields.json", "pdf")
    ]
    if not all(path.is_file() for path in required):
        pytest.skip("local acquired M20 corpus artifacts are not present")

    selected: set[tuple[str, str]] = set()
    selected_faces: dict[tuple[str, str], str] = {}
    directions = Counter()
    for document_id in document_ids:
        frame = build_cell_frame_from_document(
            load_document_input(document_id, year="2025", root=ROOT)
        )
        for row in frame.rows:
            extent = row.metadata["clause_extent"]
            directions[extent["disagreement"] or "agree"] += 1
            if extent["method"] == "bracket":
                selected.add((document_id, row.line))
                selected_faces[(document_id, row.line)] = row.form_face_text

    assert len(selected) == 42
    assert selected == {
        ("form_6251_2025", line) for line in ("2b", "2f", "2s")
    } | {
        ("schedule_1_2025", line)
        for line in ("8a", "8d", "8s", "8v", "12", "13", "14")
    } | {
        ("schedule_2_2025", line)
        for line in ("1a", "2", "5", "6", "8", "11", "12", "16", "17c", "17d", "17e", "17f")
    } | {
        ("schedule_3_2025", line)
        for line in ("1", "2", "4", "6a", "6b", "6c", "6f", "6g", "6h", "6i", "6j", "6k", "6m", "9", "12", "13a", "13b")
    } | {
        ("schedule_a_2025", line) for line in ("5e", "9", "15")
    }
    assert directions["bracket_longer"] == 44
    assert directions["fallback_longer"] == 27
    assert {"( )", "years"}.isdisjoint(
        set(selected_faces.values())
    )
