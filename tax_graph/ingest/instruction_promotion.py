"""Join mined instruction sections to canonical addresses and promote citations.

The join is intentionally structure-first.  A section's nearest document heading
selects the return document, and its printed line tokens select terminal canonical
addresses.  A missing document context, a missing address, or a source quote that
cannot be verified is retained as a review finding instead of being guessed.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

import yaml

from tax_graph.addressing.registry import CanonicalAddress, load_address_artifacts
from tax_graph.ingest.instruction_sections import (
    InstructionDocumentContext,
    MinedInstructionSection,
    instruction_document_contexts,
    mine_instruction_html_file,
)
from tax_graph.review_queue import upsert_deferred_review_entries


CANARY_DOCUMENTS = frozenset(
    {
        "form_1040_2025",
        "schedule_1_2025",
        "schedule_1a_2025",
        "schedule_2_2025",
        "schedule_3_2025",
    }
)


@dataclass(frozen=True)
class InstructionJoinFinding:
    """One fail-closed instruction-to-address join finding."""

    queue_id: str
    document_id: str
    control: str
    reason: str
    observed: str
    expected: str
    evidence: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        """Return a stable review-queue-shaped record."""
        return {
            "queue_id": self.queue_id,
            "document_id": self.document_id,
            "control": self.control,
            "reason": self.reason,
            "observed": self.observed,
            "expected": self.expected,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True)
class InstructionJoin:
    """One mined section joined to one return document's addresses."""

    source_document_id: str
    target_document_id: str
    citation_id: str
    section: MinedInstructionSection
    address_ids: tuple[str, ...]
    quoted_text: str


@dataclass(frozen=True)
class InstructionJoinResult:
    """Deterministic join output before any artifact write."""

    joins: tuple[InstructionJoin, ...]
    findings: tuple[InstructionJoinFinding, ...]
    coverage_before: dict[str, int]
    coverage_after: dict[str, int]


