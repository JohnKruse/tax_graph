"""M20-S88 context-arm pilot for model-selected formula derivation.

This module is deliberately outside ``tax_graph/``.  It measures three input
packets against the same model and source rows without changing the production
selector, sectioner, or graph writer:

* A keeps the current line-owned instruction section.
* B adds a line buffer on both sides of that section.
* C uses a fixed raw-text window around the printed line heading and does not
  ask the sectioner for a section.

Every arm admits the same printed-anchor denominator.  The pilot copy of a
row records the production selector decision, but changes that decision only
for the provider call in this experiment.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Mapping, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tax_graph.config import get_config_value, load_config, resolve_llm_model, resolve_llm_seed
from tax_graph.acquire.manifest import load_manifest
from tax_graph.extract.cells import (
    CellFrame,
    CellRecord,
    build_cell_frame_from_document,
    build_reference_inventory,
    derive_cells,
    load_cell_prompt,
)
from tax_graph.extract.inputs import load_document_input
from tax_graph.extract.instruction_sections import InstructionSection
from tax_graph.extract.outline import build_instruction_sections_frame
from tax_graph.extract.llm_client import build_llm_client
from tax_graph.io.loader import load_graph


ARM_NAMES = ("A", "B", "C")
DEFAULT_BUFFER_LINES = 8
DEFAULT_REGION_RADIUS = 12

# This is the fixed scoring set from the S88 handoff.  It is pilot input, not
# graph content, and must not be expanded after seeing the arm results.
KNOWN_MISSED_FORMULAS: tuple[tuple[str, str], ...] = (
    ("form_1040_2025", "6b"),
    ("form_1040_2025", "12e"),
    ("form_1040_2025", "16"),
    ("form_1040_2025", "27a"),
    ("form_1040_2025", "38"),
    ("form_2441_2025", "4"),
    ("form_2441_2025", "18"),
    ("form_6251_2025", "1a"),
    ("form_6251_2025", "1b"),
    ("form_6251_2025", "2c"),
    ("form_6251_2025", "2d"),
    ("form_6251_2025", "2f"),
    ("form_6251_2025", "2g"),
    ("form_6251_2025", "2h"),
    ("form_6251_2025", "2i"),
    ("form_6251_2025", "2k"),
    ("form_6251_2025", "2l"),
    ("form_6251_2025", "2m"),
    ("form_6251_2025", "2n"),
    ("form_6251_2025", "2o"),
    ("form_6251_2025", "2p"),
    ("form_6251_2025", "2q"),
    ("form_6251_2025", "2r"),
    ("form_6251_2025", "2t"),
    ("form_6251_2025", "5"),
    ("form_6251_2025", "7"),
    ("form_6251_2025", "8"),
    ("form_6251_2025", "2"),
    ("form_6251_2025", "10"),
    ("form_6251_2025", "15"),
    ("form_6251_2025", "19"),
    ("form_6251_2025", "25"),
)


@dataclass(frozen=True)
class ContextPacket:
    """One arm's instruction context and its provenance."""

    text: str
    source: str
    span_ids: tuple[str, ...]
    section_count: int
    line_start: int | None = None
    line_end: int | None = None


