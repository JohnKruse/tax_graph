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
            source_text = load_source_text(
                source_document_id,
                text_dir=text_dir,
                prefer_html=False,
            )
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


LF = chr(10)
CRLF = chr(13) + LF

CITATION_ARTIFACT_GLOBS = ("graph/{year}/citations/*.yaml",)
EXTENSION_ARTIFACT_GLOBS = ("graph_ext/{year}/*/citations.yaml",)


def apply_citation_range_patch_to_files(
    patch: dict[str, Any],
    *,
    root: str | Path,
    year: str | int | None = None,
) -> dict[str, Any]:
    """Write the proposed ranges into the artifacts that hold each citation.

    The edit is textual and additive: a ``ranges:`` block is appended to the
    record that already carries the citation, and nothing else in the file is
    rewritten.  A full YAML round trip would reflow every folded ``quoted_text``
    and bury the change in noise, which is the opposite of what a protected-set
    write needs to look like in review.  A record that already carries ranges is
    an error, not a silent overwrite.

    Citations held by a ``graph_ext/`` overlay are DEFERRED, never written.  The
    overlay is content-hash gated and stamped by the accept path, and it is
    gitignored, so a range written there would both break the gate and be
    invisible in review.  They are returned under ``deferred`` for the round
    that retires the overlay.
    """
    project_root = Path(root).resolve()
    year = str(year or patch.get("year") or "")
    proposals = {
        str(item["citation_id"]): item["ranges"]
        for item in patch.get("proposed_ranges", ())
    }
    files = [
        path
        for pattern in CITATION_ARTIFACT_GLOBS
        for path in sorted(project_root.glob(pattern.format(year=year)))
    ]
    written: dict[str, int] = {}
    applied: set[str] = set()
    for path in files:
        raw = path.read_bytes().decode("utf-8")
        newline = CRLF if CRLF in raw else LF
        lines = raw.replace(CRLF, LF).split(LF)
        bounds = _record_bounds(lines)
        edited = False
        for citation_id, start, end in reversed(bounds):
            ranges = proposals.get(citation_id)
            if ranges is None:
                continue
            if any(line.startswith("  ranges:") for line in lines[start:end]):
                raise ValueError(
                    f"{citation_id} in {path.name} already carries ranges"
                )
            stop = end
            while stop > start and not lines[stop - 1].strip():
                stop -= 1
            lines[stop:stop] = _range_lines(ranges)
            applied.add(citation_id)
            written[str(path.relative_to(project_root))] = (
                written.get(str(path.relative_to(project_root)), 0) + 1
            )
            edited = True
        if edited:
            path.write_bytes(newline.join(lines).encode("utf-8"))
    unplaced = set(proposals) - applied
    deferred = sorted(
        citation_id
        for citation_id in unplaced
        if any(
            f"- citation_id: {citation_id}" in path.read_text(encoding="utf-8")
            for pattern in EXTENSION_ARTIFACT_GLOBS
            for path in project_root.glob(pattern.format(year=year))
        )
    )
    missing = sorted(unplaced - set(deferred))
    if missing:
        raise ValueError(f"no citation artifact holds: {', '.join(missing)}")
    return {
        "files": written,
        "citations_written": len(applied),
        "deferred": deferred,
        "deferred_reason": "held by a content-hash gated graph_ext overlay",
    }


def _record_bounds(lines: list[str]) -> list[tuple[str, int, int]]:
    """Return ``(citation_id, start, end)`` for each top-level citation record."""
    starts = [
        (index, line[len("- citation_id: "):].strip())
        for index, line in enumerate(lines)
        if line.startswith("- citation_id: ")
    ]
    return [
        (
            citation_id,
            index,
            starts[position + 1][0] if position + 1 < len(starts) else len(lines),
        )
        for position, (index, citation_id) in enumerate(starts)
    ]


def _range_lines(ranges: list[dict[str, Any]]) -> list[str]:
    """Render a ``ranges`` block in the shape the shipped artifacts already use."""
    rendered = ["  ranges:"]
    for item in ranges:
        rendered.append(f"  - start: {int(item['start'])}")
        rendered.append(f"    end: {int(item['end'])}")
    return rendered


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
    parser.add_argument(
        "--write",
        action="store_true",
        help="apply the proposal to the citation artifacts (John, 2026-08-19)",
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
    if args.write:
        result = apply_citation_range_patch_to_files(
            patch,
            root=root,
            year=args.year,
        )
        for path, count in sorted(result["files"].items()):
            print(f"  {path}: {count} citations ranged")
        print(f"applied {result['citations_written']} ranges")
        if result["deferred"]:
            print(
                f"deferred {len(result['deferred'])}: {result['deferred_reason']}"
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
