"""Geometry-first structure proposals for acquired form PDFs.

The corrected form text is the content authority. This module uses the PDF
word and widget rectangles only to recover visual rows and their association.
It never rewrites the text layer or writes an acquired artifact.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from tax_graph.acquire.render_form import _group_words_by_y, _rendered_row_strings
from tax_graph.acquire.text_normalize import normalize_punctuation
from tax_graph.extract.models import SourceDocumentInput


_LINE_TOKEN_RE = re.compile(r"^(?:[1-9][0-9]?[a-z]?|[a-z])$", re.IGNORECASE)
_FULL_LINE_RE = re.compile(r"^[1-9][0-9]?[a-z]$", re.IGNORECASE)
_REJECTED_PRECEDERS = {"box", "boxes", "code", "codes", "option", "options", "page"}
_HEADER_PHRASES = (
    "complete this part",
    "instructions for",
    "part i",
    "part ii",
    "part iii",
    "part iv",
    "section ",
)


@dataclass(frozen=True)
class StructureFinding:
    """One named structure or caption-association finding."""

    code: str
    page: int
    detail: str
    field_name: str = ""
    row_text: str = ""


@dataclass(frozen=True)
class StructureRow:
    """One visual text row with its geometry-derived association."""

    page: int
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    text_offset: int
    line_anchor: str | None = None
    widget_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class StructureModel:
    """Geometry-derived rows, anchor index additions, and findings."""

    rows: tuple[StructureRow, ...]
    line_anchors: tuple[dict[str, Any], ...]
    findings: tuple[StructureFinding, ...]
    captioned_fields: int
    total_fields: int

    @property
    def coverage(self) -> float:
        """Return the fraction of fields associated with a visible text row."""
        if not self.total_fields:
            return 1.0
        return self.captioned_fields / self.total_fields

    def as_dict(self, document_id: str) -> dict[str, Any]:
        """Return a stable report payload for tests and review tooling."""
        return {
            "document_id": document_id,
            "coverage": round(self.coverage, 6),
            "captioned_fields": self.captioned_fields,
            "total_fields": self.total_fields,
            "rows": [
                {
                    "page": row.page,
                    "text": row.text,
                    "line_anchor": row.line_anchor,
                    "widget_names": list(row.widget_names),
                }
                for row in self.rows
            ],
            "findings": [
                {
                    "code": finding.code,
                    "page": finding.page,
                    "detail": finding.detail,
                    "field_name": finding.field_name,
                    "row_text": finding.row_text,
                }
                for finding in self.findings
            ],
        }


def build_structure_model(document: SourceDocumentInput) -> StructureModel | None:
    """Build a geometry-derived model when the acquired PDF is available.

    The source PDF sits beside the rendered field grid in the acquisition
    store. Synthetic extraction fixtures without that PDF continue to use the
    legacy text-only outline builder, which keeps this proposal layer scoped to
    real acquired forms.
    """
    pdf_path = _pdf_path(document)
    if pdf_path is None or not pdf_path.exists():
        return None

    import fitz

    rows: list[StructureRow] = []
    findings: list[StructureFinding] = []
    line_anchors: list[dict[str, Any]] = []
    text_cursor = 0
    text_pages = document.text.split("\f")
    with fitz.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf, 1):
            page_words = page.get_text("words")
            page_text = text_pages[page_number - 1] if page_number <= len(text_pages) else ""
            page_rows = _page_rows(page_words, page_number=page_number, page_text=page_text, text_cursor=text_cursor)
            rows.extend(page_rows)
            text_cursor += len(page_text) + (1 if page_text else 0)
            for row in page_rows:
                if row.line_anchor:
                    line_anchors.append(_anchor_record(row))

    fields = list((document.fields or {}).get("fields", []) or [])
    captioned_fields = 0
    for field in fields:
        match = _nearest_row(field, rows)
        if match is None:
            findings.append(
                StructureFinding(
                    "missing_caption",
                    int(field.get("page", 0) or 0),
                    "widget has no geometry-nearby text row",
                    str(field.get("field_name", "")),
                )
            )
            continue
        captioned_fields += 1

    if not rows:
        findings.append(StructureFinding("empty_structure", 0, "PDF yielded no visual text rows"))
    elif not any(row.line_anchor for row in rows):
        findings.append(
            StructureFinding(
                "no_line_anchors",
                0,
                "document has no printed line anchors; geometry-only association is in use",
            )
        )

    return StructureModel(
        rows=tuple(rows),
        line_anchors=tuple(line_anchors),
        findings=tuple(findings),
        captioned_fields=captioned_fields,
        total_fields=len(fields),
    )


def _pdf_path(document: SourceDocumentInput) -> Path | None:
    """Return the sibling PDF path for a rendered field grid."""
    if document.fields_path is None:
        return None
    name = document.fields_path.name
    if name.endswith(".fields.json"):
        return document.fields_path.with_name(name.removesuffix(".fields.json") + ".pdf")
    return document.fields_path.with_suffix(".pdf")


def _page_rows(
    words: list[tuple[Any, ...]],
    *,
    page_number: int,
    page_text: str,
    text_cursor: int,
) -> list[StructureRow]:
    rows: list[StructureRow] = []
    cursor = 0
    for word_row in _group_words_by_y(words):
        sorted_words = sorted(word_row, key=lambda word: word[0])
        rendered = _rendered_row_strings(sorted_words)
        if not rendered:
            continue
        content = rendered[0]
        if not content or _is_dot_leader(content):
            cursor += sum(len(item) + 1 for item in rendered)
            continue
        x0 = min(float(word[0]) for word in sorted_words)
        y0 = min(float(word[1]) for word in sorted_words)
        x1 = max(float(word[2]) for word in sorted_words)
        y1 = max(float(word[3]) for word in sorted_words)
        offset = page_text.find(content, cursor)
        if offset < 0:
            offset = cursor
        candidates = _anchor_candidates(sorted_words)
        anchor = _defining_anchor(candidates, content)
        rows.append(
            StructureRow(
                page=page_number,
                text=content,
                x0=round(x0, 2),
                y0=round(y0, 2),
                x1=round(x1, 2),
                y1=round(y1, 2),
                text_offset=text_cursor + offset,
                line_anchor=anchor,
            )
        )
        cursor = offset + sum(len(item) + 1 for item in rendered)
    return rows


def _anchor_candidates(words: list[tuple[Any, ...]]) -> list[tuple[str, float]]:
    candidates: list[tuple[str, float]] = []
    tokens = [normalize_punctuation(str(word[4]).strip()) for word in words]
    # The first visual tokens are the row's left label. Later numeric tokens
    # are commonly references inside a caption (for example 1a and 1h in the
    # 1z caption) or ordinary prose such as "6 months". The full row geometry
    # remains available for caption association; only this bounded prefix is
    # eligible to mint a defining line anchor.
    for index, token in enumerate(tokens[:4]):
        if not _LINE_TOKEN_RE.fullmatch(token):
            continue
        if token.isalpha() and token.lower() != "z":
            continue
        if index and tokens[index - 1].lower().rstrip(":") in _REJECTED_PRECEDERS:
            continue
        row = " ".join(tokens).lower()
        if any(phrase in row for phrase in _HEADER_PHRASES):
            continue
        candidates.append((token.lower(), float(words[index][0])))
    return candidates


def _defining_anchor(candidates: list[tuple[str, float]], row_text: str) -> str | None:
    if not candidates:
        return None
    raw_anchor = min(candidates, key=lambda item: item[1])[0]
    if len(raw_anchor) == 1 and raw_anchor.isalpha():
        matches = re.findall(r"\b([0-9]+[a-z])\b", row_text.lower())
        matching = [match for match in matches if match.endswith(raw_anchor)]
        if matching:
            return matching[-1]
    return raw_anchor


def _nearest_row(field: dict[str, Any], rows: list[StructureRow]) -> StructureRow | None:
    page = int(field.get("page", 0) or 0)
    if not page:
        return None
    center = (float(field.get("y0", 0.0)) + float(field.get("y1", 0.0))) / 2
    page_rows = [row for row in rows if row.page == page]
    if not page_rows:
        return None
    row = min(page_rows, key=lambda candidate: abs(((candidate.y0 + candidate.y1) / 2) - center))
    return row if abs(((row.y0 + row.y1) / 2) - center) <= 30 else None


def _anchor_record(row: StructureRow) -> dict[str, Any]:
    """Return a positional index record compatible with span resolution."""
    return {
        "anchor": row.line_anchor,
        "page": row.page,
        "x0": row.x0,
        "x1": row.x1,
        "y0": row.y0,
        "y1": row.y1,
        "text_offset": row.text_offset,
        "text_length": len(row.line_anchor or ""),
    }


def _is_dot_leader(value: str) -> bool:
    stripped = value.strip()
    return bool(stripped) and all(char in "._" for char in stripped)