def join_instruction_sections(
    sections: Iterable[MinedInstructionSection],
    addresses: Iterable[CanonicalAddress],
    *,
    source_document_id: str,
    expected_document_ids: Iterable[str] = (),
    expected_contexts: Mapping[str, InstructionDocumentContext] | None = None,
) -> InstructionJoinResult:
    """Join mined sections to terminal addresses without writing artifacts.

    The five-document 1040 canary is deliberately bounded.  Multiple terminal
    controls sharing one printed line are an intentional fan-out, not an
    ambiguity: every control on that canonical line receives the same instruction
    citation.  Ambiguity is reserved for unresolved structural document context.
    """
    address_items = tuple(addresses)
    address_groups: dict[tuple[str, str], list[CanonicalAddress]] = {}
    for address in address_items:
        if address.document_id not in CANARY_DOCUMENTS:
            continue
        if address.kind not in {"control", "option"} or not address.official_ref:
            continue
        key = (address.document_id, str(address.official_ref).lower())
        address_groups.setdefault(key, []).append(address)

    coverage_before = {
        document_id: sum(bool(address.raw.get("citation_refs")) for address in group)
        for document_id, group in _terminal_addresses(address_items).items()
        if document_id in CANARY_DOCUMENTS
    }
    joins: list[InstructionJoin] = []
    findings: list[InstructionJoinFinding] = []
    seen_citations: set[str] = set()

    for section in sections:
        target_document_id = _target_document_id(section)
        evidence = (
            f"source_document_id={source_document_id}",
            f"anchor={section.heading.anchor_id or 'missing'}",
            f"source_span={section.source_start}:{section.source_end}",
            f"line_tokens={','.join(section.line_tokens)}",
        )
        if target_document_id is None:
            findings.append(
                _finding(
                    source_document_id,
                    section,
                    "unresolved_document_context",
                    observed="; ".join(section.parent_headings),
                    expected="one canary return-document instruction context",
                    evidence=evidence,
                )
            )
            continue

        address_ids = sorted(
            {
                address.address_id
                for token in section.line_tokens
                for address in address_groups.get((target_document_id, token.lower()), [])
            }
        )
        if not address_ids:
            findings.append(
                _finding(
                    source_document_id,
                    section,
                    "missing_canonical_address",
                    observed=f"{target_document_id}:{','.join(section.line_tokens)}",
                    expected="at least one terminal canonical address",
                    evidence=evidence,
                )
            )
            continue

        if not section.heading.anchor_id:
            findings.append(
                _finding(
                    source_document_id,
                    section,
                    "missing_html_anchor",
                    observed="empty anchor id",
                    expected="stable HTML anchor id",
                    evidence=evidence,
                )
            )
            continue

        quoted_text = section_quote(section)
        if not quoted_text:
            findings.append(
                _finding(
                    source_document_id,
                    section,
                    "empty_source_quote",
                    observed="empty section text",
                    expected="non-empty text derived from stored HTML",
                    evidence=evidence,
                )
            )
            continue

        citation_id = _citation_id(target_document_id, section)
        if citation_id in seen_citations:
            findings.append(
                _finding(
                    source_document_id,
                    section,
                    "duplicate_citation_id",
                    observed=citation_id,
                    expected="unique deterministic citation id",
                    evidence=evidence,
                )
            )
            continue
        seen_citations.add(citation_id)
        joins.append(
            InstructionJoin(
                source_document_id=source_document_id,
                target_document_id=target_document_id,
                citation_id=citation_id,
                section=section,
                address_ids=tuple(address_ids),
                quoted_text=quoted_text,
            )
        )

    joined_documents = {join.target_document_id for join in joins}
    for document_id in sorted(set(expected_document_ids) - joined_documents):
        context = (expected_contexts or {}).get(document_id)
        findings.append(
            _empty_document_finding(
                source_document_id,
                document_id,
                context=context,
            )
        )

    cited_ids = {address_id for join in joins for address_id in join.address_ids}
    coverage_after = {
        document_id: sum(
            bool(address.raw.get("citation_refs")) or address.address_id in cited_ids
            for address in group
        )
        for document_id, group in _terminal_addresses(address_items).items()
        if document_id in CANARY_DOCUMENTS
    }
    return InstructionJoinResult(
        joins=tuple(joins),
        findings=tuple(findings),
        coverage_before=coverage_before,
        coverage_after=coverage_after,
    )


def section_quote(section: MinedInstructionSection) -> str:
    """Return one contiguous source block without adding wrappers.

    A mined section can contain intermediate HTML subheadings between body blocks.
    Joining those blocks would manufacture a non-contiguous quote, so promotion
    cites the first source block and preserves the complete section structure in
    the miner output for later, independently cited spans.
    """
    blocks = [block.text.strip() for block in section.blocks if block.text.strip()]
    if blocks:
        return blocks[0]
    return section.semantic_title.strip()


