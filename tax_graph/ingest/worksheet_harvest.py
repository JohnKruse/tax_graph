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


QDCGT_TARGET = "qualified_dividends_capital_gain_tax_worksheet"


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
    classification: TableClassification | None = None

    @property
    def ok(self) -> bool:
        """Whether the harvest passed all fail-closed checks."""
        return not self.findings and self.document is not None

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
        return {
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
            "classification": self.classification.as_dict() if self.classification is not None else None,
            "conditions": [condition.as_dict() for condition in self.conditions],
            "findings": [finding.as_dict() for finding in self.findings],
            "counts": {
                "lines": len(self.line_nodes),
                "constants": len(self.parameter_nodes),
                "edges": len(self.edges),
                "citations": len(self.citations),
            },
        }


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
class TableClassification:
    """The model's classification of one acquired table."""

    table_id: int
    heading: str
    anchor_id: str
    kind: str
    lines: tuple[str, ...]
    source_start: int
    source_end: int

    def as_dict(self) -> dict[str, Any]:
        """Return the review-facing classification record."""
        return {
            "table_id": self.table_id,
            "heading": self.heading,
            "anchor_id": self.anchor_id,
            "kind": self.kind,
            "lines": list(self.lines),
            "source_start": self.source_start,
            "source_end": self.source_end,
        }


class TableClassifier(Protocol):
    """Callable seam for the table-classification model."""

    def __call__(self, table: _RawTable, source_text: str) -> Mapping[str, Any]:
        """Classify one table from its own heading and visible text."""


