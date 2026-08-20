"""Run M20-S158 fixed-span instruction attribution as a scratch pilot.

The source frame and its byte boundaries are deterministic inputs. The model
only labels each existing span with zero or more printed line tokens from a
closed form inventory. No body-prose line-reference miner, graph write, or
draft promotion belongs in this stage.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pilot.html_document_frame_m20_s132 import parse_html_document_frame
from pilot.html_section_frame_m20_s128 import _visible_text
from tax_graph.acquire.manifest import load_manifest
from tax_graph.config import (
    get_config_value,
    load_config,
    resolve_llm_model,
    resolve_llm_seed,
)
from tax_graph.extract.cells import build_cell_frame_from_document
from tax_graph.extract.inputs import load_document_input
from tax_graph.extract.llm_client import build_llm_client, response_telemetry


ROUND = "M20-S158"
DEFAULT_DOCUMENTS = ("schedule_1a_2025", "form_1116_2025")
ATTRIBUTION_MAX_TOKENS = 24000
SCHEDULE_1A_GOVERNING_LINES = frozenset(
    {
        "1",
        "2a",
        "2b",
        "2c",
        "2d",
        "2e",
        "3",
        "4",
        "7",
        "9",
        "15",
        "17",
        "26",
        "32",
        "33",
        "34",
        "35",
        "36a",
        "36b",
    }
)
SCHEDULE_1A_CEILING_LINES = frozenset(
    {
        "6",
        "8",
        "11",
        "12",
        "13",
        "14c",
        "16",
        "19",
        "20",
        "21",
        "23",
        "25",
        "28",
        "29",
        "30",
        "31",
        "37",
        "38",
    }
)
SCHEDULE_1A_NONE_FLOOR = 50


@dataclass(frozen=True)
class FixedSpan:
    """One source-backed span whose boundaries this stage must preserve."""

    span_id: str
    heading: str
    line_tokens: tuple[str, ...]
    start_offset: int
    end_offset: int
    source_text: str

    @property
    def visible_text(self) -> str:
        """Return visible source text for the model and scratch report."""
        return _visible_text(self.source_text)

    def as_prompt_record(self, *, max_text: int = 1800) -> dict[str, Any]:
        """Return bounded evidence without modifying the source span."""
        text = self.visible_text
        if len(text) > max_text:
            text = text[:max_text] + " [text shortened for prompt]"
        return {
            "span_id": self.span_id,
            "heading": self.heading,
            "existing_line_tokens": list(self.line_tokens),
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "text": text,
        }

    def as_report_record(self, governs: Sequence[str]) -> dict[str, Any]:
        """Return the attribution and the source witness for a scratch report."""
        return {
            "span_id": self.span_id,
            "heading": self.heading,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "source_sha256": hashlib.sha256(self.source_text.encode("utf-8")).hexdigest(),
            "text": self.visible_text,
            "governs": list(governs),
        }


def line_inventory(document: Any) -> tuple[str, ...]:
    """Return unique printed anchors from the existing form frame.

    This function reads the deterministic form-face frame only. It never reads
    instruction prose and never asks a model to discover line tokens.
    """
    frame = build_cell_frame_from_document(document)
    return tuple(dict.fromkeys(str(row.line).lower() for row in frame.rows if row.line))


def line_inventory_details(document: Any) -> tuple[dict[str, str], ...]:
    """Return printed anchors with their existing form-face wording."""
    frame = build_cell_frame_from_document(document)
    details: dict[str, dict[str, str]] = {}
    for row in frame.rows:
        token = str(row.line or "").lower()
        if token and token not in details:
            details[token] = {
                "line": token,
                "form_face": str(row.form_face_text or row.label or ""),
            }
    return tuple(details.values())


def fixed_spans(
    document_id: str,
    *,
    year: str = "2025",
    root: str | Path = ROOT,
) -> tuple[FixedSpan, ...]:
    """Load accepted HTML spans and verify each source slice before labeling."""
    root_path = Path(root).resolve()
    manifest = load_manifest(root=root_path)
    entry = manifest.by_document_id()[document_id]
    booklet_id = entry.instructions_document_id
    if not booklet_id:
        raise ValueError(f"{document_id} has no instruction booklet")
    html_path = root_path / ".cache" / "raw" / str(year) / f"{booklet_id}.html"
    source_text = html_path.read_text(encoding="utf-8")
    frame = parse_html_document_frame(
        source_text,
        source_document_id=booklet_id,
        root=root_path,
    )
    required_invariants = (
        "sections_tile_content",
        "section_offsets_valid",
        "section_source_resolves",
        "sections_nonempty",
    )
    if not all(frame.structural_invariants.get(key) is True for key in required_invariants):
        raise ValueError(f"fixed frame failed byte invariants for {document_id}")
    result: list[FixedSpan] = []
    for section in frame.sections:
        if section.owner_document_id != document_id or section.rejected:
            continue
        start = int(section.start_offset)
        end = int(section.end_offset)
        if source_text.encode("utf-8")[start:end].decode("utf-8") != section.source_text:
            raise ValueError(f"fixed span does not resolve for {section.section_id}")
        result.append(
            FixedSpan(
                span_id=section.section_id,
                heading=section.heading,
                line_tokens=tuple(section.line_tokens),
                start_offset=start,
                end_offset=end,
                source_text=section.source_text,
            )
        )
    return tuple(result)


def attribution_schema(
    *,
    span_ids: Iterable[str],
    line_tokens: Iterable[str],
) -> dict[str, Any]:
    """Return a closed structured-output schema for fixed-span labels."""
    spans = tuple(span_ids)
    lines = tuple(line_tokens)
    item = {
        "type": "object",
        "additionalProperties": False,
        "required": ["span_id", "governs"],
        "properties": {
            "span_id": {"type": "string", "enum": list(spans)},
            "governs": {
                "type": "array",
                "items": {"type": "string", "enum": list(lines)},
            },
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["attributions"],
        "properties": {
            "attributions": {
                "type": "array",
                "minItems": len(spans),
                "maxItems": len(spans),
                "items": item,
            }
        },
    }


def build_attribution_prompt(
    document_id: str,
    spans: Sequence[FixedSpan],
    line_tokens: Sequence[str],
    *,
    line_details: Sequence[Mapping[str, str]] | None = None,
    template: str | None = None,
) -> str:
    """Render the closed inventory and fixed-span evidence into one prompt."""
    instructions = template or (
        Path(ROOT / "prompts" / "instruction_attribution_m20_s158.md")
        .read_text(encoding="ascii")
    )
    inventory_payload = list(line_details or ({"line": line} for line in line_tokens))
    payload = {
        "document_id": document_id,
        "line_inventory": inventory_payload,
        "spans": [span.as_prompt_record() for span in spans],
    }
    token_list = ""
    if line_details is None:
        token_list = (
            "Closed line token list (the only allowed answer values):\n"
            f"{json.dumps(list(line_tokens), separators=(',', ':'))}\n"
        )
    return (
        f"{instructions.rstrip()}\n\n"
        f"Form document_id: {document_id}\n"
        "Closed printed line inventory (the line field is the only allowed answer token):\n"
        f"{json.dumps(inventory_payload, ensure_ascii=True, separators=(',', ':'))}\n"
        f"{token_list}"
        "Fixed spans and their source evidence:\n"
        f"{json.dumps(payload['spans'], ensure_ascii=True, separators=(',', ':'))}\n"
        "Return one attribution record per span.\n"
    )


def validate_attributions(
    response: Mapping[str, Any],
    *,
    spans: Sequence[FixedSpan],
    line_tokens: Sequence[str],
) -> dict[str, tuple[str, ...]]:
    """Fail closed on missing, duplicate, or out-of-inventory labels."""
    records = response.get("attributions")
    if not isinstance(records, list):
        raise ValueError("attributions must be a list")
    expected = tuple(span.span_id for span in spans)
    expected_set = set(expected)
    line_set = set(line_tokens)
    result: dict[str, tuple[str, ...]] = {}
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("each attribution must be an object")
        span_id = str(record.get("span_id") or "")
        if span_id not in expected_set:
            raise ValueError(f"unknown span_id in attribution: {span_id}")
        if span_id in result:
            raise ValueError(f"duplicate attribution for {span_id}")
        governs = record.get("governs")
        if not isinstance(governs, list):
            raise ValueError(f"governs must be a list for {span_id}")
        values = tuple(str(value).lower() for value in governs)
        if len(values) != len(set(values)):
            raise ValueError(f"duplicate line token for {span_id}")
        unknown = sorted(set(values) - line_set)
        if unknown:
            raise ValueError(f"unknown line tokens for {span_id}: {unknown}")
        result[span_id] = values
    if set(result) != expected_set or len(records) != len(expected):
        missing = sorted(expected_set - set(result))
        raise ValueError(f"attributions must cover every fixed span; missing={missing}")
    return {span_id: result[span_id] for span_id in expected}


def score_attributions(
    document_id: str,
    *,
    spans: Sequence[FixedSpan],
    labels: Mapping[str, Sequence[str]],
    line_tokens: Sequence[str],
    before_instruction_lines: Iterable[str],
    reference_lines: Iterable[str] = (),
    ceiling_lines: Iterable[str] = (),
) -> dict[str, Any]:
    """Report none-rate, zero-cell movement, and optional Schedule 1-A score."""
    inventory = set(line_tokens)
    attributed = {
        line
        for span in spans
        for line in labels.get(span.span_id, ())
        if line in inventory
    }
    before = {str(line).lower() for line in before_instruction_lines}
    zero_before = sorted(inventory - before)
    zero_after = sorted(inventory - attributed)
    none_count = sum(not labels.get(span.span_id, ()) for span in spans)
    report: dict[str, Any] = {
        "document_id": document_id,
        "span_count": len(spans),
        "none_count": none_count,
        "none_rate": round(none_count / len(spans), 6) if spans else 1.0,
        "attributed_line_count": len(attributed),
        "attributed_lines": sorted(attributed),
        "line_inventory_count": len(inventory),
        "zero_instruction_cells_before": len(zero_before),
        "zero_instruction_cells_after": len(zero_after),
        "zero_instruction_lines_before": zero_before,
        "zero_instruction_lines_after": zero_after,
    }
    references = {str(line).lower() for line in reference_lines}
    ceiling = {str(line).lower() for line in ceiling_lines}
    if references:
        reached = references & attributed
        report["schedule_1a_score"] = {
            "reference_count": len(references),
            "reached_count": len(reached),
            "reached_lines": sorted(reached),
            "missed_reference_lines": sorted(references - attributed),
            "ceiling_count_excluded": len(ceiling),
            "ceiling_lines_reached": sorted(ceiling & attributed),
            "denominator": len(references),
        }
        report["constraint_3"] = {
            "required_none_count": SCHEDULE_1A_NONE_FLOOR,
            "none_count": none_count,
            "passed": none_count >= SCHEDULE_1A_NONE_FLOOR,
        }
    return report


def before_instruction_lines(document: Any) -> tuple[str, ...]:
    """Read the existing deterministic join for the before measurement."""
    frame = build_cell_frame_from_document(document)
    return tuple(
        dict.fromkeys(
            str(row.line).lower()
            for row in frame.rows
            if row.line and row.metadata.get("instruction_span_ids")
        )
    )


def run_document(
    document_id: str,
    *,
    root: str | Path = ROOT,
    year: str = "2025",
    client: Any | None = None,
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Call the configured model once for one document and score the result."""
    root_path = Path(root).resolve()
    settings = dict(config or load_config(root=root_path))
    document = load_document_input(document_id, year=year, root=root_path, config=settings)
    spans = fixed_spans(document_id, year=year, root=root_path)
    inventory = line_inventory(document)
    prompt = build_attribution_prompt(
        document_id,
        spans,
        inventory,
        line_details=line_inventory_details(document),
    )
    schema = attribution_schema(
        span_ids=(span.span_id for span in spans),
        line_tokens=inventory,
    )
    model_client = client or build_llm_client(settings)
    request: dict[str, Any] = {
        "prompt": prompt,
        "schema": schema,
        "model": resolve_llm_model(settings, "micro"),
        "max_tokens": ATTRIBUTION_MAX_TOKENS,
        "temperature": get_config_value(settings, "llm.temperature"),
        "purpose": "tax_graph_m20_s158_instruction_attribution",
    }
    seed = resolve_llm_seed(settings)
    if seed is not None:
        request["seed"] = seed
    response = model_client.structured_completion(**request)
    labels = validate_attributions(response, spans=spans, line_tokens=inventory)
    before = before_instruction_lines(document)
    score = score_attributions(
        document_id,
        spans=spans,
        labels=labels,
        line_tokens=inventory,
        before_instruction_lines=before,
        reference_lines=(
            SCHEDULE_1A_GOVERNING_LINES if document_id == "schedule_1a_2025" else ()
        ),
        ceiling_lines=(
            SCHEDULE_1A_CEILING_LINES if document_id == "schedule_1a_2025" else ()
        ),
    )
    metadata = response_telemetry(response)
    score["telemetry"] = {
        "prompt_tokens": getattr(metadata, "prompt_tokens", None),
        "completion_tokens": getattr(metadata, "completion_tokens", None),
        "total_tokens": getattr(metadata, "total_tokens", None),
        "cost": getattr(metadata, "cost", None),
        "resolved_model": getattr(metadata, "resolved_model", None),
        "resolved_provider": getattr(metadata, "resolved_provider", None),
    }
    score["prompt_sha256"] = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    score["spans"] = [span.as_report_record(labels[span.span_id]) for span in spans]
    return score


