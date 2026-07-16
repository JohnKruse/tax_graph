"""M15 A4 browser checks for hover, focus, and pinned field selection."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.m15


def test_form_1040_field_label_and_click_pin_do_not_cover_the_form(page, workbench_url: str) -> None:
    page.goto(workbench_url)
    page.locator('[data-queue-id="field_map_review_form_1040_2025"]').click()
    # The last page region is topmost when official fields geometrically touch.
    official = page.locator("#official-pane .official-region").last
    official.hover()
    assert official.evaluate("element => element.classList.contains('paired')")
    assert official.get_attribute("data-label") in page.locator(".field-hover-label").inner_text()
    official.click()
    page.locator("#drawer .drawer-heading").wait_for()
    assert page.locator("#drawer .drawer-heading h2").evaluate("element => element === document.activeElement")
    page.locator("#official-pane .page-canvas img").click(position={"x": 2, "y": 2})
    assert official.evaluate("element => element.classList.contains('pinned')")
    assert official.get_attribute("aria-pressed") == "true"
