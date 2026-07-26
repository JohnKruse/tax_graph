#!/usr/bin/env python3
"""Promote the deterministic M19-S3a structured-form concept inventory."""

from __future__ import annotations

import argparse
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tax_graph.output.concepts import STRUCTURED_DOCUMENTS, promote_structured_concepts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("document_ids", nargs="*", default=list(STRUCTURED_DOCUMENTS))
    args = parser.parse_args()
    summary = promote_structured_concepts(args.root.resolve(), args.year, args.document_ids)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
