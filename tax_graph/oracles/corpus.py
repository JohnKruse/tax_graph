"""Frozen oracle corpus generation and replay."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from tax_graph.engine import Engine, Graph, load_facts
from tax_graph.oracles.box_map import BoxMap, load_box_map
from tax_graph.oracles.domain import assert_scenario_in_domain, generate_scenarios, load_domain_profile
from tax_graph.oracles.scenario import CapitalGainScenario, render_tax_graph_facts_yaml


@dataclass(frozen=True)
class FreezeCandidate:
    """One scenario and its freeze eligibility status."""

    scenario: CapitalGainScenario
    status: str = "agreed"
    disposition: str | None = None


@dataclass(frozen=True)
class FrozenCorpusSummary:
    """Summary of a frozen corpus write."""

    corpus_dir: Path
    scenario_count: int
    manifest_path: Path


@dataclass(frozen=True)
class ReplayIssue:
    """One corpus replay mismatch."""

    scenario_id: str
    node_id: str
    expected: Any
    actual: Any


@dataclass(frozen=True)
class ReplayReport:
    """Result of replaying a frozen corpus."""

    scenario_count: int
    issues: tuple[ReplayIssue, ...]

    @property
    def ok(self) -> bool:
        """Return whether every frozen expected value matched."""

        return not self.issues


def freeze_generated_corpus(
    *,
    year: str,
    root: str | Path,
    corpus_dir: str | Path,
    scenario_count: int,
    seed: int,
    generated_date: str,
    oracle_version: str,
    source: str | None = None,
) -> FrozenCorpusSummary:
    """Freeze generated in-domain scenarios as offline replay fixtures."""

    root_path = Path(root)
    profile = load_domain_profile(root_path / "oracles" / f"domain_{year}.yaml")
    scenarios = generate_scenarios(profile, n=scenario_count, seed=seed)
    candidates = [FreezeCandidate(scenario=scenario, status="agreed") for scenario in scenarios]
    return freeze_candidates(
        candidates,
        year=year,
        root=root_path,
        corpus_dir=corpus_dir,
        seed=seed,
        generated_date=generated_date,
        oracle_version=oracle_version,
        source=source,
    )


def freeze_candidates(
    candidates: list[FreezeCandidate],
    *,
    year: str,
    root: str | Path,
    corpus_dir: str | Path,
    seed: int,
    generated_date: str,
    oracle_version: str,
    source: str | None = None,
) -> FrozenCorpusSummary:
    """Write eligible candidates into a frozen example corpus."""

    root_path = Path(root)
    output_dir = Path(corpus_dir)
    profile = load_domain_profile(root_path / "oracles" / f"domain_{year}.yaml")
    box_map = load_box_map(root_path / "oracles" / f"box_map_{year}.yaml")
    graph = Graph(year, root=root_path, source=source)
    output_dir.mkdir(parents=True, exist_ok=True)

    entries: list[dict[str, Any]] = []
    for candidate in candidates:
        validate_freeze_candidate(candidate)
        assert_scenario_in_domain(profile, candidate.scenario)
        scenario_dir = output_dir / candidate.scenario.scenario_id
        scenario_dir.mkdir(parents=True, exist_ok=True)
        (scenario_dir / "facts.yaml").write_text(
            render_tax_graph_facts_yaml(candidate.scenario),
            encoding="utf-8",
            newline="\n",
        )
        expected = expected_values_for_scenario(candidate.scenario, graph, box_map)
        (scenario_dir / "expected.yaml").write_text(
            _dump_yaml({"expected": expected}),
            encoding="utf-8",
            newline="\n",
        )
        entries.append(
            {
                "scenario_id": candidate.scenario.scenario_id,
                "path": candidate.scenario.scenario_id,
                "status": candidate.status,
                "disposition": candidate.disposition,
            }
        )

    manifest_path = output_dir / "corpus.yaml"
    manifest_path.write_text(
        _dump_yaml(
            {
                "tax_year": int(year),
                "scenario_count": len(candidates),
                "seed": seed,
                "generated_date": generated_date,
                "provenance": {
                    "oracle": "opentaxsolver",
                    "oracle_version": oracle_version,
                    "source": "m6_seeded_single_lot_corpus",
                },
                "entries": entries,
            }
        ),
        encoding="utf-8",
        newline="\n",
    )
    return FrozenCorpusSummary(
        corpus_dir=output_dir,
        scenario_count=len(candidates),
        manifest_path=manifest_path,
    )


def validate_freeze_candidate(candidate: FreezeCandidate) -> None:
    """Reject candidates that lack an oracle agreement or disposition."""

    if candidate.status == "agreed":
        return
    if candidate.disposition:
        return
    raise ValueError(
        f"scenario {candidate.scenario.scenario_id} has status {candidate.status} "
        "and no adjudicated disposition"
    )


def expected_values_for_scenario(
    scenario: CapitalGainScenario,
    graph: Graph,
    box_map: BoxMap,
) -> dict[str, Any]:
    """Compute frozen expected values for mapped Tax Graph boxes."""

    facts_path_values = yaml.safe_load(render_tax_graph_facts_yaml(scenario))["facts"]
    facts = {item["node_id"]: item["value"] for item in facts_path_values}
    result = Engine(graph).execute(facts)
    expected: dict[str, Any] = {}
    for box in box_map.boxes:
        expected[box.node_id] = result.values[box.node_id]
    return expected


def replay_corpus(*, year: str, root: str | Path, corpus_dir: str | Path, source: str | None = None) -> ReplayReport:
    """Replay a frozen corpus against the current Tax Graph engine."""

    root_path = Path(root)
    graph = Graph(year, root=root_path, source=source)
    manifest = _load_manifest(corpus_dir)
    issues: list[ReplayIssue] = []
    for entry in manifest.get("entries", []):
        scenario_id = str(entry["scenario_id"])
        scenario_dir = Path(corpus_dir) / str(entry["path"])
        facts = load_facts(scenario_dir / "facts.yaml")
        expected = yaml.safe_load((scenario_dir / "expected.yaml").read_text(encoding="utf-8"))["expected"]
        result = Engine(graph).execute(facts)
        for node_id, want in expected.items():
            got = result.values[node_id]
            if got != want:
                issues.append(
                    ReplayIssue(
                        scenario_id=scenario_id,
                        node_id=node_id,
                        expected=want,
                        actual=got,
                    )
                )
    return ReplayReport(scenario_count=len(manifest.get("entries", [])), issues=tuple(issues))


def load_triage_log(path: str | Path) -> dict[str, Any]:
    """Load the oracle triage log."""

    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def _load_manifest(corpus_dir: str | Path) -> Mapping[str, Any]:
    return yaml.safe_load((Path(corpus_dir) / "corpus.yaml").read_text(encoding="utf-8")) or {}


def _dump_yaml(data: dict[str, Any]) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=False)


def candidate_to_dict(candidate: FreezeCandidate) -> dict[str, Any]:
    """Return a plain mapping useful for future triage serialization."""

    data = asdict(candidate)
    return data
