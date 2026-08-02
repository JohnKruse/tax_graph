"""Run the M20-S26 cell frame and property-validator bench.

The pure derivation function remains in ``tax_graph.extract.cells``.  This
caller is the reproducible boundary that loads acquired inputs, persists the
typed instruction frame and coverage report, and optionally calls the
configured provider for the real 1040.  It never writes drafts or graph state.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
from pathlib import Path
import sys
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tax_graph.config import get_config_value, load_config
from tax_graph.extract.cells import (
    build_cell_frame_from_document,
    derive_cells,
    load_cell_prompt,
)
from tax_graph.extract.inputs import load_document_input
from tax_graph.extract.instruction_sections import write_instruction_sections_artifact
from tax_graph.extract.llm_client import build_llm_client
from tax_graph.extract.outline import build_instruction_sections_frame, build_outline_tree


def persist_instruction_frame(
    *,
    root: str | Path,
    year: str,
    document_id: str = "form_1040_2025",
    output_dir: str | Path | None = None,
) -> tuple[Path, Path]:
    """Persist the deterministic instruction frame and its coverage report."""
    root_path = Path(root).resolve()
    document = load_document_input(document_id, year=year, root=root_path)
    frame = build_instruction_sections_frame(document, outline=build_outline_tree(document))
    frame = _portable_frame(frame, root_path)
    destination = Path(output_dir) if output_dir is not None else root_path / "output"
    destination.mkdir(parents=True, exist_ok=True)
    frame_path = write_instruction_sections_artifact(
        frame,
        destination / f"m20_s26_{document_id}_instruction_sections.yaml",
    )
    coverage_path = destination / f"m20_s26_{document_id}_instruction_sections_coverage.yaml"
    coverage_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": frame.schema_version,
                "year": frame.year,
                "source_document_id": frame.source_document_id,
                "section_count": len(frame.sections),
                "coverage": frame.coverage,
            },
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="utf-8",
        newline="\n",
    )
    return frame_path, coverage_path


def _portable_frame(frame: Any, root: Path) -> Any:
    """Replace machine-specific source paths with repository-relative paths."""
    def relative(value: str | None) -> str | None:
        if value is None:
            return None
        path = Path(value)
        try:
            return path.resolve().relative_to(root).as_posix()
        except ValueError:
            return str(value).replace("\\", "/")

    sections = tuple(
        replace(section, locator=replace(section.locator, source_path=relative(section.locator.source_path)))
        for section in frame.sections
    )
    return replace(frame, source_path=relative(frame.source_path), sections=sections)


def run_real_1040(
    *,
    root: str | Path,
    year: str,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Derive the real 1040 rows and persist only an aggregate report."""
    root_path = Path(root).resolve()
    config = load_config(root=root_path)
    document = load_document_input("form_1040_2025", year=year, root=root_path, config=config)
    frame = build_cell_frame_from_document(document)
    client = build_llm_client(config)
    prompt = load_cell_prompt(config, root=root_path)
    result = derive_cells(
        frame,
        prompt,
        None,
        client=client,
        model=str(get_config_value(config, "llm.micro_model", "configured-llm")),
        provider=str(get_config_value(config, "llm.provider", "configured-provider")),
    )
    raw_status_counts = Counter(row.status for row in result.rows)
    status_counts = {
        "derived": raw_status_counts.get("derived", 0),
        "repaired": raw_status_counts.get("repaired", 0),
        "gapped": raw_status_counts.get("gapped", 0),
        "errored": raw_status_counts.get("error", 0) + raw_status_counts.get("errored", 0),
    }
    row_details = [
        {
            "line": row.line,
            "label_before": row.metadata.get("label_before", row.label),
            "label_after": row.label,
            "form_face_before": row.metadata.get("form_face_before", row.form_face_text),
            "form_face_after": row.form_face_text,
            "status": row.status,
            "error": row.error,
            "validation_failures": row.metadata.get("validation_failures", []),
            "validation_warnings": row.metadata.get("validation_warnings", []),
            "dropped_instruction_sections": row.metadata.get("dropped_instruction_sections", []),
        }
        for row in result.rows
    ]
    report = {
        "document_id": document.document_id,
        "year": str(year),
        "rows": len(result.rows),
        "row_status_counts": status_counts,
        "raw_row_status_counts": dict(sorted(raw_status_counts.items())),
        "rows_detail": row_details,
        "validation": result.validation_report,
    }
    destination = Path(output_dir) if output_dir is not None else root_path / "output"
    destination.mkdir(parents=True, exist_ok=True)
    report_path = destination / "m20_s26_form_1040_2025_derive_cells_report.yaml"
    report_path.write_text(
        yaml.safe_dump(report, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
        newline="\n",
    )
    return report


def main() -> int:
    """Run persistence and, unless disabled, the real provider bench."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--year", default="2025")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--no-provider", action="store_true")
    args = parser.parse_args()
    frame_path, coverage_path = persist_instruction_frame(
        root=args.root,
        year=args.year,
        output_dir=args.output_dir,
    )
    print(f"instruction_frame={frame_path}")
    print(f"instruction_coverage={coverage_path}")
    if args.no_provider:
        return 0
    report = run_real_1040(root=args.root, year=args.year, output_dir=args.output_dir)
    print(yaml.safe_dump(report, sort_keys=False, allow_unicode=False).rstrip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