def build_arm_frame(
    document: Any,
    arm: str,
    *,
    buffer_lines: int = DEFAULT_BUFFER_LINES,
    region_radius: int = DEFAULT_REGION_RADIUS,
) -> tuple[CellFrame, Any, dict[str, Any]]:
    """Build one all-anchor frame and return its canonical section witness.

    The returned frame contains every printed anchor from the production frame,
    including rows the production selector would skip.  Only the copied pilot
    metadata has ``selector_admitted=True``; the production frame is not
    mutated.
    """
    normalized_arm = str(arm).upper()
    if normalized_arm not in ARM_NAMES:
        raise ValueError(f"unknown context arm {arm!r}; expected A, B, or C")
    if buffer_lines < 0 or region_radius < 0:
        raise ValueError("buffer_lines and region_radius must be non-negative")

    production = build_cell_frame_from_document(document)
    outline = None
    instruction_frame = build_instruction_sections_frame(document, outline=outline)
    source = next(
        (
            item
            for item in document.related_sources
            if item.relationship == "instructions"
        ),
        None,
    )
    source_text = source.text if source is not None else ""
    rows: list[CellRecord] = []
    packet_stats: Counter[str] = Counter()

    for original in production.rows:
        row = CellRecord.from_mapping(original.as_dict())
        original_admitted = row.metadata.get("selector_admitted")
        original_reason = row.metadata.get("selector_skip_reason", "")
        packet = _context_packet(
            row,
            normalized_arm,
            instruction_frame=instruction_frame,
            source_text=source_text,
            buffer_lines=buffer_lines,
            region_radius=region_radius,
        )
        metadata = dict(row.metadata)
        metadata.update(
            {
                "selector_admitted": True,
                "selector_skip_reason": "",
                "pilot_original_selector_admitted": original_admitted,
                "pilot_original_selector_skip_reason": original_reason,
                "pilot_arm": normalized_arm,
                "pilot_context_source": packet.source,
                "pilot_context_section_count": packet.section_count,
                "pilot_context_line_start": packet.line_start,
                "pilot_context_line_end": packet.line_end,
            }
        )
        evidence_spans = [
            item
            for item in (metadata.get("evidence_spans") or [])
            if isinstance(item, Mapping)
        ]
        context_span_id = f"pilot_{normalized_arm.lower()}_{_slug(row.form)}_{_slug(row.line)}"
        evidence_spans = [
            {"span_id": str(item.get("span_id") or ""), "text": str(item.get("text") or "")}
            for item in evidence_spans
            if item.get("span_id") and item.get("text")
        ]
        if packet.text:
            evidence_spans.append({"span_id": context_span_id, "text": packet.text})
        metadata["evidence_spans"] = evidence_spans
        metadata["instruction_span_ids"] = list(packet.span_ids)
        metadata["pilot_context_span_id"] = context_span_id if packet.text else ""
        row.metadata = metadata
        row.instruction_text = packet.text
        row.instruction_locator = context_span_id if packet.text else ""
        rows.append(row)
        packet_stats[packet.source] += 1

    return (
        CellFrame(rows),
        instruction_frame,
        {
            "arm": normalized_arm,
            "source_document_id": source.document_id if source is not None else "",
            "anchor_count": len(rows),
            "context_rows_by_source": dict(sorted(packet_stats.items())),
            "buffer_lines": buffer_lines,
            "region_radius": region_radius,
        },
    )


def _context_packet(
    row: CellRecord,
    arm: str,
    *,
    instruction_frame: Any,
    source_text: str,
    buffer_lines: int,
    region_radius: int,
) -> ContextPacket:
    sections = instruction_frame.for_line(row.form, row.line)
    if arm == "A":
        return ContextPacket(
            text=row.instruction_text,
            source="line_section" if row.instruction_text else "none",
            span_ids=tuple(section.section_id for section in sections),
            section_count=len(sections),
        )
    if arm == "B":
        packets = [
            _expanded_section(source_text, section, buffer_lines)
            for section in sections
        ]
        packets = _unique_packets(packets)
        return ContextPacket(
            text="\n\n".join(packet.text for packet in packets),
            source="section_plus_buffer" if packets else "none",
            span_ids=tuple(section.section_id for section in sections),
            section_count=len(sections),
            line_start=min((packet.line_start for packet in packets), default=None),
            line_end=max((packet.line_end for packet in packets), default=None),
        )
    region = _raw_heading_region(
        source_text,
        line=row.line,
        radius=region_radius,
    )
    if region is None:
        return ContextPacket(text="", source="none", span_ids=(), section_count=0)
    return ContextPacket(
        text=region.text,
        source="raw_heading_region",
        span_ids=(),
        section_count=0,
        line_start=region.line_start,
        line_end=region.line_end,
    )


