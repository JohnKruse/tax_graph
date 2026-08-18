from __future__ import annotations

import json

import pytest

from tax_graph.acquire.citation_check import check_citation_integrity


@pytest.mark.m3
def test_citation_integrity_accepts_matching_quote_with_normalized_whitespace(tmp_path):
    text_dir = tmp_path / "2025"
    text_dir.mkdir()
    source = (
        "Subtract column (e) from column (d)\n"
        "and combine the result with column (g) to figure your gain or loss."
    )
    (text_dir / "form_8949_2025.txt").write_text(source, encoding="utf-8")
    citations = [
        {
            "citation_id": "cite_8949_col_h_gain",
            "document_id": "form_8949_2025",
            "ranges": [{"start": 0, "end": len(source)}],
            "quoted_text": "Subtract column (e) from column (d) and combine the result with column (g)",
        }
    ]

    report = check_citation_integrity(citations, text_dir=text_dir)

    assert report.ok
    assert report.checked == 1
    assert report.mismatches == []


def test_citation_integrity_skips_computed_table_without_quote(tmp_path):
    (tmp_path / "instructions_form_1040_2025.txt").write_text("rate table", encoding="utf-8")
    report = check_citation_integrity(
        [
            {
                "citation_id": "cite_computed_table",
                "document_id": "instructions_form_1040_2025",
                "kind": "computed_table",
                "ranges": [{"start": 10, "end": 20}],
                "derivation": "Apply the rate table rows to the filing-status bracket.",
            }
        ],
        text_dir=tmp_path,
    )

    assert report.checked == 1
    assert report.ok
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
            "ranges": [{"start": 0, "end": len("Real IRS text")}],
            "quoted_text": "Doctored text",
        }
    ]

    report = check_citation_integrity(citations, text_dir=text_dir)

    assert not report.ok
    assert report.mismatches[0].citation_id == "cite_bad"
    assert report.mismatches[0].reason == "quote not found in cited range"


