"""Small artifact-inspection CLI for the review workbench."""

from __future__ import annotations

import argparse
from pathlib import Path

from workbench.artifacts import load_artifact_bundle
from workbench.builder import build_bundle
from workbench.manifest import build_manifest, write_manifest
from workbench.preflight import PreflightError, run_preflight
from workbench.verdicts import emit_verdict


def main(argv: list[str] | None = None) -> int:
    """Inspect the published artifact seam without starting a UI."""
    parser = argparse.ArgumentParser(prog="review-workbench")
    parser.add_argument("--root", default=".", help="workspace root")
    parser.add_argument("--year", default="2025", help="tax year")
    parser.add_argument("command", choices=["inspect", "build", "manifest", "preflight", "serve", "verdict"])
    parser.add_argument("--output-dir", default=None, help="static bundle output directory for build")
    parser.add_argument("--db", default=None, help="compiled SQLite artifact")
    parser.add_argument("--pdf-dir", default=None, help="source PDF directory")
    parser.add_argument("--port", type=int, default=0, help="loopback server port; 0 chooses an available port")
    parser.add_argument("--queue-id", default=None, help="deferred-review queue id for verdict")
    parser.add_argument("--verdict-id", default=None, help="append-only verdict id")
    parser.add_argument("--reviewer-id", default=None, help="human reviewer id")
    parser.add_argument("--human-minutes", type=float, default=None, help="minutes spent on review")
    parser.add_argument("--verdict", choices=["confirmed", "questioned", "rejected", "pipeline_defect", "source_pathology"], default=None)
    parser.add_argument("--reason", default=None, help="reason for a non-confirmed verdict")
    parser.add_argument("--comment", default=None, help="reviewer observation for a questioned or rejected verdict")
    parser.add_argument("--reviewed-at", default=None, help="ISO-8601 review timestamp")
    args = parser.parse_args(argv)
    if args.command == "build":
        path = build_bundle(
            Path(args.root),
            args.year,
            output_dir=args.output_dir,
            db_path=args.db,
            pdf_dir=args.pdf_dir,
        )
        print(path)
        return 0
    if args.command == "manifest":
        output_dir = (
            Path(args.output_dir)
            if args.output_dir is not None
            else Path(args.root) / ".workbench_state" / str(args.year)
        )
        result = write_manifest(
            Path(args.root),
            args.year,
            output_path=output_dir / "review_manifest.json",
            db_path=args.db,
            pdf_dir=args.pdf_dir,
        )
        print(result.path)
        return 0
    if args.command == "verdict":
        required = {
            "--queue-id": args.queue_id,
            "--verdict-id": args.verdict_id,
            "--reviewer-id": args.reviewer_id,
            "--human-minutes": args.human_minutes,
            "--verdict": args.verdict,
        }
        missing = [name for name, value in required.items() if value is None]
        if missing:
            parser.error("verdict requires " + ", ".join(missing))
        manifest = build_manifest(Path(args.root), args.year, db_path=args.db, pdf_dir=args.pdf_dir)
        result = emit_verdict(
            root=Path(args.root), year=args.year, queue_id=args.queue_id,
            manifest_hash=manifest["manifest_hash"],
            verdict_id=args.verdict_id, reviewer_id=args.reviewer_id,
            human_minutes=args.human_minutes, verdict=args.verdict,
            reviewed_at=args.reviewed_at, reason=args.reason, comment=args.comment,
        )
        print(result.path)
        return 0
    if args.command == "preflight":
        try:
            report = run_preflight(Path(args.root), args.year, db_path=args.db, pdf_dir=args.pdf_dir)
        except PreflightError as exc:
            print(str(exc))
            return 1
        print(f"review preflight passed - {args.year}")
        print(f"  derived manifest entries: {report['entries']}")
        print(f"  derived manifest units: {report['units']}")
        derived = report["derived"]
        print(f"  derived cells: {derived['denominator']}")
        print(
            "  derived states: "
            + ", ".join(f"{key}={value}" for key, value in sorted(derived["states"].items()))
        )
        print(f"  derived blast radius: {derived['blast_radius']['invalidated']}")
        for dimension in (
            "by_kind", "by_document", "by_object", "by_geometry",
            "by_display_name_provenance", "legacy_mined_by_document",
        ):
            values = ", ".join(f"{key}={value}" for key, value in report[dimension].items())
            print(f"  {dimension}: {values}")
        return 0
    if args.command == "serve":
        from workbench.server import serve

        serve(Path(args.root), args.year, port=args.port)
        return 0
    bundle = load_artifact_bundle(Path(args.root), args.year)
    print(f"review workbench artifacts - {bundle.tax_year}")
    print(f"  graph objects: {sum(len(items) for items in bundle.graph.objects_by_kind.values())}")
    print("  review entries: derived from physical form cells (run preflight for counts)")
    print(f"  draft directories: {len(bundle.drafts)}")
    print(f"  source PDFs: {len(bundle.pdfs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
