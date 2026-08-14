"""Harvest worksheet-shaped graph drafts from acquired instruction HTML.

The worksheet harvester is intentionally separate from promotion.  It reads
only the acquired source supplied by the caller, discovers worksheet tables,
and returns schema-shaped draft objects with a source witness for every
object.  HTML table boundaries are the structural extent authority.  The
rendered Markdown text is a prose witness and is checked as an independent
extent oracle.  The source anchor is retained as an observation, not used as
worksheet identity.  It never writes graph state.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from html.parser import HTMLParser
import hashlib
from pathlib import Path
import re
import unicodedata
from typing import Any, Iterable, Mapping, Protocol

import yaml

from tax_graph.acquire.instruction_html import InstructionHeading, parse_headings
from tax_graph.documents import document_class_for


QDCGT_TARGET = "qualified_dividends_and_capital_gain_tax_worksheet_2025"


@dataclass(frozen=True)
class WorksheetTarget:
    """Describe a worksheet whose title is the stable source identity.

    ``start_anchor`` is retained as a source observation and compatibility
    input for existing targets.  The harvester never requires that generated
    HTML id to remain unchanged across tax years.  Extent is read from the
    selected HTML table, never from this target.
    """

    document_id: str
    title: str
    start_anchor: str
    source_document_id: str | None = None
    # Legacy canary assertions are retained for QDCGT compatibility.  New
    # document-wide discovery never populates these fields; its counts come
    # from the selected source table and are reported as observations.
    expected_line_count: int | None = None
    expected_constant_count: int | None = None
    citation_groups: tuple[tuple[str, ...], ...] | None = None


QDCGT_WORKSHEET_TARGET = WorksheetTarget(
    document_id=QDCGT_TARGET,
    title="Qualified Dividends and Capital Gain Tax Worksheet",
    start_anchor="en_US_2025_publink1000158415",
    source_document_id="instructions_form_1040_2025",
    expected_line_count=25,
    expected_constant_count=13,
    citation_groups=(
        ("1",),
        ("2",),
        ("3",),
        ("4",),
        ("5",),
        ("6", "7", "8", "9"),
        ("10", "11", "12"),
        ("13", "14", "15", "16", "17"),
        ("18", "19", "20", "21"),
        ("22",),
        ("23", "24", "25"),
        ("24",),
        ("25",),
    ),
)


@dataclass(frozen=True)
class WorksheetFinding:
    """A deterministic reason why a worksheet draft cannot be trusted."""

    kind: str
    message: str
    evidence: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        """Return a stable review-facing finding."""
        return {"kind": self.kind, "message": self.message, "evidence": list(self.evidence)}


@dataclass(frozen=True)
class WorksheetCondition:
    """A conditional route preserved from a worksheet line's source text."""

    line: str
    referenced_document: str
    behavior: str
    source_quote: str

    def as_dict(self) -> dict[str, str]:
        """Return the condition as draft metadata."""
        return {
            "line": self.line,
            "referenced_document": self.referenced_document,
            "behavior": self.behavior,
            "source_quote": self.source_quote,
        }


@dataclass(frozen=True)
class HarvestObject:
    """One schema-shaped object plus the source witness used to emit it."""

    kind: str
    data: Mapping[str, Any]
    source_quote: str
    source_start: int
    source_end: int
    source_spans: tuple[tuple[int, int], ...] = ()

    def __getitem__(self, key: str) -> Any:
        """Allow draft objects to be inspected like the dictionaries they serialize to."""
        return self.data[key]

    def get(self, key: str, default: Any = None) -> Any:
        """Return one schema field without exposing the witness in the schema payload."""
        return self.data.get(key, default)

    def as_dict(self) -> dict[str, Any]:
        """Return the schema-shaped object without internal source metadata."""
        return dict(self.data)


@dataclass(frozen=True)
class WorksheetHarvest:
    """Pure worksheet harvest output, suitable for draft routing."""

    target: WorksheetTarget
    year: str
    source_document_id: str
    start_anchor: str
    document: HarvestObject | None
    nodes: tuple[HarvestObject, ...]
    edges: tuple[HarvestObject, ...]
    citations: tuple[HarvestObject, ...]
    conditions: tuple[WorksheetCondition, ...]
    findings: tuple[WorksheetFinding, ...]
    worksheet_source_span: tuple[int, int] | None = None
    markdown_lines: tuple[str, ...] | None = None
    html_lines: tuple[str, ...] = ()
    window: WorksheetWindow | None = None
    advisories_enabled: bool = False
    source_table_ids: tuple[int, ...] = ()

    @property
    def ok(self) -> bool:
        """Whether the harvest has a usable document and no fatal finding.

        Window-edge, oracle, overlap, and unresolved-footnote observations are
        advisory.  They stay attached to the draft for review, but they do not
        suppress deterministic source-backed output.
        """
        return self.document is not None and (
            not _has_fatal_findings(self.findings)
            if self.advisories_enabled
            else not self.findings
        )

    @property
    def line_nodes(self) -> tuple[HarvestObject, ...]:
        """Return emitted worksheet fields, excluding parameter nodes."""
        return tuple(node for node in self.nodes if node.get("node_type") == "worksheet_field")

    @property
    def parameter_nodes(self) -> tuple[HarvestObject, ...]:
        """Return emitted constants discovered in worksheet prose."""
        return tuple(node for node in self.nodes if node.get("node_type") == "parameter")

    @property
    def observed_start_anchor(self) -> str:
        """Return the generated source anchor observed on the chosen heading."""
        return self.start_anchor

    def as_dict(self) -> dict[str, Any]:
        """Return a draft report without changing the graph schema."""
        report = {
            "schema_version": 1,
            "status": "ready" if self.ok else "blocked",
            "document_id": self.target.document_id,
            "year": self.year,
            "source_document_id": self.source_document_id,
            "worksheet_title": self.target.title,
            "start_anchor": self.start_anchor,
            "observed_start_anchor": self.observed_start_anchor,
            "start_resolution": "title",
            "worksheet_source_span": list(self.worksheet_source_span)
            if self.worksheet_source_span is not None
            else None,
            "oracle": {
                "status": (
                    "unavailable"
                    if self.markdown_lines is None
                    else "agree" if tuple(self.markdown_lines) == self.html_lines else "disagree"
                ),
                "markdown_lines": list(self.markdown_lines or ()),
                "html_lines": list(self.html_lines),
            },
            "window": self.window.as_dict() if self.window is not None else None,
            "conditions": [condition.as_dict() for condition in self.conditions],
            "findings": [finding.as_dict() for finding in self.findings],
            "counts": {
                "lines": len(self.line_nodes),
                "constants": len(self.parameter_nodes),
                "edges": len(self.edges),
                "citations": len(self.citations),
            },
        }
        if self.source_table_ids:
            report["source_table_ids"] = list(self.source_table_ids)
        return report


@dataclass(frozen=True)
class _RawRow:
    """One HTML table row with visible cell text and source offsets."""

    table_id: int
    start: int
    end: int
    cells: tuple[str, ...]
    text: str


@dataclass(frozen=True)
class _RawTable:
    """One acquired HTML table and its source-backed rows."""

    table_id: int
    start: int
    end: int
    rows: tuple[_RawRow, ...]
    heading: InstructionHeading | None


@dataclass(frozen=True)
class WorksheetWindow:
    """One cache-backed model answer over a table and its lookahead."""

    anchor_table_id: int
    starts_a_worksheet: bool
    title: str
    table_ids: tuple[int, ...]
    parameter_table_ids: tuple[int, ...]
    serves_lines: tuple[str, ...]
    source_start: int
    source_end: int
    finding: WorksheetFinding | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return the review-facing window record."""
        record = {
            "anchor_table_id": self.anchor_table_id,
            "starts_a_worksheet": self.starts_a_worksheet,
            "title": self.title,
            "table_ids": list(self.table_ids),
            "parameter_table_ids": list(self.parameter_table_ids),
            "serves_lines": list(self.serves_lines),
            "source_start": self.source_start,
            "source_end": self.source_end,
        }
        if self.finding is not None:
            record["finding"] = self.finding.as_dict()
        return record


class WindowClassifier(Protocol):
    """Provider seam for one candidate-table window."""

    def __call__(
        self,
        table: _RawTable,
        source_text: str,
        lookahead: int,
        following_tables: tuple[_RawTable, ...],
    ) -> Mapping[str, Any]:
        """Decide whether the candidate starts a worksheet and return table ids."""


class TableClassifier(Protocol):
    """Callable seam for the table-classification model."""

    def __call__(self, table: _RawTable, source_text: str) -> Mapping[str, Any]:
        """Classify one table from its own heading and visible text."""


@dataclass(frozen=True)
class WorksheetDiscovery:
    """Document-wide window observations and harvested worksheet drafts."""

    source_document_id: str
    year: str
    classifications: tuple[TableClassification, ...]
    worksheets: tuple[WorksheetHarvest, ...]
    findings: tuple[WorksheetFinding, ...] = ()
    inventory: tuple[WorksheetFinding, ...] = ()
    windows: tuple[WorksheetWindow, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        """Return a stable discovery report without source payloads."""
        return {
            "schema_version": 1,
            "source_document_id": self.source_document_id,
            "year": self.year,
            "classifications": [item.as_dict() for item in self.classifications],
            "windows": [item.as_dict() for item in self.windows],
            "worksheets": [item.as_dict() for item in self.worksheets],
            "findings": [item.as_dict() for item in self.findings],
            "inventory": [item.as_dict() for item in self.inventory],
        }


@dataclass
class _RowParser(HTMLParser):
    """Capture table rows without turning acquired HTML into authored text."""

    source: str
    rows: list[_RawRow] = field(default_factory=list)

    def __post_init__(self) -> None:
        HTMLParser.__init__(self, convert_charrefs=True)
        self._line_starts = [0]
        for index, char in enumerate(self.source):
            if char == "\n":
                self._line_starts.append(index + 1)
        self._table_id = 0
        self._table_stack: list[int] = []
        self._table_starts: dict[int, int] = {}
        self._table_ends: dict[int, int] = {}
        self._table_rows: dict[int, list[_RawRow]] = {}
        self._row_start = 0
        self._row_table_id = 0
        self._row_cells: list[str] = []
        self._cell_parts: list[str] | None = None

    @property
    def tables(self) -> tuple[_RawTable, ...]:
        """Return parsed table ranges in source order."""
        return tuple(
            _RawTable(
                table_id=table_id,
                start=self._table_starts[table_id],
                end=self._table_ends.get(table_id, len(self.source)),
                rows=tuple(self._table_rows.get(table_id, ())),
                heading=None,
            )
            for table_id in sorted(self._table_starts)
        )

    def _offset(self) -> int:
        line, column = self.getpos()
        return self._line_starts[line - 1] + column

    def _tag_end(self, offset: int) -> int:
        close = self.source.find(">", offset)
        return close + 1 if close >= 0 else offset

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered == "table":
            self._table_id += 1
            table_id = self._table_id
            self._table_stack.append(table_id)
            self._table_starts[table_id] = self._offset()
            self._table_rows[table_id] = []
            return
        if lowered == "tr" and self._row_cells == [] and self._cell_parts is None:
            self._row_start = self._offset()
            self._row_table_id = self._table_stack[-1] if self._table_stack else 0
            self._row_cells = []
            return
        if lowered in {"td", "th"} and self._row_cells is not None and self._cell_parts is None:
            self._cell_parts = []
            return
        if lowered == "br" and self._cell_parts is not None:
            self._cell_parts.append(" ")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "br" and self._cell_parts is not None:
            self._cell_parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"td", "th"} and self._cell_parts is not None:
            self._row_cells.append(_normalize_text("".join(self._cell_parts)))
            self._cell_parts = None
            return
        if lowered == "tr" and self._row_cells != [] and self._cell_parts is None:
            end = self._tag_end(self._offset())
            cells = tuple(self._row_cells)
            row = _RawRow(
                table_id=self._row_table_id,
                start=self._row_start,
                end=end,
                cells=cells,
                text=_normalize_text(" ".join(cell for cell in cells if cell)),
            )
            self.rows.append(row)
            self._table_rows.setdefault(self._row_table_id, []).append(row)
            self._row_cells = []
            return
        if lowered == "table" and self._table_stack:
            table_id = self._table_stack.pop()
            self._table_ends[table_id] = self._tag_end(self._offset())

    def handle_data(self, data: str) -> None:
        if self._cell_parts is not None:
            self._cell_parts.append(data)


WINDOW_LOOKAHEAD = 4
_SOURCE_TOKEN_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?|[0-9]+(?:[A-Za-z]+)?")
_SOURCE_DOT_LEADER_RE = re.compile(r"(?:\.{2,}|\.\s+\.|_{2,}|\\_{2,})")
_SOURCE_NOTE_RE = re.compile(r"\bnote\b", re.IGNORECASE)
_SOURCE_ROUTING_RE = re.compile(
    r"\b(?:go\s+to\s+line|otherwise|skip\s+lines?|also\s+enter)\b",
    re.IGNORECASE,
)
_SOURCE_LINE_REFERENCE_RE = re.compile(r"\bline\s+([0-9]+[a-z]?)\b", re.IGNORECASE)
ADVISORY_FINDING_KINDS = frozenset(
    {
        "html_markdown_extent_disagreement",
        "unresolved_footnote_marker",
        "worksheet_window_reached_edge",
        "window_claim_overlap",
    }
)


@dataclass(frozen=True)
class TableClassification:
    """The cached per-table candidate gate used before opening a window."""

    table_id: int
    heading: str
    anchor_id: str
    kind: str
    lines: tuple[str, ...]
    source_start: int
    source_end: int
    finding: WorksheetFinding | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return the review-facing classification record."""
        record = {
            "table_id": self.table_id,
            "heading": self.heading,
            "anchor_id": self.anchor_id,
            "kind": self.kind,
            "lines": list(self.lines),
            "source_start": self.source_start,
            "source_end": self.source_end,
        }
        if self.finding is not None:
            record["finding"] = self.finding.as_dict()
        return record


