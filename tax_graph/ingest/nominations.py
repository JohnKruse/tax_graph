"""Self-serve nomination and acceptance of source-document regions.

The nomination queue is derived from pipeline evidence.  Acceptance verifies the
same evidence against the acquired parent HTML and writes only a manifest entry;
the worksheet harvester remains the source of draft graph objects.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
from typing import Any, Iterable

import yaml

from tax_graph.acquire.manifest import load_manifest
from tax_graph.config import project_root
from tax_graph.ingest.worksheet_harvest import (
    QDCGT_TARGET,
    QDCGT_WORKSHEET_TARGET,
    SOURCE_VERIFIED_WORKSHEET_TARGETS,
    WorksheetTarget,
    harvest_worksheet,
    harvest_worksheet_file,
    normalize_printed_title,
)
from tax_graph.io.loader import load_yaml


_QDCGT_KEY = normalize_printed_title(QDCGT_WORKSHEET_TARGET.title)
_SOURCE_VERIFIED_TARGETS_BY_TITLE = {
    normalize_printed_title(target.title): target
    for target in SOURCE_VERIFIED_WORKSHEET_TARGETS
}
_TITLE_STOP_WORDS = {
    "a",
    "amount",
    "and",
    "are",
    "complete",
    "enter",
    "for",
    "from",
    "form",
    "gain",
    "if",
    "in",
    "instructions",
    "line",
    "of",
    "or",
    "see",
    "tax",
    "the",
    "this",
    "to",
    "use",
    "whichever",
    "worksheet",
}


@dataclass(frozen=True)
class NominationEvidence:
    """One evidence-backed candidate region."""

    title: str
    normalized_title: str
    citing_rows: tuple[str, ...]
    evidence: tuple[str, ...]
    frontier_ids: tuple[str, ...]

    @property
    def count(self) -> int:
        """Return the number of distinct citing rows."""
        return len(self.citing_rows)

    def as_dict(self) -> dict[str, Any]:
        """Return a stable report record."""
        return {
            "title": self.title,
            "normalized_title": self.normalized_title,
            "citing_rows": list(self.citing_rows),
            "reference_count": self.count,
            "evidence": list(self.evidence),
            "frontier_ids": list(self.frontier_ids),
        }


def list_nominations(
    *,
    year: str | int = "2025",
    root: str | Path | None = None,
    run_dir: str | Path | None = None,
    evidence_paths: Iterable[str | Path] = (),
) -> tuple[NominationEvidence, ...]:
    """Derive worksheet candidates from reports and the frontier registry.

    A candidate is listed only when a real row or frontier record names it.  The
    function does not invent a source title and does not write any state.
    """
    root_path = Path(root).resolve() if root is not None else project_root()
    observations: dict[str, dict[str, Any]] = {}

    report_paths: list[Path] = []
    if run_dir is not None:
        run_path = Path(run_dir)
        report_paths.extend(sorted(run_path.glob("*derive_cells_report.yaml")))
        if run_path.is_file():
            report_paths = [run_path]
    report_paths.extend(Path(path) for path in evidence_paths)
    for path in sorted(set(report_paths)):
        _collect_report_observations(path, observations)

    frontier_path = root_path / "graph" / str(year) / "frontier.yaml"
    if frontier_path.exists():
        frontier = load_yaml(frontier_path) or {}
        for item in frontier.get("frontiers", []) or []:
            frontier_id = str(item.get("frontier_id") or "")
            text = " ".join(
                str(item.get(field) or "") for field in ("title", "purpose")
            )
            for title in _titles_in_text(text):
                _observe(
                    observations,
                    title=title,
                    citing_row=_frontier_citing_row(item),
                    evidence=text,
                    frontier_id=frontier_id,
                )

    results = []
    for item in observations.values():
        results.append(
            NominationEvidence(
                title=item["title"],
                normalized_title=item["normalized_title"],
                citing_rows=tuple(sorted(item["citing_rows"])),
                evidence=tuple(item["evidence"]),
                frontier_ids=tuple(sorted(item["frontier_ids"])),
            )
        )
    return tuple(sorted(results, key=lambda item: item.normalized_title))


def accept_nomination(
    *,
    title: str,
    source_document_id: str,
    year: str | int = "2025",
    root: str | Path | None = None,
    document_id: str | None = None,
    kind: str = "worksheet",
    run_dir: str | Path | None = None,
    evidence_paths: Iterable[str | Path] = (),
    html_path: str | Path | None = None,
) -> dict[str, Any]:
    """Accept one evidence-backed title region into the acquisition manifest."""
    root_path = Path(root).resolve() if root is not None else project_root()
    wanted = normalize_printed_title(title)
    evidence = next(
        (item for item in list_nominations(
            year=year,
            root=root_path,
            run_dir=run_dir,
            evidence_paths=evidence_paths,
        ) if item.normalized_title == wanted),
        None,
    )
    if evidence is None or evidence.count == 0:
        raise ValueError(
            f"cannot accept {title!r}: no citing row or frontier evidence was found"
        )

    manifest_path = root_path / "config" / "manifest.yaml"
    manifest_data = load_yaml(manifest_path) or {}
    entries = manifest_data.get("documents") or []
    by_id = {str(entry["document_id"]): entry for entry in entries}
    if source_document_id not in by_id:
        raise ValueError(f"unknown region parent document: {source_document_id}")
    parent = by_id[source_document_id]
    if parent.get("region"):
        raise ValueError(f"region parent cannot itself be a region: {source_document_id}")
    if not parent.get("url"):
        raise ValueError(f"region parent has no acquired URL: {source_document_id}")

    source_path = (
        Path(html_path)
        if html_path is not None
        else root_path / ".cache" / "raw" / str(year) / f"{source_document_id}.html"
    )
    if not source_path.exists():
        raise FileNotFoundError(f"missing acquired parent HTML: {source_path}")
    source_bytes = source_path.read_bytes()
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    try:
        source_text = source_bytes.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError(f"region parent HTML is not ASCII: {source_path}") from exc

    # Preserve the title actually observed in the report.  The normalized key
    # is identity; the printed spelling is the evidence-facing display value.
    title = evidence.title
    resolved_document_id = document_id or _document_id_for_title(title)
    if resolved_document_id in by_id:
        existing = by_id[resolved_document_id]
        existing_title = existing.get("region", {}).get("title", "")
        if normalize_printed_title(existing_title) == wanted:
            if existing.get("region", {}).get("parent_sha256") != source_hash:
                raise ValueError(
                    f"region parent changed for existing document: {resolved_document_id}"
                )
            return {
                "document_id": resolved_document_id,
                "status": "already_present",
                "evidence": evidence,
                "parent_sha256": source_hash,
            }
        raise ValueError(f"manifest document id already exists: {resolved_document_id}")

    target = _target_for_title(
        document_id=resolved_document_id,
        title=title,
        source_document_id=source_document_id,
    )
    harvest_path = source_path
    source_target = _SOURCE_VERIFIED_TARGETS_BY_TITLE.get(normalize_printed_title(title))
    rendered_text_path = source_path.with_suffix(".txt")
    if html_path is None and source_target is not None and rendered_text_path.exists():
        harvest_path = rendered_text_path
    if harvest_path != source_path:
        harvest = harvest_worksheet_file(harvest_path, target, year=year)
    else:
        harvest = harvest_worksheet(source_text, target, year=year)
    if not harvest.ok:
        detail = "; ".join(f"{item.kind}: {item.message}" for item in harvest.findings)
        raise ValueError(f"region title/extent did not verify: {detail}")

    entry = {
        "document_id": resolved_document_id,
        "kind": kind,
        "region": {
            "source_document_id": source_document_id,
            "title": title,
            "parent_sha256": source_hash,
        },
    }
    entries.append(entry)
    manifest_path.write_text(
        yaml.safe_dump(manifest_data, sort_keys=False, allow_unicode=False),
        encoding="ascii",
        newline="\n",
    )
    # Reload through the schema and semantic validator before reporting success.
    load_manifest(root=root_path)
    return {
        "document_id": resolved_document_id,
        "status": "accepted",
        "evidence": evidence,
        "parent_sha256": source_hash,
        "draft_ready": True,
        "harvest": harvest,
    }


def drop_nomination(
    document_id: str,
    *,
    root: str | Path | None = None,
) -> None:
    """Remove one region entry from the manifest without touching graph state."""
    root_path = Path(root).resolve() if root is not None else project_root()
    manifest_path = root_path / "config" / "manifest.yaml"
    manifest_data = load_yaml(manifest_path) or {}
    entries = manifest_data.get("documents") or []
    kept = [entry for entry in entries if str(entry.get("document_id")) != document_id]
    if len(kept) == len(entries):
        raise ValueError(f"manifest document not found: {document_id}")
    removed = next(entry for entry in entries if str(entry.get("document_id")) == document_id)
    if not removed.get("region"):
        raise ValueError(f"refusing to drop non-region manifest document: {document_id}")
    manifest_data["documents"] = kept
    manifest_path.write_text(
        yaml.safe_dump(manifest_data, sort_keys=False, allow_unicode=False),
        encoding="ascii",
        newline="\n",
    )
    load_manifest(root=root_path)


def _collect_report_observations(path: Path, observations: dict[str, dict[str, Any]]) -> None:
    if not path.exists():
        raise FileNotFoundError(f"nomination evidence file not found: {path}")
    payload = load_yaml(path) or {}
    if not isinstance(payload, dict):
        return
    document_id = str(payload.get("document_id") or path.stem)
    for row in payload.get("rows_detail", []) or []:
        texts = [
            row.get("label_before"),
            row.get("form_face_before"),
            row.get("error"),
            row.get("rendered"),
        ]
        for failure in row.get("validation_failures", []) or []:
            texts.extend([failure.get("kind"), failure.get("message")])
        for external in row.get("unresolved_external_nodes", []) or []:
            if isinstance(external, dict):
                texts.extend(str(value) for value in external.values())
        row_id = f"{document_id} line {row.get('line')}"
        for text in texts:
            for title in _titles_in_text(str(text or "")):
                _observe(
                    observations,
                    title=title,
                    citing_row=row_id,
                    evidence=_evidence_excerpt(str(text or ""), title),
                    frontier_id="",
                )
    for cell in payload.get("incomplete_cells", []) or []:
        if not isinstance(cell, dict):
            continue
        text = " ".join(str(cell.get(key) or "") for key in ("printed_label", "instruction_text"))
        row_id = f"{cell.get('document_id') or document_id} line {cell.get('line') or '?'}"
        for title in _titles_in_text(text):
            _observe(
                observations,
                title=title,
                citing_row=row_id,
                evidence=_evidence_excerpt(text, title),
                frontier_id=str(cell.get("frontier_id") or ""),
            )


def _observe(
    observations: dict[str, dict[str, Any]],
    *,
    title: str,
    citing_row: str,
    evidence: str,
    frontier_id: str,
) -> None:
    normalized = normalize_printed_title(title)
    if not normalized:
        return
    item = observations.setdefault(
        normalized,
        {
            "title": " ".join(title.split()),
            "normalized_title": normalized,
            "citing_rows": set(),
            "evidence": [],
            "frontier_ids": set(),
        },
    )
    item["citing_rows"].add(citing_row)
    if evidence and evidence not in item["evidence"]:
        item["evidence"].append(evidence)
    if frontier_id:
        item["frontier_ids"].add(frontier_id)


def _titles_in_text(text: str) -> tuple[str, ...]:
    compact = " ".join(text.split())
    titles: dict[str, str] = {}
    tokens = compact.split()
    for end, raw_token in enumerate(tokens):
        token = raw_token.strip(" .,;:()")
        if token != "Worksheet":
            continue
        candidates: list[str] = []
        for start in range(max(0, end - 14), end):
            first = tokens[start].strip(" .,;:()")
            if not first or first.casefold() in _TITLE_STOP_WORDS or first.isdigit():
                continue
            if first.isupper() and len(first) > 3:
                continue
            candidate_tokens = [item.strip(" .,;:()") for item in tokens[start : end + 1]]
            if any(not item for item in candidate_tokens):
                continue
            candidates.append(" ".join(candidate_tokens))
        if candidates:
            title = max(candidates, key=lambda item: len(item.split()))
            normalized = normalize_printed_title(title)
            if normalized:
                titles.setdefault(normalized, title)
    return tuple(titles.values())


def _evidence_excerpt(text: str, title: str) -> str:
    compact = " ".join(text.split())
    index = compact.find(title)
    if index < 0:
        return compact[:240]
    start = max(0, index - 80)
    return compact[start : min(len(compact), index + len(title) + 160)]


def _frontier_citing_row(item: dict[str, Any]) -> str:
    source = item.get("source") or {}
    target = item.get("target") or {}
    document_id = source.get("document_id") or target.get("document_id") or "frontier"
    line = target.get("line")
    return f"{document_id} line {line}" if line else str(document_id)


def _document_id_for_title(title: str) -> str:
    if normalize_printed_title(title) == _QDCGT_KEY:
        return QDCGT_TARGET
    source_target = _SOURCE_VERIFIED_TARGETS_BY_TITLE.get(normalize_printed_title(title))
    if source_target is not None:
        return source_target.document_id
    slug = re.sub(r"[^a-z0-9]+", "_", title.casefold()).strip("_")
    return slug or "region_document"


def _target_for_title(*, document_id: str, title: str, source_document_id: str) -> WorksheetTarget:
    if normalize_printed_title(title) == _QDCGT_KEY:
        return WorksheetTarget(
            document_id=document_id,
            title=QDCGT_WORKSHEET_TARGET.title,
            start_anchor=QDCGT_WORKSHEET_TARGET.start_anchor,
            source_document_id=source_document_id,
            expected_line_count=QDCGT_WORKSHEET_TARGET.expected_line_count,
            expected_constant_count=QDCGT_WORKSHEET_TARGET.expected_constant_count,
            citation_groups=QDCGT_WORKSHEET_TARGET.citation_groups,
        )
    source_target = _SOURCE_VERIFIED_TARGETS_BY_TITLE.get(normalize_printed_title(title))
    if source_target is not None:
        return WorksheetTarget(
            document_id=document_id,
            title=source_target.title,
            start_anchor=source_target.start_anchor,
            source_document_id=source_document_id,
            end_line=source_target.end_line,
            expected_line_count=source_target.expected_line_count,
            expected_constant_count=source_target.expected_constant_count,
            citation_groups=source_target.citation_groups,
        )
    return WorksheetTarget(
        document_id=document_id,
        title=title,
        start_anchor="nominated-title",
        source_document_id=source_document_id,
    )
