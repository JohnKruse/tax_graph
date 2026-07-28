"""Derive clean citation text from acquired form-source text."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from tax_graph.acquire.citation_check import _contains_normalized


_WRAPPER_RE = re.compile(r"^\s*-\s*([^:]+):\s*(.*)\Z", re.DOTALL)
_TRAILING_LINE_RE = re.compile(r"\s+(\d+[a-z]?)(?:\s*)\Z", re.IGNORECASE)
_LEADING_SUBLINE_RE = re.compile(r"^([a-z])\s+(?=[A-Z])", re.IGNORECASE)


@dataclass(frozen=True)
class CitationCleanup:
    """One source-verified citation cleanup result."""

    quoted_text: str
    source_document_id: str | None
    changed: bool
    reason: str | None = None


def infer_source_document_id(
    citation: dict[str, Any], *, available_source_ids: set[str]
) -> str | None:
    """Return certain source provenance for a citation, or None when uncertain."""
    explicit = citation.get("source_document_id")
    if explicit:
        return str(explicit)
    document_id = str(citation.get("document_id", ""))
    if document_id in available_source_ids:
        return document_id
    return None


def derive_clean_quote(citation: dict[str, Any], source_text: str) -> CitationCleanup:
    """Remove an extraction wrapper only when the result occurs in source text.

    Form accessibility extraction commonly emits ``- token: text token``. The
    leading marker and a repeated printed line token are extraction scaffolding,
    not the human-quotable text. The source check is deliberately performed
    after every transformation; an unverifiable result is returned unchanged.
    """
    original = str(citation.get("quoted_text", ""))
    match = _WRAPPER_RE.match(original)
    source_id = citation.get("source_document_id")
    if match is None:
        return CitationCleanup(original, str(source_id) if source_id else None, False)

    wrapper_token, body = match.groups()
    candidate = body.strip()
    trailing = _TRAILING_LINE_RE.search(candidate)
    if trailing:
        candidate = candidate[: trailing.start()].rstrip()
    if re.fullmatch(r"\d+", wrapper_token.strip()) and _LEADING_SUBLINE_RE.match(candidate):
        candidate = _LEADING_SUBLINE_RE.sub("", candidate, count=1).strip()
    if not candidate:
        candidate = wrapper_token.strip()

    if not _contains_normalized(source_text, candidate) and not _contains_normalized(source_text, original):
        return CitationCleanup(
            original,
            str(source_id) if source_id else None,
            False,
            "cleaned quote not found in acquired source",
        )
    return CitationCleanup(candidate, str(source_id) if source_id else None, candidate != original)
