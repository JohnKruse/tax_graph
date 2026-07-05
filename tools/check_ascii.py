#!/usr/bin/env python3
"""Fail if authored text files contain non-ASCII characters.

Operational/planning/docs/data files must be ASCII-only so PowerShell (cp1252),
patch/diff tooling, and agent handoffs stay reliable. Wire this into CI.

Usage:  python tools/check_ascii.py
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIRS = ["plans", "docs", "config", "schemas", "graph", "examples", "oracles", "tests", "tax_graph"]
EXTS = {".md", ".yaml", ".yml", ".json", ".txt", ".py", ".toml"}
SKIP = {"__pycache__", ".pytest_cache"}


def main() -> int:
    bad = []
    for d in DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in EXTS:
                continue
            if any(part in SKIP for part in p.parts):
                continue
            for lineno, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                for col, ch in enumerate(line, 1):
                    if ord(ch) > 127:
                        bad.append(f"{p.relative_to(ROOT)}:{lineno}:{col}  U+{ord(ch):04X}")
                        break
    if bad:
        print("Non-ASCII found. Use ASCII only: '-' not em dashes, '->' not arrows,")
        print("'Section' not the section sign, straight quotes, plain-ASCII diagrams.")
        for b in bad:
            print("  " + b)
        return 1
    print("ASCII check OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
