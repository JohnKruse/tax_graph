"""M15 S16 Gate A vertical-slice checks at both target desktop sizes."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.m15


@pytest.mark.parametrize("viewport", [{"width": 1280, "height": 800}, {"width": 1920, "height": 1080}])
def test_three_representative_cases_are_reviewable_in_the_paired_view(page, workbench_url: str, viewport) -> None:
    page.set_viewport_size(viewport)
    page.goto(workbench_url)

    page.locator('[data-case-target="field_map_review_form_1040_2025"]').click()
    page.locator('#official-pane [data-document-id="form_1040_2025"]').wait_for()
    classes = {value.lower() for value in page.locator("#analog-pane .semantic-kind").all_inner_texts()}
    page.get_by_role("button", name="Next page").click()
    page.locator('#official-pane [data-page="2"]').wait_for()
    assert page.locator("#analog-pane .page-canvas").get_attribute("data-page") == "2"
    classes.update(value.lower() for value in page.locator("#analog-pane .semantic-kind").all_inner_texts())
    assert {"input", "copy", "calculation", "lookup", "branch"} <= classes
    assert_side_by_side(page)

    page.locator('[data-case-target="field_map_review_form_8949_2025"]').click()
    page.locator('#official-pane [data-document-id="form_8949_2025"]').wait_for()
    summaries = page.locator("#analog-pane .semantic-summary").all_inner_texts()
    assert any("Per transaction" in summary for summary in summaries)
    assert any("Total column" in summary for summary in summaries)

    page.locator('[data-case-target="authored_review_schedule_d_2025_tax_worksheet"]').click()
    worksheet = page.locator("#analog-pane .evidence-analog-list")
    worksheet.wait_for()
    assert worksheet.locator(".analog-card").count() > 5
    assert "Review gap" in page.locator("#official-pane").inner_text()
    worksheet.locator(".analog-card").first.click()
    page.locator("#drawer .drawer-heading").wait_for()

    verdicts = page.locator(".verdict-bar button")
    assert verdicts.count() == 4
    assert all(verdicts.nth(index).is_disabled() for index in range(verdicts.count()))
    assert "not yet wired" in page.locator(".verdict-bar").inner_text().lower()


def assert_side_by_side(page) -> None:
    official = page.locator(".review-pane").nth(0).bounding_box()
    analog = page.locator(".review-pane").nth(1).bounding_box()
    assert official is not None and analog is not None
    assert official["width"] > 300
    assert analog["width"] > 300
    assert analog["x"] > official["x"] + official["width"]
    assert abs(official["y"] - analog["y"]) < 2
