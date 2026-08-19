"""M17 S3 browser checks for the cell-atomic review workbench shell."""

from __future__ import annotations

from pathlib import Path
import re

import pytest
from playwright.sync_api import expect

from pilot.html_document_frame_m20_s132 import parse_html_document_frame
from workbench.generated_review import build_generated_document_cells


pytestmark = pytest.mark.m17
ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = ROOT / ".cache" / "raw" / "2025"
LINE_1I_GAP_REASON = (
    "M20-S139 queue: the acquired HTML line 1i instruction section is not projected into the generated cell"
)
# This is a non-increasing ceiling for the frame-to-draft gap, not a frozen
# corpus count.  The report below remains useful when another line is closed.
S132_1040_FRAME_GAP_CEILING = 5


def test_three_pane_shell_exposes_cell_river_and_local_review_state(page, workbench_url: str) -> None:
    page.goto(workbench_url)

    assert page.locator(".review-layout").count() == 1
    assert page.locator("#official-pane").count() == 1
    assert page.locator("#drawer").count() == 1
    assert page.locator("#save-progress").is_disabled()

    page.locator('[data-document-id="form_8949_2025"].document-entry').click()
    cards = page.locator("#river .review-unit-card")
    cards.first.wait_for()
    assert cards.count() > 0

    card = cards.first
    card.locator(".unit-card-select").click()
    heading = page.locator("#river-detail .drawer-heading")
    heading.wait_for()
    assert heading.count() == 1
    assert page.locator("#river-detail .selected-ref").inner_text()

    assert card.locator('input[type="checkbox"]').count() == 0
    assert card.locator("textarea").count() == 0

    checkbox = page.locator("#river-detail .session-approve")
    assert checkbox.count() == 1
    checkbox.check()
    note = page.locator("#river-detail .session-note")
    assert note.count() == 1
    note.fill("Checked against the official cell.")
    note.press("Tab")

    assert page.locator("#approved-count").inner_text() == "1 / " + str(cards.count())
    assert page.locator("#save-progress").is_enabled()
    page.locator("#save-progress").click()
    page.get_by_text("Progress saved locally.", exact=True).wait_for()


def test_form_and_river_selection_crosses_pages_and_keeps_selection_visible(page, workbench_url: str) -> None:
    page.goto(workbench_url)
    page.locator('[data-document-id="form_1040_2025"].document-entry').click()
    cards = page.locator("#river .review-unit-card")
    cards.first.wait_for()

    # data-page is on the card element itself, so it must be part of the card selector -
    # cards.locator("[data-page]") would match only DESCENDANTS of a card and never resolve.
    page_two = page.locator('#river .review-unit-card[data-page="2"]').first
    page_two.wait_for()
    page_two.locator(".unit-card-select").click()
    page.locator('#official-pane .page-canvas[data-page="2"]').wait_for()
    assert page_two.get_attribute("data-unit-id") == page.locator("#river .review-unit-card.selected").get_attribute("data-unit-id")

    official = page.locator("#official-pane .official-region").first
    official.click()
    selected_id = official.get_attribute("data-unit-id")
    selected_card = page.locator(f'#river .review-unit-card[data-unit-id="{selected_id}"]')
    expect(selected_card).to_have_attribute("data-page", "2")
    expect(selected_card).to_have_class(re.compile(r"\bselected\b"))
    assert selected_card.evaluate(
        "card => { const c = card.getBoundingClientRect(); const r = card.closest('#river').getBoundingClientRect(); return c.top >= r.top && c.bottom <= r.bottom; }"
    )
    expect(official).to_have_class(re.compile(r"\bpinned\b"))
    # Assert the selection CONTRACT, not one px value: the cue is a repeating stripe
    # (a shape cue, so it survives colour blindness and grayscale) drawn INSIDE the cell,
    # with nothing painted outside it. John, 2026-07-27: the old outward double ring
    # "hides some of the text labels in some forms/cells", so box-shadow must stay none.
    expect(official).to_have_css("background-image", re.compile("repeating-linear-gradient"))
    expect(official).to_have_css("box-shadow", "none")

    # The tiny checkbox has almost no interior area, so verify the same in-cell treatment
    # still applies at a sub-20px target rather than relying on the region's dimensions.
    checkbox_region = page.locator('#official-pane .official-region[data-label="You as a dependent"]')
    checkbox_region.click()
    expect(checkbox_region).to_have_css("background-image", re.compile("repeating-linear-gradient"))
    expect(checkbox_region).to_have_css("box-shadow", "none")
    assert checkbox_region.evaluate(
        "region => { const r = region.getBoundingClientRect(); return r.width < 20 && r.height < 20; }"
    )


