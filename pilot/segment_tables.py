"""Measure whether ONE segmentation call over EVERY acquired table can replace
the per-table classifier.

This is a pilot, off to the side: no CLI wiring, no production import depends on
it, and it writes nothing into the graph. It answers one question before S99 is
built - does the model, shown all 200 of the 1040's tables in order as Markdown,
group them into the worksheets we already know are correct?

The model returns TABLE IDS, never text. Rows, byte offsets, and citations stay
with the deterministic HTML parser, so provenance is untouched.

    .venv\\Scripts\\python.exe pilot\\segment_tables.py instructions_form_1040_2025

Add --dry-run to print the payload size and the prompt without calling out.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tax_graph.ingest.worksheet_harvest as W  # noqa: E402
from tax_graph.config import (  # noqa: E402
    get_config_value,
    load_config,
    resolve_llm_model,
    resolve_llm_seed,
)


def _table_markdown(table: Any) -> str:
    """Render one acquired table as Markdown, with its printed line tokens.

    The line tokens come from the same `_row_line` accessor the extent walker
    uses, so what the model sees is what the harvester would parse.
    """
    heading = table.heading.text.strip() if table.heading is not None else "(no heading)"
    lines = [W._row_line(row) for row in table.rows]
    lines = [line for line in lines if line]
    parts = [f"### table {table.table_id}", f"heading: {heading}"]
    parts.append(f"printed_line_tokens: {','.join(lines) if lines else '(none)'}")
    body = []
    for row in table.rows:
        text = row.text.strip()
        if text:
            body.append(f"| {text}")
    parts.append("\n".join(body) if body else "(no rows)")
    return "\n".join(parts)


def build_payload(source_text: str) -> tuple[str, tuple[Any, ...]]:
    tables = W._source_tables(source_text)
    rendered = "\n\n".join(_table_markdown(table) for table in tables)
    return rendered, tables


PROMPT_HEADER = """Segment an IRS instruction booklet into its worksheets.

You are given EVERY table in one acquired booklet, in printed order, as Markdown.
Each carries its table id, its heading, and the printed line tokens parsed from
its rows.

Group the tables. A worksheet is a computation a filer fills in, and ONE
worksheet is often split across several tables: a caption table with no numbered
rows, a body table, a continuation whose numbering resumes where the previous
table stopped, and parameter grids the worksheet's own lines refer to. Lookup
tables that stand alone (a tax table, an EIC table) are NOT worksheets. Layout
and prose tables are not worksheets.

Return one entry per worksheet you find. Use the printed title. List the table
ids that compose it, in printed order, and say which of them are parameter grids
rather than numbered worksheet rows. Report the printed form line(s) the
worksheet serves when its heading names them.

Account for EVERY table id: any table not part of a worksheet goes in
`not_a_worksheet` with a one-word reason (lookup, layout, prose).

Return table ids only. Do not transcribe row text.
"""


def segmentation_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["worksheets", "not_a_worksheet"],
        "properties": {
            "worksheets": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "title",
                        "table_ids",
                        "parameter_table_ids",
                        "serves_lines",
                    ],
                    "properties": {
                        "title": {"type": "string"},
                        "table_ids": {"type": "array", "items": {"type": "integer"}},
                        "parameter_table_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                        "serves_lines": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            "not_a_worksheet": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["table_id", "reason"],
                    "properties": {
                        "table_id": {"type": "integer"},
                        "reason": {"type": "string"},
                    },
                },
            },
        },
    }


def call_model(prompt: str, config: Mapping[str, Any], max_tokens: int) -> Mapping[str, Any]:
    from tax_graph.extract.llm_client import build_llm_client

    client = build_llm_client(dict(config))
    request: dict[str, Any] = {
        "prompt": prompt,
        "schema": segmentation_schema(),
        "model": resolve_llm_model(config, "micro"),
        "max_tokens": max_tokens,
        "temperature": get_config_value(dict(config), "llm.temperature"),
        "purpose": "tax_graph_pilot_table_segmentation",
    }
    seed = resolve_llm_seed(config)
    if seed is not None:
        request["seed"] = seed
    return client.structured_completion(**request)


WINDOW_HEADER = """Decide where ONE worksheet ends in an IRS instruction booklet.

