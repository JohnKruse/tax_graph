"""Phase M15 Step 2 geometry and static bundle tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from workbench.geometry import GeometryIndex
from workbench.render import render_pdf_pages


@pytest.mark.m15
def test_geometry_index_keeps_field_provenance_and_gap_layers_distinct() -> None:
    index = GeometryIndex(
        {
            "tax_year": 2025,
            "entries": [
                {"document_id": "form_a_2025", "field_name": "f1", "page": 1, "rect": [10, 10, 20, 20], "node_id": "node_a"},
                {"document_id": "form_a_2025", "field_name": "f2", "page": 1, "rect": [30, 30, 40, 40], "identity_slot": "unmodeled"},
            ],
        }
    )
    hits = index.at(page=1, x=15, y=15)
    assert [hit.layer for hit in hits] == ["provenance", "field"]
    assert hits[0].node_id == "node_a"
    assert len(index.gaps_for_page(1)) == 1
    assert index.at(page=1, x=25, y=25) == ()


@pytest.mark.m15
def test_pdf_renderer_is_build_time_only(tmp_path: Path) -> None:
    fitz = pytest.importorskip("fitz")
    pdf_path = tmp_path / "form_a_2025.pdf"
    document = fitz.open()
    document.new_page(width=72, height=144)
    document.save(pdf_path)
    document.close()
    pages = render_pdf_pages(pdf_path, tmp_path / "pages", dpi=72)
    assert len(pages) == 1
    assert pages[0].path.exists()
    assert pages[0].width == 72
    assert pages[0].height == 144
