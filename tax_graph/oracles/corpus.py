"""Frozen oracle corpus generation and replay."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

import yaml

from tax_graph.engine import TABLE_FACTS_KEY, Engine, Graph, load_facts
from tax_graph.oracles.box_map import load_box_map
from tax_graph.oracles.diff import OracleDiffReport, diff_engine_result
from tax_graph.oracles.domain import assert_scenario_in_domain, generate_scenarios, load_domain_profile
from tax_graph.oracles.ots import find_ots_1040_template, run_ots_1040
from tax_graph.oracles.scenario import (
    CapitalGainScenario,
    render_tax_graph_facts_document,
    render_tax_graph_facts_yaml,
    write_ots_input_bundle,
)


OtsRunner = Callable[..., Any]


@dataclass(frozen=True)
class FreezeCandidate:
    """One scenario and its freeze eligibility status."""

    scenario: CapitalGainScenario
    status: str = "agreed"
    disposition: str | None = None
    expected: Mapping[str, Any] | None = None


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
    executable: str | Path | None = None,
    output_dir: str | Path | None = None,
    template_path: str | Path | None = None,
    runner: OtsRunner = run_ots_1040,
) -> FrozenCorpusSummary:
    """Freeze generated scenarios after live OTS agreement."""

    if executable is None:
        raise ValueError("live OTS executable is required to freeze an oracle corpus")
    root_path = Path(root)
    profile = load_domain_profile(root_path / "oracles" / f"domain_{year}.yaml")
    box_map = load_box_map(root_path / "oracles" / f"box_map_{year}.yaml")
    graph = Graph(year, root=root_path, source=source)
    scenarios = generate_scenarios(profile, n=scenario_count, seed=seed)
    render_dir = (
        Path(output_dir)
        if output_dir is not None
        else root_path / "output" / "oracle_freeze" / f"{year}_seed{seed}"
    )
    render_template = _resolve_template_path(executable, year=year, template_path=template_path, runner=runner)
    candidates: list[FreezeCandidate] = []
    failures: list[str] = []
    for scenario in scenarios:
        assert_scenario_in_domain(profile, scenario)
        paths = write_ots_input_bundle(
            scenario,
            render_dir / scenario.scenario_id,
            template_path=render_template,
        )
        result = Engine(graph).execute(_facts_from_scenario(scenario))
        ots_result = runner(paths["input"], executable=executable)
        report = diff_engine_result(result, ots_result.labels, box_map, scenario=scenario)
        if report.status != "agreed":
            failures.append(f"{scenario.scenario_id}: {report.status}")
            continue
        candidates.append(
            FreezeCandidate(
                scenario=scenario,
                status=report.status,
                expected=expected_values_from_report(report),
            )
        )
    if failures:
        joined = ", ".join(failures[:5])
        more = "" if len(failures) <= 5 else f", ... ({len(failures)} total)"
        raise ValueError(f"cannot freeze corpus; live oracle did not agree for {joined}{more}")
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
        expected = dict(candidate.expected or {})
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
                    "source": "live_ots_diff_report",
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

    if candidate.status == "agreed" and candidate.expected:
        return
    if candidate.status == "agreed":
        raise ValueError(f"scenario {candidate.scenario.scenario_id} lacks oracle expected values")
    if candidate.disposition and candidate.expected:
        return
    if candidate.disposition:
        raise ValueError(f"scenario {candidate.scenario.scenario_id} lacks adjudicated expected values")
    raise ValueError(
        f"scenario {candidate.scenario.scenario_id} has status {candidate.status} "
        "and no adjudicated disposition"
    )


def expected_values_from_report(report: OracleDiffReport) -> dict[str, Any]:
    """Extract frozen expected values from an agreed live oracle report."""

    if report.status != "agreed":
        raise ValueError(f"cannot freeze expected values from {report.status} report")
    return {
        item.node_id: _clean_expected_value(
            item.tax_graph_value if item.ots_value is None else item.ots_value
        )
        for item in report.comparisons
    }


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


def _facts_from_scenario(scenario: CapitalGainScenario) -> dict[str, Any]:
    document = render_tax_graph_facts_document(scenario)
    facts = {fact["node_id"]: fact["value"] for fact in document["facts"]}
    if document.get("filing_status"):
        facts["taxpayer_2025_filing_status"] = document["filing_status"]
    if document.get("tables"):
        facts[TABLE_FACTS_KEY] = document["tables"]
    return facts


def _resolve_template_path(
    executable: str | Path,
    *,
    year: str,
    template_path: str | Path | None,
    runner: OtsRunner,
) -> Path | None:
    if template_path is not None:
        return Path(template_path)
    executable_path = Path(executable)
    if executable_path.exists() or runner is run_ots_1040:
        return find_ots_1040_template(executable_path, year=year)
    return None


def _clean_expected_value(value: Any) -> Any:
    if isinstance(value, (int, float)):
        number = float(value)
        return int(number) if number.is_integer() else value
    return value
