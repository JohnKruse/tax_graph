"""Return-scoped output paths and filing-bundle orchestration."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Mapping

from tax_graph.config import get_config_value, load_config
from tax_graph.engine import Result
from tax_graph.output.field_maps import load_field_maps
from tax_graph.output.fill import FilledForm, build_field_values, fill_official_pdf
from tax_graph.output.sidecar import write_ots_sidecar


RETURN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")


def resolve_return_root(
    *,
    project_root: str | Path,
    facts_document: Mapping[str, Any],
    return_id: str | None = None,
    output_root: str | Path | None = None,
) -> tuple[str, Path]:
    """Resolve and create one isolated return output directory."""
    root = Path(project_root).resolve()
    resolved_id = str(
        return_id
        or facts_document.get("return_id")
        or facts_document.get("scenario_id")
        or "return"
    )
    if not RETURN_ID_RE.fullmatch(resolved_id):
        raise ValueError("return_id must contain only letters, digits, underscores, and hyphens")
    if output_root is None:
        config = load_config(root=root)
        configured = get_config_value(config, "project.paths.output_dir", "output")
        base = (root / str(configured)).resolve()
    else:
        base = Path(output_root).resolve()
    _reject_graph_path(root, base)
    destination = (base / "returns" / resolved_id).resolve()
    if base not in destination.parents:
        raise ValueError("return output escaped the configured output root")
    destination.mkdir(parents=True, exist_ok=True)
    return resolved_id, destination


def validate_direct_return_root(*, project_root: str | Path, return_root: str | Path) -> Path:
    """Validate a legacy direct output directory against committed graph data."""
    root = Path(project_root).resolve()
    destination = Path(return_root).resolve()
    _reject_graph_path(root, destination)
    return destination


def used_form_ids(facts_document: Mapping[str, Any]) -> tuple[str, ...]:
    """Return official forms actually touched by supplied return facts."""
    used = {"form_1040_2025"}
    for fact in facts_document.get("facts", []) or []:
        node_id = str(fact.get("node_id", ""))
        for document_id in (
            "schedule_1_2025",
            "schedule_1a_2025",
            "schedule_2_2025",
            "schedule_3_2025",
            "schedule_a_2025",
            "schedule_b_2025",
            "schedule_d_2025",
            "form_6251_2025",
        ):
            if node_id.startswith(f"{document_id}_"):
                used.add(document_id)
    if facts_document.get("tables"):
        used.update({"form_8949_2025", "schedule_d_2025"})
    return tuple(sorted(used))


def export_filing_bundle(
    *,
    facts_document: Mapping[str, Any],
    result: Result,
    year: str | int,
    project_root: str | Path,
    return_root: str | Path,
    template_path: str | Path | None = None,
) -> dict[str, Any]:
    """Fill used official forms and emit the OTS sidecar under one return root."""
    project = Path(project_root).resolve()
    destination = Path(return_root).resolve()
    forms_dir = destination / "forms"
    maps = {item["document_id"]: item for item in load_field_maps(year, project)}
    filled: list[FilledForm] = []
    blank_notes: list[dict[str, str]] = []
    for document_id in used_form_ids(facts_document):
        source = project / ".cache" / "raw" / str(year) / f"{document_id}.pdf"
        if not source.exists():
            raise FileNotFoundError(f"official cached PDF is missing: {source}")
        field_values, notes = build_field_values(maps[document_id], result, facts_document, root=project)
        filled.append(
            fill_official_pdf(
                source,
                forms_dir / f"{document_id}.pdf",
                document_id=document_id,
                field_values=field_values,
                blank_with_note=notes,
            )
        )
        blank_notes.extend({"document_id": document_id, **item} for item in notes)
    sidecar = write_ots_sidecar(facts_document, destination / "ots", root=project, template_path=template_path)
    manifest = {
        "forms": [str(item.output_path) for item in filled],
        "sidecar": {key: str(value) for key, value in sidecar.items()},
        "blank_with_note": _dedupe_notes(blank_notes),
    }
    (destination / "bundle.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return manifest


def _dedupe_notes(notes: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    result: list[dict[str, str]] = []
    for item in notes:
        key = (item.get("document_id", ""), item.get("frontier_id", ""), item.get("note", ""))
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _reject_graph_path(project_root: Path, candidate: Path) -> None:
    graph_root = (project_root / "graph").resolve()
    if candidate == graph_root or graph_root in candidate.parents:
        raise ValueError("return outputs may not be written under graph/<year>")
