"""Mine and replay IRS worked examples."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

import yaml

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
    limit: int | None = None,
    source: str | None = None,
) -> ExampleMiningReport:
    """Mine worked examples for one rendered document and optionally freeze them."""
    root_path = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[2]
    settings = config or {}
    llm_client = client or build_llm_client(settings)
    document = load_document_input(document_id, year=year, root=root_path, config=settings or None)
    source_texts = [(document.document_id, document.text)]
    source_texts.extend((related.document_id, related.text) for related in document.related_sources)
    graph = Graph(year, root=root_path, source=source)
    examples: list[MinedExample] = []
    for source_document_id, text in source_texts:
        for block in segment_example_blocks(text, source_document_id=source_document_id):
            if limit is not None and len(examples) >= limit:
                break
            mined = _mine_block(block, client=llm_client, graph=graph)
            if confirm and mined.status == "agreed":
                mined = _freeze_mined_example(mined, output_dir=_examples_dir(root_path, output_dir))
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


def _mine_block(block: ExampleBlock, *, client: LlmClient, graph: Graph) -> MinedExample:
    response = client.structured_completion(
        prompt=_example_prompt(block),
        schema=_example_schema(),
        model="configured-micro-model",
        max_tokens=2000,
        temperature=0,
        purpose="tax_graph_example_miner",
    )
    facts_document = _normalize_facts_document(response.get("facts", {}))
    expected = dict(response.get("expected", {}) or {})
    if not expected:
        return MinedExample(block, facts_document, expected, status="unmappable", mismatches=("no expected values",))
    result = Engine(graph).execute(_facts_from_document(facts_document))
    mismatches = tuple(_expected_mismatches(expected, result.values))
    status = "agreed" if not mismatches else "disagreed"
    return MinedExample(block, facts_document, expected, status=status, mismatches=mismatches)


def _freeze_mined_example(mined: MinedExample, *, output_dir: Path) -> MinedExample:
    example_dir = output_dir / mined.block.source_document_id / mined.block.example_id
    example_dir.mkdir(parents=True, exist_ok=True)
    _write_yaml(example_dir / "facts.yaml", mined.facts_document)
    _write_yaml(
        example_dir / "expected.yaml",
        {
            "example_id": mined.block.example_id,
            "source_document_id": mined.block.source_document_id,
            "confirmed": True,
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
            "human_confirmed": True,
        },
    )
    return MinedExample(
        block=mined.block,
        facts_document=mined.facts_document,
        expected=mined.expected,
        status=mined.status,
        mismatches=mined.mismatches,
        output_dir=example_dir,
    )


def _expected_mismatches(expected: Mapping[str, Any], actual_values: Mapping[str, Any]) -> list[str]:
    mismatches: list[str] = []
    for node_id, expected_value in expected.items():
        actual = actual_values.get(node_id)
        if actual != expected_value:
            mismatches.append(f"{node_id}: got {actual}, want {expected_value}")
    return mismatches


def _normalize_facts_document(facts: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(facts)
    normalized.setdefault("facts", [])
    normalized.setdefault("tables", [])
    return normalized


def _facts_from_document(facts_document: Mapping[str, Any]) -> dict[str, Any]:
    facts = {fact["node_id"]: fact["value"] for fact in facts_document.get("facts", []) or []}
    if facts_document.get("tables"):
        facts["#tables"] = list(facts_document["tables"])
    return facts


def _example_prompt(block: ExampleBlock) -> str:
    return "\n".join(
        [
            "Extract this IRS worked example into Tax Graph facts and expected node values.",
            "Return schema fields: facts, expected, notes.",
            "Use table row_key values that are stable lowercase ids.",
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


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, data: Any) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=False), encoding="utf-8", newline="\n")


_EXAMPLE_HEADING_RE = re.compile(r"(?m)^(?:\*\*)?Example\b[^.\n]*\.(?:\*\*)?")
_NEXT_HEADING_RE = re.compile(r"(?m)^#{1,6}\s+")
