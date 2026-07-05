"""Seeded oracle fuzz runner."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

import yaml

from tax_graph.config import get_config_value
from tax_graph.engine import MISSING, Engine, Graph
from tax_graph.oracles.box_map import load_box_map
from tax_graph.oracles.diff import OracleDiffReport, diff_engine_result
from tax_graph.oracles.domain import assert_scenario_in_domain, generate_scenarios, load_domain_profile
from tax_graph.oracles.ots import find_ots_1040_template, find_ots_executable, run_ots_1040
from tax_graph.oracles.scenario import CapitalGainScenario, render_tax_graph_facts_document, write_ots_input_bundle


OtsRunner = Callable[..., Any]


@dataclass(frozen=True)
class FuzzSummary:
    """Summary of a seeded oracle fuzz run."""

    generated: int
    agreed: int
    disagreed: int
    rejected: int
    triage_path: Path


def run_fuzz(
    *,
    year: str,
    n: int,
    seed: int,
    root: str | Path,
    output_dir: str | Path,
    executable: str | Path,
    source: str | None = None,
    runner: OtsRunner = run_ots_1040,
) -> FuzzSummary:
    """Generate scenarios, run Tax Graph and OTS, diff, and write triage."""

    root_path = Path(root)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    profile = load_domain_profile(root_path / "oracles" / f"domain_{year}.yaml")
    box_map = load_box_map(root_path / "oracles" / f"box_map_{year}.yaml")
    graph = Graph(year, root=root_path, source=source)
    scenarios = generate_scenarios(profile, n=n, seed=seed)
    template_path = find_ots_1040_template(executable, year=year)

    triage_entries: list[dict[str, Any]] = []
    agreed = disagreed = rejected = 0
    for scenario in scenarios:
        assert_scenario_in_domain(profile, scenario)
        scenario_dir = out_dir / scenario.scenario_id
        paths = write_ots_input_bundle(scenario, scenario_dir, template_path=template_path)
        facts = _facts_from_scenario(scenario)
        engine_result = Engine(graph).execute(facts)
        ots_result = runner(paths["input"], executable=executable)
        report = diff_engine_result(engine_result, ots_result.labels, box_map, scenario=scenario)
        if report.status == "agreed":
            agreed += 1
        elif report.status == "rejected":
            rejected += 1
            triage_entries.append(_triage_entry(scenario, report))
        else:
            disagreed += 1
            triage_entries.append(_triage_entry(scenario, report))

    triage_path = out_dir / "triage.yaml"
    triage_path.write_text(
        yaml.safe_dump(
            {
                "tax_year": int(year),
                "seed": seed,
                "scenario_count": n,
                "entries": triage_entries,
            },
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="utf-8",
        newline="\n",
    )
    return FuzzSummary(
        generated=len(scenarios),
        agreed=agreed,
        disagreed=disagreed,
        rejected=rejected,
        triage_path=triage_path,
    )


def resolve_ots_executable(config: dict[str, Any], *, root: str | Path, year: str) -> Path | None:
    """Resolve an OTS executable from env, config override, or install dir."""

    env_value = os.environ.get(f"OTS_1040_{year}_BIN")
    if env_value:
        return Path(env_value)
    configured = get_config_value(config, "oracles.opentaxsolver.executable")
    if configured:
        path = Path(str(configured))
        return path if path.is_absolute() else Path(root) / path
    install_dir = get_config_value(config, "oracles.opentaxsolver.install_dir")
    if not install_dir:
        return None
    install_path = Path(str(install_dir))
    if not install_path.is_absolute():
        install_path = Path(root) / install_path
    try:
        return find_ots_executable(install_path, year=year)
    except Exception:
        return None


def _facts_from_scenario(scenario: CapitalGainScenario) -> dict[str, Any]:
    document = render_tax_graph_facts_document(scenario)
    return {fact["node_id"]: fact["value"] for fact in document["facts"]}


def _triage_entry(scenario: CapitalGainScenario, report: OracleDiffReport) -> dict[str, Any]:
    return {
        "scenario": asdict(scenario),
        "status": report.status,
        "guard_violations": [_plain(asdict(item)) for item in report.guard_violations],
        "disagreements": [_plain(asdict(item)) for item in report.disagreements],
    }


def _plain(value: Any) -> Any:
    if value is MISSING:
        return "MISSING"
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value
