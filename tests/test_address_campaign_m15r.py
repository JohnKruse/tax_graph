from __future__ import annotations

import json
from pathlib import Path
import re
import unicodedata

import jsonschema
import fitz
import pytest
import yaml

from tax_graph.addressing import CORE_RETURN_DOCUMENTS, INFORMATION_RETURN_DOCUMENTS, build_address_campaign
from tax_graph.addressing import build_document_addresses
from tax_graph.link import link_outbound_flows


ROOT = Path(__file__).resolve().parents[1]


def _require_official_pdf(document_id: str) -> Path:
    """Return the cached official PDF path or skip: fresh checkouts (CI) carry no raw cache."""
    path = ROOT / ".cache/raw/2025" / f"{document_id}.pdf"
    if not path.exists():
        pytest.skip(f"official cached PDF {document_id} is required for this check")
    return path


def _open_official_pdf(document_id: str) -> fitz.Document:
    return fitz.open(_require_official_pdf(document_id))


@pytest.fixture(scope="module")
def campaign():
    if not (ROOT / ".cache" / "raw" / "2025").exists():
        pytest.skip("official raw cache is required to build the core address campaign")
    return build_address_campaign(ROOT, CORE_RETURN_DOCUMENTS)


@pytest.fixture(scope="module")
def form_1040_campaign():
    return build_document_addresses(ROOT, "form_1040_2025")


@pytest.fixture(scope="module")
def schedule_1_campaign():
    _require_official_pdf("schedule_1_2025")
    return build_document_addresses(ROOT, "schedule_1_2025")


@pytest.fixture(scope="module")
def schedule_1a_campaign():
    _require_official_pdf("schedule_1a_2025")
    return build_document_addresses(ROOT, "schedule_1a_2025")


@pytest.mark.m15
def test_schedule_1_campaign_authors_every_widget_and_corrected_totals(
    schedule_1_campaign,
) -> None:
    assert schedule_1_campaign["coverage"] == {
        "inventory": 73,
        "addressed_widgets": 73,
        "exempt_widgets": 0,
        "node_bindings": 28,
        "references": 0,
    }
    addresses = {
        item["address_id"]: item for item in schedule_1_campaign["registry"]["addresses"]
    }
    assert addresses[
        "2025/document=schedule_1/line=7/control=repaid_amount"
    ]["printed_label"] == "Amount of repaid unemployment compensation"
    assert addresses[
        "2025/document=schedule_1/line=8z/control=description"
    ]["printed_label"] == "Other income - type"
    assert addresses[
        "2025/document=schedule_1/line=9/control=amount"
    ]["printed_label"] == "Total other income"
    assert addresses[
        "2025/document=schedule_1/line=24z/control=description"
    ]["printed_label"] == "Other adjustments - type"
    assert addresses[
        "2025/document=schedule_1/line=25/control=amount"
    ]["printed_label"] == "Total other adjustments"
    assert schedule_1_campaign["field_addresses"][
        "topmostSubform[0].Page1[0].f1_36[0]"
    ] == "2025/document=schedule_1/line=8z/control=amount"
    assert schedule_1_campaign["field_addresses"][
        "topmostSubform[0].Page1[0].f1_37[0]"
    ] == "2025/document=schedule_1/line=9/control=amount"
    assert schedule_1_campaign["field_addresses"][
        "topmostSubform[0].Page2[0].f2_28[0]"
    ] == "2025/document=schedule_1/line=24z/control=amount"
    assert schedule_1_campaign["field_addresses"][
        "topmostSubform[0].Page2[0].f2_29[0]"
    ] == "2025/document=schedule_1/line=25/control=amount"


