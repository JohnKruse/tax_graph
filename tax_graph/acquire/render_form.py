"""Render IRS forms with complete text and a separate line-anchor index."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from tax_graph.acquire.text_normalize import normalize_punctuation

LINE_ANCHOR_RE = re.compile(r"^[1-9][0-9]?[a-z]?$")
_SPLIT_LINE_ANCHOR_RE = re.compile(r"^[1-9][0-9]?$", re.IGNORECASE)
_LINE_HEADER_WORDS = {
    "line",
    "amount",
    "total",
    "income",
    "expenses",
    "deduction",
    "tax",
    "wages",
    "rents",
    "royalties",
    "interest",
    "business",
    "other",
}
_NON_LINE_HEADER_PHRASES = (
    "complete this part",
    "instructions for",
    "part i",
    "part ii",
    "part iii",
    "part iv",
    "section ",
)


@dataclass(frozen=True)
class FormRenderResult:
    """Artifacts emitted by the form renderer."""

    document_id: str
    markdown_path: str
    fields_path: str


def render_form_pdf(pdf_path: str | Path, *, document_id: str, output_dir: str | Path) -> FormRenderResult:
    """Render a form PDF into line-numbered markdown and field-grid JSON."""
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    markdown_path = output_root / f"{document_id}.txt"
    fields_path = output_root / f"{document_id}.fields.json"

    markdown = extract_line_markdown(pdf_path)
    fields = extract_field_grid(pdf_path)

    markdown_path.write_text(markdown, encoding="utf-8", newline="\n")
    fields_path.write_text(json.dumps(fields, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return FormRenderResult(
        document_id=document_id,
        markdown_path=str(markdown_path),
        fields_path=str(fields_path),
    )


def extract_line_markdown(pdf_path: str | Path) -> str:
    """Extract the complete normalized PDF text, separated by page markers.

    Line anchors are intentionally absent from this content layer. They are
    emitted separately in the ``line_anchors`` field-grid index.
    """
    import fitz

    pages: list[str] = []
    with fitz.open(pdf_path) as document:
        for page_number, page in enumerate(document, 1):
            page_text = _complete_page_text(page)
            pages.append(page_text.rstrip())
    return "\f".join(pages) + ("\n" if pages else "")


def extract_field_grid(pdf_path: str | Path) -> dict[str, Any]:
    """Extract AcroForm widgets plus the source PDF's per-page geometry."""
    import fitz

    fields: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    line_anchors: list[dict[str, Any]] = []
    text_offset = 0
    with fitz.open(pdf_path) as document:
        for page_number, page in enumerate(document, 1):
            page_text = _complete_page_text(page)
            page_content_offset = text_offset
            page_anchor_records = _line_anchor_records(
                page.get_text("words"),
                page_text,
                text_offset=page_content_offset,
                page_number=page_number,
            )
            line_anchors.extend(page_anchor_records)
            pages.append(
                {
                    "page": page_number,
                    "width": round(float(page.rect.width), 2),
                    "height": round(float(page.rect.height), 2),
                    "rotation": int(page.rotation),
                }
            )
            line_positions = [(item["anchor"], float(item["y0"])) for item in page_anchor_records]
            widgets = page.widgets() or []
            for widget in widgets:
                rect = widget.rect
                field = {
                    "field_name": widget.field_name,
                    "field_type": widget.field_type_string,
                    "field_value": widget.field_value or "",
                    "page": page_number,
                    "x0": round(rect.x0, 2),
                    "y0": round(rect.y0, 2),
                    "x1": round(rect.x1, 2),
                    "y1": round(rect.y1, 2),
                    "x_cluster": _cluster(rect.x0),
                    "y_cluster": _cluster(rect.y0),
                }
                if widget.field_type_string == "CheckBox":
                    field["on_state"] = widget.on_state()
                line_anchor = _nearest_line_anchor(rect.y0, line_positions)
                if line_anchor:
                    field["line_anchor"] = line_anchor
                fields.append(field)
            text_offset += len(page_text.rstrip()) + 1
    return {"fields": fields, "line_anchors": line_anchors, "pages": pages}


