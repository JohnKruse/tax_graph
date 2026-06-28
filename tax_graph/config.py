"""Configuration helpers for Tax Graph.

Phase M0 starts with a lightweight placeholder. The CLI step will expand this
module into the single configuration entry point described in the engineering
plan.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


DEFAULT_CONFIG_FILE = "tax-graph.config.yaml"


def project_root() -> Path:
    """Return the repository root when running from the source checkout."""
    return Path(__file__).resolve().parents[1]


def default_config_path(root: Path | None = None) -> Path:
    """Return the default user configuration path."""
    return (root or project_root()) / DEFAULT_CONFIG_FILE


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load configuration if present.

    The full precedence rules belong to Phase M0 Step 4. For now this function
    provides a stable import target and returns an empty configuration when no
    local config file exists.
    """
    config_path = Path(path) if path is not None else default_config_path()
    if not config_path.exists():
        return {}

    import yaml

    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return data or {}
