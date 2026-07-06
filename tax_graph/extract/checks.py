"""Deterministic cross-checks for extracted drafts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import jsonschema

from tax_graph.acquire.citation_check import check_citation_integrity
from tax_graph.extract.models import (
    CheckIssue,
    DeterministicReport,
    DraftObject,
    ExtractionBatch,
    SourceDocumentInput,
)
from tax_graph.extract.prompts import graph_object_schemas
from tax_graph.verify import check_field_grid_completeness


LINE_RE = re.compile(r"^-\s+([0-9]+[a-z]?|[a-z]):", re.MULTILINE)
FIELD_LINE_RE = re.compile(r"(?:^|[^a-z0-9])line([1-9][0-9]*[a-z]?)(?:_|[^a-z0-9]|$)")
FIELD_FORM_LINE_RE = re.compile(r"(?:^|[^a-z0-9])f([1-9][0-9]*[a-z]?)(?=$|[^a-z0-9_]|_[a-z])")


def run_deterministic_checks(
    document: SourceDocumentInput,
    batch: ExtractionBatch,
    *,
    root: str | Path | None = None,
) -> DeterministicReport:
    """Run schema, line, field-grid, and quote checks and flag draft objects."""
    issues: list[CheckIssue] = []
    issues.extend(_schema_issues(batch, root=root))
    issues.extend(_rule_citation_issues(batch))
    issues.extend(_line_completeness_issues(document, batch))
    issues.extend(_field_grid_issues(document, batch))
    issues.extend(_citation_quote_issues(document, batch))
    _apply_issues(batch, issues)
    return DeterministicReport(issues=issues)


def _schema_issues(batch: ExtractionBatch, *, root: str | Path | None) -> list[CheckIssue]:
    schemas = graph_object_schemas(root=root)
    issues: list[CheckIssue] = []
    for obj in batch.objects:
        try:
            jsonschema.validate(obj.data, schemas[obj.kind])
        except jsonschema.ValidationError as exc:
            issues.append(CheckIssue(obj.kind, obj.object_id, f"schema: {exc.message}"))
    return issues


def _rule_citation_issues(batch: ExtractionBatch) -> list[CheckIssue]:
    issues: list[CheckIssue] = []
    for rule in batch.items("rules"):
        if not rule.data.get("citation_refs"):
            issues.append(CheckIssue("rules", rule.object_id, "rule has no citation_refs"))
    return issues


def _line_completeness_issues(document: SourceDocumentInput, batch: ExtractionBatch) -> list[CheckIssue]:
    anchors = _true_line_anchors(document)
    if not anchors:
        return []

    nodes = [obj for obj in batch.items("nodes") if obj.data.get("document_id") == document.document_id]
    issues: list[CheckIssue] = []
    for anchor in anchors:
        matching = [node for node in nodes if _node_mentions_line(node, anchor)]
        if not matching:
            issues.append(CheckIssue("document", document.document_id, f"line {anchor} has no node"))
    return issues


def _field_grid_issues(document: SourceDocumentInput, batch: ExtractionBatch) -> list[CheckIssue]:
    if not document.fields:
        return []
    report = check_field_grid_completeness(
        document_id=document.document_id,
        fields=document.fields,
        nodes=[obj.data for obj in batch.items("nodes")],
        tables=[obj.data for obj in batch.items("tables")],
        not_modeled_fields=document.not_modeled_fields,
    )
    return [
        CheckIssue("document", document.document_id, f"field {issue.field_name}: {issue.reason}")
        for issue in report.issues
    ]


def _citation_quote_issues(document: SourceDocumentInput, batch: ExtractionBatch) -> list[CheckIssue]:
    citations = [obj.data for obj in batch.items("citations")]
    if not citations:
        return []
    report = check_citation_integrity(citations, text_dir=document.text_path.parent)
    return [
        CheckIssue("citations", mismatch.citation_id, f"citation quote: {mismatch.reason}")
        for mismatch in report.mismatches
    ]


def _apply_issues(batch: ExtractionBatch, issues: list[CheckIssue]) -> None:
    by_identity = batch.by_identity()
    for issue in issues:
        obj = by_identity.get((issue.kind, issue.object_id))
        if obj:
            obj.flag(issue.reason)
    if any(issue.kind == "document" for issue in issues):
        for obj in batch.objects:
            obj.flag("document-level deterministic check failed")


def _raw_line_anchors(text: str) -> list[str]:
    seen: list[str] = []
    for match in LINE_RE.finditer(text):
        anchor = match.group(1).lower()
        if anchor not in seen:
            seen.append(anchor)
    return seen


def _true_line_anchors(document: SourceDocumentInput) -> list[str]:
    anchors = []
    field_anchors = _field_anchors(document)
    related_text = "\n".join(source.text.lower() for source in document.related_sources)
    for anchor in _raw_line_anchors(document.text):
        if anchor in field_anchors or _instruction_mentions_anchor(related_text, anchor):
            anchors.append(anchor)
    return anchors


def _field_anchors(document: SourceDocumentInput) -> set[str]:
    anchors: set[str] = set()
    if not document.fields:
        return anchors
    for field in document.fields.get("fields", []):
        anchor = str(field.get("line_anchor", "")).lower()
        if anchor:
            anchors.add(anchor)
    return anchors


def _instruction_mentions_anchor(text: str, anchor: str) -> bool:
    if not text:
        return False
    escaped = re.escape(anchor)
    return bool(re.search(rf"\bline\s+{escaped}\b", text))


def _node_mentions_line(node: DraftObject, anchor: str) -> bool:
    normalized = _normalize_anchor(anchor)
    haystacks = [
        str(node.data.get("node_id", "")).lower(),
        str(node.data.get("label", "")).lower(),
        str(node.data.get("description", "")).lower(),
    ]
    return any(f"line_{normalized}" in value or f"line {anchor}" in value for value in haystacks)


def _normalize_anchor(anchor: str) -> str:
    return anchor.lower().replace("-", "_")


def _field_anchor(field_name: str) -> str | None:
    field_name = field_name.lower()
    if "table_line" in field_name:
        return None
    match = FIELD_LINE_RE.search(field_name)
    if match:
        return match.group(1).lower()
    match = FIELD_FORM_LINE_RE.search(field_name)
    return match.group(1).lower() if match else None