def worksheet_table_schema() -> dict[str, Any]:
    """Return the strict schema for the candidate worksheet gate."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["kind"],
        "properties": {
            "kind": {
                "type": "string",
                "enum": ["worksheet", "lookup_table", "layout"],
            },
        },
    }


def classify_worksheet_tables(
    source_text: str,
    *,
    classifier: Any | None = None,
    config: Mapping[str, Any] | None = None,
    cache_path: str | Path | None = None,
) -> tuple[TableClassification, ...]:
    """Classify every acquired table and retain the incremental cache.

    This is the cheap candidate gate.  Only tables classified as ``worksheet``
    are sent through the more expensive sliding-window segmentation pass.
    """
    if not _is_html_source(source_text):
        raise ValueError("worksheet table classification requires acquired HTML")
    tables = _source_tables(source_text)
    if not tables:
        return ()
    settings = dict(config or {})
    cache_file = Path(cache_path) if cache_path is not None else None
    cached = _load_classification_cache(cache_file)
    updated_cache = dict(cached)
    classifications: list[TableClassification] = []
    for table in tables:
        fingerprint = hashlib.sha256(source_text[table.start : table.end].encode("ascii")).hexdigest()
        cached_payload = cached.get(fingerprint)
        try:
            if isinstance(cached_payload, dict):
                payload = cached_payload
                parsed = _classification_from_payload(table, payload)
            elif classifier is not None:
                payload = _call_table_classifier(table, source_text, classifier=classifier, config=settings)
                updated_cache[fingerprint] = dict(payload)
                parsed = _classification_from_payload(table, payload)
                if cache_file is not None:
                    _write_classification_cache(cache_file, updated_cache)
            else:
                payload = _call_table_classifier(table, source_text, classifier=None, config=settings)
                updated_cache[fingerprint] = dict(payload)
                parsed = _classification_from_payload(table, payload)
                if cache_file is not None:
                    _write_classification_cache(cache_file, updated_cache)
            classifications.append(parsed)
        except Exception as exc:
            classifications.append(_classification_failure(table, exc))
    return tuple(classifications)


def _call_table_classifier(
    table: _RawTable,
    source_text: str,
    *,
    classifier: Any,
    config: Mapping[str, Any],
) -> Mapping[str, Any]:
    if classifier is not None:
        if hasattr(classifier, "classify_table"):
            response = classifier.classify_table(table, source_text)
        elif callable(classifier) and not hasattr(classifier, "structured_completion"):
            response = classifier(table, source_text)
        else:
            response = None
        if response is not None:
            if not isinstance(response, Mapping):
                raise ValueError("worksheet table classifier returned a non-object")
            return response
    if classifier is None or hasattr(classifier, "structured_completion"):
        client = classifier
        settings = dict(config)
        if client is None:
            from tax_graph.extract.llm_client import build_llm_client

            client = build_llm_client(settings)
        return _model_classify_table(client, table, source_text, settings)
    raise ValueError("worksheet table classifier returned no result")


def _model_classify_table(
    client: Any,
    table: _RawTable,
    source_text: str,
    config: Mapping[str, Any],
) -> Mapping[str, Any]:
    from tax_graph.config import get_config_value, resolve_llm_model, resolve_llm_seed

    heading = table.heading.text if table.heading is not None else "(no heading)"
    anchor = table.heading.anchor_id if table.heading is not None else "(no anchor)"
    visible = _visible_text(source_text[table.start : table.end])
    prompt = (
        "Classify exactly one acquired IRS instruction HTML table. "
        "The table kind must be worksheet, lookup_table, or layout. "
        "A worksheet is a named computation document a filer completes. "
        "A lookup_table is reference bands or rates, and a layout is "
        "presentation structure without a computation. "
        "Do not infer line numbers from row prose. The pipeline reads "
        "printed line numbers from the table's own heading.\n\n"
        f"heading: {heading}\nanchor: {anchor}\ntable_text:\n{visible}\n"
    )
    request: dict[str, Any] = {
        "prompt": prompt,
        "schema": worksheet_table_schema(),
        "model": resolve_llm_model(config, "micro"),
        "max_tokens": int(get_config_value(dict(config), "extraction.worksheet_classifier_max_tokens", 6000)),
        "temperature": get_config_value(dict(config), "llm.temperature"),
        "purpose": "tax_graph_worksheet_table_classifier",
    }
    seed = resolve_llm_seed(config)
    if seed is not None:
        request["seed"] = seed
    response = client.structured_completion(**request)
    if not isinstance(response, Mapping):
        raise ValueError("worksheet table classifier returned a non-object")
    return response


def _classification_from_payload(table: _RawTable, payload: Mapping[str, Any]) -> TableClassification:
    kind = str(payload.get("kind") or "").strip()
    if kind not in {"worksheet", "lookup_table", "layout"}:
        raise ValueError(f"unsupported worksheet table kind: {kind!r}")
    heading = table.heading
    return TableClassification(
        table_id=table.table_id,
        heading=heading.text if heading is not None else "",
        anchor_id=heading.anchor_id if heading is not None else "",
        kind=kind,
        lines=_heading_lines(heading.text if heading is not None else ""),
        source_start=table.start,
        source_end=table.end,
    )


def _classification_failure(table: _RawTable, exc: Exception) -> TableClassification:
    finding = WorksheetFinding(
        "table_classification_failed",
        f"table {table.table_id} classification failed: {exc}",
        (
            f"table_id={table.table_id}",
            f"heading={table.heading.text if table.heading is not None else '(none)'}",
            f"source_span={table.start}:{table.end}",
        ),
    )
    return TableClassification(
        table_id=table.table_id,
        heading=table.heading.text if table.heading is not None else "",
        anchor_id=table.heading.anchor_id if table.heading is not None else "",
        kind="classification_error",
        lines=_heading_lines(table.heading.text if table.heading is not None else ""),
        source_start=table.start,
        source_end=table.end,
        finding=finding,
    )


def _load_classification_cache(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="ascii")) or {}
    if not isinstance(payload, dict) or not isinstance(payload.get("tables", {}), dict):
        raise ValueError(f"invalid worksheet classification cache: {path}")
    return {
        str(key): dict(value)
        for key, value in payload["tables"].items()
        if isinstance(value, dict)
    }


def _write_classification_cache(path: Path, entries: Mapping[str, Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump({"schema_version": 1, "tables": dict(entries)}, sort_keys=True, allow_unicode=False),
        encoding="ascii",
        newline="\n",
    )


def _has_fatal_findings(findings: Iterable[WorksheetFinding]) -> bool:
    """Return whether a finding prevents emitting source-backed draft objects."""
    return any(finding.kind not in ADVISORY_FINDING_KINDS for finding in findings)


def window_schema() -> dict[str, Any]:
    """Return the strict schema for one sliding-window segmentation call."""
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


def _table_window_text(table: _RawTable) -> str:
    """Render a table window without introducing a second text authority."""
    heading = table.heading.text.strip() if table.heading is not None else "(no heading)"
    lines = [line for line in (_row_line(row) for row in table.rows) if line]
    parts = [
        f"### table {table.table_id}",
        f"heading: {heading}",
        f"printed_line_tokens:{','.join(lines) if lines else '(none)'}",
    ]
    body = [f"| {row.text.strip()}" for row in table.rows if row.text.strip()]
    parts.append("\n".join(body) if body else "(no rows)")
    return "\n".join(parts)


def window_fingerprint(
    source_text: str,
    tables: tuple[_RawTable, ...],
    index: int,
    lookahead: int = WINDOW_LOOKAHEAD,
) -> str:
    """Return the cache key used by the seeding pass, byte for byte."""
    chunk = tables[index : index + 1 + lookahead]
    joined = "\n".join(source_text[table.start : table.end] for table in chunk)
    return hashlib.sha256(f"{lookahead}\n{joined}".encode("ascii")).hexdigest()


def _load_window_cache(path: Path | None) -> tuple[int, dict[str, dict[str, Any]]]:
    if path is None or not path.exists():
        return WINDOW_LOOKAHEAD, {}
    payload = yaml.safe_load(path.read_text(encoding="ascii")) or {}
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError(f"invalid worksheet window cache schema: {path}")
    lookahead = payload.get("lookahead")
    windows = payload.get("windows")
    if not isinstance(lookahead, int) or lookahead < 1 or not isinstance(windows, dict):
        raise ValueError(f"invalid worksheet window cache: {path}")
    return lookahead, {
        str(key): dict(value)
        for key, value in windows.items()
        if isinstance(value, dict)
    }


def _model_window(
    client: Any,
    tables: tuple[_RawTable, ...],
    index: int,
    lookahead: int,
    config: Mapping[str, Any],
) -> Mapping[str, Any]:
    from tax_graph.config import get_config_value, resolve_llm_model, resolve_llm_seed

    chunk = tables[index : index + 1 + lookahead]
    prompt = (
        "Decide where ONE worksheet ends in an IRS instruction booklet.\n\n"
        "You are given a CANDIDATE table and the tables that FOLLOW it in printed order. "
        "Decide whether the candidate starts a worksheet, and if it does, which following "
        "tables belong to the SAME worksheet. A worksheet may contain a caption table, a "
        "numbered body, a continuation, and parameter grids. A standalone lookup chart is "
        "not part of the worksheet even when adjacent. Return table ids only; do not "
        "transcribe row text.\n\n"
        f"candidate table id: {tables[index].table_id}\n\n"
        + "\n\n".join(_table_window_text(table) for table in chunk)
        + "\n"
    )
    request: dict[str, Any] = {
        "prompt": prompt,
        "schema": window_schema(),
        "model": resolve_llm_model(config, "micro"),
        "max_tokens": int(get_config_value(dict(config), "extraction.worksheet_window_max_tokens", 6000)),
        "temperature": get_config_value(dict(config), "llm.temperature"),
        "purpose": "tax_graph_worksheet_window",
    }
    seed = resolve_llm_seed(config)
    if seed is not None:
        request["seed"] = seed
    response = client.structured_completion(**request)
    if not isinstance(response, Mapping):
        raise ValueError("worksheet window provider returned a non-object")
    return response


def _call_window_provider(
    tables: tuple[_RawTable, ...],
    source_text: str,
    index: int,
    lookahead: int,
    *,
    classifier: Any,
    config: Mapping[str, Any],
) -> Mapping[str, Any]:
    table = tables[index]
    chunk = tables[index : index + 1 + lookahead]
    if hasattr(classifier, "segment_window"):
        response = classifier.segment_window(table, source_text, lookahead, chunk)
    elif hasattr(classifier, "structured_completion"):
        response = _model_window(classifier, tables, index, lookahead, config)
    elif callable(classifier):
        try:
            response = classifier(table, source_text, lookahead, chunk)
        except TypeError:
            response = classifier(table, source_text)
    else:
        raise ValueError("worksheet window provider returned no result")
    if not isinstance(response, Mapping):
        raise ValueError("worksheet window provider returned a non-object")
    return response


def _window_observation(
    source_text: str,
    tables: tuple[_RawTable, ...],
    index: int,
    lookahead: int,
    payload: Mapping[str, Any] | None,
) -> WorksheetWindow:
    """Validate one cached/provider response and retain a source span."""
    table = tables[index]
    source_end = tables[min(len(tables) - 1, index + lookahead)].end
    evidence_prefix = (
        f"anchor_table_id={table.table_id}",
        f"source_span={table.start}:{source_end}",
    )
    if payload is None:
        finding = WorksheetFinding(
            "window_cache_missing",
            f"no seeded worksheet window exists for table {table.table_id}",
            evidence_prefix,
        )
        return WorksheetWindow(table.table_id, False, "", (), (), (), table.start, source_end, finding)
    if payload.get("error"):
        finding = WorksheetFinding(
            "window_provider_failed",
            f"worksheet window for table {table.table_id} failed: {payload['error']}",
            evidence_prefix,
        )
        return WorksheetWindow(table.table_id, False, "", (), (), (), table.start, source_end, finding)
    if payload.get("anchor_table_id") is not None and payload.get("anchor_table_id") != table.table_id:
        finding = WorksheetFinding(
            "window_cache_entry_misaligned",
            f"worksheet window cache entry is keyed to table {payload.get('anchor_table_id')}, not table {table.table_id}",
            evidence_prefix,
        )
        return WorksheetWindow(table.table_id, False, "", (), (), (), table.start, source_end, finding)
    starts = payload.get("starts_a_worksheet")
    title = str(payload.get("title") or "").strip()
    raw_ids = payload.get("table_ids") or []
    raw_parameter_ids = payload.get("parameter_table_ids") or []
    raw_serves_lines = payload.get("serves_lines") or []
    if not isinstance(starts, bool) or not isinstance(raw_ids, list) or not isinstance(raw_parameter_ids, list) or not isinstance(raw_serves_lines, list):
        finding = WorksheetFinding(
            "window_response_invalid",
            f"worksheet window for table {table.table_id} has the wrong response shape",
            evidence_prefix,
        )
        return WorksheetWindow(table.table_id, False, title, (), (), (), table.start, source_end, finding)
    try:
        table_ids = tuple(int(value) for value in raw_ids)
        parameter_ids = tuple(int(value) for value in raw_parameter_ids)
        serves_lines = tuple(str(value) for value in raw_serves_lines)
    except (TypeError, ValueError) as exc:
        finding = WorksheetFinding(
            "window_response_invalid",
            f"worksheet window for table {table.table_id} contains non-typed ids: {exc}",
            evidence_prefix,
        )
        return WorksheetWindow(table.table_id, False, title, (), (), (), table.start, source_end, finding)
    if not starts:
        return WorksheetWindow(table.table_id, False, title, (), (), serves_lines, table.start, source_end)
    by_id = {candidate.table_id: candidate for candidate in tables[index : index + 1 + lookahead]}
    expected_order = [candidate.table_id for candidate in tables[index : index + 1 + lookahead]]
    invalid_ids = [table_id for table_id in table_ids if table_id not in by_id]
    duplicate_ids = len(set(table_ids)) != len(table_ids)
    out_of_order = [table_id for table_id in table_ids if table_id in by_id]
    invalid_parameters = [table_id for table_id in parameter_ids if table_id not in table_ids]
    if (
        not title
        or table.table_id not in table_ids
        or not table_ids
        or invalid_ids
        or duplicate_ids
        or out_of_order != [table_id for table_id in expected_order if table_id in table_ids]
        or invalid_parameters
    ):
        details = list(evidence_prefix)
        if invalid_ids:
            details.append(f"invalid_table_ids={','.join(str(value) for value in invalid_ids)}")
        if invalid_parameters:
            details.append(f"invalid_parameter_table_ids={','.join(str(value) for value in invalid_parameters)}")
        finding = WorksheetFinding(
            "window_response_invalid",
            f"worksheet window for table {table.table_id} contains an invalid worksheet claim",
            tuple(details),
        )
        return WorksheetWindow(table.table_id, False, title, table_ids, parameter_ids, serves_lines, table.start, source_end, finding)
    return WorksheetWindow(
        table.table_id,
        True,
        title,
        table_ids,
        parameter_ids,
        serves_lines,
        table.start,
        source_end,
    )


def _is_html_source(source_text: str) -> bool:
    return "<table" in source_text.lower()


def _source_tables(source_text: str) -> tuple[_RawTable, ...]:
    parser = _RowParser(source_text)
    parser.feed(source_text)
    parser.close()
    headings = parse_headings(source_text)
    return tuple(
        replace(
            table,
            heading=max(
                (heading for heading in headings if heading.source_end <= table.start),
                key=lambda heading: heading.source_end,
                default=None,
            ),
        )
        for table in parser.tables
    )


def _semantic_worksheet_title(value: str) -> str:
    """Remove source navigation suffixes while retaining the printed title."""
    title = re.sub(r"\s*[- ]*continued\s*$", "", value, flags=re.IGNORECASE)
    title = re.sub(
        r"\s*[- ]*schedule\s+[0-9]+[a-z]?\s*,?\s+lines?\s+.+$",
        "",
        title,
        flags=re.IGNORECASE,
    )
    title = re.sub(r"\s*[- ]*lines?\s+.+$", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+lines?\s+.+$", "", title, flags=re.IGNORECASE)
    return title.strip(" -:") or value.strip()


def _heading_lines(value: str) -> tuple[str, ...]:
    """Read printed line tokens from the table's own heading."""
    match = re.search(r"\blines?\b(?P<tail>.*)$", value, re.IGNORECASE)
    if match is None:
        return ()
    tokens = re.findall(r"\b[0-9]+[a-z]?\b", match.group("tail"), re.IGNORECASE)
    return tuple(dict.fromkeys(token.lower() for token in tokens))


