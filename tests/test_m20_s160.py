"""M20-S160 guards for HTML instruction sources and range coordinates."""

from __future__ import annotations

from pathlib import Path

from tax_graph.acquire.citation_check import check_citation_integrity
from tax_graph.acquire.html_source import HtmlSourceIndex
from tax_graph.extract.inputs import load_document_input


ROOT = Path(__file__).resolve().parents[1]


def test_instruction_related_source_uses_html_form_face_stays_txt() -> None:
    document = load_document_input("form_1040_2025", year="2025", root=ROOT)

    assert document.text_path.suffix == ".txt"
    assert document.related_sources
    assert document.related_sources[0].text_path.suffix == ".html"
    assert document.related_sources[0].text.startswith("<!DOCTYPE html>")


def test_html_quote_ranges_are_utf8_bytes_and_integrity_resolves(tmp_path: Path) -> None:
    text_dir = tmp_path / "2025"
    text_dir.mkdir()
    source = '<div class="book"><h2>Line 1</h2><p>Enter the cafe amount.</p></div>'
    (text_dir / "instructions_test_2025.html").write_text(source, encoding="ascii")
    index = HtmlSourceIndex(source)
    ranges = index.ranges_for_quote("Enter the cafe amount.")

    assert ranges is not None
    assert ranges[0]["end"] > ranges[0]["start"]
    report = check_citation_integrity(
        [
            {
                "citation_id": "cite_html_bytes",
                "document_id": "form_test_2025",
                "source_document_id": "instructions_test_2025",
                "ranges": list(ranges),
                "quoted_text": "Enter the cafe amount.",
            }
        ],
        text_dir=text_dir,
    )

    assert report.checked == 1
    assert report.ok


def test_m20_s160_rebind_floor_is_exact() -> None:
    from tools.rebind_instruction_html_ranges_m20_s160 import rebind_instruction_citations

    report = rebind_instruction_citations(root=ROOT, year="2025")

    assert report["affected_ranges_rederived"] == 338
    assert report["unaffected_ranges_unchanged"] == 255


def test_lifted_segmenter_replays_accepted_fixture() -> None:
    from tax_graph.extract.model_instruction_segmenter import build_frame_from_fixture

    source = ROOT / ".cache" / "raw" / "2025" / "instructions_form_1040_2025.txt"
    fixture = ROOT / "pilot" / "fixtures" / "instruction_segmenter_live_1040.json"
    frame = build_frame_from_fixture(
        source,
        source_document_id="instructions_form_1040_2025",
        fixture_path=fixture,
        root=ROOT,
    )

    assert frame.source_document_id == "instructions_form_1040_2025"
    assert frame.sections