@pytest.mark.m15
def test_schedule_1a_campaign_authors_every_widget(schedule_1a_campaign) -> None:
    assert schedule_1a_campaign["coverage"] == {
        "inventory": 54,
        "addressed_widgets": 54,
        "exempt_widgets": 0,
        "node_bindings": 23,
        "references": 0,
    }
    addresses = {
        item["address_id"]: item for item in schedule_1a_campaign["registry"]["addresses"]
    }
    assert addresses[
        "2025/document=schedule_1a/line=3/control=amount"
    ]["printed_label"] == "Add lines 1 and 2e"
    assert addresses[
        "2025/document=schedule_1a/line=38/control=amount"
    ]["printed_label"] == "Add lines 13, 21, 30, and 37"
    assert addresses[
        "2025/document=schedule_1a/table=line_22/row_template=vehicle/column=vin"
    ]["printed_label"] == "Vehicle identification number (VIN)"
    assert schedule_1a_campaign["field_addresses"][
        "form1[0].Page1[0].f1_03[0]"
    ] == "2025/document=schedule_1a/line=1/control=amount"
    assert schedule_1a_campaign["field_addresses"][
        "form1[0].Page2[0].f2_07[0]"
    ] == "2025/document=schedule_1a/line=23/control=amount"
    assert schedule_1a_campaign["field_addresses"][
        "form1[0].Page2[0].f2_23[0]"
    ] == "2025/document=schedule_1a/line=38/control=amount"


@pytest.mark.m15
def test_schedule_1a_numbered_lines_have_adjacent_number_and_caption(
    schedule_1a_campaign,
) -> None:
    """Cross-check every authored line number and caption against the official PDF."""
    addresses = {
        item["address_id"]: item for item in schedule_1a_campaign["registry"]["addresses"]
    }
    binding_by_address = {
        item["address_id"]: item for item in schedule_1a_campaign["widget_bindings"]["bindings"]
    }
    pdf = _open_official_pdf("schedule_1a_2025")
    checked = set()
    for address_id, address in addresses.items():
        match = re.search(r"/line=([^/]+)/control=amount$", address_id)
        if not match:
            continue
        line = match.group(1)
        binding = binding_by_address[address_id]
        page = pdf[binding["page"] - 1]
        widget = fitz.Rect(binding["rect"])
        number_matches = _caption_rects(page, line)
        caption_matches = _caption_rects(page, address["printed_label"])
        assert number_matches, f"missing printed line number {line!r} for {address_id}"
        assert caption_matches, f"missing printed caption for {address_id}"
        assert min(_rect_distance(widget, item) for item in number_matches) <= 420
        assert min(_rect_distance(widget, item) for item in caption_matches) <= 420
        checked.add(line)
    assert len(checked) == 46


@pytest.mark.m15
def test_form_1040_campaign_binds_every_widget_to_authored_form_structure(
    form_1040_campaign,
) -> None:
    assert form_1040_campaign["coverage"] == {
        "inventory": 199,
        "addressed_widgets": 199,
        "exempt_widgets": 0,
        "node_bindings": 24,
        "references": 0,
    }
    assert len({
        item["address_id"] for item in form_1040_campaign["widget_bindings"]["bindings"]
    }) == 167
    addresses = {
        item["address_id"]: item for item in form_1040_campaign["registry"]["addresses"]
    }
    assert addresses[
        "2025/document=form_1040/section=identity/control=taxpayer_first_name"
    ]["printed_label"] == "First name and middle initial"
    assert addresses[
        "2025/document=form_1040/line=3a/control=amount"
    ]["printed_label"] == "Qualified dividends"
    assert addresses[
        "2025/document=form_1040/line=14/control=amount"
    ]["printed_label"] == "Add lines 12e, 13a, and 13b"
    assert addresses[
        "2025/document=form_1040/table=dependents/row_template=dependent/column=child_tax_credit"
    ]["printed_label"] == "Child tax credit"
    field_addresses = form_1040_campaign["field_addresses"]
    assert field_addresses["topmostSubform[0].Page1[0].f1_58[0]"] == (
        "2025/document=form_1040/line=2a/control=amount"
    )
    assert field_addresses["topmostSubform[0].Page1[0].f1_60[0]"] == (
        "2025/document=form_1040/line=3a/control=amount"
    )
    assert field_addresses["topmostSubform[0].Page2[0].f2_05[0]"] == (
        "2025/document=form_1040/line=14/control=amount"
    )


