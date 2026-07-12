"""Generate user-facing per-form verification records from committed data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from tax_graph.frontier.build import summarize_frontier
from tax_graph.io.loader import load_graph
from tax_graph.oracles.box_map import load_box_map
from tax_graph.verify.metrics import collect_metrics


@dataclass(frozen=True)
class WitnessSummary:
    """Committed witness evidence for one document."""

    oracle_scenarios: int = 0
    oracle_version: str | None = None
    irs_examples: int = 0
    irs_examples_pending_review: int = 0
    calibration_sample: int | None = None
    escapes: int | None = None
    human_minutes: float | None = None
    nversion_note: str = "No committed N-version corroboration artifact for this document."
    property_note: str = "No committed per-form property-test artifact for this document."
    triage_count: int = 0


@dataclass(frozen=True)
class VerificationRecord:
    """Rendered verification inputs for one public document."""

    document_id: str
    title: str
    document_type: str
    status: str
    source_url: str
    modeled_counts: dict[str, int]
    gaps: tuple[str, ...]
    witnesses: WitnessSummary
    verification_tier: str
    page_path: Path
    gate: str = "project"
    artifact_hash: str = ""


@dataclass(frozen=True)
class VerificationBundle:
    """All generated verification pages plus the roll-up page."""

    year: str
    rollup_text: str
    page_texts: dict[str, str]
    records: tuple[VerificationRecord, ...]


@dataclass(frozen=True)
class VerificationWriteResult:
    """Filesystem paths written by ``write_verification_record``."""

    rollup_path: Path
    page_paths: dict[str, Path]
    bundle: VerificationBundle


def build_verification_bundle(year: str = "2025", root: str | Path | None = None) -> VerificationBundle:
    """Collect committed evidence and render deterministic verification pages."""

    root_path = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[2]
    graph = load_graph(year, root_path)
    frontier = summarize_frontier(year, root=root_path)
    coverage = frontier["coverage"]
    metrics_index = {
        str(report.get("document_id")): report
        for report in collect_metrics(root_path, year=year)
        if isinstance(report, dict) and report.get("document_id")
    }
    example_counts, pending_example_counts = _collect_example_counts(root_path)
    oracle_counts, oracle_version = _collect_oracle_coverage(root_path, graph)
    triage_counts = _collect_triage_counts(root_path, graph)
    gaps_by_document = _collect_gaps(graph, frontier)
    modeled_counts = _collect_modeled_counts(graph)

    records: list[VerificationRecord] = []
    page_texts: dict[str, str] = {}
    for document in _public_documents(graph):
        document_id = str(document["document_id"])
        witnesses = WitnessSummary(
            oracle_scenarios=oracle_counts.get(document_id, 0),
            oracle_version=oracle_version if oracle_counts.get(document_id, 0) else None,
            irs_examples=example_counts.get(document_id, 0),
            irs_examples_pending_review=pending_example_counts.get(document_id, 0),
            calibration_sample=_optional_int(metrics_index.get(document_id, {}).get("routing", {}).get("calibration_sample")),
            escapes=_optional_int(metrics_index.get(document_id, {}).get("escapes")),
            human_minutes=_optional_float(metrics_index.get(document_id, {}).get("human_minutes")),
            triage_count=triage_counts.get(document_id, 0),
        )
        page_path = Path("docs") / "verification" / f"{document_id}.md"
        gate = str(document.get("gate") or "project")
        verification_tier = _verification_tier(witnesses)
        if gate == "user":
            verification_tier = str(
                (graph.extension_metadata or {}).get(document_id, {}).get("verification_tier")
                or verification_tier
            )
        record = VerificationRecord(
            document_id=document_id,
            title=str(document.get("title") or document_id),
            document_type=str(document.get("document_type") or "unknown"),
            status=str(document.get("status") or "unknown"),
            source_url=str(document.get("source_url") or "https://www.irs.gov/forms-pubs"),
            modeled_counts=modeled_counts.get(document_id, {}),
            gaps=gaps_by_document.get(document_id, ()),
            witnesses=witnesses,
            verification_tier=verification_tier,
            page_path=page_path,
            gate=gate,
            artifact_hash=(graph.extension_hashes or {}).get(document_id, graph.base_content_hash),
        )
        records.append(record)
        page_texts[document_id] = render_verification_page(record)

    rollup_text = render_verification_rollup(
        tuple(records),
        year=str(year),
        coverage=coverage,
        declared_count=len(frontier["worklist"]),
    )
    return VerificationBundle(
        year=str(year),
        rollup_text=rollup_text,
        page_texts=page_texts,
        records=tuple(records),
    )


def write_verification_record(
    year: str = "2025",
    root: str | Path | None = None,
    *,
    rollup_path: str | Path | None = None,
    pages_dir: str | Path | None = None,
) -> VerificationWriteResult:
    """Write ``VERIFICATION.md`` plus per-form pages."""

    root_path = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[2]
    bundle = build_verification_bundle(year=year, root=root_path)
    final_rollup_path = Path(rollup_path).resolve() if rollup_path is not None else root_path / "VERIFICATION.md"
    final_pages_dir = Path(pages_dir).resolve() if pages_dir is not None else root_path / "docs" / "verification"
    final_pages_dir.mkdir(parents=True, exist_ok=True)
    _write_text(final_rollup_path, bundle.rollup_text)
    written_pages: dict[str, Path] = {}
    for record in bundle.records:
        page_path = final_pages_dir / f"{record.document_id}.md"
        _write_text(page_path, bundle.page_texts[record.document_id])
        written_pages[record.document_id] = page_path
    return VerificationWriteResult(rollup_path=final_rollup_path, page_paths=written_pages, bundle=bundle)


def render_verification_rollup(
    records: tuple[VerificationRecord, ...],
    *,
    year: str,
    coverage: dict[str, Any],
    declared_count: int,
) -> str:
    """Render the repo-wide ``VERIFICATION.md`` roll-up."""

    lines = [
        f"# Verification Record ({year})",
        "",
        "This report is generated from committed repository data by `tax_graph.verify.record`.",
        "",
        "## Coverage",
        "",
        f"- Full filer-weighted coverage: {coverage['full_universe_percent']:.1f}% ({coverage['modeled_weight']} / {coverage['full_universe_weight']})",
        f"- In-scope filer-weighted coverage: {coverage['in_scope_percent']:.1f}% ({coverage['in_scope_modeled_weight']} / {coverage['in_scope_weight']})",
        f"- Declared frontier items still open: {declared_count}",
        "",
        "## Forms",
        "",
    ]
    for record in records:
        lines.extend(
            [
                f"### [{record.title}]({record.page_path.as_posix()})",
                "",
                f"- Document id: `{record.document_id}`",
                f"- Status: `{record.status}`",
                f"- Verification tier: {record.verification_tier}",
                f"- Gate: {record.gate}",
                f"- Artifact content hash: `{record.artifact_hash}`",
                f"- Oracle witness: {_oracle_summary(record.witnesses)}",
                f"- IRS worked examples: {_example_summary(record.witnesses)}",
                f"- Calibration audit: {_calibration_summary(record.witnesses)}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def render_verification_page(record: VerificationRecord) -> str:
    """Render one per-form verification page."""

    lines = [
        f"# {record.title} Verification Record ({record.document_id})",
        "",
        "This page is generated from committed repository data by `tax_graph.verify.record`.",
        "",
        "## Summary",
        "",
        f"- Document id: `{record.document_id}`",
        f"- Document type: `{record.document_type}`",
        f"- Status: `{record.status}`",
        f"- Verification tier: {record.verification_tier}",
        f"- Gate: {record.gate}",
        f"- Artifact content hash: `{record.artifact_hash}`",
        f"- Source URL: {record.source_url}",
        "",
        "## Modeled",
        "",
    ]
    if record.modeled_counts:
        for kind, count in sorted(record.modeled_counts.items()):
            lines.append(f"- {kind}: {count}")
    else:
        lines.append("- No modeled objects are committed for this document yet.")

    lines.extend(["", "## Explicit Gaps", ""])
    if record.gaps:
        for gap in record.gaps:
            lines.append(f"- {gap}")
    else:
        lines.append("- No explicit gap record is committed for this document.")

    lines.extend(
        [
            "",
            "## Witnesses",
            "",
            f"- Oracle differential: {_oracle_summary(record.witnesses)}",
            f"- IRS worked examples: {_example_summary(record.witnesses)}",
            f"- N-version corroboration: {record.witnesses.nversion_note}",
            f"- Property tests: {record.witnesses.property_note}",
            f"- Calibration audit: {_calibration_summary(record.witnesses)}",
            f"- Triage outcomes: {_triage_summary(record.witnesses)}",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def verification_summary_for_document(
    document_id: str,
    *,
    year: str = "2025",
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Return one document's verification summary for CLI/MCP consumers."""

    bundle = build_verification_bundle(year=year, root=root)
    for record in bundle.records:
        if record.document_id == document_id:
            return {
                "document_id": record.document_id,
                "title": record.title,
                "status": record.status,
                "verification_tier": record.verification_tier,
                "gate": record.gate,
                "artifact_hash": record.artifact_hash,
                "modeled_counts": record.modeled_counts,
                "gaps": list(record.gaps),
                "witnesses": {
                    "oracle_scenarios": record.witnesses.oracle_scenarios,
                    "oracle_version": record.witnesses.oracle_version,
                    "irs_examples": record.witnesses.irs_examples,
                    "irs_examples_pending_review": record.witnesses.irs_examples_pending_review,
                    "calibration_sample": record.witnesses.calibration_sample,
                    "escapes": record.witnesses.escapes,
                    "human_minutes": record.witnesses.human_minutes,
                    "nversion_note": record.witnesses.nversion_note,
                    "property_note": record.witnesses.property_note,
                    "triage_count": record.witnesses.triage_count,
                },
                "page_markdown": bundle.page_texts[document_id],
            }
    return {"document_id": document_id, "found": False}


