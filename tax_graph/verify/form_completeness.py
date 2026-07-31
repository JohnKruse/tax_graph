"""Measure draft completeness against each form's deterministic outline.

This report is intentionally independent of the retired handcrafted expression
set. A formula cell is complete only when the outline pass attempted it, produced
an expression rule, and attached a verbatim form-face citation. Non-computed
physical controls are measured separately: they need a reasoned policy and a
verbatim form-face citation, not a formula expression. Instruction-page citations
augment both records but never gate completeness.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import yaml

from tax_graph.config import get_config_value, load_config, project_root
from tax_graph.extract.instruction_ownership import instruction_line_owners, instruction_span_ids_for_line
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
        background_controls = [
            item for item in stats.get("background_controls", [])
            if isinstance(item, dict)
        ]
        policy_controls = [
            item for item in background_controls
            if str(item.get("population_policy") or "") not in {"computed", "copied"}
        ]
        policy_complete = [
            item for item in policy_controls
            if item.get("has_policy") and str(item.get("population_policy") or "") != "unsupported"
        ]
        policy_with_form_face = [
            item for item in policy_complete
            if _has_form_face_citation(item)
        ]
        policy_origins = Counter(_policy_origin(item) for item in policy_controls)
        policy_derived = [item for item in policy_controls if _policy_origin(item) == "derived"]
        policy_defaulted = [item for item in policy_controls if _policy_origin(item) == "defaulted"]
        policy_authored = [item for item in policy_controls if _policy_origin(item) == "authored"]
        review_cells = _review_line_records(
            stats,
            _load_mapping(draft_dir / "outline.yaml"),
            document_id,
        )
        spans = _load_sequence(draft_dir / "candidate_spans.yaml")
        owners = instruction_line_owners(spans)
        instruction_before = sum(
            bool(item.get("instruction_span_ids"))
            for item in review_cells
        )
        instruction_cells = {
            str(item.get("target_cell_id")): instruction_span_ids_for_line(
                spans,
                str(item.get("line_anchor") or ""),
                owners=owners,
            )
            for item in review_cells
        }
        if spans:
            wrong_owner_count, wrong_owner_addresses = _wrong_owner_instruction_report(
                cells,
                spans,
                owners,
            )
        else:
            wrong_owner_count = int(stats.get("wrong_owner_instruction_span_count", 0))
            wrong_owner_addresses = sorted(
                set(str(item) for item in stats.get("wrong_owner_instruction_addresses", []))
            )
        form_face = [item for item in cells if _has_form_face_citation(item)]
        instruction_page = [
            item for item in review_cells
            if instruction_cells.get(str(item.get("target_cell_id")), [])
            or _has_instruction_citation(item)
        ]
        complete = [
            item for item in cells
            if item.get("has_expression")
            and _has_form_face_citation(item)
        ]
        with_expression_no_citation = [
            item for item in cells if item.get("status") == "expression_without_citation"
        ]
        gaps = [item for item in cells if item.get("status") == "review_gap"]
        metrics = _load_mapping(draft_dir / "metrics.yaml")
        llm_calls = [item for item in metrics.get("llm_calls", []) if isinstance(item, dict)]
        rendered[document_id] = {
            "formula_cells": len(cells),
            "policy_controls": len(policy_controls),
            "policy_controls_with_policy": len(policy_complete),
            "policy_and_form_face_citation": len(policy_with_form_face),
            "policy_coverage_rate": len(policy_complete) / len(policy_controls) if policy_controls else 0.0,
            "policy_and_form_face_citation_rate": len(policy_with_form_face) / len(policy_controls) if policy_controls else 0.0,
            "policy_derived": len(policy_derived),
            "policy_defaulted": len(policy_defaulted),
            "policy_authored": len(policy_authored),
            "policy_derived_and_form_face_citation": sum(
                _has_form_face_citation(item) for item in policy_derived
            ),
            "policy_defaulted_and_form_face_citation": sum(
                _has_form_face_citation(item) for item in policy_defaulted
            ),
            "policy_origin_counts": dict(sorted(policy_origins.items())),
            "policy_mix_before": dict(stats.get("background_policy_before", {})),
            "policy_mix_after": dict(stats.get("background_policy_after", {})),
            "policy_mix_after_by_origin": dict(stats.get("background_policy_after_by_origin", {})),
            "failover_class_counts": dict(stats.get("background_failover_class_counts", {})),
            "background_policy_before": dict(stats.get("background_policy_before", {})),
            "background_policy_after": dict(stats.get("background_policy_after", {})),
            "background_policy_progress": int(stats.get("background_policy_progress", 0)),
            "background_policy_review_gaps": _background_refs(
                [item for item in policy_controls if not item.get("has_policy")]
            ),
            "expression_and_verbatim_citation": len(complete),
            "expression_and_form_face_citation": sum(
                bool(item.get("has_expression")) and _has_form_face_citation(item)
                for item in cells
            ),
            "expression_and_instruction_page_citation": sum(
                bool(
                    item.get("has_expression")
                    and (
                        instruction_cells.get(str(item.get("target_cell_id")), [])
                        or _has_instruction_citation(item)
                    )
                )
                for item in cells
            ),
            "expression_and_both_citations": sum(
                bool(item.get("has_expression"))
                and _has_form_face_citation(item)
                and bool(
                    instruction_cells.get(str(item.get("target_cell_id")), [])
                    or _has_instruction_citation(item)
                )
                for item in cells
            ),
            "expression_without_citation": len(with_expression_no_citation),
            "neither_expression_nor_citation": len(gaps),
            "completeness_rate": len(complete) / len(cells) if cells else 0.0,
            "instruction_review_cells": len(review_cells),
            "instruction_page_citation_before": instruction_before,
            "instruction_page_citation": len(instruction_page),
            "instruction_page_citation_rate": len(instruction_page) / len(review_cells) if review_cells else 0.0,
            "instruction_page_citation_missing_cells": _cell_refs(
                [item for item in review_cells if not instruction_cells.get(str(item.get("target_cell_id")), [])]
            ),
            "expression_without_citation_cells": _cell_refs(with_expression_no_citation),
            "review_gaps": gaps,
            "wrong_owner_instruction_spans": wrong_owner_count,
            "wrong_owner_instruction_addresses": wrong_owner_addresses,
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
    total_policy_controls = sum(item["policy_controls"] for item in rendered.values())
    total_policy_complete = sum(item["policy_controls_with_policy"] for item in rendered.values())
    total_policy_with_form_face = sum(item["policy_and_form_face_citation"] for item in rendered.values())
    return {
        "schema_version": 1,
        "measurement": "m20_s20_form_completeness",
        "tax_year": int(year),
        "primary_metric": "expression_and_form_face_citation_over_formula_cells",
        "secondary_metric": "policy_and_form_face_citation_over_non_computed_controls",
        "handcrafted_expression_set": {
            "status": "review_flag_only",
            "note": "Disagreements are retained to direct human review; they are not scored as accuracy.",
        },
        "totals": {
            "formula_cells": total_cells,
            "policy_controls": total_policy_controls,
            "policy_controls_with_policy": total_policy_complete,
            "policy_and_form_face_citation": total_policy_with_form_face,
            "policy_coverage_rate": total_policy_complete / total_policy_controls if total_policy_controls else 0.0,
            "policy_and_form_face_citation_rate": total_policy_with_form_face / total_policy_controls if total_policy_controls else 0.0,
            "policy_derived": sum(item["policy_derived"] for item in rendered.values()),
            "policy_defaulted": sum(item["policy_defaulted"] for item in rendered.values()),
            "policy_authored": sum(item["policy_authored"] for item in rendered.values()),
            "policy_derived_and_form_face_citation": sum(
                item["policy_derived_and_form_face_citation"] for item in rendered.values()
            ),
            "policy_defaulted_and_form_face_citation": sum(
                item["policy_defaulted_and_form_face_citation"] for item in rendered.values()
            ),
            "policy_origin_counts": _sum_counts(
                item["policy_origin_counts"] for item in rendered.values()
            ),
            "policy_mix_before": _sum_counts(item["policy_mix_before"] for item in rendered.values()),
            "policy_mix_after": _sum_counts(item["policy_mix_after"] for item in rendered.values()),
            "policy_mix_after_by_origin": _sum_nested_counts(
                item["policy_mix_after_by_origin"] for item in rendered.values()
            ),
            "failover_class_counts": _sum_counts(item["failover_class_counts"] for item in rendered.values()),
            "expression_and_verbatim_citation": total_complete,
            "expression_and_form_face_citation": total_complete,
            "expression_and_both_citations": sum(
                item["expression_and_both_citations"] for item in rendered.values()
            ),
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
    path = Path(output_path) if output_path is not None else root_path / "output" / "m20_s20_form_completeness.yaml"
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


def _load_sequence(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    value = load_yaml(path)
    return [item for item in value or [] if isinstance(item, dict)]


def _review_line_records(stats: dict[str, Any], outline: dict[str, Any], document_id: str) -> list[dict[str, Any]]:
    """Return formula, source, and deterministic line records for instruction coverage."""
    records = [
        item
        for key in ("formula_cells", "non_formula_cells")
        for item in stats.get(key, [])
        if isinstance(item, dict)
    ]
    if document_id != "form_1040_2025" or not isinstance(outline, dict):
        return records
    seen = {str(item.get("line_anchor") or "").lower() for item in records}
    for item in _outline_lines(outline.get("children", []) or []):
        if item.get("kind") != "line" or not item.get("line_anchor"):
            continue
        anchor = str(item["line_anchor"]).lower()
        if not any(char.isdigit() for char in anchor) or anchor in seen:
            continue
        records.append({
            "target_cell_id": f"{document_id}_root_line_{anchor}",
            "line_anchor": anchor,
            "status": "review_gap",
            "instruction_span_ids": [],
        })
        seen.add(anchor)
    return records


def _outline_lines(items: list[Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        result.append(item)
        result.extend(_outline_lines(item.get("children", []) or []))
    return result


def _has_form_face_citation(item: dict[str, Any]) -> bool:
    return bool(item.get("has_form_face_citation", item.get("has_verbatim_citation")))


def _has_instruction_citation(item: dict[str, Any]) -> bool:
    return bool(item.get("has_instruction_citation") or item.get("instruction_span_ids"))


def _policy_origin(item: dict[str, Any]) -> str:
    """Return the explicit origin, with a conservative legacy-draft fallback."""
    origin = str(item.get("policy_origin") or "")
    if origin in {"authored", "derived", "defaulted", "review_gap"}:
        return origin
    if not item.get("has_policy") or str(item.get("population_policy") or "") == "unsupported":
        return "review_gap"
    if str(item.get("status") or "") == "authored":
        return "authored"
    return "derived"


def _sum_counts(values: Iterable[dict[str, Any]]) -> dict[str, int]:
    result: Counter[str] = Counter()
    for value in values:
        result.update({str(key): int(count) for key, count in (value or {}).items()})
    return dict(sorted(result.items()))


def _sum_nested_counts(values: Iterable[dict[str, dict[str, Any]]]) -> dict[str, dict[str, int]]:
    result: dict[str, Counter[str]] = {}
    for value in values:
        for origin, policies in (value or {}).items():
            result.setdefault(str(origin), Counter()).update({
                str(key): int(count) for key, count in (policies or {}).items()
            })
    return {
        origin: dict(sorted(policies.items()))
        for origin, policies in sorted(result.items())
    }


def _wrong_owner_instruction_report(
    cells: list[dict[str, Any]],
    spans: list[dict[str, Any]],
    owners: dict[str, frozenset[str]],
) -> tuple[int, list[str]]:
    """Re-measure mention-only candidates against the current owner map."""
    if not spans:
        return 0, []
    total = 0
    addresses: set[str] = set()
    for cell in cells:
        anchor = str(cell.get("line_anchor") or "").lower()
        if not anchor:
            continue
        phrase = f"line {anchor}"
        for span in spans:
            if str(span.get("relationship") or "") == "source":
                continue
            text = str(span.get("text") or "")
            lowered = text.lower()
            if phrase not in lowered or not _direct_line_evidence(lowered):
                continue
            span_id = str(span.get("span_id") or "")
            owned = {str(value).lower() for value in owners.get(span_id, ())}
            if owned and anchor not in owned:
                total += 1
                addresses.add(str(cell.get("target_cell_id") or ""))
    return total, sorted(addresses)


def _direct_line_evidence(text: str) -> bool:
    return any(token in text for token in ("enter", "report", "include", "combine", "total", "add", "subtract"))


def _cell_refs(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "target_cell_id": str(item.get("target_cell_id", "")),
            "line_anchor": str(item.get("line_anchor", "")),
            "review_gap": str(item.get("review_gap", "")),
        }
        for item in cells
    ]


def _background_refs(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return unresolved physical controls without hiding their reason."""
    return [
        {
            "field_name": str(item.get("field_name") or ""),
            "address_id": str(item.get("address_id") or ""),
            "label": str(item.get("label") or ""),
            "review_gap": str(item.get("review_gap") or "policy is unresolved"),
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
