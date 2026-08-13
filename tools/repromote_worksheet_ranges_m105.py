"""Rebind promoted worksheet drafts to acquired source ranges for M20-S105."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from tax_graph.acquire.manifest import load_manifest
from tax_graph.config import get_config_value, load_config
from tax_graph.ingest.worksheet_harvest import (
    WorksheetTarget,
    rebind_worksheet_draft_ranges,
)


def main() -> int:
    """Regenerate worksheet citation ranges from acquired source text."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--year", default="2025")
    args = parser.parse_args()
    root = args.root.resolve()
    config = load_config(root=root)
    raw_store = Path(get_config_value(config, "project.paths.raw_store", ".cache/raw"))
    if not raw_store.is_absolute():
        raw_store = root / raw_store
    manifest = load_manifest(root=root)
    for entry in manifest.documents:
        if not entry.is_region:
            continue
        source_id = str(entry.region_of or "")
        source_path = raw_store / str(args.year) / f"{source_id}.txt"
        draft_dir = root / "graph" / str(args.year) / "_drafts" / entry.document_id
        target = WorksheetTarget(
            document_id=entry.document_id,
            title=str(entry.region_title or entry.document_id),
            start_anchor="m20_s105_source_range_rebind",
            source_document_id=source_id,
        )
        rebind_worksheet_draft_ranges(
            draft_dir,
            source_text=source_path.read_text(encoding="ascii"),
            target=target,
        )
        nodes_path = draft_dir / "nodes.yaml"
        nodes = yaml.safe_load(nodes_path.read_text(encoding="ascii")) or []
        for node in nodes:
            node.pop("form_face_text", None)
        nodes_path.write_text(
            yaml.safe_dump(nodes, sort_keys=False, allow_unicode=False),
            encoding="ascii",
            newline="\n",
        )
        print(f"rebound {entry.document_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
