"""M20-S158 guards for fixed-span attribution and closed line answers."""

from __future__ import annotations

from pathlib import Path

import pytest

from pilot.attribution_m20_s158 import (
    FixedSpan,
    SCHEDULE_1A_CEILING_LINES,
    SCHEDULE_1A_GOVERNING_LINES,
    attribution_schema,
    build_attribution_prompt,
    score_attributions,
    validate_attributions,
)


pytestmark = pytest.mark.m20


def _spans() -> tuple[FixedSpan, ...]:
    return (
        FixedSpan("span_a", "Part I", (), 0, 10, "<h2>Part I</h2><p>MAGI</p>"),
        FixedSpan("span_b", "Example", (), 10, 20, "<h2>Example</h2><p>line 7</p>"),
    )


def test_schema_closes_span_ids_and_line_tokens_and_allows_empty() -> None:
    schema = attribution_schema(span_ids=("span_a", "span_b"), line_tokens=("1", "2a"))
    item = schema["properties"]["attributions"]["items"]
    assert schema["properties"]["attributions"]["minItems"] == 2
    assert item["properties"]["span_id"]["enum"] == ["span_a", "span_b"]
    assert item["properties"]["governs"]["items"]["enum"] == ["1", "2a"]
    assert item["additionalProperties"] is False


def test_prompt_contains_inventory_and_forbids_body_reference_mining() -> None:
    prompt = build_attribution_prompt(
        "demo_2025",
        _spans(),
        ("1", "2a"),
        template="Do not mine line references from body prose.",
    )
    assert '"1","2a"' in prompt
    assert "span_a" in prompt
    assert "Do not mine line references from body prose." in prompt
    assert "form cell" not in prompt.lower()


def test_validation_requires_every_span_and_rejects_unknown_lines() -> None:
    spans = _spans()
    assert validate_attributions(
        {"attributions": [{"span_id": "span_a", "governs": []}, {"span_id": "span_b", "governs": ["1"]}]},
        spans=spans,
        line_tokens=("1", "2a"),
    ) == {"span_a": (), "span_b": ("1",)}
    with pytest.raises(ValueError, match="unknown line tokens"):
        validate_attributions(
            {"attributions": [{"span_id": "span_a", "governs": ["line 1"]}, {"span_id": "span_b", "governs": []}]},
            spans=spans,
            line_tokens=("1", "2a"),
        )


def test_score_reports_none_rate_zero_movement_and_excludes_ceiling() -> None:
    spans = _spans()
    labels = {"span_a": ("1",), "span_b": ()}
    report = score_attributions(
        "schedule_1a_2025",
        spans=spans,
        labels=labels,
        line_tokens=("1", "2a", "6"),
        before_instruction_lines=(),
        reference_lines=("1", "2a"),
        ceiling_lines=("6",),
    )
    assert report["none_count"] == 1
    assert report["none_rate"] == 0.5
    assert report["zero_instruction_cells_before"] == 3
    assert report["zero_instruction_cells_after"] == 2
    assert report["schedule_1a_score"]["denominator"] == 2
    assert report["schedule_1a_score"]["ceiling_count_excluded"] == 1


def test_reference_and_ceiling_sets_are_disjoint_and_have_specified_sizes() -> None:
    assert len(SCHEDULE_1A_GOVERNING_LINES) == 19
    assert len(SCHEDULE_1A_CEILING_LINES) == 18
    assert not SCHEDULE_1A_GOVERNING_LINES & SCHEDULE_1A_CEILING_LINES


def test_run_documents_rejects_repository_output(tmp_path: Path) -> None:
    from pilot.attribution_m20_s158 import run_documents

    with pytest.raises(ValueError, match="outside the repository root"):
        run_documents(
            (),
            root=tmp_path,
            output=tmp_path / "inside" / "report.json",
        )