def harvest_worksheet(
    source_text: str,
    target: WorksheetTarget | Mapping[str, Any],
    *,
    source_document_id: str | None = None,
    year: str | int = "2025",
    oracle_source_text: str | None = None,
    oracle_heading_text: str | None = None,
    _tables: tuple[_RawTable, ...] | None = None,
    _parameter_table_ids: tuple[int, ...] = (),
    _initial_findings: tuple[WorksheetFinding, ...] = (),
    _window: WorksheetWindow | None = None,
    _advisories_enabled: bool = False,
    _allow_same_title_group: bool = False,
) -> WorksheetHarvest:
    """Harvest one worksheet using HTML structure and an optional text oracle.

    ``_allow_same_title_group`` is an internal seam for document-wide discovery:
    repeated source tables with one normalized title have already passed the
    merge ambiguity check and may be harvested as one logical worksheet.  A
    direct title-targeted call keeps the stricter single-heading behavior.
    """
    resolved_target = _coerce_target(target)
    year_text = str(year)
    source_id = source_document_id or resolved_target.source_document_id or ""
    tables = _tables
    start_heading: InstructionHeading | None = None
    if _is_html_source(source_text):
        headings = _source_headings(source_text)
        start_candidates = _find_start_headings(headings, resolved_target)
        same_title_group = (
            _allow_same_title_group
            and bool(start_candidates)
            and len({_semantic_worksheet_title(candidate.text) for candidate in start_candidates}) == 1
        )
        if len(start_candidates) > 1 and not _is_one_logical_heading(start_candidates) and not same_title_group:
            finding = _start_heading_finding(resolved_target, source_id, start_candidates)
            return _blocked_harvest(
                resolved_target,
                year_text,
                source_id,
                (finding,),
                observed_start_anchor=resolved_target.start_anchor,
            )
        tables = tables or _tables_for_target(source_text, resolved_target)
        if not tables:
            finding = _start_heading_finding(
                resolved_target,
                source_id,
                _find_start_headings(headings, resolved_target),
            )
            return _blocked_harvest(
                resolved_target,
                year_text,
                source_id,
                (finding,),
                observed_start_anchor=resolved_target.start_anchor,
            )
        start_heading = tables[0].heading
        parameter_ids = set(_parameter_table_ids)
        rows = tuple(
            replace(row, table_id=1)
            for row in sorted(
                (
                    row
                    for table in tables
                    if table.table_id not in parameter_ids
                    for row in table.rows
                ),
                key=lambda candidate: candidate.start,
            )
        )
    else:
        headings = _source_headings(source_text)
        start_candidates = _find_start_headings(headings, resolved_target)
        if len(start_candidates) != 1:
            finding = _start_heading_finding(resolved_target, source_id, start_candidates)
            return _blocked_harvest(
                resolved_target,
                year_text,
                source_id,
                (finding,),
                observed_start_anchor=resolved_target.start_anchor,
            )
        start_heading = start_candidates[0]
        rows = tuple(row for row in _source_rows(source_text) if row.start >= start_heading.source_end)
    assert start_heading is not None
    observed_start_anchor = start_heading.anchor_id or resolved_target.start_anchor
    selected, line_rows, terminal_row, findings = _discover_extent(
        rows,
        source_text,
        target=resolved_target,
    )
    if _has_fatal_findings(findings):
        return _blocked_harvest(
            resolved_target,
            year_text,
            source_id,
            tuple(findings),
            worksheet_source_span=(start_heading.source_start, terminal_row.end)
            if terminal_row is not None
            else None,
            observed_start_anchor=observed_start_anchor,
        )

    assert terminal_row is not None
    assert line_rows
    conditions = _conditions_for_lines(line_rows, source_text)
    citations, citation_for_line = _build_citations(
        source_text,
        resolved_target,
        source_id,
        line_rows,
        oracle_source_text=oracle_source_text,
    )
    nodes = _build_line_nodes(
        source_text,
        resolved_target,
        citation_for_line,
        line_rows,
        conditions,
    )
    parameter_nodes, parameter_edges = _build_constant_nodes(
        source_text,
        resolved_target,
        citation_for_line,
        line_rows,
    )
    edges = [
        *parameter_edges,
        *_build_line_reference_edges(source_text, resolved_target, citation_for_line, line_rows),
    ]
    nodes = [*nodes, *parameter_nodes]
    document = _document_object(resolved_target, year_text, source_id, start_heading)
    all_findings = [*_initial_findings, *findings]
    if oracle_source_text is not None:
        missing_ranges = tuple(
            str(citation.get("citation_id"))
            for citation in citations
            if citation.get("kind") == "row" and not citation.get("ranges")
        )
        if missing_ranges:
            all_findings.append(
                WorksheetFinding(
                    "source_range_missing",
                    "one or more worksheet row citations could not be mapped to rendered source ranges",
                    missing_ranges,
                )
            )
    all_findings.extend(_count_findings(resolved_target, line_rows, parameter_nodes))
    all_objects = [document, *nodes, *edges, *citations]
    all_findings.extend(_verify_harvest_objects(source_text, all_objects, oracle_source_text=oracle_source_text))
    markdown_lines: tuple[str, ...] | None = None
    if oracle_source_text is not None:
        markdown_lines = _markdown_extent_lines(
            oracle_source_text,
            resolved_target.title,
            heading_text=oracle_heading_text,
        )
        if markdown_lines is not None:
            html_lines = tuple(sorted(line_rows, key=_line_sort_key))
            if markdown_lines != html_lines:
                all_findings.append(
                    WorksheetFinding(
                        "html_markdown_extent_disagreement",
                        "HTML table extent disagrees with rendered-text extent oracle",
                        (
                            f"html_lines={','.join(html_lines)}",
                            f"markdown_lines={','.join(markdown_lines)}",
                        ),
                    )
                )
        else:
            html_lines = tuple(sorted(line_rows, key=_line_sort_key))
    else:
        html_lines = tuple(sorted(line_rows, key=_line_sort_key))
    if _has_fatal_findings(all_findings):
        return _blocked_harvest(
            resolved_target,
            year_text,
            source_id,
            tuple(all_findings),
            worksheet_source_span=(start_heading.source_start, terminal_row.end),
            observed_start_anchor=observed_start_anchor,
            markdown_lines=markdown_lines,
            html_lines=html_lines,
        )
    return WorksheetHarvest(
        target=resolved_target,
        year=year_text,
        source_document_id=source_id,
        start_anchor=observed_start_anchor,
        document=document,
        nodes=tuple(nodes),
        edges=tuple(edges),
        citations=tuple(citations),
        conditions=tuple(conditions),
        findings=tuple(_dedupe_findings(all_findings)),
        worksheet_source_span=(start_heading.source_start, terminal_row.end),
        markdown_lines=markdown_lines,
        html_lines=html_lines,
        window=_window,
        advisories_enabled=_advisories_enabled,
    )


def harvest_worksheet_file(
    path: str | Path,
    target: WorksheetTarget | Mapping[str, Any],
    *,
    source_document_id: str | None = None,
    year: str | int = "2025",
    advisories_enabled: bool = False,
) -> WorksheetHarvest:
    """Read an acquired file and use a sibling rendered text file as oracle."""
    source_path = Path(path)
    oracle_source_text = None
    if _is_html_source(source_path.read_text(encoding="ascii")):
        rendered_path = source_path.with_suffix(".txt")
        if rendered_path.exists():
            oracle_source_text = rendered_path.read_text(encoding="ascii")
    return harvest_worksheet(
        source_path.read_text(encoding="ascii"),
        target,
        source_document_id=source_document_id,
        year=year,
        oracle_source_text=oracle_source_text,
        _advisories_enabled=advisories_enabled,
    )


