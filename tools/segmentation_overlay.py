"""Show the whole booklet text with coloured section start/stop markers in place.

Unlike a list of sections, this renders the SOURCE continuously and marks where
each section opens and closes.  That makes the things a list hides visible:
text no section covers, sections that overlap, and boundaries that fall in the
middle of a sentence.

Sections are located by searching for their own text rather than by their
stored byte ranges, because those ranges are in two coordinate systems
(measured 2026-08-18: 238 resolve as bytes, 241 only after a character
conversion).  Searching cannot land in the wrong place; it can only fail to
find, and a section that cannot be found in its own source is reported.

    .venv\\Scripts\\python.exe tools/segmentation_overlay.py --doc form_1040_2025
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from workbench import generated_review as gr  # noqa: E402

PALETTE = [
    "#cfe8ff", "#ffe0b3", "#d6f5d6", "#f5d6e8", "#e6d6f5",
    "#fff2b3", "#c9f0ef", "#ffd6cc", "#ddeecc", "#e0e0ff",
]


def _source_text(document_id: str, year: str) -> str:
    """Return the acquired text the pipeline actually segments."""
    pages = ROOT / ".cache" / "raw" / year / f"{document_id}.pages"
    if pages.is_dir():
        return "".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in sorted(pages.glob("*.md"))
        )
    single = ROOT / ".cache" / "raw" / year / f"{document_id}.md"
    if single.is_file():
        return single.read_text(encoding="utf-8", errors="ignore")
    raise FileNotFoundError(f"no acquired text for {document_id}")


def _normalise(text: str) -> tuple[str, list[int]]:
    """Collapse whitespace, keeping a map from each kept char to its source index."""
    out: list[str] = []
    index: list[int] = []
    previous_space = False
    for position, char in enumerate(text):
        if char.isspace():
            if previous_space or not out:
                continue
            out.append(" ")
            index.append(position)
            previous_space = True
        else:
            out.append(char)
            index.append(position)
            previous_space = False
    return "".join(out), index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doc", required=True, help="instruction document id")
    parser.add_argument("--year", default="2025")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    # Instruction spans live on the FORM's draft but quote the instructions doc.
    owner = args.doc
    if owner.startswith("instructions_"):
        owner = owner[len("instructions_"):]
    draft = gr._load_draft(ROOT, args.year, owner)
    spans = gr._span_index(draft.get("candidate_spans"))
    sections = [
        (span_id, span)
        for span_id, span in spans.items()
        if span.get("relationship") != "source"
    ]
    if not sections:
        print(f"no instruction sections on draft {owner}", file=sys.stderr)
        return 1

    document_id = str(sections[0][1].get("document_id") or f"instructions_{owner}")
    source = _source_text(document_id, args.year)
    flat, index = _normalise(source)

    placed: list[tuple[int, int, str, list[str], bool]] = []
    missing = truncated = 0
    for span_id, span in sections:
        needle, _ = _normalise(str(span.get("text") or ""))
        needle = needle.strip()
        if not needle:
            continue
        at = flat.find(needle)
        partial = False
        if at < 0:
            # Big sections often cannot be found whole: the OCR path injects a
            # page footer, a page number and a "# Page N" heading into the
            # middle of a sentence, so the section is not contiguous source
            # text.  Fall back to the longest prefix that IS present, so the
            # start marker still lands and the operator can see the boundary.
            low, high = 0, len(needle)
            while low < high:
                mid = (low + high + 1) // 2
                if flat.find(needle[:mid]) >= 0:
                    low = mid
                else:
                    high = mid - 1
            if low < 40:
                missing += 1
                continue
            at = flat.find(needle[:low])
            needle = needle[:low]
            partial = True
            truncated += 1
        start = index[at]
        end = index[min(at + len(needle) - 1, len(index) - 1)] + 1
        placed.append((start, end, span_id, [str(v) for v in (span.get("owner_lines") or [])], partial))
    placed.sort()

    overlaps = sum(
        1 for i in range(1, len(placed)) if placed[i][0] < placed[i - 1][1]
    )
    covered = sum(end - start for start, end, _, _, _ in placed)

    colour_for: dict[str, str] = {}
    out_parts: list[str] = []
    cursor = 0
    for start, end, span_id, owners, partial in placed:
        if start < cursor:          # overlapping: mark it, do not nest
            start = cursor
            if end <= start:
                continue
        out_parts.append(f'<span class="gap">{html.escape(source[cursor:start])}</span>')
        label = ", ".join(owners[:5]) if owners else "NO LINE"
        key = label
        colour_for.setdefault(key, PALETTE[len(colour_for) % len(PALETTE)])
        colour = colour_for[key] if owners else "#eeeeee"
        number = re.search(r"section_(\d+)", span_id)
        tag = f"{number.group(1) if number else '?'}"
        out_parts.append(
            f'<span class="sec" style="background:{colour}">'
            f'<span class="mark start{" cut" if partial else ""}">&#9654; {html.escape(tag)} &middot; '
            f'{html.escape(label)}</span>'
            f"{html.escape(source[start:end])}"
            f'<span class="mark end">&#9664; end {html.escape(tag)}</span></span>'
        )
        cursor = end
    out_parts.append(f'<span class="gap">{html.escape(source[cursor:])}</span>')

    head = [
        "<style>",
        "body{font:13px/1.6 system-ui,sans-serif;margin:18px;background:#fff}",
        "#doc{white-space:pre-wrap;font:12px/1.7 ui-monospace,monospace}",
        ".gap{color:#b00;background:#fff5f5}",
        ".mark{font:700 10px/1 system-ui,sans-serif;padding:2px 5px;border-radius:3px;"
        "background:#222;color:#fff;margin:0 4px;white-space:nowrap}",
        ".mark.end{background:#666}",
        ".mark.cut{background:#b35c00}",
        ".legend{position:sticky;top:0;background:#fff;padding:8px 0;border-bottom:1px solid #ddd}",
        "</style>",
        '<div class="legend">',
        f"<b>{html.escape(document_id)}</b> &middot; {len(placed)} sections located, "
        f"{missing} not found, {truncated} truncated at a page break, "
        f"{overlaps} overlapping &middot; "
        f"{covered * 100 // max(len(source), 1)}% of the text is inside a section. "
        '<span class="gap">Red text belongs to no section.</span>',
        "</div>",
        '<div id="doc">',
    ]
    out = args.out or ROOT / "output" / f"overlay_{document_id}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(head) + "".join(out_parts) + "</div>", encoding="utf-8")
    print(
        f"{len(placed)} located ({truncated} truncated at a page break), {missing} not found, {overlaps} overlapping, "
        f"{covered * 100 // max(len(source), 1)}% covered"
    )
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
