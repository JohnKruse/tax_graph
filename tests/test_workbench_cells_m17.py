"""M17 cell-inventory + document-centric review API tests.

The review is re-sourced from the FORM: every addressable, clickable control on the
page is a reviewable cell, in reading order, joined to its address / disposition /
node binding. These tests pin that contract and the per-document session round-trip.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest

from workbench.cell_inventory import (
    _citations,
    _load_citations,
    build_document_cells,
    build_documents_index,
)


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
    geometry_payload = json.loads((ROOT / "graph" / "2025" / "node_geometry.json").read_text("utf-8"))
    geometry = geometry_payload["entries"]
    index = build_documents_index(
        ROOT, 2025, ["form_1040_2025", "does_not_exist"], geometry_entries=geometry,
        page_geometry=geometry_payload.get("pages", []), titles={"form_1040_2025": "Form 1040"},
    )
    assert [item["document_id"] for item in index] == ["form_1040_2025"]
    assert index[0]["title"] == "Form 1040"
    assert index[0]["cell_count"] == len(built.cells)
    assert index[0]["pages"] == built.pages
    assert index[0]["page_geometry"] == built.page_geometry
    assert sum(index[0]["policy_counts"].values()) == index[0]["cell_count"]
    assert index[0]["policy_counts"]["user_entered"] > 0


@pytest.mark.m17
def test_cell_carries_all_field_map_disposition_metadata() -> None:
    cells = build_document_cells(ROOT, 2025, "form_1040_2025").cells
    unsupported = next(cell for cell in cells if cell["population_policy"] == "unsupported")
    assert unsupported["policy_reason"]
    assert unsupported["downstream_effect"]
    assert unsupported["missing_capability"]


@pytest.mark.m17
def test_citations_resolve_to_verbatim_text_and_provenance() -> None:
    citations = _load_citations(ROOT / "graph" / "2025" / "citations")
    records = _citations(
        {"citation_refs": ["cite_span_form_1040_2025_0007", "missing_citation"]},
        citations,
    )
    assert records[0] == {
        "citation_id": "cite_span_form_1040_2025_0007",
        # M18-S2b re-derived this from the acquired source. The old expectation pinned the
        # extraction wrapper ("- 1: a ... 1a") that John flagged in review, so this test was
        # asserting the defect.
        "quoted_text": "Total amount from Form(s) W-2, box 1 (see instructions)",
        "locator": "page 1, line 8",
        "url": "https://www.irs.gov/pub/irs-prior/f1040--2025.pdf",
        "retrieved_date": "2026-07-09",
        "source_document_id": "form_1040_2025",
        "resolved": True,
    }
    assert records[1]["citation_id"] == "missing_citation"
    assert records[1]["quoted_text"] is None
    assert records[1]["resolved"] is False


@pytest.mark.m17
def test_instruction_citations_are_separate_from_authority() -> None:
    cells = build_document_cells(ROOT, 2025, "form_1040_2025").cells
    cell = next(cell for cell in cells if cell["instruction_citations"])
    assert cell["instruction_citations"][0]["source_document_id"].startswith("instructions_")
    assert all(
        not str(citation.get("source_document_id") or "").startswith("instructions_")
        for citation in cell["citations"]
    )


@pytest.mark.m17
def test_promoted_html_instruction_projects_to_the_matching_1040_cell() -> None:
    cells = build_document_cells(ROOT, 2025, "form_1040_2025").cells
    cell = next(
        cell for cell in cells
        if str(cell.get("address_id") or "").endswith("/line=1a/control=amount")
    )
    instruction = next(
        citation for citation in cell["instruction_citations"]
        if citation["citation_id"].startswith("cite_instruction_form_1040_2025_en_us_")
    )
    assert instruction["semantic_title"] == "Total Amount From Form(s) W-2, Box 1"
    assert instruction["locator"].startswith("html#")
    assert "- 1a:" not in instruction["quoted_text"]


@pytest.mark.m17
def test_document_index_reports_citation_coverage() -> None:
    import json
    geometry_payload = json.loads((ROOT / "graph" / "2025" / "node_geometry.json").read_text("utf-8"))
    geometry = geometry_payload["entries"]
    index = build_documents_index(
        ROOT, 2025, ["form_1040_2025"], geometry_entries=geometry,
        page_geometry=geometry_payload.get("pages", []),
    )
    counts = index[0]["citation_counts"]
    assert counts["cited"] > 0
    assert counts["uncited"] > 0
    assert counts["cited"] + counts["uncited"] == index[0]["cell_count"]


@pytest.mark.m17
def test_document_cells_expose_captured_page_geometry() -> None:
    built = build_document_cells(ROOT, 2025, "form_13614_c_2025")
    assert built.page_geometry
    landscape = next(item for item in built.page_geometry if item["page"] == 1)
    assert landscape["width"] == 792.0
    assert landscape["height"] == 612.0
    assert landscape["rotation"] == 0
