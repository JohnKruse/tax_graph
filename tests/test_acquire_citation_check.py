from __future__ import annotations

import json

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


@pytest.mark.m3
def test_citation_integrity_ignores_header_decoration_when_quote_spans_injected_lines(tmp_path):
    text_dir = tmp_path / "2025"
    text_dir.mkdir()
    (text_dir / "instructions_form_8949_2025.txt").write_text(
        "\n".join(
            [
                "# Page 1",
                "Subtract column (e)",
                "Header: from column (d) and combine the result",
                "Header: with column (g)",
                "to figure your gain or loss.",
            ]
        ),
        encoding="utf-8",
    )
    citations = [
        {
            "citation_id": "cite_header_shift",
            "document_id": "form_8949_2025",
            "source_document_id": "instructions_form_8949_2025",
            "quoted_text": "Subtract column (e) from column (d) and combine the result with column (g)",
        }
    ]

    report = check_citation_integrity(citations, text_dir=text_dir)

    assert report.ok


@pytest.mark.m3
def test_citation_integrity_reports_explicit_source_drift(tmp_path):
    text_dir = tmp_path / "2025"
    text_dir.mkdir()
    (text_dir / "form_8949_2025.txt").write_text("Pinned IRS text", encoding="utf-8")
    (text_dir / "form_8949_2025.json").write_text(
        json.dumps({"content_hash": "b" * 64}),
        encoding="utf-8",
    )
    citations = [
        {
            "citation_id": "cite_pinned",
            "document_id": "form_8949_2025",
            "quoted_text": "Pinned IRS text",
        }
    ]

    report = check_citation_integrity(
        citations,
        text_dir=text_dir,
        source_pins={"form_8949_2025": "a" * 64},
    )

    assert not report.ok
    assert report.mismatches[0].citation_id == "source_drift_form_8949_2025"
    assert report.mismatches[0].reason.startswith("source drift:")


@pytest.mark.m3
def test_citation_integrity_prefers_explicit_source_document_id_over_source_map(tmp_path):
    text_dir = tmp_path / "2025"
    text_dir.mkdir()
    (text_dir / "form_1040_2025.txt").write_text("Capital gain or (loss). Attach Schedule D if required.", encoding="utf-8")
    (text_dir / "instructions_form_1040_2025.txt").write_text("Different instruction text", encoding="utf-8")
    citations = [
        {
            "citation_id": "cite_explicit_source",
            "document_id": "form_1040_2025",
            "source_document_id": "form_1040_2025",
            "quoted_text": "Capital gain or (loss). Attach Schedule D if required.",
        }
    ]

    report = check_citation_integrity(
        citations,
        text_dir=text_dir,
        source_map={"form_1040_2025": "instructions_form_1040_2025"},
    )

    assert report.ok


@pytest.mark.m3
def test_citation_integrity_falls_back_to_pdf_text_when_rendered_text_misses(tmp_path, monkeypatch):
    text_dir = tmp_path / "2025"
    text_dir.mkdir()
    (text_dir / "schedule_d_2025.txt").write_text("rendered text misses the quote", encoding="utf-8")
    (text_dir / "schedule_d_2025.pdf").write_bytes(b"%PDF-1.4")
    citations = [
        {
            "citation_id": "cite_pdf_fallback",
            "document_id": "schedule_d_2025",
            "quoted_text": "Enter the amount from line 16 on Form 1040 or 1040-SR, line 7.",
        }
    ]

    monkeypatch.setattr(
        "tax_graph.acquire.citation_check._load_pdf_text",
        lambda path: "Enter the amount from line 16 on Form 1040 or 1040-SR, line 7.",
    )

    report = check_citation_integrity(citations, text_dir=text_dir)

    assert report.ok