def _expanded_section(source_text: str, section: InstructionSection, radius: int) -> ContextPacket:
    lines = source_text.splitlines(keepends=True)
    if not lines:
        return ContextPacket("", "none", (), 0)
    start_line = max(1, section.locator.start_line - radius)
    end_line = min(len(lines), section.locator.end_line + radius)
    return ContextPacket(
        text="".join(lines[start_line - 1 : end_line]),
        source="section_plus_buffer",
        span_ids=(section.section_id,),
        section_count=1,
        line_start=start_line,
        line_end=end_line,
    )


def _unique_packets(packets: Iterable[ContextPacket]) -> list[ContextPacket]:
    seen: set[str] = set()
    result: list[ContextPacket] = []
    for packet in packets:
        if not packet.text or packet.text in seen:
            continue
        seen.add(packet.text)
        result.append(packet)
    return result


@dataclass(frozen=True)
class _Region:
    text: str
    line_start: int
    line_end: int


def _raw_heading_region(text: str, *, line: str, radius: int) -> _Region | None:
    """Return a fixed raw-text window around a printed line heading."""
    lines = text.splitlines(keepends=True)
    if not lines:
        return None
    token = re.escape(str(line).strip())
    pattern = re.compile(
        rf"^\s*(?:[#*_]+\s*)?Line\s+{token}(?=[A-Za-z\s:;,.()\-]|$)",
        re.IGNORECASE,
    )
    for index, raw in enumerate(lines):
        if not pattern.search(raw.rstrip("\r\n")):
            continue
        start = max(0, index - radius)
        end = min(len(lines), index + radius + 1)
        return _Region("".join(lines[start:end]), start + 1, end)
    return None


def derive_arm(
    frame: CellFrame,
    *,
    prompt: str,
    client: Any,
    model: str,
    provider: str,
    temperature: float | None,
    seed: int | None,
    reference_inventory: Mapping[str, Any],
    max_tokens: int = 4000,
) -> CellFrame:
    """Run the production cell boundary against one pilot frame."""
    result = derive_cells(
        frame,
        prompt,
        None,
        client=client,
        model=model,
        provider=provider,
        temperature=temperature,
        seed=seed,
        max_tokens=max_tokens,
        reference_inventory=reference_inventory,
    )
    if not isinstance(result, CellFrame):
        raise TypeError("derive_cells returned a list for a CellFrame pilot input")
    return result