def promote_instruction_html(
    root: str | Path,
    *,
    year: str | int,
    source_document_id: str,
    html_path: str | Path,
    citation_filename: str = "instruction-form-1040-html.yaml",
) -> InstructionJoinResult:
    """Promote verified 1040 HTML sections into citations and address refs."""
    root_path = Path(root).resolve()
    source_path = Path(html_path)
    html_text = source_path.read_text(encoding="ascii")
    sections = mine_instruction_html_file(source_path, document_id=source_document_id)
    contexts = instruction_document_contexts(html_text, year=year)
    address_artifacts = load_address_artifacts(year, root_path)
    result = join_instruction_sections(
        sections,
        address_artifacts.addresses,
        source_document_id=source_document_id,
        expected_document_ids=(context.document_id for context in contexts),
        expected_contexts={context.document_id: context for context in contexts},
    )

    metadata_path = source_path.with_name(source_path.name + ".json")
    metadata = json.loads(metadata_path.read_text(encoding="ascii"))
    _verify_quotes_are_from_html(result.joins, html_text)

    citation_path = root_path / "graph" / str(year) / "citations" / citation_filename
    if result.joins:
        existing = _load_list(citation_path)
        existing_by_id = {str(item.get("citation_id")): item for item in existing}
        new_records = [_citation_record(join, metadata) for join in result.joins]
        for record in new_records:
            old = existing_by_id.get(str(record["citation_id"]))
            if old is not None and old != record:
                if not (
                    old.get("source_document_id") == source_document_id
                    and str(old.get("locator") or "").startswith("html#")
                ):
                    raise ValueError(f"citation id collision with different content: {record['citation_id']}")
            existing_by_id[str(record["citation_id"])] = record
        _write_yaml(citation_path, [existing_by_id[key] for key in sorted(existing_by_id)])

    by_address: dict[str, list[str]] = {}
    for join in result.joins:
        for address_id in join.address_ids:
            by_address.setdefault(address_id, []).append(join.citation_id)
    for document_id in sorted({join.target_document_id for join in result.joins}):
        address_path = root_path / "graph" / str(year) / "addresses" / f"{document_id}.yaml"
        payload = yaml.safe_load(address_path.read_text(encoding="utf-8")) or {}
        for address in payload.get("addresses", []) or []:
            address_id = str(address.get("address_id") or "")
            refs = {str(value) for value in address.get("citation_refs", []) or []}
            refs.update(by_address.get(address_id, []))
            if refs:
                address["citation_refs"] = sorted(refs)
        _write_yaml(address_path, payload)
    if result.findings:
        upsert_deferred_review_entries(
            root=root_path,
            year=year,
            entries=(
                _finding_queue_entry(
                    finding,
                    root=root_path,
                    source_document_id=source_document_id,
                    html_path=source_path,
                    citation_path=citation_path,
                    metadata=metadata,
                )
                for finding in result.findings
            ),
        )
    return result


def _target_document_id(section: MinedInstructionSection) -> str | None:
    """Resolve one structural instruction context to one canary document."""
    parents = list(section.parent_headings)
    lowered = [parent.lower() for parent in parents]
    context_index = -1
    target: str | None = None
    for index, parent in enumerate(lowered):
        if "instructions for schedule 1-a" in parent:
            context_index, target = index, "schedule_1a_2025"
        elif "instructions for schedule 1 additional" in parent:
            context_index, target = index, "schedule_1_2025"
        elif "instructions for schedule 2 additional" in parent:
            context_index, target = index, "schedule_2_2025"
        elif "instructions for schedule 3 additional" in parent:
            context_index, target = index, "schedule_3_2025"
        elif "line instructions for forms 1040" in parent:
            context_index, target = index, "form_1040_2025"
    if target is None:
        return None
    if any("worksheet" in parent for parent in lowered[context_index + 1 :]):
        return None
    return target


def _empty_document_finding(
    source_document_id: str,
    target_document_id: str,
    *,
    context: InstructionDocumentContext | None,
) -> InstructionJoinFinding:
    """Create a finding when an expected document produced zero joins."""
    heading = context.heading if context is not None else None
    anchor = heading.anchor_id if heading is not None else "missing"
    evidence = [
        f"source_document_id={source_document_id}",
        f"expected_document_id={target_document_id}",
        f"context_heading={heading.text if heading is not None else 'not found'}",
        f"anchor={anchor}",
        f"source_span={heading.source_start}:{heading.source_end}" if heading is not None else "source_span=unknown",
        "promoted_section_count=0",
    ]
    return InstructionJoinFinding(
        queue_id=f"instruction_join_{source_document_id}_{target_document_id}_empty_document",
        document_id=target_document_id,
        control=anchor,
        reason="empty_expected_document",
        observed="promoted_section_count=0",
        expected="at least one promoted instruction section or an explicit source finding",
        evidence=tuple(evidence),
    )


