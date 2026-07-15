from __future__ import annotations

import copy
from pathlib import Path
import random

import jsonschema
import pytest

from tax_graph.addressing import generate_candidate_registry, write_candidate_registry


ROOT = Path(__file__).resolve().parents[1]
HASH = "a" * 64


def _controls():
    return [
        {"official_ref": "1a", "control_role": "amount", "printed_label": "W-2 box 1 and Schedule 1 line 26", "field_name": "opaque_a", "page": 1, "rect": [1, 2, 3, 4], "accessibility_label": "Line 1a amount"},
        {"official_ref": "1a", "control_role": "description", "printed_label": "Type and amount", "field_name": "opaque_b", "page": 1, "rect": [5, 6, 7, 8]},
        {"semantic_path": [{"kind": "table", "token": "part_i_line_1"}, {"kind": "row_template", "token": "transaction"}, {"kind": "column", "token": "d"}], "official_ref": "Column (d)", "control_role": "amount", "printed_label": "Proceeds", "field_name": "row_01_d", "page": 1},
        {"section_token": "filing_status", "neutral_token": "1", "control_role": "radio", "printed_label": "", "field_name": "choice_42", "page": 1, "semantic_status": "provisional"},
    ]


def _generate(controls):
    return generate_candidate_registry(year=2025, document_id="form_test_2025", document_token="form_test", source_path="raw/test.pdf", source_hash=HASH, controls=controls)


@pytest.mark.m15r
def test_physical_and_prose_perturbations_do_not_change_semantic_paths() -> None:
    original = _controls()
    changed = copy.deepcopy(original)
    random.Random(7).shuffle(changed)
    for index, item in enumerate(changed):
        item["field_name"] = f"renamed_{index}"
        item["page"] = 9
        item["rect"] = [9, 9, 9, 9]
        item["printed_label"] += " references lines 2, 26, and 31"
    before = [item["address_id"] for item in _generate(original)["addresses"]]
    after = [item["address_id"] for item in _generate(changed)["addresses"]]
    assert before == after
    assert "2025/document=form_test/line=1a/control=amount" in before
    assert "2025/document=form_test/table=part_i_line_1/row_template=transaction/column=d" in before


@pytest.mark.m15r
def test_missing_label_is_neutral_and_provisional_and_schema_valid() -> None:
    payload = _generate(_controls())
    option = next(item for item in payload["addresses"] if item["kind"] == "option")
    assert option["status"] == "provisional"
    assert option["address_id"].endswith("section=filing_status/option=1")
    schema = __import__("json").loads((ROOT / "schemas" / "address_registry.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(payload, schema)


@pytest.mark.m15r
def test_candidate_writer_cannot_escape_draft_boundary(tmp_path: Path) -> None:
    path = write_candidate_registry(_generate(_controls()), tmp_path)
    assert path == tmp_path / "graph/2025/_drafts/addresses/form_test_2025.yaml"
    assert path.exists()
