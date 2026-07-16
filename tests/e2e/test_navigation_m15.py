"""M15 S15 keyboard and synchronized-view browser checks."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.m15


def test_keyboard_navigation_and_official_page_zoom(page, workbench_url: str) -> None:
    page.goto(workbench_url)
    select_check(page, "form_8949_2025", "calculations")
    first = page.locator("#official-pane .official-region").first
    first.wait_for()

    page.keyboard.press("j")
    pinned = page.locator("#official-pane .official-region.pinned")
    assert pinned.count() == 1
    first_id = pinned.get_attribute("data-unit-id")
    page.keyboard.press("j")
    assert pinned.get_attribute("data-unit-id") != first_id
    page.keyboard.press("k")
    assert pinned.get_attribute("data-unit-id") == first_id

    active_id = page.locator(".queue-entry.active").get_attribute("data-check-group")
    page.keyboard.press("n")
    page.wait_for_function(
        "id => document.querySelector('.queue-entry.active')?.dataset.checkGroup !== id",
        arg=active_id,
    )
    page.keyboard.press("p")
    page.wait_for_function(
        "id => document.querySelector('.queue-entry.active')?.dataset.checkGroup === id",
        arg=active_id,
    )
    page.wait_for_function(
        "() => document.querySelector('#official-pane .page-canvas')?.dataset.documentId === 'form_8949_2025'"
    )

    page.get_by_role("button", name="Zoom in").click()
    assert page.locator("#official-pane .page-canvas").get_attribute("data-zoom") == "1.25"
    official = page.locator("#official-pane .page-viewport")
    official.evaluate("element => { element.scrollTop = 20; element.dispatchEvent(new Event('scroll')); }")
    assert official.evaluate("element => element.scrollTop") == 20


def test_document_navigation_restores_page_and_selected_field(page, workbench_url: str) -> None:
    page.goto(workbench_url)
    select_check(page, "form_8949_2025", "calculations")
    page.get_by_role("button", name="Next page").click()
    selected = page.locator("#official-pane .official-region").first
    selected.click()
    unit_id = selected.get_attribute("data-unit-id")

    select_check(page, "form_1040_2025", "identity_inputs")
    select_check(page, "form_8949_2025", "calculations")

    assert page.locator("#official-pane .page-canvas").get_attribute("data-page") == "2"
    assert page.locator(f'#official-pane [data-unit-id="{unit_id}"]').get_attribute("aria-pressed") == "true"


def select_check(page, document_id: str, group_id: str) -> None:
    page.locator(f'[data-document-id="{document_id}"].document-entry').click()
    page.locator(f'[data-document-id="{document_id}"][data-check-group="{group_id}"]').click()
    page.locator(f'#official-pane [data-document-id="{document_id}"]').wait_for()
