"""Dump face, instructions and derived operation for a random sample of cells.

Built 2026-08-20 after a blind spot that cost a day: every failure list in this
repo records errors of COMMISSION - something ran and complained.  A thin
evidence packet raises nothing, appears in no list, and produced 147 cells that
are marked complete while having no instruction evidence at all.  There was
nothing to open, so nobody opened it.

This reads what we HANDED the model beside what came back, for a sample you can
actually eyeball.  No model calls; it only reads drafts.

    .venv\\Scripts\\python.exe tools/sample_rows.py --pct 5
    .venv\\Scripts\\python.exe tools/sample_rows.py --doc form_1116_2025 --pct 100
    .venv\\Scripts\\python.exe tools/sample_rows.py --pct 10 --only-missing-instructions
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from workbench import generated_review as gr  # noqa: E402


def _clip(value: Any, width: int) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= width else text[: width - 3] + "..."


def _rows(year: str, documents: list[str]) -> list[tuple[str, dict, dict]]:
    out: list[tuple[str, dict, dict]] = []
    drafts = ROOT / "graph" / year / "_drafts"
    for path in sorted(drafts.iterdir()):
        if not path.is_dir() or (documents and path.name not in documents):
            continue
        try:
            draft = gr._load_draft(ROOT, year, path.name)
        except Exception:  # noqa: BLE001 - an unreadable draft is a fact to report
            print(f"  ! {path.name}: draft unreadable", file=sys.stderr)
            continue
        spans = gr._span_index(draft.get("candidate_spans"))
        micro = draft.get("micro_extraction", {}) or {}
        records = (micro.get("formula_cells") or []) + (micro.get("review_gaps") or [])
        for record in records:
            if isinstance(record, dict):
                out.append((path.name, record, spans))
    return out


def _render(document_id: str, record: dict, spans: dict) -> str:
    span_ids = record.get("instruction_span_ids") or []
    lines = [
        "=" * 78,
        f"{document_id}  line {record.get('line_anchor')}   [{record.get('status') or '?'}]",
        "",
        f"  FACE   : {_clip(record.get('label'), 300)}",
    ]
    if span_ids:
        for span_id in span_ids[:3]:
            span = spans.get(str(span_id)) or {}
            lines.append(f"  INSTR  : {span_id}")
            lines.append(f"           {_clip(span.get('text'), 400)}")
    else:
        lines.append("  INSTR  : *** NONE ***")
        wrong = int(record.get("wrong_owner_instruction_spans") or 0)
        if wrong:
            lines.append(f"           ({wrong} wrong-owner instruction span(s) were seen and rejected)")
    operation = record.get("expression") or record.get("outcome_kind") or record.get("response_kind")
    lines.append(f"  DERIVED: {_clip(operation, 300) or '(none)'}")
    if record.get("review_gap"):
        lines.append(f"  GAP    : {_clip(record.get('review_gap'), 200)}")
    if record.get("rejected_quote"):
        lines.append(f"  REJECTED QUOTE: {_clip(record.get('rejected_quote'), 200)}")
    # The point of the tool: a label that defers to instructions we never supplied.
    face = str(record.get("label") or "").lower()
    if not span_ids and "instruction" in face:
        lines.append("  >>> FACE SAYS 'SEE INSTRUCTIONS' AND NONE WERE SUPPLIED <<<")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", default="2025")
    parser.add_argument("--doc", action="append", default=[], help="repeat to select documents")
    parser.add_argument("--pct", type=float, default=5.0, help="sample percentage, 1-100")
    parser.add_argument("--seed", type=int, default=0, help="0 means a fresh sample each run")
    parser.add_argument("--out", type=Path, help="write to a file instead of stdout")
    parser.add_argument(
        "--only-missing-instructions",
        action="store_true",
        help="sample only cells that got no instruction evidence",
    )
    args = parser.parse_args()

    if not 0 < args.pct <= 100:
        print("--pct must be between 1 and 100", file=sys.stderr)
        return 2

    rows = _rows(args.year, args.doc)
    if args.only_missing_instructions:
        rows = [item for item in rows if not (item[1].get("instruction_span_ids") or [])]
    if not rows:
        print("no rows matched", file=sys.stderr)
        return 1

    rng = random.Random(args.seed or None)
    take = max(1, round(len(rows) * args.pct / 100))
    sample = rng.sample(rows, min(take, len(rows)))
    sample.sort(key=lambda item: (item[0], str(item[1].get("line_anchor"))))

    missing = sum(1 for _, record, _ in sample if not (record.get("instruction_span_ids") or []))
    body = [
        f"SAMPLE: {len(sample)} of {len(rows)} rows ({args.pct}%)"
        + (" [missing-instructions only]" if args.only_missing_instructions else ""),
        f"of the sample, {missing} have NO instruction evidence"
        f" ({missing * 100 // max(len(sample), 1)}%)",
        "",
    ]
    body.extend(_render(document_id, record, spans) for document_id, record, spans in sample)
    text = "\n".join(body) + "\n"

    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"wrote {len(sample)} rows to {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
