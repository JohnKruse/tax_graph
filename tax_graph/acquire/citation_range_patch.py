"""Build a non-destructive source-range proposal for legacy citations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tax_graph.acquire.citation_check import _contiguous_quote_ranges
from tax_graph.acquire.citation_check import _split_table_separator_ranges
from tax_graph.acquire.citation_check import check_citation_integrity
from tax_graph.acquire.source_ranges import load_source_text
from tax_graph.io.loader import load_graph


SCHEMA_VERSION = "m20-s136-citation-range-patch-v1"


def build_citation_range_patch(
    *,
    year: str | int,
    root: str | Path,
    raw_store: str | Path,
) -> dict[str, Any]:
    """Build proposed ranges without changing any graph or extension artifact."""
    project_root = Path(root).resolve()
    text_dir = Path(raw_store) / str(year)
    graph = load_graph(year, project_root)
    texts: dict[str, str] = {}
    proposals: list[dict[str, Any]] = []
    html_only: list[dict[str, str]] = []
    considered = [
        item
        for item in graph.items("citations")
        if item.get("kind") != "computed_table" and not item.get("ranges")
    ]

    for citation in considered:
        source_document_id = str(
            citation.get("source_document_id") or citation["document_id"]
        )
        source_text = texts.get(source_document_id)
        if source_text is None:
            source_text = load_source_text(source_document_id, text_dir=text_dir)
            texts[source_document_id] = source_text
        quote = str(citation.get("quoted_text") or "")
        exact_start = source_text.find(quote)
        method = "txt_exact"
        if exact_start >= 0:
            ranges = (
                {"start": exact_start, "end": exact_start + len(quote)},
            )
        else:
            aligned = _contiguous_quote_ranges(source_text, quote)
            if aligned is None:
                ranges = None
            else:
                ranges = _split_table_separator_ranges(source_text, aligned)
                method = "txt_format_normalized"
                if not _format_only_gaps(source_text, ranges):
                    ranges = None

        if ranges is None:
            html_only.append(
                {
                    "citation_id": str(citation["citation_id"]),
                    "document_id": str(citation["document_id"]),
                    "source_document_id": source_document_id,
                    "reason": "quoted text is locatable only in acquired HTML",
                }
            )
            continue

        candidate = dict(citation)
        candidate["ranges"] = [dict(item) for item in ranges]
        verification = check_citation_integrity([candidate], text_dir=text_dir)
        if verification.mismatches:
            html_only.append(
                {
                    "citation_id": str(citation["citation_id"]),
                    "document_id": str(citation["document_id"]),
                    "source_document_id": source_document_id,
                    "reason": "quoted text is locatable only in acquired HTML",
                }
            )
            continue
        proposals.append(
            {
                "citation_id": str(citation["citation_id"]),
                "document_id": str(citation["document_id"]),
                "source_document_id": source_document_id,
                "method": method,
                "ranges": [dict(item) for item in ranges],
            }
        )

    proposals.sort(key=lambda item: item["citation_id"])
    html_only.sort(key=lambda item: item["citation_id"])
    computed_count = sum(
        item.get("kind") == "computed_table" for item in graph.items("citations")
    )
    ranged_before_count = sum(
        item.get("kind") != "computed_table" and bool(item.get("ranges"))
        for item in graph.items("citations")
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "year": str(year),
        "source": "acquired_txt",
        "apply": "not applied; graph and extension citation artifacts are protected",
        "unverifiable_count": len(considered),
        "proposed_range_count": len(proposals),
        "html_only_count": len(html_only),
        "unverifiable_after_apply": len(html_only),
        "accounting": {
            "ranged_before": ranged_before_count,
            "unverifiable": len(considered),
            "computed_table": computed_count,
            "total": len(graph.items("citations")),
        },
        "proposed_ranges": proposals,
        "html_only": html_only,
    }


def apply_citation_range_patch(
    citations: list[dict[str, Any]],
    patch: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return an in-memory graph view with a proposal applied."""
    by_id = {
        str(item["citation_id"]): item["ranges"]
        for item in patch.get("proposed_ranges", ())
    }
    result: list[dict[str, Any]] = []
    for citation in citations:
        copied = dict(citation)
        ranges = by_id.get(str(citation.get("citation_id")))
        if ranges is not None:
            copied["ranges"] = [dict(item) for item in ranges]
        result.append(copied)
    return result


def write_citation_range_patch(patch: dict[str, Any], output: str | Path) -> Path:
    """Write the generated proposal as an ASCII JSON artifact."""
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(patch, ensure_ascii=True, indent=2) + "\n",
        encoding="ascii",
        newline="\n",
    )
    return output_path


def main(argv: list[str] | None = None) -> int:
    """Generate the M20-S136 proposal from the local acquired sources."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", default="2025")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--raw-store", type=Path, default=None)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("plans/m20_s136_citation_ranges.json"),
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    raw_store = args.raw_store or root / ".cache" / "raw"
    patch = build_citation_range_patch(
        year=args.year,
        root=root,
        raw_store=raw_store,
    )
    output = write_citation_range_patch(patch, args.output)
    print(
        f"wrote {output}: {patch['proposed_range_count']} proposed, "
        f"{patch['html_only_count']} HTML-only"
    )
    return 0


def _format_only_gaps(
    source_text: str,
    ranges: tuple[dict[str, int], ...],
) -> bool:
    """Accept only whitespace, table, or markdown separators between ranges."""
    for preceding, following in zip(ranges, ranges[1:]):
        gap = source_text[int(preceding["end"]) : int(following["start"])]
        if gap.strip("*_| \t\r\n"):
            return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
