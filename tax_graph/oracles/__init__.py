"""Differential oracle adapters for Tax Graph."""

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

__all__ = [
    "OtsInstallError",
    "OtsRelease",
    "OtsRunError",
    "OtsRunResult",
    "find_ots_executable",
    "install_ots_release",
    "output_path_for",
    "parse_ots_output",
    "release_from_config",
    "run_ots_1040",
]
