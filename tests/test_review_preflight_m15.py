"""Fail-closed preflight and coverage tests for M15 S6."""

from __future__ import annotations

import copy
from dataclasses import replace
from pathlib import Path

import pytest

from workbench.artifacts import ArtifactBundle, load_artifact_bundle
from workbench.manifest import build_manifest
from workbench.preflight import PreflightError, preflight_manifest, run_preflight


ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    not (ROOT / "graph" / "2025" / "_drafts").exists(),
    reason="live review drafts are required: fresh checkouts (CI) carry no _drafts",
)


@pytest.fixture(scope="module")
def artifacts() -> tuple[dict[str, object], ArtifactBundle]:
    return build_manifest(ROOT, 2025), load_artifact_bundle(ROOT, 2025)


@pytest.mark.m15
def test_real_2025_preflight_passes_with_all_coverage_dimensions() -> None:
    report = run_preflight(ROOT, 2025)

    assert report["entries"] > 0
    assert report["units"] >= report["entries"]
    assert set(report) == {
        "entries", "units", "by_kind", "by_document", "by_object", "by_geometry",
        "by_display_name_provenance", "legacy_mined_by_document", "queue", "derived",
        "divergence_findings",
    }
    assert report["by_geometry"]["located"] > 0
    assert report["by_geometry"]["unlocated"] > 0
    assert report["by_display_name_provenance"]["legacy_mined"] > 0
    assert sum(report["legacy_mined_by_document"].values()) == report["by_display_name_provenance"]["legacy_mined"]
    assert report["queue"]["units"] == report["units"]
    assert report["derived"]["denominator"] == 1921
    assert report["derived"]["states"] == {"unreviewed": 1921, "approved": 0, "needs_recheck": 0}
    assert report["derived"]["blast_radius"]["invalidated"] == 0
    assert report["divergence_findings"] == []


@pytest.mark.m15
def test_seeded_bad_artifacts_fail_every_section_four_condition_actionably(
    artifacts: tuple[dict[str, object], ArtifactBundle],
) -> None:
    original_manifest, original_bundle = artifacts

    manifest = copy.deepcopy(original_manifest)
    manifest["entries"][0]["units"] = []
    _assert_code(manifest, original_bundle, "zero_units")

    graph_objects = dict(original_bundle.graph.objects_by_kind)
    decision = next(
        item for item in graph_objects["decisions"]
        if item.get("decision_id") == "decision_1040_deduction_method"
    )
    graph_objects["decisions"] = (*graph_objects["decisions"], copy.deepcopy(decision))
    _assert_code(original_manifest, _with_graph(original_bundle, graph_objects), "ambiguous_object")

    geometry = copy.deepcopy(original_bundle.geometry)
    geometry["entries"].append(copy.deepcopy(geometry["entries"][0]))
    _assert_code(original_manifest, replace(original_bundle, geometry=geometry), "ambiguous_geometry")

    graph_objects = dict(original_bundle.graph.objects_by_kind)
    graph_objects["rules"] = (*graph_objects["rules"], {"rule_id": "bad_rule", "operation": "MYSTERY"})
    _assert_code(original_manifest, _with_graph(original_bundle, graph_objects), "missing_formatter")

    queue = copy.deepcopy(original_bundle.review_queue)
    promotion = next(item for item in queue["entries"] if item.get("kind") == "promotion_review")
    promotion["review_scope"]["object_refs"] = []
    promotion["changed_object_ids"] = []
    _assert_code(original_manifest, replace(original_bundle, review_queue=queue), "promotion_scope_missing")

    queue = copy.deepcopy(original_bundle.review_queue)
    field_map = next(item for item in queue["entries"] if item.get("kind") == "field_map_review")
    field_map["review_scope"]["object_refs"].pop(0)
    _assert_code(original_manifest, replace(original_bundle, review_queue=queue), "field_map_incomplete")

    graph_objects = dict(original_bundle.graph.objects_by_kind)
    citations = [copy.deepcopy(item) for item in graph_objects["citations"]]
    citation = next(item for item in citations if item.get("citation_id") == "cite_1040_standard_deduction")
    citation.pop("locator", None)
    graph_objects["citations"] = tuple(citations)
    _assert_code(original_manifest, _with_graph(original_bundle, graph_objects), "citation_unresolved")

    manifest = copy.deepcopy(original_manifest)
    located_units = [
        unit
        for entry in manifest["entries"]
        for unit in entry["units"]
        if unit.get("official_location")
        and unit.get("address_id")
        and unit.get("field_name")
        and unit.get("display_name_provenance") != "legacy_mined"
    ]
    first = located_units[0]
    second = next(
        unit for unit in located_units
        if unit["official_location"]["document_id"] == first["official_location"]["document_id"]
        and unit.get("address_id") != first.get("address_id")
    )
    second["display_name"] = first["display_name"]
    second["official_locator"] = first["official_locator"]
    _assert_code(manifest, original_bundle, "ambiguous_display_name")

    manifest = copy.deepcopy(original_manifest)
    authored = next(
        unit for entry in manifest["entries"] for unit in entry["units"]
        if unit.get("display_name_provenance") == "authored_address"
    )
    authored["display_name"] = "Official caption - f1_92"
    _assert_code(manifest, original_bundle, "invalid_display_name")


def _with_graph(bundle: ArtifactBundle, objects: dict[str, tuple[dict[str, object], ...]]) -> ArtifactBundle:
    return replace(bundle, graph=replace(bundle.graph, objects_by_kind=objects))


def _assert_code(manifest: dict[str, object], bundle: ArtifactBundle, code: str) -> None:
    with pytest.raises(PreflightError) as caught:
        preflight_manifest(manifest, bundle)
    assert any(issue.code == code for issue in caught.value.issues), str(caught.value)
    assert code in str(caught.value)
