"""M20-S108 regressions for outbound-flow repair and batch isolation."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import tax_graph.extract.pipeline as pipeline
from tax_graph.extract.models import RoutedDrafts
from tax_graph.extract.micro import formula_micro_schema
from tax_graph.extract.outline import build_candidate_spans, build_outline_tree, build_outbound_flows
from tax_graph.extract.outline_checks import run_outline_artifact_checks
from tax_graph.extract.inputs import load_document_input


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.m20
def test_formula_micro_schema_matches_strict_structured_output_contract() -> None:
    """Guard every formula response object against the provider schema contract."""
    schema = formula_micro_schema(root=ROOT)
    forbidden = {"allOf", "if", "then", "else", "not", "$ref"}

    def visit(value: object, path: str, *, root: bool = False) -> None:
        assert isinstance(value, dict), path
        assert not (set(value) & forbidden), path
        if root:
            assert value.get("type") == "object", path
        properties = value.get("properties")
        if isinstance(properties, dict):
            required = value.get("required")
            assert isinstance(required, list), path
            assert set(properties) == set(required), path
            for optional_name in ("role", "value_type"):
                if optional_name in properties:
                    optional_schema = properties[optional_name]
                    assert isinstance(optional_schema, dict), path
                    optional_types = optional_schema.get("type")
                    assert isinstance(optional_types, list) and "null" in optional_types, path
            for name, child in properties.items():
                visit(child, f"{path}.properties.{name}")
        items = value.get("items")
        if isinstance(items, dict):
            visit(items, f"{path}.items")
        alternatives = value.get("anyOf")
        if isinstance(alternatives, list):
            for index, child in enumerate(alternatives):
                visit(child, f"{path}.anyOf[{index}]")

    visit(schema, "schema", root=True)


@pytest.mark.m20
def test_form_8949_outbound_flows_use_current_geometry_outline_ids() -> None:
    document = load_document_input("form_8949_2025", year="2025", root=ROOT)
    outline = build_outline_tree(document)
    spans = build_candidate_spans(document)
    flows = build_outbound_flows(document, outline=outline, spans=spans)

    report = run_outline_artifact_checks(document, outline, spans, flows)

    assert report.ok, [issue.reason for issue in report.issues]
    by_target = {flow.target_line: flow for flow in flows}
    assert by_target["1b"].source_outline_id in {
        node.outline_id
        for node in outline.children[1].children
    }
    assert by_target["8b"].source_outline_id in {
        node.outline_id
        for node in outline.children[2].children
    }
    assert by_target["1b"].source_node_id.endswith("_column_h")
    assert by_target["8b"].source_node_id.endswith("_column_h")


@pytest.mark.m20
def test_extract_year_records_one_document_failure_and_continues(tmp_path, monkeypatch) -> None:
    entries = [
        SimpleNamespace(document_id="good_a_2025", kind="schedule"),
        SimpleNamespace(document_id="bad_2025", kind="tax_form"),
        SimpleNamespace(document_id="good_b_2025", kind="schedule"),
    ]
    manifest = SimpleNamespace(tax_year=2025, documents=entries)
    calls: list[str] = []

    def fake_extract_document(document_id: str, **kwargs) -> RoutedDrafts:
        calls.append(document_id)
        if document_id == "bad_2025":
            raise RuntimeError("synthetic outline failure")
        return RoutedDrafts(accepted=[], review=[], issues=[], output_dir=tmp_path / document_id)

    monkeypatch.setattr(pipeline, "load_manifest", lambda **kwargs: manifest)
    monkeypatch.setattr(pipeline, "extract_document", fake_extract_document)
    monkeypatch.setattr(pipeline, "_write_batch_verification_sidecars", lambda **kwargs: None)

    routed = pipeline.extract_year(
        year="2025",
        root=tmp_path,
        client=object(),
        config={"extraction": {"max_docs_per_run": 20}},
    )

    assert calls == ["good_a_2025", "bad_2025", "good_b_2025"]
    assert len(routed) == 3
    failure = routed[1]
    assert failure.micro_stats["status"] == "failed"
    assert failure.issues[0].object_id == "bad_2025"
    assert "synthetic outline failure" in failure.issues[0].reason
    assert routed[2].output_dir.name == "good_b_2025"
