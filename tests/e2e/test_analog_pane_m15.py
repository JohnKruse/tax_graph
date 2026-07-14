"""M15 S12 browser checks for the aligned semantic analog."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.m15


def test_analog_cards_align_and_link_to_official_regions(page, workbench_url: str) -> None:
    page.goto(workbench_url)
    page.locator('[data-queue-id="field_map_review_form_8949_2025"]').click()

    official = page.locator("#official-pane .official-region").first
    unit_id = official.get_attribute("data-unit-id")
    analog = page.locator(f'#analog-pane .analog-card[data-unit-id="{unit_id}"]')
    analog.wait_for()

    assert analog.locator(".semantic-summary").inner_text()
    assert analog.locator(".semantic-kind").inner_text()
    connector = analog.locator(".pair-connector")
    assert connector.is_visible()
    official_box = official.bounding_box()
    analog_box = analog.bounding_box()
    assert official_box is not None and analog_box is not None
    assert abs(official_box["y"] - analog_box["y"]) < 24
