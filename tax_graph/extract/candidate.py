"""Build a review-only candidate graph from a completed derivation run.

The provider run is deliberately outside this module.  A completed run is
evidence; this module turns that evidence into a candidate draft, coverage
report, and handcrafted-graph diff.  The output is always outside the
published graph and carries no human-review claim.
"""

from __future__ import annotations

from collections import defaultdict
import re
import shutil
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import yaml

from tax_graph.acquire.manifest import load_manifest
from tax_graph.extract.cells import expression_to_graph, get_structural_skip_reason
from tax_graph.io.loader import load_graph
from tax_graph.operation_registry import OPERATION_SPECS, projection_rule_for


CANDIDATE_SCHEMA_VERSION = 1
DERIVATION_REPORT_SUFFIX = "_derive_cells_report.yaml"


def write_candidate_from_run(
    run_dir: str | Path,
    output_dir: str | Path,
    *,
    root: str | Path,
    year: str | int = "2025",
    expected_documents: Sequence[str] | None = None,
) -> Path:
    """Write one candidate workspace from a complete provider run.

    ``run_dir`` must contain one top-level derivation report per expected
    manifest document.  ``output_dir`` must be outside ``root`` and must not
    already exist.  The returned directory contains ``candidate.yaml``, a
    report-backed draft directory, a handcrafted diff, and a publish plan.
    """
    root_path = Path(root).resolve()
    source = Path(run_dir).resolve()
    destination = Path(output_dir).resolve()
    _require_directory(source, "run directory")
    _require_new_external_directory(destination, root_path)

    reports = _load_reports(source, year=str(year))
    expected = list(expected_documents) if expected_documents is not None else _manifest_documents(root_path, year)
    report_ids = {item[0] for item in reports}
    missing = sorted(set(expected) - report_ids)
    unexpected = sorted(report_ids - set(expected))
    if missing:
        raise ValueError(
            "full derivation run is missing expected documents: " + ", ".join(missing)
        )
    if unexpected:
        raise ValueError(
            "derivation run contains documents outside the expected set: "
            + ", ".join(unexpected)
        )

    destination.mkdir(parents=True)
    graph_root = destination / "graph" / str(year) / "_drafts"
    report_root = destination / "source_reports"
    graph_root.mkdir(parents=True)
    report_root.mkdir()

    documents: list[dict[str, Any]] = []
    for document_id, report_path, report in reports:
        copied_report = report_root / report_path.name
        shutil.copy2(report_path, copied_report)
        documents.append(
            _write_document_candidate(
                report,
                report_path=report_path,
                destination=graph_root / document_id,
                root=root_path,
                year=str(year),
            )
        )

    stub_registry = _stub_registry(
        documents,
        year=str(year),
        real_document_ids={item[0] for item in reports},
    )
    _write_stub_documents(
        stub_registry,
        destination=graph_root,
    )

    worksheet_report = _copy_worksheet_drafts(
        root_path,
        year=str(year),
        destination=graph_root,
    )
    graph_integrity = _assert_candidate_operand_resolution(graph_root)
    _write_yaml(destination / "stub_lifecycle.yaml", stub_registry["lifecycle"])
    graph_diff = _handcrafted_diff(root_path, str(year), documents)
    coverage = _coverage_total(documents)
    publish = {
        "status": "not_published",
        "would_replace": [
            f"graph/{year}/nodes",
            f"graph/{year}/edges",
            f"graph/{year}/rules",
            f"graph/{year}/citations",
        ],
        "rollback": "restore the prior committed graph tree after review",
        "human_confirmed": False,
    }
    manifest = {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "kind": "candidate_graph",
        "year": str(year),
        "status": "pending_review",
        "source_run": str(source),
        "documents": [
            item["document_id"] for item in documents
        ] + stub_registry["document_ids"],
        "source_documents": [item["document_id"] for item in documents],
        "stub_documents": stub_registry["document_ids"],
        "coverage": coverage,
        "stub_lifecycle": stub_registry["lifecycle"],
        "graph_integrity": graph_integrity,
        "worksheet_drafts": worksheet_report,
        "diff": graph_diff,
        "publish": publish,
    }
    _write_yaml(destination / "candidate.yaml", manifest)
    _write_yaml(destination / "coverage.yaml", coverage)
    _write_yaml(destination / "diff.yaml", graph_diff)
    _write_yaml(destination / "publish.yaml", publish)
    return destination


