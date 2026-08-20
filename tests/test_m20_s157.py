from __future__ import annotations

import pytest

from tax_graph.extract.evidence import evidence_quote_matches, normalize_evidence_text
from tax_graph.extract.micro import MicroExtractionError, validate_formula_plan
from tax_graph.extract.outline import CandidateSpan, join_adjacent_source_spans


def _span(
    span_id: str,
    start: int,
    end: int,
    text: str,
    *,
    evidence_text: str | None = None,
) -> CandidateSpan:
    return CandidateSpan(
        span_id=span_id,
        document_id="fixture",
        relationship="source",
        locator=span_id,
        text=text,
        evidence_text=evidence_text,
        source_ranges=({"start": start, "end": end},),
    )


def test_evidence_normalization_is_presentation_only_and_exact() -> None:
    source = "deduc-\ntion"

    assert normalize_evidence_text(source) == "deduction"
    assert not evidence_quote_matches("deduction", source)
    assert evidence_quote_matches("deduction", normalize_evidence_text(source))
    assert not evidence_quote_matches("deduction.", source)
    assert source == "deduc-\ntion"


def test_joined_span_uses_only_contiguous_source_offsets() -> None:
    source = "first\nsecond\nbarrier X third"
    spans = [
        _span("span_1", 0, 5, "first"),
        _span("span_2", 6, 12, "second"),
        _span("span_3", 13, 20, "barrier"),
        _span("span_4", 23, 28, "third"),
    ]

    derived = join_adjacent_source_spans(spans, source_text=source)

    assert len(derived) == 2
    first_join = next(span for span in derived if span.joined_from == ("span_1", "span_2"))
    assert first_join.text == source[0:12]
    assert first_join.evidence_text == source[0:12]
    assert first_join.source_ranges == ({"start": 0, "end": 12},)
    assert not any(span.joined_from == ("span_3", "span_4") for span in derived)


def test_formula_quote_validation_uses_normalized_packet_not_fuzzy_acceptance() -> None:
    spans = [
        _span(
            "span_1",
            0,
            11,
            "deduc-\ntion",
            evidence_text="deduction",
        )
    ]
    plan = {
        "operation": "SUM",
        "source_lines": ["1"],
        "quote": "deduction",
    }

    validate_formula_plan(plan, spans=spans)
    with pytest.raises(MicroExtractionError):
        validate_formula_plan({**plan, "quote": "deduction."}, spans=spans)
    with pytest.raises(MicroExtractionError):
        validate_formula_plan(
            plan,
            spans=[_span("span_1", 0, 11, "deduc-\ntion")],
        )
