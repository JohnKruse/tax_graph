"""M15 complete AcroForm field-disposition contract tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import fitz
import pytest
import yaml

from tax_graph.engine import Engine, Graph
from tax_graph.io.loader import load_graph
from tax_graph.output.field_maps import (
    migrate_field_dispositions,
    validate_exposed_pdf_fields,
    validate_field_maps,
    load_field_maps,
)
from tax_graph.output.fill import build_field_values, fill_official_pdf


ROOT = Path(__file__).resolve().parents[1]


def _fixture_root(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    (tmp_path / "schemas").mkdir()
    (tmp_path / "graph/2025/field_maps").mkdir(parents=True)
    (tmp_path / "graph/2025/field_inventories").mkdir(parents=True)
    (tmp_path / "schemas/field_map.schema.json").write_text(
        (ROOT / "schemas/field_map.schema.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    inventory = {
        "fields": [
            {"field_name": "f_text", "field_type": "Text", "page": 1},
            {"field_name": "f_check", "field_type": "CheckBox", "page": 1},
        ]
    }
    (tmp_path / "graph/2025/field_inventories/form_test_2025.json").write_text(
        json.dumps(inventory), encoding="utf-8"
    )
    field_map: dict[str, object] = {
        "schema_version": 2,
        "tax_year": 2025,
        "document_id": "form_test_2025",
        "inventory": "graph/2025/field_inventories/form_test_2025.json",
        "mappings": [
            {"slot": "wages", "field_name": "f_text", "format": "dollars", "node_id": "form_test_2025_line_1"}
        ],
        "excluded_nodes": [],
        "frontier_fields": [],
        "field_dispositions": [
            {
                "field_name": "f_text",
                "label": "Line 1 wages",
                "population_policy": "computed",
                "value_format": "dollars",
                "node_id": "form_test_2025_line_1",
            },
            {
                "field_name": "f_check",
                "label": "Unsupported election",
                "population_policy": "unsupported",
                "value_format": "checkbox",
                "reason": "Election logic is not modeled.",
                "downstream_effect": "The return cannot claim this election.",
                "missing_capability": "A cited qualification branch is required.",
            },
        ],
    }
    return tmp_path, field_map


def _write_map(root: Path, field_map: dict[str, object]) -> list[str]:
    (root / "graph/2025/field_maps/form_test_2025.yaml").write_text(
        yaml.safe_dump(field_map, sort_keys=False), encoding="utf-8"
    )
    return validate_field_maps(
        "2025", root, node_ids={"form_test_2025_line_1"}, frontier_ids=set()
    )


@pytest.mark.m15
def test_complete_field_disposition_fixture_is_valid(tmp_path: Path) -> None:
    root, field_map = _fixture_root(tmp_path)
    assert _write_map(root, field_map) == []


@pytest.mark.m15
@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda item: item["field_dispositions"].pop(), "field has no disposition"),
        (lambda item: item["field_dispositions"].append(copy.deepcopy(item["field_dispositions"][0])), "duplicate field disposition"),
        (lambda item: item["field_dispositions"][0].update(field_name="unknown"), "disposition references unknown field"),
    ],
)
def test_missing_duplicate_and_unknown_dispositions_fail(
    tmp_path: Path, mutation: object, message: str
) -> None:
    root, field_map = _fixture_root(tmp_path)
    mutation(field_map)  # type: ignore[operator]
    assert any(message in error for error in _write_map(root, field_map))


@pytest.mark.m15
def test_unsupported_requires_consequence_and_capability(tmp_path: Path) -> None:
    root, field_map = _fixture_root(tmp_path)
    unsupported = field_map["field_dispositions"][1]  # type: ignore[index]
    unsupported.pop("downstream_effect")
    errors = _write_map(root, field_map)
    assert any("schema" in error and "downstream_effect" in error for error in errors)


@pytest.mark.m15
@pytest.mark.parametrize(
    "policy",
    ["copied", "computed"],
)
def test_graph_operation_policy_requires_node_ref(tmp_path: Path, policy: str) -> None:
    root, field_map = _fixture_root(tmp_path)
    disposition = field_map["field_dispositions"][0]  # type: ignore[index]
    disposition["population_policy"] = policy
    disposition.pop("node_id")
    errors = _write_map(root, field_map)
    assert any("schema" in error and "node_id" in error for error in errors)


@pytest.mark.m15
def test_migration_is_idempotent_and_never_guesses_unmapped_policy(tmp_path: Path) -> None:
    root, field_map = _fixture_root(tmp_path)
    field_map.pop("schema_version")
    field_map.pop("field_dispositions")
    field_map["mappings"] = [
        {"slot": "taxpayer_name", "field_name": "f_text", "format": "text", "identity_slot": "taxpayer_name"}
    ]
    _write_map(root, field_map)
    target = root / "worklist.yaml"
    first = migrate_field_dispositions("2025", root, output_path=target)
    first_text = target.read_text(encoding="utf-8")
    second = migrate_field_dispositions("2025", root, output_path=target)
    assert target.read_text(encoding="utf-8") == first_text
    assert first == second
    report = first.documents[0]
    assert report.proposed_dispositions[0]["population_policy"] == "user_entered"
    assert report.authored_work == (
        {
            "field_name": "f_check",
            "field_type": "CheckBox",
            "page": 1,
            "reason": "unclassified legacy inventory field",
        },
    )


@pytest.mark.m15
def test_real_pdf_widget_preflight_detects_missing_maps() -> None:
    errors = validate_exposed_pdf_fields("2025", ROOT)
    assert errors == []
    assert not any("instructions_form_1040_2025" in error for error in errors)


@pytest.mark.m15
def test_all_exposed_controls_have_one_complete_disposition() -> None:
    for path in sorted((ROOT / "graph/2025/field_maps").glob("*.yaml")):
        field_map = yaml.safe_load(path.read_text(encoding="utf-8"))
        inventory = json.loads((ROOT / field_map["inventory"]).read_text(encoding="utf-8"))
        widget_names = {item["field_name"] for item in inventory["fields"]}
        dispositions = field_map["field_dispositions"]
        assert {item["field_name"] for item in dispositions} == widget_names
        assert len(dispositions) == len(widget_names)
        assert all(item["label"] for item in dispositions)
        assert all("not mapped in the supported output profile" not in item["reason"].lower() for item in field_map["excluded_nodes"])


@pytest.mark.m15
def test_form_1040_lines_1a_through_1h_and_1z_have_exact_fields() -> None:
    field_map = yaml.safe_load((ROOT / "graph/2025/field_maps/form_1040_2025.yaml").read_text())
    by_node = {item.get("node_id"): item["field_name"] for item in field_map["mappings"] if item.get("node_id")}
    assert by_node["form_1040_2025_root_line_1a"].endswith("f1_47[0]")
    for offset, anchor in enumerate(("1b", "1c", "1d", "1e", "1f", "1g"), 48):
        assert by_node[f"form_1040_2025_root_line_{anchor}"].endswith(f"f1_{offset:02d}[0]")
    assert by_node["form_1040_2025_root_line_1h"].endswith("f1_55[0]")
    assert by_node["form_1040_2025_root_line_z"].endswith("f1_57[0]")
    description = next(item for item in field_map["mappings"] if item.get("identity_slot") == "line_1h_description")
    assert description["field_name"].endswith("f1_54[0]")


@pytest.mark.m15
def test_form_1040_nonzero_1b_through_1h_sum_and_pdf_echo(tmp_path: Path) -> None:
    if not (ROOT / ".cache/raw/2025/form_1040_2025.pdf").exists():
        pytest.skip("official cached PDF is required for the gated PDF echo")
    graph = Graph(2025, root=ROOT, source="yaml")
    facts = {f"form_1040_2025_root_line_1{letter}": index * 100 for index, letter in enumerate("abcdefgh", 1)}
    facts["filing_status"] = "single"
    result = Engine(graph).execute(facts)
    assert result.values["form_1040_2025_root_line_z"] == 3600
    field_map = next(
        item
        for item in load_field_maps(2025, ROOT)
        if item["document_id"] == "form_1040_2025"
    )
    facts_document = {
        "filing_status": "single",
        "identity": {"line_1h_description": "Jury duty pay"},
        "facts": [{"node_id": key, "value": value} for key, value in facts.items() if key != "filing_status"],
    }
    values, notes = build_field_values(field_map, result, facts_document, root=ROOT)
    expected = {
        "topmostSubform[0].Page1[0].f1_48[0]": "200",
        "topmostSubform[0].Page1[0].f1_49[0]": "300",
        "topmostSubform[0].Page1[0].f1_50[0]": "400",
        "topmostSubform[0].Page1[0].f1_51[0]": "500",
        "topmostSubform[0].Page1[0].f1_52[0]": "600",
        "topmostSubform[0].Page1[0].f1_53[0]": "700",
        "topmostSubform[0].Page1[0].f1_54[0]": "Jury duty pay",
        "topmostSubform[0].Page1[0].f1_55[0]": "800",
        "topmostSubform[0].Page1[0].f1_57[0]": "3600",
    }
    assert expected.items() <= values.items()
    filled = fill_official_pdf(
        ROOT / ".cache/raw/2025/form_1040_2025.pdf",
        tmp_path / "form_1040_lines_1.pdf",
        document_id="form_1040_2025",
        field_values={key: values[key] for key in expected},
        blank_with_note=notes,
    )
    assert filled.field_values == expected


@pytest.mark.m15
def test_form_8949_total_mappings_and_pdf_positions(tmp_path: Path) -> None:
    if not (ROOT / ".cache/raw/2025/form_8949_2025.pdf").exists():
        pytest.skip("official cached PDF is required for the gated PDF echo")
    field_map = yaml.safe_load((ROOT / "graph/2025/field_maps/form_8949_2025.yaml").read_text())
    totals = {
        item["node_id"]: item["field_name"]
        for item in field_map["mappings"]
        if "line_2_line_2_column" in item.get("node_id", "")
    }
    expected = {
        "form_8949_2025_part_i_line_2_line_2_column_d_total": "topmostSubform[0].Page1[0].f1_91[0]",
        "form_8949_2025_part_i_line_2_line_2_column_e_total": "topmostSubform[0].Page1[0].f1_92[0]",
        "form_8949_2025_part_i_line_2_line_2_column_g_total": "topmostSubform[0].Page1[0].f1_94[0]",
        "form_8949_2025_part_i_line_2_line_2_column_h_total": "topmostSubform[0].Page1[0].f1_95[0]",
        "form_8949_2025_part_ii_line_2_line_2_column_d_total": "topmostSubform[0].Page2[0].f2_91[0]",
        "form_8949_2025_part_ii_line_2_line_2_column_e_total": "topmostSubform[0].Page2[0].f2_92[0]",
        "form_8949_2025_part_ii_line_2_line_2_column_g_total": "topmostSubform[0].Page2[0].f2_94[0]",
        "form_8949_2025_part_ii_line_2_line_2_column_h_total": "topmostSubform[0].Page2[0].f2_95[0]",
    }
    assert totals == expected
    field_values = {field_name: str((index + 1) * 111) for index, field_name in enumerate(expected.values())}
    filled = fill_official_pdf(
        ROOT / ".cache/raw/2025/form_8949_2025.pdf",
        tmp_path / "form_8949_totals.pdf",
        document_id="form_8949_2025",
        field_values=field_values,
    )
    assert filled.field_values == field_values


@pytest.mark.m15
def test_schedule_1_other_amounts_and_totals_have_distinct_pdf_positions(tmp_path: Path) -> None:
    if not (ROOT / ".cache/raw/2025/schedule_1_2025.pdf").exists():
        pytest.skip("official cached PDF is required for the gated PDF echo")
    graph = Graph(2025, root=ROOT, source="yaml")
    result = Engine(graph).execute({
        "filing_status": "single",
        "form_1040_2025_root_line_1a": 50000,
        "schedule_1_2025_part_i_line_8v": 100,
        "schedule_1_2025_part_i_line_8z": 811,
        "schedule_1_2025_part_ii_line_24e": 100,
        "schedule_1_2025_part_ii_line_24z": 2411,
        "schedule_d_2025_line_7_net_st": 0,
    })
    assert result.values["schedule_1_2025_part_i_line_9"] == 911
    assert result.values["schedule_1_2025_part_ii_line_25"] == 2511

    field_map = next(
        item for item in load_field_maps(2025, ROOT)
        if item["document_id"] == "schedule_1_2025"
    )
    by_node = {
        item["node_id"]: item["field_name"]
        for item in field_map["mappings"]
        if item.get("node_id")
    }
    expected_fields = {
        "schedule_1_2025_part_i_line_8z": "topmostSubform[0].Page1[0].f1_36[0]",
        "schedule_1_2025_part_i_line_9": "topmostSubform[0].Page1[0].f1_37[0]",
        "schedule_1_2025_part_ii_line_24z": "topmostSubform[0].Page2[0].f2_28[0]",
        "schedule_1_2025_part_ii_line_25": "topmostSubform[0].Page2[0].f2_29[0]",
    }
    assert expected_fields.items() <= by_node.items()

    values, notes = build_field_values(
        field_map,
        result,
        {
            "filing_status": "single",
            "facts": [
                {"node_id": "schedule_1_2025_part_i_line_8v", "value": 100},
                {"node_id": "schedule_1_2025_part_i_line_8z", "value": 811},
                {"node_id": "schedule_1_2025_part_ii_line_24e", "value": 100},
                {"node_id": "schedule_1_2025_part_ii_line_24z", "value": 2411},
            ],
        },
        root=ROOT,
    )
    expected_values = {
        "topmostSubform[0].Page1[0].f1_36[0]": "811",
        "topmostSubform[0].Page1[0].f1_37[0]": "911",
        "topmostSubform[0].Page2[0].f2_28[0]": "2411",
        "topmostSubform[0].Page2[0].f2_29[0]": "2511",
    }
    assert expected_values.items() <= values.items()
    filled = fill_official_pdf(
        ROOT / ".cache/raw/2025/schedule_1_2025.pdf",
        tmp_path / "schedule_1_other_and_totals.pdf",
        document_id="schedule_1_2025",
        field_values={key: values[key] for key in expected_values},
        blank_with_note=notes,
    )
    assert filled.field_values == expected_values
    expected_positions = {
        "topmostSubform[0].Page1[0].f1_36[0]": (1, (410.4, 630.0, 481.65, 642.0), "811"),
        "topmostSubform[0].Page1[0].f1_37[0]": (1, (504.0, 642.0, 576.0, 654.0), "911"),
        "topmostSubform[0].Page2[0].f2_28[0]": (2, (410.4, 504.0, 481.65, 516.0), "2411"),
        "topmostSubform[0].Page2[0].f2_29[0]": (2, (504.0, 516.0, 576.0, 528.0), "2511"),
    }
    positioned = {}
    with fitz.open(filled.output_path) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            for widget in page.widgets() or []:
                if widget.field_name in expected_positions:
                    positioned[widget.field_name] = (
                        page_number,
                        tuple(round(value, 2) for value in widget.rect),
                        str(widget.field_value),
                    )
    assert positioned == expected_positions


@pytest.mark.m15
def test_mapping_triangle_reports_node_widget_and_mapping_disagreement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, field_map = _fixture_root(tmp_path)
    (root / "graph/2025/addresses").mkdir(parents=True)
    field_map["mappings"][0]["address_id"] = "2025/document=form_test/line=1/control=amount"
    field_map["field_dispositions"][0]["address_id"] = "2025/document=form_test/line=1/control=amount"
    artifacts = SimpleNamespace(
        addresses=(
            SimpleNamespace(address_id="2025/document=form_test/line=1/control=amount"),
            SimpleNamespace(address_id="2025/document=form_test/line=2/control=amount"),
        ),
        widget_bindings=({
            "document_id": "form_test_2025", "field_name": "f_text",
            "address_id": "2025/document=form_test/line=1/control=amount",
        },),
        node_bindings=({
            "document_id": "form_test_2025", "node_id": "form_test_2025_line_1",
            "address_id": "2025/document=form_test/line=2/control=amount",
        },),
    )
    monkeypatch.setattr("tax_graph.addressing.load_address_artifacts", lambda year, path: artifacts)
    errors = _write_map(root, field_map)
    assert any(
        "mapping triangle disagrees for f_text" in error
        and "node form_test_2025_line_1" in error
        and "widget f_text" in error
        and "mapping -> 2025/document=form_test/line=1/control=amount" in error
        for error in errors
    )


@pytest.mark.m15
@pytest.mark.parametrize("field_type", ["text", "checkbox"])
def test_seeded_missing_widget_type_fails_preflight(tmp_path: Path, field_type: str) -> None:
    fitz = pytest.importorskip("fitz")
    raw = tmp_path / ".cache/raw/2025"
    maps = tmp_path / "graph/2025/field_maps"
    inventories = tmp_path / "graph/2025/field_inventories"
    raw.mkdir(parents=True)
    maps.mkdir(parents=True)
    inventories.mkdir(parents=True)
    document = fitz.open()
    page = document.new_page()
    widget = fitz.Widget()
    widget.field_name = f"missing_{field_type}"
    widget.field_type = {
        "text": fitz.PDF_WIDGET_TYPE_TEXT,
        "checkbox": fitz.PDF_WIDGET_TYPE_CHECKBOX,
    }[field_type]
    widget.rect = fitz.Rect(20, 20, 80, 40)
    page.add_widget(widget)
    document.save(raw / "form_seed_2025.pdf")
    document.close()
    (inventories / "form_seed_2025.json").write_text('{"fields": []}', encoding="utf-8")
    (maps / "form_seed_2025.yaml").write_text(
        yaml.safe_dump(
            {
                "tax_year": 2025,
                "document_id": "form_seed_2025",
                "inventory": "graph/2025/field_inventories/form_seed_2025.json",
                "mappings": [],
                "excluded_nodes": [],
                "frontier_fields": [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    errors = validate_exposed_pdf_fields("2025", tmp_path)
    assert any("widget/inventory mismatch" in error and "missing=1" in error for error in errors)


@pytest.mark.m15
def test_seeded_missing_radio_disposition_fails_preflight(tmp_path: Path) -> None:
    root, field_map = _fixture_root(tmp_path)
    inventory_path = root / "graph/2025/field_inventories/form_test_2025.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    inventory["fields"].append({"field_name": "f_radio", "field_type": "RadioButton", "page": 1})
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
    errors = _write_map(root, field_map)
    assert any("field has no disposition: f_radio" in error for error in errors)


@pytest.mark.m15
def test_entirely_missing_form_inventory_fails_preflight(tmp_path: Path) -> None:
    fitz = pytest.importorskip("fitz")
    raw = tmp_path / ".cache/raw/2025"
    raw.mkdir(parents=True)
    document = fitz.open()
    page = document.new_page()
    widget = fitz.Widget()
    widget.field_name = "orphan"
    widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
    widget.rect = fitz.Rect(20, 20, 80, 40)
    page.add_widget(widget)
    document.save(raw / "form_orphan_2025.pdf")
    document.close()
    errors = validate_exposed_pdf_fields("2025", tmp_path)
    assert errors == ["exposed AcroForm form_orphan_2025 -> missing committed field map and inventory"]


@pytest.mark.m15
def test_real_v2_maps_validate_with_pdf_coverage() -> None:
    graph = load_graph("2025", ROOT)
    frontier = yaml.safe_load((ROOT / "graph/2025/frontier.yaml").read_text(encoding="utf-8"))
    assert validate_field_maps(
        "2025",
        ROOT,
        node_ids=(item["node_id"] for item in graph.items("nodes")),
        frontier_ids=(item["frontier_id"] for item in frontier["frontiers"]),
        check_exposed_pdfs=True,
    ) == []
