"""M15 S11 browser checks for lazy official-page review."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.m15


def test_official_pane_lazily_shows_the_scoped_page_and_regions(page, workbench_url: str) -> None:
    page.goto(workbench_url)
    page.locator('[data-document-id="form_8949_2025"].document-entry').click()
    entry = page.locator('[data-document-id="form_8949_2025"][data-check-group="calculations"]')
    entry.click()

    canvas = page.locator("#official-pane .page-canvas")
    canvas.wait_for()
    assert canvas.get_attribute("data-document-id") == "form_8949_2025"
    assert canvas.get_attribute("data-page") == "1"
    image = canvas.locator("img")
    assert "/api/documents/form_8949_2025/pages/1.png" in image.get_attribute("src")
    image.evaluate("image => image.complete && image.naturalWidth > 0")
    regions = canvas.locator(".official-region")
    assert regions.count() > 0
    assert regions.first.get_attribute("data-unit-id")
