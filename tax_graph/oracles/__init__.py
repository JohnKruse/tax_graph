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
    "GuardViolation",
    "OracleDiffReport",
    "GuardBox",
    "OtsInstallError",
    "OtsRelease",
    "OtsRunError",
    "OtsRunResult",
    "find_ots_executable",
    "diff_engine_result",
    "diff_values",
    "install_ots_release",
    "load_box_map",
    "load_ots_label_inventory",
    "output_path_for",
    "parse_ots_output",
    "release_from_config",
    "render_ots_8949_csv",
    "render_ots_input_text",
    "render_tax_graph_facts_document",
    "render_tax_graph_facts_yaml",
    "run_ots_1040",
    "validate_box_map",
    "write_ots_input_bundle",
]