def run_documents(
    document_ids: Sequence[str] = DEFAULT_DOCUMENTS,
    *,
    root: str | Path = ROOT,
    output: str | Path,
    year: str = "2025",
) -> dict[str, Any]:
    """Run at most two documents and write only the scratch report."""
    selected = tuple(document_ids)
    if len(selected) > 2:
        raise ValueError("M20-S158 permits at most two documents")
    if selected and selected[0] != "schedule_1a_2025":
        raise ValueError("schedule_1a_2025 must be the first live document")
    root_path = Path(root).resolve()
    output_path = Path(output).resolve()
    try:
        output_path.relative_to(root_path)
    except ValueError:
        pass
    else:
        raise ValueError("M20-S158 output must be outside the repository root")
    reports = [run_document(document_id, root=root, year=year) for document_id in selected]
    costs = [
        item["telemetry"]["cost"]
        for item in reports
        if item["telemetry"].get("cost") is not None
    ]
    result = {
        "round": ROUND,
        "documents": list(selected),
        "call_count": len(reports),
        "cost": round(sum(float(value) for value in costs), 8) if costs else None,
        "reports": {item["document_id"]: item for item in reports},
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="ascii",
        newline="\n",
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    """Run the two-document live attribution pilot."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--year", default="2025")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--document", dest="documents", action="append")
    args = parser.parse_args(argv)
    documents = tuple(args.documents or DEFAULT_DOCUMENTS)
    report = run_documents(documents, root=args.root, output=args.output, year=args.year)
    print(f"M20-S158: calls={report['call_count']} cost={report['cost']}")
    for document_id in report["documents"]:
        item = report["reports"][document_id]
        print(
            f"{document_id}: spans={item['span_count']} none={item['none_count']}/"
            f"{item['span_count']} ({item['none_rate']:.2%}), zero="
            f"{item['zero_instruction_cells_before']} -> "
            f"{item['zero_instruction_cells_after']}"
        )
        if "schedule_1a_score" in item:
            score = item["schedule_1a_score"]
            print(
                f"schedule_1a reached={score['reached_count']}/"
                f"{score['denominator']} ceiling_excluded={score['ceiling_count_excluded']}"
            )
    print(f"report written to {Path(args.output).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