_FORM_1040_LINE_PREFIX = {
    "1a": "1 a", "1b": "b", "1c": "c", "1d": "d", "1e": "e", "1f": "f",
    "1g": "g", "1h": "h", "1i": "i", "1z": "z", "2a": "2a", "2b": "b",
    "3a": "3a", "3b": "b", "4a": "4a", "4b": "b", "5a": "5a", "5b": "b",
    "6a": "6a", "6b": "b", "7a": "7a", "8": "8", "9": "9", "10": "10",
    "11a": "11a", "11b": "11b", "12e": "e", "13a": "13a", "13b": "b",
    "14": "14", "15": "15", "16": "16", "17": "17", "18": "18", "19": "19",
    "20": "20", "21": "21", "22": "22", "23": "23", "24": "24", "25a": "a",
    "25b": "b", "25c": "c", "25d": "d", "26": "26", "27a": "27a", "28": "28",
    "29": "29", "30": "30", "31": "31", "32": "32", "33": "33", "34": "34",
    "35a": "35a", "36": "36", "37": "37", "38": "38",
}

_FORM_1040_LINE_CAPTION = {
    "1h": "h Other earned income",
    "25a": "a Form(s) W-2",
    "25b": "b Form(s) 1099",
    "25c": "c Other forms (see instructions)",
    "34": "34 If line 33 is more than line 24, subtract line 24 from line 33",
}

_FORM_1040_CAPTION_ALIAS = {
    "/line=12d/option=spouse_blind": "Is blind",
    "/line=12d/option=you_blind": "Are blind",
    "/line=16/control=text": "3",
    "/line=16/option=form_4972": "2 4972",
    "/line=16/option=form_8814": "1 8814",
    "/line=16/option=other_form": "3",
    "/line=26/control=identifier": "enter their SSN (see instructions)",
    "/line=27c/option=do_not_claim_eic": "If you do not want to claim the EIC, check here",
    "/line=28/option=do_not_claim_actc": "If you do not want to claim the ACTC, check here",
    "/line=3c/option=line_3a": "1 Line 3a",
    "/line=3c/option=line_3b": "2 Line 3b",
    "/line=4c/control=text": "3",
    "/line=4c/option=other_word_or_code": "3",
    "/line=5c/control=text": "3",
    "/line=5c/option=other_word_or_code": "3",
    "/line=6d/option=mfs_lived_apart": "If you are married filing separately and lived apart from your spouse the entire year",
    "/section=filing_status/control=hoh_qss_child_name": "enter the child's name",
    "/section=filing_status/control=mfs_spouse_full_name": "and full name here",
    "/section=filing_status/control=nonresident_alien_spouse_name": "enter their name",
    "/section=filing_status/option=mfs_hoh_lived_apart": "If your filing status is MFS or HOH and you lived apart from your spouse for the last 6 months of 2025",
    "/section=identity/control=spouse_last_name": "Last name",
    "/section=identity/option=presidential_election_spouse": "Spouse",
    "/section=identity/option=presidential_election_you": "You",
    "/section=return_header/control=combat_zone_name": "Combat zone",
    "/section=return_header/control=other_filing_designation_text": "Other",
    "/section=return_header/control=other_tax_year_ending": "ending",
    "/section=return_header/control=other_tax_year_ending_suffix": "20",
    "/section=return_header/control=spouse_deceased_day": "DD",
    "/section=return_header/control=spouse_deceased_month": "MM",
    "/section=return_header/control=spouse_deceased_year": "YYYY",
    "/section=return_header/control=taxpayer_deceased_day": "DD",
    "/section=return_header/control=taxpayer_deceased_month": "MM",
    "/section=return_header/control=taxpayer_deceased_year": "YYYY",
    "/section=sign_here/control=spouse_ip_pin": "Identity Protection PIN",
    "/section=sign_here/control=your_ip_pin": "Identity Protection PIN",
}


