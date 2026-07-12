"""Small artifact-inspection CLI for the review workbench."""

from __future__ import annotations

import argparse
from pathlib import Path

from workbench.artifacts import load_artifact_bundle


def main(argv: list[str] | None = None) -> int:
    """Inspect the published artifact seam without starting a UI."""
    parser = argparse.ArgumentParser(prog="review-workbench")
    parser.add_argument("--root", default=".", help="workspace root")
    parser.add_argument("--year", default="2025", help="tax year")
    parser.add_argument("command", choices=["inspect"])
    args = parser.parse_args(argv)
    bundle = load_artifact_bundle(Path(args.root), args.year)
    print(f"review workbench artifacts - {bundle.tax_year}")
    print(f"  graph objects: {sum(len(items) for items in bundle.graph.objects_by_kind.values())}")
    print(f"  queue entries: {len(bundle.review_queue.get('entries', []))}")
    print(f"  draft directories: {len(bundle.drafts)}")
    print(f"  source PDFs: {len(bundle.pdfs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
