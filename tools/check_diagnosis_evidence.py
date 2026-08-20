"""Fail when a spec or queued item names a cause without showing the artifact.

AGENTS.md already carries this rule twice, in words, and it has been broken
anyway - most recently on 2026-08-20, in a queued item that quoted the rule.
Prose reminders depend on the writer classifying their own activity correctly,
which is exactly what fails when they are moving fast on something else.  This
check does not care how the writer classified it.

The rule enforced here is deliberately narrow, because a noisy checker gets
ignored and that is worse than no checker.  Only Current round and Queued are
scanned, only units that name a specific failing cell are required to show
anything, and any pasted record or explain-cell reference satisfies it.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


DEFAULT_TARGET = Path("plans/AGENT_HANDOFF.md")

SCANNED_SECTIONS = ("## Current round", "## Queued")

# A cause claim can be phrased infinitely many ways.  A phrase list was tried
# first and FAILED its own regression case: the 2026-08-20 queued item read "THE
# FORM FACE NAMES THE SOURCE AND THE PIPELINE CANNOT FIND IT", which asserts a
# cause without using any stock phrase.  So the trigger is inverted.  Instead of
# hunting for cause language, this requires evidence from any unit that is ABOUT
# a specific failing cell - which is what a diagnosis always is.
DEFECT_SUBJECTS = (
    "review_gap",
    "target_cell_id",
    "unresolved_source_line",
    "operand_not_printed",
    "operand_document_not_found",
    "quote_not_verbatim",
    "subtract_direction",
    "ambiguous_parent_source_line",
)

LINE_SUBJECT = re.compile(r"line\s+[0-9]+[a-z]?", re.IGNORECASE)

# Any one of these in the same unit counts as showing the artifact.
EVIDENCE_MARKERS = (
    "explain-cell",
    "quoted verbatim",
)


def _sections(lines: list[str]) -> list[tuple[str, int, list[str]]]:
    """Split the document into (heading, first_line_number, body) triples."""
    out: list[tuple[str, int, list[str]]] = []
    heading = ""
    start = 0
    body: list[str] = []
    for number, line in enumerate(lines, start=1):
        if line.startswith("## "):
            if heading:
                out.append((heading, start, body))
            heading, start, body = line.strip(), number, []
            continue
        body.append(line)
    if heading:
        out.append((heading, start, body))
    return out


def _has_excerpt(body: list[str]) -> bool:
    """Return whether the section shows a real artifact rather than describing one."""
    for line in body:
        if line.startswith("    ") and line.strip():
            return True  # indented block: a pasted record
        if line.lstrip().startswith("```"):
            return True
        lowered = line.lower()
        if any(marker in lowered for marker in EVIDENCE_MARKERS):
            return True
    return False


def _units(heading: str, start: int, body: list[str]) -> list[tuple[int, list[str]]]:
    """Split a section into the units that must each stand on their own.

    Queued holds many independent items, so one item's excerpt must not excuse
    the next one's absence.  Current round is a single spec and is one unit.
    """
    if not heading.startswith("## Queued"):
        return [(start, body)]
    units: list[tuple[int, list[str]]] = []
    current: list[str] = []
    first = start
    for offset, line in enumerate(body):
        if line.startswith("- "):
            if current:
                units.append((first, current))
            first, current = start + offset + 1, [line]
        elif current:
            current.append(line)
    if current:
        units.append((first, current))
    return units


def _is_about_a_defect(text: str) -> bool:
    lowered = text.lower()
    if any(subject in lowered for subject in DEFECT_SUBJECTS):
        return True
    return bool(LINE_SUBJECT.search(text))


def check(path: Path) -> list[str]:
    """Return one complaint per unit that discusses a failing cell and shows nothing."""
    if not path.exists():
        return [f"{path}: not found"]
    lines = path.read_text(encoding="utf-8").splitlines()
    problems: list[str] = []
    for heading, start, body in _sections(lines):
        if not heading.startswith(SCANNED_SECTIONS):
            continue
        for first, unit in _units(heading, start, body):
            text = chr(10).join(unit)
            if not text.strip() or not _is_about_a_defect(text):
                continue
            if _has_excerpt(unit):
                continue
            if "[SUPERSEDED" in text or "NONE IN FLIGHT" in text:
                continue
            problems.append(
                f"{path}:{first}: discusses a specific failing cell with no excerpt "
                f'in "{heading}". Paste the record, or run explain-cell and paste that. '
                "An error string names the stage that raised, not the cause."
            )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, default=[DEFAULT_TARGET])
    args = parser.parse_args()
    problems: list[str] = []
    for path in args.paths or [DEFAULT_TARGET]:
        problems.extend(check(path))
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        print(
            f"\n{len(problems)} unsupported cause claim(s). "
            "An error string names the stage that raised, not the cause.",
            file=sys.stderr,
        )
        return 1
    print("diagnosis evidence check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
