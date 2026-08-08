#!/usr/bin/env python3
"""Standalone prompt experiment: instructions + labels in, model answer out, side by side.

NOT part of the extraction pipeline. Reads a flat JSON snapshot of the pipeline's
artifacts (experiments/data/lines_<year>.json) so you can iterate on the PROMPT
without running extraction and without touching any draft or promoted artifact.

Edit PROMPT_TEMPLATE below, re-run, read the table. That is the whole loop.

Usage
-----
  # see the prompts without spending anything
  python experiments/prompt_experiment.py --form form_1040_2025 --dry-run

  # run it for real, write experiments/out/form_1040_2025.md
  python experiments/prompt_experiment.py --form form_1040_2025

  # just a few lines
  python experiments/prompt_experiment.py --form form_1040_2025 --lines 1z,9,11a

  # every form that has instruction coverage
  python experiments/prompt_experiment.py --all
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tax_graph.config import load_config, resolve_llm_model, resolve_llm_seed  # noqa: E402
from tax_graph.extract.cells import expression_schema, render  # noqa: E402
from tax_graph.extract.llm_client import LlmUnavailable, build_llm_client  # noqa: E402
from tax_graph.extract.instruction_sections import (  # noqa: E402
    InstructionSectionsFrame,
    build_instruction_sections_file,
)

DATA = ROOT / "experiments" / "data"
OUT = ROOT / "experiments" / "out"
_INSTRUCTION_FRAME_CACHE: dict[str, InstructionSectionsFrame] = {}


# ---------------------------------------------------------------------------
# THE PROMPT. Edit this, re-run, compare. This is the experiment.
# ---------------------------------------------------------------------------
PROMPT_TEMPLATE = """\
Answer the human question for one line of a US tax form.

Which printed lines does this line use, and what operation combines them?
Use the form's printed line numbers in source_lines, never internal ids.
If the line is not computed from other lines on this form, say so with
operation REQUIRE_INPUT and an empty source_lines list.

Quote verbatim from the text you were given; do not paraphrase.

form: {form}
line: {line}

form face:
{label}

instructions for this line:
{instructions}
"""

# Recurring IRS phrasing that is ambiguous without a hint. Keep this short.
PHRASING_HINTS = """\
"Subtract line A from line B"   -> SUBTRACT, minuend=B, subtrahend=A  (NOT A - B)
"If zero or less, enter -0-"    -> wrap the result in MAX(x, 0)
"but not more than $X"          -> MIN(x, X)
"Combine lines ..."             -> SUM (operands may be negative)
"Enter the smaller of ..."      -> MIN
"whichever is larger"           -> MAX
"from Form N, line L"           -> a fetch from another form, not a computation
"""


EXPR_PROMPT_TEMPLATE = """\
Write the arithmetic for one line of a US tax form.

Return an expression tree. An operand is one of:
  {{"line": "18"}}                        a printed line on THIS form
  {{"form": "Form 2441", "line": "26"}}   a line on ANOTHER form
  {{"const": 0}}                          a numeric constant
and an operand may itself be a nested expression.

Write the WHOLE rule, including any floor or cap the instruction states.
"Subtract line 21 from line 18. If zero or less, enter -0-" is
MAX(SUBTRACT(line 18, line 21), 0) - not a bare subtraction.

For SUBTRACT and DIVIDE, list args in computation order: the value being
reduced first. If the line is not computed from other lines on this form,
use op REQUIRE_INPUT with a single line arg naming itself.

Quote verbatim from the text you were given; do not paraphrase.

form: {form}
line: {line}

form face:
{label}

