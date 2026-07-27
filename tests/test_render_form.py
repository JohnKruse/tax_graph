from __future__ import annotations

import json

import pytest

from tax_graph.acquire.render_form import render_form_pdf


@pytest.mark.m3
def test_render_form_extracts_line_rows_and_fields(tmp_path):
    fitz = pytest.importorskip("fitz")
    pdf_path = tmp_path / "f1116_fixture.pdf"
    document = fitz.open()
    page = document.new_page(width=612, height=792)
    page.insert_text((72, 72), "3a Deduction allocation column A")
    page.insert_text((72, 92), "3b Deduction allocation column B")
    page.insert_text((72, 112), "3c .... Deduction allocation column C")
    page.insert_text((72, 132), "4a Other deduction entry")
    page.insert_text((72, 152), "4b Another deduction entry")
    page.insert_text((72, 172), "(h) Gain or loss. Subtract column (e) from column (d)")
    page.insert_text((72, 192), "8949 2025")

    widget = fitz.Widget()
    widget.field_name = "topmostSubform[0].Page1[0].f3a_colA[0]"
    widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
    widget.rect = fitz.Rect(300, 66, 360, 84)
    page.add_widget(widget)
    document.save(pdf_path)
    document.close()

    result = render_form_pdf(pdf_path, document_id="form_1116_2025", output_dir=tmp_path)

    markdown = (tmp_path / "form_1116_2025.txt").read_text(encoding="utf-8")
    assert "- 3a: Deduction allocation column A" in markdown
    assert "- 3b: Deduction allocation column B" in markdown
    assert "- 3c: Deduction allocation column C" in markdown
    assert "- 4a: Other deduction entry" in markdown
    assert "- 4b: Another deduction entry" in markdown
    assert "Header: (h) Gain or loss. Subtract column (e) from column (d)" in markdown
    assert "- 8949:" not in markdown
    assert "- 2025:" not in markdown

    fields = json.loads((tmp_path / "form_1116_2025.fields.json").read_text(encoding="utf-8"))
    assert fields["pages"] == [{"page": 1, "width": 612.0, "height": 792.0, "rotation": 0}]
    assert fields["fields"][0]["field_name"] == "topmostSubform[0].Page1[0].f3a_colA[0]"
    assert fields["fields"][0]["x_cluster"] == 300
    assert fields["fields"][0]["line_anchor"] == "3a"
    assert result.document_id == "form_1116_2025"
