"""M15 S15 keyboard and synchronized-view browser checks."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.m15


def test_keyboard_navigation_and_official_page_zoom(page, workbench_url: str) -> None:
    page.goto(workbench_url)
    page.locator('[data-queue-id="field_map_review_form_8949_2025"]').click()
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

    active_id = page.locator(".queue-entry.active").get_attribute("data-queue-id")
    page.keyboard.press("n")
    page.wait_for_function(
        "id => document.querySelector('.queue-entry.active')?.dataset.queueId !== id",
        arg=active_id,
    )
    page.keyboard.press("p")
    page.wait_for_function(
        "id => document.querySelector('.queue-entry.active')?.dataset.queueId === id",
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
