"""Harvest worksheet-shaped graph drafts from acquired instruction HTML.

The worksheet harvester is intentionally separate from promotion.  It reads
only the acquired source supplied by the caller, discovers a worksheet from a
stable start anchor, and returns schema-shaped draft objects with a source
witness for every object.  It never writes graph state and it never treats an
end anchor as worksheet identity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

import yaml

from tax_graph.acquire.instruction_html import InstructionHeading, parse_headings
from tax_graph.documents import document_class_for


QDCGT_TARGET = "qualified_dividends_capital_gain_tax_worksheet"


@dataclass(frozen=True)
class WorksheetTarget:
    """Describe a worksheet by its stable source anchor and output identity."""

    document_id: str
    title: str
    start_anchor: str
    source_document_id: str | None = None
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

    def as_dict(self) -> dict[str, Any]:
        """Return a draft report without changing the graph schema."""
        return {
            "schema_version": 1,
            "status": "ready" if self.ok else "blocked",
            "document_id": self.target.document_id,
            "year": self.year,
            "source_document_id": self.source_document_id,
            "start_anchor": self.start_anchor,
            "worksheet_source_span": list(self.worksheet_source_span)
            if self.worksheet_source_span is not None
            else None,
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
        self._table_depth = 0
        self._row_start = 0
        self._row_table_id = 0
        self._row_cells: list[str] = []
        self._cell_parts: list[str] | None = None

    def _offset(self) -> int:
        line, column = self.getpos()
        return self._line_starts[line - 1] + column

    def _tag_end(self, offset: int) -> int:
        close = self.source.find(">", offset)
        return close + 1 if close >= 0 else offset

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered == "table":
            self._table_depth += 1
            self._table_id += 1
            return
        if lowered == "tr" and self._row_cells == [] and self._cell_parts is None:
            self._row_start = self._offset()
            self._row_table_id = self._table_id
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
            self.rows.append(
                _RawRow(
                    table_id=self._row_table_id,
                    start=self._row_start,
                    end=end,
                    cells=cells,
                    text=_normalize_text(" ".join(cell for cell in cells if cell)),
                )
            )
            self._row_cells = []
            return
        if lowered == "table" and self._table_depth:
            self._table_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._cell_parts is not None:
            self._cell_parts.append(data)


def harvest_worksheet(
    source_text: str,
    target: WorksheetTarget | Mapping[str, Any],
    *,
    source_document_id: str | None = None,
    year: str | int = "2025",
) -> WorksheetHarvest:
    """Harvest one worksheet from acquired HTML without writing any files.

    The source anchor selects where discovery begins.  The extent is accepted
    only after the harvester sees contiguous numbered rows, a terminal row
    that states its destination, and resolvable footnote markers.  A failed
    check returns findings and no graph objects, so callers cannot accidentally
    route a partial worksheet into promotion.
    """
    resolved_target = _coerce_target(target)
    year_text = str(year)
    source_id = source_document_id or resolved_target.source_document_id or ""
    headings = parse_headings(source_text)
    start_heading = _find_start_heading(headings, resolved_target)
    if start_heading is None:
        finding = WorksheetFinding(
            "missing_start_anchor",
            f"worksheet start anchor not found: {resolved_target.start_anchor}",
            (f"source_document_id={source_id}", f"start_anchor={resolved_target.start_anchor}"),
        )
        return _blocked_harvest(resolved_target, year_text, source_id, (finding,))

    parser = _RowParser(source_text)
    parser.feed(source_text)
    parser.close()
    rows = tuple(row for row in parser.rows if row.start >= start_heading.source_start)
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
    edges = [*parameter_edges, *_build_line_reference_edges(resolved_target, citation_for_line, line_rows)]
    nodes = [*nodes, *parameter_nodes]
    document = _document_object(resolved_target, year_text, source_id, start_heading)
    all_findings = list(_count_findings(resolved_target, line_rows, parameter_nodes))
    all_objects = [document, *nodes, *edges, *citations]
    all_findings.extend(_verify_harvest_objects(source_text, all_objects))
    if all_findings:
        return _blocked_harvest(
            resolved_target,
            year_text,
            source_id,
            tuple(all_findings),
            worksheet_source_span=(start_heading.source_start, terminal_row.end),
        )
    return WorksheetHarvest(
        target=resolved_target,
        year=year_text,
        source_document_id=source_id,
        start_anchor=resolved_target.start_anchor,
        document=document,
        nodes=tuple(nodes),
        edges=tuple(edges),
        citations=tuple(citations),
        conditions=tuple(conditions),
        findings=tuple(),
        worksheet_source_span=(start_heading.source_start, terminal_row.end),
    )


def harvest_worksheet_file(
    path: str | Path,
    target: WorksheetTarget | Mapping[str, Any],
    *,
    source_document_id: str | None = None,
    year: str | int = "2025",
) -> WorksheetHarvest:
    """Read an acquired HTML file and delegate to the pure text harvester."""
    source_path = Path(path)
    return harvest_worksheet(
        source_path.read_text(encoding="ascii"),
        target,
        source_document_id=source_document_id,
        year=year,
    )


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


def _find_start_heading(
    headings: Iterable[InstructionHeading], target: WorksheetTarget
) -> InstructionHeading | None:
    return next((heading for heading in headings if heading.anchor_id == target.start_anchor), None)


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
    expected = 1
    table_id: int | None = None
    terminal: _RawRow | None = None
    after_terminal = False
    for row in rows:
        line = _row_line(row)
        if table_id is None and line == "1":
            table_id = row.table_id
        if table_id is None or row.table_id != table_id:
            if after_terminal:
                break
            continue
        if after_terminal:
            if line is None:
                selected.append(row)
                line_rows.setdefault(current_line or "", []).append(row)
                continue
            break
        if line is None:
            if current_line is not None:
                selected.append(row)
                line_rows[current_line].append(row)
            continue
        if line != str(expected):
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
        if target.expected_line_count is not None and expected == target.expected_line_count:
            terminal = row
            after_terminal = True
        elif target.expected_line_count is None and _contains_terminal_destination((row,), source_text):
            terminal = row
            after_terminal = True
        expected += 1

    if not line_rows:
        findings.append(
            WorksheetFinding(
                "missing_numbered_rows",
                "worksheet start was found but no numbered table rows followed it",
            )
        )
    terminal_line = str(target.expected_line_count or max((int(line) for line in line_rows), default=0))
    if target.expected_line_count is None and terminal_line in line_rows:
        candidate = line_rows[terminal_line]
        if _contains_terminal_destination(candidate, source_text):
            terminal = candidate[0]
    if terminal is None:
        findings.append(
            WorksheetFinding(
                "missing_terminal_line",
                f"worksheet terminal line {terminal_line} was not discovered",
                (f"observed_lines={','.join(line_rows)}",),
            )
        )
    elif not _contains_terminal_destination(line_rows[terminal_line], source_text):
        findings.append(
            WorksheetFinding(
                "terminal_destination_missing",
                f"worksheet terminal line {terminal_line} does not state its destination",
                (f"row_span={terminal.start}:{terminal.end}",),
            )
        )
    if target.expected_line_count is not None and len(line_rows) != target.expected_line_count:
        findings.append(
            WorksheetFinding(
                "line_count_mismatch",
                f"expected {target.expected_line_count} worksheet lines, found {len(line_rows)}",
            )
        )
    if terminal is not None:
        footnote_rows = tuple(line_rows.get(terminal_line, ()))
        marker_text = " ".join(row.text for row in selected if row is not terminal or row.text)
        markers = {"*"} if "*" in marker_text else set()
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


def _contains_terminal_destination(rows: Iterable[_RawRow], source_text: str) -> bool:
    text = _normalize_text(" ".join(row.text for row in rows)).lower()
    return (
        "also include this amount on the entry space on form 1040" in text
        and "line 16" in text
    )


def _row_line(row: _RawRow) -> str | None:
    first = row.cells[0] if row.cells else ""
    match = re.match(r"^\s*([0-9]+[a-z]?)\s*[.)]?\s*$", first, re.IGNORECASE)
    return match.group(1).lower() if match else None


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
                "locator": f"html#{target.start_anchor}:lines={slug}",
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
                    source_quote=_visible_text_from_rows(rows),
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
) -> WorksheetHarvest:
    return WorksheetHarvest(
        target=target,
        year=year,
        source_document_id=source_document_id,
        start_anchor=target.start_anchor,
        document=None,
        nodes=tuple(),
        edges=tuple(),
        citations=tuple(),
        conditions=tuple(),
        findings=_dedupe_findings(findings),
        worksheet_source_span=worksheet_source_span,
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


def _write_yaml(path: Path, payload: Any) -> None:
    text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=False)
    text.encode("ascii")
    path.write_text(text, encoding="ascii", newline="\n")