def score_arm(
    result: CellFrame,
    *,
    instruction_frame: Any,
    baseline_rows: Mapping[tuple[str, str, int], Mapping[str, Any]] | None = None,
    recovery_targets: Sequence[tuple[str, str]] = KNOWN_MISSED_FORMULAS,
) -> dict[str, Any]:
    """Score recovery, regressions, quote ownership, and provider telemetry."""
    rows = [row.as_dict() for row in result.rows]
    indexed = _index_rows(rows)
    successful = {"derived", "repaired"}
    recovery = [
        {
            "document_id": document_id,
            "line": line,
            "status": _first_status(indexed, document_id, line),
            "recovered": _first_status(indexed, document_id, line) in successful,
        }
        for document_id, line in recovery_targets
    ]
    regressions: list[dict[str, Any]] = []
    if baseline_rows:
        for key, baseline in sorted(baseline_rows.items()):
            if str(baseline.get("status") or "") not in successful:
                continue
            current = indexed.get(key)
            if current is None or str(current.get("status") or "") not in successful:
                regressions.append(
                    {
                        "document_id": key[0],
                        "line": key[1],
                        "occurrence": key[2],
                        "baseline_status": baseline.get("status"),
                        "arm_status": current.get("status") if current else "missing",
                        "arm_error": current.get("error") if current else "",
                    }
                )

    ownership = Counter()
    ownership_rows: list[dict[str, Any]] = []
    canonical = _canonical_sections(instruction_frame)
    for row in rows:
        if str(row.get("status") or "") not in successful:
            continue
        owner = _quote_owner(row, canonical)
        ownership[owner] += 1
        ownership_rows.append(
            {
                "document_id": row.get("form"),
                "line": row.get("line"),
                "quote_span_id": row.get("quote_span_id"),
                "quote_owner": owner,
            }
        )

    costs = [row.get("cost") for row in rows if row.get("cost") is not None]
    prompt_tokens = [row.get("prompt_tokens") for row in rows if row.get("prompt_tokens") is not None]
    completion_tokens = [
        row.get("completion_tokens")
        for row in rows
        if row.get("completion_tokens") is not None
    ]
    status_counts = Counter(str(row.get("status") or "") for row in rows)
    return {
        "anchor_count": len(rows),
        "status_counts": dict(sorted(status_counts.items())),
        "recovery": {
            "target_count": len(recovery_targets),
            "recovered_count": sum(item["recovered"] for item in recovery),
            "rows": recovery,
        },
        "regressions": {
            "count": len(regressions),
            "rows": regressions,
        },
        "misattribution": {
            "counts": dict(sorted(ownership.items())),
            "rows": ownership_rows,
        },
        "telemetry": {
            "prompt_tokens": sum(prompt_tokens) if prompt_tokens else None,
            "completion_tokens": sum(completion_tokens) if completion_tokens else None,
            "cost": round(sum(float(value) for value in costs), 8) if costs else None,
        },
        "rows": [
            {
                "document_id": row.get("form"),
                "line": row.get("line"),
                "label": row.get("label"),
                "form_face_text": row.get("form_face_text"),
                "instruction_text": row.get("instruction_text"),
                "instruction_locator": row.get("instruction_locator"),
                "status": row.get("status"),
                "error": row.get("error"),
                "expression": row.get("expression"),
                "rendered": row.get("rendered"),
                "quote": row.get("quote"),
                "quote_span_id": row.get("quote_span_id"),
                "validation_failures": row.get("validation_failures", []),
                "pilot_arm": row.get("pilot_arm"),
                "pilot_original_selector_admitted": row.get("pilot_original_selector_admitted"),
                "pilot_original_selector_skip_reason": row.get("pilot_original_selector_skip_reason"),
                "pilot_context_source": row.get("pilot_context_source"),
                "pilot_context_section_count": row.get("pilot_context_section_count"),
                "pilot_context_line_start": row.get("pilot_context_line_start"),
                "pilot_context_line_end": row.get("pilot_context_line_end"),
                "prompt_tokens": row.get("prompt_tokens"),
                "completion_tokens": row.get("completion_tokens"),
                "cost": row.get("cost"),
            }
            for row in rows
        ],
    }


def _canonical_sections(instruction_frame: Any) -> dict[tuple[str, str], list[str]]:
    result: dict[tuple[str, str], list[str]] = defaultdict(list)
    for section in instruction_frame.sections:
        key = (section.document_id, section.line)
        if section.text not in result[key]:
            result[key].append(section.text)
    return result


def _quote_owner(row: Mapping[str, Any], canonical: Mapping[tuple[str, str], Sequence[str]]) -> str:
    quote = _normalize_text(row.get("quote"))
    if not quote:
        return "unknown"
    form_face = _normalize_text(row.get("form_face_text"))
    if form_face and quote in form_face:
        return "form_face"
    key = (str(row.get("document_id") or row.get("form") or ""), str(row.get("line") or ""))
    if any(quote in _normalize_text(text) for text in canonical.get(key, ())):
        return "correct_line"
    for (document_id, _line), texts in canonical.items():
        if document_id == key[0] and any(quote in _normalize_text(text) for text in texts):
            return "wrong_line"
    return "unknown"


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).lower()


