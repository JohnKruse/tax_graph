"""Reject document-specific measured counts embedded in model prompts."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
from typing import Any


_DOCUMENT_RE = re.compile(
    r"\b(?:form|schedule)\s+[0-9]+[a-z]?(?:[- ]?[a-z])?\b",
    re.IGNORECASE,
)
_MEASUREMENT_RE = re.compile(
    r"\b(?:measured|expectation|expected|target|reference\s+answer|none\s+rate|"
    r"coverage|score|count)\b.{0,120}?\b[0-9]+\b",
    re.IGNORECASE,
)


def find_prompt_measured_counts(root: str | Path) -> list[dict[str, Any]]:
    """Return prompt locations that pair a document name with a measured count."""
    root_path = Path(root).resolve()
    prompt_root = root_path / "prompts"
    violations: list[dict[str, Any]] = []
    if not prompt_root.is_dir():
        return violations
    for path in sorted(prompt_root.rglob("*.md")):
        text = path.read_text(encoding="ascii")
        compact = " ".join(text.split())
        for document_match in _DOCUMENT_RE.finditer(compact):
            window_start = max(0, document_match.start() - 40)
            window_end = min(len(compact), document_match.end() + 220)
            window = compact[window_start:window_end]
            measurement = _MEASUREMENT_RE.search(window)
            if measurement is None:
                continue
            violations.append(
                {
                    "path": str(path),
                    "document": document_match.group(0),
                    "excerpt": window,
                }
            )
    return violations


def main(argv: list[str] | None = None) -> int:
    """Check all prompt templates under the repository root."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    violations = find_prompt_measured_counts(args.root)
    for violation in violations:
        print(f"{violation['path']}: {violation['document']}: {violation['excerpt']}")
    if violations:
        print(f"prompt measured-count check failed: {len(violations)} violation(s)")
        return 1
    print("prompt measured-count check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