def _public_documents(graph: Any) -> list[dict[str, Any]]:
    return sorted(
        [
            document
            for document in graph.items("documents")
            if str(document.get("document_type")) in {"tax_form", "schedule", "source_document"}
        ],
        key=lambda document: (str(document.get("title") or ""), str(document.get("document_id") or "")),
    )


def _collect_modeled_counts(graph: Any) -> dict[str, dict[str, int]]:
    node_doc = {str(node["node_id"]): str(node["document_id"]) for node in graph.items("nodes") if node.get("document_id")}
    counts: dict[str, dict[str, int]] = {}
    for kind in ("documents", "nodes", "tables", "citations"):
        for item in graph.items(kind):
            document_id = item.get("document_id")
            if not document_id:
                continue
            counts.setdefault(str(document_id), {})
            counts[str(document_id)][kind] = counts[str(document_id)].get(kind, 0) + 1

    rules_by_document: dict[str, set[str]] = {}
    edges_by_document: dict[str, int] = {}
    for edge in graph.items("edges"):
        target_doc = node_doc.get(str(edge.get("target")))
        if not target_doc:
            continue
        edges_by_document[target_doc] = edges_by_document.get(target_doc, 0) + 1
        if edge.get("rule_id"):
            rules_by_document.setdefault(target_doc, set()).add(str(edge["rule_id"]))
    for document_id, count in edges_by_document.items():
        counts.setdefault(document_id, {})
        counts[document_id]["edges"] = count
    for document_id, rule_ids in rules_by_document.items():
        counts.setdefault(document_id, {})
        counts[document_id]["rules"] = len(rule_ids)
    return counts