@pytest.mark.m15
def test_form_1040_line_controls_have_number_bearing_adjacent_printed_text(
    form_1040_campaign,
) -> None:
    """Cross-check each feasible line ref and caption against the official 2025 PDF."""
    addresses = {
        item["address_id"]: item for item in form_1040_campaign["registry"]["addresses"]
    }
    bindings_by_address: dict[str, list[dict]] = {}
    for binding in form_1040_campaign["widget_bindings"]["bindings"]:
        bindings_by_address.setdefault(binding["address_id"], []).append(binding)
    pdf = _open_official_pdf("form_1040_2025")
    checked = set()
    for address_id, address in addresses.items():
        matched = re.search(r"/line=([^/]+)/control=(amount|description)$", address_id)
        if not matched or matched.group(1) not in _FORM_1040_LINE_PREFIX:
            continue
        line = matched.group(1)
        caption = _FORM_1040_LINE_CAPTION.get(
            line, f"{_FORM_1040_LINE_PREFIX[line]} {address['printed_label']}",
        )
        distances = []
        for binding in bindings_by_address[address_id]:
            matches = _caption_rects(pdf[binding["page"] - 1], caption)
            widget = fitz.Rect(binding["rect"])
            distances.extend(_rect_distance(widget, match) for match in matches)
        assert distances, f"missing official printed line sequence {caption!r} for {address_id}"
        assert min(distances) <= 420, f"printed line sequence {caption!r} is not adjacent to {address_id}"
        checked.add(line)
    assert checked == set(_FORM_1040_LINE_PREFIX)


@pytest.mark.m15
def test_form_1040_other_authored_captions_are_adjacent_in_official_pdf(
    form_1040_campaign,
) -> None:
    """Cross-check non-line and line-choice identities against their printed captions."""
    addresses = {
        item["address_id"]: item for item in form_1040_campaign["registry"]["addresses"]
        if item["kind"] in {"control", "option", "column"}
    }
    bindings_by_address: dict[str, list[dict]] = {}
    for binding in form_1040_campaign["widget_bindings"]["bindings"]:
        bindings_by_address.setdefault(binding["address_id"], []).append(binding)
    pdf = _open_official_pdf("form_1040_2025")
    missing = []
    distant = []
    for address_id, address in addresses.items():
        if re.search(r"/line=([^/]+)/control=(amount|description)$", address_id):
            continue
        caption = next(
            (value for suffix, value in _FORM_1040_CAPTION_ALIAS.items() if address_id.endswith(suffix)),
            address["printed_label"],
        )
        distances = []
        for binding in bindings_by_address[address_id]:
            matches = _caption_rects(pdf[binding["page"] - 1], caption)
            widget = fitz.Rect(binding["rect"])
            distances.extend(_rect_distance(widget, match) for match in matches)
        if not distances:
            missing.append((address_id, caption))
        elif min(distances) > 280:
            distant.append((address_id, caption, min(distances)))
    assert not missing, "\n".join(f"{address_id}: {caption}" for address_id, caption in missing)
    assert not distant, "\n".join(
        f"{address_id}: {caption} ({distance})" for address_id, caption, distance in distant
    )


