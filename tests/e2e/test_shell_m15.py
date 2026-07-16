"""M15 S10 browser checks for the no-build static shell."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.m15


def test_shell_loads_and_populates_the_review_queue(page, workbench_url: str) -> None:
    page.goto(workbench_url)

    assert page.title() == "Tax Graph Review Workbench"
    page.get_by_role("heading", name="Review queue").wait_for()
    entries = page.locator(".queue-entry")
    assert entries.count() == 35
    assert "35 entries" in page.locator("#progress").inner_text()
    assert page.get_by_role("heading", name="Official IRS artifact").is_visible()
    assert page.locator("#semantic-flow").is_hidden()
