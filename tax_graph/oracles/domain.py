"""Domain profile and seeded generator for oracle fuzzing."""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from tax_graph.oracles.scenario import CapitalGainScenario


@dataclass(frozen=True)
class NumericRange:
    """Inclusive numeric range with optional preferred values."""

    minimum: int | float
    maximum: int | float
    include: tuple[int | float, ...] = ()


@dataclass(frozen=True)
class DomainProfile:
    """Fenced scenario domain for one form slice."""

    tax_year: str
    filing_statuses: tuple[str, ...]
    proceeds: NumericRange
    cost: NumericRange
    adjustment: NumericRange
    net_gain_loss: NumericRange
    date_acquired: str
    date_sold: str


def load_domain_profile(path: str | Path) -> DomainProfile:
    """Load a committed domain profile YAML file."""

    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    lot = data["single_lot"]
    return DomainProfile(
        tax_year=str(data["tax_year"]),
        filing_statuses=tuple(str(item) for item in data["filing_statuses"]),
        proceeds=_range(lot["proceeds"]),
        cost=_range(lot["cost"]),
        adjustment=_range(lot["adjustment"]),
        net_gain_loss=_range(lot["net_gain_loss"]),
        date_acquired=str(lot["date_acquired"]),
        date_sold=str(lot["date_sold"]),
    )


def generate_scenarios(profile: DomainProfile, *, n: int, seed: int) -> list[CapitalGainScenario]:
    """Generate deterministic in-domain scenarios."""

    if n < 0:
        raise ValueError("scenario count must be nonnegative")
    rng = random.Random(seed)
    return [_generate_one(profile, rng, seed=seed, index=index) for index in range(n)]


def assert_scenario_in_domain(profile: DomainProfile, scenario: CapitalGainScenario) -> None:
    """Raise if a scenario is outside the fenced profile."""

    if str(scenario.tax_year) != profile.tax_year:
        raise ValueError(f"tax_year outside domain: {scenario.tax_year}")
    if scenario.filing_status not in profile.filing_statuses:
        raise ValueError(f"filing_status outside domain: {scenario.filing_status}")
    _assert_in_range("proceeds", scenario.proceeds, profile.proceeds)
    _assert_in_range("cost", scenario.cost, profile.cost)
    _assert_in_range("adjustment", scenario.adjustment, profile.adjustment)
    _assert_in_range("net_gain_loss", scenario.gain_loss, profile.net_gain_loss)


def _generate_one(profile: DomainProfile, rng: random.Random, *, seed: int, index: int) -> CapitalGainScenario:
    for _attempt in range(1000):
        proceeds = _draw_number(rng, profile.proceeds)
        adjustment = _draw_number(rng, profile.adjustment)
        min_cost = profile.cost.minimum
        max_cost = min(
            profile.cost.maximum,
            proceeds + adjustment - profile.net_gain_loss.minimum,
        )
        if max_cost < min_cost:
            continue
        cost = _draw_number(rng, NumericRange(min_cost, max_cost, profile.cost.include))
        scenario = CapitalGainScenario(
            scenario_id=f"m6_seed{seed}_{index:04d}",
            tax_year=profile.tax_year,
            filing_status=rng.choice(profile.filing_statuses),
            description=f"Generated LT lot {index + 1}",
            date_acquired=profile.date_acquired,
            date_sold=profile.date_sold,
            proceeds=proceeds,
            cost=cost,
            adjustment=adjustment,
        )
        try:
            assert_scenario_in_domain(profile, scenario)
        except ValueError:
            continue
        return scenario
    raise ValueError("could not generate an in-domain scenario after 1000 attempts")


def _draw_number(rng: random.Random, range_: NumericRange) -> int | float:
    valid_includes = [item for item in range_.include if range_.minimum <= item <= range_.maximum]
    if valid_includes and rng.random() < 0.25:
        return rng.choice(valid_includes)
    if _is_int_like(range_.minimum) and _is_int_like(range_.maximum):
        return rng.randint(int(range_.minimum), int(range_.maximum))
    return round(rng.uniform(float(range_.minimum), float(range_.maximum)), 2)


def _range(data: dict[str, Any]) -> NumericRange:
    return NumericRange(
        minimum=data["min"],
        maximum=data["max"],
        include=tuple(data.get("include", [])),
    )


def _assert_in_range(name: str, value: int | float, range_: NumericRange) -> None:
    if value < range_.minimum or value > range_.maximum:
        raise ValueError(f"{name} outside domain: {value} not in [{range_.minimum}, {range_.maximum}]")


def _is_int_like(value: int | float) -> bool:
    return float(value).is_integer()