instructions for this line:
{instructions}
"""


def build_prompt(form: str, row: dict, hints: bool, mode: str = "flat") -> str:
    instructions = row.get("instructions") or "(no instruction text for this line)"
    template = EXPR_PROMPT_TEMPLATE if mode == "expr" else PROMPT_TEMPLATE
    prompt = template.format(
        form=form,
        line=row.get("line") or "?",
        label=row.get("label") or "",
        instructions=instructions,
    )
    if hints:
        prompt += "\nCommon IRS phrasing:\n" + PHRASING_HINTS
    return prompt


def rows_with_instruction_sections(
    form: str,
    entry: dict,
    rows: list[dict],
    *,
    year: str = "2025",
) -> list[dict]:
    """Replace snapshot instruction joins with the pipeline's frame output."""
    frame = _instruction_frame_for_form(form, entry, year=year)
    if frame is None:
        return rows
    refreshed: list[dict] = []
    for row in rows:
        sections = frame.for_line(form, str(row.get("line") or ""))
        updated = dict(row)
        if sections:
            updated["instructions"] = "\n\n".join(section.text for section in sections)
        else:
            updated["instructions"] = ""
        refreshed.append(updated)
    return refreshed


def _instruction_frame_for_form(
    form: str,
    entry: dict,
    *,
    year: str,
) -> InstructionSectionsFrame | None:
    configured = entry.get("instructions_file")
    if configured:
        source_path = ROOT / str(configured)
    elif form in {
        f"schedule_1_{year}",
        f"schedule_1a_{year}",
        f"schedule_2_{year}",
        f"schedule_3_{year}",
    }:
        source_path = ROOT / ".cache" / "raw" / year / f"instructions_form_1040_{year}.txt"
    else:
        return None
    if not source_path.exists():
        return None
    cache_key = f"{source_path.resolve()}::{year}"
    if cache_key not in _INSTRUCTION_FRAME_CACHE:
        _INSTRUCTION_FRAME_CACHE[cache_key] = build_instruction_sections_file(
            source_path,
            source_document_id=source_path.stem,
            year=year,
        )
    return _INSTRUCTION_FRAME_CACHE[cache_key]


def cell(text: str, limit: int = 400) -> str:
    """Make a string safe and readable inside a markdown table cell.

    IRS instruction text contains its own markdown tables, so it arrives with
    both raw and already-escaped pipes. Strip the escapes first, then escape
    once, or the row splits into extra columns.
    """
    s = " ".join(str(text or "").split())
    s = s.replace("\\|", "|").replace("|", "\\|")
    if len(s) > limit:
        s = s[: limit - 3] + "..."
    return s


def run_form(form: str, data: dict, args, client) -> list[dict]:
    entry = data["forms"][form]
    rows = rows_with_instruction_sections(
        form,
        entry,
        entry["lines"],
        year=str(args.year),
    )
    if args.lines:
        wanted = {x.strip().lower() for x in args.lines.split(",") if x.strip()}
        rows = [r for r in rows if r["line"] in wanted]
    if args.only_with_instructions:
        rows = [r for r in rows if r.get("instructions")]
    if args.limit:
        rows = rows[: args.limit]

    schema = (
        expression_schema(data["operations"])
        if args.mode == "expr"
        else response_schema(data["operations"])
    )
    results = []
    for i, row in enumerate(rows, 1):
        prompt = build_prompt(form, row, hints=not args.no_hints, mode=args.mode)
        if args.dry_run:
            print(f"\n{'=' * 70}\n{form}  line {row['line']}\n{'=' * 70}\n{prompt}")
            results.append({**row, "answer": None, "error": "dry-run"})
            continue
        print(f"  [{i}/{len(rows)}] line {row['line']} ...", flush=True)
        try:
            request = {
                "prompt": prompt,
                "schema": schema,
                "model": args.model,
                "max_tokens": args.max_tokens,
                "temperature": None,
                "purpose": "experiment_line_formula",
            }
            if getattr(args, "seed", None) is not None:
                request["seed"] = args.seed
            res = client.structured_completion(**request)
            payload = getattr(res, "payload", res)
            results.append({**row, "answer": payload, "error": None})
        except LlmUnavailable as exc:
            results.append({**row, "answer": None, "error": f"LlmUnavailable: {exc}"})
        except Exception as exc:  # noqa: BLE001 - experiment reports whatever it hits
            results.append({**row, "answer": None, "error": f"{type(exc).__name__}: {exc}"})
    return results


