"""M15 S13 browser checks for the core paired-review gesture."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.m15


def test_form_1040_pairing_works_in_both_directions_and_click_pins(page, workbench_url: str) -> None:
    page.goto(workbench_url)
    page.locator('[data-queue-id="field_map_review_form_1040_2025"]').click()
    # The last page region is topmost when official fields geometrically touch.
    official = page.locator("#official-pane .official-region").last
    unit_id = official.get_attribute("data-unit-id")
    analog = page.locator(f'#analog-pane .analog-card[data-unit-id="{unit_id}"]')

    official.hover()
    assert official.evaluate("element => element.classList.contains('paired')")
    assert analog.evaluate("element => element.classList.contains('paired')")
    analog.hover()
    assert official.evaluate("element => element.classList.contains('paired')")
    assert analog.evaluate("element => element.classList.contains('paired')")

    analog.click()
    page.locator("header.topbar").hover()
    assert official.evaluate("element => element.classList.contains('pinned')")
    assert analog.evaluate("element => element.classList.contains('pinned')")
    assert official.get_attribute("aria-pressed") == "true"
    assert analog.get_attribute("aria-pressed") == "true"