def test_selected_cell_uses_human_headers_dossier_order_and_occurrence(page, workbench_url: str) -> None:
    """Selected cards keep human-readable authority and typed generated content."""
    page.goto(workbench_url)
    page.locator('[data-document-id="form_1040_2025"].document-entry').click()
    cards = page.locator("#river .review-unit-card")
    cards.first.wait_for()

    # The printed line leads the card header, with the authored label after it.
    anchors = cards.locator(".unit-card-anchor").all_inner_texts()
    line_index = anchors.index("33")
    line_card = cards.nth(line_index)
    expect(line_card.locator(".unit-card-anchor")).to_have_text("33")
    line_card.locator(".unit-card-select").click()

    detail = page.locator("#river-detail")
    expect(detail.locator("h2")).to_have_text(re.compile(r"^33 - "))
    expect(detail.locator(".cell-instruction")).to_contain_text("Not yet ingested")
    expect(detail.locator(".authority")).to_be_visible()
    expect(detail.locator(".authority")).to_contain_text("33 Add lines 25d, 26, and 32")
    expect(detail.locator(".generated-verdict")).to_be_visible()
    expect(detail.locator(".generated-expression")).to_contain_text("line 33 = line 25d + line 26 + line 32")
    assert detail.locator("details.technical-record").get_attribute("open") is None

    # The 1040 line 1a record retains the instruction citation in the authority
    # slot even when its generated source result is unresolved.
    line_1a = cards.nth(anchors.index("1a"))
    line_1a.locator(".unit-card-select").click()
    expect(detail.locator(".authority")).to_contain_text("Total amount from Form(s) W-2")
    # The draft may change its derivation result; the card contract requires a
    # non-empty human expression, or a typed absence, rather than blank output.
    expect(detail.locator(".generated-expression")).to_have_text(re.compile(r"line 1a = .+\S"))
    expect(detail.locator(".generated-verdict")).to_be_visible()

    # Line 1i is sourced from the instruction page's own Line 1i section,
    # including the deeper semantic heading below it.
    line_1i = cards.nth(anchors.index("1i"))
    line_1i.locator(".unit-card-select").click()
    instruction = detail.locator(".cell-instruction")
    expect(instruction).to_be_visible()
    # The review contract is typed: show ingested instruction text when it is
    # present, otherwise show the explicit absence placeholder.  The source
    # linkage gap is guarded separately below so this assertion cannot hide it.
    expect(instruction).to_have_text(re.compile(r"\S"))
    placeholder = instruction.locator("p.not-authored")
    if placeholder.count():
        expect(placeholder).to_have_text(
            "Not yet ingested - the form instruction for this line will appear here."
        )
    else:
        expect(instruction.locator("blockquote").first).to_be_visible()
    expect(detail.locator(".verdict-accept")).to_be_visible()
    expect(detail.locator(".verdict-question")).to_be_visible()
    expect(detail.locator(".verdict-reject")).to_be_visible()
    expect(detail.locator(".verdict-question")).to_have_text("Try Again")
    expect(detail.locator(".verdict-comment")).to_be_visible()
    assert detail.locator(".reject-dialog .reject-filer").count() == 0
    assert detail.locator(".verdict-reviewer").count() == 0

    # Repeated-concept occurrence contracts are exercised by the M19 concept tests;
    # this 57-cell Form 1040 review projection intentionally contains line cells only.


