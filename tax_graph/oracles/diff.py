"""Box-level oracle differ with guard-box rejection."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Mapping

from tax_graph.engine import MISSING
from tax_graph.oracles.box_map import BoxMap, BoxMapping, GuardBox


@dataclass(frozen=True)
class BoxComparison:
    """One mapped Tax Graph node compared to one OTS output label."""

    node_id: str
    ots_label: str
    tax_graph_value: Any
    ots_value: Any
    status: str
    scenario: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GuardViolation:
    """A guard box that proves a scenario is outside the fenced domain."""

    guard_id: str
    ots_label: str
    expected: Any
    actual: Any
    reason: str
    scenario: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OracleDiffReport:
    """Structured result of a Tax Graph vs OTS box diff."""

    status: str
    comparisons: tuple[BoxComparison, ...] = ()
    guard_violations: tuple[GuardViolation, ...] = ()

    @property
    def disagreements(self) -> tuple[BoxComparison, ...]:
        """Return mapped boxes that did not agree."""

        return tuple(item for item in self.comparisons if item.status != "agree")

    @property
    def ok(self) -> bool:
        """Return whether the comparison agreed and no guard rejected it."""

        return self.status == "agreed"


def diff_engine_result(
    result: Any,
    ots_values: Mapping[str, Any],
    box_map: BoxMap,
    *,
    scenario: Any = None,
) -> OracleDiffReport:
    """Diff an engine ``Result`` against parsed OTS output labels."""

    return diff_values(result.values, ots_values, box_map, scenario=scenario)


def diff_values(
    tax_graph_values: Mapping[str, Any],
    ots_values: Mapping[str, Any],
    box_map: BoxMap,
    *,
    scenario: Any = None,
) -> OracleDiffReport:
    """Compare Tax Graph values to OTS labels through a box map."""

    scenario_payload = _scenario_payload(scenario)
    guard_violations = _check_guards(box_map.guards, ots_values, scenario_payload)
    if guard_violations:
        return OracleDiffReport(status="rejected", guard_violations=tuple(guard_violations))

    comparisons = tuple(
        comparison
        for box in box_map.boxes
        if _condition_applies(box, tax_graph_values)
        for comparison in (_compare_box(box, tax_graph_values, ots_values, scenario_payload),)
    )
    status = "agreed" if all(item.status == "agree" for item in comparisons) else "disagreed"
    return OracleDiffReport(status=status, comparisons=comparisons)


def _check_guards(
    guards: tuple[GuardBox, ...],
    ots_values: Mapping[str, Any],
    scenario: dict[str, Any],
) -> list[GuardViolation]:
    violations: list[GuardViolation] = []
    for guard in guards:
        if guard.ots_label not in ots_values:
            if guard.allow_absent:
                continue
            violations.append(
                GuardViolation(
                    guard_id=guard.guard_id,
                    ots_label=guard.ots_label,
                    expected=guard.expected,
                    actual=None,
                    reason="missing_guard_label",
                    scenario=scenario,
                )
            )
            continue
        actual = ots_values[guard.ots_label]
        if _whole_dollar(actual) != _whole_dollar(guard.expected):
            violations.append(
                GuardViolation(
                    guard_id=guard.guard_id,
                    ots_label=guard.ots_label,
                    expected=guard.expected,
                    actual=actual,
                    reason="guard_not_inert",
                    scenario=scenario,
                )
            )
    return violations


def _compare_box(
    box: BoxMapping,
    tax_graph_values: Mapping[str, Any],
    ots_values: Mapping[str, Any],
    scenario: dict[str, Any],
) -> BoxComparison:
    tax_value = tax_graph_values.get(box.node_id, MISSING)
    if tax_value is MISSING:
        return BoxComparison(
            node_id=box.node_id,
            ots_label=box.ots_label,
            tax_graph_value=tax_value,
            ots_value=ots_values.get(box.ots_label),
            status="missing_tax_graph",
            scenario=scenario,
        )
    if box.ots_label not in ots_values:
        if _whole_dollar(tax_value) == 0:
            return BoxComparison(
                node_id=box.node_id,
                ots_label=box.ots_label,
                tax_graph_value=tax_value,
                ots_value=None,
                status="agree",
                scenario=scenario,
            )
        return BoxComparison(
            node_id=box.node_id,
            ots_label=box.ots_label,
            tax_graph_value=tax_value,
            ots_value=None,
            status="missing_ots",
            scenario=scenario,
        )
    ots_value = ots_values[box.ots_label]
    status = "agree" if _whole_dollar(tax_value) == _whole_dollar(ots_value) else "disagree"
    return BoxComparison(
        node_id=box.node_id,
        ots_label=box.ots_label,
        tax_graph_value=tax_value,
        ots_value=ots_value,
        status=status,
        scenario=scenario,
    )


def _condition_applies(box: BoxMapping, tax_graph_values: Mapping[str, Any]) -> bool:
    if box.condition is None:
        return True
    if box.condition == "tax_graph_negative":
        value = tax_graph_values.get(box.node_id, MISSING)
        return value is not MISSING and value is not None and float(value) < 0
    raise ValueError(f"unsupported box-map condition: {box.condition}")


def _whole_dollar(value: Any) -> int | None:
    if value is None or value is MISSING:
        return None
    return round(float(value))


def _scenario_payload(scenario: Any) -> dict[str, Any]:
    if scenario is None:
        return {}
    if is_dataclass(scenario):
        return asdict(scenario)
    if isinstance(scenario, Mapping):
        return dict(scenario)
    return {"scenario": repr(scenario)}
