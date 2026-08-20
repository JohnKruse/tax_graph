"""Grade a sample of derived cells against the evidence we actually supplied.

The point is NOT to ask a model whether an answer looks nice.  It is to put
three things side by side - the printed face, the instruction paragraphs we
handed over, and the operation that came back - and ask whether the evidence
supports the operation.

The grade scale has a deliberate escape hatch.  About half of all cells reach
the model with no instruction evidence at all, and grading those as failures
would confuse "we starved it" with "it reasoned badly".  Those get NO_EVIDENCE,
which is a verdict about US, not about the answer.

    .venv\\Scripts\\python.exe tools/grade_sample.py --n 15 --out sample.html
"""

from __future__ import annotations

import argparse
import html
import json
import random
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tax_graph.acquire.manifest import load_manifest  # noqa: E402
from tax_graph.config import load_config, resolve_llm_model  # noqa: E402
from tax_graph.extract.llm_client import build_llm_client  # noqa: E402
from workbench import generated_review as gr  # noqa: E402


GRADES = ["F", "D", "C", "B", "A", "NO_EVIDENCE"]

# Two axes, deliberately. The first version asked only "does the operation
# follow from the evidence", and a swapped-instruction control could satisfy it
# by answering "not derivable" - correct, given wrong evidence, and useless to
# us. Whether the evidence BELONGS to this line is a separate question and the
# one that finds misattribution.
FITS = ["GOVERNS", "WRONG_LINE", "NONE_SUPPLIED", "UNCLEAR"]

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["evidence_fit", "governs_line", "grade", "reason"],
    "properties": {
        "evidence_fit": {"type": "string", "enum": FITS},
        "governs_line": {
            "type": "string",
            "description": "when WRONG_LINE, the line the supplied text actually governs; else empty",
        },
        "grade": {"type": "string", "enum": GRADES},
        "reason": {"type": "string", "minLength": 1},
    },
}

PROMPT = """You are auditing one cell of a US tax form graph.

You get the PRINTED FACE of a form line, the INSTRUCTION TEXT that was supplied
to the extractor, and the OPERATION the extractor produced.

Answer TWO independent questions.

1. evidence_fit - does the supplied instruction text actually govern THIS line?
   GOVERNS        the text is the instruction for this very line
   WRONG_LINE     the text is a real instruction, but for a DIFFERENT line;
                  put that line in governs_line
   NONE_SUPPLIED  no instruction text was supplied
   UNCLEAR        you cannot tell
   Judge this by what the text says about itself - its own heading and its own
   line references. Do not use your own tax knowledge to excuse a mismatch.

2. grade - given whatever evidence was actually supplied, is the operation a
   defensible answer? A is clearly supported, F is contradicted. If nothing
   usable was supplied and the face cannot settle it, NO_EVIDENCE.

These are independent. WRONG_LINE with grade A is a normal and important
result: it means the extractor coped correctly with evidence we mis-supplied.
That is a defect in OUR pipeline and we need to see it.

Reason: under 25 words, naming what decided the fit.

PRINTED FACE:
{face}

INSTRUCTION TEXT SUPPLIED:
{instructions}

OPERATION PRODUCED:
{operation}
"""


def _clip(value: Any, width: int) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= width else text[: width - 3] + "..."


def _collect(year: str, documents: list[str]) -> list[tuple[str, dict, dict]]:
    rows: list[tuple[str, dict, dict]] = []
    for path in sorted((ROOT / "graph" / year / "_drafts").iterdir()):
        if not path.is_dir() or (documents and path.name not in documents):
            continue
        try:
            draft = gr._load_draft(ROOT, year, path.name)
        except Exception:  # noqa: BLE001
            continue
        spans = gr._span_index(draft.get("candidate_spans"))
        spans = dict(spans)
        spans["__ops__"] = _graph_operations(draft)
        spans["__outcomes__"] = _outcome_summary(draft)
        micro = draft.get("micro_extraction", {}) or {}
        for record in (micro.get("formula_cells") or []) + (micro.get("review_gaps") or []):
            if isinstance(record, dict) and record.get("line_anchor"):
                rows.append((path.name, record, spans))
    return rows


