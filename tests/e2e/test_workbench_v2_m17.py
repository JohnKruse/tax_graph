"""M17 S3 browser checks for the cell-atomic review workbench shell."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.m17


def test_three_pane_shell_exposes_cell_river_and_local_review_state(page, workbench_url: str) -> None:
    page.goto(workbench_url)

    assert page.locator(".review-layout").count() == 1
    assert page.locator("#official-pane").count() == 1
    assert page.locator("#drawer").count() == 1
    assert page.locator("#save-progress").is_disabled()

    page.locator('[data-document-id="form_8949_2025"].document-entry').click()
    page.locator('[data-document-id="form_8949_2025"][data-check-group="calculations"]').click()
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