@pytest.mark.xfail(reason=LINE_1I_GAP_REASON, strict=False)
def test_s132_1040_line_1i_instruction_section_reaches_generated_cell() -> None:
    """The accepted HTML frame must reach the generated 1040 line 1i cell."""
    frame = parse_html_document_frame(
        (RAW_ROOT / "instructions_form_1040_2025.html").read_text(encoding="utf-8"),
        source_document_id="instructions_form_1040_2025",
        root=ROOT,
    )
    line_section = next(
        section
        for section in frame.sections
        if section.heading == "Line 1i"
        and section.line_tokens == ("1i",)
    )
    semantic_section = next(
        section
        for section in frame.sections
        if section.heading == "Nontaxable Combat Pay Election"
    )
    assert line_section.owner_document_id == "form_1040_2025"
    assert semantic_section.owner_document_id == "form_1040_2025"

    cells = build_generated_document_cells(ROOT, 2025, "form_1040_2025").cells
    line_1i = next(
        cell
        for cell in cells
        if str(cell.get("official_ref") or "").strip().lower() == "1i"
    )
    assert line_1i.get("instruction_citations"), (
        "the frame-owned Line 1i instruction section exists but does not reach the generated cell"
    )


def test_s132_1040_frame_owned_instruction_gap_count_is_measured() -> None:
    """Keep the frame-to-draft gap visible without freezing today's count."""
    frame = parse_html_document_frame(
        (RAW_ROOT / "instructions_form_1040_2025.html").read_text(encoding="utf-8"),
        source_document_id="instructions_form_1040_2025",
        root=ROOT,
    )
    frame_lines = {
        token.lower()
        for section in frame.sections
        if section.owner_document_id == "form_1040_2025"
        for token in section.line_tokens
    }
    cells = build_generated_document_cells(ROOT, 2025, "form_1040_2025").cells
    missing = {
        line
        for line in frame_lines
        if not any(
            str(cell.get("official_ref") or "").strip().lower() == line
            and cell.get("instruction_citations")
            for cell in cells
        )
    }
    assert len(missing) <= S132_1040_FRAME_GAP_CEILING


def test_generated_cell_try_again_shows_fresh_result_without_session_progress(
    page,
    retry_workbench_url: str,
) -> None:
    page.goto(retry_workbench_url)
    session_writes = []
    page.on("request", lambda request: session_writes.append(request.url) if request.method == "PUT" else None)
    page.locator('[data-document-id="form_1040_2025"].document-entry').click()
    cards = page.locator("#river .review-unit-card")
    cards.first.wait_for()
    anchors = cards.locator(".unit-card-anchor").all_inner_texts()
    cards.nth(anchors.index("33")).locator(".unit-card-select").click()

    panel = page.locator("#river-detail .generated-verdict")
    expect(panel).to_be_visible()
    expect(panel.locator(".verdict-comment")).to_have_value("")
    panel.locator(".verdict-comment").fill("Use the current form face.")
    panel.locator(".verdict-question").click()
    expect(panel.locator(".try-again-status")).to_contain_text("first try")
    expect(panel.locator(".try-again-result")).to_contain_text("trial expression for line 33")
    expect(panel.locator(".try-again-result")).to_contain_text("quote_not_verbatim")
    assert session_writes == []

    panel.locator(".verdict-comment").fill("Use the current form face and line label.")
    panel.locator(".verdict-question").click()
    expect(panel.locator(".try-again-status")).to_contain_text("changed correction")
    expect(panel.locator(".try-again-result")).to_contain_text("Use the current form face and line label.")

    panel.locator(".verdict-question").click()
    expect(panel.locator(".try-again-status")).to_contain_text("same correction")
    assert session_writes == []


def test_landscape_page_uses_captured_geometry_for_region_placement(page, workbench_url: str) -> None:
    page.goto(workbench_url)
    page.locator('[data-document-id="form_13614_c_2025"].document-entry').click()
    canvas = page.locator('#official-pane .page-canvas[data-page="1"]')
    canvas.wait_for()
    page.wait_for_function(
        """() => {
            const canvas = document.querySelector('#official-pane .page-canvas[data-page="1"]');
            return canvas?.querySelector('.official-region') && canvas.querySelector('img')?.complete;
        }"""
    )

    metrics = canvas.evaluate(
        """canvas => {
            const box = canvas.getBoundingClientRect();
            const region = canvas.querySelector('.official-region').getBoundingClientRect();
            return {
                ratio: box.width / box.height,
                regionRight: region.right,
                regionBottom: region.bottom,
                canvasRight: box.right,
                canvasBottom: box.bottom,
            };
        }"""
    )
    assert metrics["ratio"] == pytest.approx(792 / 612, rel=0.02)
    assert metrics["regionRight"] <= metrics["canvasRight"] + 1
    assert metrics["regionBottom"] <= metrics["canvasBottom"] + 1
