"""Guards for the diagnosis-evidence checker.

The first test is the regression case the checker exists for: the real queued
item from 2026-08-20 that named a cause off an error string without opening the
finding.  An earlier phrase-matching implementation passed this text, which is
why the checker triggers on the SUBJECT of a unit rather than on cause wording.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_diagnosis_evidence import check  # noqa: E402


REAL_BAD_ITEM = """# handoff

## Queued (ONE LINE each - do not spec ahead)

- **LINE 1e: THE FORM FACE NAMES THE SOURCE AND THE PIPELINE CANNOT FIND IT (Architect, verdict
  recorded 2026-08-20).** Printed label *"Taxable dependent care benefits from Form 2441, line
  26"*; draft says `status: review_gap`, `review_gap: source line is not present in the
  deterministic outline index`. **OPEN IT INDIVIDUALLY** - on 2026-08-15 that exact error string
  turned out to be five unrelated defects.
"""

WITH_EXCERPT = """# handoff

## Queued (ONE LINE each - do not spec ahead)

- **LINE 1e DOES NOT RESOLVE (Architect).** The finding, pasted:

      code: unresolved_source_line
      source_line: {form: Form 2441, line: '26', role: null}
"""

VIA_EXPLAIN_CELL = """# handoff

## Current round

**M20-SXX.** Line 1e does not resolve; `explain-cell --doc form_1040_2025 --line 1e` shows the
computed key and the lookup result.
"""

NO_DEFECT_SUBJECT = """# handoff

## Queued (ONE LINE each - do not spec ahead)

- **RETIRE THE 2441 OVERLAY.** It is a surviving special case and blocks a later round.
"""


@pytest.mark.m20
def test_the_real_2026_08_20_bad_item_is_caught(tmp_path: Path) -> None:
    path = tmp_path / "handoff.md"
    path.write_text(REAL_BAD_ITEM, encoding="utf-8")

    problems = check(path)

    assert len(problems) == 1
    assert "no excerpt" in problems[0]


@pytest.mark.m20
@pytest.mark.parametrize("body", [WITH_EXCERPT, VIA_EXPLAIN_CELL, NO_DEFECT_SUBJECT])
def test_evidence_or_no_defect_subject_passes(tmp_path: Path, body: str) -> None:
    path = tmp_path / "handoff.md"
    path.write_text(body, encoding="utf-8")

    assert check(path) == []


@pytest.mark.m20
def test_one_items_excerpt_does_not_excuse_the_next(tmp_path: Path) -> None:
    """Queued items are judged one at a time; a neighbour's record is not evidence."""
    path = tmp_path / "handoff.md"
    path.write_text(WITH_EXCERPT + REAL_BAD_ITEM.split("do not spec ahead)\n", 1)[1], encoding="utf-8")

    assert len(check(path)) == 1


@pytest.mark.m20
def test_the_live_handoff_satisfies_its_own_rule() -> None:
    assert check(ROOT / "plans" / "AGENT_HANDOFF.md") == []
