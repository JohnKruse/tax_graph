"""Real-corpus tests for the M20-S75 instruction parser pilot."""

from __future__ import annotations

import json
from pathlib import Path

from instruction_parser import (
    INSTRUCTION_FORMS,
    build_instruction_sections_file,
    main,
    measure_corpus,
    parse_html_sections,
    parse_ocr_sections,
)


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / ".cache" / "raw" / "2025"


def test_6251_repairs_bold_headings_and_phantom_anchors() -> None:
    """The measured 6251 defects are fixed against the cached sources."""

    document_id = "instructions_form_6251_2025"
    html = parse_html_sections(
        (RAW_ROOT / f"{document_id}.html").read_text(encoding="utf-8"),
        source_document_id=document_id,
    )
    known_lines = {token for section in html for token in section.line_tokens}
    fixed = parse_ocr_sections(
        (RAW_ROOT / f"{document_id}.txt").read_text(encoding="utf-8"),
        source_document_id=document_id,
        known_lines=known_lines,
        known_sections=html,
    )
    current = build_instruction_sections_file(
        RAW_ROOT / f"{document_id}.txt",
        source_document_id=document_id,
    )

    current_phantoms = {
        section.line
        for section in current.sections
        if section.line not in known_lines
    }
    fixed_phantoms = {
        token
        for section in fixed
        for token in section.line_tokens
        if token not in known_lines
    }
    assert current_phantoms == {"3o", "4a", "5e", "8a", "11a"}
    assert fixed_phantoms == set()
    assert len(fixed) == 33
    assert len(html) == 33
    assert {
        (section.owner_document_id, token)
        for section in fixed
        for token in section.line_tokens
    } == {
        (section.owner_document_id, token)
        for section in html
        for token in section.line_tokens
    }
    assert any(
        section.line_tokens == ("2d",)
        for section in fixed
    )
    assert any(
        section.line_tokens == ("2f",)
        for section in fixed
    )
    assert any(
        section.line_tokens == ("2g",)
        for section in fixed
    )
    assert any(
        section.line_tokens == ("2l",)
        for section in fixed
    )


def test_all_seven_instruction_documents_are_measured_and_empty_is_named() -> None:
    """The report keeps an explicit finding for a document that yields nothing."""

    report = measure_corpus(RAW_ROOT)
    assert set(report["documents"]) == set(INSTRUCTION_FORMS)
    for data in report["documents"].values():
        assert data["counts"]["ocr_with_fixes"] == data["counts"]["html"]
        assert data["phantom_anchors"]["ocr_with_fixes"] == []

    schedule_b = report["documents"]["instructions_schedule_b_2025"]
    assert schedule_b["counts"] == {
        "ocr_today": 0,
        "ocr_with_fixes": 0,
        "html": 0,
    }
    assert any(
        finding["kind"] == "document_without_line_sections"
        for finding in schedule_b["source_findings"]
    )


def test_html_and_ocr_keep_named_sources_and_report_disagreement() -> None:
    """A source disagreement is visible rather than resolved by fallback."""

    report = measure_corpus(RAW_ROOT)
    data = report["documents"]["instructions_form_6251_2025"]
    disagreement = [
        finding
        for finding in data["source_findings"]
        if finding.get("kind") == "source_section_disagreement"
        and finding.get("line") == "2d"
    ]
    assert disagreement
    assert disagreement[0]["ocr_heading"] == "Line 2dDepletion"
    assert disagreement[0]["html_heading"] == "Line 2d-Depletion"
    ocr = next(
        section
        for section in data["sections"]["ocr_with_fixes"]
        if section["line_tokens"] == ["2d"]
    )
    html = next(
        section
        for section in data["sections"]["html"]
        if section["line_tokens"] == ["2d"]
    )
    assert ocr["source"] == "ocr"
    assert html["source"] == "html"
    assert ocr["text"] != html["text"]


def test_cli_writes_json_measurement(tmp_path: Path) -> None:
    """The pilot has a reproducible, non-graph measurement entry point."""

    output = tmp_path / "instruction_parser.json"
    assert main(
        [
            "--raw-root",
            str(RAW_ROOT),
            "--output",
            str(output),
        ]
    ) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["documents"]["instructions_form_6251_2025"]["counts"]["ocr_with_fixes"] == 33
