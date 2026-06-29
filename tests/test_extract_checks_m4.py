from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.extract.checks import _field_anchor, _true_line_anchors, run_deterministic_checks
from tax_graph.extract.models import DraftObject, ExtractionBatch, RelatedSourceInput, SourceDocumentInput


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.m4
def test_field_anchor_reads_form_line_names_without_index_noise():
    assert _field_anchor("topmostSubform[0].Page1[0].f3a_colA[0]") == "3a"
    assert _field_anchor("topmostSubform[0].Page1[0].line16_total[0]") == "16"
    assert _field_anchor("topmostSubform[0].Page1[0].f1_03[0]") is None
    assert _field_anchor("topmostSubform[0].Page1[0].Table_Line1_Part1[0].Row1[0].f1_03[0]") is None


@pytest.mark.m4
def test_true_line_anchors_ignore_renderer_artifacts(tmp_path):
    text_path = tmp_path / "form_8949_2025.txt"
    text_path.write_text("- 8949:\n- 2025:\n- 1: Enter proceeds\n- 2: Totals\n", encoding="utf-8")
    document = SourceDocumentInput(
        document_id="form_8949_2025",
        kind="tax_form",
        year="2025",
        url="https://www.irs.gov/pub/irs-pdf/f8949.pdf",
        text=text_path.read_text(encoding="utf-8"),
        text_path=text_path,
        fields={"fields": [{"field_name": "topmostSubform[0].line1_total[0]", "line_anchor": "1"}]},
        related_sources=[
            RelatedSourceInput(
                document_id="instructions_form_8949_2025",
                kind="instructions",
                text="Instructions for line 2 explain totals.",
                text_path=text_path,
            )
        ],
    )

    assert _true_line_anchors(document) == ["1", "2"]


@pytest.mark.m4
def test_line_completeness_allows_multiple_column_nodes_for_one_line(tmp_path):
    text_path = tmp_path / "form_8949_2025.txt"
    text_path.write_text("- 2: Totals. Add the amounts in columns (d), (e), (g), and (h)\n", encoding="utf-8")
    document = SourceDocumentInput(
        document_id="form_8949_2025",
        kind="tax_form",
        year="2025",
        url="https://www.irs.gov/pub/irs-pdf/f8949.pdf",
        text=text_path.read_text(encoding="utf-8"),
        text_path=text_path,
        fields={"fields": []},
        related_sources=[
            RelatedSourceInput(
                document_id="instructions_form_8949_2025",
                kind="instructions",
                text="Instructions for line 2 explain totals.",
                text_path=text_path,
            )
        ],
    )
    batch = ExtractionBatch(
        document_id="form_8949_2025",
        year="2025",
        objects=[
            DraftObject(
                "nodes",
                {
                    "node_id": "form_8949_line_2_col_d",
                    "document_id": "form_8949_2025",
                    "label": "Form 8949 line 2 column d",
                    "node_type": "form_line",
                    "value_type": "currency",
                },
                "",
                "mock",
                1,
            ),
            DraftObject(
                "nodes",
                {
                    "node_id": "form_8949_line_2_col_e",
                    "document_id": "form_8949_2025",
                    "label": "Form 8949 line 2 column e",
                    "node_type": "form_line",
                    "value_type": "currency",
                },
                "",
                "mock",
                1,
            ),
        ],
    )

    report = run_deterministic_checks(document, batch, root=ROOT)

    assert not report.issues
