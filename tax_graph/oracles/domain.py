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
    wages: NumericRange
    taxable_interest: NumericRange
    qualified_dividends: NumericRange
    ordinary_dividends: NumericRange
    lot_count: NumericRange
    proceeds: NumericRange
    cost: NumericRange
    adjustment: NumericRange
    net_gain_loss: NumericRange
    long_term_date_acquired: str
    short_term_date_acquired: str
    date_sold: str
    supplemental_inputs: tuple["SupplementalInput", ...] = ()


@dataclass(frozen=True)
class SupplementalInput:
    """One additive modeled input exercised by the oracle domain."""

    node_id: str
    ots_input: str
    range: NumericRange
    tax_graph_multiplier: int | float = 1
    ots_multiplier: int | float = 1


def load_domain_profile(path: str | Path) -> DomainProfile:
    """Load a committed domain profile YAML file."""

    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    lot = data.get("multi_lot") or data["single_lot"]
    count = lot.get("count", {"min": 1, "max": 1, "include": [1]})
    return DomainProfile(
        tax_year=str(data["tax_year"]),
        filing_statuses=tuple(str(item) for item in data["filing_statuses"]),
        wages=_range(data["wages"]),
        taxable_interest=_range(data.get("taxable_interest", {"min": 0, "max": 0, "include": [0]})),
        qualified_dividends=_range(data.get("qualified_dividends", {"min": 0, "max": 0, "include": [0]})),
        ordinary_dividends=_range(data.get("ordinary_dividends", {"min": 0, "max": 0, "include": [0]})),
        lot_count=_range(count),
        proceeds=_range(lot["proceeds"]),
        cost=_range(lot["cost"]),
        adjustment=_range(lot["adjustment"]),
        net_gain_loss=_range(lot["net_gain_loss"]),
        long_term_date_acquired=str(lot["date_acquired"]),
        short_term_date_acquired=str(lot.get("short_term_date_acquired", lot["date_acquired"])),
        date_sold=str(lot["date_sold"]),
        supplemental_inputs=tuple(
            SupplementalInput(
                node_id=str(item["node_id"]),
                ots_input=str(item["ots_input"]),
                range=_range(item),
                tax_graph_multiplier=item.get("tax_graph_multiplier", 1),
                ots_multiplier=item.get("ots_multiplier", 1),
            )
            for item in data.get("supplemental_inputs", [])
        ),
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
    _assert_in_range("wages", scenario.wages, profile.wages)
    _assert_in_range("taxable_interest", scenario.taxable_interest, profile.taxable_interest)
    _assert_in_range("qualified_dividends", scenario.qualified_dividends, profile.qualified_dividends)
    _assert_in_range("ordinary_dividends", scenario.ordinary_dividends, profile.ordinary_dividends)
    for spec in profile.supplemental_inputs:
        if spec.node_id not in scenario.extra_tax_graph_facts:
            raise ValueError(f"missing supplemental Tax Graph fact: {spec.node_id}")
        if spec.ots_input not in scenario.extra_ots_inputs:
            raise ValueError(f"missing supplemental OTS input: {spec.ots_input}")
        fact_value = scenario.extra_tax_graph_facts[spec.node_id]
        ots_value = scenario.extra_ots_inputs[spec.ots_input]
        raw_fact = fact_value / spec.tax_graph_multiplier
        raw_ots = ots_value / spec.ots_multiplier
        if raw_fact != raw_ots:
            raise ValueError(
                f"supplemental values diverged for {spec.node_id} / {spec.ots_input}: "
                f"{raw_fact} != {raw_ots}"
            )
        _assert_in_range(spec.node_id, raw_fact, spec.range)


def _generate_one(profile: DomainProfile, rng: random.Random, *, seed: int, index: int) -> CapitalGainScenario:
    for _attempt in range(1000):
        filing_status = _draw_filing_status(profile, index=index)
        count = _draw_lot_count(profile, rng, index=index)
        target_profile = _target_income_profile(index=index, filing_status=filing_status)
        lots = tuple(
            _generate_lot(
                profile,
                rng,
                row_index=row_index,
                force_sign=_forced_sign(count, row_index, scenario_index=index, target_profile=target_profile),
                holding_period=_forced_holding_period(count, row_index, scenario_index=index),
            )
            for row_index in range(count)
        )
        supplemental_values = _supplemental_tax_graph_facts(profile, rng)
        wages, taxable_interest, qualified_dividends, ordinary_dividends = _core_income_values(
            profile,
            rng,
            filing_status=filing_status,
            index=index,
            gain_loss=_clean_number(sum(lot.gain_loss for lot in lots)),
            target_profile=target_profile,
        )
        scenario = CapitalGainScenario(
            scenario_id=f"m6_seed{seed}_{index:04d}",
            tax_year=profile.tax_year,
            filing_status=filing_status,
            description=f"Generated capital gains scenario {index + 1}",
            date_acquired=lots[0].date_acquired,
            date_sold=profile.date_sold,
            proceeds=lots[0].proceeds,
            cost=lots[0].cost,
            adjustment=lots[0].adjustment,
            holding_period=lots[0].holding_period,
            wages=wages,
            taxable_interest=taxable_interest,
            qualified_dividends=qualified_dividends,
            ordinary_dividends=ordinary_dividends,
            lots=lots,
            extra_tax_graph_facts=supplemental_values,
            extra_ots_inputs=_supplemental_ots_inputs(profile, supplemental_values),
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


def _draw_filing_status(profile: DomainProfile, *, index: int) -> str:
    statuses = profile.filing_statuses
    return statuses[index % len(statuses)]


def _supplemental_tax_graph_facts(profile: DomainProfile, rng: random.Random) -> dict[str, int | float]:
    return {
        spec.node_id: _draw_number(rng, spec.range) * spec.tax_graph_multiplier
        for spec in profile.supplemental_inputs
    }


def _supplemental_ots_inputs(
    profile: DomainProfile,
    values: dict[str, int | float],
) -> dict[str, int | float]:
    return {
        spec.ots_input: (values[spec.node_id] / spec.tax_graph_multiplier) * spec.ots_multiplier
        for spec in profile.supplemental_inputs
    }


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


def _forced_sign(count: int, row_index: int, *, scenario_index: int, target_profile: str | None) -> str | None:
    if target_profile and target_profile.startswith("regular_tax"):
        return "flat"
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
    if force_sign == "flat":
        return 0
    if force_sign == "severe_loss":
        return -rng.randint(3001, 10000)
    if force_sign == "gain":
        return rng.randint(100, 5000)
    if force_sign == "loss":
        return -rng.randint(100, 8000)
    if force_sign == "adjusted_gain":
        return rng.randint(100, 2000)
    return rng.randint(-8000, 5000)


STANDARD_DEDUCTION_BY_STATUS = {
    "single": 15750,
    "married_filing_jointly": 31500,
    "married_filing_separately": 15750,
    "head_of_household": 23625,
    "qualifying_surviving_spouse": 31500,
}


QDCGT_ZERO_BREAKPOINT_BY_STATUS = {
    "single": 48350,
    "married_filing_jointly": 96700,
    "married_filing_separately": 48350,
    "head_of_household": 64750,
    "qualifying_surviving_spouse": 96700,
}


QDCGT_FIFTEEN_BREAKPOINT_BY_STATUS = {
    "single": 533400,
    "married_filing_jointly": 600050,
    "married_filing_separately": 300000,
    "head_of_household": 566700,
    "qualifying_surviving_spouse": 600050,
}


def _target_income_profile(*, index: int, filing_status: str) -> str | None:
    forced_slot = index // len(STANDARD_DEDUCTION_BY_STATUS)
    if forced_slot == 0:
        return "regular_tax_below_table_boundary"
    if forced_slot == 1:
        return "regular_tax_at_table_boundary"
    if forced_slot == 2:
        return "qdcgt_below_zero_breakpoint"
    if forced_slot == 3:
        return "qdcgt_above_zero_breakpoint"
    if forced_slot == 4:
        return "qdcgt_below_fifteen_breakpoint"
    if forced_slot == 5:
        return "qdcgt_above_fifteen_breakpoint"
    return None


def _core_income_values(
    profile: DomainProfile,
    rng: random.Random,
    *,
    filing_status: str,
    index: int,
    gain_loss: int | float,
    target_profile: str | None,
) -> tuple[int | float, int | float, int | float, int | float]:
    if target_profile is None:
        wages = _draw_number(rng, profile.wages)
        taxable_interest = _draw_number(rng, profile.taxable_interest)
        qualified_dividends = _draw_number(rng, profile.qualified_dividends)
        ordinary_dividends = max(qualified_dividends, _draw_number(rng, profile.ordinary_dividends))
        return (
            _clean_number(wages),
            _clean_number(taxable_interest),
            _clean_number(qualified_dividends),
            _clean_number(ordinary_dividends),
        )

    standard_deduction = STANDARD_DEDUCTION_BY_STATUS[filing_status]
    taxable_interest = 0
    if target_profile == "regular_tax_below_table_boundary":
        target_taxable_income = 99999
        ordinary_dividends = 0
        qualified_dividends = 0
    elif target_profile == "regular_tax_at_table_boundary":
        target_taxable_income = 100000
        ordinary_dividends = 0
        qualified_dividends = 0
    elif target_profile == "qdcgt_below_zero_breakpoint":
        target_taxable_income = QDCGT_ZERO_BREAKPOINT_BY_STATUS[filing_status] - 1
        ordinary_dividends = 5000
        qualified_dividends = 5000
    elif target_profile == "qdcgt_above_zero_breakpoint":
        target_taxable_income = QDCGT_ZERO_BREAKPOINT_BY_STATUS[filing_status] + 1
        ordinary_dividends = 5000
        qualified_dividends = 5000
    elif target_profile == "qdcgt_below_fifteen_breakpoint":
        target_taxable_income = QDCGT_FIFTEEN_BREAKPOINT_BY_STATUS[filing_status] - 1
        ordinary_dividends = 5000
        qualified_dividends = 5000
    else:
        target_taxable_income = QDCGT_FIFTEEN_BREAKPOINT_BY_STATUS[filing_status] + 1
        ordinary_dividends = 5000
        qualified_dividends = 5000

    wages = target_taxable_income + standard_deduction - ordinary_dividends - _clean_number(gain_loss)
    return (
        _clean_number(wages),
        taxable_interest,
        qualified_dividends,
        ordinary_dividends,
    )


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
