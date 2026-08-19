"""M20-S113 guards for model-owned classification and grounded outcomes."""

from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.extract.assembly import assemble_formula_plan
from tax_graph.extract.micro import (
    MicroExtractionError,
    _formula_prompt,
    formula_micro_schema,
    validate_formula_plan,
)
from tax_graph.extract.models import SourceDocumentInput
from tax_graph.extract.outline import CandidateSpan, OutlineNode
from tax_graph.extract.outline_pipeline import (
    _model_formula_outline_nodes,
    _record_routing_agreement,
    _record_union_non_computation,
)


ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.m20


def _span(span_id: str = "span_form") -> CandidateSpan:
    return CandidateSpan(
        span_id,
        "form_1040_2025",
        "source",
        "page 1, line 35a",
        "35a Amount of line 34 you want refunded to you",
    )


def _union_base(kind: str) -> dict[str, object]:
    return {
        "kind": kind,
        "operation": None,
        "source_lines": None,
        "question": None,
        "options": None,
        "form": None,
        "line": None,
        "box": None,
        "reason": None,
        "quote": _span().text,
    }


def test_formula_union_enumerates_all_branches_and_requires_all_fields() -> None:
    schema = formula_micro_schema(root=ROOT)

    assert set(schema["properties"]) == set(schema["required"])
    assert schema["properties"]["kind"]["enum"] == [
        "computation",
        "filer_entry",
        "election",
        "information_return",
        "not_derivable",
    ]
    option_schema = schema["properties"]["options"]["items"]
    assert set(option_schema["properties"]) == set(option_schema["required"])
    assert option_schema["properties"]["option_type"]["enum"] == ["choice", "escalate"]


@pytest.mark.parametrize("kind", ("filer_entry", "information_return", "not_derivable"))
def test_non_computation_branches_are_grounded_terminal_outcomes(kind: str) -> None:
    plan = _union_base(kind)
    if kind == "information_return":
        plan.update({"form": "W-2", "box": "1"})
    elif kind == "not_derivable":
        plan["reason"] = "The supplied evidence does not establish the applicable amount."

    validate_formula_plan(plan, spans=[_span()], root=ROOT)


def test_filer_entry_preserves_a_named_information_return_source() -> None:
    plan = _union_base("filer_entry")
    plan.update({"form": "W-2", "line": "1a", "box": "1"})

    validate_formula_plan(plan, spans=[_span()], root=ROOT)

    document = SourceDocumentInput(
        document_id="form_1040_2025",
        kind="tax_form",
        year="2025",
        url="https://example.test/form-1040.pdf",
        text=_span().text,
        text_path=ROOT / "tests" / "fixtures" / "form_1040.txt",
    )
    stats = {
        "review_gaps": [],
        "outcomes": [],
        "outcome_counts": {"filer_entry": 0, "election": 0, "information_return": 0, "not_derivable": 0},
        "non_formula_cells": [],
        "resolved_source_addresses": [],
    }
    cell = {"target_cell_id": "cell_1a", "line_anchor": "1a", "label": "W-2 box 1"}
    _record_union_non_computation(
        document,
        OutlineNode("root_line_1a", "line", _span().text, line_anchor="1a"),
        plan,
        [_span()],
        line_index={},
        stats=stats,
        cell=cell,
    )

    assert stats["outcomes"][0]["form"] == "W-2"
    assert stats["outcomes"][0]["line"] == "1a"
    assert stats["outcomes"][0]["box"] == "1"
    assert stats["outcomes"][0]["resolved_source_id"] == "filer_entry"


def test_election_requires_escalation_and_supplied_citations() -> None:
    plan = _union_base("election")
    plan.update(
        {
            "question": "Where should the overpayment go?",
            "options": [
                {
                    "label": "Refund it",
                    "downstream_effect": "Pay the overpayment to the filer.",
                    "citation_refs": ["span_form"],
                    "option_type": "choice",
                }
            ],
        }
    )

    with pytest.raises(MicroExtractionError, match="escalate"):
        validate_formula_plan(plan, spans=[_span()], root=ROOT)

    plan["options"].append(
        {
            "label": "Escalate",
            "downstream_effect": "Ask a human before choosing.",
            "citation_refs": ["span_form"],
            "option_type": "escalate",
        }
    )
    validate_formula_plan(plan, spans=[_span()], root=ROOT)

    plan["options"][0]["citation_refs"] = ["span_missing"]
    with pytest.raises(MicroExtractionError, match="supplied evidence"):
        validate_formula_plan(plan, spans=[_span()], root=ROOT)


def test_prompt_requires_grounding_and_exposes_cues_as_examples() -> None:
    prompt = _formula_prompt(
        OutlineNode("root_line_35a", "line", _span().text, line_anchor="35a"),
        [_span()],
    )

    assert "Answer only from the supplied evidence" in prompt
    assert "return kind not_derivable" in prompt
    assert "these phrases are not routing rules" in prompt
    assert "span_form" in prompt