def _links(manifest: Any, document_id: str) -> tuple[str, str]:
    """Return (form url, instructions url) straight from the manifest."""
    by_id = manifest.by_document_id()
    entry = by_id.get(document_id)
    form_url = getattr(entry, "url", "") or ""
    instructions_url = ""
    target = getattr(entry, "instructions_document_id", "") or ""
    if target and target in by_id:
        related = by_id[target]
        instructions_url = getattr(related, "instruction_url", "") or getattr(related, "url", "") or ""
    return form_url, instructions_url


FIT_BADGE = {
    "GOVERNS": "ok",
    "WRONG_LINE": "WRONG",
    "NONE_SUPPLIED": "none",
    "UNCLEAR": "?",
}


def _graph_operations(draft: dict) -> dict:
    """Map a target cell to the operation the GRAPH holds for it.

    Draft rules carry a human-readable ``description`` - "line 19 = line 17 /
    line 18" - and edges bind a rule to its target.  This is the answer to
    "what did the pipeline actually decide", which the outcome kind alone
    ("computation") never tells you.
    """
    rules = {str(r.get("rule_id")): r for r in gr._records(draft.get("rules"))}
    out: dict[str, str] = {}
    for edge in gr._records(draft.get("edges")):
        rule = rules.get(str(edge.get("rule_id") or ""))
        target = str(edge.get("target") or "")
        if rule and target and target not in out:
            description = str(rule.get("description") or "").strip()
            operation = str(rule.get("operation") or "").strip()
            if description:
                out[target] = f"{description}   [{operation}]" if operation else description
    for rule_id, rule in rules.items():
        description = str(rule.get("description") or "").strip()
        if not description:
            continue
        stem = rule_id[len("rule_"):] if rule_id.startswith("rule_") else rule_id
        for suffix in ("_" + str(rule.get("operation") or "").lower(), ""):
            target = stem[: -len(suffix)] if suffix and stem.endswith(suffix) else stem
            out.setdefault(target, description)
            break
    return out


def _outcome_summary(draft: dict) -> dict:
    """Map a target cell to its non-computed outcome, in plain words."""
    out: dict[str, str] = {}
    micro = draft.get("micro_extraction", {}) or {}
    for record in micro.get("outcomes") or []:
        if not isinstance(record, dict):
            continue
        target = str(record.get("target_cell_id") or "")
        kind = str(record.get("kind") or "")
        if not target or not kind:
            continue
        form, line, box = (str(record.get(k) or "") for k in ("form", "line", "box"))
        source = ""
        if form and box:
            source = f" from {form} box {box}"
        elif form and line:
            source = f" from {form} line {line}"
        reason = str(record.get("reason") or "")
        detail = f": {reason[:90]}" if kind == "not_derivable" and reason else ""
        out[target] = f"{kind}{source}{detail}"
    return out