@pytest.mark.m15r
def test_core_campaign_reconciles_every_inventory_control(campaign) -> None:
    registry_schema = json.loads((ROOT / "schemas/address_registry.schema.json").read_text(encoding="utf-8"))
    binding_schema = json.loads((ROOT / "schemas/address_binding.schema.json").read_text(encoding="utf-8"))
    reference_schema = json.loads((ROOT / "schemas/address_reference.schema.json").read_text(encoding="utf-8"))
    assert tuple(campaign) == CORE_RETURN_DOCUMENTS
    for payload in campaign.values():
        coverage = payload["coverage"]
        assert coverage["inventory"] == coverage["addressed_widgets"] + coverage["exempt_widgets"]
        assert len(payload["widget_bindings"]["bindings"]) == coverage["addressed_widgets"]
        assert len(payload["node_bindings"]["bindings"]) == coverage["node_bindings"]
        assert all(item["status"] in {"pending_review", "provisional"} for item in payload["registry"]["addresses"])
        jsonschema.validate(payload["registry"], registry_schema)
        jsonschema.validate(payload["widget_bindings"], binding_schema)
        jsonschema.validate(payload["node_bindings"], binding_schema)
        jsonschema.validate(payload["references"], reference_schema)


@pytest.mark.m15r
def test_form_8949_uses_row_template_columns(campaign) -> None:
    payload = campaign["form_8949_2025"]
    assert payload["coverage"] == {
        "inventory": 202,
        "addressed_widgets": 200,
        "exempt_widgets": 2,
        "node_bindings": 16,
        "references": 6,
    }
    paths = [item["path"] for item in payload["registry"]["addresses"]]
    assert any(
        [part["kind"] for part in path[-3:]] == ["table", "row_template", "column"]
        and path[-1]["token"] == "d"
        for path in paths
    )
    bindings = payload["widget_bindings"]["bindings"]
    assert len({item["address_id"] for item in bindings}) < len(bindings)
    addresses = {item["address_id"]: item for item in payload["registry"]["addresses"]}
    assert addresses["2025/document=form_8949/table=part_i_line_1/row_template=transaction/column=a"]["printed_label"] == "Description of property"
    assert addresses["2025/document=form_8949/table=part_ii_line_2/row_template=total/column=e"]["printed_label"] == "Total cost or other basis"


@pytest.mark.m15r
def test_schedule_d_worksheet_steps_are_explicitly_bound(campaign) -> None:
    payload = campaign["schedule_d_2025"]
    bindings = {item["node_id"]: item for item in payload["node_bindings"]["bindings"]}
    for node_id in (
        "schedule_d_2025_carryover_worksheet_line_1",
        "schedule_d_2025_carryover_worksheet_line_13",
        "schedule_d_2025_tax_worksheet_line_1",
        "schedule_d_2025_tax_worksheet_line_47",
    ):
        assert bindings[node_id]["address_id"].split("/")[-1].startswith("worksheet_step=")


@pytest.mark.m15r
def test_form_8949_cross_form_claims_resolve_exactly() -> None:
    if not (ROOT / "graph" / "2025" / "_drafts").exists():
        pytest.skip("live review drafts are required: fresh checkouts (CI) carry no _drafts")
    result = link_outbound_flows(2025, ROOT, write=False)
    assert len(result.realized) == 6
    assert result.unresolved == []
    assert len(result.rejected) == 2


@pytest.fixture(scope="module")
def information_campaign():
    return build_address_campaign(ROOT, INFORMATION_RETURN_DOCUMENTS)


@pytest.mark.m15r
def test_information_return_campaign_uses_typed_boxes_and_choices(information_campaign) -> None:
    schema = json.loads((ROOT / "schemas/address_registry.schema.json").read_text(encoding="utf-8"))
    for document_id, payload in information_campaign.items():
        coverage = payload["coverage"]
        assert coverage["inventory"] == coverage["addressed_widgets"] + coverage["exempt_widgets"]
        jsonschema.validate(payload["registry"], schema)
        if document_id == "form_13614_c_2025":
            assert coverage["addressed_widgets"] == coverage["inventory"]
            continue
        assert coverage["addressed_widgets"] > 0
        if document_id == "form_w2_2025":
            assert coverage["exempt_widgets"] == 6
            continue
        assert coverage["exempt_widgets"] == 0
        addressed = {item["address_id"]: item for item in payload["registry"]["addresses"]}
        for binding in payload["widget_bindings"]["bindings"]:
            path = addressed[binding["address_id"]]["path"]
            assert path[-2]["kind"] in {"box", "section", "row_template"}
            assert path[-1]["kind"] in {"control", "option", "column"}