def harvest_worksheets(
    source_text: str,
    *,
    source_document_id: str,
    year: str | int = "2025",
    title: str | None = None,
    classifier: Any | None = None,
    window_classifier: Any | None = None,
    config: Mapping[str, Any] | None = None,
    cache_path: str | Path | None = None,
    window_cache_path: str | Path | None = None,
    lookahead: int = WINDOW_LOOKAHEAD,
    oracle_source_text: str | None = None,
) -> WorksheetDiscovery:
    """Discover and harvest every worksheet table in one instruction document.

    The cached per-table classifier is the candidate gate.  Only its
    ``worksheet`` tables open a sliding window.  The window model returns
    table ids, never row text.  First anchor in printed order wins when
    overlapping windows claim the same table; the later claim is retained as a
    printed-disagreement finding.  ``window_classifier`` exists for recorded
    fixtures and provider-contract tests; the normal pipeline reads its seeded
    window cache.
    """
    year_text = str(year)
    tables = _source_tables(source_text) if _is_html_source(source_text) else ()
    if not tables:
        return WorksheetDiscovery(source_document_id, year_text, (), ())
    settings = dict(config or {})
    classification_cache = Path(cache_path) if cache_path is not None else None
    classifications = classify_worksheet_tables(
        source_text,
        classifier=classifier,
        config=settings,
        cache_path=classification_cache,
    )
    cache_file = Path(window_cache_path) if window_cache_path is not None else None
    if cache_file is None and cache_path is not None and Path(cache_path).name.endswith(".worksheet_windows.yaml"):
        cache_file = Path(cache_path)
    cached_lookahead, cached = _load_window_cache(cache_file)
    active_lookahead = cached_lookahead if cache_file is not None and cache_file.exists() else lookahead
    if active_lookahead < 1:
        raise ValueError("worksheet window lookahead must be positive")
    table_by_id = {table.table_id: table for table in tables}
    table_index = {table.table_id: index for index, table in enumerate(tables)}
    windows: list[WorksheetWindow] = []
    window_position: dict[int, int] = {}
    findings: list[WorksheetFinding] = []
    inventory: list[WorksheetFinding] = []
    candidate_indices: list[int] = []
    for index, (table, classification) in enumerate(zip(tables, classifications)):
        if classification.finding is not None:
            findings.append(classification.finding)
            continue
        if classification.kind != "worksheet":
            inventory.append(
                WorksheetFinding(
                    "classified_not_emitted",
                    f"table {table.table_id} classified as {classification.kind} and was not emitted",
                    (
                        f"table_id={table.table_id}",
                        f"heading={classification.heading or '(none)'}",
                        f"kind={classification.kind}",
                    ),
                )
            )
            continue
        candidate_indices.append(index)
    for index in candidate_indices:
        table = tables[index]
        fingerprint = window_fingerprint(source_text, tables, index, active_lookahead)
        payload = cached.get(fingerprint)
        if payload is None and window_classifier is not None:
            try:
                payload = dict(
                    _call_window_provider(
                        tables,
                        source_text,
                        index,
                        active_lookahead,
                        classifier=window_classifier,
                        config=settings,
                    )
                )
            except Exception as exc:  # noqa: BLE001 - one window must not kill the batch
                payload = {"error": f"{type(exc).__name__}: {exc}"[:300]}
        observation = _window_observation(
            source_text,
            tables,
            index,
            active_lookahead,
            payload,
        )
        windows.append(observation)
        window_position[observation.anchor_table_id] = len(windows) - 1
        if observation.finding is not None:
            findings.append(observation.finding)

    wanted = normalize_printed_title(title) if title else None
    worksheets: list[WorksheetHarvest] = []
    claimed: dict[int, int] = {}
    claims: list[tuple[WorksheetWindow, tuple[_RawTable, ...], tuple[WorksheetFinding, ...]]] = []
    for observation in windows:
        if observation.finding is not None or not observation.starts_a_worksheet:
            if observation.finding is None:
                inventory.append(
                    WorksheetFinding(
                        "table_not_worksheet",
                        f"table {observation.anchor_table_id} did not start a worksheet in its window",
                        (f"table_id={observation.anchor_table_id}", "reason=window_no_start"),
                    )
                )
            continue
        overlap = tuple(table_id for table_id in observation.table_ids if table_id in claimed)
        if overlap:
            finding = WorksheetFinding(
                "window_claim_overlap",
                f"window anchored at table {observation.anchor_table_id} claimed already-owned table ids; first anchor wins",
                tuple(
                    [f"anchor_table_id={observation.anchor_table_id}"]
                    + [f"overlap_table_id={table_id}" for table_id in overlap]
                ),
            )
            findings.append(finding)
            windows[window_position[observation.anchor_table_id]] = replace(observation, finding=finding)
            continue
        selected_tables = tuple(table_by_id[table_id] for table_id in observation.table_ids)
        for table_id in observation.table_ids:
            claimed[table_id] = observation.anchor_table_id
        edge_findings: list[WorksheetFinding] = []
        anchor_index = table_index[observation.anchor_table_id]
        window_end_index = min(len(tables) - 1, anchor_index + active_lookahead)
        if (
            observation.table_ids
            and anchor_index + active_lookahead < len(tables)
            and table_index[observation.table_ids[-1]] == window_end_index
        ):
            edge_findings.append(
                WorksheetFinding(
                    "worksheet_window_reached_edge",
                    f"worksheet claim from table {observation.anchor_table_id} reaches the lookahead edge",
                    (
                        f"anchor_table_id={observation.anchor_table_id}",
                        f"lookahead={active_lookahead}",
                        f"table_ids={','.join(str(table_id) for table_id in observation.table_ids)}",
                    ),
                )
            )
        claims.append((observation, selected_tables, tuple(edge_findings)))

    for observation, selected_tables, edge_findings in claims:
        title_text = _semantic_worksheet_title(observation.title)
        first_table = selected_tables[0]
        if wanted and not _title_matches(title_text, wanted):
            continue
        if not _has_printed_worksheet_title(title_text):
            findings.append(
                WorksheetFinding(
                    "worksheet_title_missing",
                    f"window at table {observation.anchor_table_id} has no printed worksheet title",
                    tuple(
                        [f"table_id={table.table_id}" for table in selected_tables]
                        + [f"title={observation.title or '(empty)'}"]
                    ),
                )
            )
            for table in selected_tables[1:]:
                inventory.append(
                    WorksheetFinding(
                        "table_merged",
                        f"table {table.table_id} merged into refused untitled window at table {observation.anchor_table_id}",
                        (f"table_id={table.table_id}", f"anchor_table_id={observation.anchor_table_id}"),
                    )
                )
            continue
        target = WorksheetTarget(
            document_id=_discovered_document_id(title_text, year_text),
            title=title_text,
            start_anchor=(first_table.heading.anchor_id if first_table.heading is not None else "")
            or f"table-{first_table.table_id}",
            source_document_id=source_document_id,
        )
        oracle_heading = first_table.heading.text if len(selected_tables) == 1 else None
        try:
            harvest = harvest_worksheet(
                source_text,
                target,
                source_document_id=source_document_id,
                year=year_text,
                oracle_source_text=oracle_source_text,
                oracle_heading_text=oracle_heading,
                _tables=selected_tables,
                _parameter_table_ids=observation.parameter_table_ids,
                _initial_findings=edge_findings,
                _window=observation,
                _advisories_enabled=True,
                _allow_same_title_group=True,
            )
        except Exception as exc:
            harvest = _blocked_harvest(
                target,
                year_text,
                source_document_id,
                (
                    WorksheetFinding(
                        "worksheet_harvest_failed",
                        f"worksheet {target.document_id} harvest failed: {exc}",
                        tuple(f"table_id={table.table_id}" for table in selected_tables),
                    ),
                ),
            )
        worksheets.append(replace(harvest, window=observation, source_table_ids=observation.table_ids))
        for table in selected_tables[1:]:
            inventory.append(
                WorksheetFinding(
                    "table_merged",
                    f"table {table.table_id} merged into {target.document_id}",
                    (
                        f"table_id={table.table_id}",
                        f"document_id={target.document_id}",
                        f"normalized_title={normalize_printed_title(title_text)}",
                    ),
                )
            )
    return WorksheetDiscovery(
        source_document_id=source_document_id,
        year=year_text,
        classifications=classifications,
        windows=tuple(windows),
        worksheets=tuple(worksheets),
        findings=tuple(findings),
        inventory=tuple(inventory),
    )


def harvest_worksheets_file(
    path: str | Path,
    *,
    source_document_id: str,
    year: str | int = "2025",
    title: str | None = None,
    classifier: Any | None = None,
    window_classifier: Any | None = None,
    config: Mapping[str, Any] | None = None,
    cache_path: str | Path | None = None,
    window_cache_path: str | Path | None = None,
    lookahead: int = WINDOW_LOOKAHEAD,
) -> WorksheetDiscovery:
    """Discover worksheets from HTML and pair it with sibling Markdown text."""
    source_path = Path(path)
    source_text = source_path.read_text(encoding="ascii")
    rendered_path = source_path.with_suffix(".txt")
    oracle_text = rendered_path.read_text(encoding="ascii") if rendered_path.exists() else None
    resolved_classification_cache = cache_path
    if resolved_classification_cache is None or Path(resolved_classification_cache).name.endswith(".worksheet_windows.yaml"):
        resolved_classification_cache = source_path.with_suffix(".worksheet_tables.yaml")
    resolved_window_cache = window_cache_path
    if resolved_window_cache is None:
        resolved_window_cache = (
            cache_path
            if cache_path is not None and Path(cache_path).name.endswith(".worksheet_windows.yaml")
            else source_path.with_suffix(".worksheet_windows.yaml")
        )
    return harvest_worksheets(
        source_text,
        source_document_id=source_document_id,
        year=year,
        title=title,
        classifier=classifier,
        window_classifier=window_classifier,
        config=config,
        cache_path=resolved_classification_cache,
        window_cache_path=resolved_window_cache,
        lookahead=lookahead,
        oracle_source_text=oracle_text,
    )


def _source_headings(source_text: str) -> tuple[InstructionHeading, ...]:
    """Parse either acquired HTML headings or rendered-text headings."""
    if _is_html_source(source_text):
        return parse_headings(source_text)
    return _parse_text_headings(source_text)


def _source_rows(source_text: str) -> tuple[_RawRow, ...]:
    """Parse either HTML tables or numbered rows from rendered instruction text."""
    if _is_html_source(source_text):
        parser = _RowParser(source_text)
        parser.feed(source_text)
        parser.close()
        return tuple(parser.rows)
    return _parse_text_rows(source_text)


def _tables_for_target(source_text: str, target: WorksheetTarget) -> tuple[_RawTable, ...]:
    """Select the table carrying a title, including an explicit continuation."""
    wanted = _normalize_title(target.title)
    tables = _source_tables(source_text)
    matches = tuple(
        table
        for table in tables
        if table.heading is not None
        and (
            _title_matches(table.heading.text, wanted)
            or _title_matches(_semantic_worksheet_title(table.heading.text), wanted)
        )
    )
    if len(matches) <= 1:
        return matches
    base = tuple(table for table in matches if _first_table_line(table) == "1")
    if not base:
        return matches
    continued = tuple(
        table
        for table in matches
        if table not in base
        and table.heading is not None
        and re.search(r"continued\s*$", table.heading.text, re.IGNORECASE)
    )
    return (base[0], *continued)


def _markdown_extent_lines(
    source_text: str,
    title: str,
    *,
    heading_text: str | None = None,
) -> tuple[str, ...] | None:
    """Walk numbered Markdown rows until the next heading boundary.

    When ``heading_text`` is supplied, only that exact source heading is used.
    This lets document-wide discovery compare a continued table with its own
    continuation rather than silently combining two source tables.  A
    title-targeted harvest intentionally combines a base heading and its
    continued heading.
    """
    headings = _parse_text_headings(source_text)
    if heading_text is not None:
        wanted_heading = normalize_printed_title(_semantic_worksheet_title(heading_text))
        continuation = bool(re.search(r"continued\s*$", heading_text, re.IGNORECASE))
        selected_headings = tuple(
            heading
            for heading in headings
            if normalize_printed_title(_semantic_worksheet_title(heading.text)) == wanted_heading
            and bool(re.search(r"continued\s*$", heading.text, re.IGNORECASE)) == continuation
        )
    else:
        wanted = _normalize_title(title)
        selected_headings = tuple(
            heading
            for heading in headings
            if (
                _title_matches(heading.text, wanted)
                or _source_title_prefix_matches(heading.text, wanted)
            )
            and not re.search(r"continued\s*$", heading.text, re.IGNORECASE)
        )
        continuations = tuple(
            heading
            for heading in headings
            if (
                _title_matches(heading.text, wanted)
                or _source_title_prefix_matches(heading.text, wanted)
            )
            and re.search(r"continued\s*$", heading.text, re.IGNORECASE)
        )
        selected_headings = selected_headings + continuations
    if not selected_headings:
        return None
    selected_headings = tuple(sorted(selected_headings, key=lambda item: item.source_start))
    line_tokens: list[str] = []
    for index, heading in enumerate(selected_headings):
        next_selected = (
            selected_headings[index + 1].source_start
            if index + 1 < len(selected_headings)
            else len(source_text)
        )
        next_boundary = next(
            (
                candidate.source_start
                for candidate in headings
                if candidate.source_start > heading.source_start
                and candidate.level <= heading.level
            ),
            len(source_text),
        )
        end = min(next_selected, next_boundary)
        for row in _parse_text_rows(source_text[heading.source_end:end]):
            line = _source_line(row)
            if line is not None:
                line_tokens.append(line)
    return tuple(sorted(dict.fromkeys(line_tokens), key=_line_sort_key))


def _parse_text_headings(source_text: str) -> tuple[InstructionHeading, ...]:
    """Parse Markdown-style headings from the acquired rendered text."""
    headings: list[InstructionHeading] = []
    offset = 0
    after_page_marker = False
    for line in source_text.splitlines(keepends=True):
        raw = line.rstrip("\r\n")
        stripped = raw.strip()
        match = re.match(r"^(?P<marks>#{1,6})\s+(?P<title>.+?)\s*$", stripped)
        if match:
            headings.append(
                InstructionHeading(
                    level=len(match.group("marks")),
                    anchor_id="",
                    text=_normalize_text(match.group("title")),
                    source_start=offset,
                    source_end=offset + len(raw),
                )
            )
            after_page_marker = stripped.lower().startswith("# page ")
        elif after_page_marker and "worksheet" in stripped.lower():
            headings.append(
                InstructionHeading(
                    level=2,
                    anchor_id="",
                    text=_normalize_text(stripped),
                    source_start=offset,
                    source_end=offset + len(raw),
                )
            )
            after_page_marker = False
        elif stripped:
            after_page_marker = False
        offset += len(line)
    return tuple(headings)