def _index_rows(rows: Iterable[Mapping[str, Any]]) -> dict[tuple[str, str, int], Mapping[str, Any]]:
    counts: Counter[tuple[str, str]] = Counter()
    result: dict[tuple[str, str, int], Mapping[str, Any]] = {}
    for row in rows:
        key = (str(row.get("form") or row.get("document_id") or ""), str(row.get("line") or ""))
        occurrence = counts[key]
        counts[key] += 1
        result[(*key, occurrence)] = row
    return result


def _first_status(indexed: Mapping[tuple[str, str, int], Mapping[str, Any]], document_id: str, line: str) -> str:
    return str(indexed.get((document_id, line, 0), {}).get("status") or "missing")


def load_baseline_rows(paths: Iterable[str | Path]) -> dict[tuple[str, str, int], Mapping[str, Any]]:
    """Load baseline rows from one or more prior derive-cells reports."""
    rows: list[Mapping[str, Any]] = []
    for path_value in paths:
        path = Path(path_value)
        report = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        document_id = str(report.get("document_id") or "")
        for row in report.get("rows_detail") or []:
            if isinstance(row, Mapping):
                rows.append({"form": document_id, **dict(row)})
    return _index_rows(rows)


def find_baseline_reports(paths: Iterable[str | Path]) -> list[Path]:
    """Resolve files or directories into derive-cells report paths."""
    result: list[Path] = []
    for value in paths:
        path = Path(value)
        if path.is_file():
            result.append(path)
        elif path.is_dir():
            result.extend(path.rglob("*_derive_cells_report.yaml"))
    return sorted(set(result))