@pytest.mark.m15
def test_w2_campaign_collapses_official_copies_and_state_rows(information_campaign) -> None:
    payload = information_campaign["form_w2_2025"]
    assert payload["coverage"] == {
        "inventory": 272,
        "addressed_widgets": 266,
        "exempt_widgets": 6,
        "node_bindings": 0,
        "references": 0,
    }
    bindings = payload["widget_bindings"]["bindings"]
    assert len({item["address_id"] for item in bindings}) == 32
    addresses = {item["address_id"]: item for item in payload["registry"]["addresses"]}
    assert addresses["2025/document=form_w2/box=1/control=value"]["printed_label"] == (
        "Wages, tips, other compensation"
    )
    assert addresses[
        "2025/document=form_w2/box=12/row_template=entry/column=code"
    ]["printed_label"] == "Code"
    state_local = {
        "state": ("Box 15", "State"),
        "employer_state_id": ("Box 15", "Employer's state ID number"),
        "state_wages": ("Box 16", "State wages, tips, etc."),
        "state_income_tax": ("Box 17", "State income tax"),
        "local_wages": ("Box 18", "Local wages, tips, etc."),
        "local_income_tax": ("Box 19", "Local income tax"),
        "locality_name": ("Box 20", "Locality name"),
    }
    for token, (official_ref, printed_label) in state_local.items():
        address = addresses[
            f"2025/document=form_w2/table=state_local/row_template=jurisdiction/column={token}"
        ]
        assert (address["official_ref"], address["printed_label"]) == (official_ref, printed_label)
    assert not any(item.get("official_ref") == "Box 21" for item in addresses.values())
    assert all(item.get("display_name") == "Shaded no-entry box 9" for item in payload["exemptions"])


def _rect_distance(left: fitz.Rect, right: fitz.Rect) -> float:
    dx = max(left.x0 - right.x1, right.x0 - left.x1, 0)
    dy = max(left.y0 - right.y1, right.y0 - left.y1, 0)
    return (dx * dx + dy * dy) ** 0.5


def _caption_rects(page: fitz.Page, caption: str) -> list[fitz.Rect]:
    def tokens(value: str) -> list[str]:
        value = value.replace("\u2013", "-").replace("\u2014", "-")
        ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
        ascii_value = ascii_value.replace("'", "")
        return re.findall(r"[a-z0-9]+", ascii_value.lower())

    wanted = tokens(caption)
    words = page.get_text("words")
    flattened: list[str] = []
    token_rects: list[fitz.Rect] = []
    for word in words:
        for token in tokens(str(word[4])):
            flattened.append(token)
            token_rects.append(fitz.Rect(word[:4]))
    result: list[fitz.Rect] = []
    for index in range(len(flattened) - len(wanted) + 1):
        if flattened[index:index + len(wanted)] != wanted:
            continue
        rect = fitz.Rect(token_rects[index])
        for token_rect in token_rects[index + 1:index + len(wanted)]:
            rect.include_rect(token_rect)
        result.append(rect)
    return result


# Controls whose caption is printed WITHOUT its own box token run-in on the official
# form. Every other authored box ref must match number+caption as one printed sequence,
# so a fabricated box number cannot pass on a correct caption alone (the A9c reopen).
_W2_CAPTION_ONLY = {
    "/box=e/control=suffix": "Suff.",
    "/box=e/control=last_name": "Last name",
    "/box=13/option=retirement_plan": "Retirement plan",
    "/box=13/option=third_party_sick_pay": "Third-party sick pay",
    "/table=state_local/row_template=jurisdiction/column=employer_state_id": "Employer's state ID number",
}


