from __future__ import annotations

import asyncio
from pathlib import Path
import shutil

import pytest

from tax_graph.compile import build_sqlite
from tax_graph.intake import (
    ConsentRequiredError,
    DocumentCandidate,
    classify_document,
    classify_documents,
    load_relevance_layer,
    require_consent,
    route_documents,
    run_intake,
)
from tax_graph.intake.engine import build_gap_list
from tax_graph.io.loader import load_graph
from tax_graph.io.sqlite_loader import load_sqlite_graph
from tax_graph.mcp import build_mcp_server


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "intake_classifier"


@pytest.mark.m14
def test_classifier_fixture_corpus_is_deterministic_and_complete():
    expected = {
        "1099-b.txt": "1099_b",
        "1099-div.txt": "1099_div",
        "1099-int.txt": "1099_int",
        "1099-nec.txt": "1099_nec",
        "w2.txt": "w2",
    }
    actual = {
        path.name: classify_document(DocumentCandidate(path, path.read_text(encoding="utf-8"))).document_type
        for path in sorted(FIXTURES.glob("*.txt"))
    }
    assert actual == expected
    assert classify_document(
        DocumentCandidate(Path("unknown.txt"), "a random scanned page")
    ).confidence == 0.0


@pytest.mark.m14
def test_routing_and_both_direction_reconciliation_are_cited():
    layer = load_relevance_layer(root=ROOT)
    candidates = [
        DocumentCandidate(FIXTURES / "w2.txt", (FIXTURES / "w2.txt").read_text(encoding="utf-8")),
        DocumentCandidate(FIXTURES / "1099-nec.txt", (FIXTURES / "1099-nec.txt").read_text(encoding="utf-8")),
    ]
    classifications = classify_documents(candidates)
    routes = route_documents(classifications, layer)
    w2_route = next(route for route in routes if route.document_type == "w2")
    assert w2_route.target == "form_1040_2025_root_line_1a"
    assert w2_route.citation_refs == ("cite_intake_w2_recipient",)

    gaps = build_gap_list(
        classifications,
        layer,
        claims={"employee_status": True},
        resolutions={
            "trigger_filing_status": "single",
            "trigger_dependents": "no",
            "trigger_digital_asset": "no",
        },
        routes=routes,
    )
    assert any(gap["kind"] == "unsupported_document" for gap in gaps)
    assert any(gap["kind"] == "documents_without_claims" for gap in gaps)
    assert all("citation_refs" in gap for gap in gaps)


@pytest.mark.m14
def test_intake_inventory_has_one_route_per_box_and_one_trigger_per_item():
    layer = load_relevance_layer(root=ROOT)
    inventory_keys = {
        (document["document_type"], box["box_id"])
        for document in layer.inventory["information_returns"]
        for box in document["boxes"]
    }
    route_keys = {
        (route["source_document_type"], route["source_box"])
        for route in layer.routing_edges
    }
    assert route_keys == inventory_keys
    assert len(layer.routing_edges) == len(inventory_keys) == 90

    inventory_trigger_ids = {
        item["trigger_id"] for item in layer.inventory["trigger_items"]
    }
    assert {trigger["trigger_id"] for trigger in layer.triggers} == inventory_trigger_ids
    assert len(inventory_trigger_ids) == 12


@pytest.mark.m14
def test_intake_run_passes_only_after_universal_and_expectation_resolution(tmp_path):
    drop = tmp_path / "drop"
    drop.mkdir()
    shutil.copyfile(FIXTURES / "w2.txt", drop / "w2.txt")
    result = run_intake(
        drop,
        root=ROOT,
        claims={"employee_status": True},
        resolutions={
            "trigger_filing_status": "single",
            "trigger_dependents": "no",
            "trigger_digital_asset": "no",
        },
    )
    assert result.complete is True
    assert result.gaps == []
    assert result.resolutions[0]["provenance"] == "user asserted"


@pytest.mark.m14
def test_consent_fails_closed_and_configured_always_is_audited():
    with pytest.raises(ConsentRequiredError, match="consent required"):
        require_consent("configured_llm")
    receipt = require_consent("configured_llm", configured_mode="always")
    assert receipt.granted is True
    assert receipt.mode == "config"


@pytest.mark.m14
def test_intake_kinds_round_trip_through_sqlite(tmp_path):
    build_sqlite("2025", root=ROOT, build_dir=tmp_path)
    loaded = load_graph("2025", root=ROOT, include_extensions=False)
    compiled = load_sqlite_graph("2025", root=ROOT, db_path=tmp_path / "tax_graph_2025.sqlite")
    assert len(loaded.items("routing_edges")) == 90
    assert len(loaded.items("triggers")) == 12
    assert len(loaded.items("expectations")) == 4
    assert sorted(compiled.items("routing_edges"), key=lambda item: item["routing_id"]) == sorted(
        loaded.items("routing_edges"), key=lambda item: item["routing_id"]
    )
    assert sorted(compiled.items("triggers"), key=lambda item: item["trigger_id"]) == sorted(
        loaded.items("triggers"), key=lambda item: item["trigger_id"]
    )
    assert sorted(compiled.items("expectations"), key=lambda item: item["expectation_id"]) == sorted(
        loaded.items("expectations"), key=lambda item: item["expectation_id"]
    )


@pytest.mark.m14
def test_mcp_relevance_query_returns_citations_and_gap_gate():
    server = build_mcp_server(year="2025", root=ROOT, source="yaml")
    _content, relevance = asyncio.run(
        server.call_tool("get_intake_relevance", {"document_type": "w2", "source_box": "box_1"})
    )
    assert relevance["routing_edges"][0]["target"] == "form_1040_2025_root_line_1a"
    assert relevance["citations"][0]["citation_id"] == "cite_intake_w2_recipient"
    _content, gaps = asyncio.run(
        server.call_tool(
            "list_intake_gaps",
            {
                "documents": [{"path": "w2.txt", "document_type": "w2", "boxes": {"box_1": "50000"}}],
                "claims": {"employee_status": True},
                "resolutions": {
                    "trigger_filing_status": "single",
                    "trigger_dependents": "no",
                    "trigger_digital_asset": "no",
                },
            },
        )
    )
    assert gaps["complete"] is True