def run_pilot(
    *,
    root: str | Path,
    year: str,
    output_dir: str | Path,
    document_ids: Sequence[str] | None = None,
    arms: Sequence[str] = ARM_NAMES,
    buffer_lines: int = DEFAULT_BUFFER_LINES,
    region_radius: int = DEFAULT_REGION_RADIUS,
    baseline_paths: Iterable[str | Path] = (),
) -> dict[str, Any]:
    """Run selected arms for every requested document and persist one report."""
    root_path = Path(root).resolve()
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    config = load_config(root=root_path)
    manifest = load_manifest(root=root_path)
    selected_documents = list(document_ids or _default_documents(manifest))
    selected_arms = tuple(str(arm).upper() for arm in arms)
    if not selected_arms or any(arm not in ARM_NAMES for arm in selected_arms):
        raise ValueError("arms must be selected from A, B, and C")

    prompt = load_cell_prompt(config, root=root_path)
    model = resolve_llm_model(config, "micro")
    provider = str(get_config_value(config, "llm.provider", "configured-provider"))
    temperature = _config_temperature(config)
    seed = resolve_llm_seed(config)
    client = build_llm_client(config)
    reference_inventory = build_reference_inventory(
        load_graph(year, root_path),
        manifest=manifest,
    )
    baseline = load_baseline_rows(find_baseline_reports(baseline_paths))
    reports: dict[str, Any] = {}

    for document_id in selected_documents:
        document = load_document_input(document_id, year=year, root=root_path, config=config)
        document_reports: dict[str, Any] = {}
        for arm in selected_arms:
            frame, instruction_frame, context_meta = build_arm_frame(
                document,
                arm,
                buffer_lines=buffer_lines,
                region_radius=region_radius,
            )
            result = derive_arm(
                frame,
                prompt=prompt,
                client=client,
                model=model,
                provider=provider,
                temperature=temperature,
                seed=seed,
                reference_inventory=reference_inventory,
                max_tokens=int(get_config_value(config, "extraction.micro_max_tokens", 4000)),
            )
            document_baseline = {
                key: value
                for key, value in baseline.items()
                if key[0] == document_id
            }
            scored = score_arm(
                result,
                instruction_frame=instruction_frame,
                baseline_rows=document_baseline,
                recovery_targets=[
                    target
                    for target in KNOWN_MISSED_FORMULAS
                    if target[0] == document_id
                ],
            )
            document_reports[arm] = {"context": context_meta, **scored}
        reports[document_id] = document_reports

    summary = {
        arm: {
            "recovery_target_count": sum(
                int(reports[document_id][arm]["recovery"]["target_count"])
                for document_id in selected_documents
            ),
            "recovered_count": sum(
                int(reports[document_id][arm]["recovery"]["recovered_count"])
                for document_id in selected_documents
            ),
            "regression_count": sum(
                int(reports[document_id][arm]["regressions"]["count"])
                for document_id in selected_documents
            ),
            "cost": _sum_optional(
                reports[document_id][arm]["telemetry"].get("cost")
                for document_id in selected_documents
            ),
            "prompt_tokens": _sum_optional(
                reports[document_id][arm]["telemetry"].get("prompt_tokens")
                for document_id in selected_documents
            ),
            "completion_tokens": _sum_optional(
                reports[document_id][arm]["telemetry"].get("completion_tokens")
                for document_id in selected_documents
            ),
        }
        for arm in selected_arms
    }
    report = {
        "schema_version": 1,
        "pilot": "M20-S88",
        "year": str(year),
        "documents": selected_documents,
        "arms": list(selected_arms),
        "model": model,
        "provider": provider,
        "temperature": temperature,
        "seed": seed,
        "buffer_lines": buffer_lines,
        "region_radius": region_radius,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "baseline_reports": [str(path) for path in find_baseline_reports(baseline_paths)],
        "summary": summary,
        "results": reports,
    }
    report_path = output_path / "m20_s88_context_arms.yaml"
    report_path.write_text(
        yaml.safe_dump(report, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
        newline="\n",
    )
    return report


def _default_documents(manifest: Any) -> list[str]:
    return [
        entry.document_id
        for entry in manifest.documents
        if not entry.is_region and entry.kind in {"tax_form", "schedule", "source_document"}
        and entry.document_id in {
            "form_1040_2025",
            "form_2441_2025",
            "form_6251_2025",
        }
    ]


def _config_temperature(config: Mapping[str, Any]) -> float | None:
    value = get_config_value(config, "llm.temperature")
    return None if value is None or value == "" else float(value)


def _sum_optional(values: Iterable[Any]) -> int | float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    total = sum(float(value) for value in present)
    return int(total) if all(float(value).is_integer() for value in present) else round(total, 8)


def _slug(value: Any) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")
    return slug or "value"


def main(argv: Sequence[str] | None = None) -> int:
    """Run the live M20-S88 pilot."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--year", default="2025")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--document", dest="documents", action="append")
    parser.add_argument("--arm", dest="arms", action="append", choices=ARM_NAMES)
    parser.add_argument("--buffer-lines", type=int, default=DEFAULT_BUFFER_LINES)
    parser.add_argument("--region-radius", type=int, default=DEFAULT_REGION_RADIUS)
    parser.add_argument(
        "--baseline",
        dest="baseline_paths",
        action="append",
        default=[],
        help="prior derive-cells report or directory; repeatable",
    )
    args = parser.parse_args(argv)
    report = run_pilot(
        root=args.root,
        year=args.year,
        output_dir=args.output,
        document_ids=args.documents,
        arms=args.arms or ARM_NAMES,
        buffer_lines=args.buffer_lines,
        region_radius=args.region_radius,
        baseline_paths=args.baseline_paths,
    )
    for document_id in report["documents"]:
        for arm in report["arms"]:
            result = report["results"][document_id][arm]
            recovery = result["recovery"]
            print(
                f"{document_id} arm {arm}: "
                f"recovered {recovery['recovered_count']}/{recovery['target_count']}, "
                f"regressions {result['regressions']['count']}, "
                f"cost {result['telemetry']['cost']}"
            )
    for arm in report["arms"]:
        summary = report["summary"][arm]
        print(
            f"summary arm {arm}: recovered {summary['recovered_count']}/"
            f"{summary['recovery_target_count']}, regressions {summary['regression_count']}, "
            f"cost {summary['cost']}"
        )
    print(f"report written to {args.output / 'm20_s88_context_arms.yaml'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