# Box choices whose official form prints the box number once for the container and
# then prints these option captions without repeating the number. The reason is kept
# beside each exception so the caption-only surface is explicit and reviewable.
_FORM_1099_CAPTION_ONLY = {
    "form_1099b_2025": {
        "/box=2/option=long_term": (
            "Long-term gain or loss", "Box 2 prints one run-in number above its three term choices."
        ),
        "/box=2/option=ordinary": (
            "Ordinary", "Box 2 prints one run-in number above its three term choices."
        ),
        "/box=3/option=collectibles": (
            "Collectibles", "Box 3 prints one run-in number above its two proceeds choices."
        ),
        "/box=3/option=qof": (
            "QOF", "Box 3 prints one run-in number above its two proceeds choices."
        ),
        "/box=6/option=gross_proceeds": (
            "Gross proceeds", "Box 6 prints one run-in number above its two reporting choices."
        ),
        "/box=6/option=net_proceeds": (
            "Net proceeds", "Box 6 prints one run-in number above its two reporting choices."
        ),
    },
}


def _official_search_caption(address_id: str, address: dict) -> str:
    if "/box=12/row_template=entry/" in address_id:
        return "12a"
    for suffix, caption in _W2_CAPTION_ONLY.items():
        if address_id.endswith(suffix):
            return caption
    token = str(address["official_ref"]).removeprefix("Box ").strip()
    return f"{token} {address['printed_label']}"


def _form_1099_search_caption(document_id: str, address_id: str, address: dict) -> str:
    for suffix, (caption, reason) in _FORM_1099_CAPTION_ONLY.get(document_id, {}).items():
        assert reason
        if address_id.endswith(suffix):
            return caption
    token = str(address["official_ref"]).removeprefix("Box ").strip()
    return f"{token} {address['printed_label']}"


@pytest.mark.m15
def test_w2_authored_box_captions_are_adjacent_in_official_pdf(information_campaign) -> None:
    """Cross-check authored box NUMBER and caption against the printed official text."""
    payload = information_campaign["form_w2_2025"]
    addresses = {item["address_id"]: item for item in payload["registry"]["addresses"]}
    first_binding: dict[str, dict] = {}
    for binding in payload["widget_bindings"]["bindings"]:
        first_binding.setdefault(binding["address_id"], binding)
    pdf = _open_official_pdf("form_w2_2025")
    for address_id, address in addresses.items():
        if not str(address.get("official_ref", "")).startswith("Box "):
            continue
        binding = first_binding[address_id]
        caption = _official_search_caption(address_id, address)
        matches = _caption_rects(pdf[binding["page"] - 1], caption)
        assert matches, f"missing official printed sequence {caption!r} for {address['official_ref']}"
        widget = fitz.Rect(binding["rect"])
        assert min(_rect_distance(widget, match) for match in matches) <= 180, (
            f"official printed sequence {caption!r} is not adjacent to {address['official_ref']}"
        )


@pytest.mark.m15
def test_w2_adjacency_check_rejects_a_fabricated_box_number() -> None:
    """The A9c defect class must fail: right caption, wrong box number finds no match."""
    page = _open_official_pdf("form_w2_2025")[1]
    assert _caption_rects(page, "20 Locality name")
    assert not _caption_rects(page, "21 Locality name")
    assert _caption_rects(page, "16 State wages, tips, etc.")
    assert not _caption_rects(page, "17 State wages, tips, etc.")


@pytest.mark.m15
def test_fatca_checkbox_numbering_matches_each_official_revision(information_campaign) -> None:
    """Only the 1099-DIV prints a numbered FATCA box (Box 11); INT and W-2-style forms do not."""
    expected = {
        "form_1099_div_2025": "Box 11",
        "form_1099_int_2025": "FATCA filing requirement",
        "form_1099b_2025": "FATCA filing requirement",
    }
    for document_id, official_ref in expected.items():
        fatca = [
            item for item in information_campaign[document_id]["registry"]["addresses"]
            if item["path"][-1].get("token") == "fatca_filing_requirement"
        ]
        assert fatca, f"missing FATCA control for {document_id}"
        assert all(item["official_ref"] == official_ref for item in fatca)


