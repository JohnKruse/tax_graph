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
_REFERENCE_PRECEDERS = _REJECTED_PRECEDERS | {"line", "lines", "through"}
_RIGHT_EDGE_TOLERANCE = 24.0
_HEADER_PHRASES = (
    "complete this part",
    "instructions for",
    "part i",
    "part ii",
    "part iii",
    "part iv",
    "section ",
    "for paperwork reduction act notice",
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
    printed_anchor: str | None = None
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
                    "printed_anchor": row.printed_anchor,
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
            page_rows = _page_rows(
                page_words,
                page_number=page_number,
                page_text=page_text,
                text_cursor=text_cursor,
                page_width=float(page.rect.width),
                allow_line_anchors=bool((document.fields or {}).get("line_anchors")),
            )
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
    findings.extend(_anchor_identity_findings(rows))

    return StructureModel(
        rows=tuple(rows),
        line_anchors=tuple(line_anchors),
        findings=tuple(findings),
        captioned_fields=captioned_fields,
        total_fields=len(fields),
    )


def validate_anchor_identity(model: StructureModel) -> tuple[StructureFinding, ...]:
    """Return named findings when a minted anchor disagrees with print geometry.

    The line anchor is minted by the structure splitter. The independent witness
    is the right-edge printed token captured on the same visual row. A caller
    that requires a safe outline must treat any returned finding as a failure;
    this function never repairs or silently chooses between competing anchors.
    """
    return tuple(_anchor_identity_findings(model.rows))


def _anchor_identity_findings(rows: list[StructureRow]) -> list[StructureFinding]:
    findings: list[StructureFinding] = []
    for row in rows:
        if not row.line_anchor or not row.printed_anchor:
            continue
        if row.line_anchor == row.printed_anchor:
            continue
        findings.append(
            StructureFinding(
                "anchor_identity_disagreement",
                row.page,
                f"minted anchor {row.line_anchor} disagrees with right-edge printed anchor {row.printed_anchor}",
                row_text=row.text,
            )
        )
    return findings


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
    page_width: float = 612.0,
    allow_line_anchors: bool = True,
) -> list[StructureRow]:
    rows: list[StructureRow] = []
    cursor = 0
    prior_anchor: str | None = None
    for word_row in _group_words_by_y(words):
        sorted_words = sorted(word_row, key=lambda word: word[0])
        rendered = _rendered_row_strings(sorted_words)
        if not rendered:
            continue
        content = rendered[0]
        if not content or _is_dot_leader(content):
            cursor += sum(len(item) + 1 for item in rendered)
            continue
        row_offset = page_text.find(content, cursor)
        if row_offset < 0:
            row_offset = cursor
        groups = (
            _row_anchor_groups(sorted_words, page_width=page_width, prior_anchor=prior_anchor)
            if allow_line_anchors
            else []
        )
        if not groups:
            rows.append(
                _make_structure_row(
                    sorted_words,
                    page=page_number,
                    page_text=page_text,
                    text_cursor=text_cursor,
                    search_from=row_offset,
                    anchor=None,
                )
            )
        else:
            search_from = row_offset
            for group_words, anchor in groups:
                rows.append(
                    _make_structure_row(
                        group_words,
                        page=page_number,
                        page_text=page_text,
                        text_cursor=text_cursor,
                        search_from=search_from,
                        anchor=anchor,
                    )
                )
                group_text = _rendered_row_strings(group_words)[0]
                group_offset = page_text.find(group_text, search_from)
                if group_offset >= 0:
                    search_from = group_offset + len(group_text)
                prior_anchor = anchor
        cursor = row_offset + sum(len(item) + 1 for item in rendered)
        if groups:
            prior_anchor = groups[-1][1]
    return rows


def _anchor_candidates(words: list[tuple[Any, ...]]) -> list[tuple[str, float]]:
    return [(item["anchor"], item["x0"]) for item in _anchor_token_candidates(words)]


def _defining_anchor(candidates: list[tuple[str, float]], row_text: str) -> str | None:
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[1])[0]


