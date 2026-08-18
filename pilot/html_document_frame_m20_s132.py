"""Apply the three-way ownership rule to the accepted M20-S130 HTML frame.

This provider-free pilot changes ownership only.  It reuses the accepted S130
heading vocabulary and byte tiling, then distinguishes a foreign naming
ancestor from the absence of a naming ancestor.  A document mention inside a
line heading is not itself an ownership boundary; worked examples beneath a
Schedule D line therefore fall back to Schedule D while worksheet headings
outside the booklet remain rejected.
"""

from __future__ import annotations

from dataclasses import replace
import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

from pilot import html_document_frame_m20_s130 as s130
from pilot.html_section_frame_m20_s128 import (
    _OwnerResolution,
    _default_owner,
    _document_aliases,
    _line_tokens,
    _resolve_owner,
)
from pilot.model_instruction_segmenter import manifest_owner_document_ids
from tax_graph.acquire.manifest import load_manifest


ROOT = Path(__file__).resolve().parents[1]
YEAR = "2025"
BOOKLET_IDS = s130.BOOKLET_IDS


def parse_html_document_frame(
    html_text: str,
    *,
    source_document_id: str,
    root: str | Path = ROOT,
    owner_document_ids: Iterable[str] | None = None,
    worksheet_document_ids: Iterable[str] | None = None,
    all_manifest_document_ids: Iterable[str] | None = None,
) -> s130.s129.HtmlDocumentFrame:
    """Reassign S130 sections with the three-way ownership rule."""
    base = s130.parse_html_document_frame(
        html_text,
        source_document_id=source_document_id,
        root=root,
        owner_document_ids=owner_document_ids,
        worksheet_document_ids=worksheet_document_ids,
        all_manifest_document_ids=all_manifest_document_ids,
    )
    root_path = Path(root).resolve()
    owners = frozenset(
        str(value).strip()
        for value in (
            owner_document_ids
            if owner_document_ids is not None
            else manifest_owner_document_ids(root_path, source_document_id=source_document_id)
        )
        if str(value).strip()
    )
    if all_manifest_document_ids is None:
        manifest = load_manifest(root=root_path)
        all_ids = frozenset(str(entry.document_id).strip() for entry in manifest.documents)
    else:
        all_ids = frozenset(
            str(value).strip() for value in all_manifest_document_ids if str(value).strip()
        )
    aliases = _document_aliases(root_path, owners | all_ids)

    sections = tuple(
        _reassign_section(
            section,
            source_document_id=source_document_id,
            owner_document_ids=owners,
            all_manifest_document_ids=all_ids,
            aliases=aliases,
        )
        for section in base.sections
    )
    rejected = tuple(
        s130.s129.HtmlSectionRejection(
            heading=section.heading,
            reason="foreign_owner_rejected",
            foreign_document_id=_foreign_id(
                section.ancestor_chain,
                source_document_id=source_document_id,
                owner_document_ids=owners,
                all_manifest_document_ids=all_ids,
                aliases=aliases,
            ),
            foreign_heading=_foreign_heading(
                section.ancestor_chain,
                source_document_id=source_document_id,
                owner_document_ids=owners,
                all_manifest_document_ids=all_ids,
                aliases=aliases,
            ),
            ancestor_chain=section.ancestor_chain,
            anchor_id=section.anchor_id,
            start_offset=section.start_offset,
            end_offset=section.end_offset,
        )
        for section in sections
        if section.rejected
    )
    invariants = dict(base.structural_invariants)
    invariants["rejected_section_count"] = len(rejected)
    return replace(base, sections=sections, rejected_sections=rejected, structural_invariants=invariants)


