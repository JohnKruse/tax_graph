"""Mine and replay IRS worked examples."""

from __future__ import annotations

from dataclasses import dataclass
import datetime as _dt
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

import yaml

from tax_graph.config import get_config_value
from tax_graph.engine import Engine, Graph, load_facts
from tax_graph.extract.inputs import load_document_input
from tax_graph.extract.llm_client import LlmClient, build_llm_client


@dataclass(frozen=True)
class ExampleBlock:
    """One deterministic source text block headed by an IRS example label."""

    example_id: str
    source_document_id: str
    ordinal: int
    text: str
    locator: str


@dataclass(frozen=True)
class MinedExample:
    """A mined worked-example candidate and its execution status."""

    block: ExampleBlock
    facts_document: dict[str, Any]
    expected: dict[str, Any]
    status: str
    mismatches: tuple[str, ...] = ()
    output_dir: Path | None = None
    review_queue_path: Path | None = None

    @property
    def ok(self) -> bool:
        """Return whether the example executed to the expected values."""
        return self.status == "agreed"


@dataclass(frozen=True)
class ExampleMiningReport:
    """Summary of one worked-example mining run."""

    document_id: str
    examples: tuple[MinedExample, ...]

    @property
    def agreed(self) -> int:
        """Return the number of agreed mined examples."""
        return sum(1 for example in self.examples if example.status == "agreed")

    @property
    def disagreed(self) -> int:
        """Return the number of examples whose expected values disagreed."""
        return sum(1 for example in self.examples if example.status == "disagreed")

    @property
    def unmappable(self) -> int:
        """Return the number of examples the miner could not map."""
        return sum(1 for example in self.examples if example.status == "unmappable")


@dataclass(frozen=True)
class ExampleReplayIssue:
    """One failed frozen example assertion."""

    example_id: str
    node_id: str
    expected: Any
    actual: Any


@dataclass(frozen=True)
class ExampleReplayReport:
    """Result of replaying frozen IRS example fixtures."""

    example_count: int
    issues: tuple[ExampleReplayIssue, ...]

    @property
    def ok(self) -> bool:
        """Return whether every frozen example matched."""
        return not self.issues


def segment_example_blocks(
    text: str,
    *,
    source_document_id: str,
) -> list[ExampleBlock]:
    """Segment rendered instruction text into worked-example blocks."""
    starts = list(_EXAMPLE_HEADING_RE.finditer(text))
    blocks: list[ExampleBlock] = []
    for index, match in enumerate(starts):
        start = match.start()
        next_start = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        heading_after = _NEXT_HEADING_RE.search(text, match.end(), next_start)
        end = heading_after.start() if heading_after else next_start
        block_text = text[start:end].strip()
        if not block_text:
            continue
        ordinal = len(blocks) + 1
        blocks.append(
            ExampleBlock(
                example_id=f"example_{ordinal:03d}",
                source_document_id=source_document_id,
                ordinal=ordinal,
                text=block_text,
                locator=f"{source_document_id} example {ordinal}",
            )
        )
    return blocks


def mine_examples(
    *,
    document_id: str,
    year: str | int = "2025",
    root: str | Path | None = None,
    client: LlmClient | None = None,
    config: dict[str, Any] | None = None,
    output_dir: str | Path | None = None,
    confirm: bool = False,
    freeze_agreed: bool = False,
    freeze_date: str | None = None,
    limit: int | None = None,
    source: str | None = None,
) -> ExampleMiningReport:
    """Mine worked examples for one rendered document and optionally freeze them."""
    if confirm and freeze_agreed:
        raise ValueError("choose either confirm or freeze_agreed, not both")
    root_path = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[2]
    settings = config or {}
    llm_client = client or build_llm_client(settings)
    document = load_document_input(document_id, year=year, root=root_path, config=settings or None)
    source_texts = [(document.document_id, document.text)]
    source_texts.extend((related.document_id, related.text) for related in document.related_sources)
    graph = Graph(year, root=root_path, source=source)
    model = _example_model(settings)
    examples: list[MinedExample] = []
    for source_document_id, text in source_texts:
        for block in segment_example_blocks(text, source_document_id=source_document_id):
            if limit is not None and len(examples) >= limit:
                break
            mined = _mine_block(block, client=llm_client, graph=graph, model=model)
            if confirm and mined.status == "agreed":
                mined = _freeze_mined_example(
                    mined,
                    output_dir=_examples_dir(root_path, output_dir),
                    root=root_path,
                    year=year,
                    freeze_date=freeze_date,
                    human_confirmed=True,
                )
            elif freeze_agreed and mined.status == "agreed":
                mined = _freeze_mined_example(
                    mined,
                    output_dir=_examples_dir(root_path, output_dir),
                    root=root_path,
                    year=year,
                    freeze_date=freeze_date,
                    human_confirmed=False,
                )
            examples.append(mined)
        if limit is not None and len(examples) >= limit:
            break
    return ExampleMiningReport(document_id=document_id, examples=tuple(examples))


