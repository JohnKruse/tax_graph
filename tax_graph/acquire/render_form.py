"""Render IRS forms with PyMuPDF using line numbers as anchors."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any


LINE_ANCHOR_RE = re.compile(r"^(?:\d+[a-z]?|[a-z])$")


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

    markdown_path.write_text(markdown, encoding="utf-8")
    fields_path.write_text(json.dumps(fields, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return FormRenderResult(
        document_id=document_id,
        markdown_path=str(markdown_path),
        fields_path=str(fields_path),
    )


def extract_line_markdown(pdf_path: str | Path) -> str:
    """Extract line-number-anchored rows from a form PDF."""
    import fitz

    rows: list[str] = []
    with fitz.open(pdf_path) as document:
        for page_number, page in enumerate(document, 1):
            page_rows = _rows_from_words(page.get_text("words"))
            if page_rows:
                rows.append(f"# Page {page_number}")
                rows.extend(page_rows)
    return _ascii_normalize("\n".join(rows) + ("\n" if rows else ""))


def extract_field_grid(pdf_path: str | Path) -> dict[str, Any]:
    """Extract AcroForm widget positions for downstream cross-checking."""
    import fitz

    fields: list[dict[str, Any]] = []
    with fitz.open(pdf_path) as document:
        for page_number, page in enumerate(document, 1):
            widgets = page.widgets() or []
            for widget in widgets:
                rect = widget.rect
                fields.append(
                    {
                        "field_name": widget.field_name,
                        "page": page_number,
                        "x0": round(rect.x0, 2),
                        "y0": round(rect.y0, 2),
                        "x1": round(rect.x1, 2),
                        "y1": round(rect.y1, 2),
                        "x_cluster": _cluster(rect.x0),
                        "y_cluster": _cluster(rect.y0),
                    }
                )
    return {"fields": fields}


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
            continue
        anchor = tokens[anchor_index]
        rest = " ".join(tokens[anchor_index + 1 :])
        rendered.append(f"- {anchor}: {rest}".rstrip())
    return rendered


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
        if LINE_ANCHOR_RE.match(token):
            return index
    return None


def _clean_token(token: str) -> str:
    return token.strip()


def _is_dot_leader(token: str) -> bool:
    stripped = token.strip()
    return bool(stripped) and all(ch in "._" for ch in stripped)


def _cluster(value: float, bucket: int = 25) -> int:
    return round(value / bucket) * bucket


def _ascii_normalize(value: str) -> str:
    return value.encode("ascii", errors="ignore").decode("ascii")