def _anchor_token_candidates(words: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
    """Return line-like tokens after removing caption references and headers.

    A line reference in prose is not a row identity. In particular, the token
    after ``Add lines`` must not beat the printed row reference at the far
    right. The returned positions let the row splitter distinguish genuine
    side-by-side columns from those references.
    """
    tokens = [normalize_punctuation(str(word[4]).strip()) for word in words]
    row = " ".join(tokens).strip().lower()
    if _is_header_text(row):
        return []
    candidates: list[dict[str, Any]] = []
    for index, token in enumerate(tokens):
        if not _LINE_TOKEN_RE.fullmatch(token):
            continue
        lowered = token.lower()
        if token.isalpha() and lowered != "z":
            continue
        previous = tokens[index - 1].lower().rstrip(":") if index else ""
        if previous in _REFERENCE_PRECEDERS:
            continue
        anchor = lowered
        if token.isdigit() and index + 1 < len(tokens):
            suffix = tokens[index + 1].lower()
            gap = float(words[index + 1][0]) - float(words[index][2])
            if len(suffix) == 1 and suffix.isalpha() and gap <= 18:
                anchor = f"{anchor}{suffix}"
        candidates.append(
            {
                "anchor": anchor,
                "index": index,
                "x0": float(words[index][0]),
                "x1": float(words[index][2]),
            }
        )
    return candidates


def _row_anchor_groups(
    words: list[tuple[Any, ...]],
    *,
    page_width: float,
    prior_anchor: str | None,
) -> list[tuple[list[tuple[Any, ...]], str]]:
    """Return one or two geometry-backed row groups with canonical anchors.

    The right half is authoritative when a row has a printed right-edge
    reference. Two groups are emitted only for sibling suffixes sharing a
    numeric base, such as 4a and 4b. This prevents prose references like
    ``1a or 1d`` from becoming a second row while preserving real two-column
    form rows.
    """
    candidates = _anchor_token_candidates(words)
    if not candidates:
        return []
    boundary = page_width / 2
    row_text = " ".join(normalize_punctuation(str(word[4]).strip()) for word in words).lower()
    if "check if" in row_text and not any(item["x0"] >= page_width * 0.75 for item in candidates):
        return []
    left_candidates = [item for item in candidates if item["x0"] < boundary * 0.42]
    right_candidates = [item for item in candidates if item["x0"] >= boundary]
    left = _canonical_candidate(left_candidates[0] if left_candidates else None, prior_anchor)
    right = _canonical_candidate(right_candidates[-1] if right_candidates else None, prior_anchor)

    if left and right and left != right and _same_numeric_base(left, right):
        split = [word for word in words if float(word[0]) < boundary]
        remainder = [word for word in words if float(word[0]) >= boundary]
        if split and remainder:
            return [(split, left), (remainder, right)]
    if right:
        return [(words, right)]
    if left:
        return [(words, left)]

    # A wrapped suffix row can carry only ``z``/``e`` at its left edge. Qualify
    # it with the numeric base of the preceding visual row instead of minting
    # a bare letter address.
    suffix = _canonical_candidate(candidates[0], prior_anchor)
    return [(words, suffix)] if suffix else []


def _canonical_candidate(candidate: dict[str, Any] | None, prior_anchor: str | None) -> str | None:
    if candidate is None:
        return None
    anchor = str(candidate["anchor"]).lower()
    if anchor.isalpha() and prior_anchor:
        base = "".join(char for char in prior_anchor if char.isdigit())
        if base:
            return f"{base}{anchor}"
    return anchor


def _same_numeric_base(left: str, right: str) -> bool:
    left_base = "".join(char for char in left if char.isdigit())
    right_base = "".join(char for char in right if char.isdigit())
    return bool(left_base and left_base == right_base and left != right)


def _is_header_text(row: str) -> bool:
    lowered = row.strip().lower()
    if not lowered:
        return True
    if lowered.startswith(
        (
            "schedule ",
            "part ",
            "section ",
            "dependents",
            "for the year",
            "go to www",
            "file with",
        )
    ):
        return True
    if "dependent 1" in lowered and "dependent 2" in lowered:
        return True
    # A caption can legitimately mention a section (for example, Schedule 1
    # line 8n).  Only a row that starts with a known header phrase is a header;
    # substring matching suppresses real lettered line anchors.
    return any(lowered.startswith(phrase) for phrase in _HEADER_PHRASES)


def _make_structure_row(
    words: list[tuple[Any, ...]],
    *,
    page: int,
    page_text: str,
    text_cursor: int,
    search_from: int,
    anchor: str | None,
) -> StructureRow:
    rendered = _rendered_row_strings(words)
    content = rendered[0] if rendered else ""
    offset = page_text.find(content, search_from) if content else -1
    if offset < 0:
        offset = search_from
    return StructureRow(
        page=page,
        text=content,
        x0=round(min(float(word[0]) for word in words), 2),
        y0=round(min(float(word[1]) for word in words), 2),
        x1=round(max(float(word[2]) for word in words), 2),
        y1=round(max(float(word[3]) for word in words), 2),
        text_offset=text_cursor + offset,
        line_anchor=anchor,
        printed_anchor=_right_edge_printed_anchor(words, anchor),
    )


def _right_edge_printed_anchor(
    words: list[tuple[Any, ...]],
    derived_anchor: str | None,
) -> str | None:
    """Read the independent right-edge line token from one visual row."""
    tokens = [normalize_punctuation(str(word[4]).strip()) for word in words]
    row = " ".join(tokens).strip().lower()
    if _is_header_text(row):
        return None
    candidates: list[dict[str, Any]] = []
    for index, token in enumerate(tokens):
        if not _LINE_TOKEN_RE.fullmatch(token):
            continue
        lowered = token.lower()
        if token.isalpha() and lowered != "z":
            continue
        previous = tokens[index - 1].lower().rstrip(":") if index else ""
        if previous in _REFERENCE_PRECEDERS:
            continue
        anchor = lowered
        if token.isdigit() and index + 1 < len(tokens):
            suffix = tokens[index + 1].lower()
            gap = float(words[index + 1][0]) - float(words[index][2])
            if len(suffix) == 1 and suffix.isalpha() and gap <= 18:
                anchor = f"{anchor}{suffix}"
        candidates.append({"anchor": anchor, "x1": float(words[index][2])})
    if not candidates:
        return None
    right_edge = max(float(word[2]) for word in words)
    right_edge_candidates = [
        item for item in candidates if item["x1"] >= right_edge - _RIGHT_EDGE_TOLERANCE
    ]
    if not right_edge_candidates:
        return None
    anchor = str(max(right_edge_candidates, key=lambda item: item["x1"])["anchor"])
    if anchor.isalpha() and derived_anchor:
        base = "".join(char for char in derived_anchor if char.isdigit())
        if base:
            return f"{base}{anchor}"
    return anchor


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
