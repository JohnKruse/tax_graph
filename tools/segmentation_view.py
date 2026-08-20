"""Render a booklet's instruction sections in document order, colour-coded.

A visual sanity check for segmentation.  Each section is shown as a block in
the order it appears in the source, labelled with the form lines it claims to
govern.  Scrolling it answers, in seconds, questions that have taken rounds:
does the sequence of claimed lines run forward?  Does a block claiming line 31
sit between blocks claiming 5 and 6?  Which blocks claim nothing?

Sections are rendered in document order rather than overlaid on the raw source
because the stored byte ranges are in two coordinate systems - measured
2026-08-18, 238 resolve as bytes and 241 only after a character conversion - so
an overlay would silently land in the wrong place.  The sections in order ARE
the document with its boundaries drawn.

    .venv\\Scripts\\python.exe tools/segmentation_view.py --doc form_1040_2025
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


# Distinct, readable hues cycled per claimed line so neighbouring blocks differ.
PALETTE = [
    "#cfe8ff", "#ffe0b3", "#d6f5d6", "#f5d6e8", "#e6d6f5",
    "#fff2b3", "#c9f0ef", "#ffd6cc", "#ddeecc", "#e0e0ff",
]


def _line_key(anchor: str):
    match = re.match(r"^(\d+)([a-z]?)$", str(anchor).lower())
    return (int(match.group(1)), match.group(2)) if match else None


def _section_number(span_id: str) -> int:
    match = re.search(r"section_(\d+)", str(span_id))
    return int(match.group(1)) if match else -1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doc", required=True, help="document id, e.g. form_1040_2025")
    parser.add_argument("--year", default="2025")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--chars", type=int, default=700, help="characters of body text per block")
    args = parser.parse_args()

    draft = gr._load_draft(ROOT, args.year, args.doc)
    spans = gr._span_index(draft.get("candidate_spans"))
    sections = sorted(
        (
            (span_id, span)
            for span_id, span in spans.items()
            if span.get("relationship") != "source"
        ),
        key=lambda item: _section_number(item[0]),
    )
    if not sections:
        print(f"no instruction sections in {args.doc}", file=sys.stderr)
        return 1

    colour_for: dict[str, str] = {}
    body = [
        "<style>",
        "body{font:14px/1.5 system-ui,sans-serif;margin:20px;background:#fafafa}",
        ".sec{border-left:10px solid #888;margin:0 0 6px;padding:8px 12px;border-radius:4px}",
        ".hdr{font-weight:700;font-size:13px;margin-bottom:4px}",
        ".none{background:#f0f0f0;color:#666;border-left-color:#ccc}",
        ".back{background:#fff3cd;border-left-color:#e0a800}",
        "pre{white-space:pre-wrap;margin:4px 0 0;font:12px/1.45 ui-monospace,monospace;color:#333}",
        ".tag{display:inline-block;padding:1px 7px;border-radius:9px;background:#222;color:#fff;"
        "font-size:11px;margin-right:6px}",
        ".warn{background:#c00}",
        "</style>",
        f"<h1>{html.escape(args.doc)} - instruction sections in document order</h1>",
        "<p>Each block is one section. The tag shows the form lines it claims to govern. "
        "<b>Amber blocks run backwards</b> - they claim a line earlier than the block above, "
        "which instructions should never do.</p>",
    ]

    previous_key = None
    backwards = claimed = 0
    for span_id, span in sections:
        owners = [str(value) for value in (span.get("owner_lines") or [])]
        keys = [k for k in (_line_key(o) for o in owners) if k]
        first = min(keys) if keys else None
        css, tag_css = "sec", "tag"
        if not owners:
            css += " none"
            label = "no line"
        else:
            claimed += 1
            label = "line " + ", ".join(owners[:6]) + (" ..." if len(owners) > 6 else "")
            key = str(sorted(owners)[0])
            colour_for.setdefault(key, PALETTE[len(colour_for) % len(PALETTE)])
            # Compare with the section immediately above, not a running
            # maximum: the first version used a max and flagged 145 of 154,
            # which said more about the check than the data.  Broad family
            # sections claiming many lines are skipped - they legitimately
            # restate a range that earlier specific sections already covered.
            broad = len(owners) > 4
            if first and previous_key and not broad and first < previous_key:
                css += " back"
                tag_css += " warn"
                backwards += 1
            if first and not broad:
                previous_key = first
        style = ""
        if owners and "back" not in css:
            style = f' style="background:{colour_for[str(sorted(owners)[0])]}"'
        text = " ".join(str(span.get("text") or "").split())
        body.append(
            f'<div class="{css}"{style}>'
            f'<div class="hdr"><span class="{tag_css}">{html.escape(label)}</span>'
            f'{html.escape(span_id.split("__")[0].rsplit("_", 1)[-1])} '
            f'&middot; {html.escape(str(span.get("locator") or ""))}</div>'
            f"<pre>{html.escape(text[: args.chars])}"
            f'{"..." if len(text) > args.chars else ""}</pre></div>'
        )

    body.insert(
        3,
        f"<p><b>{len(sections)}</b> sections &middot; <b>{claimed}</b> claim at least one line "
        f"&middot; <b>{backwards}</b> run backwards</p>",
    )
    out = args.out or ROOT / "output" / f"segmentation_{args.doc}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(body), encoding="utf-8")
    print(f"{len(sections)} sections, {claimed} claim a line, {backwards} run backwards")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
