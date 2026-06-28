#!/usr/bin/env python3
"""Validate the authored graph YAML for a tax year.

Usage:  python tools/validate_graph.py [tax_year]   (default 2025)
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tax_graph.validate.graph_validator import validate_graph  # noqa: E402


def main(year: str = "2025") -> int:
    """Run graph validation and print the human-readable report."""
    try:
        result = validate_graph(year, root=ROOT)
    except FileNotFoundError:
        print(f"no graph dir for {year}")
        return 1
    print(result.format_report())
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "2025"))