def _parse_text_rows(source_text: str) -> tuple[_RawRow, ...]:
    """Parse numbered worksheet rows from the rendered source text."""
    rows: list[_RawRow] = []
    offset = 0
    for line in source_text.splitlines(keepends=True):
        raw = line.rstrip("\r\n")
        stripped = raw.strip()
        line_match = re.match(
            r"^\s*(?:\|\s*)?(?P<line>[0-9]+[a-z]?)\s*[.)]\s*(?P<body>.*?)(?:\s*\|\s*)?$",
            raw,
            re.IGNORECASE,
        )
        table_line_match = re.match(
            r"^\s*\|\s*(?P<line>[0-9]+[a-z]?)\s*\|\s*(?P<body>.*)$",
            raw,
            re.IGNORECASE,
        )
        if line_match:
            token = line_match.group("line").lower()
            body = line_match.group("body").strip()
            if not body and re.fullmatch(r"\s*[0-9]+\s*", raw):
                text = ""
                cells = ("",)
            else:
                text = _normalize_text(f"{token}. {body}")
                cells = (f"{token}.", body)
        elif table_line_match:
            token = table_line_match.group("line").lower()
            body = table_line_match.group("body").strip().rstrip("|").strip()
            text = _normalize_text(f"{token}. {body}")
            cells = (token, body)
        elif re.match(r"^\s*\|?\s*---(?:\s*\|\s*---)+", raw):
            text = ""
            cells = ("",)
        elif re.fullmatch(r"\s*[0-9]+\s*", raw):
            text = ""
            cells = ("",)
        elif stripped:
            text = _normalize_text(stripped)
            cells = (stripped,)
        else:
            text = ""
            cells = ("",)
        rows.append(
            _RawRow(
                table_id=1,
                start=offset,
                end=offset + len(raw),
                cells=cells,
                text=text,
            )
        )
        offset += len(line)
    return tuple(rows)


