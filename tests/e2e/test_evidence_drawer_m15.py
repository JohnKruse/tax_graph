"""M15 S14 browser checks for progressive evidence disclosure."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.m15


def test_clicking_a_unit_pins_real_evidence_with_json_hidden_by_default(page, workbench_url: str) -> None:
    page.goto(workbench_url)
    page.locator('[data-queue-id="promotion_review_form_1040_2025"]').click()
    card = page.locator("#official-pane .official-region").last
    card.click()

    drawer = page.locator("#drawer")
    drawer.locator(".drawer-heading").wait_for()
    assert drawer.locator('[data-drawer-tab="Formula"]').get_attribute("aria-selected") == "true"
    assert drawer.locator('[data-drawer-panel="Formula"] .primary-explanation').inner_text()
    advanced = drawer.locator('[data-drawer-panel="Advanced JSON"]')
    assert advanced.is_hidden()

    drawer.locator('[data-drawer-tab="Advanced JSON"]').click()
    assert advanced.is_visible()
    assert card.get_attribute("data-unit-id") in advanced.inner_text()
