"""Measure draft completeness against each form's deterministic outline.

This report is intentionally independent of the retired handcrafted expression
set. A cell is complete only when the outline pass attempted it, produced an
expression rule, and attached a verbatim citation. Missing work is a named
review gap rather than an absent row in a score.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import yaml

from tax_graph.config import get_config_value, load_config, project_root
from tax_graph.io.loader import load_yaml
from tax_graph.verify.expressions import build_expression_agreement_report


DEFAULT_FORMS = ("form_1040_2025", "schedule_1_2025", "schedule_a_2025")


def build_form_completeness_report(
    *,
    year: str | int = "2025",
    root: str | Path | None = None,
    documents: Iterable[str] = DEFAULT_FORMS,
    graph_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Build the review-facing completeness report from draft sidecars."""
    root_path = Path(root).resolve() if root is not None else project_root()
    configured = Path(graph_dir) if graph_dir is not None else Path(
        get_config_value(load_config(root=root_path), "project.paths.graph_dir", "graph")
    )
    draft_root = configured if configured.is_absolute() else root_path / configured
    draft_root = draft_root / str(year) / "_drafts"
    agreement = build_expression_agreement_report(year=year, root=root_path, graph_dir=graph_dir)
    diff_by_document: dict[str, list[dict[str, Any]]] = {}
    for row in agreement.get("rows", []):
        diff_by_document.setdefault(str(row.get("document_id", "unknown")), []).append(row)

    rendered: dict[str, dict[str, Any]] = {}
    for document_id in documents:
        draft_dir = draft_root / document_id
        stats = _load_mapping(draft_dir / "micro_extraction.yaml")
        cells = [item for item in stats.get("formula_cells", []) if isinstance(item, dict)]
        complete = [item for item in cells if item.get("status") == "complete"]
        with_expression_no_citation = [
            item for item in cells if item.get("status") == "expression_without_citation"
        ]
        gaps = [item for item in cells if item.get("status") == "review_gap"]
        metrics = _load_mapping(draft_dir / "metrics.yaml")
        llm_calls = [item for item in metrics.get("llm_calls", []) if isinstance(item, dict)]
        rendered[document_id] = {
            "formula_cells": len(cells),
            "expression_and_verbatim_citation": len(complete),
            "expression_without_citation": len(with_expression_no_citation),
            "neither_expression_nor_citation": len(gaps),
            "completeness_rate": len(complete) / len(cells) if cells else 0.0,
            "expression_without_citation_cells": _cell_refs(with_expression_no_citation),
            "review_gaps": gaps,
            "wrong_owner_instruction_spans": int(stats.get("wrong_owner_instruction_span_count", 0)),
            "wrong_owner_instruction_addresses": sorted(
                set(str(item) for item in stats.get("wrong_owner_instruction_addresses", []))
            ),
            "unresolved_line_refs": list(stats.get("unresolved_line_refs", [])),
            "resolved_models": sorted({str(item.get("resolved_model")) for item in llm_calls if item.get("resolved_model")}),
            "resolved_providers": sorted({str(item.get("resolved_provider")) for item in llm_calls if item.get("resolved_provider")}),
            "prompt_tokens": sum(_number(item.get("prompt_tokens")) for item in llm_calls),
            "completion_tokens": sum(_number(item.get("completion_tokens")) for item in llm_calls),
            "total_tokens": sum(_number(item.get("total_tokens")) for item in llm_calls),
            "cost": sum(_number(item.get("cost")) for item in llm_calls),
            "handcrafted_diff": {
                "flag_only": True,
                "note": "The handcrafted set is a review-prioritization flag, not a grade.",
                "counts": _diff_counts(diff_by_document.get(document_id, [])),
            },
        }
    total_cells = sum(item["formula_cells"] for item in rendered.values())
    total_complete = sum(item["expression_and_verbatim_citation"] for item in rendered.values())
    return {
        "schema_version": 1,
        "measurement": "m20_s14_form_completeness",
        "tax_year": int(year),
        "primary_metric": "expression_and_verbatim_citation_over_formula_cells",
        "handcrafted_expression_set": {
            "status": "review_flag_only",
            "note": "Disagreements are retained to direct human review; they are not scored as accuracy.",
        },
        "totals": {
            "formula_cells": total_cells,
            "expression_and_verbatim_citation": total_complete,
            "completeness_rate": total_complete / total_cells if total_cells else 0.0,
        },
        "by_document": rendered,
    }


def write_form_completeness_report(
    report: dict[str, Any],
    *,
    root: str | Path | None = None,
    output_path: str | Path | None = None,
) -> Path:
    """Write the completeness report as deterministic ASCII YAML."""
    root_path = Path(root).resolve() if root is not None else project_root()
    path = Path(output_path) if output_path is not None else root_path / "output" / "m20_s14_form_completeness.yaml"
    if not path.is_absolute():
        path = root_path / path
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(report, sort_keys=False, allow_unicode=False)
    text.encode("ascii")
    path.write_text(text, encoding="ascii", newline="\n")
    return path


def _load_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    value = load_yaml(path)
    return value if isinstance(value, dict) else {}


def _cell_refs(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "target_cell_id": str(item.get("target_cell_id", "")),
            "line_anchor": str(item.get("line_anchor", "")),
            "review_gap": str(item.get("review_gap", "")),
        }
        for item in cells
    ]


def _diff_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        category = str(row.get("category", "unknown"))
        counts[category] = counts.get(category, 0) + 1
    return dict(sorted(counts.items()))


def _number(value: Any) -> int | float:
    if isinstance(value, bool) or value is None:
        return 0
    try:
        return float(value) if isinstance(value, float) else int(value)
    except (TypeError, ValueError):
        return 0
