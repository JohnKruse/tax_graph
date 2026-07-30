"""Shared models for extraction drafts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DRAFT_KINDS = ("nodes", "edges", "rules", "citations", "decisions", "tables")
ID_FIELDS = {
    "documents": "document_id",
    "nodes": "node_id",
    "edges": "edge_id",
    "rules": "rule_id",
    "citations": "citation_id",
    "decisions": "decision_id",
    "tables": "table_id",
}


@dataclass(frozen=True)
class RelatedSourceInput:
    """Additional source text bundled into extraction context."""

    document_id: str
    kind: str
    text: str
    text_path: Path
    links: list[dict[str, Any]] = field(default_factory=list)
    links_path: Path | None = None
    relationship: str = "related"


@dataclass(frozen=True)
class SourceDocumentInput:
    """Rendered source artifacts for one manifest document."""

    document_id: str
    kind: str
    year: str
    url: str
    text: str
    text_path: Path
    fields: dict[str, Any] | None = None
    fields_path: Path | None = None
    pages_dir: Path | None = None
    links: list[dict[str, Any]] = field(default_factory=list)
    links_path: Path | None = None
    related_sources: list[RelatedSourceInput] = field(default_factory=list)
    not_modeled_fields: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class DraftObject:
    """One schema-pure graph object plus extraction metadata."""

    kind: str
    data: dict[str, Any]
    source_span: str
    extracted_by: str
    confidence: float
    critic_agrees: bool = True
    flags: list[str] = field(default_factory=list)
    tier: str | None = None
    requested_model: str | None = None
    resolved_model: str | None = None

    @property
    def object_id(self) -> str:
        """Return the object's schema id."""
        return str(self.data.get(ID_FIELDS[self.kind], ""))

    def flag(self, reason: str) -> None:
        """Attach a human-review reason once."""
        if reason not in self.flags:
            self.flags.append(reason)


@dataclass
class ExtractionBatch:
    """Draft graph objects extracted from one source document."""

    document_id: str
    year: str
    objects: list[DraftObject]
    llm_calls: list["LlmCallTelemetry"] = field(default_factory=list)

    def items(self, kind: str) -> list[DraftObject]:
        """Return draft objects for a graph kind."""
        return [obj for obj in self.objects if obj.kind == kind]

    def by_identity(self) -> dict[tuple[str, str], DraftObject]:
        """Index draft objects by kind and object id."""
        return {(obj.kind, obj.object_id): obj for obj in self.objects}


@dataclass(frozen=True)
class LlmCallTelemetry:
    """Resolved model, usage, and outcome returned for one live model call."""

    provider: str
    requested_model: str
    resolved_model: str | None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost: float | None = None
    finish_reason: str | None = None
    latency_ms: float | None = None
    outcome: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return the ASCII-safe serialized call record."""
        return {
            "provider": self.provider,
            "requested_model": self.requested_model,
            "resolved_model": self.resolved_model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost": self.cost,
            "finish_reason": self.finish_reason,
            "latency_ms": self.latency_ms,
            "outcome": self.outcome,
        }


@dataclass(frozen=True)
class CheckIssue:
    """A deterministic extraction check issue."""

    kind: str
    object_id: str
    reason: str


@dataclass(frozen=True)
class DeterministicReport:
    """Result of deterministic extraction checks."""

    issues: list[CheckIssue]

    @property
    def ok(self) -> bool:
        """Whether no deterministic checks failed."""
        return not self.issues


@dataclass(frozen=True)
class CriticFinding:
    """One independent critic finding."""

    kind: str
    object_id: str
    agrees: bool
    reason: str = ""


@dataclass(frozen=True)
class CriticReport:
    """Independent critic agreement report."""

    findings: list[CriticFinding]

    def agrees(self, kind: str, object_id: str) -> bool:
        """Return critic agreement for an object, defaulting to true."""
        for finding in self.findings:
            if finding.kind == kind and finding.object_id == object_id:
                return finding.agrees
        return True

    def has_finding(self, kind: str, object_id: str) -> bool:
        """Return whether the critic explicitly reviewed an object."""
        return any(
            finding.kind == kind and finding.object_id == object_id
            for finding in self.findings
        )

    def reason(self, kind: str, object_id: str) -> str:
        """Return critic reason for an object, if any."""
        for finding in self.findings:
            if finding.kind == kind and finding.object_id == object_id:
                return finding.reason
        return ""


@dataclass(frozen=True)
class RoutedDrafts:
    """Routing result for extracted drafts."""

    accepted: list[DraftObject]
    review: list[DraftObject]
    issues: list[CheckIssue]
    output_dir: Path | None = None
    calibration: list[DraftObject] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Whether every draft cleared automatic routing checks."""
        return not self.review and not self.issues
