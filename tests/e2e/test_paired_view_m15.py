"""M15 A4 official-first layout checks at both target desktop sizes."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.m15


@pytest.mark.parametrize("viewport", [{"width": 1280, "height": 800}, {"width": 1920, "height": 1080}])
def test_three_representative_cases_are_reviewable_without_form_overlays(page, workbench_url: str, viewport) -> None:
    page.set_viewport_size(viewport)
    page.goto(workbench_url)

    select_check(page, "form_1040_2025", "identity_inputs")
    page.locator('#official-pane [data-document-id="form_1040_2025"]').wait_for()
    assert page.locator("#semantic-flow").is_hidden()
    assert page.locator("#official-pane .official-region").count() > 0
    assert all(page.locator("#official-pane .official-region").nth(index).evaluate("element => element.tabIndex >= 0")
               for index in range(page.locator("#official-pane .official-region").count()))
    assert_no_persistent_labels_or_horizontal_overflow(page)
    page.get_by_role("button", name="Next page").click()
    page.locator('#official-pane [data-page="2"]').wait_for()
    page.locator("#official-pane .official-region").first.focus()
    assert page.locator(".field-hover-label").inner_text() != "Hover or focus a field for its label"

    select_check(page, "form_8949_2025", "calculations")
    page.locator('#official-pane [data-document-id="form_8949_2025"]').wait_for()
    selected = page.locator("#official-pane .official-region").first
    selected.click()
    page.get_by_role("button", name="Show semantic flow").click()
    assert page.locator("#semantic-flow .semantic-flow-card").count() == 1
    assert_no_persistent_labels_or_horizontal_overflow(page)

    select_check(page, "schedule_d_2025", "tables_worksheets")
    page.locator("#official-pane .page-gap").wait_for()
    assert "Review gap" in page.locator("#official-pane").inner_text()
    page.get_by_role("button", name="Show semantic flow").click()
    worksheet = page.locator("#semantic-flow .semantic-flow-card")
    assert worksheet.count() > 5
    worksheet.first.click()
    page.locator("#drawer .drawer-heading").wait_for()

    verdicts = page.locator(".verdict-bar button")
    assert verdicts.count() == 4
    assert all(verdicts.nth(index).is_disabled() for index in range(verdicts.count()))
    assert "not yet wired" in page.locator(".verdict-bar").inner_text().lower()

def assert_no_persistent_labels_or_horizontal_overflow(page) -> None:
    region = page.locator("#official-pane .official-region").first
    assert region.evaluate("element => getComputedStyle(element, '::after').content") in {"none", "normal"}
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")


def select_check(page, document_id: str, group_id: str) -> None:
    page.locator(f'[data-document-id="{document_id}"].document-entry').click()
    page.locator(f'[data-document-id="{document_id}"][data-check-group="{group_id}"]').click()
    if document_id != "schedule_d_2025":
        page.locator(f'#official-pane [data-document-id="{document_id}"]').wait_for()
