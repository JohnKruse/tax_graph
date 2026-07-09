from __future__ import annotations

import csv
from types import SimpleNamespace

import yaml
from pathlib import Path

import pytest

from tax_graph.compile.tax_table import compute_tax_for_midpoint, generate_tax_table_ranges, load_brackets_from_graph
from tax_graph.oracles.corpus import (
    FreezeCandidate,
    freeze_generated_corpus,
    replay_corpus,
    validate_freeze_candidate,
)
from tax_graph.oracles.domain import generate_scenarios, load_domain_profile


ROOT = Path(__file__).resolve().parents[1]
BRACKETS = load_brackets_from_graph(ROOT, "2025")
STANDARD_DEDUCTION_BY_STATUS = {
    "Single": 15750,
    "Married/Joint": 31500,
    "Married/Sep": 15750,
    "Head_of_House": 23625,
    "Widow(er)": 31500,
}
STATUS_KEY_BY_OTS_STATUS = {
    "Single": "single",
    "Married/Joint": "married_filing_jointly",
    "Married/Sep": "married_filing_separately",
    "Head_of_House": "head_of_household",
    "Widow(er)": "qualifying_surviving_spouse",
}
TAX_TABLE_RANGES = generate_tax_table_ranges()


@pytest.mark.m6
def test_freeze_generated_corpus_replays(tmp_path):
    summary = freeze_generated_corpus(
        year="2025",
        root=ROOT,
        corpus_dir=tmp_path / "corpus",
        scenario_count=3,
        seed=101,
        generated_date="2026-07-05",
        oracle_version="test_ots",
        source="yaml",
        executable=tmp_path / "fake_ots.exe",
        runner=_fake_agreeing_ots_runner,
    )

    report = replay_corpus(year="2025", root=ROOT, corpus_dir=summary.corpus_dir, source="yaml")

    assert summary.scenario_count == 3
    assert report.ok
    assert report.scenario_count == 3


@pytest.mark.m6
def test_replay_corpus_detects_corrupted_expected_value(tmp_path):
    summary = freeze_generated_corpus(
        year="2025",
        root=ROOT,
        corpus_dir=tmp_path / "corpus",
        scenario_count=1,
        seed=202,
        generated_date="2026-07-05",
        oracle_version="test_ots",
        source="yaml",
        executable=tmp_path / "fake_ots.exe",
        runner=_fake_agreeing_ots_runner,
    )
    manifest = yaml.safe_load(summary.manifest_path.read_text(encoding="utf-8"))
    scenario_dir = summary.corpus_dir / manifest["entries"][0]["path"]
    expected_path = scenario_dir / "expected.yaml"
    expected = yaml.safe_load(expected_path.read_text(encoding="utf-8"))
    expected["expected"]["form_1040_2025_line_7_capital_gain_loss"] = 999999
    expected_path.write_text(yaml.safe_dump(expected, sort_keys=False), encoding="utf-8", newline="\n")

    report = replay_corpus(year="2025", root=ROOT, corpus_dir=summary.corpus_dir, source="yaml")

    assert not report.ok
    assert report.issues[0].node_id == "form_1040_2025_line_7_capital_gain_loss"


@pytest.mark.m6
def test_disagreed_candidate_cannot_freeze_without_disposition():
    profile = load_domain_profile(ROOT / "oracles" / "domain_2025.yaml")
    scenario = generate_scenarios(profile, n=1, seed=303)[0]

    with pytest.raises(ValueError, match="no adjudicated disposition"):
        validate_freeze_candidate(FreezeCandidate(scenario=scenario, status="disagreed"))


@pytest.mark.m6
def test_agreed_candidate_cannot_freeze_without_expected_values():
    profile = load_domain_profile(ROOT / "oracles" / "domain_2025.yaml")
    scenario = generate_scenarios(profile, n=1, seed=353)[0]

    with pytest.raises(ValueError, match="lacks oracle expected values"):
        validate_freeze_candidate(FreezeCandidate(scenario=scenario, status="agreed"))


@pytest.mark.m6
def test_disagreed_candidate_can_freeze_with_disposition():
    profile = load_domain_profile(ROOT / "oracles" / "domain_2025.yaml")
    scenario = generate_scenarios(profile, n=1, seed=404)[0]

    validate_freeze_candidate(
        FreezeCandidate(
            scenario=scenario,
            status="disagreed",
            disposition="our_bug_fixed_regression",
            expected={"form_1040_2025_line_7_capital_gain_loss": scenario.gain_loss},
        )
    )


@pytest.mark.m6
def test_committed_oracle_corpus_replays():
    corpus_dir = ROOT / "examples" / "oracle_corpus"
    manifest = yaml.safe_load((corpus_dir / "corpus.yaml").read_text(encoding="utf-8"))

    report = replay_corpus(year="2025", root=ROOT, corpus_dir=corpus_dir, source="yaml")

    assert manifest["scenario_count"] >= 20
    assert report.ok


