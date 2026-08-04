"""M20-S52 tests for explicit incomplete-cell payloads."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from tax_graph.engine import (
    Engine,
    Graph,
    Result,
    build_incomplete_cell_payload,
    frontier_text_coverage,
    load_facts,
)
from tax_graph.mcp import build_mcp_server
from tax_graph.output.session import export_filing_bundle


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]
FACTS = ROOT / "examples" / "capital_gains_basic" / "facts.yaml"


def test_frontier_execution_emits_evidence_bearing_incomplete_cells() -> None:
    graph = Graph("2025", root=ROOT, source="yaml")
    result = Engine(graph).execute(load_facts(FACTS))

    by_frontier = {item["frontier_id"]: item for item in result.incomplete_cells}
    assert set(by_frontier) == {
        "deferred_schedule_1_2025_student_loan_interest_deduction_worksheet",
        "deferred_schedule_d_2025_28_rate_gain_worksheet",
        "deferred_schedule_d_2025_unrecaptured_1250_worksheet",
    }
    student_loan = by_frontier["deferred_schedule_1_2025_student_loan_interest_deduction_worksheet"]
    assert student_loan["canonical_address"] == "2025/document=schedule_1/line=21/control=amount"
    assert student_loan["printed_label"] == "Line 21: Student loan interest deduction 21"
    assert student_loan["reason"] == "reference_not_in_corpus"
    assert student_loan["operation"] == "NOT_COMPUTED_CALLER_MUST_RESOLVE"
    assert "caller must resolve" in student_loan["operation_statement"]

    rate_gain = by_frontier["deferred_schedule_d_2025_28_rate_gain_worksheet"]
    assert rate_gain["instruction_text"].startswith("If you checked 'Yes'")
    assert rate_gain["instruction_citation_refs"] == ["cite_schedule_d_line18_28pct"]
    assert result.trace[rate_gain["node_id"]]["incomplete_cell"] == rate_gain


def test_incomplete_payload_supports_the_future_approval_gate() -> None:
    graph = Graph("2025", root=ROOT, source="yaml")

    payload = build_incomplete_cell_payload(
        graph,
        "schedule_d_2025_line_18",
        reason="not_approved",
    )

    assert payload["reason"] == "not_approved"
    assert payload["printed_label"].startswith("Schedule D, line 18")
    assert payload["canonical_address"] == "2025/document=schedule_d/line=18/control=amount"
    assert payload["operation"] == "NOT_COMPUTED_CALLER_MUST_RESOLVE"

    with pytest.raises(ValueError, match="unsupported incomplete-cell reason"):
        build_incomplete_cell_payload(graph, "schedule_d_2025_line_18", reason="guessed")


def test_frontier_label_coverage_reports_acquisition_gaps() -> None:
    coverage = frontier_text_coverage(Graph("2025", root=ROOT, source="yaml"))

    assert coverage["total"] == 89
    assert coverage["with_printed_label"] == 12
    assert coverage["without_printed_label"] == 77
    assert "deferred_form_1040_2025_total_tax_chain" in coverage["missing_frontier_ids"]


def test_mcp_exposes_incomplete_cells_separately_from_missing_inputs() -> None:
    server = build_mcp_server(year="2025", root=ROOT, source="yaml")
    facts = load_facts(FACTS)
    _content, response = asyncio.run(server.call_tool("execute_tax_tree", {"facts": facts}))

    assert response["missing_required_inputs"] == []
    assert len(response["incomplete_cells"]) == 3
    assert all(item["reason"] == "reference_not_in_corpus" for item in response["incomplete_cells"])


def test_filing_bundle_persists_incomplete_cells_inside_bundle_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {"node_id": "test_node", "reason": "not_approved", "operation": "NOT_COMPUTED_CALLER_MUST_RESOLVE"}
    result = Result(incomplete_cells=[payload])
    project_root = tmp_path / "project"
    return_root = tmp_path / "return"
    return_root.mkdir(parents=True)

    monkeypatch.setattr("tax_graph.output.session.used_form_ids", lambda *_args, **_kwargs: ())
    monkeypatch.setattr(
        "tax_graph.output.session.write_ots_sidecar",
        lambda *_args, **_kwargs: {"scenario": return_root / "ots" / "scenario.json"},
    )

    manifest = export_filing_bundle(
        facts_document={"tax_year": 2025, "facts": []},
        result=result,
        year="2025",
        project_root=project_root,
        return_root=return_root,
    )

    assert manifest["incomplete_cells"] == [payload]
    saved = json.loads((return_root / "bundle.json").read_text(encoding="utf-8"))
    assert saved["incomplete_cells"] == [payload]