@pytest.mark.m3
def test_citation_integrity_uses_source_map(tmp_path):
    text_dir = tmp_path / "2025"
    text_dir.mkdir()
    (text_dir / "instructions_form_8949_2025.txt").write_text("Mapped instruction quote", encoding="utf-8")
    citations = [
        {
            "citation_id": "cite_mapped",
            "document_id": "form_8949_2025",
            "ranges": [{"start": 0, "end": len("Mapped instruction quote")}],
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
def test_citation_integrity_concatenates_explicit_ranges_across_source_lines(tmp_path):
    text_dir = tmp_path / "2025"
    text_dir.mkdir()
    source = "\n".join(
        [
            "# Page 1",
            "Subtract column (e) - page furniture",
            "from column (d) and combine the result",
            "with column (g).",
        ]
    )
    (text_dir / "instructions_form_8949_2025.txt").write_text(source, encoding="utf-8")
    first = source.index("Subtract")
    second = source.index("from column")
    third = source.index("with column")
    citations = [
        {
            "citation_id": "cite_header_shift",
            "document_id": "form_8949_2025",
            "source_document_id": "instructions_form_8949_2025",
            "ranges": [
                {"start": first, "end": first + len("Subtract column (e)")},
                {"start": second, "end": second + len("from column (d) and combine the result")},
                {"start": third, "end": third + len("with column (g).")},
            ],
            "quoted_text": "Subtract column (e) from column (d) and combine the result with column (g).",
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
            "ranges": [{"start": 0, "end": len("Pinned IRS text")}],
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
            "ranges": [{
                "start": 0,
                "end": len("Capital gain or (loss). Attach Schedule D if required."),
            }],
            "quoted_text": "Capital gain or (loss). Attach Schedule D if required.",
        }
    ]

    report = check_citation_integrity(
        citations,
        text_dir=text_dir,
        source_map={"form_1040_2025": "instructions_form_1040_2025"},
    )

    assert report.ok


def test_citation_integrity_does_not_fallback_to_stored_html(tmp_path):
    text_dir = tmp_path / "2025"
    text_dir.mkdir()
    (text_dir / "instructions_form_1040_2025.txt").write_text(
        "PDF extraction does not carry this HTML-only paragraph.", encoding="utf-8"
    )
    (text_dir / "instructions_form_1040_2025.html").write_text(
        '<h4 id="line-1">Line 1</h4><p>Enter the HTML-acquired instruction text.</p>',
        encoding="ascii",
    )
    report = check_citation_integrity(
        [
            {
                "citation_id": "cite_html_source",
                "document_id": "instructions_form_1040_2025",
                "source_document_id": "instructions_form_1040_2025",
                "ranges": [{"start": 0, "end": len("PDF extraction does not carry this HTML-only paragraph.")}],
                "quoted_text": "Enter the HTML-acquired instruction text.",
            }
        ],
        text_dir=text_dir,
    )

    assert not report.ok
    assert report.mismatches[0].reason == "quote not found in cited range"


@pytest.mark.m3
def test_citation_integrity_does_not_fallback_to_pdf_text(tmp_path):
    text_dir = tmp_path / "2025"
    text_dir.mkdir()
    (text_dir / "schedule_d_2025.txt").write_text("rendered text misses the quote", encoding="utf-8")
    (text_dir / "schedule_d_2025.pdf").write_bytes(b"%PDF-1.4")
    citations = [
        {
            "citation_id": "cite_pdf_fallback",
            "document_id": "schedule_d_2025",
            "ranges": [{"start": 0, "end": len("rendered text misses the quote")}],
            "quoted_text": "Enter the amount from line 16 on Form 1040 or 1040-SR, line 7.",
        }
    ]

    report = check_citation_integrity(citations, text_dir=text_dir)

    assert not report.ok
    assert report.mismatches[0].reason == "quote not found in cited range"


def test_citation_integrity_requires_explicit_ranges_for_table_elision(tmp_path):
    text_dir = tmp_path / "2025"
    text_dir.mkdir()
    source = "3. Combine lines 1 and 2. | 3. _____ | | 4. Enter the smaller of line 2 or line 3"
    (text_dir / "schedule_d_2025.txt").write_text(source, encoding="utf-8")

    report = check_citation_integrity(
        [
            {
                "citation_id": "cite_elided_table_furniture",
                "document_id": "schedule_d_2025",
                "ranges": [
                    {"start": 0, "end": source.index("|")},
                    {"start": source.index("4."), "end": len(source)},
                ],
                "quoted_text": "3. Combine lines 1 and 2. 4. Enter the smaller of line 2 or line 3",
            }
        ],
        text_dir=text_dir,
    )

    assert report.ok


def test_citation_integrity_rejects_quote_found_only_in_a_neighboring_row(tmp_path):
    text_dir = tmp_path / "2025"
    text_dir.mkdir()
    source = "Target row has the unique alpha phrase.\nNeighbor row has different beta text."
    (text_dir / "schedule_d_2025.txt").write_text(source, encoding="utf-8")
    start = source.index("Neighbor")

    report = check_citation_integrity(
        [
            {
                "citation_id": "cite_perturbed_range",
                "document_id": "schedule_d_2025",
                "ranges": [{"start": start, "end": len(source)}],
                "quoted_text": "Target row has the unique alpha phrase.",
            }
        ],
        text_dir=text_dir,
    )

    assert not report.ok
    assert report.mismatches[0].reason == "quote not found in cited range"


@pytest.mark.m20
def test_citation_integrity_rejects_legacy_row_renderer_formatting(tmp_path):
    text_dir = tmp_path / "2025"
    text_dir.mkdir()
    (text_dir / "form_2441_2025.txt").write_text(
        "3 Add the amounts in column (d) of line 2. Don't enter more than $3,000 if you had one qualifying person\n"
        "Tax-exempt interest 2a b Taxable interest\n"
        "25 Excluded benefits. If you checked \"No\" on line 22, enter the smaller of line 20 or line 21.\n",
        encoding="utf-8",
    )
    report = check_citation_integrity(
        [
            {
                "citation_id": "legacy_wrapper",
                "document_id": "form_2441_2025",
                "ranges": [{"start": 0, "end": 105}],
                "quoted_text": "- 3: Add the amounts in column (d) of line 2. Dont enter more than $3,000 if you had one qualifying person",
            },
            {
                "citation_id": "legacy_dots",
                "document_id": "form_2441_2025",
                "ranges": [{"start": 105, "end": 147}],
                "quoted_text": "Tax-exempt interest 2a b Taxable interest",
            },
            {
                "citation_id": "legacy_quotes",
                "document_id": "form_2441_2025",
                "ranges": [{"start": 147, "end": 242}],
                "quoted_text": "- 25: Excluded benefits. If you checked No on line 22, enter the smaller of line 20 or line 21.",
            },
        ],
        text_dir=text_dir,
    )

    assert not report.ok
    assert {m.citation_id for m in report.mismatches} == {"legacy_wrapper", "legacy_quotes"}