def write_worksheet_draft(harvest: WorksheetHarvest, draft_dir: str | Path) -> Path:
    """Write a successful harvest beneath an explicit ``_drafts`` directory.

    This writer is deliberately separate from :func:`harvest_worksheet` and
    refuses live graph paths.  It writes only schema-shaped objects to the
    standard draft files; source witnesses and completeness findings stay in
    ``harvest.yaml`` for review and later promotion tooling.
    """
    if not harvest.ok:
        raise ValueError("cannot write a blocked worksheet harvest")
    output = Path(draft_dir).resolve()
    if "_drafts" not in {part.lower() for part in output.parts}:
        raise ValueError(f"worksheet drafts must be beneath a _drafts directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    _write_yaml(output / "documents.yaml", [harvest.document.as_dict()])
    _write_yaml(output / "nodes.yaml", [node.as_dict() for node in harvest.nodes])
    _write_yaml(output / "edges.yaml", [edge.as_dict() for edge in harvest.edges])
    _write_yaml(output / "citations.yaml", [citation.as_dict() for citation in harvest.citations])
    (output / "harvest.yaml").write_text(
        yaml.safe_dump(harvest.as_dict(), sort_keys=False, allow_unicode=False),
        encoding="ascii",
        newline="\n",
    )
    return output


def rebind_worksheet_draft_ranges(
    draft_dir: str | Path,
    *,
    source_text: str,
    target: WorksheetTarget,
) -> Path:
    """Regenerate draft citation text and ranges from acquired source text.

    This is the bounded re-promotion seam for already-harvested worksheet
    drafts.  It preserves object ids and node references while replacing the
    fused citation payload with source-owned ranges and adding any explicit
    note or routing chunks discovered between numbered rows.
    """
    output = Path(draft_dir).resolve()
    citation_path = output / "citations.yaml"
    if not citation_path.exists():
        raise FileNotFoundError(f"worksheet draft citations are missing: {citation_path}")
    citations = yaml.safe_load(citation_path.read_text(encoding="ascii")) or []
    rows = _source_text_rows_for_target(source_text, target)
    line_names = tuple(
        sorted(
            {
                str(line)
                for citation in citations
                for line in _citation_lines(citation)
                if str(line)
            },
            key=_line_sort_key,
        )
    )
    line_ranges, gaps = _source_ranges_for_lines(source_text, rows, line_names)
    missing = [line for line in line_names if not line_ranges.get(line)]
    if missing:
        raise ValueError(
            f"worksheet citation ranges could not be derived for {target.document_id}: "
            f"{','.join(missing)}"
        )
    existing_ids = {str(citation.get("citation_id")) for citation in citations}
    for citation in citations:
        lines = _citation_lines(citation)
        if not lines:
            continue
        # Fresh drafts already carry the source-owned ranges and their
        # normalized quote from the HTML/oracle join.  Rebinding is a repair
        # seam for older drafts, not a second extent algorithm that may erase
        # legitimate multi-column ranges or replace the stored quote with a
        # broader row fallback.
        ranges = tuple(
            dict(item)
            for item in citation.get("ranges") or ()
            if isinstance(item, Mapping)
        )
        if not ranges:
            ranges = tuple(
                source_range
                for line in lines
                for source_range in line_ranges[line]
            )
            citation["quoted_text"] = _source_quote_for_ranges(source_text, ranges)
            citation["ranges"] = list(ranges)
        citation.setdefault("kind", "row")
    for gap_index, gap in enumerate(gaps):
        suffix = _slug(f"{gap['kind']}_after_{gap['after_line']}_{gap_index}")
        citation_id = (
            f"cite_{_slug(target.document_id)}_"
            f"{suffix}"
        )
        if citation_id in existing_ids:
            continue
        ranges = gap["ranges"]
        citations.append(
            {
                "citation_id": citation_id,
                "document_id": target.document_id,
                "source_document_id": target.source_document_id or "",
                "locator": (
                    f"source_document={target.source_document_id or ''};"
                    f"worksheet={target.title};after={gap['after_line']}"
                ),
                "quoted_text": _source_quote_for_ranges(source_text, ranges),
                "kind": gap["kind"],
                "governs": gap["governs"],
                "ranges": list(ranges),
            }
        )
    _write_yaml(citation_path, citations)
    return citation_path


def _citation_lines(citation: Mapping[str, Any]) -> tuple[str, ...]:
    """Read the stable printed-line list from a worksheet citation locator."""
    locator = str(citation.get("locator") or "")
    match = re.search(r";lines=([^;]+)$", locator)
    if match is None:
        return ()
    value = match.group(1)
    parts = tuple(part for part in value.split("_") if part)
    if len(parts) == 1:
        return parts
    if all(re.fullmatch(r"[0-9]+", part) for part in parts):
        start, end = (int(parts[0]), int(parts[-1]))
        return tuple(str(number) for number in range(start, end + 1))
    return parts


def write_worksheet_discovery_report(discovery: WorksheetDiscovery, draft_dir: str | Path) -> Path:
    """Persist the complete discovery accounting beside worksheet drafts.

    The report is a run artifact, not promoted graph state.  It keeps
    classified-not-emitted tables, merges, and refusals available after the
    command exits, including worksheets that were not safe to draft.
    """
    output = Path(draft_dir).resolve()
    if "_drafts" not in {part.lower() for part in output.parts}:
        raise ValueError(f"worksheet discovery reports must be beneath a _drafts directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    payload = yaml.safe_dump(discovery.as_dict(), sort_keys=False, allow_unicode=False)
    report_path = output / "worksheet-discovery.yaml"
    report_path.write_text(payload, encoding="ascii", newline="\n")
    # Keep a per-parent copy so a later source-document harvest cannot erase
    # the refusal accounting from an earlier parent.  The canonical filename
    # remains for existing callers and single-document runs.
    source_report = output / f"worksheet-discovery-{_slug(discovery.source_document_id)}.yaml"
    if source_report != report_path:
        source_report.write_text(payload, encoding="ascii", newline="\n")
    return report_path


def _coerce_target(target: WorksheetTarget | Mapping[str, Any]) -> WorksheetTarget:
    if isinstance(target, WorksheetTarget):
        return target
    data = dict(target)
    start_anchor = data.get("start_anchor") or data.get("anchor_id") or data.get("start_anchor_id")
    if not start_anchor:
        raise ValueError("worksheet target requires start_anchor")
    groups = data.get("citation_groups")
    citation_groups = tuple(tuple(str(line) for line in group) for group in groups) if groups else None
    return WorksheetTarget(
        document_id=str(data["document_id"]),
        title=str(data["title"]),
        start_anchor=str(start_anchor),
        source_document_id=str(data.get("source_document_id") or "") or None,
        expected_line_count=(int(data["expected_line_count"]) if data.get("expected_line_count") is not None else None),
        expected_constant_count=(
            int(data["expected_constant_count"]) if data.get("expected_constant_count") is not None else None
        ),
        citation_groups=citation_groups,
    )


def _find_start_headings(
    headings: Iterable[InstructionHeading], target: WorksheetTarget
) -> tuple[InstructionHeading, ...]:
    """Return headings whose normalized printed title identifies the worksheet."""
    wanted = _normalize_title(target.title)
    return tuple(
        heading
        for heading in headings
        if _title_matches(heading.text, wanted)
        or _text_heading_matches(heading.text, wanted)
        or _source_title_prefix_matches(heading.text, wanted)
    )


def _find_start_heading(
    headings: Iterable[InstructionHeading], target: WorksheetTarget
) -> InstructionHeading | None:
    """Return a title match only when the source has exactly one candidate."""
    candidates = _find_start_headings(headings, target)
    return candidates[0] if len(candidates) == 1 else None


def _is_one_logical_heading(headings: tuple[InstructionHeading, ...]) -> bool:
    """Allow only one base heading plus its explicit continuation heading."""
    semantic_titles = {_semantic_worksheet_title(heading.text) for heading in headings}
    base_count = sum(
        not re.search(r"continued\s*$", heading.text, re.IGNORECASE)
        for heading in headings
    )
    return len(semantic_titles) == 1 and base_count <= 1


def _normalize_title(value: str) -> str:
    """Normalize title punctuation, case, and whitespace for exact matching."""
    return normalize_printed_title(value)


def normalize_printed_title(value: str) -> str:
    """Return the stable comparison key for a printed document title."""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = re.sub(r"[\W_]+", " ", normalized, flags=re.UNICODE)
    return " ".join(normalized.split())


def _title_matches(value: str, wanted: str) -> bool:
    """Match a title, allowing IRS line, lines, and continuation suffixes."""
    candidate = _normalize_title(value)
    if candidate == wanted:
        return True
    if not candidate.startswith(wanted):
        return False
    suffix = candidate[len(wanted) :].strip()
    return bool(
        re.fullmatch(r"continued", suffix)
        or re.fullmatch(r"lines?\s+[0-9]+[a-z]?(?:\s+and\s+[0-9]+[a-z]?)*", suffix)
    )


def _text_heading_matches(value: str, wanted: str) -> bool:
    """Match rendered-text headings whose title runs into a line descriptor."""
    return _title_matches(value, wanted)


def _has_printed_worksheet_title(value: str) -> bool:
    """Return whether a classified table has a document title worth emitting.

    ``Step N`` blocks can contain arithmetic or a local worksheet, but the
    printed form has not given that block an independent document identity.
    Keep those tables visible as refusals until the intermediate-node design
    is implemented instead of minting a guessed worksheet document.
    """
    title = _semantic_worksheet_title(value).strip()
    return bool(title) and not re.match(r"^step\s+[0-9]+\b", title, re.IGNORECASE)


def _start_heading_finding(
    target: WorksheetTarget,
    source_document_id: str,
    candidates: tuple[InstructionHeading, ...],
) -> WorksheetFinding:
    """Describe a zero or ambiguous title match with all source candidates."""
    count = len(candidates)
    kind = "missing_start_title" if count == 0 else "ambiguous_start_title"
    evidence = [
        f"source_document_id={source_document_id}",
        f"candidate_count={count}",
    ]
    evidence.extend(
        f"candidate[{index}]={heading.text};anchor={heading.anchor_id or 'missing'}"
        for index, heading in enumerate(candidates)
    )
    return WorksheetFinding(
        kind,
        f"worksheet title matched {count} headings; expected exactly one: {target.title}",
        tuple(evidence),
    )


def _discover_extent(
    rows: Iterable[_RawRow],
    source_text: str,
    *,
    target: WorksheetTarget,
) -> tuple[
    tuple[_RawRow, ...],
    dict[str, tuple[_RawRow, ...]],
    _RawRow | None,
    list[WorksheetFinding],
]:
    rows = tuple(rows)
    line_rows: dict[str, list[_RawRow]] = {}
    selected: list[_RawRow] = []
    findings: list[WorksheetFinding] = []
    current_line: str | None = None
    expected: int | None = None
    table_id: int | None = None
    terminal: _RawRow | None = None
    for row in rows:
        line = _row_line(row)
        if table_id is None and (line is not None or row.table_id):
            table_id = row.table_id
        if table_id is not None and row.table_id != table_id:
            break
        if line is None:
            if _is_text_source(source_text) and _is_text_extent_boundary(row.text):
                if current_line is not None:
                    break
                continue
            if not row.text or current_line is None:
                continue
            selected.append(row)
            line_rows[current_line].append(row)
            continue
        if expected is None:
            expected = _line_number(line) + 1
        elif line == current_line:
            selected.append(row)
            line_rows[line].append(row)
            terminal = row
            continue
        elif current_line is not None and _line_number(line) == _line_number(current_line):
            # Printed sub-lines such as 14a/14b and 1a/1b belong to
            # the same numeric sequence position.  Keep each printed
            # address distinct while preserving the next integer expected.
            selected.append(row)
            line_rows.setdefault(line, []).append(row)
            current_line = line
            terminal = row
            continue
        elif _line_number(line) != expected:
            findings.append(
                WorksheetFinding(
                    "line_sequence_gap",
                    f"expected worksheet line {expected}, found {line}",
                    (f"table_id={row.table_id}", f"row_span={row.start}:{row.end}"),
                )
            )
            break
        current_line = line
        line_rows[line] = [row]
        selected.append(row)
        terminal = row
        expected = _line_number(line) + 1

    if not line_rows:
        findings.append(
            WorksheetFinding(
                "missing_numbered_rows",
                "worksheet start was found but no numbered rows followed it",
            )
        )
    if terminal is None:
        findings.append(
            WorksheetFinding(
                "missing_terminal_line",
                "worksheet terminal line was not discovered from the source boundary",
                (f"observed_lines={','.join(line_rows)}",),
            )
        )
    if terminal is not None:
        terminal_line = _row_line(terminal) or ""
        footnote_rows = tuple(line_rows.get(terminal_line, ()))
        marker_text = " ".join(row.text for row in selected if row is not terminal or row.text)
        markers = (
            {"*"}
            if "<" in source_text
            and re.search(r"(?<!\*)\*(?!\*)", marker_text)
            else set()
        )
        footnotes = {"*" for row in footnote_rows if row.text.lstrip().startswith("*")}
        missing = sorted(markers - footnotes)
        if missing:
            findings.append(
                WorksheetFinding(
                    "unresolved_footnote_marker",
                    "one or more worksheet footnote markers have no footnote in the discovered extent",
                    (f"markers={','.join(sorted(markers))}", f"resolved={','.join(sorted(footnotes))}"),
                )
            )
    return tuple(selected), {key: tuple(value) for key, value in line_rows.items() if key}, terminal, findings


def _is_text_extent_boundary(text: str) -> bool:
    """Return whether rendered text marks the end of a selected worksheet."""
    lowered = text.strip().lower()
    return (
        lowered.startswith("# page ")
        or lowered.startswith("## ")
        or lowered.startswith("### ")
        or lowered.startswith("keep for your record")
        or lowered.endswith("worksheetcontinued")
    )


def _is_text_source(source_text: str) -> bool:
    return not _is_html_source(source_text)


def _line_number(line: str) -> int:
    match = re.match(r"[0-9]+", line)
    return int(match.group(0)) if match else -1


def _row_line(row: _RawRow) -> str | None:
    for cell in row.cells:
        match = re.fullmatch(r"\s*([0-9]+[a-z]?)\s*[.)]?\s*", cell, re.IGNORECASE)
        if match:
            return match.group(1).lower()
        match = re.match(r"\s*[\"']?([0-9]+[a-z]?)\s*[.)]\s+", cell, re.IGNORECASE)
        if match:
            return match.group(1).lower()
    return None


def _source_line(row: _RawRow) -> str | None:
    """Return a rendered-source line label without mistaking table values for lines."""
    for cell in row.cells:
        match = re.fullmatch(r"\s*([0-9]+[a-z]?)\s*[.)]\s*", cell, re.IGNORECASE)
        if match:
            return match.group(1).lower()
        match = re.match(r"\s*[\"']?([0-9]+[a-z]?)\s*[.)]\s+", cell, re.IGNORECASE)
        if match:
            return match.group(1).lower()
    return None


def _source_row_line(row: _RawRow) -> str | None:
    """Return a source row's line label, including bare Markdown table cells."""
    line = _source_line(row)
    if line is not None:
        return line
    for cell in row.cells:
        match = re.fullmatch(r"\s*([0-9]+[a-z]?)\s*", cell, re.IGNORECASE)
        if match:
            return match.group(1).lower()
    return None


def _first_table_line(table: _RawTable) -> str | None:
    for row in table.rows:
        line = _row_line(row)
        if line is not None:
            return line
    return None


def _build_citations(
    source_text: str,
    target: WorksheetTarget,
    source_document_id: str,
    line_rows: Mapping[str, tuple[_RawRow, ...]],
    *,
    oracle_source_text: str | None = None,
) -> tuple[tuple[HarvestObject, ...], dict[str, HarvestObject]]:
    line_numbers = tuple(sorted(line_rows, key=_line_sort_key))
    groups = target.citation_groups or tuple((line,) for line in line_numbers)
    citations: list[HarvestObject] = []
    citation_for_line: dict[str, HarvestObject] = {}
    source_rows = (
        _source_text_rows_for_target(oracle_source_text, target)
        if oracle_source_text is not None
        else ()
    )
    source_line_ranges, source_gaps = _source_ranges_for_lines(
        oracle_source_text or "",
        source_rows,
        line_numbers,
        line_faces={
            line: _visible_text(
                source_text[line_rows[line][0].start:line_rows[line][-1].end]
            )
            for line in line_numbers
            if line_rows.get(line)
        },
    )
    for group in groups:
        selected_lines = tuple(line for line in group if line in line_rows)
        if not selected_lines:
            continue
        first = line_rows[selected_lines[0]][0]
        last = line_rows[selected_lines[-1]][-1]
        ranges = tuple(
            source_range
            for line in selected_lines
            for source_range in source_line_ranges.get(line, ())
        )
        quote = (
            _source_quote_for_ranges(oracle_source_text, ranges)
            if oracle_source_text is not None and ranges
            else _visible_text(source_text[first.start:last.end])
        )
        slug = _citation_slug(selected_lines)
        citation_id = f"cite_{_slug(target.document_id)}_lines_{slug}"
        data = {
            "citation_id": citation_id,
            # The citation belongs to the promoted worksheet object while
            # source_document_id preserves the acquired text authority.
            "document_id": target.document_id,
            "source_document_id": source_document_id,
            "locator": (
                f"source_document={source_document_id};"
                f"worksheet={target.title};lines={slug}"
            ),
            "quoted_text": quote,
            "kind": "row",
        }
        if ranges:
            data["ranges"] = list(ranges)
        citation = HarvestObject(
            kind="citation",
            data=data,
            source_quote=quote,
            source_start=(ranges[0]["start"] if ranges else first.start),
            source_end=(ranges[-1]["end"] if ranges else last.end),
            source_spans=tuple(
                (item["start"], item["end"])
                for item in ranges
            ) or ((first.start, last.end),),
        )
        citations.append(citation)
        for line in selected_lines:
            current = citation_for_line.get(line)
            if current is None or _citation_span_size(citation) < _citation_span_size(current):
                citation_for_line[line] = citation
    for gap_index, gap in enumerate(source_gaps):
        kind = gap["kind"]
        governs = gap["governs"]
        after_line = gap["after_line"]
        suffix = _slug(f"{kind}_after_{after_line}_{gap_index}")
        citation_id = f"cite_{_slug(target.document_id)}_{suffix}"
        quote = _source_quote_for_ranges(oracle_source_text, gap["ranges"])
        data = {
            "citation_id": citation_id,
            "document_id": target.document_id,
            "source_document_id": source_document_id,
            "locator": (
                f"source_document={source_document_id};"
                f"worksheet={target.title};after={after_line}"
            ),
            "quoted_text": quote,
            "kind": kind,
            "governs": governs,
            "ranges": list(gap["ranges"]),
        }
        citations.append(
            HarvestObject(
                kind="citation",
                data=data,
                source_quote=quote,
                source_start=gap["ranges"][0]["start"],
                source_end=gap["ranges"][-1]["end"],
                source_spans=tuple(
                    (item["start"], item["end"])
                    for item in gap["ranges"]
                ),
            )
        )
    return tuple(citations), citation_for_line


def _source_text_rows_for_target(
    source_text: str,
    target: WorksheetTarget,
) -> tuple[_RawRow, ...]:
    """Return rendered-source rows inside the target worksheet heading."""
    headings = _parse_text_headings(source_text)
    wanted = _normalize_title(target.title)
    selected = tuple(
        heading
        for heading in headings
        if _title_matches(heading.text, wanted)
        or _source_title_prefix_matches(heading.text, wanted)
    )
    if not selected:
        return ()
    all_rows = _parse_text_rows(source_text)
    selected_rows: list[_RawRow] = []
    for index, heading in enumerate(selected):
        next_selected = (
            selected[index + 1].source_start
            if index + 1 < len(selected)
            else len(source_text)
        )
        next_boundary = next(
            (
                candidate.source_start
                for candidate in headings
                if candidate.source_start > heading.source_start
                and candidate.level <= heading.level
            ),
            len(source_text),
        )
        end = min(next_selected, next_boundary)
        selected_rows.extend(
            row for row in all_rows
            if row.start >= heading.source_end and row.start < end
        )
    return tuple(selected_rows)


def _source_title_prefix_matches(value: str, wanted: str) -> bool:
    """Match renderer headings that weld a worksheet title to its schedule."""
    candidate = re.sub(r"[^a-z0-9]+", "", value.casefold())
    expected = re.sub(r"[^a-z0-9]+", "", wanted.casefold())
    return bool(expected) and candidate.startswith(expected)


def _source_ranges_for_lines(
    source_text: str,
    source_rows: tuple[_RawRow, ...],
    lines: Iterable[str],
    *,
    line_faces: Mapping[str, str] | None = None,
) -> tuple[dict[str, tuple[dict[str, int], ...]], tuple[dict[str, Any], ...]]:
    """Align HTML row faces to rendered source and preserve intervening chunks."""
    if not source_rows:
        return {}, ()
    ordered_lines = tuple(lines)
    start = source_rows[0].start
    end = source_rows[-1].end
    by_line: dict[str, tuple[dict[str, int], ...]] = {}
    positions: list[tuple[str, int]] = []
    cursor = 0
    inline_gaps: list[dict[str, Any]] = []
    for line in ordered_lines:
        face = (line_faces or {}).get(line, "")
        if face:
            aligned, next_cursor = _align_source_face(
                source_text,
                face,
                line=line,
                start=max(start, cursor),
                end=end,
            )
        else:
            aligned_parts: list[dict[str, int]] = []
            next_cursor = max(start, cursor)
            for row in source_rows:
                is_subline = re.fullmatch(r"[0-9]+[a-z]", line, re.IGNORECASE)
                if row.start < next_cursor and not is_subline:
                    continue
                row_ranges = ()
                row_line = _source_row_line(row)
                if row_line == line:
                    row_ranges = _source_row_ranges(source_text, row, line)
                elif is_subline and row_line in {
                    re.match(r"[0-9]+", line).group(0),
                    None,
                }:
                    # Lettered sub-lines share a parent table row.  Do not
                    # apply this fallback to numeric lines: prose such as
                    # ``go to line 3.`` is not a printed row anchor.
                    row_ranges = _source_subrow_ranges(source_text, row, line)
                    if not row_ranges and row_line is not None:
                        # Some Markdown tables print the sub-line output
                        # cells as ``2a 2b`` without a prose anchor.  The
                        # parent row is the only source-owned text available
                        # for that sub-line; keep it rather than matching a
                        # later prose reference such as ``line 2a.``.
                        row_ranges = _source_row_ranges(
                            source_text,
                            row,
                            row_line,
                        )
                if row_ranges:
                    aligned_parts.extend(row_ranges)
                    next_cursor = row_ranges[-1]["end"]
                    break
            aligned = tuple(aligned_parts)
        if not aligned:
            # The HTML face can contain renderer-only punctuation or a
            # continuation fragment that is absent from the acquired text.
            # The printed source row is still an authoritative, bounded
            # fallback; keep the row visible rather than refusing the batch.
            for row in source_rows:
                if _source_row_line(row) != line:
                    continue
                aligned = _source_row_ranges(source_text, row, line)
                if aligned:
                    next_cursor = aligned[-1]["end"]
                break
        if not aligned:
            continue
        aligned = _extend_source_ranges_over_continuations(
            source_text,
            source_rows,
            aligned,
        )
        line_ranges = aligned
        span_start = aligned[0]["start"]
        span_end = aligned[-1]["end"]
        for row in source_rows:
            if row.end <= span_start or row.start >= span_end or not row.text:
                continue
            governed = _governed_source_row(row)
            if governed is None:
                continue
            kind, governs = governed
            governed_start = _governed_source_row_start(source_text, row)
            line_ranges = _subtract_source_interval(
                line_ranges,
                governed_start,
                row.end,
            )
            route_ranges: tuple[dict[str, int], ...] = (
                {"start": governed_start, "end": row.end},
            )
            marker_ranges = _source_marker_ranges_for_row(source_text, row, line)
            for marker in marker_ranges:
                route_ranges = _subtract_source_interval(
                    route_ranges,
                    marker["start"],
                    marker["end"],
                )
            if re.fullmatch(r"[0-9]+[a-z]", line, re.IGNORECASE):
                line_ranges = tuple([*line_ranges, *marker_ranges])
            inline_gaps.append(
                {
                    "after_line": (
                        ordered_lines[ordered_lines.index(line) - 1]
                        if re.fullmatch(r"[0-9]+[a-z]", line, re.IGNORECASE)
                        and ordered_lines.index(line) > 0
                        else line
                    ),
                    "kind": kind,
                    "governs": governs,
                    "ranges": route_ranges,
                }
            )
        by_line[line] = line_ranges
        positions.append((line, aligned[0]["start"], aligned[-1]["end"]))
        cursor = next_cursor

    gaps: list[dict[str, Any]] = [*inline_gaps]
    for previous, current in zip(positions, positions[1:]):
        previous_line, _, previous_end = previous
        _, current_start, _ = current
        gap_start = previous_end
        gap_end = current_start
        gap_text = source_text[gap_start:gap_end]
        content_rows = tuple(
            row
            for row in source_rows
            if row.start >= gap_start and row.end <= gap_end and row.text
        )
        governed_rows = tuple(
            (row, _governed_source_row(row))
            for row in content_rows
            if _governed_source_row(row) is not None
        )
        if not governed_rows:
            continue
        for row, governed in governed_rows:
            assert governed is not None
            kind, governs = governed
            gaps.append(
                {
                    "after_line": previous_line,
                    "kind": kind,
                    "governs": governs,
                    "ranges": ({"start": row.start, "end": row.end},),
                }
            )
    unique_gaps: list[dict[str, Any]] = []
    seen_gaps: set[tuple[Any, ...]] = set()
    for gap in gaps:
        key = (
            gap["kind"],
            tuple(gap["governs"]),
            tuple((item["start"], item["end"]) for item in gap["ranges"]),
        )
        if key in seen_gaps:
            continue
        seen_gaps.add(key)
        unique_gaps.append(gap)
    return by_line, tuple(unique_gaps)


def _extend_source_ranges_over_continuations(
    source_text: str,
    source_rows: tuple[_RawRow, ...],
    ranges: tuple[dict[str, int], ...],
) -> tuple[dict[str, int], ...]:
    """Keep an unnumbered yes/no branch attached to its preceding printed row."""
    if not ranges:
        return ranges
    last_end = max(int(item["end"]) for item in ranges)
    row_index = next(
        (
            index
            for index, row in enumerate(source_rows)
            if row.start < last_end <= row.end
        ),
        None,
    )
    if row_index is None:
        return ranges
    branch_row = re.compile(r"\s*(?:yes|no)\b", re.IGNORECASE)
    if not branch_row.match(source_rows[row_index].text):
        next_row = source_rows[row_index + 1] if row_index + 1 < len(source_rows) else None
        if next_row is None or not branch_row.match(next_row.text):
            return ranges
    extended = [dict(item) for item in ranges]
    for row in source_rows[row_index + 1 :]:
        if _source_row_line(row) is not None:
            break
        if not row.text.strip():
            continue
        extended.extend(_source_ranges_for_fragment(source_text, row.start, row.end))
    return tuple(extended)


def _governed_source_row(row: _RawRow) -> tuple[str, list[str]] | None:
    """Classify a standalone rendered row that governs later worksheet lines."""
    has_next_instruction = re.search(r"\bnext\s*[.:]", row.text, re.IGNORECASE) is not None
    starts_yes_branch = re.match(r"\s*\|?\s*yes\b", row.text, re.IGNORECASE) is not None
    if _source_row_line(row) is not None and not has_next_instruction and not starts_yes_branch:
        return None
    if _SOURCE_NOTE_RE.search(row.text):
        kind = "note"
    elif _SOURCE_ROUTING_RE.search(row.text):
        kind = "routing_sentence"
    else:
        return None
    governs = list(
        dict.fromkeys(
            match.group(1).lower()
            for match in _SOURCE_LINE_REFERENCE_RE.finditer(row.text)
        )
    )
    return (kind, governs) if governs else None


def _governed_source_row_start(source_text: str, row: _RawRow) -> int:
    """Return the first byte of the routing/note prose within one source row."""
    raw = source_text[row.start:row.end]
    match = re.search(
        r"\b(?:next|yes)\s*[.:]",
        raw,
        re.IGNORECASE,
    )
    if match is None:
        return row.start
    start = row.start + match.start()
    if start >= row.start + 2 and source_text[start - 2:start] == "**":
        start -= 2
    return start


def _source_marker_ranges_for_row(
    source_text: str,
    row: _RawRow,
    line: str,
) -> tuple[dict[str, int], ...]:
    """Keep printed output markers when a governed tail owns the row prose."""
    number = re.match(r"[0-9]+", line)
    if number is None:
        return ()
    prefix = number.group(0)
    marker_pattern = re.compile(
        rf"(?<![A-Za-z0-9]){re.escape(prefix)}[a-z]?\s*[.)]",
        re.IGNORECASE,
    )
    matches = tuple(marker_pattern.finditer(source_text, row.start, row.end))
    return tuple(
        {"start": match.start(), "end": match.end()}
        for match in matches
        if re.fullmatch(rf"{re.escape(prefix)}[a-z]?", match.group(0).rstrip(".) "), re.IGNORECASE)
    )


def _subtract_source_range_rows(
    ranges: Iterable[Mapping[str, int]],
    excluded: _RawRow,
) -> tuple[dict[str, int], ...]:
    """Remove one governed source row from an aligned line span."""
    result: list[dict[str, int]] = []
    for item in ranges:
        start = int(item["start"])
        end = int(item["end"])
        if excluded.end <= start or excluded.start >= end:
            result.append({"start": start, "end": end})
            continue
        if start < excluded.start:
            result.append({"start": start, "end": excluded.start})
        if excluded.end < end:
            result.append({"start": excluded.end, "end": end})
    return tuple(item for item in result if item["start"] < item["end"])


def _subtract_source_interval(
    ranges: Iterable[Mapping[str, int]],
    start: int,
    end: int,
) -> tuple[dict[str, int], ...]:
    """Remove an arbitrary source interval from aligned ranges."""
    result: list[dict[str, int]] = []
    for item in ranges:
        item_start = int(item["start"])
        item_end = int(item["end"])
        if end <= item_start or start >= item_end:
            result.append({"start": item_start, "end": item_end})
            continue
        if item_start < start:
            result.append({"start": item_start, "end": start})
        if end < item_end:
            result.append({"start": end, "end": item_end})
    return tuple(item for item in result if item["start"] < item["end"])


def _align_source_face(
    source_text: str,
    face: str,
    *,
    line: str,
    start: int,
    end: int,
) -> tuple[tuple[dict[str, int], ...], int]:
    """Find one HTML-derived face in the rendered source, in order."""
    source_matches = tuple(_SOURCE_TOKEN_RE.finditer(source_text, start, end))
    # HTML tables put output slots in the middle of prose (and repeat the
    # printed line marker there).  Those slots are not worksheet prose and
    # must not force a false mismatch against the rendered text row.
    face = re.sub(
        r"(?<![A-Za-z0-9])[0-9]+[a-z]?\s*[.)]\s*(?:_+|\\_+)",
        " ",
        face,
        flags=re.IGNORECASE,
    )
    # A continuation table header can be attached to the last preceding HTML
    # row by the structural parser.  It is a boundary marker, not row prose.
    face = re.split(r"\b[A-Za-z][A-Za-z ]+Worksheet[- ]Continued\b", face, maxsplit=1)[0]
    wanted_matches = tuple(_SOURCE_TOKEN_RE.finditer(face))
    wanted = [
        match.group(0).casefold().replace("'", "")
        for match in wanted_matches
        if match.group(0).casefold() not in {"field", "checkbox"}
    ]
    if not wanted:
        return (), start
    for first_index, first in enumerate(source_matches):
        if first.group(0).casefold().replace("'", "") != wanted[0]:
            continue
        selected = [first]
        source_index = first_index + 1
        for wanted_token in wanted[1:]:
            while source_index < len(source_matches):
                candidate = source_matches[source_index]
                source_index += 1
                if candidate.group(0).casefold().replace("'", "") == wanted_token:
                    selected.append(candidate)
                    break
            else:
                break
        if len(selected) != len(wanted):
            continue
        ranges: list[dict[str, int]] = []
        range_start = selected[0].start()
        previous_end = selected[0].end()
        for previous, current in zip(selected, selected[1:]):
            gap = source_text[previous.end():current.start()]
            if _SOURCE_DOT_LEADER_RE.search(gap):
                ranges.append({"start": range_start, "end": previous_end})
                range_start = current.start()
            previous_end = current.end()
        ranges.append({"start": range_start, "end": previous_end})
        return tuple(ranges), selected[-1].end()
    return (), start


def _source_row_ranges(
    source_text: str,
    row: _RawRow,
    line: str,
) -> tuple[dict[str, int], ...]:
    """Keep lexical row text while dropping printed field markers and leaders."""
    raw = source_text[row.start:row.end]
    anchor = _source_printed_anchor(source_text, row, line)
    if anchor is None:
        return ()
    start, end_limit = anchor
    tokens = tuple(_SOURCE_TOKEN_RE.finditer(source_text[start:end_limit]))
    if not tokens:
        return ()
    ranges: list[dict[str, int]] = []
    range_start = start + tokens[0].start()
    previous_end = start + tokens[0].end()
    for previous, current in zip(tokens, tokens[1:]):
        previous_absolute_end = start + previous.end()
        current_absolute_start = start + current.start()
        gap = source_text[previous_absolute_end:current_absolute_start]
        if _SOURCE_DOT_LEADER_RE.search(gap):
            ranges.append({"start": range_start, "end": previous_end})
            range_start = current_absolute_start
        previous_end = start + current.end()
    ranges.append({"start": range_start, "end": previous_end})
    return tuple(ranges)


def _source_printed_anchor(
    source_text: str,
    row: _RawRow,
    line: str,
) -> tuple[int, int] | None:
    """Return the bounded printed anchor segment for one source row."""
    raw = source_text[row.start:row.end]
    anchor = re.compile(
        rf"""(?:
            (?<![A-Za-z0-9]){re.escape(line)}[.)](?=\s|$)
            |\|\s*{re.escape(line)}\s*\|
        )""",
        re.IGNORECASE | re.VERBOSE,
    )
    matches = tuple(anchor.finditer(raw))
    if not matches:
        return None
    first_index = 0
    if (
        len(matches) >= 3
        and matches[1].start() - matches[0].end() <= 2
    ):
        # Some rendered Markdown rows repeat the printed line in the first
        # cell and at the start of the prose cell: ``1. 1. Enter ... 1.``.
        # The second anchor is the prose row's start; the third is its
        # trailing printed marker.
        first_index = 1
    first = matches[first_index]
    second = matches[first_index + 1] if len(matches) > first_index + 1 else None
    return (
        row.start + first.start(),
        row.start + (second.start() if second is not None else len(raw)),
    )


def _source_subrow_ranges(
    source_text: str,
    row: _RawRow,
    line: str,
) -> tuple[dict[str, int], ...]:
    """Claim a lettered sub-line's prose before its printed output marker."""
    suffix = re.fullmatch(r"[0-9]+([a-z])", line, re.IGNORECASE)
    if suffix is None:
        return ()
    body_anchor = re.compile(
        rf"(?<![A-Za-z0-9]){re.escape(suffix.group(1))}[.)](?=\s)",
        re.IGNORECASE,
    ).search(source_text, row.start, row.end)
    if body_anchor is None:
        return ()
    marker_pattern = re.compile(
        rf"(?<![A-Za-z0-9]){re.escape(line)}[.)](?=\s|$)",
        re.IGNORECASE,
    )
    marker = None
    for candidate in marker_pattern.finditer(source_text, body_anchor.end(), row.end):
        prefix = source_text[max(row.start, candidate.start() - 4):candidate.start()]
        suffix_text = source_text[candidate.end():candidate.end() + 12]
        if "|" in prefix or _SOURCE_DOT_LEADER_RE.search(suffix_text):
            marker = candidate
            break
    end = marker.start() if marker is not None else row.end
    if end <= body_anchor.start():
        return ()
    start = body_anchor.start()
    return _source_ranges_for_fragment(source_text, start, end)


def _source_ranges_for_fragment(
    source_text: str,
    start: int,
    end: int,
) -> tuple[dict[str, int], ...]:
    """Split a source fragment at dot leaders while retaining lexical text."""
    tokens = tuple(_SOURCE_TOKEN_RE.finditer(source_text[start:end]))
    if not tokens:
        return ()
    ranges: list[dict[str, int]] = []
    range_start = start + tokens[0].start()
    previous_end = start + tokens[0].end()
    for previous, current in zip(tokens, tokens[1:]):
        previous_absolute_end = start + previous.end()
        current_absolute_start = start + current.start()
        if _SOURCE_DOT_LEADER_RE.search(source_text[previous_absolute_end:current_absolute_start]):
            ranges.append({"start": range_start, "end": previous_end})
            range_start = current_absolute_start
        previous_end = start + current.end()
    ranges.append({"start": range_start, "end": previous_end})
    return tuple(ranges)


def _source_quote_for_ranges(
    source_text: str | None,
    ranges: Iterable[Mapping[str, int]],
) -> str:
    """Render source ranges into the stored quote without inventing prose."""
    if source_text is None:
        return ""
    return _normalize_text(
        " ".join(source_text[int(item["start"]):int(item["end"])] for item in ranges)
    )


def _build_line_nodes(
    source_text: str,
    target: WorksheetTarget,
    citation_for_line: Mapping[str, HarvestObject],
    line_rows: Mapping[str, tuple[_RawRow, ...]],
    conditions: Iterable[WorksheetCondition],
) -> list[HarvestObject]:
    condition_lines = {condition.line for condition in conditions}
    nodes: list[HarvestObject] = []
    for line in sorted(line_rows, key=_line_sort_key):
        rows = line_rows[line]
        first, last = rows[0], rows[-1]
        face_end = last.end
        fragment = source_text[first.start:face_end]
        if "<table" in fragment.lower():
            nested_start = source_text.find("<table", first.start)
            nested_end = source_text.find("</table>", nested_start)
            outer_end = source_text.find("</tr>", nested_end)
            if nested_start >= 0 and nested_end >= 0 and outer_end >= 0:
                face_end = outer_end + len("</tr>")
        quote = _visible_text(source_text[first.start:face_end])
        citation = citation_for_line.get(line)
        if citation is None:
            continue
        data: dict[str, Any] = {
            "node_id": f"{_slug(target.document_id)}_line_{line}",
            "document_id": target.document_id,
            "label": f"{target.title} line {line}",
            "node_type": "worksheet_field",
            "value_type": "currency",
            "required": "optional",
            "citation_refs": [str(citation["citation_id"])],
        }
        if line in condition_lines:
            data["description"] = "Source text contains a conditional Form 2555 route; see harvest.yaml."
        nodes.append(
            HarvestObject(
                kind="node",
                data=data,
                source_quote=quote,
                source_start=first.start,
                source_end=face_end,
                source_spans=((first.start, face_end),),
            )
        )
    return nodes


def _build_constant_nodes(
    source_text: str,
    target: WorksheetTarget,
    citation_for_line: Mapping[str, HarvestObject],
    line_rows: Mapping[str, tuple[_RawRow, ...]],
) -> tuple[list[HarvestObject], list[HarvestObject]]:
    nodes: list[HarvestObject] = []
    edges: list[HarvestObject] = []

    for line, rate_name in (("18", "15"), ("21", "20")):
        if line not in line_rows:
            continue
        rows = line_rows[line]
        text = _normalize_text(" ".join(row.text for row in rows))
        match = re.search(rf"{rate_name}%\s*\((0\.[0-9]+)\)", text)
        if match is None:
            continue
        node, edge = _constant_object(
            source_text,
            target,
            line_rows,
            citation_for_line,
            line=line,
            node_suffix=f"rate_{rate_name}",
            label=f"{target.title} {rate_name} percent rate",
            value_type="percentage",
            value=float(match.group(1)),
            quote=match.group(0),
        )
        nodes.append(node)
        edges.append(edge)

    for line in ("6", "13"):
        if line not in line_rows:
            continue
        rows = line_rows[line]
        text = _normalize_text(" ".join(row.text for row in rows))
        rate_prefix = "0" if line == "6" else "15"
        for match in re.finditer(
            r"\$([0-9][0-9,]*)\s+if\s+([^$]+?)(?=\$[0-9]|$)",
            text,
        ):
            value = int(match.group(1).replace(",", ""))
            roles = _roles_from_phrase(match.group(2))
            for role in roles:
                node, edge = _constant_object(
                    source_text,
                    target,
                    line_rows,
                    citation_for_line,
                    line=line,
                    node_suffix=f"breakpoint_{rate_prefix}_{role}",
                    label=f"{target.title} {rate_prefix} percent breakpoint, {_role_label(role)}",
                    value_type="currency",
                    value=value,
                    quote=match.group(0).rstrip(" ,."),
                )
                nodes.append(node)
                edges.append(edge)

    if "22" in line_rows:
        rows = line_rows["22"]
        text = _normalize_text(" ".join(row.text for row in rows))
        match = re.search(r"\$([0-9][0-9,]*)", text)
        if match:
            node, edge = _constant_object(
                source_text,
                target,
                line_rows,
                citation_for_line,
                line="22",
                node_suffix="tax_table_threshold",
                label=f"{target.title} tax table threshold",
                value_type="currency",
                value=int(match.group(1).replace(",", "")),
                quote=match.group(0),
            )
            nodes.append(node)
            edges.append(edge)
    return nodes, edges


def _constant_object(
    source_text: str,
    target: WorksheetTarget,
    line_rows: Mapping[str, tuple[_RawRow, ...]],
    citation_for_line: Mapping[str, HarvestObject],
    *,
    line: str,
    node_suffix: str,
    label: str,
    value_type: str,
    value: int | float,
    quote: str,
) -> tuple[HarvestObject, HarvestObject]:
    rows = line_rows[line]
    first, last = rows[0], rows[-1]
    citation = citation_for_line[line]
    node_id = f"{_slug(target.document_id)}_{node_suffix}"
    node = HarvestObject(
        kind="node",
        data={
            "node_id": node_id,
            "document_id": target.document_id,
            "label": label,
            "node_type": "parameter",
            "value_type": value_type,
            "required": "optional",
            "constant_value": value,
            "citation_refs": [str(citation["citation_id"])],
        },
        source_quote=quote,
        source_start=first.start,
        source_end=last.end,
        source_spans=((first.start, last.end),),
    )
    edge = HarvestObject(
        kind="edge",
        data={
            "edge_id": f"e_{node_id}_references_line_{line}",
            "source": node_id,
            "target": f"{_slug(target.document_id)}_line_{line}",
            "relationship": "REFERENCES",
            "role": "constant",
            "citation_refs": [str(citation["citation_id"])],
        },
        source_quote=quote,
        source_start=first.start,
        source_end=last.end,
        source_spans=((first.start, last.end),),
    )
    return node, edge


def _build_line_reference_edges(
    source_text: str,
    target: WorksheetTarget,
    citation_for_line: Mapping[str, HarvestObject],
    line_rows: Mapping[str, tuple[_RawRow, ...]],
) -> list[HarvestObject]:
    edges: list[HarvestObject] = []
    for line, rows in line_rows.items():
        text = _normalize_text(" ".join(row.text for row in rows))
        for match in re.finditer(r"\blines?\s+([0-9]+[a-z]?)\b", text, re.IGNORECASE):
            referenced = match.group(1).lower()
            if referenced not in line_rows or _is_external_line_reference(text, match.start()):
                continue
            citation = citation_for_line.get(line)
            if citation is None:
                continue
            source_id = f"{_slug(target.document_id)}_line_{referenced}"
            target_id = f"{_slug(target.document_id)}_line_{line}"
            rows_first, rows_last = rows[0], rows[-1]
            edges.append(
                HarvestObject(
                    kind="edge",
                    data={
                        "edge_id": f"e_{source_id}_references_{target_id}",
                        "source": source_id,
                        "target": target_id,
                        "relationship": "REFERENCES",
                        "citation_refs": [str(citation["citation_id"])],
                    },
                    source_quote=_visible_text(source_text[rows_first.start : rows_last.end]),
                    source_start=rows_first.start,
                    source_end=rows_last.end,
                    source_spans=((rows_first.start, rows_last.end),),
                )
            )
    return _dedupe_edges(edges)


def _conditions_for_lines(
    line_rows: Mapping[str, tuple[_RawRow, ...]], source_text: str
) -> list[WorksheetCondition]:
    conditions: list[WorksheetCondition] = []
    for line in ("1", "25"):
        rows = line_rows.get(line)
        if not rows:
            continue
        text = _normalize_text(" ".join(row.text for row in rows))
        if "form 2555" not in text.lower():
            continue
        first, last = rows[0], rows[-1]
        conditions.append(
            WorksheetCondition(
                line=line,
                referenced_document="form_2555",
                behavior="conditional source or destination routing",
                source_quote=_visible_text(source_text[first.start:last.end]),
            )
        )
    return conditions


def _document_object(
    target: WorksheetTarget,
    year: str,
    source_document_id: str,
    heading: InstructionHeading,
) -> HarvestObject:
    data = {
        "document_id": target.document_id,
        "title": target.title,
        "tax_year": int(year),
        "document_type": "worksheet",
        "document_class": document_class_for(document_id=target.document_id, document_type="worksheet"),
        "status": "partial",
    }
    return HarvestObject(
        kind="document",
        data=data,
        source_quote=heading.text,
        source_start=heading.source_start,
        source_end=heading.source_end,
        source_spans=((heading.source_start, heading.source_end),),
    )


def _count_findings(
    target: WorksheetTarget,
    line_rows: Mapping[str, tuple[_RawRow, ...]],
    parameter_nodes: Iterable[HarvestObject],
) -> list[WorksheetFinding]:
    findings: list[WorksheetFinding] = []
    if target.expected_line_count is not None and len(line_rows) != target.expected_line_count:
        findings.append(
            WorksheetFinding(
                "line_count_mismatch",
                f"expected {target.expected_line_count} worksheet lines, found {len(line_rows)}",
            )
        )
    parameters = tuple(parameter_nodes)
    if target.expected_constant_count is not None and len(parameters) != target.expected_constant_count:
        findings.append(
            WorksheetFinding(
                "constant_count_mismatch",
                f"expected {target.expected_constant_count} constants, found {len(parameters)}",
            )
        )
    return _dedupe_findings(findings)


def _verify_harvest_objects(
    source_text: str,
    objects: Iterable[HarvestObject],
    *,
    oracle_source_text: str | None = None,
) -> list[WorksheetFinding]:
    findings: list[WorksheetFinding] = []
    for obj in objects:
        spans = obj.source_spans or ((obj.source_start, obj.source_end),)
        if not obj.source_quote:
            findings.append(
                WorksheetFinding(
                    "empty_source_quote",
                    f"{obj.kind} {obj.get('node_id', obj.get('edge_id', obj.get('citation_id', '')))} has no source quote",
                )
            )
            continue
        ranged = obj.data.get("ranges")
        if oracle_source_text is not None and ranged:
            expected = _source_quote_for_ranges(oracle_source_text, ranged)
            if _normalize_text(obj.source_quote) != expected:
                findings.append(
                    WorksheetFinding(
                        "quote_not_verbatim",
                        f"{obj.kind} source quote does not reconstruct from its ranges",
                        (
                            f"source_span={obj.source_start}:{obj.source_end}",
                            f"range_count={len(ranged)}",
                        ),
                    )
                )
            continue
        if not any(
            _normalize_text(obj.source_quote).lower()
            in _normalize_text(_visible_text(source_text[start:end])).lower()
            for start, end in spans
        ):
            findings.append(
                WorksheetFinding(
                    "quote_not_verbatim",
                    f"{obj.kind} source quote is not present in its source span",
                    (f"source_span={obj.source_start}:{obj.source_end}",),
                )
            )
    return findings


def _blocked_harvest(
    target: WorksheetTarget,
    year: str,
    source_document_id: str,
    findings: tuple[WorksheetFinding, ...],
    worksheet_source_span: tuple[int, int] | None = None,
    observed_start_anchor: str | None = None,
    markdown_lines: tuple[str, ...] | None = None,
    html_lines: tuple[str, ...] = (),
) -> WorksheetHarvest:
    return WorksheetHarvest(
        target=target,
        year=year,
        source_document_id=source_document_id,
        start_anchor=(target.start_anchor if observed_start_anchor is None else observed_start_anchor),
        document=None,
        nodes=tuple(),
        edges=tuple(),
        citations=tuple(),
        conditions=tuple(),
        findings=_dedupe_findings(findings),
        worksheet_source_span=worksheet_source_span,
        markdown_lines=markdown_lines,
        html_lines=html_lines,
    )


def _roles_from_phrase(phrase: str) -> tuple[str, ...]:
    lowered = phrase.lower()
    roles: list[str] = []
    for token, marker in (
        ("single", "single"),
        ("married filing separately", "mfs"),
        ("married filing jointly", "mfj"),
        ("qualifying surviving spouse", "qss"),
        ("head of household", "hoh"),
    ):
        if token in lowered and marker not in roles:
            roles.append(marker)
    return tuple(roles)


def _role_label(role: str) -> str:
    return {
        "single": "Single",
        "mfs": "Married filing separately",
        "mfj": "Married filing jointly",
        "qss": "Qualifying surviving spouse",
        "hoh": "Head of household",
    }[role]


def _visible_text_from_rows(rows: Iterable[_RawRow]) -> str:
    return _normalize_text(" ".join(row.text for row in rows))


def _visible_text(fragment: str) -> str:
    class TextParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.parts: list[str] = []

        def handle_data(self, data: str) -> None:
            self.parts.append(data)

    parser = TextParser()
    parser.feed(fragment)
    parser.close()
    return _normalize_text(" ".join(parser.parts))


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _is_external_line_reference(text: str, start: int) -> bool:
    context = text[max(0, start - 70) : start + 80].lower()
    return any(
        marker in context
        for marker in (
            "form 1040",
            "schedule d",
            "foreign earned income tax worksheet",
            "unrecaptured section 1250 gain worksheet",
        )
    )


def _citation_span_size(citation: HarvestObject) -> int:
    ranges = citation.data.get("ranges")
    if ranges:
        return sum(int(item["end"]) - int(item["start"]) for item in ranges)
    return citation.source_end - citation.source_start


def _citation_slug(lines: Iterable[str]) -> str:
    values = tuple(lines)
    if len(values) == 1:
        return values[0]
    return f"{values[0]}_{values[-1]}"


def _line_sort_key(value: str) -> tuple[int, str]:
    match = re.fullmatch(r"([0-9]+)([a-z]?)", value.lower())
    if match:
        return int(match.group(1)), match.group(2)
    return 10**9, value.lower()


def _dedupe_edges(edges: Iterable[HarvestObject]) -> list[HarvestObject]:
    result: list[HarvestObject] = []
    seen: set[str] = set()
    for edge in edges:
        edge_id = str(edge["edge_id"])
        if edge_id not in seen:
            result.append(edge)
            seen.add(edge_id)
    return result


def _dedupe_findings(findings: Iterable[WorksheetFinding]) -> tuple[WorksheetFinding, ...]:
    result: list[WorksheetFinding] = []
    seen: set[tuple[str, str]] = set()
    for finding in findings:
        key = (finding.kind, finding.message)
        if key not in seen:
            result.append(finding)
            seen.add(key)
    return tuple(result)


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "worksheet"


def _discovered_document_id(title: str, year: str) -> str:
    """Mint a document id from the source title and tax year, not line text."""
    return f"{_slug(title)}_{year}"


def _write_yaml(path: Path, payload: Any) -> None:
    text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=False)
    text.encode("ascii")
    path.write_text(text, encoding="ascii", newline="\n")
