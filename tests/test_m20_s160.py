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


def test_html_segmentable_view_preserves_heading_lines_and_utf8_ranges() -> None:
    source = (
        '<div class="book"><h2>Line 1</h2><p>Enter caf&eacute; amount.</p>'
        "<h2>Line 2</h2><p>Next amount.</p></div>"
    )
    index = HtmlSourceIndex(source)

    assert index.segmentable_text.startswith("## Line 1\n")
    assert "Enter caf\u00e9 amount." in index.segmentable_text
    start = index.segmentable_text.encode("utf-8").index(b"## Line 1")
    end = index.segmentable_text.encode("utf-8").index(b"## Line 2")
    raw_range = index.raw_range_for_segment_bytes(start, end)

    assert raw_range is not None
    visible = index.visible_text_for_ranges((raw_range,))
    assert "Line 1" in visible
    assert "caf\u00e9 amount" in visible


def test_lifted_segmenter_maps_html_model_coordinates_to_raw_bytes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from tax_graph.extract import model_instruction_segmenter as segmenter

    source_path = tmp_path / "instructions_form_1040_2025.html"
    source_path.write_text(
        '<div class="book"><h1>First</h1><p>Enter caf&eacute; amount.</p>'
        "<h1>Second</h1><p>Enter the next amount.</p></div>",
        encoding="utf-8",
    )
    source_index = HtmlSourceIndex(source_path.read_text(encoding="utf-8"))
    source_bytes = source_index.segmentable_text.encode("utf-8")
    second_start = source_bytes.index(b"# Second")

    monkeypatch.setattr(
        segmenter,
        "manifest_owner_document_ids",
        lambda *args, **kwargs: frozenset({"form_1040_2025"}),
    )
    monkeypatch.setattr(
        segmenter,
        "manifest_worksheet_document_ids",
        lambda *args, **kwargs: frozenset(),
    )

    class FakeClient:
        def structured_completion(self, **request):
            return {
                "sections": [
                    {
                        "heading": "# First",
                        "level": 1,
                        "start_byte": 0,
                        "end_byte": len(source_bytes),
                        "document_id": "form_1040_2025",
                        "governs": ["1"],
                    },
                    {
                        "heading": "# Second",
                        "level": 1,
                        "start_byte": second_start,
                        "end_byte": len(source_bytes),
                        "document_id": "form_1040_2025",
                        "governs": ["2"],
                    },
                ]
            }

    frame = segmenter.build_frame_from_source(
        source_path,
        source_document_id="instructions_form_1040_2025",
        config={"llm": {"temperature": 0, "micro_model": "fixture-model"}},
        root=ROOT,
        client=FakeClient(),
        max_window_bytes=10000,
        overlap_bytes=100,
    )

    assert frame.coverage["source_coordinate_space"] == "raw_html_utf8_bytes"
    assert len(frame.sections) == 2
    first = frame.sections[0]
    first_visible = HtmlSourceIndex(source_path.read_text(encoding="utf-8")).visible_text_for_ranges(
        ({"start": first.start_byte, "end": first.end_byte},)
    )
    assert "First" in first_visible
    assert "caf\u00e9 amount" in first_visible