def _citation_id(target_document_id: str, section: MinedInstructionSection) -> str:
    anchor = re.sub(r"[^a-z0-9]+", "_", section.heading.anchor_id.lower()).strip("_")
    return f"cite_instruction_{target_document_id}_{anchor}"


def _citation_record(join: InstructionJoin, metadata: Mapping[str, Any]) -> dict[str, Any]:
    section = join.section
    return {
        "citation_id": join.citation_id,
        "document_id": join.source_document_id,
        "source_document_id": join.source_document_id,
        "locator": f"html#{section.heading.anchor_id}",
        "quoted_text": join.quoted_text,
        "semantic_title": section.semantic_title,
        "url": str(metadata["url"]),
        "retrieved_date": str(metadata["retrieved_date"]),
    }


def _verify_quotes_are_from_html(joins: Iterable[InstructionJoin], html_text: str) -> None:
    for join in joins:
        section = join.section
        if section.blocks:
            for block in section.blocks:
                fragment = html_text[block.source_start : block.source_end]
                if _normalize(block.text) not in _normalize(_html_text(fragment)):
                    raise ValueError(f"quote is not present in stored HTML: {join.citation_id}")
        else:
            if _normalize(section.semantic_title) not in _normalize(_html_text(html_text)):
                raise ValueError(f"quote is not present in stored HTML: {join.citation_id}")


def _html_text(html_text: str) -> str:
    from html.parser import HTMLParser

    class TextParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.parts: list[str] = []

        def handle_data(self, data: str) -> None:
            self.parts.append(data)

    parser = TextParser()
    parser.feed(html_text)
    parser.close()
    return "".join(parser.parts)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _terminal_addresses(
    addresses: Iterable[CanonicalAddress],
) -> dict[str, list[CanonicalAddress]]:
    result: dict[str, list[CanonicalAddress]] = {}
    for address in addresses:
        if address.kind in {"control", "option"}:
            result.setdefault(address.document_id, []).append(address)
    return result


def _finding(
    source_document_id: str,
    section: MinedInstructionSection,
    reason: str,
    *,
    observed: str,
    expected: str,
    evidence: Iterable[str],
) -> InstructionJoinFinding:
    anchor = re.sub(r"[^a-z0-9]+", "_", section.heading.anchor_id.lower()).strip("_") or "no_anchor"
    return InstructionJoinFinding(
        queue_id=f"instruction_join_{source_document_id}_{anchor}_{reason}",
        document_id=source_document_id,
        control=anchor,
        reason=reason,
        observed=observed,
        expected=expected,
        evidence=tuple(evidence),
    )


def _finding_queue_entry(
    finding: InstructionJoinFinding,
    *,
    root: Path,
    source_document_id: str,
    html_path: Path,
    citation_path: Path,
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Shape one deterministic finding as a deferred-review queue entry."""
    return {
        "queue_id": finding.queue_id,
        "kind": "instruction_join_review",
        "status": "deferred",
        "priority": "medium",
        "document_id": finding.document_id,
        "source_document_id": source_document_id,
        "created_date": str(metadata.get("retrieved_date") or "unknown"),
        "created_by": "tax_graph.ingest.instruction_promotion",
        "summary": (
            f"Instruction join finding {finding.reason} for {finding.document_id}: "
            f"{finding.observed}; expected {finding.expected}."
        ),
        "artifact_paths": [
            _relative_path(root, html_path),
            _relative_path(root, citation_path),
        ],
        "reason": finding.reason,
        "observed": finding.observed,
        "expected": finding.expected,
        "evidence": list(finding.evidence),
    }


def _relative_path(root: Path, path: Path) -> str:
    """Return a stable repository-relative path when possible."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _load_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(payload, list):
        raise ValueError(f"citation file must contain a list: {path}")
    return [dict(item) for item in payload]


def _write_yaml(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(value, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
        newline="\n",
    )
