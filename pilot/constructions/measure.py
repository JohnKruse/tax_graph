"""Measure IRS construction patterns in a candidate derivation workspace.

This pilot is intentionally independent from the production pipeline.  It
reads the source reports copied into a candidate workspace, treats every
printed anchor as the denominator, and reports which outcome each matching
anchor reached.  The vocabulary section is collected from the source text;
it is not checked against an authored operation list.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections import defaultdict
from pathlib import Path
import re
import sys
from typing import Any, Callable, Iterable, Mapping

import yaml

PILOT_ROOT = Path(__file__).resolve().parents[1]
if str(PILOT_ROOT) not in sys.path:
    sys.path.insert(0, str(PILOT_ROOT))
import cell_access


REPORT_SUFFIX = "_derive_cells_report.yaml"
EXAMPLE_LIMIT = 10
OUTCOME_KEYS = ("derived", "repaired", "errored", "skipped")


def _row_with_cell(
    source: Mapping[str, Any] | None,
    candidate: Mapping[str, Any] | None,
    anchor: Mapping[str, Any] | None,
    line: str,
    *,
    printed_anchor_index: int | None = None,
) -> dict[str, Any]:
    """Keep source records separate and attach the one joined cell view."""

    if source is not None:
        row = dict(source)
    elif candidate is not None:
        row = dict(candidate)
    else:
        row = {"line": line}
    row["line"] = line
    if printed_anchor_index is not None:
        row["printed_anchor_index"] = printed_anchor_index
    row["_cell"] = cell_access.join_rows(
        anchor=anchor,
        source=source,
        candidate=candidate,
    )
    return row


def _normalise_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _line_key(value: Any) -> str:
    return _normalise_space(value).lower()


def _first_int(*values: Any, default: int = 0) -> int:
    for value in values:
        if value is None or value == "":
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return default


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a YAML object")
    return value


def _row_text(row: Mapping[str, Any]) -> str:
    cell = row.get("_cell")
    if not isinstance(cell, cell_access.Cell):
        cell = cell_access.join_rows(source=row, anchor=row)
    parts: list[str] = []
    text_values = (
        cell_access.label(cell),
        cell_access.form_face(cell),
        cell_access.instruction_section(cell),
        cell_access.quote(cell),
    )
    for text_value in text_values:
        if text_value.value is None:
            continue
        value = _normalise_space(text_value.value)
        if value and value not in parts:
            parts.append(value)
    return " ".join(parts)


def _anchor_id(document_id: str, row: Mapping[str, Any]) -> str:
    cell = row.get("_cell")
    if not isinstance(cell, cell_access.Cell):
        cell = cell_access.join_rows(source=row, anchor=row)
    node_value = cell_access.node_id(cell)
    explicit = _normalise_space(node_value.value) if node_value.value is not None else ""
    if explicit:
        return explicit
    line = _line_key(row.get("line"))
    anchor_index = row.get("printed_anchor_index")
    if anchor_index:
        return f"{document_id}#anchor={anchor_index}:line={line}"
    return f"{document_id}#line={line}"


def _outcome(row: Mapping[str, Any]) -> str:
    cell = row.get("_cell")
    if not isinstance(cell, cell_access.Cell):
        cell = cell_access.join_rows(source=row, anchor=row)
    status_value = cell_access.status(cell)
    raw = _line_key(status_value.value) if status_value.value is not None else ""
    if raw in {"derived", "repaired", "skipped"}:
        return raw
    if raw in {"error", "errored", "gapped", "review_gap", ""}:
        return "errored"
    return "errored"


def _raw_status(row: Mapping[str, Any]) -> str:
    cell = row.get("_cell")
    if not isinstance(cell, cell_access.Cell):
        cell = cell_access.join_rows(source=row, anchor=row)
    status_value = cell_access.status(cell)
    raw = _line_key(status_value.value) if status_value.value is not None else ""
    return raw if raw else "missing"


def _report_rows(candidate_root: Path, report: Mapping[str, Any]) -> list[dict[str, Any]]:
    document_id = _normalise_space(report.get("document_id"))
    raw_rows_by_line: dict[str, list[dict[str, Any]]] = defaultdict(list)

    raw_rows = report.get("rows_detail")
    if isinstance(raw_rows, list):
        for value in raw_rows:
            if not isinstance(value, Mapping):
                continue
            line = _line_key(value.get("line"))
            if line:
                raw_rows_by_line[line].append(dict(value))

    candidate_rows_by_line: dict[str, list[dict[str, Any]]] = defaultdict(list)

    candidate_rows_path = (
        candidate_root
        / "graph"
        / str(report.get("year") or "2025")
        / "_drafts"
        / document_id
        / "rows.yaml"
    )
    if candidate_rows_path.is_file():
        candidate_rows = yaml.safe_load(candidate_rows_path.read_text(encoding="utf-8"))
        if isinstance(candidate_rows, list):
            for value in candidate_rows:
                if not isinstance(value, Mapping):
                    continue
                line = _line_key(value.get("line"))
                if not line:
                    continue
                candidate_rows_by_line[line].append(dict(value))

    denominator = report.get("denominator")
    anchors = denominator.get("anchors") if isinstance(denominator, Mapping) else None
    if isinstance(anchors, list):
        line_counts = Counter(
            _line_key(value.get("anchor") or value.get("line"))
            for value in anchors
            if isinstance(value, Mapping)
        )
        rows: list[dict[str, Any]] = []
        for index, value in enumerate(anchors, start=1):
            if not isinstance(value, Mapping):
                continue
            line = _line_key(value.get("anchor") or value.get("line"))
            if not line:
                continue
            skip_reason = _normalise_space(value.get("skip_reason"))
            if skip_reason:
                source = {
                    "line": line,
                    "label_after": value.get("label_after"),
                    "form_face_after": value.get("form_face_text"),
                    "status": "skipped",
                    "error": skip_reason,
                }
                candidate = None
            else:
                source = raw_rows_by_line[line].pop(0) if raw_rows_by_line[line] else None
                candidate = candidate_rows_by_line[line].pop(0) if candidate_rows_by_line[line] else None
                if source is None and candidate is None:
                    source = {
                        "line": line,
                        "label_after": value.get("label_after"),
                        "form_face_after": value.get("form_face_text"),
                        "status": "error",
                        "error": "missing derivation row for admitted anchor",
                    }
            row = _row_with_cell(
                source,
                candidate,
                value,
                line,
                printed_anchor_index=index if line_counts[line] > 1 else None,
            )
            rows.append(row)
    else:
        rows = []
        for line, values in raw_rows_by_line.items():
            rows.extend(_row_with_cell(value, None, value, line) for value in values)
        for line, values in candidate_rows_by_line.items():
            if not raw_rows_by_line[line]:
                rows.extend(_row_with_cell(None, value, value, line) for value in values)

    printed = _first_int(
        report.get("line_anchor_count"),
        denominator.get("line_anchor_count") if isinstance(denominator, Mapping) else None,
        len(anchors) if isinstance(anchors, list) else None,
        len(rows),
    )
    if printed != len(rows):
        raise ValueError(
            f"{document_id}: printed anchor count is {printed}, but only {len(rows)} anchor rows are available"
        )
    return [dict(row, line=_line_key(row.get("line"))) for row in rows]


def _match_parenthetical(text: str) -> list[str]:
    return [
        _normalise_space(match.group(0))
        for match in re.finditer(r"\([^()\n]{2,160}\)", text)
        if re.search(r"\bif\b", match.group(0), re.IGNORECASE)
    ]


def _match_checkbox(text: str) -> list[str]:
    return [
        _normalise_space(match.group(0))
        for match in re.finditer(r"\b(?:check(?:ed)?|checkbox|box)\b", text, re.IGNORECASE)
    ]


def _match_smaller(text: str) -> list[str]:
    return [
        _normalise_space(match.group(0))
        for match in re.finditer(r"\b(?:smaller|smallest)\s+of\b", text, re.IGNORECASE)
    ]


def _match_if_otherwise(text: str) -> list[str]:
    if re.search(r"\bif\b", text, re.IGNORECASE) and re.search(r"\botherwise\b", text, re.IGNORECASE):
        return ["If ... Otherwise ..."]
    return []


def _match_zero_or_less(text: str) -> list[str]:
    return [
        _normalise_space(match.group(0))
        for match in re.finditer(r"if\s+zero\s+or\s+less,?\s+enter\s+-?0-", text, re.IGNORECASE)
    ]


CONSTRUCTION_MATCHERS: tuple[tuple[str, str, Callable[[str], list[str]]], ...] = (
    (
        "parenthetical_base_variant_condition",
        "BASE (VARIANT if CONDITION)",
        _match_parenthetical,
    ),
    ("checkbox_line", "checkbox line", _match_checkbox),
    ("smaller_or_smallest_of", "smaller of / smallest of", _match_smaller),
    ("if_otherwise", "If ... Otherwise ...", _match_if_otherwise),
    ("zero_or_less_floor", "If zero or less, enter -0-", _match_zero_or_less),
)


INCLUSIVE_COMPARATORS = re.compile(
    r"\b(?:at\s+least|no\s+(?:more|less)\s+than|equal\s+to\s+or\s+(?:less|more)|or\s+(?:less|more|greater))\b",
    re.IGNORECASE,
)
EXCLUSIVE_COMPARATORS = re.compile(
    r"\b(?:less\s+than|more\s+than|greater\s+than|under|below|over|exceeds)\b",
    re.IGNORECASE,
)
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'-]*|\$?\d[\d,]*(?:\.\d+)?%?")


def _empty_outcomes() -> dict[str, int]:
    return {key: 0 for key in OUTCOME_KEYS}


def _cross_tab(rows: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    result = _empty_outcomes()
    for row in rows:
        result[_outcome(row)] += 1
    return result


def _construction_record(
    construction_id: str,
    label: str,
    matches: Mapping[str, list[tuple[Mapping[str, Any], list[str]]]],
) -> dict[str, Any]:
    values = matches.get(construction_id, [])
    phrase_counts: Counter[str] = Counter()
    examples: list[str] = []
    rows: list[Mapping[str, Any]] = []
    for row, phrases in values:
        rows.append(row)
        anchor = _anchor_id(_normalise_space(row.get("document_id")), row)
        if anchor not in examples and len(examples) < EXAMPLE_LIMIT:
            examples.append(anchor)
        phrase_counts.update(_normalise_space(phrase).lower() for phrase in phrases if _normalise_space(phrase))
    return {
        "id": construction_id,
        "label": label,
        "count": len(values),
        "example_anchor_ids": examples,
        "outcomes": _cross_tab(rows),
        "corpus_phrases": dict(sorted(phrase_counts.items())),
    }


def _document_record(document_id: str, report: Mapping[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    denominator = report.get("denominator") if isinstance(report.get("denominator"), Mapping) else {}
    status_counts = Counter(_raw_status(row) for row in rows)
    outcome_counts = _cross_tab(rows)
    return {
        "document_id": document_id,
        "printed_anchors": len(rows),
        "selected": _first_int(report.get("rows"), len(report.get("rows_detail") or [])),
        "attempted": _first_int(report.get("rows_attempted"), report.get("validation", {}).get("attempted") if isinstance(report.get("validation"), Mapping) else None),
        "outcomes": outcome_counts,
        "raw_status_counts": dict(sorted(status_counts.items())),
        "skipped_by_reason": dict(sorted((str(key), _first_int(value)) for key, value in denominator.get("skipped_by_reason", {}).items())) if isinstance(denominator.get("skipped_by_reason"), Mapping) else {},
    }


def measure(candidate_root: str | Path) -> dict[str, Any]:
    """Return a construction inventory for one candidate workspace."""

    root = Path(candidate_root).resolve()
    source_reports = root / "source_reports"
    if not source_reports.is_dir():
        raise ValueError(f"candidate root has no source_reports directory: {root}")
    candidate_manifest = _load_yaml(root / "candidate.yaml") if (root / "candidate.yaml").is_file() else {}
    expected = [str(value) for value in candidate_manifest.get("documents", [])]
    report_paths = sorted(source_reports.glob(f"*{REPORT_SUFFIX}"))
    if not report_paths:
        raise ValueError(f"candidate root has no {REPORT_SUFFIX} files: {root}")

    reports: list[tuple[str, dict[str, Any], list[dict[str, Any]]]] = []
    for path in report_paths:
        report = _load_yaml(path)
        document_id = _normalise_space(report.get("document_id"))
        if not document_id:
            raise ValueError(f"{path}: missing document_id")
        rows = _report_rows(root, report)
        for row in rows:
            row["document_id"] = document_id
        reports.append((document_id, report, rows))

    actual = [document_id for document_id, _report, _rows in reports]
    if expected and sorted(expected) != sorted(actual):
        raise ValueError(
            "candidate manifest documents do not match source reports: "
            f"expected {sorted(expected)}, found {sorted(actual)}"
        )

    all_rows = [row for _document_id, _report, rows in reports for row in rows]
    matches: dict[str, list[tuple[Mapping[str, Any], list[str]]]] = {key: [] for key, _label, _matcher in CONSTRUCTION_MATCHERS}
    token_counts: Counter[str] = Counter()
    phrase_counts: Counter[str] = Counter()
    inclusive_rows: list[Mapping[str, Any]] = []
    exclusive_rows: list[Mapping[str, Any]] = []
    for row in all_rows:
        text = _row_text(row)
        token_counts.update(token.lower() for token in TOKEN_RE.findall(text))
        for construction_id, _label, matcher in CONSTRUCTION_MATCHERS:
            phrases = matcher(text)
            if phrases:
                matches[construction_id].append((row, phrases))
                phrase_counts.update(_normalise_space(phrase).lower() for phrase in phrases)
        if INCLUSIVE_COMPARATORS.search(text):
            inclusive_rows.append(row)
        if EXCLUSIVE_COMPARATORS.search(text):
            exclusive_rows.append(row)

    comparator_rows = {id(row): row for row in inclusive_rows + exclusive_rows}
    comparator_outcomes = _cross_tab(comparator_rows.values())
    comparator_examples = [
        _anchor_id(_normalise_space(row.get("document_id")), row)
        for row in comparator_rows.values()
    ][:EXAMPLE_LIMIT]
    construction_records = [
        _construction_record(construction_id, label, matches)
        for construction_id, label, _matcher in CONSTRUCTION_MATCHERS
    ]

    document_records = {
        document_id: _document_record(document_id, report, rows)
        for document_id, report, rows in reports
    }
    return {
        "schema_version": 1,
        "kind": "construction_inventory",
        "source_candidate": str(root),
        "documents": [document_id for document_id, _report, _rows in reports],
        "denominator": {
            "printed_anchors": len(all_rows),
            "selected": sum(item["selected"] for item in document_records.values()),
            "attempted": sum(item["attempted"] for item in document_records.values()),
            "outcomes": _cross_tab(all_rows),
            "documents": document_records,
        },
        "constructions": construction_records,
        "comparator_gap": {
            "inclusive_or_exclusive_anchor_count": len(comparator_rows),
            "inclusive_anchor_count": len({id(row) for row in inclusive_rows}),
            "exclusive_anchor_count": len({id(row) for row in exclusive_rows}),
            "example_anchor_ids": comparator_examples,
            "outcomes": comparator_outcomes,
        },
        "vocabulary": {
            "source": "all printed-anchor text in the candidate reports",
            "token_counts": dict(sorted(token_counts.items())),
            "matched_phrase_counts": dict(sorted(phrase_counts.items())),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure constructions in a candidate graph workspace.")
    parser.add_argument("candidate_root", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    inventory = measure(args.candidate_root)
    output = (args.output or args.candidate_root / "constructions.yaml").resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        yaml.safe_dump(inventory, sort_keys=False, allow_unicode=False),
        encoding="ascii",
        newline="\n",
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
