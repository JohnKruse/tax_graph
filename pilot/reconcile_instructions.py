"""Build the checked-in M20-S117 instruction reconciliation artifact."""

from __future__ import annotations

import argparse
from pathlib import Path

from tax_graph.acquire.manifest import load_manifest
from tax_graph.extract.cells import build_cell_frame_from_document
from tax_graph.extract.instruction_reconciliation import (
    build_instruction_reconciliation_report,
    write_instruction_reconciliation_report,
)
from tax_graph.extract.inputs import load_document_input
from tax_graph.extract.outline import build_instruction_sections_frame


def build_live_report(root: str | Path, year: str = "2025") -> dict:
    """Load acquired forms and build the deterministic S117 report."""
    root_path = Path(root).resolve()
    manifest = load_manifest(root=root_path)
    documents = []
    for entry in sorted(manifest.documents, key=lambda item: item.document_id):
        if entry.kind not in {"tax_form", "schedule", "source_document"}:
            continue
        if not entry.instructions_document_id:
            continue
        try:
            document = load_document_input(
                entry.document_id,
                year=year,
                root=root_path,
                manifest=manifest,
            )
        except (FileNotFoundError, OSError, ValueError):
            continue
        frame = build_instruction_sections_frame(document)
        instruction_source = next(
            (
                source
                for source in document.related_sources
                if source.relationship == "instructions"
            ),
            None,
        )
        if instruction_source is None:
            continue
        documents.append(
            {
                "document_id": document.document_id,
                "raw_booklet_text": instruction_source.text,
                "frame": frame,
                "cells": build_cell_frame_from_document(document).rows,
            }
        )
    return build_instruction_reconciliation_report(
        documents,
        table_addressed_cells=46,
    )


def main() -> int:
    """Run the report builder from the repository root."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--year", default="2025")
    parser.add_argument(
        "--output",
        default="plans/m20_s116_instruction_reconciliation.yaml",
    )
    args = parser.parse_args()
    report = build_live_report(args.root, args.year)
    write_instruction_reconciliation_report(report, Path(args.root) / args.output)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
