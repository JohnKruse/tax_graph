"""M20-S142 tests for run-in instruction projection."""

from __future__ import annotations

import pytest

from workbench.generated_review import (
    _instruction_citation,
    _instruction_run_in_segments,
)


@pytest.mark.m20
def test_instruction_run_in_segments_use_singular_line_labels_only() -> None:
    text = (
        "## Lines 17a Through 17z\n\n"
        "### Other Additional Taxes\n\n"
        "**Line 17a.** Recapture of the following credits.\n\n"
        "**Line 17b.** Enter the additional tax. See line 13b.\n\n"
        "##### Line 17z\n\n"
        "List the type and amount of tax.\n"
    )

    segments = _instruction_run_in_segments(text)

    assert set(segments) == {"17a", "17b", "17z"}
    assert segments["17a"] == "**Line 17a.** Recapture of the following credits."
    assert "**Line 17b.**" not in segments["17a"]
    assert "See line 13b." in segments["17b"]


@pytest.mark.m20
def test_instruction_run_in_segments_accept_artifact_label_forms() -> None:
    text = (
        "## Lines 1a Through 1z\n\n"
        "**Line 1a. Excess advance premium tax credit repayment.** The amount.\n\n"
        "##### Line 24a\n\nJury duty pay.\n\n"
        "### Line 13b\n\nAdditional deductions.\n"
    )

    segments = _instruction_run_in_segments(text)

    assert set(segments) == {"1a", "24a", "13b"}
    assert segments["1a"].startswith(
        "**Line 1a. Excess advance premium tax credit repayment.**"
    )
    assert segments["24a"].startswith("##### Line 24a")
    assert segments["13b"].startswith("### Line 13b")


@pytest.mark.m20
def test_instruction_citation_keeps_full_block_when_line_has_no_run_in_label() -> None:
    text = (
        "## Lines 17a Through 17z\n\n"
        "**Line 17a.** Recapture of the following credits.\n\n"
        "**Line 17b.** Enter the additional tax.\n"
    )
    span = {
        "span_id": "span_shared",
        "document_id": "instructions_form_1040_2025",
        "owner_lines": ["17a", "17b", "17c"],
        "locator": "page 113, lines 6689-6753",
        "text": text,
    }

    labelled = _instruction_citation("span_shared", span, "17a")
    unlabelled = _instruction_citation("span_shared", span, "17c")

    assert labelled["citation_id"] == "span_shared__line_17a"
    assert labelled["source_span_id"] == "span_shared"
    assert labelled["projection"] == "run_in_line"
    assert labelled["quoted_text"] == "**Line 17a.** Recapture of the following credits."
    assert unlabelled["citation_id"] == "span_shared"
    assert unlabelled["quoted_text"] == text
    assert "source_span_id" not in unlabelled