def _rows_from_words(words: list[tuple[Any, ...]]) -> list[str]:
    rows = _group_words_by_y(words)
    rendered: list[str] = []
    for row_words in rows:
        tokens = [_clean_token(str(word[4])) for word in sorted(row_words, key=lambda word: word[0])]
        tokens = [token for token in tokens if token and not _is_dot_leader(token)]
        if not tokens:
            continue
        anchor_index = _anchor_index(tokens)
        if anchor_index is None:
            header = _header_row(tokens)
            if header:
                rendered.append(f"Header: {header}")
            continue
        anchor = tokens[anchor_index]
        rest = " ".join(tokens[anchor_index + 1 :])
        rendered.append(f"- {anchor}: {rest}".rstrip())
    return rendered


def _complete_page_text(page: Any) -> str:
    """Emit every PDF word while keeping visual rows citable.

    PyMuPDF's plain-text reading order can split two visual columns across
    unrelated lines. Word rows preserve the source content and association.
    Dot leaders are retained on their own cosmetic lines so they cannot break
    a content quote.
    """
    rows: list[str] = []
    for row_words in _group_words_by_y(page.get_text("words")):
        rows.extend(_rendered_row_strings(row_words))
    return "\n".join(rows)


def _rendered_row_strings(row_words: list[tuple[Any, ...]]) -> list[str]:
    """Return the content and cosmetic lines emitted for one visual row."""
    tokens = [normalize_punctuation(_clean_token(str(word[4]))) for word in sorted(row_words, key=lambda word: word[0])]
    tokens = [token for token in tokens if token]
    content = [token for token in tokens if not _is_dot_leader(token)]
    leaders = [token for token in tokens if _is_dot_leader(token)]
    return [line for line in (" ".join(content), " ".join(leaders)) if line]


def _group_words_by_y(words: list[tuple[Any, ...]], tolerance: float = 3.0) -> list[list[tuple[Any, ...]]]:
    groups: list[list[tuple[Any, ...]]] = []
    for word in sorted(words, key=lambda item: (item[1], item[0])):
        y0 = float(word[1])
        for group in groups:
            if abs(float(group[0][1]) - y0) <= tolerance:
                group.append(word)
                break
        else:
            groups.append([word])
    return groups


def _anchor_index(tokens: list[str]) -> int | None:
    for index, token in enumerate(tokens[:4]):
        if LINE_ANCHOR_RE.fullmatch(token) and not _is_rejected_anchor(tokens, index):
            return index
    return None


def _header_row(tokens: list[str]) -> str | None:
    row = " ".join(tokens).strip()
    lowered = row.lower()
    if not row:
        return None
    if "column" in lowered or re.search(r"\([a-z]\)", lowered):
        return row
    if lowered.startswith("part ") or "schedule d" in lowered:
        return row
    return None


def _line_anchor_positions(words: list[tuple[Any, ...]]) -> list[tuple[str, float]]:
    positions: list[tuple[str, float]] = []
    option_mode = False
    for row_words in _group_words_by_y(words):
        sorted_words = sorted(row_words, key=lambda word: word[0])
        word_tokens = [
            (word, normalize_punctuation(_clean_token(str(word[4]))))
            for word in sorted_words
            if _clean_token(str(word[4])) and not _is_dot_leader(_clean_token(str(word[4])))
        ]
        tokens = [token for _, token in word_tokens]
        if _is_option_header(tokens):
            option_mode = True
            continue
        candidate = _row_anchor(word_tokens, tokens)
        if candidate is None:
            continue
        anchor, first_word, _ = candidate
        if option_mode and _is_option_code_row(tokens, anchor):
            if not any(word in " ".join(tokens).lower() for word in _LINE_HEADER_WORDS):
                continue
            option_mode = False
        elif option_mode:
            option_mode = False
        positions.append((anchor.lower(), float(first_word[1])))
    return positions


