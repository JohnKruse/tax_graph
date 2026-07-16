"""M15 S10 browser checks for the no-build static shell."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.m15


def test_shell_loads_and_populates_the_review_queue(page, workbench_url: str) -> None:
    page.goto(workbench_url)

    assert page.title() == "Tax Graph Review Workbench"
    page.get_by_role("heading", name="Documents").wait_for()
    documents = page.locator(".document-entry")
    assert documents.count() >= 17
    assert "35 entries" in page.locator("#progress").inner_text()
    assert page.get_by_text("Gate A cases").count() == 0
    assert all("review_" not in text for text in documents.all_inner_texts())
    assert page.get_by_role("heading", name="Official IRS artifact").is_visible()
    assert page.locator("#semantic-flow").is_hidden()
