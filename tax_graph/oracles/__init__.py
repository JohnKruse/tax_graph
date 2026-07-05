"""Differential oracle adapters for Tax Graph."""

from tax_graph.oracles.box_map import (
    BoxMap,
    BoxMapValidationReport,
    BoxMapping,
    GuardBox,
    load_box_map,
    load_ots_label_inventory,
    validate_box_map,
)
from tax_graph.oracles.diff import (
    BoxComparison,
    GuardViolation,
    OracleDiffReport,
    diff_engine_result,
    diff_values,
)
from tax_graph.oracles.domain import (
    DomainProfile,
    assert_scenario_in_domain,
    generate_scenarios,
    load_domain_profile,
)
from tax_graph.oracles.fuzz import FuzzSummary, run_fuzz
from tax_graph.oracles.ots import (
    OtsInstallError,
    OtsRelease,
    OtsRunError,
    OtsRunResult,
    find_ots_executable,
    install_ots_release,
    output_path_for,
    parse_ots_output,
    release_from_config,
    run_ots_1040,
)
from tax_graph.oracles.scenario import (
    CapitalGainScenario,
    render_ots_8949_csv,
    render_ots_input_text,
    render_tax_graph_facts_document,
    render_tax_graph_facts_yaml,
    write_ots_input_bundle,
)

__all__ = [
    "BoxMap",
    "BoxMapValidationReport",
    "BoxMapping",
    "BoxComparison",
    "CapitalGainScenario",
    "DomainProfile",
    "FuzzSummary",
    "GuardViolation",
    "OracleDiffReport",
    "GuardBox",
    "OtsInstallError",
    "OtsRelease",
    "OtsRunError",
    "OtsRunResult",
    "assert_scenario_in_domain",
    "diff_engine_result",
    "diff_values",
    "find_ots_executable",
    "generate_scenarios",
    "install_ots_release",
    "load_box_map",
    "load_domain_profile",
    "load_ots_label_inventory",
    "output_path_for",
    "parse_ots_output",
    "release_from_config",
    "render_ots_8949_csv",
    "render_ots_input_text",
    "render_tax_graph_facts_document",
    "render_tax_graph_facts_yaml",
    "run_fuzz",
    "run_ots_1040",
    "validate_box_map",
    "write_ots_input_bundle",
]