def measure_corpus(root: str | Path = ROOT, *, year: str = YEAR) -> dict[str, Any]:
    """Report ownership movement before and after S132 across all booklets."""
    root_path = Path(root).resolve()
    before: dict[str, s130.s129.HtmlDocumentFrame] = {}
    after: dict[str, s130.s129.HtmlDocumentFrame] = {}
    for source_document_id in BOOKLET_IDS:
        source_path = root_path / ".cache" / "raw" / year / f"{source_document_id}.html"
        html_text = source_path.read_text(encoding="utf-8")
        before[source_document_id] = s130.parse_html_document_frame(
            html_text,
            source_document_id=source_document_id,
            root=root_path,
        )
        after[source_document_id] = parse_html_document_frame(
            html_text,
            source_document_id=source_document_id,
            root=root_path,
        )

    before_documents = s130._line_anchored_report(root_path, before)
    after_documents = s130._line_anchored_report(root_path, after)
    documents: dict[str, Any] = {}
    for document_id in sorted(after_documents):
        old = before_documents[document_id]
        new = after_documents[document_id]
        documents[document_id] = {
            "booklet_id": new["booklet_id"],
            "cells": new["cells"],
            "line_anchored_before": old["line_anchored"],
            "line_anchored": new["line_anchored"],
            "line_anchored_cell_ids": new["line_anchored_cell_ids"],
        }

    return {
        "round": "M20-S132",
        "rule": {
            "case_1": "nearest naming ancestor in booklet vocabulary owns the section",
            "case_2": "nearest naming ancestor outside vocabulary rejects the section",
            "case_3": "no naming ancestor falls back to the booklet form",
            "line_heading_mentions": "document mentions inside line headings do not create ownership boundaries",
        },
        "booklets": {
            source_document_id: {
                "section_count": len(after[source_document_id].sections),
                "rejected_before": len(before[source_document_id].rejected_sections),
                "rejected_after": len(after[source_document_id].rejected_sections),
                "structural_invariants": dict(after[source_document_id].structural_invariants),
            }
            for source_document_id in sorted(after)
        },
        "documents": documents,
        "summary": {
            "booklet_count": len(after),
            "structural_invariants_hold": all(
                all(
                    frame.structural_invariants[key] is True
                    for key in s130._REQUIRED_FRAME_INVARIANTS
                )
                for frame in after.values()
            ),
            "total_rejected_before": sum(len(frame.rejected_sections) for frame in before.values()),
            "total_rejected_after": sum(len(frame.rejected_sections) for frame in after.values()),
        },
    }


def _reassign_section(
    section: s130.s129.HtmlDocumentSection,
    *,
    source_document_id: str,
    owner_document_ids: frozenset[str],
    all_manifest_document_ids: frozenset[str],
    aliases: dict[str, tuple[str, ...]],
) -> s130.s129.HtmlDocumentSection:
    """Return one section with ownership resolved under all three cases."""
    owner = _resolve_three_way(
        section.ancestor_chain,
        source_document_id=source_document_id,
        owner_document_ids=owner_document_ids,
        all_manifest_document_ids=all_manifest_document_ids,
        aliases=aliases,
    )
    rejected = bool(owner.foreign_heading)
    return replace(
        section,
        owner_document_id=None if rejected else owner.document_id,
        owner_source="rejected" if rejected else owner.source,
        rejected=rejected,
    )


def _resolve_three_way(
    ancestor_chain: Sequence[str],
    *,
    source_document_id: str,
    owner_document_ids: frozenset[str],
    all_manifest_document_ids: frozenset[str],
    aliases: dict[str, tuple[str, ...]],
) -> _OwnerResolution:
    """Resolve an owner while ignoring document mentions in line headings."""
    for title in reversed(tuple(ancestor_chain)):
        if _line_tokens(title):
            continue
        resolution = _resolve_owner(
            (title,),
            source_document_id=source_document_id,
            owner_document_ids=owner_document_ids,
            all_manifest_document_ids=all_manifest_document_ids,
            aliases=aliases,
        )
        if resolution.source == "ancestor":
            return resolution
        if resolution.foreign_heading:
            return resolution
    return _OwnerResolution(_default_owner(source_document_id), "default_form")


def _foreign_heading(
    ancestor_chain: Sequence[str],
    *,
    source_document_id: str,
    owner_document_ids: frozenset[str],
    all_manifest_document_ids: frozenset[str],
    aliases: dict[str, tuple[str, ...]],
) -> str:
    return _resolve_three_way(
        ancestor_chain,
        source_document_id=source_document_id,
        owner_document_ids=owner_document_ids,
        all_manifest_document_ids=all_manifest_document_ids,
        aliases=aliases,
    ).foreign_heading


def _foreign_id(
    ancestor_chain: Sequence[str],
    *,
    source_document_id: str,
    owner_document_ids: frozenset[str],
    all_manifest_document_ids: frozenset[str],
    aliases: dict[str, tuple[str, ...]],
) -> str | None:
    return _resolve_three_way(
        ancestor_chain,
        source_document_id=source_document_id,
        owner_document_ids=owner_document_ids,
        all_manifest_document_ids=all_manifest_document_ids,
        aliases=aliases,
    ).foreign_document_id


def main(argv: Sequence[str] | None = None) -> int:
    """Print the S132 ownership movement report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--year", default=YEAR)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    report = measure_corpus(args.root, year=args.year)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
            encoding="ascii",
            newline="\n",
        )
    print(
        f"M20-S132: {report['summary']['booklet_count']} booklets; "
        f"rejected {report['summary']['total_rejected_before']} -> "
        f"{report['summary']['total_rejected_after']}"
    )
    for source_document_id, item in report["booklets"].items():
        print(
            f"{source_document_id}: rejected={item['rejected_before']} -> "
            f"{item['rejected_after']}"
        )
    for document_id, item in report["documents"].items():
        print(
            f"{document_id}: line_anchored={item['line_anchored_before']} -> "
            f"{item['line_anchored']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