def _fake_agreeing_ots_runner(input_path: str | Path, *, executable: str | Path):
    csv_path = Path(input_path).with_name(f"{Path(input_path).stem}_f8949.csv")
    input_text = Path(input_path).read_text(encoding="utf-8")
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    short_rows = [row for row in rows if str(row["Date_Acquired"]).endswith("2025")]
    long_rows = [row for row in rows if row not in short_rows]
    proceeds = _clean_number(sum(_clean_number(row["Proceeds"]) for row in long_rows))
    cost = _clean_number(sum(_clean_number(row["Cost"]) for row in long_rows))
    adjustment = _clean_number(sum(_clean_number(row.get("Adjustment") or 0) for row in long_rows))
    long_gain = _clean_number(proceeds - cost + adjustment)
    short_gain = _gain(short_rows)
    total = _clean_number(short_gain + long_gain)
    line_7 = max(total, -3000)
    extra_inputs = _parse_numeric_inputs(
        input_text,
        (
            "Status",
            "L1a",
            "S1_8z",
            "S1_21",
            "S1A_2a",
            "S2_1a",
            "S2_17z",
            "S3_1",
            "S3_13z",
            "A5a",
            "A15",
            "A16",
            "L2b",
            "L3a",
            "L3b",
            "AMTws2c",
            "AMTws2g",
        ),
    )
    status = str(extra_inputs.get("Status", "Single"))
    agi = _clean_number(extra_inputs.get("L1a", 0) + extra_inputs.get("L2b", 0) + extra_inputs.get("L3b", 0) + line_7)
    deduction = STANDARD_DEDUCTION_BY_STATUS[status]
    taxable_income = max(_clean_number(agi - deduction), 0)
    tax = _regular_tax(taxable_income, STATUS_KEY_BY_OTS_STATUS[status])
    return SimpleNamespace(
        labels={
            "A5a": extra_inputs.get("A5a", 0),
            "A15": extra_inputs.get("A15", 0),
            "A16": extra_inputs.get("A16", 0),
            "AMT_Form_6251_L2c": extra_inputs.get("AMTws2c", 0),
            "AMT_Form_6251_L2g": extra_inputs.get("AMTws2g", 0),
            "B4": extra_inputs.get("L2b", 0),
            "B6": extra_inputs.get("L3b", 0),
            "F8949_2d": proceeds,
            "F8949_2e": cost,
            "F8949_2g": adjustment,
            "F8949_2h": long_gain,
            "D1bh": short_gain,
            "D7": short_gain,
            "D8bh": long_gain,
            "D15": long_gain,
            "D16": total,
            "D21": line_7 if total < 0 else 0,
            "L7a": line_7,
            "L11b": agi,
            "L12": deduction,
            "L15": taxable_income,
            "L16": tax,
            "S1_3": 0,
            "S1_8z": extra_inputs.get("S1_8z", 0),
            "S1_21": extra_inputs.get("S1_21", 0),
            "S1A_2a": extra_inputs.get("S1A_2a", 0),
            "S2_1a": extra_inputs.get("S2_1a", 0),
            "S2_18": extra_inputs.get("S2_17z", 0),
            "S3_1": extra_inputs.get("S3_1", 0),
            "S3_9": 0,
            "S3_13z": extra_inputs.get("S3_13z", 0),
        }
    )


def _gain(rows):
    proceeds = _clean_number(sum(_clean_number(row["Proceeds"]) for row in rows))
    cost = _clean_number(sum(_clean_number(row["Cost"]) for row in rows))
    adjustment = _clean_number(sum(_clean_number(row.get("Adjustment") or 0) for row in rows))
    return _clean_number(proceeds - cost + adjustment)


def _clean_number(value):
    number = float(value or 0)
    return int(number) if number.is_integer() else number


def _parse_numeric_inputs(text, labels):
    values = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        for label in sorted(labels, key=len, reverse=True):
            if not (line == label or line.startswith(f"{label} ") or line.startswith(f"{label}:")):
                continue
            if label == "Status":
                payload = line[len(label) :].replace(":", " ").strip()
                values[label] = payload.split()[0] if payload else "Single"
                break
            payload = line[len(label) :].replace(":", " ").strip()
            token = payload.split()[0] if payload else ""
            if not token:
                values[label] = 0
                continue
            try:
                values[label] = _clean_number(token)
            except ValueError:
                values[label] = 0
            break
    return values


def _regular_tax(taxable_income, filing_status):
    if taxable_income <= 0:
        return 0
    if taxable_income < 100000:
        for income_min, income_max in TAX_TABLE_RANGES:
            if income_min <= taxable_income < income_max:
                midpoint = (income_min + income_max) / 2.0
                return compute_tax_for_midpoint(midpoint, filing_status, BRACKETS)
    return _clean_number(_bracket_tax(taxable_income, filing_status))


def _bracket_tax(taxable_income, filing_status):
    tiers = BRACKETS[filing_status]
    for tier in reversed(tiers):
        if taxable_income >= tier["floor"]:
            return tier["cumulative"] + tier["rate"] * (taxable_income - tier["floor"])
    return 0
