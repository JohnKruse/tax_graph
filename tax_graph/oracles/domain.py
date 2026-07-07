"""Domain profile and seeded generator for oracle fuzzing."""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from tax_graph.oracles.scenario import CapitalGainLot, CapitalGainScenario


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
    lot_count: NumericRange
    proceeds: NumericRange
    cost: NumericRange
    adjustment: NumericRange
    net_gain_loss: NumericRange
    long_term_date_acquired: str
    short_term_date_acquired: str
    date_sold: str


def load_domain_profile(path: str | Path) -> DomainProfile:
    """Load a committed domain profile YAML file."""

    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    lot = data.get("multi_lot") or data["single_lot"]
    count = lot.get("count", {"min": 1, "max": 1, "include": [1]})
    return DomainProfile(
        tax_year=str(data["tax_year"]),
        filing_statuses=tuple(str(item) for item in data["filing_statuses"]),
        lot_count=_range(count),
        proceeds=_range(lot["proceeds"]),
        cost=_range(lot["cost"]),
        adjustment=_range(lot["adjustment"]),
        net_gain_loss=_range(lot["net_gain_loss"]),
        long_term_date_acquired=str(lot["date_acquired"]),
        short_term_date_acquired=str(lot.get("short_term_date_acquired", lot["date_acquired"])),
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
    _assert_in_range("lot_count", len(scenario.normalized_lots), profile.lot_count)
    for lot in scenario.normalized_lots:
        _assert_in_range("proceeds", lot.proceeds, profile.proceeds)
        _assert_in_range("cost", lot.cost, profile.cost)
        _assert_in_range("adjustment", lot.adjustment, profile.adjustment)
    _assert_in_range("net_gain_loss", scenario.gain_loss, profile.net_gain_loss)


def _generate_one(profile: DomainProfile, rng: random.Random, *, seed: int, index: int) -> CapitalGainScenario:
    for _attempt in range(1000):
        count = _draw_lot_count(profile, rng, index=index)
        lots = tuple(
            _generate_lot(
                profile,
                rng,
                row_index=row_index,
                force_sign=_forced_sign(count, row_index, scenario_index=index),
                holding_period=_forced_holding_period(count, row_index, scenario_index=index),
            )
            for row_index in range(count)
        )
        scenario = CapitalGainScenario(
            scenario_id=f"m6_seed{seed}_{index:04d}",
            tax_year=profile.tax_year,
            filing_status=rng.choice(profile.filing_statuses),
            description=f"Generated capital gains scenario {index + 1}",
            date_acquired=lots[0].date_acquired,
            date_sold=profile.date_sold,
            proceeds=lots[0].proceeds,
            cost=lots[0].cost,
            adjustment=lots[0].adjustment,
            holding_period=lots[0].holding_period,
            lots=lots,
        )
        try:
            assert_scenario_in_domain(profile, scenario)
        except ValueError:
            continue
        return scenario
    raise ValueError("could not generate an in-domain scenario after 1000 attempts")


def _draw_lot_count(profile: DomainProfile, rng: random.Random, *, index: int) -> int:
    includes = [int(item) for item in profile.lot_count.include if profile.lot_count.minimum <= item <= profile.lot_count.maximum]
    if index < len(includes):
        return includes[index]
    return int(_draw_number(rng, profile.lot_count))


def _generate_lot(
    profile: DomainProfile,
    rng: random.Random,
    *,
    row_index: int,
    force_sign: str | None,
    holding_period: str,
) -> CapitalGainLot:
    for _attempt in range(1000):
        adjustment = _draw_number(rng, profile.adjustment)
        if force_sign == "adjusted_gain" and adjustment == 0:
            adjustment = 50 if profile.adjustment.maximum >= 50 else profile.adjustment.maximum
        target_gain = _draw_lot_gain(rng, force_sign=force_sign)
        if target_gain >= 0:
            cost = _draw_number(rng, NumericRange(profile.cost.minimum, min(profile.cost.maximum, 20000), profile.cost.include))
            proceeds = cost + target_gain - adjustment
        else:
            proceeds = _draw_number(
                rng,
                NumericRange(profile.proceeds.minimum, min(profile.proceeds.maximum, 20000), profile.proceeds.include),
            )
            cost = proceeds + adjustment - target_gain
        proceeds = _clean_number(proceeds)
        cost = _clean_number(cost)
        if profile.proceeds.minimum <= proceeds <= profile.proceeds.maximum and profile.cost.minimum <= cost <= profile.cost.maximum:
            return CapitalGainLot(
                row_key=f"lot_{row_index + 1}",
                description=f"Generated {'ST' if holding_period == 'short_term' else 'LT'} lot {row_index + 1}",
                date_acquired=(
                    profile.short_term_date_acquired
                    if holding_period == "short_term"
                    else profile.long_term_date_acquired
                ),
                date_sold=profile.date_sold,
                proceeds=proceeds,
                cost=cost,
                adjustment=adjustment,
                holding_period=holding_period,
            )
    raise ValueError("could not generate an in-domain lot after 1000 attempts")


def _forced_sign(count: int, row_index: int, *, scenario_index: int) -> str | None:
    if scenario_index == 0 and row_index == 0:
        return "severe_loss"
    if count < 3:
        return None
    if row_index == 0:
        return "gain"
    if row_index == 1:
        return "loss"
    if row_index == 2:
        return "adjusted_gain"
    return None


def _forced_holding_period(count: int, row_index: int, *, scenario_index: int) -> str:
    if count == 1:
        return "long_term"
    if row_index == 0:
        return "short_term"
    if row_index == 1:
        return "long_term"
    return "short_term" if (scenario_index + row_index) % 2 else "long_term"


def _draw_lot_gain(rng: random.Random, *, force_sign: str | None) -> int:
    if force_sign == "severe_loss":
        return -rng.randint(3001, 10000)
    if force_sign == "gain":
        return rng.randint(100, 5000)
    if force_sign == "loss":
        return -rng.randint(100, 8000)
    if force_sign == "adjusted_gain":
        return rng.randint(100, 2000)
    return rng.randint(-8000, 5000)


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


def _clean_number(value: int | float) -> int | float:
    number = float(value)
    return int(number) if number.is_integer() else number