def _collect_gaps(graph: Any, frontier: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    gaps: dict[str, list[str]] = {}
    for document in graph.items("documents"):
        document_id = document.get("document_id")
        if not document_id:
            continue
        entries = []
        for item in document.get("not_modeled_fields", []):
            reason = str(item.get("reason") or "No reason recorded.")
            if item.get("line_anchor"):
                entries.append(f"Line {item['line_anchor']}: {reason}")
            elif item.get("field_id"):
                entries.append(f"{item['field_id']}: {reason}")
            else:
                entries.append(reason)
        gaps[str(document_id)] = entries

    for item in frontier.get("worklist", []):
        target = item.get("target", {})
        document_id = target.get("document_id")
        if not document_id:
            continue
        title = str(item.get("title") or item.get("frontier_id") or "Declared frontier item")
        line = (
            f" line {target['line']}"
            if target.get("line") is not None and f"line {target['line']}".lower() not in title.lower()
            else ""
        )
        purpose = str(item.get("purpose") or "No purpose recorded.")
        gaps.setdefault(str(document_id), []).append(f"{title}{line}: {purpose}")
    return {document_id: tuple(entries) for document_id, entries in sorted(gaps.items())}


def _collect_example_counts(root: Path) -> tuple[dict[str, int], dict[str, int]]:
    counts: dict[str, int] = {}
    pending_counts: dict[str, int] = {}
    examples_dir = root / "examples" / "irs_examples"
    if not examples_dir.is_dir():
        return counts, pending_counts
    for provenance_path in sorted(examples_dir.rglob("provenance.yaml")):
        payload = yaml.safe_load(provenance_path.read_text(encoding="utf-8")) or {}
        source_document_id = str(payload.get("source_document_id") or "")
        if not source_document_id:
            continue
        pending_review = not bool(payload.get("human_confirmed"))
        for document_id in _related_document_ids(source_document_id):
            counts[document_id] = counts.get(document_id, 0) + 1
            if pending_review:
                pending_counts[document_id] = pending_counts.get(document_id, 0) + 1
    return counts, pending_counts


def _collect_oracle_coverage(root: Path, graph: Any) -> tuple[dict[str, int], str | None]:
    corpus_path = root / "examples" / "oracle_corpus" / "corpus.yaml"
    if not corpus_path.exists():
        return {}, None
    corpus = yaml.safe_load(corpus_path.read_text(encoding="utf-8")) or {}
    scenario_count = int(corpus.get("scenario_count") or 0)
    version = str(corpus.get("provenance", {}).get("oracle_version") or "") or None
    box_map = load_box_map(root / "oracles" / "box_map_2025.yaml")
    node_doc = {str(node["node_id"]): str(node["document_id"]) for node in graph.items("nodes") if node.get("document_id")}
    counts: dict[str, int] = {}
    for box in box_map.boxes:
        document_id = node_doc.get(box.node_id)
        if not document_id:
            continue
        counts[document_id] = scenario_count
    return counts, version


def _collect_triage_counts(root: Path, graph: Any) -> dict[str, int]:
    triage_path = root / "oracles" / "triage.yaml"
    if not triage_path.exists():
        return {}
    payload = yaml.safe_load(triage_path.read_text(encoding="utf-8")) or {}
    entries = payload.get("entries", []) if isinstance(payload, dict) else []
    node_doc = {str(node["node_id"]): str(node["document_id"]) for node in graph.items("nodes") if node.get("document_id")}
    counts: dict[str, int] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        document_id = None
        node_id = entry.get("node_id")
        if node_id:
            document_id = node_doc.get(str(node_id))
        if not document_id and entry.get("document_id"):
            document_id = str(entry["document_id"])
        if document_id:
            counts[document_id] = counts.get(document_id, 0) + 1
    return counts


def _related_document_ids(document_id: str) -> set[str]:
    related = {document_id}
    if document_id.startswith("instructions_"):
        related.add(document_id.removeprefix("instructions_"))
    else:
        related.add(f"instructions_{document_id}")
    return related


def _verification_tier(witnesses: WitnessSummary) -> str:
    if witnesses.oracle_scenarios:
        return "independently witnessed"
    if witnesses.irs_examples:
        return "IRS-example verified"
    if witnesses.calibration_sample is not None:
        return "structurally verified"
    return "partial"


def _oracle_summary(witnesses: WitnessSummary) -> str:
    if not witnesses.oracle_scenarios:
        return "No committed oracle witness covers this document."
    return (
        f"{witnesses.oracle_scenarios} agreed scenario(s)"
        f" via OpenTaxSolver `{witnesses.oracle_version}`."
    )


def _example_summary(witnesses: WitnessSummary) -> str:
    if not witnesses.irs_examples:
        return "No committed IRS worked-example fixture covers this document."
    if not witnesses.irs_examples_pending_review:
        return f"{witnesses.irs_examples} committed IRS worked-example fixture(s)."
    return (
        f"{witnesses.irs_examples} committed IRS worked-example fixture(s); "
        f"{witnesses.irs_examples_pending_review} pending human review."
    )


def _calibration_summary(witnesses: WitnessSummary) -> str:
    if witnesses.calibration_sample is None:
        return "No committed calibration metrics artifact covers this document."
    minutes = (
        f"human minutes {witnesses.human_minutes:g}"
        if witnesses.human_minutes is not None
        else "human minutes not yet recorded"
    )
    escapes = witnesses.escapes if witnesses.escapes is not None else 0
    return f"sample {witnesses.calibration_sample}, escapes {escapes}, {minutes}."


def _triage_summary(witnesses: WitnessSummary) -> str:
    if not witnesses.triage_count:
        return "No committed triage entries for this document."
    return f"{witnesses.triage_count} committed triage entrie(s)."


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