@dataclass(frozen=True)
class WorksheetDiscovery:
    """Document-wide table classifications and harvested worksheet drafts."""

    source_document_id: str
    year: str
    classifications: tuple[TableClassification, ...]
    worksheets: tuple[WorksheetHarvest, ...]
    findings: tuple[WorksheetFinding, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        """Return a stable discovery report without source payloads."""
        return {
            "schema_version": 1,
            "source_document_id": self.source_document_id,
            "year": self.year,
            "classifications": [item.as_dict() for item in self.classifications],
            "worksheets": [item.as_dict() for item in self.worksheets],
            "findings": [item.as_dict() for item in self.findings],
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


def worksheet_table_schema() -> dict[str, Any]:
    """Return the strict schema for one table-classification call."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["kind", "lines"],
        "properties": {
            "kind": {
                "type": "string",
                "enum": ["worksheet", "lookup_table", "layout"],
            },
            "lines": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
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
    """Classify every acquired HTML table, using a cache keyed by table bytes.

    The classifier receives every table, including lookup tables and layouts.
    No prefilter is applied because a prefilter would make the missing-table
    case silent.  ``classifier`` may be a test callable, an object exposing
    ``classify_table``, or the provider-agnostic structured-completion client.
    When it is omitted, the configured LLM client is built lazily.
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
        if isinstance(cached_payload, dict):
            payload = cached_payload
        else:
            payload = _call_table_classifier(
                table,
                source_text,
                classifier=classifier,
                config=settings,
            )
            updated_cache[fingerprint] = dict(payload)
        classifications.append(_classification_from_payload(table, payload))
    if cache_file is not None and updated_cache != cached:
        _write_classification_cache(cache_file, updated_cache)
    return tuple(classifications)


def _call_table_classifier(
    table: _RawTable,
    source_text: str,
    *,
    classifier: Any | None,
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
        "Report only printed form line numbers that the table serves. "
        "Use the table's own heading, not a neighboring heading or row prose.\n\n"
        f"heading: {heading}\n"
        f"anchor: {anchor}\n"
        f"table_text:\n{visible}\n"
    )
    request: dict[str, Any] = {
        "prompt": prompt,
        "schema": worksheet_table_schema(),
        "model": resolve_llm_model(config, "micro"),
        "max_tokens": int(get_config_value(dict(config), "extraction.worksheet_classifier_max_tokens", 512)),
        "temperature": get_config_value(dict(config), "llm.temperature"),
        "purpose": "tax_graph_worksheet_table_classifier",
    }
    seed = resolve_llm_seed(config)
    if seed is not None:
        request["seed"] = seed
    return client.structured_completion(**request)


def _classification_from_payload(table: _RawTable, payload: Mapping[str, Any]) -> TableClassification:
    kind = str(payload.get("kind") or "").strip()
    if kind not in {"worksheet", "lookup_table", "layout"}:
        raise ValueError(f"unsupported worksheet table kind: {kind!r}")
    raw_lines = payload.get("lines")
    if not isinstance(raw_lines, (list, tuple)):
        raise ValueError("worksheet table classification lines must be an array")
    lines = tuple(str(line).strip().lower() for line in raw_lines if str(line).strip())
    if any(not re.fullmatch(r"[0-9]+[a-z]?", line) for line in lines):
        raise ValueError("worksheet table classification lines must be printed line tokens")
    heading = table.heading
    return TableClassification(
        table_id=table.table_id,
        heading=heading.text if heading is not None else "",
        anchor_id=heading.anchor_id if heading is not None else "",
        kind=kind,
        lines=tuple(dict.fromkeys(lines)),
        source_start=table.start,
        source_end=table.end,
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
    title = re.sub(r"\s*[- ]*lines?\s+.+$", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+lines?\s+.+$", "", title, flags=re.IGNORECASE)
    return title.strip(" -:") or value.strip()


def harvest_worksheet(
    source_text: str,
    target: WorksheetTarget | Mapping[str, Any],
    *,
    source_document_id: str | None = None,
    year: str | int = "2025",
    oracle_source_text: str | None = None,
    oracle_heading_text: str | None = None,
    _tables: tuple[_RawTable, ...] | None = None,
) -> WorksheetHarvest:
    """Harvest one worksheet using HTML structure and an optional text oracle."""
    resolved_target = _coerce_target(target)
    year_text = str(year)
    source_id = source_document_id or resolved_target.source_document_id or ""
    tables = _tables
    start_heading: InstructionHeading | None = None
    if _is_html_source(source_text):
        tables = tables or _tables_for_target(source_text, resolved_target)
        if not tables:
            headings = _source_headings(source_text)
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
        rows = tuple(
            replace(row, table_id=1)
            for table in tables
            for row in table.rows
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
    if findings:
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
    all_findings = list(_count_findings(resolved_target, line_rows, parameter_nodes))
    all_objects = [document, *nodes, *edges, *citations]
    all_findings.extend(_verify_harvest_objects(source_text, all_objects))
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
    if all_findings:
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
        findings=tuple(),
        worksheet_source_span=(start_heading.source_start, terminal_row.end),
        markdown_lines=markdown_lines,
        html_lines=html_lines,
    )


def harvest_worksheet_file(
    path: str | Path,
    target: WorksheetTarget | Mapping[str, Any],
    *,
    source_document_id: str | None = None,
    year: str | int = "2025",
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
    )


def harvest_worksheets(
    source_text: str,
    *,
    source_document_id: str,
    year: str | int = "2025",
    title: str | None = None,
    classifier: Any | None = None,
    config: Mapping[str, Any] | None = None,
    cache_path: str | Path | None = None,
    oracle_source_text: str | None = None,
) -> WorksheetDiscovery:
    """Discover and harvest every worksheet table in one instruction document.

    A title narrows the already-classified document; it never changes the
    structural extent rule.  The five Schedule D source tables therefore
    remain five classifications, while a title-targeted harvest can combine a
    base worksheet with its explicitly continued table.
    """
    year_text = str(year)
    tables = _source_tables(source_text) if _is_html_source(source_text) else ()
    if not tables:
        return WorksheetDiscovery(source_document_id, year_text, (), ())
    classifications = classify_worksheet_tables(
        source_text,
        classifier=classifier,
        config=config,
        cache_path=cache_path,
    )
    wanted = normalize_printed_title(title) if title else None
    worksheets: list[WorksheetHarvest] = []
    findings: list[WorksheetFinding] = []
    for table, classification in zip(tables, classifications):
        if classification.kind != "worksheet":
            continue
        if table.heading is None or not table.heading.text.strip():
            findings.append(
                WorksheetFinding(
                    "worksheet_table_missing_heading",
                    f"worksheet table {table.table_id} has no associated heading",
                )
            )
            continue
        semantic_title = _semantic_worksheet_title(table.heading.text)
        if wanted and not _title_matches(semantic_title, wanted):
            continue
        is_continuation = bool(re.search(r"continued\s*$", table.heading.text, re.IGNORECASE))
        if wanted and is_continuation and any(
            other is not table
            and other.heading is not None
            and _semantic_worksheet_title(other.heading.text) == semantic_title
            and not re.search(r"continued\s*$", other.heading.text, re.IGNORECASE)
            for other in tables
        ):
            continue
        identity_title = semantic_title
        if is_continuation:
            identity_title = f"{semantic_title} Continued"
        target = WorksheetTarget(
            document_id=_discovered_document_id(identity_title, year_text),
            title=semantic_title,
            start_anchor=classification.anchor_id or f"table-{table.table_id}",
            source_document_id=source_document_id,
        )
        selected_tables = (table,)
        oracle_heading = table.heading.text
        if not is_continuation:
            continued_tables = tuple(
                other
                for other in tables
                if other is not table
                and other.heading is not None
                and _semantic_worksheet_title(other.heading.text) == semantic_title
                and re.search(r"continued\s*$", other.heading.text, re.IGNORECASE)
            )
            if continued_tables:
                selected_tables = (table, *continued_tables)
                oracle_heading = None
        harvest = harvest_worksheet(
            source_text,
            target,
            source_document_id=source_document_id,
            year=year_text,
            oracle_source_text=oracle_source_text,
            oracle_heading_text=oracle_heading,
            _tables=selected_tables,
        )
        worksheets.append(replace(harvest, classification=classification))
    return WorksheetDiscovery(
        source_document_id=source_document_id,
        year=year_text,
        classifications=classifications,
        worksheets=tuple(worksheets),
        findings=tuple(findings),
    )


def harvest_worksheets_file(
    path: str | Path,
    *,
    source_document_id: str,
    year: str | int = "2025",
    title: str | None = None,
    classifier: Any | None = None,
    config: Mapping[str, Any] | None = None,
    cache_path: str | Path | None = None,
) -> WorksheetDiscovery:
    """Discover worksheets from HTML and pair it with sibling Markdown text."""
    source_path = Path(path)
    source_text = source_path.read_text(encoding="ascii")
    rendered_path = source_path.with_suffix(".txt")
    oracle_text = rendered_path.read_text(encoding="ascii") if rendered_path.exists() else None
    return harvest_worksheets(
        source_text,
        source_document_id=source_document_id,
        year=year,
        title=title,
        classifier=classifier,
        config=config,
        cache_path=cache_path,
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
            if _title_matches(heading.text, wanted)
            and not re.search(r"continued\s*$", heading.text, re.IGNORECASE)
        )
        continuations = tuple(
            heading
            for heading in headings
            if _title_matches(heading.text, wanted)
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
            line = _row_line(row)
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
        if line_match:
            token = line_match.group("line").lower()
            body = line_match.group("body").strip()
            if not body and re.fullmatch(r"\s*[0-9]+\s*", raw):
                text = ""
                cells = ("",)
            else:
                text = _normalize_text(f"{token}. {body}")
                cells = (f"{token}.", body)
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
    )


def _find_start_heading(
    headings: Iterable[InstructionHeading], target: WorksheetTarget
) -> InstructionHeading | None:
    """Return a title match only when the source has exactly one candidate."""
    candidates = _find_start_headings(headings, target)
    return candidates[0] if len(candidates) == 1 else None


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
) -> tuple[tuple[HarvestObject, ...], dict[str, HarvestObject]]:
    line_numbers = tuple(sorted(line_rows, key=_line_sort_key))
    groups = target.citation_groups or tuple((line,) for line in line_numbers)
    citations: list[HarvestObject] = []
    citation_for_line: dict[str, HarvestObject] = {}
    for group in groups:
        selected_lines = tuple(line for line in group if line in line_rows)
        if not selected_lines:
            continue
        first = line_rows[selected_lines[0]][0]
        last = line_rows[selected_lines[-1]][-1]
        quote = _visible_text(source_text[first.start:last.end])
        slug = _citation_slug(selected_lines)
        citation_id = f"cite_{_slug(target.document_id)}_lines_{slug}"
        citation = HarvestObject(
            kind="citation",
            data={
                "citation_id": citation_id,
                "document_id": source_document_id,
                "source_document_id": source_document_id,
                "locator": (
                    f"source_document={source_document_id};"
                    f"worksheet={target.title};lines={slug}"
                ),
                "quoted_text": quote,
            },
            source_quote=quote,
            source_start=first.start,
            source_end=last.end,
            source_spans=((first.start, last.end),),
        )
        citations.append(citation)
        for line in selected_lines:
            current = citation_for_line.get(line)
            if current is None or _citation_span_size(citation) < _citation_span_size(current):
                citation_for_line[line] = citation
    return tuple(citations), citation_for_line


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
        quote = _visible_text(source_text[first.start:last.end])
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
                source_end=last.end,
                source_spans=((first.start, last.end),),
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


def _verify_harvest_objects(source_text: str, objects: Iterable[HarvestObject]) -> list[WorksheetFinding]:
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
