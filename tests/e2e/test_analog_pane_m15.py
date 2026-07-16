"""M15 A4 browser checks for selected-only semantic flow."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.m15


def test_semantic_flow_is_hidden_until_requested_and_contains_only_selection(page, workbench_url: str) -> None:
    page.goto(workbench_url)
    page.locator('[data-document-id="form_8949_2025"].document-entry').click()
    page.locator('[data-document-id="form_8949_2025"][data-check-group="calculations"]').click()

    official = page.locator("#official-pane .official-region").first
    assert page.locator("#semantic-flow").is_hidden()
    official.click()
    unit_id = official.get_attribute("data-unit-id")
    page.get_by_role("button", name="Show semantic flow").click()
    flow = page.locator("#semantic-flow")
    assert flow.is_visible()
    cards = flow.locator(".semantic-flow-card")
    assert cards.count() == 1
    assert cards.first.get_attribute("data-unit-id") == unit_id
    assert cards.first.locator(".semantic-summary").inner_text()
    page.get_by_role("button", name="Close").click()
    assert flow.is_hidden()