def test_election_assembly_emits_decision_without_copy_rule() -> None:
    document = SourceDocumentInput(
        document_id="form_1040_2025",
        kind="tax_form",
        year="2025",
        url="https://example.test/form-1040.pdf",
        text=_span().text,
        text_path=ROOT / "tests" / "fixtures" / "form_1040.txt",
    )
    node = OutlineNode("root_line_35a", "line", _span().text, line_anchor="35a")
    instruction = CandidateSpan(
        "span_instruction",
        "instructions_form_1040_2025",
        "instructions",
        "page 20, line 35a",
        "Choose whether to receive the overpayment or apply it to estimated tax.",
    )
    plan = _union_base("election")
    plan.update(
        {
            "question": "Do you want a refund or estimated tax credit?",
            "options": [
                {
                    "label": "Receive a refund",
                    "downstream_effect": "The overpayment is refunded.",
                    "citation_refs": ["span_form", "span_instruction"],
                    "option_type": "choice",
                },
                {
                    "label": "Escalate",
                    "downstream_effect": "Ask the filer before choosing.",
                    "citation_refs": ["span_form"],
                    "option_type": "escalate",
                },
            ],
        }
    )

    batch = assemble_formula_plan(document, node, plan, [_span(), instruction], model="test-model")

    assert batch.items("rules") == []
    assert batch.items("edges") == []
    assert len(batch.items("decisions")) == 1
    assert {item["option_type"] for item in batch.items("decisions")[0].data["options"]} == {
        "choice",
        "escalate",
    }


def test_model_node_set_is_wider_than_legacy_cue_set() -> None:
    nodes = [
        OutlineNode("line_1", "line", "Enter an amount.", line_anchor="1"),
        OutlineNode("line_2", "line", "Add lines 1 and 1.", line_anchor="2"),
        OutlineNode("header", "section", "Section", children=[]),
    ]

    selected = _model_formula_outline_nodes(nodes)
    assert [node.outline_id for node in selected] == ["line_1", "line_2"]


def test_routing_agreement_records_all_four_quadrants() -> None:
    stats = {
        "routing_agreement": {
            "quadrants": {
                "matcher_admitted_model_computation": {"count": 0, "cells": []},
                "matcher_admitted_model_non_computation": {"count": 0, "cells": []},
                "matcher_skipped_model_computation": {"count": 0, "cells": []},
                "matcher_skipped_model_non_computation": {"count": 0, "cells": []},
            },
            "unclassified": [],
        }
    }
    _record_routing_agreement(stats, OutlineNode("line_1", "line", "Add line 2", line_anchor="1"), "computation")
    _record_routing_agreement(stats, OutlineNode("line_2", "line", "Enter an amount", line_anchor="2"), "filer_entry")
    _record_routing_agreement(stats, OutlineNode("line_3", "line", "Amount of line 4", line_anchor="3"), "election")
    _record_routing_agreement(stats, OutlineNode("line_4", "line", "Name", line_anchor="4"), "not_derivable")
    _record_routing_agreement(stats, OutlineNode("line_5", "line", "Total income", line_anchor="5"), "computation")

    counts = {
        name: value["count"]
        for name, value in stats["routing_agreement"]["quadrants"].items()
    }
    assert counts == {
        "matcher_admitted_model_computation": 1,
        "matcher_admitted_model_non_computation": 1,
        "matcher_skipped_model_computation": 1,
        "matcher_skipped_model_non_computation": 2,
    }


def test_declines_are_outcomes_and_never_review_gaps() -> None:
    document = SourceDocumentInput(
        document_id="form_1040_2025",
        kind="tax_form",
        year="2025",
        url="https://example.test/form-1040.pdf",
        text=_span().text,
        text_path=ROOT / "tests" / "fixtures" / "form_1040.txt",
    )
    stats = {
        "review_gaps": [],
        "outcomes": [],
        "outcome_counts": {
            "filer_entry": 0,
            "election": 0,
            "information_return": 0,
            "not_derivable": 0,
        },
        "non_formula_cells": [],
        "resolved_source_addresses": [],
    }
    for kind, extra in (
        ("filer_entry", {}),
        ("information_return", {"form": "W-2", "box": "1"}),
        ("not_derivable", {"reason": "The packet omits the filing status."}),
    ):
        plan = _union_base(kind)
        plan.update(extra)
        cell = {"target_cell_id": f"cell_{kind}", "line_anchor": "35a", "label": "Input"}
        _record_union_non_computation(
            document,
            OutlineNode("root_line_35a", "line", _span().text, line_anchor="35a"),
            plan,
            [_span()],
            line_index={},
            stats=stats,
            cell=cell,
        )

    assert stats["review_gaps"] == []
    assert stats["outcome_counts"] == {
        "filer_entry": 1,
        "election": 0,
        "information_return": 1,
        "not_derivable": 1,
    }
    assert {item["kind"] for item in stats["outcomes"]} == {
        "filer_entry",
        "information_return",
        "not_derivable",
    }
