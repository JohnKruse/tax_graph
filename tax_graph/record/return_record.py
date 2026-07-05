"""Build deterministic Return Record objects from facts, graph, and trace.

The Return Record is the cross-year memory artifact. This module builds the
typed in-memory record while preserving the dual-format rule: prose renderers
may display facts and carryforwards, but next year's machine ingestion reads
only the structured carryforward block.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
import yaml

from tax_graph.engine import Graph, MISSING, Result
from tax_graph.io.loader import load_yaml


SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"
CAPITAL_LOSS_SOURCE_NODE = "schedule_d_2025_line_16_total"
CAPITAL_LOSS_DERIVATION = (
    "Capital Loss Carryover Worksheet / $3000 limitation is not modeled in v0; "
    "this is the RAW net loss, not the usable carryover."
)


@dataclass(frozen=True)
class RecordMetadata:
    """Stable metadata for one generated Return Record."""

    tax_year: int
    filing_status: str | None
    generated_date: str
    tax_graph_version: str
    target_node: str | None = None


@dataclass(frozen=True)
class FactLedgerEntry:
    """One taxpayer-supplied fact with provenance preserved."""

    node_id: str
    label: str
    value: Any
    source: dict[str, Any] = field(default_factory=dict)
    confidence: float | None = None


@dataclass(frozen=True)
class DecisionLogEntry:
    """One resolved decision with option, rationale, and citations."""

    decision_id: str
    question: str
    chosen_option_id: str
    chosen_label: str
    chosen_option_type: str
    rationale: str
    decided_by: str
    decided_date: str
    options_presented: list[dict[str, Any]]
    citations: list[dict[str, Any]]


@dataclass(frozen=True)
class TraceSummaryEntry:
    """A stable, compact trace row for rendered record summaries."""

    node_id: str
    label: str
    kind: str
    value: Any
    operation: str | None = None
    rule: str | None = None
    citations: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CarryforwardBlock:
    """Structured carryforward payload paired with the prose memo."""

    tax_year: int
    tax_graph_version: str
    generated_date: str
    carryforwards: list[dict[str, Any]] = field(default_factory=list)
    elections: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a schema-shaped dictionary for YAML emission."""
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class ReturnRecord:
    """Typed Return Record assembled from a single engine execution."""

    metadata: RecordMetadata
    facts: list[FactLedgerEntry]
    decisions: list[DecisionLogEntry]
    unsupported: list[str]
    outputs: list[TraceSummaryEntry]
    trace_summary: list[TraceSummaryEntry]
    carryforward_block: CarryforwardBlock
    elections: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dictionary suitable for YAML or JSON rendering."""
        return _json_safe(asdict(self))


def build_return_record(
    *,
    facts_document: dict[str, Any],
    result: Result,
    graph: Graph,
    decision_resolutions: dict[str, Any] | None = None,
    tax_year: int | str | None = None,
    tax_graph_version: str = "unknown",
    generated_date: str = "unknown",
    target_node: str | None = None,
) -> ReturnRecord:
    """Build a deterministic Return Record model from an engine result."""
    record_year = int(tax_year or facts_document.get("tax_year") or graph.year)
    metadata = RecordMetadata(
        tax_year=record_year,
        filing_status=facts_document.get("filing_status"),
        generated_date=str(generated_date),
        tax_graph_version=tax_graph_version,
        target_node=target_node,
    )
    resolutions = validate_decision_resolutions(decision_resolutions or {"resolutions": []}, graph)
    facts = _build_facts(facts_document, graph)
    decisions = _build_decisions(resolutions, graph)
    trace_summary = [_trace_entry(node_id, trace, graph) for node_id, trace in sorted(result.trace.items())]
    outputs = _build_outputs(result, graph, target_node)
    carryforward_block = _build_carryforward_block(
        result=result,
        tax_year=record_year,
        tax_graph_version=tax_graph_version,
        generated_date=str(generated_date),
    )
    validate_carryforward_block(carryforward_block.to_dict())
    unsupported = _build_unsupported(result, decisions, carryforward_block)
    return ReturnRecord(
        metadata=metadata,
        facts=facts,
        decisions=decisions,
        unsupported=unsupported,
        outputs=outputs,
        trace_summary=trace_summary,
        carryforward_block=carryforward_block,
        elections=[],
    )


def load_decision_resolutions(path: str | Path) -> dict[str, Any]:
    """Load decision resolutions from YAML and normalize an empty file."""
    data = load_yaml(path)
    return data if data is not None else {"resolutions": []}


def render_memo(record: ReturnRecord) -> str:
    """Render a stable ASCII Markdown memo for human review."""
    lines = [
        "# Tax Graph Return Record",
        "",
        "## Metadata",
        f"- Tax year: {record.metadata.tax_year}",
        f"- Filing status: {record.metadata.filing_status or 'not provided'}",
        f"- Generated date: {record.metadata.generated_date}",
        f"- Tax Graph version: {record.metadata.tax_graph_version}",
        f"- Target node: {record.metadata.target_node or 'not provided'}",
        "",
        "## Facts Ledger",
    ]
    if record.facts:
        for fact in record.facts:
            lines.extend(
                [
                    f"- {fact.label} (`{fact.node_id}`): {_format_value(fact.value)}",
                    f"  - Source: {_format_source(fact.source)}",
                    f"  - Confidence: {_format_confidence(fact.confidence)}",
                ]
            )
    else:
        lines.append("- No input facts were supplied.")

    lines.extend(["", "## Decision Log"])
    if record.decisions:
        for decision in record.decisions:
            lines.extend(
                [
                    f"### {decision.decision_id}",
                    f"- Question: {decision.question}",
                    "- Options presented:",
                ]
            )
            for option in decision.options_presented:
                lines.append(
                    f"  - {option['option_id']}: {option['label']} [{option['option_type']}]"
                )
            lines.extend(
                [
                    f"- Chosen: {decision.chosen_option_id} - {decision.chosen_label} [{decision.chosen_option_type}]",
                    f"- Rationale: {decision.rationale}",
                    f"- Decided by: {decision.decided_by}",
                    f"- Decided date: {decision.decided_date}",
                    "- Citations:",
                ]
            )
            lines.extend(_render_citations(decision.citations, indent="  "))
    else:
        lines.append("- No decisions were required.")

    lines.extend(["", "## Unsupported / Deferred"])
    if record.unsupported:
        lines.extend(f"- {item}" for item in record.unsupported)
    else:
        lines.append("- No unsupported or deferred items were recorded.")

    lines.extend(["", "## Computed Outputs"])
    if record.outputs:
        lines.extend(_render_trace_entries(record.outputs))
    else:
        lines.append("- No computed outputs were recorded.")

    lines.extend(["", "## Trace Summary"])
    if record.trace_summary:
        lines.extend(_render_trace_entries(record.trace_summary))
    else:
        lines.append("- No trace entries were recorded.")

    lines.extend(["", "## Carryforwards"])
    if record.carryforward_block.carryforwards:
        for item in record.carryforward_block.carryforwards:
            lines.append(
                f"- {item['carryforward_id']} ({item['kind']}): {_format_value(item['amount'])}"
            )
            if item.get("target_node"):
                lines.append(f"  - Target node: {item['target_node']}")
            else:
                lines.append("  - Target node: not ingestible in v0")
            if item.get("derivation"):
                lines.append(f"  - Derivation: {item['derivation']}")
    else:
        lines.append("- No carryforwards emitted.")
    lines.append("- Machine payload: see paired carryforward YAML; do not parse this prose.")

    lines.extend(["", "## Elections"])
    elections = record.elections or record.carryforward_block.elections
    if elections:
        for election in elections:
            lines.append(f"- {election['election_id']}: {election['choice']}")
    else:
        lines.append("- No consistency elections recorded.")

    return "\n".join(lines) + "\n"


def render_carryforward_yaml(block: CarryforwardBlock | dict[str, Any]) -> str:
    """Render a schema-validated carryforward block as LF-normalized YAML."""
    payload = block.to_dict() if isinstance(block, CarryforwardBlock) else dict(block)
    validate_carryforward_block(payload)
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=False).replace("\r\n", "\n")


def validate_carryforward_block(data: dict[str, Any]) -> None:
    """Validate a structured carryforward block against the project schema."""
    schema = load_yaml(SCHEMA_DIR / "carryforward.schema.json")
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))
    if errors:
        first = errors[0]
        path = ".".join(str(part) for part in first.path) or "<root>"
        raise ValueError(f"invalid carryforward block at {path}: {first.message}")


def validate_decision_resolutions(data: dict[str, Any], graph: Graph) -> list[dict[str, Any]]:
    """Validate resolution schema and ensure every decision option exists."""
    schema = load_yaml(SCHEMA_DIR / "decision_resolutions.schema.json")
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))
    if errors:
        first = errors[0]
        path = ".".join(str(part) for part in first.path) or "<root>"
        raise ValueError(f"invalid decision resolutions at {path}: {first.message}")

    resolutions = sorted(data.get("resolutions", []), key=lambda item: item["decision_id"])
    for resolution in resolutions:
        decision = graph.decisions.get(resolution["decision_id"])
        if decision is None:
            raise ValueError(f"unknown decision_id: {resolution['decision_id']}")
        option_ids = {option["option_id"] for option in decision.get("options", [])}
        if resolution["chosen_option_id"] not in option_ids:
            raise ValueError(
                f"unknown option_id {resolution['chosen_option_id']} for decision {resolution['decision_id']}"
            )
    return resolutions


def _build_facts(facts_document: dict[str, Any], graph: Graph) -> list[FactLedgerEntry]:
    facts: list[FactLedgerEntry] = []
    for fact in sorted(facts_document.get("facts", []), key=lambda item: item["node_id"]):
        node = graph.nodes.get(fact["node_id"], {})
        facts.append(
            FactLedgerEntry(
                node_id=fact["node_id"],
                label=node.get("label", fact["node_id"]),
                value=fact.get("value"),
                source=dict(fact.get("source", {})),
                confidence=fact.get("confidence"),
            )
        )
    return facts


def _build_decisions(resolutions: list[dict[str, Any]], graph: Graph) -> list[DecisionLogEntry]:
    entries: list[DecisionLogEntry] = []
    for resolution in resolutions:
        decision = graph.decisions[resolution["decision_id"]]
        chosen = next(
            option for option in decision["options"] if option["option_id"] == resolution["chosen_option_id"]
        )
        citation_ids = sorted(set(decision.get("citation_refs", []) + chosen.get("citation_refs", [])))
        entries.append(
            DecisionLogEntry(
                decision_id=decision["decision_id"],
                question=decision["question"],
                chosen_option_id=chosen["option_id"],
                chosen_label=chosen["label"],
                chosen_option_type=chosen["option_type"],
                rationale=resolution["rationale"],
                decided_by=resolution["decided_by"],
                decided_date=resolution["decided_date"],
                options_presented=list(decision.get("options", [])),
                citations=[
                    graph.citations[citation_id]
                    for citation_id in citation_ids
                    if citation_id in graph.citations
                ],
            )
        )
    return entries


def _build_unsupported(
    result: Result,
    decisions: list[DecisionLogEntry],
    carryforward_block: CarryforwardBlock,
) -> list[str]:
    items = [
        f"Missing required input: {node_id}"
        for node_id in result.missing_required_inputs
    ]
    for decision in decisions:
        if decision.chosen_option_type in {"other", "unsupported", "escalate"}:
            items.append(
                f"Decision {decision.decision_id} chose {decision.chosen_option_type}: {decision.chosen_label}"
            )
    for carryforward in carryforward_block.carryforwards:
        if not carryforward.get("target_node"):
            items.append(
                f"Carryforward {carryforward['carryforward_id']} is not ingestible in v0: "
                f"{carryforward.get('derivation', 'no derivation recorded')}"
            )
    return sorted(items)


def _build_carryforward_block(
    *,
    result: Result,
    tax_year: int,
    tax_graph_version: str,
    generated_date: str,
) -> CarryforwardBlock:
    carryforwards: list[dict[str, Any]] = []
    net_value = result.values.get(CAPITAL_LOSS_SOURCE_NODE)
    if isinstance(net_value, (int, float)) and net_value < 0:
        carryforwards.append(
            {
                "carryforward_id": f"capital_loss_raw_{tax_year}",
                "kind": "capital_loss",
                "amount": abs(net_value),
                "originating_year": tax_year,
                "applies_from_year": tax_year + 1,
                "source_node": CAPITAL_LOSS_SOURCE_NODE,
                "derivation": CAPITAL_LOSS_DERIVATION,
            }
        )
    return CarryforwardBlock(
        tax_year=tax_year,
        tax_graph_version=tax_graph_version,
        generated_date=generated_date,
        carryforwards=carryforwards,
        elections=[],
    )


def _build_outputs(result: Result, graph: Graph, target_node: str | None) -> list[TraceSummaryEntry]:
    if target_node:
        trace = result.trace.get(target_node, {"kind": "not_found", "value": None})
        return [_trace_entry(target_node, trace, graph)]
    return [
        _trace_entry(node_id, trace, graph)
        for node_id, trace in sorted(result.trace.items())
        if trace.get("kind") == "computed"
    ]


def _trace_entry(node_id: str, trace: dict[str, Any], graph: Graph) -> TraceSummaryEntry:
    return TraceSummaryEntry(
        node_id=node_id,
        label=graph.nodes.get(node_id, {}).get("label", node_id),
        kind=trace.get("kind", "unknown"),
        value=_json_safe(trace.get("value")),
        operation=trace.get("operation"),
        rule=trace.get("rule"),
        citations=list(trace.get("citations", [])),
    )


def _json_safe(value: Any) -> Any:
    if value is MISSING:
        return "MISSING"
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _format_value(value: Any) -> str:
    safe = _json_safe(value)
    if safe is None:
        return "blank"
    return str(safe)


def _format_source(source: dict[str, Any]) -> str:
    if not source:
        return "not recorded"
    return ", ".join(f"{key}={source[key]}" for key in sorted(source))


def _format_confidence(confidence: float | None) -> str:
    return "not recorded" if confidence is None else str(confidence)


def _render_citations(citations: list[dict[str, Any]], *, indent: str = "") -> list[str]:
    if not citations:
        return [f"{indent}- No citations recorded."]
    return [
        f"{indent}- {citation['citation_id']} ({citation.get('locator', 'unknown locator')}): "
        f"\"{_collapse_text(citation.get('quoted_text', ''))}\""
        for citation in citations
    ]


def _render_trace_entries(entries: list[TraceSummaryEntry]) -> list[str]:
    lines: list[str] = []
    for entry in entries:
        suffix = []
        if entry.operation:
            suffix.append(f"operation={entry.operation}")
        if entry.rule:
            suffix.append(f"rule={entry.rule}")
        if entry.citations:
            suffix.append("citations=" + ",".join(entry.citations))
        detail = f" ({'; '.join(suffix)})" if suffix else ""
        lines.append(
            f"- {entry.label} (`{entry.node_id}`): {_format_value(entry.value)} [{entry.kind}]{detail}"
        )
    return lines


def _collapse_text(text: str) -> str:
    return " ".join(str(text).split())
