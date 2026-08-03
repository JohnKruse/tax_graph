from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.acquire.render_form import extract_field_grid, extract_line_markdown
from tax_graph.extract.inputs import load_document_input
from tax_graph.extract.models import SourceDocumentInput
from tax_graph.extract.outline import build_candidate_spans, build_outline_tree
from tax_graph.extract.outline_pipeline import _formula_outline_nodes, _span_for_line
from tax_graph.extract.structure import (
    StructureModel,
    StructureRow,
    build_structure_model,
    validate_anchor_identity,
)


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
    assert any(item.get("anchor") == "5d" for item in document.fields["line_anchors"])
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
    assert any(item.get("anchor") == "1z" for item in document.fields["line_anchors"])
    line_1z = [node for node in nodes if node.line_anchor == "1z"]
    assert len(line_1z) == 1
    assert line_1z[0].label.startswith("z Add lines 1a through 1h")

    span = _span_for_line(document, line_1z[0], build_candidate_spans(document))
    assert span is not None
    assert "Add lines 1a through 1h 1z" in span.text


@pytest.mark.m20
def test_geometry_anchor_identity_rejects_references_and_splits_sibling_columns():
    schedule_a = _document_or_skip("schedule_a_2025")
    schedule_a_model = build_structure_model(schedule_a)
    assert schedule_a_model is not None
    line_5d = [row for row in schedule_a_model.rows if "Add lines 5a through 5c" in row.text]
    assert [row.line_anchor for row in line_5d] == ["5d"]
    assert not any(row.line_anchor == "5a" for row in line_5d)

    form_1040 = _document_or_skip("form_1040_2025")
    form_1040_model = build_structure_model(form_1040)
    assert form_1040_model is not None
    line_1z = [row for row in form_1040_model.rows if "Add lines 1a through 1h" in row.text]
    assert [row.line_anchor for row in line_1z] == ["1z"]
    left_column = [row for row in form_1040_model.rows if "IRA distributions" in row.text]
    right_column = [row for row in form_1040_model.rows if "Taxable amount 4b" in row.text]
    assert [row.line_anchor for row in left_column] == ["4a"]
    assert [row.line_anchor for row in right_column] == ["4b"]
    assert any(row.text.startswith("Dependents") and row.line_anchor is None for row in form_1040_model.rows)

    schedule_1a = _document_or_skip("schedule_1a_2025")
    schedule_1a_model = build_structure_model(schedule_1a)
    assert schedule_1a_model is not None
    line_14c = [row for row in schedule_1a_model.rows if "Add lines 14a and 14b" in row.text]
    assert [row.line_anchor for row in line_14c] == ["14c"]
    line_36a = [row for row in schedule_1a_model.rows if row.text.startswith("36 a If you have")]
    assert [row.line_anchor for row in line_36a] == ["36a"]

    schedule_1 = _document_or_skip("schedule_1_2025")
    schedule_1_model = build_structure_model(schedule_1)
    assert schedule_1_model is not None
    assert not validate_anchor_identity(schedule_1_model)

    schedule_d = _document_or_skip("schedule_d_2025")
    schedule_d_model = build_structure_model(schedule_d)
    assert schedule_d_model is not None
    assert not validate_anchor_identity(schedule_d_model)


@pytest.mark.m20
def test_anchor_identity_validator_reports_mismatch_without_repairing_it():
    model = StructureModel(
        rows=(
            StructureRow(
                page=1,
                text="5a Add lines 1 through 4 5d",
                x0=1.0,
                y0=1.0,
                x1=100.0,
                y1=12.0,
                text_offset=0,
                line_anchor="5a",
                printed_anchor="5d",
            ),
        ),
        line_anchors=(),
        findings=(),
        captioned_fields=0,
        total_fields=0,
    )

    findings = validate_anchor_identity(model)
    assert len(findings) == 1
    assert findings[0].code == "anchor_identity_disagreement"
    assert "minted anchor 5a" in findings[0].detail
    assert "printed anchor 5d" in findings[0].detail


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
def test_legacy_outline_assembles_continuation_text_into_its_source_span():
    text = (
        "- 18: If line 17 is small, multiply line 17 by 26%.\n"
        "Otherwise, multiply line 17 by 28% and subtract the threshold.\n"
        "- 19: Enter the result.\n"
    )
    document = SourceDocumentInput(
        document_id="schedule_a_2025",
        kind="schedule",
        year="2025",
        url="https://www.irs.gov/example",
        text=text,
        text_path=ROOT / "tests" / "fixtures" / "synthetic.txt",
        fields={
            "fields": [],
            "line_anchors": [
                {"anchor": "18", "page": 1, "text_offset": text.index("18")},
                {"anchor": "19", "page": 1, "text_offset": text.index("19")},
            ],
        },
    )

    outline = build_outline_tree(document)
    line_18 = next(node for node in _flatten(outline.children) if node.line_anchor == "18")
    assert "Otherwise, multiply line 17 by 28%" in line_18.label

    span = _span_for_line(document, line_18, build_candidate_spans(document))
    assert span is not None
    assert span.text == "- 18: If line 17 is small, multiply line 17 by 26%. Otherwise, multiply line 17 by 28% and subtract the threshold."


@pytest.mark.m20
@pytest.mark.parametrize(
    ("document_id", "expected_outline_node_count", "expected_line_anchor_count"),
    [
        ("form_1040_2025", 60, 59),
        ("schedule_a_2025", 29, 28),
        ("schedule_d_2025", 31, 24),
        ("schedule_1_2025", 66, 61),
        ("schedule_2_2025", 52, 45),
        ("schedule_3_2025", 38, 35),
        ("schedule_1a_2025", 60, 48),
        ("form_6251_2025", 68, 63),
        ("schedule_b_2025", 12, 8),
    ],
)
def test_row_assembly_preserves_outline_shape(
    document_id: str,
    expected_outline_node_count: int,
    expected_line_anchor_count: int,
):
    document = _document_or_skip(document_id)
    nodes = _flatten(build_outline_tree(document).children)
    assert len(nodes) == expected_outline_node_count
    assert sum(bool(node.line_anchor) for node in nodes) == expected_line_anchor_count


@pytest.mark.m20
@pytest.mark.parametrize(
    ("line_anchor", "continuation"),
    [
        ("18", "Otherwise, multiply line 17 by 28%"),
        ("20", "line 14 of the Schedule D Tax Worksheet"),
        ("27", "line 21 of the Schedule D Tax Worksheet"),
        ("39", "Otherwise, multiply line 12 by 28%"),
    ],
)
def test_form_6251_wrapped_rows_share_assembled_label_and_evidence(
    line_anchor: str,
    continuation: str,
):
    document = _document_or_skip("form_6251_2025")
    nodes = _flatten(build_outline_tree(document).children)
    node = next(item for item in nodes if item.line_anchor == line_anchor)
    span = _span_for_line(document, node, build_candidate_spans(document))
    assert continuation in node.label
    assert span is not None
    assert continuation in span.text
    assert span.text == node.label


@pytest.mark.m20
def test_assembled_worksheet_references_remain_formula_rows():
    document = _document_or_skip("form_6251_2025")
    formula_nodes = _formula_outline_nodes(build_outline_tree(document).children)
    assert len(formula_nodes) == 29
    assert {node.line_anchor for node in formula_nodes} >= {"13", "20", "27"}


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
