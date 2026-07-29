"""Local Flask API tests for M15 S7."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from workbench.server import create_app


ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    not (ROOT / "graph" / "2025" / "_drafts").exists(),
    reason="live review drafts are required: fresh checkouts (CI) carry no _drafts",
)


@pytest.fixture(scope="module")
def client():
    app = create_app(ROOT, 2025, write_token="test-write-token")
    app.config.update(TESTING=True)
    return app.test_client()


@pytest.mark.m15
def test_derived_api_groups_pending_entries_and_reports_progress(client) -> None:
    response = client.get("/api/queue")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["tax_year"] == 2025
    assert len(payload["manifest_hash"]) == 64
    assert payload["progress"]["total_entries"] == 18
    assert payload["progress"]["remaining_entries"] == 18
    assert payload["progress"]["total_units"] == payload["coverage"]["units"]
    assert payload["groups"] == sorted(payload["groups"], key=lambda group: group["review_kind"])
    assert all(group["entries"] for group in payload["groups"])


@pytest.mark.m15
def test_derived_api_projects_deterministic_document_checklists(client) -> None:
    payload = client.get("/api/queue").get_json()
    documents = payload["documents"]

    assert documents == sorted(
        documents,
        key=lambda item: (item["document_id"] == "unlocated", item["title"], item["document_id"]),
    )
    assert any(item["title"] == "Form 1040" for item in documents)
    assert all(item["check_groups"] for item in documents)
    assert all("_" not in group["label"] for item in documents for group in item["check_groups"])
    projected = [
        (ref["queue_id"], ref["unit_id"])
        for item in documents
        for group in item["check_groups"]
        for ref in group["unit_refs"]
    ]
    assert len(projected) == payload["progress"]["total_units"]
    assert len(projected) == len(set(projected))
    assert sum(item["counts"]["required"] for item in documents) == sum(
        entry["required_units"] for group in payload["groups"] for entry in group["entries"]
    )


@pytest.mark.m15
def test_derived_entry_api_returns_only_the_requested_scoped_units(client) -> None:
    queue = client.get("/api/queue").get_json()
    selected = queue["groups"][0]["entries"][0]

    response = client.get(f"/api/entries/{selected['queue_id']}")
    missing = client.get("/api/entries/not_a_queue_id")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["entry"]["queue_id"] == selected["queue_id"]
    assert len(payload["entry"]["units"]) == selected["unit_count"]
    assert all(unit["queue_id"] == selected["queue_id"] for unit in payload["entry"]["units"])
    assert missing.status_code == 404
    assert missing.get_json()["error"] == "unknown queue_id"


@pytest.mark.m15
def test_form_1040_first_name_has_canonical_reviewer_language(client) -> None:
    payload = client.get("/api/entries/form_1040_2025").get_json()
    unit = next(
        item for item in payload["entry"]["units"]
        if item.get("field_name") == "topmostSubform[0].Page1[0].f1_14[0]"
    )

    assert unit["display_name"] == "First name and middle initial"
    assert unit["population_policy"] == "user_entered"
    assert "filer-entered fact" in unit["review_prompt"]
    assert "f1_14" not in unit["display_name"]
    assert unit["display_name_provenance"] == "authored_address"
    assert "f1_14" not in unit["official_locator"]


@pytest.mark.m15
def test_representative_units_never_use_raw_field_names_as_display_names(client) -> None:
    manifest = client.application.config["WORKBENCH_MANIFEST"]
    units = [unit for entry in manifest["entries"] for unit in entry["units"]]
    representatives = [
        next(unit for unit in units if unit.get("identity_slot") == "taxpayer_first_name"),
        next(unit for unit in units if unit.get("address_id") == "2025/document=form_1040/line=1a/control=amount"),
        next(unit for unit in units if unit.get("address_id") == "2025/document=form_1040/line=1h/control=description"),
        next(unit for unit in units if unit.get("address_id") == "2025/document=form_1040/line=1h/control=amount"),
        next(
            unit for unit in units
            if unit.get("address_id")
            == "2025/document=form_8949/table=part_i_line_1/row_template=transaction/column=d"
        ),
        next(
            unit for unit in units
            if unit.get("address_id")
            == "2025/document=form_8949/table=part_i_line_2/row_template=total/column=h"
        ),
        next(unit for unit in units if unit.get("repeatable", {}).get("row_slot") == 1),
        next(unit for unit in units if unit.get("population_policy") == "decision_required"),
        next(unit for unit in units if unit.get("population_policy") == "computed"),
        next(unit for unit in units if unit.get("population_policy") == "unsupported"),
    ]
    for unit in representatives:
        assert unit["display_name"]
        assert unit["display_name"] != unit.get("field_name")
        assert "[0]" not in unit["display_name"]


@pytest.mark.m15
def test_read_apis_do_not_mutate_authoritative_artifacts(client) -> None:
    paths = [
        ROOT / "build" / "tax_graph_2025.sqlite",
        ROOT / "graph" / "2025" / "node_geometry.json",
    ]
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}

    queue = client.get("/api/queue").get_json()
    for group in queue["groups"]:
        client.get(f"/api/entries/{group['entries'][0]['queue_id']}")

    after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    assert after == before
    assert not (ROOT / "review_queue" / "2025" / "deferred_review.yaml").exists()
