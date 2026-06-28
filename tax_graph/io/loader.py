"""Shared YAML loading utilities.

The full graph loader is implemented in Phase M0 Step 2. This module already
contains the date normalization needed by both the validator and engine so YAML
implicit typing does not leak into schema validation.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Any

import yaml


def normalize_yaml_value(value: Any) -> Any:
    """Normalize YAML parser output into schema-friendly Python values."""
    if isinstance(value, dict):
        return {key: normalize_yaml_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_yaml_value(item) for item in value]
    if isinstance(value, (_dt.date, _dt.datetime)):
        return value.isoformat()
    return value


def load_yaml(path: str | Path) -> Any:
    """Load a YAML file and normalize values used by JSON Schema validation."""
    yaml_path = Path(path)
    return normalize_yaml_value(yaml.safe_load(yaml_path.read_text(encoding="utf-8")))