def replay_irs_examples(
    *,
    year: str | int = "2025",
    root: str | Path | None = None,
    examples_dir: str | Path | None = None,
    source: str | None = None,
) -> ExampleReplayReport:
    """Replay frozen IRS worked examples through the engine."""
    root_path = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[2]
    base_dir = _examples_dir(root_path, examples_dir)
    graph = Graph(year, root=root_path, source=source)
    issues: list[ExampleReplayIssue] = []
    example_count = 0
    for facts_path in sorted(base_dir.glob("*/*/facts.yaml")):
        example_count += 1
        example_dir = facts_path.parent
        expected_doc = _load_yaml(example_dir / "expected.yaml")
        expected = expected_doc.get("expected", {})
        result = Engine(graph).execute(load_facts(facts_path))
        for node_id, expected_value in expected.items():
            actual = result.values.get(node_id)
            if actual != expected_value:
                issues.append(
                    ExampleReplayIssue(
                        example_id=example_dir.name,
                        node_id=node_id,
                        expected=expected_value,
                        actual=actual,
                    )
                )
    return ExampleReplayReport(example_count=example_count, issues=tuple(issues))


def _mine_block(block: ExampleBlock, *, client: LlmClient, graph: Graph, model: str) -> MinedExample:
    try:
        response = client.structured_completion(
            prompt=_example_prompt(block, graph=graph),
            schema=_example_schema(),
            model=model,
            max_tokens=2000,
            temperature=0,
            purpose="tax_graph_example_miner",
        )
    except Exception as exc:
        return MinedExample(
            block,
            {},
            {},
            status="unmappable",
            mismatches=(f"example miner unavailable: {exc}",),
        )
    facts_document, expected = _normalize_mined_payload(
        response.get("facts", {}),
        response.get("expected", {}),
        graph=graph,
        block=block,
    )
    if not expected:
        return MinedExample(block, facts_document, expected, status="unmappable", mismatches=("no expected values",))
    result = Engine(graph).execute(_facts_from_document(facts_document))
    mismatches = tuple(_expected_mismatches(expected, result.values))
    status = "agreed" if not mismatches else "disagreed"
    return MinedExample(block, facts_document, expected, status=status, mismatches=mismatches)


def _freeze_mined_example(
    mined: MinedExample,
    *,
    output_dir: Path,
    root: Path,
    year: str | int,
    freeze_date: str | None,
    human_confirmed: bool,
) -> MinedExample:
    example_dir = output_dir / mined.block.source_document_id / mined.block.example_id
    example_dir.mkdir(parents=True, exist_ok=True)
    recorded_date = freeze_date or _dt.date.today().isoformat()
    _write_yaml(example_dir / "facts.yaml", mined.facts_document)
    _write_yaml(
        example_dir / "expected.yaml",
        {
            "example_id": mined.block.example_id,
            "source_document_id": mined.block.source_document_id,
            "confirmed": human_confirmed,
            "machine_agreed": True,
            "review_status": "confirmed" if human_confirmed else "pending_human_review",
            "expected": mined.expected,
        },
    )
    _write_yaml(
        example_dir / "provenance.yaml",
        {
            "example_id": mined.block.example_id,
            "source_document_id": mined.block.source_document_id,
            "locator": mined.block.locator,
            "quoted_text": mined.block.text,
            "human_confirmed": human_confirmed,
            "machine_agreed": True,
            "review_status": "confirmed" if human_confirmed else "pending_human_review",
            "machine_agreed_basis": "engine_replay_matched_expected",
            "recorded_date": recorded_date,
        },
    )
    review_queue_path = None
    if not human_confirmed:
        review_queue_path = _append_deferred_review_queue_entry(
            root=root,
            year=year,
            mined=mined,
            example_dir=example_dir,
            recorded_date=recorded_date,
        )
    return MinedExample(
        block=mined.block,
        facts_document=mined.facts_document,
        expected=mined.expected,
        status=mined.status,
        mismatches=mined.mismatches,
        output_dir=example_dir,
        review_queue_path=review_queue_path,
    )


def _expected_mismatches(expected: Mapping[str, Any], actual_values: Mapping[str, Any]) -> list[str]:
    mismatches: list[str] = []
    for node_id, expected_value in expected.items():
        actual = actual_values.get(node_id)
        if actual != expected_value:
            mismatches.append(f"{node_id}: got {actual}, want {expected_value}")
    return mismatches