def write_markdown(form: str, data: dict, results: list[dict], path: Path, prompt_sample: str) -> None:
    entry = data["forms"][form]
    lines_md = [
        f"# {form}",
        "",
        f"- form PDF: `{entry.get('pdf')}`",
        f"- instructions: `{entry.get('instructions_file')}`",
        f"- lines: {entry['line_count']}, with instruction text: {entry['with_instructions']}",
        f"- rows in this run: {len(results)}",
        "",
        "## Results",
        "",
        "| line | form face label | instructions | returned |",
        "|---|---|---|---|",
    ]
    for r in results:
        if r["error"] and r["error"] != "dry-run":
            returned = f"**ERROR** {cell(r['error'], 200)}"
        elif r["answer"] is None:
            returned = "_(dry run)_"
        else:
            a = r["answer"]
            if "expression" in a:
                returned = (
                    f"`{cell(render(a['expression']), 220)}`"
                    f"<br>quote: {cell(a.get('quote'), 200)}"
                )
            else:
                srcs = ", ".join(a.get("source_lines") or []) or "_(none)_"
                returned = (
                    f"**{a.get('operation')}**<br>sources: {cell(srcs, 200)}"
                    f"<br>quote: {cell(a.get('quote'), 200)}"
                )
        lines_md.append(
            f"| {r['line']} | {cell(r['label'], 220)} | {cell(r.get('instructions'), 500)} | {returned} |"
        )

    lines_md += ["", "## Full instruction text", ""]
    for r in results:
        if not r.get("instructions"):
            continue
        lines_md += [
            f"### line {r['line']}",
            "",
            "```",
            str(r["instructions"])[:4000],
            "```",
            "",
        ]

    lines_md += ["", "## Prompt used", "", "```", prompt_sample, "```", ""]
    path.write_text("\n".join(lines_md), encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--form", help="document id, e.g. form_1040_2025")
    p.add_argument("--all", action="store_true", help="every form that has instruction text")
    p.add_argument("--lines", help="comma list of line anchors, e.g. 1z,9,11a")
    p.add_argument("--limit", type=int, help="cap rows per form")
    p.add_argument("--only-with-instructions", action="store_true")
    p.add_argument("--no-hints", action="store_true", help="omit the IRS phrasing hints")
    p.add_argument("--dry-run", action="store_true", help="print prompts, call nothing")
    p.add_argument("--mode", choices=["flat","expr"], default="flat",
                   help="flat = operation+source_lines; expr = nested expression tree")
    p.add_argument("--year", default="2025")
    p.add_argument("--model", default=None)
    p.add_argument("--max-tokens", type=int, default=4000)
    args = p.parse_args()

    data = json.loads((DATA / f"lines_{args.year}.json").read_text(encoding="utf-8"))

    if args.all:
        forms = [k for k, v in data["forms"].items() if v["with_instructions"]]
    elif args.form:
        forms = [args.form]
    else:
        print("Pick --form or --all. Forms with instruction text:\n")
        for k, v in data["forms"].items():
            if v["with_instructions"]:
                print(f"  {k:26} {v['with_instructions']:3} of {v['line_count']} lines")
        return 1

    client = None
    if not args.dry_run:
        settings = load_config(root=str(ROOT))
        client = build_llm_client(settings)
        if args.model is None:
            args.model = resolve_llm_model(settings)
        args.seed = resolve_llm_seed(settings)

    OUT.mkdir(parents=True, exist_ok=True)
    for form in forms:
        if form not in data["forms"]:
            print(f"unknown form: {form}")
            return 1
        print(f"\n{form}")
        results = run_form(form, data, args, client)
        if args.dry_run:
            continue
        sample_rows = rows_with_instruction_sections(
            form,
            data["forms"][form],
            data["forms"][form]["lines"],
            year=str(args.year),
        )
        sample = build_prompt(form, sample_rows[0], hints=not args.no_hints, mode=args.mode)
        out_path = OUT / f"{form}.md"
        write_markdown(form, data, results, out_path, sample)
        ok = sum(1 for r in results if r["answer"])
        print(f"  -> {out_path.relative_to(ROOT)}  ({ok}/{len(results)} answered)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
