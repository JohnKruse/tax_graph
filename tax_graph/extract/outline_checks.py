"""Deterministic checks for outline-first extraction artifacts."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re

from tax_graph.extract.models import SourceDocumentInput
from tax_graph.extract.outline import (
    CandidateSpan,
    OutboundFlow,
    OutlineNode,
    OutlineTree,
    _canonical_line_anchor,
)


LINE_RE = re.compile(r"^-\s+([0-9]+[a-z]?|[a-z]):", re.MULTILINE | re.IGNORECASE)
PART_RE = re.compile(r"Header:\s+Part\s+([ivxlcdm]+)", re.IGNORECASE)


class OutlineArtifactError(ValueError):
    """Raised when outline-first artifacts fail deterministic checks."""


@dataclass(frozen=True)
class OutlineIssue:
    """One deterministic outline artifact issue."""

    artifact: str
    reason: str


@dataclass(frozen=True)
class OutlineReport:
    """Deterministic report for outline-first intermediate artifacts."""

    issues: list[OutlineIssue]

    @property
    def ok(self) -> bool:
        return not self.issues

    def raise_for_issues(self) -> None:
        if self.issues:
            details = "; ".join(f"{issue.artifact}: {issue.reason}" for issue in self.issues)
            raise OutlineArtifactError(details)


def run_outline_artifact_checks(
    document: SourceDocumentInput,
    outline: OutlineTree,
    spans: list[CandidateSpan],
    flows: list[OutboundFlow],
) -> OutlineReport:
    """Check outline, evidence, and outbound-flow intermediate artifacts."""
    issues: list[OutlineIssue] = []
    issues.extend(_outline_empty_issues(document, outline))
    issues.extend(_outline_completeness_issues(document, outline))
    issues.extend(_candidate_span_issues(spans))
    issues.extend(_outbound_flow_issues(outline, spans, flows))
    return OutlineReport(issues=issues)


def _outline_empty_issues(document: SourceDocumentInput, outline: OutlineTree) -> list[OutlineIssue]:
    """A document with real text must not produce an empty outline.

    This is the fail-closed boundary for structure. A zero-node outline previously
    coexisted with a successful exit, so extraction reported success while producing
    nothing - the M20-S3a failure. Per-anchor gaps are coverage findings; a document
    that yields no structure at all is an error.
    """
    if _flatten_nodes(outline.children):
        return []
    if len(document.text.strip().splitlines()) < 5:
        return []
    return [
        OutlineIssue(
            artifact="outline_empty",
            reason=(
                f"{document.document_id}: outline produced zero nodes from "
                f"{len(document.text.splitlines())} lines of source text"
            ),
        )
    ]


def _outline_completeness_issues(document: SourceDocumentInput, outline: OutlineTree) -> list[OutlineIssue]:
    issues: list[OutlineIssue] = []
    rendered_lines: Counter[str] = Counter()
    for raw_line in document.text.splitlines():
        match = re.match(r"^-\s+([0-9]+[a-z]?|[a-z]):\s*(.*)$", raw_line, re.IGNORECASE)
        if match:
            rendered_lines[_canonical_line_anchor(match.group(1).lower(), match.group(2))] += 1
    outline_lines = Counter(
        node.line_anchor.lower()
        for node in _flatten_nodes(outline.children)
        if node.line_anchor
    )
    for anchor, count in rendered_lines.items():
        if outline_lines[anchor] < count:
            issues.append(
                OutlineIssue(
                    "outline",
                    f"line {anchor} count {outline_lines[anchor]} below rendered count {count}",
                )
            )

    rendered_parts = {_part_id(match.group(1)) for match in PART_RE.finditer(document.text)}
    outline_parts = {node.outline_id for node in outline.children if node.kind == "section"}
    for part_id in sorted(rendered_parts - outline_parts):
        issues.append(OutlineIssue("outline", f"missing section {part_id}"))
    return issues


def _candidate_span_issues(spans: list[CandidateSpan]) -> list[OutlineIssue]:
    issues: list[OutlineIssue] = []
    ids = [span.span_id for span in spans]
    for span_id, count in Counter(ids).items():
        if count > 1:
            issues.append(OutlineIssue("candidate_spans", f"duplicate span id {span_id}"))
    for span in spans:
        if not span.text.strip():
            issues.append(OutlineIssue("candidate_spans", f"empty text for {span.span_id}"))
        if not span.locator.strip():
            issues.append(OutlineIssue("candidate_spans", f"empty locator for {span.span_id}"))
    return issues


def _outbound_flow_issues(
    outline: OutlineTree,
    spans: list[CandidateSpan],
    flows: list[OutboundFlow],
) -> list[OutlineIssue]:
    issues: list[OutlineIssue] = []
    outline_ids = {node.outline_id for node in _flatten_nodes(outline.children)}
    span_ids = {span.span_id for span in spans}
    flow_ids = [flow.flow_id for flow in flows]
    for flow_id, count in Counter(flow_ids).items():
        if count > 1:
            issues.append(OutlineIssue("outbound_flows", f"duplicate flow id {flow_id}"))
    for flow in flows:
        if flow.source_outline_id not in outline_ids:
            issues.append(OutlineIssue("outbound_flows", f"{flow.flow_id} source outline missing"))
        for span_id in flow.citation_span_ids:
            if span_id not in span_ids:
                issues.append(OutlineIssue("outbound_flows", f"{flow.flow_id} unknown span {span_id}"))
        if not flow.target_document_id or not flow.target_line:
            issues.append(OutlineIssue("outbound_flows", f"{flow.flow_id} missing target"))
    return issues


def _flatten_nodes(nodes: list[OutlineNode]) -> list[OutlineNode]:
    flattened: list[OutlineNode] = []
    for node in nodes:
        flattened.append(node)
        flattened.extend(_flatten_nodes(node.children))
    return flattened


def _part_id(roman: str) -> str:
    return f"part_{roman.lower()}"
