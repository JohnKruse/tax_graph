"""M17 cell-inventory + document-centric review API tests.

The review is re-sourced from the FORM: every addressable, clickable control on the
page is a reviewable cell, in reading order, joined to its address / disposition /
node binding. These tests pin that contract and the per-document session round-trip.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest

from workbench.cell_inventory import build_document_cells, build_documents_index
from workbench.server import create_app


ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    not (ROOT / "graph" / "2025" / "_drafts").exists(),
    reason="live review drafts are required: fresh checkouts (CI) carry no _drafts",
)

CELL_ID = re.compile(r"^[a-z0-9_]+$")


@pytest.mark.m17
def test_cell_inventory_is_form_complete_and_reading_order() -> None:
    built = build_document_cells(ROOT, 2025, "form_1040_2025")
    cells = built.cells
    assert len(cells) > 100, "the 1040 has many addressable cells"
    # Every physical cell has geometry, an id, and exactly one population policy.
    assert all(cell["page"] and cell["rect"] for cell in cells)
    assert all(CELL_ID.match(cell["cell_id"]) for cell in cells)
    assert all(cell["population_policy"] for cell in cells), "no unpolicied (invisible) cell"
    # Ids are unique per document (the session keys them).
    assert len({cell["cell_id"] for cell in cells}) == len(cells)
    # Reading order: sorted by (page, top, left).
    keys = [(cell["page"], round(cell["rect"][1], 1), round(cell["rect"][0], 1)) for cell in cells]
    assert keys == sorted(keys)


@pytest.mark.m17
def test_return_header_cells_are_present_not_dropped() -> None:
    # These were fully parsed but never in the deferred-review queue, so the old
    # queue-sourced UI hid them. The form-sourced inventory must surface them.
    cells = build_document_cells(ROOT, 2025, "form_1040_2025").cells
    addresses = {cell["address_id"] for cell in cells if cell["address_id"]}
    for control in (
        "section=return_header/control=combat_zone_name",
        "section=return_header/option=combat_zone",
        "section=return_header/control=taxpayer_deceased_month",
    ):
        assert any(address.endswith(control) for address in addresses), control


@pytest.mark.m17
def test_first_name_is_an_identity_input_not_a_calculation() -> None:
    cells = build_document_cells(ROOT, 2025, "form_1040_2025").cells
    first = next(
        cell for cell in cells
        if cell["address_id"] and cell["address_id"].endswith("control=taxpayer_first_name")
    )
    assert first["display_name"] == "First name and middle initial"
    assert first["population_policy"] == "user_entered"
    assert first["control_role"] == "text"


@pytest.mark.m17
def test_documents_index_loads_geometry_once_and_omits_empty() -> None:
    built = build_document_cells(ROOT, 2025, "form_1040_2025")
    # Reuse the same geometry the index would load, filtered.
    import json
    geometry = json.loads((ROOT / "graph" / "2025" / "node_geometry.json").read_text("utf-8"))["entries"]
    index = build_documents_index(
        ROOT, 2025, ["form_1040_2025", "does_not_exist"],
        geometry_entries=geometry, titles={"form_1040_2025": "Form 1040"},
    )
    assert [item["document_id"] for item in index] == ["form_1040_2025"]
    assert index[0]["title"] == "Form 1040"
    assert index[0]["cell_count"] == len(built.cells)
    assert index[0]["pages"] == built.pages


@pytest.fixture(scope="module")
def client():
    app = create_app(ROOT, 2025, write_token="test-write-token")
    app.config.update(TESTING=True)
    return app.test_client()


@pytest.mark.m17
def test_documents_api_lists_forms(client) -> None:
    payload = client.get("/api/documents").get_json()
    assert payload["tax_year"] == 2025
    assert any(item["document_id"] == "form_1040_2025" for item in payload["documents"])
    assert all(item["cell_count"] > 0 for item in payload["documents"])


@pytest.mark.m17
def test_document_cells_api_returns_ordered_cells(client) -> None:
    response = client.get("/api/documents/form_1040_2025/cells")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["document_id"] == "form_1040_2025"
    assert payload["pages"] == sorted(payload["pages"])
    assert payload["cells"], "the 1040 has cells"
    assert client.get("/api/documents/not_a_form/cells").status_code == 404


@pytest.mark.m17
def test_document_session_round_trip_and_scope(client) -> None:
    session = client.get("/api/documents/form_1040_2025/session").get_json()
    assert session["queue_id"] == "form_1040_2025"
    assert session["progress"]["total"] > 0
    cells = client.get("/api/documents/form_1040_2025/cells").get_json()["cells"]
    target = cells[0]["cell_id"]
    session["unit_reviews"] = {
        target: {"status": "approved", "note": "ok", "updated_at": "2026-07-24T00:00:00+00:00"}
    }
    session["current_unit_id"] = target
    session.pop("progress", None)
    saved = client.put(
        "/api/documents/form_1040_2025/session",
        json=session,
        headers={"X-Workbench-Token": "test-write-token"},
    )
    assert saved.status_code == 200, saved.get_json()
    assert saved.get_json()["progress"]["approved"] == 1
    # A review keyed to a cell outside the document is rejected.
    session["unit_reviews"]["not_a_cell_here"] = {
        "status": "approved", "note": "", "updated_at": "2026-07-24T00:00:00+00:00"
    }
    bad = client.put(
        "/api/documents/form_1040_2025/session",
        json=session,
        headers={"X-Workbench-Token": "test-write-token"},
    )
    assert bad.status_code == 400


@pytest.mark.m17
def test_document_session_requires_write_token(client) -> None:
    session = client.get("/api/documents/form_1040_2025/session").get_json()
    session.pop("progress", None)
    denied = client.put("/api/documents/form_1040_2025/session", json=session)
    assert denied.status_code == 403
