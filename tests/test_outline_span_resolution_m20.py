from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.extract.cells import build_cell_frame_from_document
from tax_graph.extract.inputs import load_document_input
from tax_graph.extract.models import SourceDocumentInput
from tax_graph.extract.outline import OutlineNode, build_candidate_spans
from tax_graph.extract.outline_checks import run_outline_artifact_checks
from tax_graph.extract.outline_pipeline import _span_for_line


ROOT = Path(__file__).resolve().parents[1]


def _document(text: str, *, line_anchors: list[dict]) -> SourceDocumentInput:
    return SourceDocumentInput(
        document_id="schedule_a_2025",
        kind="schedule",
        year="2025",
        url="https://www.irs.gov/pub/irs-pdf/f1040sa.pdf",
        text=text,
        text_path=ROOT / ".cache" / "raw" / "2025" / "schedule_a_2025.txt",
        fields={"fields": [], "line_anchors": line_anchors},
    )


@pytest.mark.m20
def test_line_span_resolution_uses_corrected_schedule_a_line_anchor_index():
    text = "Other 16 Other-from list in instructions. List type and amount:\n"
    document = _document(
        text,
        line_anchors=[
            {
                "anchor": "16",
                "page": 1,
                "text_offset": text.index("16"),
                "text_length": 2,
            }
        ],
    )

    span = _span_for_line(
        document,
        OutlineNode("root_line_16", "line", "Other-from list", line_anchor="16"),
        build_candidate_spans(document),
    )

    assert span is not None
    assert span.text == "Other 16 Other-from list in instructions. List type and amount:"


@pytest.mark.m20
def test_duplicate_anchor_uses_outline_page_and_row_label():
    text = (
        "Internal Revenue Service Go to www.irs.gov/Form6251 for instructions. 32\n"
        "32 Add lines 23 and 30 32\n"
    )
    document = _document(
        text,
        line_anchors=[
            {"anchor": "32", "page": 1, "text_offset": text.index("32")},
            {
                "anchor": "32",
                "page": 2,
                "text_offset": text.rindex("32"),
            },
        ],
    )

    span = _span_for_line(
        document,
        OutlineNode(
            "part_iii_line_32",
            "line",
            "32 Add lines 23 and 30 32",
            page=2,
            line_anchor="32",
        ),
        build_candidate_spans(document),
    )

    assert span is not None
    assert span.text == "32 Add lines 23 and 30 32"


@pytest.mark.m20
def test_anchor_only_header_match_fails_closed_without_row_label_context():
    text = "# Page 2\n32 Header text only 32\n"
    document = _document(
        text,
        line_anchors=[
            {"anchor": "32", "page": 2, "text_offset": text.index("32")},
        ],
    )

    assert (
        _span_for_line(
            document,
            OutlineNode(
                "part_iii_line_32",
                "line",
                "32 Add lines 23 and 30 32",
                page=2,
                line_anchor="32",
            ),
            build_candidate_spans(document),
        )
        is None
    )


@pytest.mark.m20
def test_unresolved_anchor_reports_no_span_without_aborting_the_batch():
    """An anchor the index does not carry yields no span - it must not raise.

    Raising here made every document lacking an index unprocessable, which is not
    fail-closed but fail-fatal: form_13614_c_2025 legitimately has zero anchors.
    The fail-closed boundary is the document-level empty-outline check instead.
    """
    text = "Other 16 Other-from list in instructions. List type and amount:\n"
    document = _document(
        text,
        line_anchors=[
            {
                "anchor": "17",
                "page": 1,
                "text_offset": text.index("16"),
                "text_length": 2,
            }
        ],
    )

    assert (
        _span_for_line(
            document,
            OutlineNode("root_line_16", "line", "Other-from list", line_anchor="16"),
            build_candidate_spans(document),
        )
        is None
    )


@pytest.mark.m20
def test_document_without_any_anchor_index_resolves_to_no_span():
    text = "Are you a US citizen? Yes No\nDid anyone else live with you?\n"
    document = SourceDocumentInput(
        document_id="form_13614_c_2025",
        kind="intake",
        year="2025",
        url="https://www.irs.gov/pub/irs-pdf/f13614c.pdf",
        text=text,
        text_path=ROOT / ".cache" / "raw" / "2025" / "form_13614_c_2025.txt",
        fields={"fields": []},
    )

    assert (
        _span_for_line(
            document,
            OutlineNode("root_line_1", "line", "citizenship", line_anchor="1"),
            build_candidate_spans(document),
        )
        is None
    )


@pytest.mark.m20
def test_numeric_anchor_does_not_fall_back_to_shorter_suffix():
    text = "Other 6 Other taxes. List type and amount:\n"
    document = _document(
        text,
        line_anchors=[
            {
                "anchor": "6",
                "page": 1,
                "text_offset": text.index("6"),
                "text_length": 1,
            }
        ],
    )

    # "16" must not silently resolve through "6" - that is the D13 mis-anchoring.
    assert (
        _span_for_line(
            document,
            OutlineNode("root_line_16", "line", "Other deductions", line_anchor="16"),
            build_candidate_spans(document),
        )
        is None
    )


@pytest.mark.m20
def test_empty_outline_on_real_text_is_a_document_level_failure():
    """The fail-closed boundary: zero structure from real text is an error.

    This is the M20-S3a failure mode - an empty outline coexisting with a
    successful exit, so extraction reported success while producing nothing.
    """
    from tax_graph.extract.outline import OutlineTree

    text = "\n".join(f"line {n} of real form text with content" for n in range(1, 12))
    document = _document(text, line_anchors=[])
    report = run_outline_artifact_checks(
        document, OutlineTree(document_id="schedule_a_2025", kind="schedule"), [], []
    )

    assert any(issue.artifact == "outline_empty" for issue in report.issues)
    with pytest.raises(Exception):
        report.raise_for_issues()


@pytest.mark.m20
def test_real_schedule_a_line_16_resolves_from_local_index():
    raw_text = ROOT / ".cache" / "raw" / "2025" / "schedule_a_2025.txt"
    fields_path = ROOT / ".cache" / "raw" / "2025" / "schedule_a_2025.fields.json"
    if not raw_text.exists() or not fields_path.exists():
        pytest.skip("local corrected Schedule A acquisition artifacts are not present")

    document = load_document_input("schedule_a_2025", year="2025", root=ROOT)
    span = _span_for_line(
        document,
        OutlineNode("root_line_16", "line", "Other-from list", line_anchor="16"),
        build_candidate_spans(document),
    )

    assert span is not None
    assert "Other-from list in instructions. List type and amount:" in span.text


@pytest.mark.m20
def test_real_form_6251_line_32_uses_form_row_not_page_header():
    raw_text = ROOT / ".cache" / "raw" / "2025" / "form_6251_2025.txt"
    fields_path = ROOT / ".cache" / "raw" / "2025" / "form_6251_2025.fields.json"
    if not raw_text.exists() or not fields_path.exists():
        pytest.skip("local acquired Form 6251 artifacts are not present")

    document = load_document_input("form_6251_2025", year="2025", root=ROOT)
    frame = build_cell_frame_from_document(document)
    row = next(row for row in frame.rows if row.line == "32")

    assert row.form_face_text == "32 Add lines 23 and 30"
    assert "Internal Revenue Service" not in row.form_face_text
