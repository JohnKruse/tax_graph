from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.extract.inputs import load_document_input
from tax_graph.extract.models import SourceDocumentInput
from tax_graph.extract.outline import OutlineNode, build_candidate_spans
from tax_graph.extract.outline_pipeline import SpanResolutionError, _span_for_line


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
def test_line_span_resolution_fails_closed_when_anchor_is_absent_from_index():
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

    with pytest.raises(SpanResolutionError, match="line anchor 16 absent"):
        _span_for_line(
            document,
            OutlineNode("root_line_16", "line", "Other-from list", line_anchor="16"),
            build_candidate_spans(document),
        )


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