You are given a CANDIDATE table and the tables that FOLLOW it in printed order.
Decide whether the candidate starts a worksheet, and if it does, which of the
following tables belong to the SAME worksheet.

ONE worksheet is often split: a caption table with no numbered rows, a body
table, a continuation whose numbering resumes where the previous table stopped,
and parameter grids the worksheet's own lines refer to. A table that starts its
own numbering at 1 under a different title is a DIFFERENT worksheet. A standalone
lookup chart is not part of the worksheet even when it sits directly beneath it.

Return table ids only. Do not transcribe row text.
"""


def window_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "starts_a_worksheet",
            "title",
            "table_ids",
            "parameter_table_ids",
            "serves_lines",
        ],
        "properties": {
            "starts_a_worksheet": {"type": "boolean"},
            "title": {"type": "string"},
            "table_ids": {"type": "array", "items": {"type": "integer"}},
            "parameter_table_ids": {"type": "array", "items": {"type": "integer"}},
            "serves_lines": {"type": "array", "items": {"type": "string"}},
        },
    }


def call_window(
    tables: tuple[Any, ...],
    index: int,
    lookahead: int,
    config: Mapping[str, Any],
    max_tokens: int,
) -> tuple[Mapping[str, Any], int]:
    from tax_graph.extract.llm_client import build_llm_client

    chunk = tables[index : index + 1 + lookahead]
    rendered = "\n\n".join(_table_markdown(table) for table in chunk)
    prompt = (
        f"{WINDOW_HEADER}\ncandidate table id: {tables[index].table_id}\n\n{rendered}\n"
    )
    client = build_llm_client(dict(config))
    request: dict[str, Any] = {
        "prompt": prompt,
        "schema": window_schema(),
        "model": resolve_llm_model(config, "micro"),
        "max_tokens": max_tokens,
        "temperature": get_config_value(dict(config), "llm.temperature"),
        "purpose": "tax_graph_pilot_table_window",
    }
    seed = resolve_llm_seed(config)
    if seed is not None:
        request["seed"] = seed
    return client.structured_completion(**request), len(prompt)


def window_fingerprint(source_text: str, tables: tuple[Any, ...], index: int, lookahead: int) -> str:
    """Key a window by the bytes of the tables it contains.

    Codex must reproduce this exactly to read the seeded cache: sha256 over the
    acquired source bytes of the anchor table and its lookahead, concatenated in
    printed order with a newline between tables, plus the lookahead size so a
    different window size cannot collide with this one.
    """
    chunk = tables[index : index + 1 + lookahead]
    joined = "\n".join(source_text[table.start : table.end] for table in chunk)
    return hashlib.sha256(f"{lookahead}\n{joined}".encode("ascii")).hexdigest()


def _load_window_cache(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="ascii")) or {}
    windows = payload.get("windows", {})
    if not isinstance(windows, dict):
        raise ValueError(f"invalid window cache: {path}")
    return {str(k): dict(v) for k, v in windows.items() if isinstance(v, dict)}


def _write_window_cache(path: Path, entries: Mapping[str, Mapping[str, Any]], lookahead: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {"schema_version": 1, "lookahead": lookahead, "windows": dict(entries)},
            sort_keys=True,
            allow_unicode=False,
        ),
        encoding="ascii",
        newline="\n",
    )


def seed_windows(
    source_text: str,
    tables: tuple[Any, ...],
    lookahead: int,
    config: Mapping[str, Any],
    max_tokens: int,
    cache_path: Path,
) -> int:
    """Call one window per table, persisting after each so a failure costs one call.

    Per-item isolation, the same rule S98 put everywhere else: a window that
    fails is recorded and the pass carries on.
    """
    cached = _load_window_cache(cache_path)
    updated = dict(cached)
    starts = 0
    failures = 0
    reused = 0
    for index, table in enumerate(tables):
        fingerprint = window_fingerprint(source_text, tables, index, lookahead)
        if fingerprint in cached:
            reused += 1
            if cached[fingerprint].get("starts_a_worksheet"):
                starts += 1
            continue
        try:
            payload, _ = call_window(tables, index, lookahead, config, max_tokens)
            record = dict(payload)
            record["anchor_table_id"] = table.table_id
        except Exception as exc:  # noqa: BLE001 - one window must not kill the pass
            failures += 1
            record = {
                "anchor_table_id": table.table_id,
                "error": f"{type(exc).__name__}: {exc}"[:300],
            }
            print(f"  t{table.table_id}: FAILED {type(exc).__name__}")
        updated[fingerprint] = record
        _write_window_cache(cache_path, updated, lookahead)
        if record.get("starts_a_worksheet"):
            starts += 1
            ids = record.get("table_ids") or []
            print(f"  t{table.table_id:<4d} -> {str(record.get('title'))[:52]:52s} {ids}")
    print(
        f"\nwindows={len(tables)}; reused={reused}; worksheet_starts={starts}; failures={failures}"
    )
    print(f"cache: {cache_path}")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_document_id")
    parser.add_argument("--year", default="2025")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-tokens", type=int, default=16000)
    parser.add_argument("--output", default=None)
    parser.add_argument(
        "--window",
        type=int,
        default=None,
        help="Sliding-window mode: lookahead size. Requires --anchor.",
    )
    parser.add_argument(
        "--anchor",
        type=int,
        action="append",
        default=[],
        help="Candidate table id to open a window on. Repeatable.",
    )
    parser.add_argument(
        "--seed-cache",
        action="store_true",
        help="Window EVERY table and persist to the acquisition cache.",
    )
    args = parser.parse_args()

    path = ROOT / ".cache" / "raw" / args.year / f"{args.source_document_id}.html"
    if not path.exists():
        print(f"no acquired HTML: {path}")
        return 1
    source_text = path.read_text(encoding="ascii")
    rendered, tables = build_payload(source_text)
    prompt = f"{PROMPT_HEADER}\n\n{rendered}\n"

    print(f"tables: {len(tables)}")
    print(f"payload characters: {len(prompt)}")
    print(f"rough tokens: {len(prompt) // 4}")
    if args.dry_run:
        print("--- first 1200 characters of payload ---")
        print(prompt[:1200])
        return 0

    config = load_config(root=ROOT)

    if args.seed_cache:
        lookahead = args.window if args.window is not None else 4
        cache_path = (
            ROOT
            / ".cache"
            / "raw"
            / args.year
            / f"{args.source_document_id}.worksheet_windows.yaml"
        )
        return seed_windows(
            source_text, tables, lookahead, config, args.max_tokens, cache_path
        )

    if args.window is not None:
        by_id = {table.table_id: index for index, table in enumerate(tables)}
        total_chars = 0
        for anchor in args.anchor:
            if anchor not in by_id:
                print(f"  t{anchor}: not a table in this document")
                continue
            payload, size = call_window(
                tables, by_id[anchor], args.window, config, args.max_tokens
            )
            total_chars += size
            if not payload.get("starts_a_worksheet"):
                print(f"  t{anchor:<4d} -> not a worksheet start ({size} chars)")
                continue
            print(
                f"  t{anchor:<4d} -> {str(payload.get('title'))[:44]:44s} "
                f"tables={payload.get('table_ids')} "
                f"params={payload.get('parameter_table_ids')} "
                f"lines={','.join(payload.get('serves_lines') or []) or '-'} "
                f"({size} chars)"
            )
        print(f"\nwindow payload characters total: {total_chars}")
        return 0

    payload = call_model(prompt, config, args.max_tokens)
    worksheets = payload.get("worksheets") or []
    other = payload.get("not_a_worksheet") or []
    seen: set[int] = set()
    print(f"\nworksheets: {len(worksheets)}")
    for entry in worksheets:
        ids = entry.get("table_ids") or []
        params = entry.get("parameter_table_ids") or []
        seen.update(int(i) for i in ids)
        serves = ",".join(entry.get("serves_lines") or []) or "-"
        print(
            f"  {str(entry.get('title'))[:56]:56s} tables={ids} params={params} lines={serves}"
        )
    seen.update(int(item.get("table_id")) for item in other if item.get("table_id") is not None)
    every = {table.table_id for table in tables}
    print(f"\nnot_a_worksheet: {len(other)}")
    missing = sorted(every - seen)
    extra = sorted(seen - every)
    print(f"accounted: {len(seen)} of {len(every)}; unaccounted={missing}; invented={extra}")

    if args.output:
        Path(args.output).write_text(
            json.dumps(payload, indent=1, sort_keys=True), encoding="ascii"
        )
        print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
