from __future__ import annotations

import pytest

from tax_graph.acquire.citation_check import check_citation_integrity


@pytest.mark.m3
def test_citation_integrity_accepts_matching_quote_with_normalized_whitespace(tmp_path):
    text_dir = tmp_path / "2025"
    text_dir.mkdir()
    (text_dir / "form_8949_2025.txt").write_text(
        "Subtract column (e) from column (d)\n"
        "and combine the result with column (g) to figure your gain or loss.",
        encoding="utf-8",
    )
    citations = [
        {
            "citation_id": "cite_8949_col_h_gain",
            "document_id": "form_8949_2025",
            "quoted_text": "Subtract column (e) from column (d) and combine the result with column (g)",
        }
    ]

    report = check_citation_integrity(citations, text_dir=text_dir)

    assert report.ok
    assert report.checked == 1
    assert report.mismatches == []


@pytest.mark.m3
def test_citation_integrity_flags_doctored_quote(tmp_path):
    text_dir = tmp_path / "2025"
    text_dir.mkdir()
    (text_dir / "form_8949_2025.txt").write_text("Real IRS text", encoding="utf-8")
    citations = [
        {
            "citation_id": "cite_bad",
            "document_id": "form_8949_2025",
            "quoted_text": "Doctored text",
        }
    ]

    report = check_citation_integrity(citations, text_dir=text_dir)

    assert not report.ok
    assert report.mismatches[0].citation_id == "cite_bad"
    assert report.mismatches[0].reason == "quote not found"


@pytest.mark.m3
def test_citation_integrity_uses_source_map(tmp_path):
    text_dir = tmp_path / "2025"
    text_dir.mkdir()
    (text_dir / "instructions_form_8949_2025.txt").write_text("Mapped instruction quote", encoding="utf-8")
    citations = [
        {
            "citation_id": "cite_mapped",
            "document_id": "form_8949_2025",
            "quoted_text": "Mapped instruction quote",
        }
    ]

    report = check_citation_integrity(
        citations,
        text_dir=text_dir,
        source_map={"form_8949_2025": "instructions_form_8949_2025"},
    )

    assert report.ok
