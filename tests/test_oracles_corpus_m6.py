from __future__ import annotations

import yaml
from pathlib import Path

import pytest

from tax_graph.oracles.corpus import (
    FreezeCandidate,
    freeze_generated_corpus,
    replay_corpus,
    validate_freeze_candidate,
)
from tax_graph.oracles.domain import generate_scenarios, load_domain_profile


ROOT = Path(__file__).resolve().parents[1]


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
def test_disagreed_candidate_can_freeze_with_disposition():
    profile = load_domain_profile(ROOT / "oracles" / "domain_2025.yaml")
    scenario = generate_scenarios(profile, n=1, seed=404)[0]

    validate_freeze_candidate(
        FreezeCandidate(
            scenario=scenario,
            status="disagreed",
            disposition="our_bug_fixed_regression",
        )
    )


@pytest.mark.m6
def test_committed_oracle_corpus_replays():
    corpus_dir = ROOT / "examples" / "oracle_corpus"
    manifest = yaml.safe_load((corpus_dir / "corpus.yaml").read_text(encoding="utf-8"))

    report = replay_corpus(year="2025", root=ROOT, corpus_dir=corpus_dir, source="yaml")

    assert manifest["scenario_count"] >= 20
    assert report.ok
