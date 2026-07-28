from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.acquire.render_form import extract_field_grid, extract_line_markdown
from tax_graph.extract.inputs import load_document_input
from tax_graph.extract.models import SourceDocumentInput
from tax_graph.extract.outline import build_candidate_spans, build_outline_tree
from tax_graph.extract.outline_pipeline import _span_for_line
from tax_graph.extract.structure import build_structure_model


ROOT = Path(__file__).resolve().parents[1]


def _document_or_skip(document_id: str):
    text_path = ROOT / ".cache" / "raw" / "2025" / f"{document_id}.txt"
    fields_path = ROOT / ".cache" / "raw" / "2025" / f"{document_id}.fields.json"
    pdf_path = ROOT / ".cache" / "raw" / "2025" / f"{document_id}.pdf"
    if not all(path.exists() for path in (text_path, fields_path, pdf_path)):
        pytest.skip(f"local acquired {document_id} structure artifacts are not present")
    return load_document_input(document_id, year="2025", root=ROOT)


def _flatten(nodes):
    result = []
    for node in nodes:
        result.append(node)
        result.extend(_flatten(node.children))
    return result


@pytest.mark.m20
def test_schedule_a_structure_is_geometry_derived_and_line_16_is_anchored():
    document = _document_or_skip("schedule_a_2025")
    model = build_structure_model(document)
    assert model is not None
    assert model.rows
    assert model.coverage == 1.0

    outline = build_outline_tree(document)
    nodes = _flatten(outline.children)
    line_16 = [node for node in nodes if node.line_anchor == "16"]
    assert len(line_16) == 1
    assert "Other-from list in instructions. List type and amount:" in line_16[0].label

    span = _span_for_line(document, line_16[0], build_candidate_spans(document))
    assert span is not None
    assert "Other-from list in instructions. List type and amount:" in span.text


@pytest.mark.m20
def test_form_1040_structure_uses_left_defining_token_for_1z():
    document = _document_or_skip("form_1040_2025")
    outline = build_outline_tree(document)
    nodes = _flatten(outline.children)
    line_1z = [node for node in nodes if node.line_anchor == "1z"]
    assert len(line_1z) == 1
    assert line_1z[0].label.startswith("z Add lines 1a through 1h")

    span = _span_for_line(document, line_1z[0], build_candidate_spans(document))
    assert span is not None
    assert "Add lines 1a through 1h 1z" in span.text


@pytest.mark.m20
def test_geometry_only_document_reports_anchorless_structure_and_caption_coverage():
    document = _document_or_skip("form_13614_c_2025")
    model = build_structure_model(document)
    assert model is not None
    assert len(model.rows) >= 200
    assert model.total_fields == 297
    assert model.coverage >= 0.99
    assert any(finding.code == "no_line_anchors" for finding in model.findings)

    outline = build_outline_tree(document)
    assert len(_flatten(outline.children)) >= 100


@pytest.mark.m20
@pytest.mark.parametrize(
    "filename",
    [
        "california_form_540_2024.pdf",
        "irs_form_1040_1999.pdf",
    ],
)
def test_structure_reads_producer_robustness_corpus(filename: str):
    pytest.importorskip("fitz")
    pdf_path = ROOT / "tests" / "fixtures" / "m20_producer_corpus" / filename
    if not pdf_path.exists():
        pytest.skip("producer robustness fixture is not present")
    document = SourceDocumentInput(
        document_id=filename.removesuffix(".pdf"),
        kind="tax_form",
        year="2024",
        url="https://example.invalid/producer-corpus",
        text=extract_line_markdown(pdf_path),
        text_path=pdf_path,
        fields=extract_field_grid(pdf_path),
        fields_path=pdf_path,
    )
    model = build_structure_model(document)
    assert model is not None
    assert model.rows
    assert model.coverage >= 0.75
