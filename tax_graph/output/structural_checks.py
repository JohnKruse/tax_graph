"""Read-only structural checks for resolver and field-map reconciliation.

The checks in this module deliberately return findings instead of booleans. They
are intended to become a review-queue input in a later phase. They do not alter
field maps, bindings, graph nodes, or promoted artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

import yaml

from tax_graph.addressing import parse_address_id
from tax_graph.output.field_identity import FieldIdentity, resolve_fields


_CAPTION_RE = re.compile(r"^\s*-\s*(?P<ref>[0-9]+[a-z]?|[a-z]):\s*(?P<text>.*)$", re.IGNORECASE)
_LINE_RE = re.compile(r"\bline\s+(?P<line>[0-9]+[a-z]?)\b", re.IGNORECASE)
_CANONICAL_LINE_RE = re.compile(r"^[0-9]+[a-z]?$", re.IGNORECASE)


@dataclass(frozen=True)
class StructuralFinding:
    """One deterministic structural contradiction for later review."""

    document: str
    control: str
    validator: str
    observed: Any
    expected: Any
    evidence: tuple[str, ...]

    @property
    def document_id(self) -> str:
        """Compatibility alias for consumers that use the artifact field name."""
        return self.document

    def as_record(self) -> dict[str, Any]:
        """Return the review-queue-shaped representation of this finding."""
        return {
            "document": self.document,
            "control": self.control,
            "validator": self.validator,
            "observed": self.observed,
            "expected": self.expected,
            "evidence": list(self.evidence),
        }

    to_dict = as_record


@dataclass(frozen=True)
class DocumentStructuralReport:
    """Findings for one promoted document."""

    document: str
    findings: tuple[StructuralFinding, ...]

    @property
    def counts(self) -> dict[str, int]:
        """Count findings by validator in stable validator order."""
        names = (
            "heading_integrity",
            "line_coverage",
            "total_presence",
            "line_identity_triangle",
        )
        return {name: sum(item.validator == name for item in self.findings) for name in names}


def check_document_structure(
    document: str,
    *,
    fields: Iterable[Mapping[str, Any]],
    field_map: Mapping[str, Any],
    nodes: Iterable[Mapping[str, Any]],
    widget_bindings: Iterable[Mapping[str, Any]] = (),
    node_bindings: Iterable[Mapping[str, Any]] = (),
    rendered_text: str | Sequence[str] | None = None,
    printed_amount_lines: Iterable[str] | None = None,
    total_lines: Iterable[str] | None = None,
    out_of_profile: Iterable[str] = (),
) -> tuple[StructuralFinding, ...]:
    """Run all four fail-closed structural checks for one field map.

    ``printed_amount_lines`` and ``total_lines`` are optional explicit evidence
    inputs. When omitted, amount lines come from resolver-resolved amount
    controls and total lines come from rendered captions containing a total
    cue. Explicit ``out_of_profile`` lines satisfy line coverage and total
    presence, respectively; an ordinary unsupported field disposition does not
    silently waive a printed total.
    """
    inventory = tuple(fields)
    identities = resolve_fields(inventory, rendered_text=rendered_text)
    node_records = tuple(nodes)
    widget_records = tuple(widget_bindings)
    node_records_by_id = {str(item.get("node_id")): item for item in node_records}
    mapping_by_field = {
        str(item["field_name"]): item
        for item in field_map.get("mappings", ())
        if item.get("field_name")
    }
    widget_by_field = {
        str(item["field_name"]): item
        for item in widget_records
        if item.get("field_name")
    }
    node_addresses = _node_addresses(node_bindings)
    disposition_by_field = _dispositions(field_map)
    explicit_out_of_profile = {_canonical_line(item) for item in out_of_profile}
    findings: list[StructuralFinding] = []
    findings.extend(
        check_heading_integrity(
            document,
            identities=identities,
            mapping_by_field=mapping_by_field,
            nodes_by_id=node_records_by_id,
        )
    )
    amount_lines = (
        {_canonical_line(item) for item in printed_amount_lines}
        if printed_amount_lines is not None
        else {
            item.line
            for item in identities
            if item.status == "resolved" and item.role == "amount" and item.line is not None
        }
    )
    findings.extend(
        check_line_coverage(
            document,
            identities=identities,
            mapping_by_field=mapping_by_field,
            disposition_by_field=disposition_by_field,
            printed_amount_lines=amount_lines,
            out_of_profile=explicit_out_of_profile,
        )
    )
    totals = (
        {_canonical_line(item) for item in total_lines}
        if total_lines is not None
        else _total_lines(rendered_text)
    )
    findings.extend(
        check_total_presence(
            document,
            total_lines=totals,
            mapping_by_field=mapping_by_field,
            nodes_by_id=node_records_by_id,
            node_addresses=node_addresses,
            widget_by_field=widget_by_field,
            out_of_profile=explicit_out_of_profile,
        )
    )
    findings.extend(
        check_line_identity_triangle(
            document,
            identities=identities,
            mapping_by_field=mapping_by_field,
            widget_by_field=widget_by_field,
            node_addresses=node_addresses,
        )
    )
    return tuple(findings)


def check_heading_integrity(
    document: str,
    *,
    identities: Iterable[FieldIdentity],
    mapping_by_field: Mapping[str, Mapping[str, Any]],
    nodes_by_id: Mapping[str, Mapping[str, Any]],
) -> tuple[StructuralFinding, ...]:
    """Flag a heading, section, or concept node owning a resolved amount cell."""
    findings: list[StructuralFinding] = []
    for identity in identities:
        if identity.status != "resolved" or identity.role != "amount":
            continue
        mapping = mapping_by_field.get(identity.field_name)
        node_id = mapping.get("node_id") if mapping else None
        node = nodes_by_id.get(str(node_id)) if node_id else None
        if node is None or not _is_heading(node):
            continue
        findings.append(
            _finding(
                document,
                identity.field_name,
                "heading_integrity",
                observed={"node_id": node_id, "node_type": node.get("node_type"), "value_type": node.get("value_type")},
                expected="amount control owned by a fillable non-heading node",
                evidence=(
                    "resolver identity: line=%s/role=%s" % identity.identity,
                    "node label: %s" % str(node.get("label", "")),
                    "heading marker: %s" % _heading_marker(node),
                ),
            )
        )
    return tuple(findings)


def check_line_coverage(
    document: str,
    *,
    identities: Iterable[FieldIdentity],
    mapping_by_field: Mapping[str, Mapping[str, Any]],
    disposition_by_field: Mapping[str, Mapping[str, Any]],
    printed_amount_lines: Iterable[str],
    out_of_profile: Iterable[str] = (),
) -> tuple[StructuralFinding, ...]:
    """Require one mapped node per printed amount line or explicit disposition."""
    by_line: dict[str, list[FieldIdentity]] = {}
    for identity in identities:
        if identity.status == "resolved" and identity.role == "amount" and identity.line in printed_amount_lines:
            by_line.setdefault(str(identity.line), []).append(identity)
    out_lines = {_canonical_line(item) for item in out_of_profile}
    findings: list[StructuralFinding] = []
    for line in sorted({_canonical_line(item) for item in printed_amount_lines}, key=_line_sort_key):
        controls = by_line.get(line, [])
        node_ids = sorted(
            {
                str(mapping_by_field[item.field_name]["node_id"])
                for item in controls
                if mapping_by_field.get(item.field_name, {}).get("node_id")
            }
        )
        explicitly_disposed = (line in out_lines or (
            bool(controls)
            and all(
                _unsupported(disposition_by_field.get(item.field_name))
                for item in controls
                if not mapping_by_field.get(item.field_name, {}).get("node_id")
            )
            and any(not mapping_by_field.get(item.field_name, {}).get("node_id") for item in controls)
        )) and not node_ids
        if len(node_ids) == 1 or explicitly_disposed:
            continue
        findings.append(
            _finding(
                document,
                _control_for_line(controls, line),
                "line_coverage",
                observed={"line": line, "controls": [item.field_name for item in controls], "node_ids": node_ids},
                expected="exactly one node or explicit out-of-profile disposition",
                evidence=(
                    "resolver amount identities: %s" % (", ".join(item.field_name for item in controls) or "none"),
                    "field-map node ids: %s" % (", ".join(node_ids) or "none"),
                ),
            )
        )
    return tuple(findings)


def check_total_presence(
    document: str,
    *,
    total_lines: Iterable[str],
    mapping_by_field: Mapping[str, Mapping[str, Any]],
    nodes_by_id: Mapping[str, Mapping[str, Any]],
    node_addresses: Mapping[str, tuple[str, ...]],
    widget_by_field: Mapping[str, Mapping[str, Any]],
    out_of_profile: Iterable[str] = (),
) -> tuple[StructuralFinding, ...]:
    """Require every PDF-present total to have a graph node or explicit waiver."""
    del widget_by_field
    out_lines = {_canonical_line(item) for item in out_of_profile}
    findings: list[StructuralFinding] = []
    for line in sorted({_canonical_line(item) for item in total_lines}, key=_line_sort_key):
        node_ids = sorted(
            node_id
            for node_id in nodes_by_id
            if _node_line(node_id, nodes_by_id.get(node_id), node_addresses.get(node_id, ())) == line
        )
        if node_ids or line in out_lines:
            continue
        findings.append(
            _finding(
                document,
                "line=%s" % line,
                "total_presence",
                observed={"pdf_total_line": line, "node_ids": node_ids},
                expected="form total has a graph node or explicit out-of-profile disposition",
                evidence=(
                    "total line supplied by rendered PDF caption evidence",
                    "promoted node inventory has no bound node for line %s" % line,
                ),
            )
        )
    return tuple(findings)


def check_line_identity_triangle(
    document: str,
    *,
    identities: Iterable[FieldIdentity],
    mapping_by_field: Mapping[str, Mapping[str, Any]],
    widget_by_field: Mapping[str, Mapping[str, Any]],
    node_addresses: Mapping[str, tuple[str, ...]],
) -> tuple[StructuralFinding, ...]:
    """Require resolver, widget, and node binding lines to agree."""
    findings: list[StructuralFinding] = []
    for identity in identities:
        mapping = mapping_by_field.get(identity.field_name, {})
        widget = widget_by_field.get(identity.field_name, {})
        node_id = mapping.get("node_id")
        bound_addresses = node_addresses.get(str(node_id), ()) if node_id else ()
        widget_address = widget.get("address_id")
        mapping_address = mapping.get("address_id")
        bound_lines = tuple(
            sorted(
                {
                    line
                    for address in (*bound_addresses, str(mapping_address or ""))
                    if (line := _address_line(address)) is not None
                },
                key=_line_sort_key,
            )
        )
        widget_line = _address_line(widget_address)
        if identity.status != "resolved":
            findings.append(
                _finding(
                    document,
                    identity.field_name,
                    "line_identity_triangle",
                    observed={"resolver": identity.identity, "status": identity.status},
                    expected="resolver-derived line and role",
                    evidence=identity.evidence,
                )
            )
            continue
        resolver_line, resolver_role = identity.identity
        mismatch = (
            resolver_line is None
            or (bound_lines and resolver_line not in bound_lines)
            or (widget_line is not None and widget_line != resolver_line)
        )
        if not mismatch:
            continue
        findings.append(
            _finding(
                document,
                identity.field_name,
                "line_identity_triangle",
                observed={
                    "resolver": {"line": resolver_line, "role": resolver_role},
                    "widget_line": widget_line,
                    "node_lines": bound_lines,
                },
                expected={"line": resolver_line, "role": resolver_role},
                evidence=(
                    "resolver evidence: %s" % ", ".join(identity.evidence),
                    "widget address: %s" % (widget_address or "unbound"),
                    "node binding addresses: %s" % (", ".join(bound_addresses) or "unbound"),
                ),
            )
        )
    return tuple(findings)


def validate_promoted_corpus(year: str | int, root: str | Path) -> tuple[DocumentStructuralReport, ...]:
    """Run the checks read-only over promoted field maps for one tax year."""
    root_path = Path(root)
    graph_root = root_path / "graph" / str(year)
    node_by_document: dict[str, list[dict[str, Any]]] = {}
    for path in sorted((graph_root / "nodes").glob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        for node in payload if isinstance(payload, list) else payload.get("nodes", []):
            node_by_document.setdefault(str(node.get("document_id", "")), []).append(node)
    reports: list[DocumentStructuralReport] = []
    for field_map_path in sorted((graph_root / "field_maps").glob("*.yaml")):
        field_map = yaml.safe_load(field_map_path.read_text(encoding="utf-8")) or {}
        document = str(field_map["document_id"])
        inventory = json.loads((root_path / str(field_map["inventory"])).read_text(encoding="utf-8"))
        widget_path = graph_root / "bindings" / "widgets" / (document + ".yaml")
        node_path = graph_root / "bindings" / "nodes" / (document + ".yaml")
        widgets = _bindings(widget_path)
        bindings = _bindings(node_path)
        text_path = root_path / ".cache" / "raw" / str(year) / (document + ".txt")
        rendered = text_path.read_text(encoding="utf-8") if text_path.is_file() else None
        findings = check_document_structure(
            document,
            fields=inventory.get("fields", []),
            field_map=field_map,
            nodes=node_by_document.get(document, []),
            widget_bindings=widgets,
            node_bindings=bindings,
            rendered_text=rendered,
        )
        reports.append(DocumentStructuralReport(document, findings))
    return tuple(reports)


def _finding(document: str, control: str, validator: str, *, observed: Any, expected: Any, evidence: Sequence[str]) -> StructuralFinding:
    return StructuralFinding(document, control, validator, observed, expected, tuple(str(item) for item in evidence))


def _bindings(path: Path) -> tuple[dict[str, Any], ...]:
    if not path.is_file():
        return ()
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return tuple(payload.get("bindings", ()))


def _node_addresses(bindings: Iterable[Mapping[str, Any]]) -> dict[str, tuple[str, ...]]:
    result: dict[str, list[str]] = {}
    for item in bindings:
        node_id = item.get("node_id")
        address_id = item.get("address_id")
        if node_id and address_id:
            result.setdefault(str(node_id), []).append(str(address_id))
    return {key: tuple(sorted(values)) for key, values in result.items()}


def _dispositions(field_map: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    values = field_map.get("field_dispositions", field_map.get("dispositions", ()))
    return {str(item.get("field_name")): item for item in values if item.get("field_name")}


def _unsupported(disposition: Mapping[str, Any] | None) -> bool:
    return bool(disposition and disposition.get("population_policy") in {"unsupported", "intentionally_blank"})


def _is_heading(node: Mapping[str, Any]) -> bool:
    node_type = str(node.get("node_type", "")).lower()
    value_type = str(node.get("value_type", "")).lower()
    label = str(node.get("label", "")).strip()
    return node_type in {"heading", "section", "concept"} or value_type in {"heading", "section", "concept"} or label.endswith(":")


def _heading_marker(node: Mapping[str, Any]) -> str:
    if str(node.get("node_type", "")).lower() in {"heading", "section", "concept"}:
        return "node_type"
    if str(node.get("value_type", "")).lower() in {"heading", "section", "concept"}:
        return "value_type"
    return "printed label ends with colon"


def _address_line(address_id: Any) -> str | None:
    if not address_id:
        return None
    try:
        _year, components = parse_address_id(str(address_id))
    except (ValueError, TypeError):
        return None
    for component in reversed(components):
        if component.kind in {"line", "box"}:
            return _canonical_line(component.token) if component.kind == "line" else "box:%s" % component.token.lower()
    return None


def _node_line(node_id: str, node: Mapping[str, Any] | None, addresses: Sequence[str]) -> str | None:
    for address in addresses:
        line = _address_line(address)
        if line is not None:
            return line
    match = re.search(r"_line_([0-9]+[a-z]?)$", node_id, re.IGNORECASE)
    if match:
        return _canonical_line(match.group(1))
    if node:
        match = _LINE_RE.search(str(node.get("label", "")))
        if match:
            return _canonical_line(match.group("line"))
    return None


def _control_for_line(controls: Sequence[FieldIdentity], line: str) -> str:
    return controls[0].field_name if controls else "line=%s" % line


def _canonical_line(value: Any) -> str:
    token = str(value).strip().lower()
    return "1z" if token == "z" else token


def _line_sort_key(value: str) -> tuple[int, str]:
    match = re.match(r"^(\d+)([a-z]*)$", value)
    return (int(match.group(1)), match.group(2)) if match else (10**9, value)


def _total_lines(rendered_text: str | Sequence[str] | None) -> set[str]:
    if rendered_text is None:
        return set()
    lines = rendered_text.splitlines() if isinstance(rendered_text, str) else tuple(str(item) for item in rendered_text)
    totals: set[str] = set()
    for line in lines:
        match = _CAPTION_RE.match(line)
        if not match:
            continue
        text = match.group("text").lower()
        if "total" in text or "add lines" in text or "these are your total" in text:
            totals.add(_canonical_line(match.group("ref")))
    return totals


__all__ = [
    "DocumentStructuralReport",
    "StructuralFinding",
    "check_document_structure",
    "check_heading_integrity",
    "check_line_coverage",
    "check_line_identity_triangle",
    "check_total_presence",
    "validate_heading_integrity",
    "validate_line_coverage",
    "validate_total_presence",
    "validate_line_identity_triangle",
    "validate_promoted_corpus",
]

# Descriptive aliases keep the four validators easy to discover without
# creating a second implementation surface.
validate_heading_integrity = check_heading_integrity
validate_line_coverage = check_line_coverage
validate_total_presence = check_total_presence
validate_line_identity_triangle = check_line_identity_triangle
