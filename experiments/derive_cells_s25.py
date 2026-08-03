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
import tempfile
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tax_graph.config import get_config_value, load_config
from tax_graph.extract.cells import (
    build_reference_inventory,
    build_cell_frame_from_document,
    derive_cells,
    load_cell_prompt,
    _scoped_graph_nodes,
)
from tax_graph.extract.inputs import load_document_input
from tax_graph.extract.instruction_sections import write_instruction_sections_artifact
from tax_graph.extract.llm_client import build_llm_client
from tax_graph.io.loader import load_graph
from tax_graph.extract.outline import (
    _flatten_outline_nodes,
    build_instruction_sections_frame,
    build_outline_tree,
)


def persist_instruction_frame(
    *,
    root: str | Path,
    year: str,
    document_id: str = "form_1040_2025",
    output_dir: str | Path | None = None,
) -> tuple[Path, Path]:
    """Persist the deterministic instruction frame and its coverage report."""
    root_path = Path(root).resolve()
    destination = _output_destination(root_path, output_dir)
    document = load_document_input(document_id, year=year, root=root_path)
    frame = build_instruction_sections_frame(document, outline=build_outline_tree(document))
    frame = _portable_frame(frame, root_path)
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


def run_real_document(
    *,
    root: str | Path,
    year: str,
    document_id: str,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Derive one real document and persist only its aggregate report."""
    root_path = Path(root).resolve()
    destination = _output_destination(root_path, output_dir)
    config = load_config(root=root_path)
    document = load_document_input(document_id, year=year, root=root_path, config=config)
    outline = build_outline_tree(document)
    outline_nodes = _flatten_outline_nodes(outline.children)
    frame = build_cell_frame_from_document(document)
    client = build_llm_client(config)
    prompt = load_cell_prompt(config, root=root_path)
    reference_inventory = build_reference_inventory(load_graph(year, root_path))
    result = derive_cells(
        frame,
        prompt,
        None,
        client=client,
        model=str(get_config_value(config, "llm.micro_model", "configured-llm")),
        provider=str(get_config_value(config, "llm.provider", "configured-provider")),
        reference_inventory=reference_inventory,
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
            "expression": row.expression,
            "rendered": row.rendered,
            "validation_failures": row.metadata.get("validation_failures", []),
            "validation_warnings": row.metadata.get("validation_warnings", []),
            "dropped_instruction_sections": row.metadata.get("dropped_instruction_sections", []),
            "unresolved_external_nodes": row.metadata.get("unresolved_external_nodes", []),
        }
        for row in result.rows
    ]
    unresolved_external_nodes = [
        {
            "form": document.document_id,
            "line": row["line"],
            **node,
        }
        for row in row_details
        for node in row["unresolved_external_nodes"]
    ]
    report = {
        "document_id": document.document_id,
        "year": str(year),
        "rows": len(result.rows),
        "rows_attempted": result.validation.get("attempted", 0),
        "outline_node_count": len(outline_nodes),
        "line_anchor_count": sum(1 for node in outline_nodes if node.line_anchor),
        "row_status_counts": status_counts,
        "raw_row_status_counts": dict(sorted(raw_status_counts.items())),
        "rows_detail": row_details,
        "validation": result.validation_report,
        "reference_inventory": {
            "total_graph_nodes": len(reference_inventory.get("graph_nodes", [])),
            "scoped_graph_nodes": len(
                _scoped_graph_nodes(reference_inventory, document.document_id)
            ),
        },
        "unresolved_external_node_count": len(unresolved_external_nodes),
        "unresolved_external_nodes": unresolved_external_nodes,
    }
    report_path = destination / f"m20_s26_{document_id}_derive_cells_report.yaml"
    report_path.write_text(
        yaml.safe_dump(report, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
        newline="\n",
    )
    return report


def _output_destination(root: Path, output_dir: str | Path | None) -> Path:
    """Return a writable output directory outside the source repository."""
    if output_dir is None:
        return Path(tempfile.mkdtemp(prefix="tax_graph_m20_s30_"))
    destination = Path(output_dir).resolve()
    try:
        destination.relative_to(root)
    except ValueError:
        destination.mkdir(parents=True, exist_ok=True)
        return destination
    raise ValueError(f"output directory must be outside repository root: {destination}")


def _top_three_counts(values: dict[str, int]) -> dict[str, int]:
    """Return the three most frequent validator findings in stable order."""
    return dict(sorted(values.items(), key=lambda item: (-item[1], item[0]))[:3])


def run_documents(
    *,
    root: str | Path,
    year: str,
    document_ids: list[str],
    output_dir: str | Path | None = None,
    no_provider: bool = False,
) -> list[dict[str, Any]]:
    """Run the harness once per document and report load/provider failures."""
    root_path = Path(root).resolve()
    destination = _output_destination(root_path, output_dir)
    reports: list[dict[str, Any]] = []
    for document_id in document_ids:
        try:
            frame_path, coverage_path = persist_instruction_frame(
                root=root_path,
                year=year,
                document_id=document_id,
                output_dir=destination,
            )
        except Exception as exc:  # noqa: BLE001 - one document must not hide another
            reports.append(
                {
                    "document_id": document_id,
                    "status": "reported",
                    "reason": f"{type(exc).__name__}: {exc}",
                    "rows_attempted": 0,
                    "derived": 0,
                    "repaired": 0,
                    "gapped": 0,
                    "errored": 0,
                }
            )
            continue

        if no_provider:
            reports.append(
                {
                    "document_id": document_id,
                    "status": "prepared",
                    "instruction_frame": str(frame_path),
                    "instruction_coverage": str(coverage_path),
                    "reason": "provider disabled",
                }
            )
            continue

        try:
            report = run_real_document(
                root=root_path,
                year=year,
                document_id=document_id,
                output_dir=destination,
            )
        except Exception as exc:  # noqa: BLE001 - report provider failures per document
            reports.append(
                {
                    "document_id": document_id,
                    "status": "reported",
                    "reason": f"{type(exc).__name__}: {exc}",
                    "rows_attempted": 0,
                    "derived": 0,
                    "repaired": 0,
                    "gapped": 0,
                    "errored": 0,
                }
            )
            continue
        rows_attempted = report["rows_attempted"]
        summary = {
            "document_id": document_id,
            "status": "empty" if rows_attempted == 0 else "complete",
            "rows_attempted": rows_attempted,
            **report["row_status_counts"],
            "outline_node_count": report["outline_node_count"],
            "line_anchor_count": report["line_anchor_count"],
            "reference_inventory": report.get("reference_inventory", {}),
            "unresolved_external_node_count": report.get("unresolved_external_node_count", 0),
            "unresolved_external_nodes": report.get("unresolved_external_nodes", []),
            "validator_failures_by_kind": _top_three_counts(
                report["validation"].get("validator_failures_by_kind", {})
            ),
        }
        if rows_attempted == 0:
            summary["reason"] = "document outline produced no derivation rows"
        reports.append(summary)
    return reports


def main() -> int:
    """Run persistence and, unless disabled, the real provider bench."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--year", default="2025")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--document", action="append", dest="documents")
    parser.add_argument("--no-provider", action="store_true")
    args = parser.parse_args()
    document_ids = args.documents or ["form_1040_2025"]
    reports = run_documents(
        root=args.root,
        year=args.year,
        document_ids=document_ids,
        output_dir=args.output_dir,
        no_provider=args.no_provider,
    )
    print(yaml.safe_dump({"documents": reports}, sort_keys=False, allow_unicode=False).rstrip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