def _normalize_mined_payload(
    facts: Mapping[str, Any],
    expected: Mapping[str, Any] | None,
    *,
    graph: Graph,
    block: ExampleBlock,
) -> tuple[dict[str, Any], dict[str, Any]]:
    facts_document = _normalize_facts_document(facts)
    normalized_expected = dict(expected or {})
    facts_document = _maybe_add_example_table(facts_document, normalized_expected, graph=graph, block=block)
    normalized_expected = _normalize_expected_runtime_ids(normalized_expected, facts_document, graph=graph)
    return facts_document, normalized_expected


def _normalize_facts_document(facts: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(facts)
    normalized.setdefault("facts", [])
    normalized.setdefault("tables", [])
    return normalized


def _maybe_add_example_table(
    facts_document: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    graph: Graph,
    block: ExampleBlock,
) -> dict[str, Any]:
    normalized = dict(facts_document)
    if normalized.get("tables"):
        return normalized
    table_id = _infer_example_table_id(normalized, expected, graph=graph)
    row_key = _infer_example_row_key(normalized, block=block)
    columns = _infer_example_columns(normalized)
    if not table_id or not row_key or not columns:
        return normalized
    columns.setdefault("g", 0)
    normalized["tables"] = [
        {
            "table_id": table_id,
            "rows": [{"row_key": row_key, "columns": columns}],
        }
    ]
    return normalized


def _infer_example_table_id(
    facts_document: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    graph: Graph,
) -> str | None:
    explicit = facts_document.get("table_id")
    if explicit:
        return str(explicit)
    table_counts: dict[str, int] = {}
    for node_id in expected:
        base_node_id = str(node_id).partition("#")[0]
        table_id = graph.nodes.get(base_node_id, {}).get("table_id")
        if table_id:
            table_counts[str(table_id)] = table_counts.get(str(table_id), 0) + 1
    if table_counts:
        return sorted(table_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    form = _digits_only(facts_document.get("form") or facts_document.get("tax_form"))
    part = _normalize_part_token(facts_document.get("part"))
    line = _normalize_line_token(facts_document.get("line"))
    if form and part and line:
        candidate = f"form_{form}_{graph.year}_part_{part}_line_{line}"
        if candidate in graph.tables:
            return candidate
    return None


def _infer_example_row_key(facts_document: Mapping[str, Any], *, block: ExampleBlock) -> str:
    if facts_document.get("row_key"):
        return _slug_token(facts_document["row_key"])
    if facts_document.get("scenario"):
        return _slug_token(f"{block.example_id}_{facts_document['scenario']}")
    if facts_document.get("example_id"):
        return _slug_token(facts_document["example_id"])
    return _slug_token(block.example_id)


def _infer_example_columns(facts_document: Mapping[str, Any]) -> dict[str, Any]:
    columns: dict[str, Any] = {}
    for raw_inputs in (facts_document.get("inputs"), facts_document.get("given_values")):
        if isinstance(raw_inputs, Mapping):
            for key, value in raw_inputs.items():
                column_id = _normalize_column_token(key)
                if column_id:
                    columns[column_id] = value
    for key, value in facts_document.items():
        column_id = _normalize_column_token(key)
        if column_id and column_id not in columns:
            columns[column_id] = value
    return columns


def _normalize_expected_runtime_ids(
    expected: Mapping[str, Any],
    facts_document: Mapping[str, Any],
    *,
    graph: Graph,
) -> dict[str, Any]:
    row_keys_by_table = _table_row_keys(facts_document)
    normalized: dict[str, Any] = {}
    for node_id, value in expected.items():
        key = str(node_id)
        if "#" in key:
            normalized[key] = value
            continue
        node = graph.nodes.get(key, {})
        table_id = node.get("table_id")
        if node.get("role") == "row_template" and table_id:
            row_keys = row_keys_by_table.get(str(table_id), [])
            if len(row_keys) == 1:
                key = f"{key}#{row_keys[0]}"
        normalized[key] = value
    return normalized


def _table_row_keys(facts_document: Mapping[str, Any]) -> dict[str, list[str]]:
    row_keys_by_table: dict[str, list[str]] = {}
    for table in facts_document.get("tables", []) or []:
        table_id = table.get("table_id")
        if not table_id:
            continue
        row_keys_by_table[str(table_id)] = [
            str(row.get("row_key"))
            for row in table.get("rows", []) or []
            if row.get("row_key") is not None
        ]
    return row_keys_by_table


def _normalize_column_token(value: Any) -> str | None:
    if value is None:
        return None
    token = str(value).strip().lower()
    if token.startswith("column_"):
        token = token[7:]
    aliases = {
        "proceeds": "d",
        "basis": "e",
        "cost_or_other_basis": "e",
        "adjustment": "g",
        "adjustment_amount": "g",
        "ordinary_loss_claimed_on_form_4797": "g",
    }
    token = aliases.get(token, token)
    if token in {"d", "e", "g"}:
        return token
    return None


def _normalize_part_token(value: Any) -> str | None:
    if value is None:
        return None
    token = re.sub(r"[^a-z0-9]", "", str(value).strip().lower())
    if token in {"1", "i", "parti"}:
        return "i"
    if token in {"2", "ii", "partii"}:
        return "ii"
    return None


def _normalize_line_token(value: Any) -> str | None:
    if value is None:
        return None
    token = str(value).strip().lower()
    match = re.search(r"[0-9]+[a-z]?", token)
    return match.group(0) if match else None


def _digits_only(value: Any) -> str:
    return re.sub(r"[^0-9]", "", str(value or ""))


def _slug_token(value: Any) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower())
    return text.strip("_") or "example"


def _facts_from_document(facts_document: Mapping[str, Any]) -> dict[str, Any]:
    facts = {fact["node_id"]: fact["value"] for fact in facts_document.get("facts", []) or []}
    if facts_document.get("filing_status"):
        facts["taxpayer_2025_filing_status"] = facts_document["filing_status"]
    if facts_document.get("tables"):
        facts["#tables"] = list(facts_document["tables"])
    return facts


def _example_model(settings: Mapping[str, Any]) -> str:
    config = dict(settings)
    model = (
        get_config_value(config, "llm.example_model")
        or get_config_value(config, "llm.micro_model")
        or get_config_value(config, "llm.model")
        or get_config_value(config, "llm.nversion_model")
    )
    return str(model or "configured-llm")


def _example_prompt(block: ExampleBlock, *, graph: Graph) -> str:
    candidate_nodes = "\n".join(f"- {node_id}" for node_id in sorted(graph.nodes))
    return "\n".join(
        [
            "Extract this IRS worked example into Tax Graph facts and expected node values.",
            "Return schema fields: facts, expected, notes.",
            "Only use expected keys that are real Tax Graph node ids or runtime table-instance ids of the form <node_id>#<row_key>.",
            "If the example is outside the currently modeled graph scope, leave expected empty and explain why in notes.",
            "Use table row_key values that are stable lowercase ids.",
            "Current in-scope static node ids:",
            candidate_nodes,
            "",
            block.text,
        ]
    )


def _example_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": True,
        "properties": {
            "facts": {"type": "object"},
            "expected": {"type": "object"},
            "notes": {"type": "string"},
        },
        "required": ["facts", "expected"],
    }