def _deep_links(year: str) -> dict:
    """Map (document, line) to a page number and an IRS instructions anchor.

    81 of 82 stored instruction citations carry a locator like
    ``html#en_US_2025_publink1000106118``, which is a real anchor on the IRS
    instructions page.  Pairing that with the address artifact's page number
    turns "here is a row" into "here is the paragraph", which is the difference
    between a report you can read and one you can act on.
    """
    import yaml

    anchors: dict[str, tuple[str, str]] = {}
    citations_dir = ROOT / "graph" / year / "citations"
    if citations_dir.is_dir():
        for path in citations_dir.glob("*.yaml"):
            try:
                payload = yaml.safe_load(path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            items = payload if isinstance(payload, list) else (payload or {}).get("citations", [])
            for citation in items or []:
                if not isinstance(citation, dict):
                    continue
                locator = str(citation.get("locator") or "")
                url = str(citation.get("url") or "")
                if "#" in locator and url:
                    anchors[str(citation.get("citation_id"))] = (url, locator.split("#", 1)[1])

    out: dict[tuple[str, str], dict] = {}
    addresses_dir = ROOT / "graph" / year / "addresses"
    if addresses_dir.is_dir():
        for path in addresses_dir.glob("*.yaml"):
            try:
                payload = yaml.safe_load(path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            rows = payload if isinstance(payload, list) else (payload or {}).get("addresses", [])
            for row in rows or []:
                if not isinstance(row, dict) or not row.get("official_ref"):
                    continue
                page = ""
                for item in row.get("evidence") or []:
                    if isinstance(item, dict) and item.get("page"):
                        page = str(item["page"])
                        break
                anchor_url = ""
                for ref in row.get("citation_refs") or []:
                    if str(ref) in anchors:
                        url, fragment = anchors[str(ref)]
                        anchor_url = f"{url}#{fragment}"
                        break
                key = (str(path.stem), str(row["official_ref"]).lower())
                if key not in out or (not out[key].get("anchor") and anchor_url):
                    out[key] = {"page": page, "anchor": anchor_url}
    return out


def _instruction_text(record: dict, spans: dict) -> str:
    ids = record.get("instruction_span_ids") or []
    if not ids:
        return ""
    out = []
    for span_id in ids[:3]:
        span = spans.get(str(span_id)) or {}
        out.append(f"[{span_id}] {_clip(span.get('text'), 1500)}")
    return "\n\n".join(out)


def _operation(record: dict, spans: dict) -> str:
    """What the graph holds for this cell, preferring the rule over the label."""
    target = str(record.get("target_cell_id") or "")
    operation = (spans.get("__ops__") or {}).get(target)
    if operation:
        return _clip(operation, 400)
    outcome = (spans.get("__outcomes__") or {}).get(target)
    if outcome:
        return _clip(outcome, 400)
    if record.get("review_gap"):
        return "NO OPERATION - " + _clip(record.get("review_gap"), 200)
    for key in ("outcome_kind", "response_kind"):
        if record.get(key):
            return _clip(record.get(key), 120) + " (no rule in graph)"
    return "(none produced)"


def _stratum(record: dict) -> str:
    """Bucket a cell by the shape of the evidence it got, not by its answer."""
    if not (record.get("instruction_span_ids") or []):
        return "starved"
    if str(record.get("status") or "") == "review_gap":
        return "gapped"
    return "complete"


def _stratified(rows: list, total: int, rng: random.Random) -> list:
    """Draw evenly across strata so a uniform sample cannot hide in easy cells."""
    buckets: dict[str, list] = {}
    for row in rows:
        buckets.setdefault(_stratum(row[1]), []).append(row)
    per = max(1, total // max(len(buckets), 1))
    out: list = []
    for name in sorted(buckets):
        pool = buckets[name]
        out.extend(rng.sample(pool, min(per, len(pool))))
        print(f"  stratum {name}: {min(per, len(pool))} of {len(pool)}")
    return out


def _swapped_controls(rows: list, count: int, rng: random.Random) -> list:
    """Known-wrong rows: a real cell paired with ANOTHER line's instructions.

    This is the calibration.  We know the answer for these by construction, so
    if the grader passes them the grades on the real rows mean nothing.  They
    are shuffled in blind - nothing marks them in the prompt.
    """
    havers = [row for row in rows if (row[1].get("instruction_span_ids") or [])]
    if len(havers) < 2:
        return []
    picks = rng.sample(havers, min(count, len(havers)))
    out = []
    for document_id, record, spans in picks:
        donor = rng.choice([r for r in havers if r[1] is not record])
        donor_text = _instruction_text(donor[1], donor[2])
        if donor_text:
            out.append((document_id, record, spans, donor_text))
    return out


def _render_html(graded: list[dict], year: str) -> str:
    order = {grade: index for index, grade in enumerate(GRADES)}
    fit_order = {"WRONG_LINE": 0, "UNCLEAR": 1, "NONE_SUPPLIED": 2, "GOVERNS": 3}
    graded.sort(key=lambda row: (fit_order.get(row.get("fit", ""), 9),
                                 order.get(row["grade"], 9),
                                 row["document_id"], str(row["line"])))
    counts: dict[str, int] = {}
    for row in graded:
        counts[row["grade"]] = counts.get(row["grade"], 0) + 1
    summary = " &middot; ".join(f"<b>{html.escape(k)}</b> {v}" for k, v in
                                sorted(counts.items(), key=lambda kv: order.get(kv[0], 9)))
    body = [
        "<style>",
        "body{font:14px/1.45 system-ui,sans-serif;margin:24px;color:#1a1a1a}",
        "table{border-collapse:collapse;width:100%}",
        "th,td{border:1px solid #d0d0d0;padding:8px;vertical-align:top;text-align:left}",
        "th{background:#f4f4f4;position:sticky;top:0}",
        "td.g{font-weight:700;text-align:center;white-space:nowrap;width:1%;font-size:12px}",
        "code{font:12px/1.4 ui-monospace,monospace}",
        ".WRONG_LINE{background:#ffc9c9}.UNCLEAR{background:#ffe8cc}.NONE_SUPPLIED{background:#e0e0e0}.GOVERNS{background:#d6f0d6}",
        ".F{background:#ffd7d7}.D{background:#ffe8cc}.C{background:#fff6cc}",
        ".B{background:#e8f5d0}.A{background:#d6f0d6}.NO_EVIDENCE{background:#e0e0e0}",
        "details{max-width:60ch}pre{white-space:pre-wrap;font:12px/1.4 ui-monospace,monospace}",
        "</style>",
        f"<h1>Derived-cell sample, {html.escape(year)}</h1>",
        f"<p>{len(graded)} cells, worst first. {summary}</p>",
        "<p><i>NO_EVIDENCE is a verdict about what we supplied, not about the answer.</i></p>",
        "<table><tr><th title=\"ok / WRONG / none\">Fit</th><th>Grade</th><th>Document</th><th>Line</th><th>Face</th>"
        "<th>Instructions supplied</th><th>Operation in the graph</th><th>Why</th><th>IRS</th></tr>",
    ]
    for row in graded:
        instructions = row["instructions"] or "<b>NONE SUPPLIED</b>"
        links = []
        if row["form_url"]:
            label = "form p." + row["form_url"].split("#page=")[1] if "#page=" in row["form_url"] else "form"
            links.append(f'<a href="{html.escape(row["form_url"])}">{html.escape(label)}</a>')
        if row["instructions_url"]:
            label = "instr &para;" if "#" in row["instructions_url"] else "instr"
            links.append(f'<a href="{html.escape(row["instructions_url"])}">{label}</a>')
        body.append(
            f'<tr><td class="g {html.escape(row.get("fit",""))}" title="{html.escape(row.get("fit",""))}">'
            f'{html.escape(FIT_BADGE.get(row.get("fit",""), "?"))}</td>'
            f'<td class="g {html.escape(row["grade"])}">{html.escape(row["grade"])}</td>'
            f'<td>{html.escape(row["document_id"])}{" <b>[CONTROL]</b>" if row.get("control") else ""}</td>'
            f'<td>{html.escape(str(row["line"]))}</td>'
            f'<td>{html.escape(_clip(row["face"], 160))}</td>'
            f'<td><details><summary>{"none" if not row["instructions"] else "show"}</summary>'
            f'<pre>{instructions if not row["instructions"] else html.escape(row["instructions"])}</pre></details></td>'
            f'<td><code>{html.escape(_clip(row["operation"], 220))}</code>{("<br><small>instr belongs to line " + html.escape(row["governs"]) + "</small>") if row.get("governs") else ""}</td>'
            f'<td>{html.escape(row["reason"])}</td>'
            f'<td>{" ".join(links) or "-"}</td></tr>'
        )
    body.append("</table>")
    return "\n".join(body)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", default="2025")
    parser.add_argument("--doc", action="append", default=[])
    parser.add_argument("--n", type=int, default=15, help="how many cells to grade")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--stratify", action="store_true",
                        help="sample evenly across starved / gapped / complete cells")
    parser.add_argument("--controls", type=int, default=0,
                        help="add N known-wrong rows whose instructions belong to another line")
    parser.add_argument("--out", type=Path, default=ROOT / "output" / "graded_sample.html")
    args = parser.parse_args()

    rows = _collect(args.year, args.doc)
    if not rows:
        print("no rows found", file=sys.stderr)
        return 1
    rng = random.Random(args.seed or None)
    if args.stratify:
        sample = _stratified(rows, args.n, rng)
    else:
        sample = rng.sample(rows, min(args.n, len(rows)))
    controls = _swapped_controls(rows, args.controls, rng) if args.controls else []
    sample = [(doc, rec, spans, None) for doc, rec, spans in sample] + controls
    rng.shuffle(sample)  # the grader must not be able to tell a control from a real row

    config = load_config(root=ROOT)
    client = build_llm_client(config)
    model = resolve_llm_model(config, "micro")
    manifest = load_manifest(root=ROOT)
    deep = _deep_links(args.year)

    graded: list[dict] = []
    for index, (document_id, record, spans, control) in enumerate(sample, start=1):
        instructions = control if control is not None else _instruction_text(record, spans)
        operation = _operation(record, spans)
        face = str(record.get("label") or "")
        prompt = PROMPT.format(
            face=face or "(none)",
            instructions=instructions or "(NONE SUPPLIED)",
            operation=operation,
        )
        try:
            payload = client.structured_completion(
                prompt=prompt,
                schema=SCHEMA,
                model=model,
                max_tokens=2000,
                temperature=None,
                purpose="grade_sample",
            )
            if isinstance(payload, str):
                payload = json.loads(payload)
            if isinstance(payload, dict) and "grade" not in payload:
                for key in ("data", "content", "response"):
                    if isinstance(payload.get(key), dict):
                        payload = payload[key]
                        break
            grade = str(payload.get("grade") or "F")
            reason = str(payload.get("reason") or "")
            fit = str(payload.get("evidence_fit") or "UNCLEAR")
            governs = str(payload.get("governs_line") or "")
        except Exception as exc:  # noqa: BLE001 - a grader failure is data too
            grade, reason = "F", f"grader error: {type(exc).__name__}: {exc}"[:200]
            fit, governs = "UNCLEAR", ""
        form_url, instructions_url = _links(manifest, document_id)
        extra = deep.get((document_id, str(record.get('line_anchor') or '').lower()), {})
        if form_url and extra.get('page'):
            form_url = f"{form_url}#page={extra['page']}"
        if extra.get('anchor'):
            instructions_url = extra['anchor']
            
        graded.append({
            "document_id": document_id, "line": record.get("line_anchor"),
            "face": face, "instructions": instructions, "operation": operation,
            "grade": grade, "reason": reason, "fit": fit, "governs": governs,
            "form_url": form_url, "instructions_url": instructions_url,
            "control": control is not None,
        })
        print(f"  [{index}/{len(sample)}] {document_id} line {record.get('line_anchor')}: {grade} / {fit}")

    control_rows = [row for row in graded if row.get("control")]
    if control_rows:
        caught = [r for r in control_rows if r["fit"] == "WRONG_LINE"]
        print("")
        print(f"CONTROLS: {len(caught)}/{len(control_rows)} swapped rows identified as WRONG_LINE")
        for row in control_rows:
            flag = "caught" if row in caught else "MISSED"
            print(f"   {flag:<7} {row['document_id']} line {row['line']} -> fit={row['fit']} grade={row['grade']}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(_render_html(graded, args.year), encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
