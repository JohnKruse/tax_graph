from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.engine import Engine, Graph, load_facts, load_facts_document
from tax_graph.record import build_return_record, validate_decision_resolutions


ROOT = Path(__file__).resolve().parents[1]
FACTS_PATH = ROOT / "examples" / "capital_gains_basic" / "facts.yaml"
TARGET = "form_1040_2025_line_7_capital_gain_loss"

pytestmark = pytest.mark.m5


def test_return_record_builder_is_deterministic_and_complete():
    graph = Graph("2025", root=ROOT, source="yaml")
    facts_document = load_facts_document(FACTS_PATH)
    result = Engine(graph).execute(load_facts(FACTS_PATH))
    resolutions = {
        "resolutions": [
            {
                "decision_id": "decision_8949_adjustments",
                "chosen_option_id": "none",
                "rationale": "Broker statement shows a simple covered long-term lot with no adjustment code.",
                "decided_by": "test_filer",
                "decided_date": "2026-07-05",
            }
        ]
    }

    record = build_return_record(
        facts_document=facts_document,
        result=result,
        graph=graph,
        decision_resolutions=resolutions,
        tax_graph_version="test-version",
        generated_date="2026-07-05",
        target_node=TARGET,
    )
    payload = record.to_dict()

    assert payload["metadata"] == {
        "tax_year": 2025,
        "filing_status": "single",
        "generated_date": "2026-07-05",
        "tax_graph_version": "test-version",
        "target_node": TARGET,
    }
    assert payload["facts"][0]["node_id"] == "form_1099b_2025_box_1d_proceeds"
    assert payload["facts"][0]["source"]["document_label"] == "Sample broker 1099-B (fake)"
    assert payload["decisions"][0]["chosen_option_id"] == "none"
    assert payload["decisions"][0]["citations"][0]["citation_id"] == "cite_8949_adjustment_codes"
    assert payload["outputs"] == [
        {
            "node_id": TARGET,
            "label": "Form 1040, line 7 - Capital gain or (loss)",
            "kind": "computed",
            "value": 2000,
            "operation": "COPY",
            "rule": "copy_currency_value",
            "citations": ["cite_schedule_d_16_to_1040_7"],
        }
    ]
    assert any(entry["operation"] == "SUBTRACT" for entry in payload["trace_summary"])
    assert payload["carryforward_block"]["carryforwards"] == []
    assert payload["unsupported"] == []


def test_decision_resolution_references_must_exist():
    graph = Graph("2025", root=ROOT, source="yaml")

    with pytest.raises(ValueError, match="unknown decision_id"):
        validate_decision_resolutions(
            {
                "resolutions": [
                    {
                        "decision_id": "decision_missing",
                        "chosen_option_id": "none",
                        "rationale": "No adjustment.",
                        "decided_by": "test_filer",
                        "decided_date": "2026-07-05",
                    }
                ]
            },
            graph,
        )

    with pytest.raises(ValueError, match="unknown option_id"):
        validate_decision_resolutions(
            {
                "resolutions": [
                    {
                        "decision_id": "decision_8949_adjustments",
                        "chosen_option_id": "missing_option",
                        "rationale": "No adjustment.",
                        "decided_by": "test_filer",
                        "decided_date": "2026-07-05",
                    }
                ]
            },
            graph,
        )