def _examples_dir(root: Path, output_dir: str | Path | None) -> Path:
    if output_dir is None:
        return root / "examples" / "irs_examples"
    path = Path(output_dir)
    return path if path.is_absolute() else root / path


def _append_deferred_review_queue_entry(
    *,
    root: Path,
    year: str | int,
    mined: MinedExample,
    example_dir: Path,
    recorded_date: str,
) -> Path:
    queue_path = root / "review_queue" / str(year) / "deferred_review.yaml"
    payload = _load_yaml(queue_path)
    if not isinstance(payload, dict):
        payload = {}
    entries = payload.get("entries")
    if not isinstance(entries, list):
        entries = []
    queue_id = f"irs_example_review_{mined.block.source_document_id}_{mined.block.example_id}"
    entry = {
        "queue_id": queue_id,
        "kind": "irs_example_review",
        "status": "pending",
        "priority": "medium",
        "document_id": _review_document_id(mined),
        "source_document_id": mined.block.source_document_id,
        "example_id": mined.block.example_id,
        "created_date": recorded_date,
        "created_by": "tax_graph.verify.examples",
        "summary": (
            f"Review machine-agreed IRS example freeze for "
            f"{mined.block.source_document_id} {mined.block.example_id}"
        ),
        "artifact_dir": str(example_dir.relative_to(root)).replace("\\", "/"),
        "machine_agreed": True,
        "human_confirmed": False,
        "expected_nodes": sorted(str(node_id) for node_id in mined.expected),
    }
    updated_entries = [item for item in entries if isinstance(item, dict) and item.get("queue_id") != queue_id]
    updated_entries.append(entry)
    updated_entries.sort(key=lambda item: str(item.get("queue_id") or ""))
    _write_yaml(
        queue_path,
        {
            "tax_year": int(year),
            "entries": updated_entries,
        },
    )
    return queue_path


def _review_document_id(mined: MinedExample) -> str:
    document_id = mined.block.source_document_id
    if document_id.startswith("instructions_"):
        return document_id.removeprefix("instructions_")
    return document_id


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=False), encoding="utf-8", newline="\n")


_EXAMPLE_HEADING_RE = re.compile(r"(?m)^(?:\*\*)?Example\b[^.\n]*\.(?:\*\*)?")
_NEXT_HEADING_RE = re.compile(r"(?m)^#{1,6}\s+")