@pytest.mark.m15
def test_1099_campaigns_collapse_copies_onto_authored_templates(information_campaign) -> None:
    expected = {
        "form_1099b_2025": (163, 39),
        "form_1099_div_2025": (140, 33),
        "form_1099_int_2025": (127, 30),
    }
    for document_id, (inventory, templates) in expected.items():
        payload = information_campaign[document_id]
        assert payload["coverage"] == {
            "inventory": inventory, "addressed_widgets": inventory, "exempt_widgets": 0,
            "node_bindings": 0, "references": 0,
        }
        assert len({item["address_id"] for item in payload["widget_bindings"]["bindings"]}) == templates
        assert all(item["printed_label"] for item in payload["registry"]["addresses"])


@pytest.mark.m15
@pytest.mark.parametrize("document_id", ["form_1099b_2025", "form_1099_div_2025", "form_1099_int_2025"])
def test_1099_authored_box_numbers_and_captions_are_adjacent_in_official_pdf(
    information_campaign, document_id: str,
) -> None:
    """Cross-check every authored box number and caption against local official text."""
    payload = information_campaign[document_id]
    addresses = {item["address_id"]: item for item in payload["registry"]["addresses"]}
    bindings_by_address: dict[str, list[dict]] = {}
    for binding in payload["widget_bindings"]["bindings"]:
        bindings_by_address.setdefault(binding["address_id"], []).append(binding)
    pdf = _open_official_pdf(document_id)
    for address_id, address in addresses.items():
        if not str(address.get("official_ref", "")).startswith("Box "):
            continue
        caption = _form_1099_search_caption(document_id, address_id, address)
        distances = []
        for binding in bindings_by_address[address_id]:
            matches = _caption_rects(pdf[binding["page"] - 1], caption)
            widget = fitz.Rect(binding["rect"])
            distances.extend(_rect_distance(widget, match) for match in matches)
        assert distances, f"missing official printed sequence {caption!r} for {address['official_ref']}"
        assert min(distances) <= 180, (
            f"official printed sequence {caption!r} is not adjacent to {address['official_ref']}"
        )


@pytest.mark.m15r
def test_intake_runtime_facts_have_one_address_per_control(information_campaign) -> None:
    payload = information_campaign["form_13614_c_2025"]
    bindings = payload["widget_bindings"]["bindings"]
    assert len(bindings) == 297
    assert len({item["field_name"] for item in bindings}) == 297
    addresses = {item["address_id"]: item for item in payload["registry"]["addresses"]}
    assert all(addresses[item["address_id"]]["path"][-2] == {"kind": "section", "token": "intake"} for item in bindings)
    assert any(addresses[item["address_id"]]["kind"] == "option" for item in bindings)


@pytest.mark.m15r
def test_information_routes_retain_authored_provenance(information_campaign) -> None:
    for document_id, payload in information_campaign.items():
        field_map = yaml.safe_load(
            (ROOT / "graph/2025/field_maps" / f"{document_id}.yaml").read_text(encoding="utf-8")
        )
        dispositions = {item["field_name"]: item for item in field_map["field_dispositions"]}
        assert {item["field_name"] for item in payload["widget_bindings"]["bindings"]} == set(payload["field_addresses"])
        assert set(payload["field_addresses"]) <= set(dispositions)
        for field_name, address_id in payload["field_addresses"].items():
            disposition = dispositions[field_name]
            assert disposition["address_id"] == address_id
            assert disposition.get("source_ref") or disposition.get("runtime_fact_ref")
        for field_name in set(dispositions) - set(payload["field_addresses"]):
            assert dispositions[field_name]["population_policy"] in {
                "user_entered", "imported", "copied", "computed", "decision_required",
                "intentionally_blank", "unsupported",
            }