def build_candidate_from_run(
    run_dir: str | Path,
    *,
    root: str | Path,
    year: str | int = "2025",
    expected_documents: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Build the candidate payload without writing it.

    This is the deterministic inspection seam used by tests and by callers
    that want to review coverage before choosing an output directory.
    """
    root_path = Path(root).resolve()
    source = Path(run_dir).resolve()
    _require_directory(source, "run directory")
    reports = _load_reports(source, year=str(year))
    expected = list(expected_documents) if expected_documents is not None else _manifest_documents(root_path, year)
    report_ids = {item[0] for item in reports}
    missing = sorted(set(expected) - report_ids)
    unexpected = sorted(report_ids - set(expected))
    if missing:
        raise ValueError(
            "full derivation run is missing expected documents: " + ", ".join(missing)
        )
    if unexpected:
        raise ValueError(
            "derivation run contains documents outside the expected set: "
            + ", ".join(unexpected)
        )
    documents = [
        _document_candidate(
            report,
            report_path=report_path,
            root=root_path,
            year=str(year),
        )
        for _document_id, report_path, report in reports
    ]
    stub_registry = _stub_registry(
        documents,
        year=str(year),
        real_document_ids={item[0] for item in reports},
    )
    return {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "kind": "candidate_graph",
        "year": str(year),
        "status": "pending_review",
        "source_run": str(source),
        "documents": [
            item["document_id"] for item in documents
        ] + stub_registry["document_ids"],
        "source_documents": [item["document_id"] for item in documents],
        "stub_documents": stub_registry["document_ids"],
        "coverage": _coverage_total(documents),
        "stub_lifecycle": stub_registry["lifecycle"],
        "diff": _handcrafted_diff(root_path, str(year), documents),
    }


def candidate_graph_root(candidate_root: str | Path, year: str | int) -> Path:
    """Return the candidate graph directory within a candidate workspace."""
    return Path(candidate_root).resolve() / "graph" / str(year)


def _write_document_candidate(
    report: Mapping[str, Any],
    *,
    report_path: Path,
    destination: Path,
    root: Path,
    year: str,
) -> dict[str, Any]:
    document = _document_candidate(report, report_path=report_path, root=root, year=year)
    destination.mkdir(parents=True)
    rows = document["rows"]
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    rules: list[dict[str, Any]] = []
    citations: list[dict[str, Any]] = []
    spans: list[dict[str, Any]] = []
    seen_nodes: set[str] = set()
    seen_edges: set[str] = set()
    seen_rules: set[str] = set()
    seen_citations: set[str] = set()
    seen_spans: set[str] = set()
    formula_cells: list[dict[str, Any]] = []
    control_roles = _field_control_roles(root, year, document["document_id"])

    for row in rows:
        line = str(row["line"])
        target = str(row["node_id"])
        row_citations = list(row.get("citation_refs") or [])
        for citation_id in row_citations:
            if citation_id in seen_citations:
                continue
            seen_citations.add(citation_id)
            citations.append(
                {
                    "citation_id": citation_id,
                    "source_document_id": document["document_id"],
                    "quoted_text": row.get("quote") or "",
                    "locator": f"line {line}",
                    "resolved": True,
                }
            )
        if row.get("quote_span_id") and row.get("quote"):
            span_id = str(row["quote_span_id"])
            if span_id not in seen_spans:
                seen_spans.add(span_id)
                spans.append(
                    {
                        "span_id": span_id,
                        "document_id": document["document_id"],
                        "relationship": "source",
                        "locator": f"line {line}",
                        "text": row["quote"],
                    }
                )

        formula_cells.append(
            {
                "target_cell_id": target,
                "line_anchor": line,
                "label": row.get("label") or "",
                "status": "complete" if row["candidate_status"] in {"derived", "repaired"} else "review_gap",
                "has_expression": bool(row.get("expression")),
                "has_verbatim_citation": bool(row_citations),
                "has_form_face_citation": bool(row_citations),
                "citation_refs": row_citations,
                "citation_span_ids": row_citations,
                "quote": row.get("quote") or "",
                "review_gap": row.get("review_gap") or None,
            }
        )
        expression = row.get("expression")
        if row["candidate_status"] not in {"derived", "repaired"} or not isinstance(expression, Mapping):
            continue
        citation_id = row_citations[0] if row_citations else ""
        if not citation_id:
            continue
        try:
            projection = expression_to_graph(
                form=document["document_id"],
                line=line,
                expression=expression,
                quote_span_id=citation_id,
                evidence_text=" ".join(
                    str(value or "")
                    for value in (row.get("form_face_text"), row.get("instruction_text"), row.get("quote"))
                ),
            )
        except (TypeError, ValueError) as exc:
            row["candidate_status"] = "review_gap"
            row.setdefault("findings", []).append(
                {
                    "kind": "candidate_projection_error",
                    "message": f"{type(exc).__name__}: {exc}",
                }
            )
            continue
        projection_parameters = _projection_rule_parameters(expression)
        target_rule_id = f"rule_{target}_candidate"
        _add_node(
            nodes,
            seen_nodes,
            {
                "node_id": target,
                "document_id": document["document_id"],
                "label": _node_label(row, line),
                "node_type": "computed",
                "value_type": "currency",
                "required": "optional",
                "citation_refs": [citation_id],
            },
        )
        for item in projection.nodes:
            item = dict(item)
            item.setdefault("citation_refs", [citation_id])
            _add_node(nodes, seen_nodes, item)
        for source in _expression_leaf_nodes(
            expression,
            document["document_id"],
            control_roles=control_roles,
        ):
            if source["node_id"] not in seen_nodes and source["node_id"] != target:
                _add_node(nodes, seen_nodes, {**source, "citation_refs": [citation_id]})
        target_rule = {
            "rule_id": target_rule_id,
            "operation": str(expression.get("op") or "").upper(),
            "description": f"Candidate derivation for {document['document_id']} line {line}.",
            "citation_refs": [citation_id],
        }
        target_parameters = _rule_parameters(expression)
        if target_parameters:
            target_rule["parameters"] = target_parameters
        _add_rule(rules, seen_rules, target_rule)
        for edge in projection.edges:
            edge = dict(edge)
            edge["rule_id"] = target_rule_id if edge.get("target") == target else str(edge.get("rule_id") or target_rule_id)
            edge.setdefault("citation_refs", [citation_id])
            _add_edge(edges, seen_edges, edge)
            rule_id = str(edge.get("rule_id") or "")
            if rule_id not in seen_rules:
                operation = _operation_for_projection_rule(rule_id) or str(expression.get("op") or "").upper()
                _add_rule(
                    rules,
                    seen_rules,
                    {
                        "rule_id": rule_id,
                        "operation": operation,
                        "description": f"Candidate projection rule {rule_id}.",
                        "citation_refs": [citation_id],
                        **(
                            {"parameters": projection_parameters[rule_id]}
                            if rule_id in projection_parameters
                            else {}
                        ),
                    },
                )

    outline = {
        "document_id": document["document_id"],
        "year": year,
        "children": [
            {
                "outline_id": f"line_{row['line']}",
                "kind": "line",
                "line_anchor": row["line"],
                "label": row.get("label") or row["line"],
                "children": [],
            }
            for row in rows
        ],
    }
    metrics = {
        "candidate": True,
        "source_report": str(report_path),
        "coverage": document["coverage"],
        "findings": document["findings"],
        "llm_calls": report.get("llm_calls") or [],
        "provenance": "completed derivation report; no human confirmation",
    }
    _write_yaml(destination / "candidate.yaml", document)
    _write_yaml(destination / "rows.yaml", rows)
    _write_yaml(destination / "outline.yaml", outline)
    _write_yaml(destination / "micro_extraction.yaml", {"formula_cells": formula_cells})
    _write_yaml(destination / "nodes.yaml", nodes)
    _write_yaml(destination / "edges.yaml", edges)
    _write_yaml(destination / "rules.yaml", rules)
    _write_yaml(destination / "citations.yaml", citations)
    _write_yaml(destination / "candidate_spans.yaml", spans)
    _write_yaml(destination / "metrics.yaml", metrics)
    return document


def _document_candidate(
    report: Mapping[str, Any],
    *,
    report_path: Path,
    root: Path,
    year: str,
) -> dict[str, Any]:
    document_id = str(report.get("document_id") or "").strip()
    if not document_id:
        raise ValueError(f"{report_path}: derivation report has no document_id")
    if str(report.get("year") or year) != year:
        raise ValueError(f"{report_path}: report year does not match {year}")
    raw_rows = report.get("rows_detail") or []
    if not isinstance(raw_rows, list):
        raise ValueError(f"{report_path}: rows_detail must be a list")
    field_addresses = _field_map_addresses(root, year, document_id)
    source_rows = _source_cell_rows(root, year, document_id)
    rows = []
    for item in raw_rows:
        if not isinstance(item, Mapping):
            continue
        line = str(item.get("line") or "").strip().lower()
        rows.append(
            _candidate_row(
                document_id,
                _enrich_report_row(item, source_rows.get(line)),
                field_addresses,
            )
        )
    denominator = report.get("denominator") if isinstance(report.get("denominator"), Mapping) else {}
    status_counts = report.get("row_status_counts") if isinstance(report.get("row_status_counts"), Mapping) else {}
    validation = report.get("validation") if isinstance(report.get("validation"), Mapping) else {}
    skipped = _integer(status_counts.get("skipped"), _integer(denominator.get("skipped")))
    skipped_by_reason = denominator.get("skipped_by_reason") if isinstance(denominator.get("skipped_by_reason"), Mapping) else {}
    for item in denominator.get("anchors", []) if isinstance(denominator.get("anchors"), list) else []:
        if not isinstance(item, Mapping) or not item.get("skip_reason"):
            continue
        line = str(item.get("anchor") or "").strip().lower()
        if not line or any(str(row["line"]) == line for row in rows):
            continue
        source_row = source_rows.get(line)
        source_fields = _source_row_fields(source_row)
        source_available = bool(source_fields)
        rows.append(
            {
                "line": line,
                "label": str(
                    source_fields.get("label")
                    if source_available
                    else item.get("label") or ""
                ),
                "form_face_text": str(source_fields.get("form_face_text") or ""),
                "instruction_text": str(source_fields.get("instruction_text") or ""),
                "instruction_locator": str(source_fields.get("instruction_locator") or ""),
                "label_before": str(
                    source_fields.get("label_before")
                    if source_available
                    else item.get("label") or ""
                ),
                "source_findings": list(source_fields.get("source_findings") or []),
                "status": "skipped",
                "candidate_status": "skipped",
                "original_status": "skipped",
                "node_id": _line_node_id(document_id, line),
                "canonical_address": field_addresses.get(line),
                "expression": None,
                "rendered": None,
                "quote": "",
                "quote_span_id": "",
                "citation_refs": [],
                "findings": [
                    {
                        "kind": "skipped_anchor",
                        "message": str(item.get("skip_reason")),
                    }
                ],
                "review_gap": str(item.get("skip_reason")),
            }
        )
        rows[-1]["findings"].extend(_source_findings(source_fields.get("source_findings")))
    rows.sort(key=lambda item: _line_sort_key(str(item["line"])))
    findings = [finding for row in rows for finding in row.get("findings", [])]
    coverage = {
        "printed_anchors": _integer(report.get("line_anchor_count"), _integer(denominator.get("line_anchor_count"))),
        "selected": _integer(report.get("rows"), len(raw_rows)),
        "attempted": _integer(report.get("rows_attempted"), _integer(validation.get("attempted"))),
        "derived": _integer(status_counts.get("derived"), _integer(validation.get("derived"))),
        "repaired": _integer(status_counts.get("repaired"), _integer(validation.get("repaired"))),
        "gapped": _integer(status_counts.get("gapped"), _integer(validation.get("gapped"))),
        "errored": _integer(status_counts.get("errored"), _integer(validation.get("errored"))),
        "skipped": skipped,
        "skipped_by_reason": dict(sorted((str(key), _integer(value)) for key, value in skipped_by_reason.items())),
    }
    coverage["resolved"] = coverage["derived"] + coverage["repaired"]
    return {
        "document_id": document_id,
        "year": year,
        "source_report": str(report_path),
        "coverage": coverage,
        "rows": rows,
        "findings": findings,
    }


def _candidate_row(document_id: str, row: Mapping[str, Any], field_addresses: Mapping[str, str]) -> dict[str, Any]:
    line = str(row.get("line") or "").strip().lower()
    if not line:
        raise ValueError(f"{document_id}: derivation row has no printed line")
    expression = row.get("expression") if isinstance(row.get("expression"), Mapping) else None
    original_status = str(row.get("status") or "error")
    quote = str(row.get("quote") or "")
    quote_span_id = str(row.get("quote_span_id") or "")
    citation_refs = [quote_span_id] if quote_span_id else [str(value) for value in row.get("citation_refs", []) or [] if str(value)]
    if original_status == "skipped":
        candidate_status = "skipped"
    else:
        candidate_status = original_status if original_status in {"derived", "repaired"} else "review_gap"
    findings = [dict(item) for item in row.get("validation_failures", []) or [] if isinstance(item, Mapping)]
    findings.extend(_source_findings(row.get("source_findings")))
    warnings = [dict(item) for item in row.get("validation_warnings", []) or [] if isinstance(item, Mapping)]
    unresolved = [
        dict(item)
        for item in row.get("unresolved_external_nodes", []) or []
        if isinstance(item, Mapping)
    ]
    for item in unresolved:
        external_document = str(item.get("document_id") or "unknown document")
        external_line = str(item.get("line") or "unknown line")
        finding = {
            "kind": "unresolved_external_reference",
            "message": f"{external_document} line {external_line} is outside the document inventory",
            "document_id": external_document,
            "line": external_line,
        }
        if finding not in findings:
            findings.append(finding)
    review_gap = str(row.get("error") or "")
    if original_status == "skipped":
        review_gap = get_structural_skip_reason(row) or str(row.get("review_gap") or "")
        if review_gap:
            findings.append({"kind": "skipped_anchor", "message": review_gap})
    if candidate_status in {"derived", "repaired"} and (expression is None or not quote or not citation_refs):
        candidate_status = "review_gap"
        review_gap = "derived row lacks a verbatim citation and cannot enter the candidate graph"
        findings.append({"kind": "missing_verbatim_citation", "message": review_gap})
    if original_status in {"gapped", "errored", "error"} and not review_gap:
        review_gap = original_status
    if expression is not None and _missing_if_else_comparison(expression):
        candidate_status = "review_gap"
        review_gap = "IF_ELSE comparator is missing; candidate graph emission is blocked"
        findings.append({"kind": "missing_comparison", "message": review_gap})
    if original_status in {"gapped", "errored", "error"} and review_gap:
        findings.append(
            {
                "kind": "row_error" if original_status in {"errored", "error"} else "row_gap",
                "message": review_gap,
            }
        )
    return {
        "line": line,
        "label": str(row.get("label_after") or ""),
        "form_face_text": str(row.get("form_face_after") or row.get("form_face_before") or ""),
        "instruction_text": str(row.get("instruction_text") or ""),
        "status": original_status,
        "model_outcome": str(row.get("model_outcome") or ""),
        "candidate_status": candidate_status,
        "original_status": original_status,
        "node_id": _line_node_id(document_id, line),
        "canonical_address": field_addresses.get(line),
        "expression": dict(expression) if expression is not None else None,
        "rendered": row.get("rendered"),
        "quote": quote,
        "quote_span_id": quote_span_id,
        "citation_refs": citation_refs,
        "findings": findings,
        "warnings": warnings,
        "unresolved_external_nodes": unresolved,
        "review_gap": review_gap,
    }


def _source_cell_rows(root: Path, year: str, document_id: str) -> dict[str, Mapping[str, Any]]:
    """Read deterministic cell text for candidate rows without calling a provider."""
    try:
        from tax_graph.extract.cells import build_cell_frame_from_document
        from tax_graph.extract.inputs import load_document_input

        document = load_document_input(document_id, year=year, root=root)
        frame = build_cell_frame_from_document(document)
    except (FileNotFoundError, OSError, ValueError, ImportError):
        return {}

    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in frame.rows:
        grouped[str(row.line).strip().lower()].append(row.as_dict())
    result: dict[str, Mapping[str, Any]] = {}
    for line, candidates in grouped.items():
        result[line] = min(candidates, key=_source_row_priority)
    return result


def _source_row_priority(row: Mapping[str, Any]) -> tuple[int, int, str]:
    """Prefer the canonical admitted row when geometry repeats an anchor."""
    metadata = row.get("metadata") if isinstance(row.get("metadata"), Mapping) else row
    structural_reason = get_structural_skip_reason(metadata)
    admitted = 1 if structural_reason else 0
    header = 1 if structural_reason == "structure_header_anchor" else 0
    return admitted, header, str(metadata.get("outline_id") or "")


def _source_row_fields(row: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        return {}
    metadata = row.get("metadata") if isinstance(row.get("metadata"), Mapping) else row
    return {
        "label": row.get("label") or "",
        "form_face_text": row.get("form_face_text") or "",
        "instruction_text": row.get("instruction_text") or "",
        "instruction_locator": row.get("instruction_locator") or "",
        "label_before": metadata.get("label_before") or "",
        "source_findings": metadata.get("evidence_findings") or [],
    }


def _enrich_report_row(row: Mapping[str, Any], source_row: Mapping[str, Any] | None) -> dict[str, Any]:
    """Overlay deterministic text while retaining provider result fields."""
    enriched = dict(row)
    fields = _source_row_fields(source_row)
    if not fields:
        return enriched
    enriched["label_after"] = fields["label"]
    enriched["form_face_after"] = fields["form_face_text"]
    enriched["instruction_text"] = fields["instruction_text"]
    enriched["instruction_locator"] = fields["instruction_locator"]
    enriched.setdefault("label_before", fields["label_before"])
    enriched["source_findings"] = fields["source_findings"]
    return enriched


def _source_findings(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [
        {
            "kind": str(item.get("code") or "source_evidence_finding"),
            "message": str(item.get("detail") or item.get("code") or "source evidence finding"),
        }
        for item in value
        if isinstance(item, Mapping)
    ]


def _node_label(row: Mapping[str, Any], line: str) -> str:
    """Build a graph label from the cleaned form-face text only."""
    text = " ".join(str(row.get("form_face_text") or "").split())
    if not text:
        text = " ".join(str(row.get("label") or "").split())
    return f"Line {line}: {text}" if text else f"Line {line}"


def _handcrafted_diff(root: Path, year: str, documents: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Compare resolved candidate target nodes with the published graph."""
    try:
        graph = load_graph(year, root, include_extensions=False)
    except (FileNotFoundError, OSError, ValueError):
        return {
            "status": "handcrafted_graph_unavailable",
            "candidate_only": [],
            "handcrafted_only": [],
            "in_both": [],
            "expression_disagreements": [],
        }
    nodes = {str(item.get("node_id")): item for item in graph.items("nodes") if item.get("node_id")}
    edges_by_target: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in graph.items("edges"):
        target = str(edge.get("target") or "")
        if target:
            edges_by_target[target].append(edge)
    rules = {str(item.get("rule_id")): item for item in graph.items("rules") if item.get("rule_id")}

    candidate_addresses: set[str] = set()
    candidate_expressions: dict[str, Any] = {}
    for document in documents:
        for row in document.get("rows", []) or []:
            if not isinstance(row, Mapping) or row.get("candidate_status") not in {"derived", "repaired"}:
                continue
            address = str(row.get("node_id") or "")
            expression = row.get("expression")
            if not address or not isinstance(expression, Mapping):
                continue
            candidate_addresses.add(address)
            candidate_expressions[address] = _normalize_candidate_expression(expression, str(document["document_id"]))
    handcrafted_addresses = set(nodes)
    in_both = sorted(candidate_addresses & handcrafted_addresses)
    candidate_only = sorted(candidate_addresses - handcrafted_addresses)
    handcrafted_only = sorted(handcrafted_addresses - candidate_addresses)
    disagreements: list[dict[str, Any]] = []
    for address in in_both:
        live_expression = _live_expression(address, nodes, edges_by_target, rules, set())
        if _json_key(candidate_expressions.get(address)) != _json_key(live_expression):
            disagreements.append(
                {
                    "address": address,
                    "candidate": candidate_expressions.get(address),
                    "handcrafted": live_expression,
                }
            )
    return {
        "status": "compared",
        "candidate_only": candidate_only,
        "handcrafted_only": handcrafted_only,
        "in_both": in_both,
        "expression_disagreements": disagreements,
    }


def _live_expression(
    node_id: str,
    nodes: Mapping[str, Mapping[str, Any]],
    edges_by_target: Mapping[str, Sequence[Mapping[str, Any]]],
    rules: Mapping[str, Mapping[str, Any]],
    seen: set[str],
) -> dict[str, Any] | None:
    if node_id in seen:
        return {"node": node_id}
    edges = list(edges_by_target.get(node_id, ()))
    if not edges:
        node = nodes.get(node_id) or {}
        if "constant_value" in node:
            return {"const": node["constant_value"]}
        return {"node": node_id}
    rule = rules.get(str(edges[0].get("rule_id") or "")) or {}
    operation = str(rule.get("operation") or "").upper()
    if not operation:
        return {"node": node_id}
    ordered = sorted(edges, key=lambda edge: _role_sort_key(str(edge.get("role") or "")))
    next_seen = set(seen)
    next_seen.add(node_id)
    args = []
    for edge in ordered:
        source = str(edge.get("source") or "")
        source_node = nodes.get(source) or {}
        if source in edges_by_target:
            value = _live_expression(source, nodes, edges_by_target, rules, next_seen)
        elif "constant_value" in source_node:
            value = {"const": source_node["constant_value"]}
        else:
            value = {"node": source}
        args.append(value)
    expression = {"op": operation, "args": args}
    if operation == "IF_ELSE":
        parameters = rule.get("parameters")
        comparison = parameters.get("comparison") if isinstance(parameters, Mapping) else None
        if isinstance(comparison, str) and comparison:
            expression["comparison"] = comparison
    return expression


def _normalize_candidate_expression(value: Mapping[str, Any], document_id: str) -> dict[str, Any]:
    if "op" not in value:
        if "form" in value and "line" in value:
            return {"node": _line_node_id(str(value["form"]), str(value["line"]))}
        if "line" in value:
            return {"node": _line_node_id(document_id, str(value["line"]))}
        if "const" in value:
            return {"const": value["const"]}
        if "node" in value:
            return {"node": str(value["node"])}
        return {"node": "unresolved"}
    normalized = {
        "op": str(value.get("op") or "").upper(),
        "args": [
            _normalize_candidate_expression(item, document_id)
            if isinstance(item, Mapping)
            else {"node": "unresolved"}
            for item in value.get("args", []) or []
        ],
    }
    if normalized["op"] == "IF_ELSE" and isinstance(value.get("comparison"), str):
        normalized["comparison"] = value["comparison"]
    return normalized


def _expression_leaf_nodes(
    expression: Mapping[str, Any],
    document_id: str,
    *,
    control_roles: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for node in _walk_expression(expression):
        if "op" in node:
            continue
        if "line" in node and "form" not in node:
            node_id = _line_node_id(document_id, str(node["line"]))
            doc = document_id
        elif "form" in node and "line" in node:
            doc = str(node["form"])
            if _slug(doc) != _slug(document_id):
                continue
            node_id = _line_node_id(doc, str(node["line"]))
        elif "node" in node:
            node_id = str(node["node"])
            doc = node_id.split("_root_line_", 1)[0]
        elif "const" in node:
            continue
        else:
            continue
        if node_id in seen:
            continue
        seen.add(node_id)
        item = {
            "node_id": node_id,
            "document_id": doc,
            "label": f"Source {node_id}",
            "node_type": "form_line" if "line" in node else "fact",
            "value_type": "currency",
            "required": "optional",
        }
        line = str(node.get("line") or "").strip().lower()
        role = (control_roles or {}).get(line) if doc == document_id else None
        if role:
            item["control_role"] = role
        result.append(item)
    return result


def _field_control_roles(root: Path, year: str, document_id: str) -> dict[str, str]:
    """Return unambiguous control roles keyed by printed line."""
    path = root / "graph" / year / "addresses" / f"{document_id}.yaml"
    if not path.is_file():
        return {}
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}
    roles: dict[str, set[str]] = defaultdict(set)
    for item in payload.get("addresses", []) if isinstance(payload, Mapping) else []:
        if not isinstance(item, Mapping):
            continue
        role = str(item.get("control_role") or "").strip().lower()
        official_ref = str(item.get("official_ref") or "").strip().lower()
        if role and role != "none" and official_ref:
            roles[official_ref].add(role)
    return {
        line: next(iter(values))
        for line, values in roles.items()
        if len(values) == 1
    }


def _walk_expression(value: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    yield value
    for item in value.get("args", []) or []:
        if isinstance(item, Mapping) and "op" in item:
            yield from _walk_expression(item)
        elif isinstance(item, Mapping):
            yield item


def _missing_if_else_comparison(expression: Mapping[str, Any]) -> bool:
    """Return whether any conditional node lacks its required comparator."""
    return any(
        str(node.get("op") or "").upper() == "IF_ELSE"
        and (
            not isinstance(node.get("comparison"), str)
            or not str(node.get("comparison") or "").strip()
        )
        for node in _walk_expression(expression)
    )


def _copy_worksheet_drafts(root: Path, *, year: str, destination: Path) -> dict[str, Any]:
    try:
        manifest = load_manifest(root=root)
    except FileNotFoundError:
        return {"required": [], "copied": [], "missing": []}
    copied: list[str] = []
    missing: list[dict[str, str]] = []
    for entry in manifest.documents:
        if not entry.is_region:
            continue
        source = root / "graph" / year / "_drafts" / entry.document_id
        target = destination / entry.document_id
        try:
            if not source.is_dir():
                missing.append({"document_id": entry.document_id, "reason": "worksheet draft is missing"})
                continue
            shutil.copytree(source, target)
            copied.append(entry.document_id)
        except OSError as exc:
            missing.append(
                {
                    "document_id": entry.document_id,
                    "reason": f"{type(exc).__name__}: {exc}",
                }
            )
    return {
        "required": sorted(entry.document_id for entry in manifest.documents if entry.is_region),
        "copied": sorted(copied),
        "missing": sorted(missing, key=lambda item: item["document_id"]),
    }


def _stub_registry(
    documents: Sequence[Mapping[str, Any]],
    *,
    year: str,
    real_document_ids: set[str],
) -> dict[str, Any]:
    """Collect source-backed external references into deterministic stubs.

    A stub is candidate output, never a live-graph write.  The canonical line
    id is checked here because it is the join between an unresolved reference
    and the later real ingestion of that document.
    """
    records: dict[str, dict[str, Any]] = {}
    for document in documents:
        for row in document.get("rows", []) or []:
            if not isinstance(row, Mapping):
                continue
            for raw in row.get("unresolved_external_nodes", []) or []:
                if not isinstance(raw, Mapping):
                    continue
                document_id = str(raw.get("document_id") or "").strip().lower()
                line = str(raw.get("line") or "").strip().lower()
                if not document_id or not line:
                    continue
                if document_id.startswith("instructions_"):
                    raise ValueError(
                        f"instructions document {document_id} cannot be emitted as a stub"
                    )
                node_id = _line_node_id(document_id, line)
                supplied_id = str(raw.get("node_id") or "").strip()
                if supplied_id and supplied_id != node_id:
                    raise ValueError(
                        f"external stub id {supplied_id} does not match canonical id {node_id}"
                    )
                node = dict(raw)
                node["node_id"] = node_id
                node["document_id"] = document_id
                node["line"] = line
                node.setdefault("status", "unresolved")
                node.setdefault(
                    "stub_message",
                    _stub_line_message(document_id, line),
                )
                records.setdefault(node_id, node)

    by_document: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in records.values():
        by_document[str(node["document_id"])].append(node)

    lifecycle: list[dict[str, Any]] = []
    document_stubs: list[dict[str, Any]] = []
    for document_id in sorted(by_document):
        lines = sorted(
            {str(item["line"]) for item in by_document[document_id]},
            key=_line_sort_key,
        )
        status = "ingested" if document_id in real_document_ids else "unresolved"
        lifecycle.extend(
            {
                "document_id": document_id,
                "line": line,
                "node_id": _line_node_id(document_id, line),
                "status": status,
                "message": (
                    "canonical node is supplied by the inducted document"
                    if status == "ingested"
                    else _stub_line_message(document_id, line)
                ),
            }
            for line in lines
        )
        if status == "unresolved":
            document_stubs.append(_stub_document(document_id, year, lines))

    return {
        "document_ids": [item["document_id"] for item in document_stubs],
        "documents": document_stubs,
        "nodes": {
            document_id: sorted(items, key=lambda item: _line_sort_key(str(item["line"])))
            for document_id, items in sorted(by_document.items())
            if document_id not in real_document_ids
        },
        "lifecycle": lifecycle,
    }


def _stub_document(document_id: str, year: str, lines: Sequence[str]) -> dict[str, Any]:
    title = _stub_title(document_id)
    line_text = ", ".join(f"line {line}" for line in lines)
    return {
        "document_id": document_id,
        "title": title,
        "tax_year": int(year),
        "document_type": "schedule" if document_id.startswith("schedule_") else "tax_form",
        "document_class": "return",
        "status": "unresolved",
        "stub_message": (
            f"{title} must be ingested or the caller must supply {line_text} "
            "before this value can be computed."
        ),
    }


def _stub_title(document_id: str) -> str:
    stem = re.sub(r"_[0-9]{4}$", "", str(document_id).strip().lower())
    words = stem.replace("_", " ").split()
    return " ".join(word.upper() if word.isdigit() else word.title() for word in words)


def _stub_line_message(document_id: str, line: str) -> str:
    return (
        f"{_stub_title(document_id)}, line {line} must be ingested or supplied "
        "by the caller before this value can be computed."
    )


def _write_stub_documents(registry: Mapping[str, Any], *, destination: Path) -> None:
    """Write document and line stubs into the candidate graph workspace."""
    documents = registry.get("documents", [])
    nodes_by_document = registry.get("nodes", {})
    for document in documents:
        document_id = str(document["document_id"])
        target = destination / document_id
        if target.exists():
            raise ValueError(f"stub document output already exists: {target}")
        target.mkdir(parents=True)
        _write_yaml(target / "documents.yaml", [document])
        _write_yaml(target / "nodes.yaml", nodes_by_document.get(document_id, []))
        _write_yaml(target / "edges.yaml", [])
        _write_yaml(target / "rules.yaml", [])
        _write_yaml(target / "citations.yaml", [])
        _write_yaml(
            target / "metrics.yaml",
            {
                "candidate": True,
                "stub": True,
                "provenance": "source-backed external reference; no human confirmation",
                "stub_message": document["stub_message"],
            },
        )


def _assert_candidate_operand_resolution(graph_root: Path) -> dict[str, Any]:
    """Assert that every candidate edge endpoint is a real or stub node."""
    node_ids: set[str] = set()
    duplicate_node_ids: set[str] = set()
    edge_count = 0
    operand_ids: set[str] = set()
    for path in graph_root.rglob("nodes.yaml"):
        payload = yaml.safe_load(path.read_text(encoding="ascii")) or []
        for item in payload if isinstance(payload, list) else [payload]:
            if not isinstance(item, Mapping):
                continue
            node_id = str(item.get("node_id") or "").strip()
            if not node_id:
                continue
            if node_id in node_ids:
                duplicate_node_ids.add(node_id)
            node_ids.add(node_id)
    missing: set[str] = set()
    for path in graph_root.rglob("edges.yaml"):
        payload = yaml.safe_load(path.read_text(encoding="ascii")) or []
        for item in payload if isinstance(payload, list) else [payload]:
            if not isinstance(item, Mapping):
                continue
            edge_count += 1
            for key in ("source", "target"):
                node_id = str(item.get(key) or "").strip()
                if not node_id:
                    continue
                operand_ids.add(node_id)
                if node_id not in node_ids:
                    missing.add(node_id)
    if duplicate_node_ids:
        raise ValueError(
            "candidate graph contains duplicate node ids: "
            + ", ".join(sorted(duplicate_node_ids))
        )
    if missing:
        raise ValueError(
            "candidate graph contains unresolved operand node ids: "
            + ", ".join(sorted(missing))
        )
    return {
        "status": "ok",
        "node_count": len(node_ids),
        "edge_count": edge_count,
        "operand_count": len(operand_ids),
        "dangling_node_ids": [],
    }


def _manifest_documents(root: Path, year: str | int) -> list[str]:
    manifest = load_manifest(root=root)
    if str(manifest.tax_year) != str(year):
        raise ValueError(f"manifest tax_year {manifest.tax_year} does not match requested year {year}")
    return [entry.document_id for entry in manifest.documents if not entry.is_region]


def _load_reports(source: Path, *, year: str) -> list[tuple[str, Path, dict[str, Any]]]:
    reports: list[tuple[str, Path, dict[str, Any]]] = []
    for path in sorted(source.glob(f"*{DERIVATION_REPORT_SUFFIX}")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"{path}: derivation report must be an object")
        document_id = str(payload.get("document_id") or "").strip()
        if not document_id:
            raise ValueError(f"{path}: derivation report has no document_id")
        if str(payload.get("year") or year) != year:
            raise ValueError(f"{path}: report year does not match {year}")
        reports.append((document_id, path, payload))
    if not reports:
        raise ValueError(f"run directory has no {DERIVATION_REPORT_SUFFIX} files: {source}")
    ids = [item[0] for item in reports]
    if len(ids) != len(set(ids)):
        raise ValueError(f"run directory contains duplicate document reports: {source}")
    return reports


def _coverage_total(documents: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    metrics = ("printed_anchors", "selected", "attempted", "derived", "repaired", "gapped", "errored", "skipped", "resolved")
    total = {metric: sum(_integer((item.get("coverage") or {}).get(metric)) for item in documents) for metric in metrics}
    skipped: dict[str, int] = defaultdict(int)
    for document in documents:
        for key, value in ((document.get("coverage") or {}).get("skipped_by_reason", {}) or {}).items():
            skipped[str(key)] += _integer(value)
    total["skipped_by_reason"] = dict(sorted(skipped.items()))
    total["documents"] = len(documents)
    return total


def _field_map_addresses(root: Path, year: str, document_id: str) -> dict[str, str]:
    path = root / "graph" / year / "field_maps" / f"{document_id}.yaml"
    if not path.is_file():
        return {}
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}
    result: dict[str, str] = {}
    for item in payload.get("mappings", []) if isinstance(payload, dict) else []:
        if not isinstance(item, Mapping) or not item.get("address_id"):
            continue
        match = re.search(r"/line=([0-9]+[a-z]?)(?:/|$)", str(item["address_id"]), re.IGNORECASE)
        if match:
            result.setdefault(match.group(1).lower(), str(item["address_id"]))
    return result


def _operation_for_projection_rule(rule_id: str) -> str | None:
    if rule_id in {"if_less_than_currency", "if_greater_than_currency"}:
        return "IF_ELSE"
    if re.fullmatch(r"if_(?:gt|ge|lt|le|eq)_currency", rule_id):
        return "IF_ELSE"
    for spec in OPERATION_SPECS:
        if spec.projection_rule == rule_id:
            return spec.name
    return None


def _rule_parameters(expression: Mapping[str, Any]) -> dict[str, Any]:
    """Return operation parameters that are part of the expression contract."""
    if str(expression.get("op") or "").upper() != "IF_ELSE":
        return {}
    comparison = expression.get("comparison")
    return {"comparison": comparison} if isinstance(comparison, str) and comparison else {}


def _projection_rule_parameters(expression: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    """Attach each nested IF_ELSE rule to its explicit comparison direction."""
    result: dict[str, dict[str, str]] = {}
    for node in _walk_expression(expression):
        if str(node.get("op") or "").upper() != "IF_ELSE":
            continue
        comparison = node.get("comparison")
        if not isinstance(comparison, str) or not comparison:
            continue
        rule_id = projection_rule_for("IF_ELSE", comparison=comparison)
        if rule_id:
            result[rule_id] = {"comparison": comparison}
    return result


def _add_node(items: list[dict[str, Any]], seen: set[str], item: Mapping[str, Any]) -> None:
    node_id = str(item.get("node_id") or "")
    if not node_id or node_id in seen:
        return
    seen.add(node_id)
    items.append(dict(item))


def _add_edge(items: list[dict[str, Any]], seen: set[str], item: Mapping[str, Any]) -> None:
    edge_id = str(item.get("edge_id") or "")
    if not edge_id or edge_id in seen:
        return
    seen.add(edge_id)
    items.append(dict(item))


def _add_rule(items: list[dict[str, Any]], seen: set[str], item: Mapping[str, Any]) -> None:
    rule_id = str(item.get("rule_id") or "")
    if not rule_id or rule_id in seen:
        return
    seen.add(rule_id)
    items.append(dict(item))


def _line_node_id(document_id: str, line: str) -> str:
    return f"{_slug(document_id)}_root_line_{_slug(line)}"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_") or "item"


def _line_sort_key(value: str) -> tuple[int, str, int, str]:
    match = re.fullmatch(r"([0-9]+)([a-z]?)", str(value).strip().lower())
    if not match:
        return (1, str(value), 0, str(value))
    return (0, "", int(match.group(1)), match.group(2))


def _role_sort_key(role: str) -> tuple[int, str]:
    return ({"condition": 0, "threshold": 1, "minuend": 0, "numerator": 0, "source": 0, "addend": 0}.get(role, 10), role)


def _json_key(value: Any) -> str:
    import json

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _integer(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _write_yaml(path: Path, value: Any) -> None:
    text = yaml.safe_dump(value, sort_keys=False, allow_unicode=False)
    text.encode("ascii")
    path.write_text(text, encoding="ascii", newline="\n")


def _require_directory(path: Path, label: str) -> None:
    if not path.is_dir():
        raise ValueError(f"{label} does not exist: {path}")


def _require_new_external_directory(path: Path, root: Path) -> None:
    try:
        path.relative_to(root)
    except ValueError:
        pass
    else:
        raise ValueError(f"candidate output must be outside repository root: {path}")
    if path.exists():
        raise ValueError(f"candidate output already exists: {path}")


__all__ = [
    "CANDIDATE_SCHEMA_VERSION",
    "build_candidate_from_run",
    "candidate_graph_root",
    "write_candidate_from_run",
]
