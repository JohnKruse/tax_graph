"""Deterministic presentation helpers for source-backed model evidence."""

from __future__ import annotations

import re


_LINE_END_HYPHEN_RE = re.compile(r"(?<=[A-Za-z])-(?:\r?\n)(?=\s*[a-z])")


def normalize_evidence_text(value: object) -> str:
    """Remove only source line-end hyphens for model-facing evidence.

    The acquired source remains canonical. This presentation-only operation
    handles a word split by the source renderer at a line boundary; it does
    not repair punctuation, join arbitrary fragments, or apply fuzzy matching.
    """

    return _LINE_END_HYPHEN_RE.sub("", str(value))


def evidence_quote_matches(quote: object, source: object) -> bool:
    """Match a quote against already prepared evidence after whitespace folding."""

    def folded(value: object) -> str:
        return " ".join(str(value).split())

    wanted = folded(quote)
    available = folded(source)
    return bool(wanted) and wanted in available


def span_evidence_text(span: object) -> str:
    """Return the model-facing text prepared for a candidate span.

    ``CandidateSpan.text`` remains the canonical source slice used for
    citations and ranges. ``evidence_text`` is the separately prepared packet
    representation, so a validator never repairs canonical source text.
    """
    prepared = getattr(span, "evidence_text", None)
    if prepared is not None:
        return str(prepared)
    return str(getattr(span, "text", span))
