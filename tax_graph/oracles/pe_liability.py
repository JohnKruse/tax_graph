"""PolicyEngine liability-level witness over the frozen oracle corpus (M11 Step 5b).

PolicyEngine US is the SECOND independent liability witness beside OTS. It has one
known modeling divergence from IRS filing mechanics: it computes the bracket formula
at every income level and does not quantize tax through the under-$100k IRS Tax
Table (whose 50-dollar bands price tax at the band midpoint). Within the table
region the worst-case legitimate divergence for the table's top 22% band is
50 * 0.22 / 2 = 5.50 dollars plus a rounding dollar, so comparisons below the
$100,000 boundary use an explicit, documented tolerance while comparisons at or
above it require whole-dollar agreement. Taxable income (line 15) must agree
exactly at whole-dollar everywhere.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import yaml

TABLE_REGION_MAX = 100000
TABLE_REGION_TOLERANCE = 6.5  # 50-dollar band midpoint pricing (max 5.50) + rounding

_FILING_STATUS_TO_PE = {
    "single": ("SINGLE", False),
    "married_filing_jointly": ("JOINT", True),
    "married_filing_separately": ("SEPARATE", False),
    "head_of_household": ("HEAD_OF_HOUSEHOLD", False),
    "qualifying_surviving_spouse": ("SURVIVING_SPOUSE", False),
}


@dataclass(frozen=True)
class PEScenarioInputs:
    """The slice of a frozen corpus scenario PolicyEngine needs."""

    scenario_id: str
    filing_status: str
    wages: float
    taxable_interest: float
    qualified_dividends: float
    ordinary_dividends: float
    short_term_gain: float
    long_term_gain: float


@dataclass(frozen=True)
class PELiabilityResult:
    scenario_id: str
    status: str  # agree_exact | agree_within_table_tolerance | disagree | fetch_error
    expected_taxable_income: float | None = None
    pe_taxable_income: float | None = None
    expected_tax: float | None = None
    pe_tax: float | None = None
    reason: str | None = None


@dataclass(frozen=True)
class PELiabilityReport:
    year: str
    pe_version: str
    results: tuple[PELiabilityResult, ...]

    def count(self, status: str) -> int:
        return sum(1 for r in self.results if r.status == status)

    @property
    def ok(self) -> bool:
        return all(r.status.startswith("agree") for r in self.results)

    def format_report(self) -> str:
        lines = [
            f"=== PolicyEngine liability diff ({self.year}) ===",
            f"  pe_version: {self.pe_version}",
            f"  scenarios: {len(self.results)}",
            f"  agree_exact: {self.count('agree_exact')}",
            f"  agree_within_table_tolerance: {self.count('agree_within_table_tolerance')}",
            f"  disagree: {self.count('disagree')}",
            f"  fetch_error: {self.count('fetch_error')}",
        ]
        for r in self.results:
            if r.status in ("disagree", "fetch_error"):
                lines.append(
                    f"  - {r.scenario_id} ({r.status}): {r.reason}"
                    f" [taxable expected={r.expected_taxable_income} pe={r.pe_taxable_income};"
                    f" tax expected={r.expected_tax} pe={r.pe_tax}]"
                )
        return "\n".join(lines) + "\n"


def scenario_inputs_from_facts(facts_doc: dict[str, Any]) -> PEScenarioInputs:
    """Extract PolicyEngine inputs from a frozen corpus facts document."""

    by_node = {fact["node_id"]: fact["value"] for fact in facts_doc.get("facts", [])}
    short_term = 0.0
    long_term = 0.0
    for table in facts_doc.get("tables", []):
        table_id = str(table.get("table_id", ""))
        for row in table.get("rows", []):
            cols = row.get("columns", {})
            gain = float(cols.get("d", 0)) - float(cols.get("e", 0)) + float(cols.get("g", 0))
            # NB: "part_i" is a substring of "part_ii" - match the segment.
            if "part_ii" in table_id:
                long_term += gain
            else:
                short_term += gain
    return PEScenarioInputs(
        scenario_id=str(facts_doc.get("scenario_id", "")),
        filing_status=str(facts_doc.get("filing_status", "single")),
        wages=float(by_node.get("form_1040_2025_root_line_1a", 0) or 0),
        taxable_interest=float(by_node.get("form_1040_2025_root_line_2b", 0) or 0),
        qualified_dividends=float(by_node.get("form_1040_2025_root_line_3a", 0) or 0),
        ordinary_dividends=float(by_node.get("form_1040_2025_root_line_3b", 0) or 0),
        short_term_gain=short_term,
        long_term_gain=long_term,
    )


def build_situation(inputs: PEScenarioInputs, year: str | int) -> dict[str, Any]:
    """Render scenario inputs as a PolicyEngine US household situation."""

    period = str(year)
    pe_status, needs_spouse = _FILING_STATUS_TO_PE[inputs.filing_status]
    people: dict[str, Any] = {
        "you": {
            "age": {period: 40},
            "employment_income": {period: inputs.wages},
            "taxable_interest_income": {period: inputs.taxable_interest},
            "qualified_dividend_income": {period: inputs.qualified_dividends},
            "non_qualified_dividend_income": {
                period: max(inputs.ordinary_dividends - inputs.qualified_dividends, 0)
            },
            "short_term_capital_gains": {period: inputs.short_term_gain},
            "long_term_capital_gains": {period: inputs.long_term_gain},
        }
    }
    members = ["you"]
    if needs_spouse:
        people["spouse"] = {"age": {period: 40}}
        members.append("spouse")
    return {
        "people": people,
        "tax_units": {"tax_unit": {"members": members, "filing_status": {period: pe_status}}},
        "households": {"household": {"members": members, "state_name": {period: "TX"}}},
    }


def _live_pe_fetcher(year: str | int) -> tuple[Callable[[PEScenarioInputs], tuple[float, float]], str]:
    try:
        import policyengine_us
        from policyengine_us import Simulation
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise RuntimeError(
            "policyengine-us is not installed; install the policyengine extra or "
            "pass an offline fixture"
        ) from exc

    version = getattr(policyengine_us, "__version__", None) or "unknown"

    def fetch(inputs: PEScenarioInputs) -> tuple[float, float]:
        sim = Simulation(situation=build_situation(inputs, year))
        taxable = float(sim.calculate("taxable_income", int(year))[0])
        # 1040 line 16 = tax on the ordinary portion (main rates) PLUS the
        # QDCGT preferential tax; PE splits these into two variables and its
        # regular_tax_before_credits carries only the main-rates component.
        tax = float(sim.calculate("income_tax_main_rates", int(year))[0]) + float(
            sim.calculate("capital_gains_tax", int(year))[0]
        )
        return taxable, tax

    return fetch, version


def _fixture_fetcher(path: Path) -> tuple[Callable[[PEScenarioInputs], tuple[float, float]], str]:
    data = json.loads(path.read_text(encoding="utf-8"))

    def fetch(inputs: PEScenarioInputs) -> tuple[float, float]:
        entry = data["scenarios"][inputs.scenario_id]
        return float(entry["taxable_income"]), float(entry["tax"])

    return fetch, str(data.get("pe_version", "offline-fixture"))


def _half_up(value: float) -> int:
    return math.floor(value + 0.5) if value >= 0 else math.ceil(value - 0.5)


def run_pe_liability(
    *,
    year: str | int,
    corpus_dir: str | Path,
    offline_fixture: str | Path | None = None,
) -> PELiabilityReport:
    """Diff PolicyEngine liability against the frozen OTS-agreed corpus values."""

    corpus_path = Path(corpus_dir)
    manifest = yaml.safe_load((corpus_path / "corpus.yaml").read_text(encoding="utf-8")) or {}
    if offline_fixture is not None:
        fetch, version = _fixture_fetcher(Path(offline_fixture))
    else:
        fetch, version = _live_pe_fetcher(year)

    results: list[PELiabilityResult] = []
    for entry in manifest.get("entries", []):
        scenario_dir = corpus_path / str(entry["path"])
        facts_doc = yaml.safe_load((scenario_dir / "facts.yaml").read_text(encoding="utf-8"))
        expected = yaml.safe_load((scenario_dir / "expected.yaml").read_text(encoding="utf-8"))["expected"]
        inputs = scenario_inputs_from_facts(facts_doc)
        expected_taxable = expected.get("form_1040_2025_root_line_15")
        expected_tax = expected.get("form_1040_2025_root_line_16")
        if expected_taxable is None or expected_tax is None:
            results.append(
                PELiabilityResult(
                    scenario_id=inputs.scenario_id,
                    status="fetch_error",
                    reason="frozen corpus entry lacks line 15/16 expected values",
                )
            )
            continue
        try:
            pe_taxable, pe_tax = fetch(inputs)
        except Exception as exc:  # noqa: BLE001 - reported, never silent
            results.append(
                PELiabilityResult(
                    scenario_id=inputs.scenario_id,
                    status="fetch_error",
                    expected_taxable_income=expected_taxable,
                    expected_tax=expected_tax,
                    reason=f"PE simulation error: {exc}",
                )
            )
            continue

        common = {
            "scenario_id": inputs.scenario_id,
            "expected_taxable_income": expected_taxable,
            "pe_taxable_income": pe_taxable,
            "expected_tax": expected_tax,
            "pe_tax": pe_tax,
        }
        if _half_up(pe_taxable) != _half_up(float(expected_taxable)):
            results.append(
                PELiabilityResult(status="disagree", reason="taxable income mismatch", **common)
            )
            continue
        tax_delta = abs(pe_tax - float(expected_tax))
        if _half_up(pe_tax) == _half_up(float(expected_tax)):
            results.append(PELiabilityResult(status="agree_exact", **common))
        elif float(expected_taxable) < TABLE_REGION_MAX and tax_delta <= TABLE_REGION_TOLERANCE:
            results.append(PELiabilityResult(status="agree_within_table_tolerance", **common))
        else:
            results.append(
                PELiabilityResult(
                    status="disagree",
                    reason=f"tax mismatch beyond tolerance (delta {tax_delta:.2f})",
                    **common,
                )
            )

    return PELiabilityReport(year=str(year), pe_version=version, results=tuple(results))