def _line_anchor_records(
    words: list[tuple[Any, ...]],
    page_text: str,
    *,
    text_offset: int = 0,
    page_number: int = 1,
) -> list[dict[str, Any]]:
    """Build anchors without removing or rewriting the page text."""
    records: list[dict[str, Any]] = []
    text_cursor = 0
    option_mode = False
    for row_words in _group_words_by_y(words):
        sorted_words = sorted(row_words, key=lambda word: word[0])
        word_tokens = [
            (word, normalize_punctuation(_clean_token(str(word[4]))))
            for word in sorted_words
            if _clean_token(str(word[4])) and not _is_dot_leader(_clean_token(str(word[4])))
        ]
        tokens = [token for _, token in word_tokens]
        rendered_rows = _rendered_row_strings(sorted_words)
        content_text = rendered_rows[0] if rendered_rows else ""
        row_length = sum(len(line) + 1 for line in rendered_rows)
        lowered = " ".join(tokens).lower()
        if _is_option_header(tokens):
            option_mode = True
            text_cursor += row_length
            continue
        candidate = _row_anchor(word_tokens, tokens)
        if candidate is None:
            text_cursor += row_length
            continue
        anchor, first_word, last_word = candidate
        if option_mode and _is_option_code_row(tokens, anchor):
            if not any(word in lowered for word in _LINE_HEADER_WORDS):
                text_cursor += row_length
                continue
            option_mode = False
        elif option_mode:
            option_mode = False
        match = _find_anchor_span(content_text, anchor, 0)
        if match is None:
            text_cursor += row_length
            continue
        records.append(
            {
                "anchor": anchor.lower(),
                "page": page_number,
                "x0": round(float(first_word[0]), 2),
                "x1": round(float(last_word[2]), 2),
                "y0": round(float(first_word[1]), 2),
                "y1": round(float(last_word[3]), 2),
                "text_offset": text_offset + text_cursor + match.start(),
                "text_length": match.end() - match.start(),
            }
        )
        text_cursor += row_length
    return records


def _row_anchor(
    word_tokens: list[tuple[tuple[Any, ...], str]], tokens: list[str]
) -> tuple[str, tuple[Any, ...], tuple[Any, ...]] | None:
    for index, token in enumerate(tokens[:4]):
        if LINE_ANCHOR_RE.fullmatch(token) and not _is_rejected_anchor(tokens, index):
            return token, word_tokens[index][0], word_tokens[index][0]
        if _SPLIT_LINE_ANCHOR_RE.fullmatch(token) and index + 1 < len(tokens):
            suffix = tokens[index + 1].lower()
            if len(suffix) == 1 and suffix.isalpha() and not _is_rejected_anchor(tokens, index):
                return token + suffix, word_tokens[index][0], word_tokens[index + 1][0]
    return None


def _find_anchor_span(text: str, anchor: str, start: int) -> re.Match[str] | None:
    if not text:
        return None
    if anchor[-1].isalpha():
        prefix = re.escape(anchor[: len(anchor) - 1])
        suffix = re.escape(anchor[-1])
        body = rf"{prefix}\s*{suffix}"
    else:
        body = re.escape(anchor)
    pattern = rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])"
    return re.compile(pattern, re.IGNORECASE | re.MULTILINE).search(text, start)


def _is_rejected_anchor(tokens: list[str], index: int) -> bool:
    if index and tokens[index - 1].lower().rstrip(":") in {"box", "boxes", "code", "codes", "option", "options", "page"}:
        return True
    row = " ".join(tokens).lower()
    return any(phrase in row for phrase in _NON_LINE_HEADER_PHRASES)


def _is_option_header(tokens: list[str]) -> bool:
    row = " ".join(tokens).lower()
    return "type of property" in row or "property type" in row or "option codes" in row


def _is_option_code_row(tokens: list[str], anchor: str) -> bool:
    return bool(re.fullmatch(r"[1-8]", anchor)) and len(tokens) > 1


def _nearest_line_anchor(y0: float, positions: list[tuple[str, float]], tolerance: float = 12.0) -> str | None:
    if not positions:
        return None
    anchor, distance = min(
        ((anchor, abs(float(y0) - anchor_y)) for anchor, anchor_y in positions),
        key=lambda item: item[1],
    )
    return anchor if distance <= tolerance else None


def _clean_token(token: str) -> str:
    return token.strip()


def _is_dot_leader(token: str) -> bool:
    stripped = token.strip()
    return bool(stripped) and all(ch in "._" for ch in stripped)


def _cluster(value: float, bucket: int = 25) -> int:
    return round(value / bucket) * bucket


def _ascii_normalize(value: str) -> str:
    return normalize_punctuation(value)
