"""M17 S3 browser checks for the cell-atomic review workbench shell."""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import expect


pytestmark = pytest.mark.m17


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

    checkbox = card.locator('input[type="checkbox"]')
    assert checkbox.count() == 1
    checkbox.check()
    note = card.locator("textarea")
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
    page.goto(workbench_url)
    page.locator('[data-document-id="form_1040_2025"].document-entry').click()
    cards = page.locator("#river .review-unit-card")
    cards.first.wait_for()

    # The printed line leads the card header, with the authored label after it.
    headings = cards.locator(".unit-card-heading").all_inner_texts()
    line_index = next(index for index, heading in enumerate(headings) if heading.startswith("33 - "))
    line_card = cards.nth(line_index)
    expect(line_card.locator(".unit-card-heading")).to_have_text(re.compile(r"^33 - "))
    line_card.locator(".unit-card-select").click()

    detail = page.locator("#river-detail")
    expect(detail.locator("h2")).to_have_text(re.compile(r"^33 - "))
    expect(detail.locator(".cell-instruction")).to_contain_text("Not yet ingested")
    expect(detail.locator(".authority")).to_be_visible()
    expect(detail.locator(".authority")).to_contain_text("No authority has been authored")
    expect(detail.locator(".human-dossier").nth(1)).to_contain_text("How this is filled")
    assert detail.locator("details.technical-record").get_attribute("open") is None

    # Existing instruction-sourced text belongs in the instruction slot, not in
    # Authority. The 1040 line 1a record is the promoted canary citation.
    line_1a = cards.filter(has_text="1a - Total amount from Form(s) W-2").first
    line_1a.locator(".unit-card-select").click()
    expect(detail.locator(".cell-instruction")).to_contain_text("Enter the total amount")
    expect(detail.locator(".authority")).to_contain_text("Total amount from Form(s) W-2")

    # M19 occurrence axes make the repeated dependent row human-addressable.
    dependent_card = cards.filter(has_text="Dependent 3 of 4").first
    dependent_card.wait_for()
    dependent_card.locator(".unit-card-select").click()
    expect(detail.locator(".dossier-occurrence")).to_have_text("Dependent 3 of 4")
