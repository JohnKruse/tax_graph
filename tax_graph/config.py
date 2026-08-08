"""Configuration helpers for Tax Graph."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

import yaml


DEFAULT_CONFIG_FILE = "tax-graph.config.yaml"
CONFIG_DIR_CONFIG_FILE = "config/tax-graph.config.yaml"


class ModelConfigurationError(ValueError):
    """Raised when a requested LLM model is absent or malformed."""


_MODEL_CONFIG_PATHS = {
    "primary": "llm.model",
    "micro": "llm.micro_model",
    "example": "llm.example_model",
    "nversion": "llm.nversion_model",
}


def project_root() -> Path:
    """Return the source checkout root or packaged runtime-data root.

    Wheels keep the shipped graph, schemas, and runtime fixtures below
    ``tax_graph/assets``.  A source checkout retains the established layout at
    the repository root, so local development and installed use share one
    root contract.
    """
    package_dir = Path(__file__).resolve().parent
    source_root = package_dir.parent
    if (source_root / "graph").is_dir():
        return source_root
    packaged_root = package_dir / "assets"
    if (packaged_root / "graph").is_dir():
        return packaged_root
    return source_root


def default_config_path(root: str | Path | None = None) -> Path:
    """Return the default user configuration path.

    The repository's ignored ``config/`` copy is a legacy fixture location,
    not a second live developer configuration.  Keep the fallback for copied
    hermetic project roots, but never select it for the real checkout when the
    root-level user config is absent.
    """
    base = Path(root) if root is not None else project_root()
    root_config = base / DEFAULT_CONFIG_FILE
    if root_config.exists():
        return root_config
    if base.resolve() == project_root().resolve():
        return root_config
    config_dir_config = base / CONFIG_DIR_CONFIG_FILE
    if config_dir_config.exists():
        return config_dir_config
    return root_config


def load_config(path: str | Path | None = None, root: str | Path | None = None) -> dict[str, Any]:
    """Load ``tax-graph.config.yaml`` if present.

    Missing config is valid for the local-first defaults used by the current
    package and CLI.
    """
    config_path = Path(path) if path is not None else default_config_path(root)
    if not config_path.exists():
        return {}

    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return data or {}


def get_config_value(config: dict[str, Any], dotted_path: str, default: Any = None) -> Any:
    """Read a nested config value using a dotted path."""
    value: Any = config
    for part in dotted_path.split("."):
        if not isinstance(value, dict) or part not in value:
            return default
        value = value[part]
    return value


def resolve_llm_model(config: Mapping[str, Any], role: str = "primary") -> str:
    """Resolve one explicitly configured model without selecting a vendor.

    Model selection is a configuration contract, not a call-site convenience.
    Each purpose has its own key so a missing or renamed setting fails with a
    typed error instead of silently changing the model family or emitting a
    placeholder model id.  The caller may use the primary role explicitly for
    a purpose that is intentionally run by the primary model.
    """
    try:
        path = _MODEL_CONFIG_PATHS[role]
    except KeyError as exc:
        allowed = ", ".join(sorted(_MODEL_CONFIG_PATHS))
        raise ModelConfigurationError(
            f"unknown LLM model role {role!r}; expected one of {allowed}"
        ) from exc
    value = get_config_value(dict(config), path)
    if value is None or not str(value).strip():
        raise ModelConfigurationError(f"{path} is required for LLM role {role}")
    return str(value).strip()


def resolve_llm_seed(config: Mapping[str, Any]) -> int | None:
    """Resolve the optional provider seed, preserving an explicit zero."""
    value = get_config_value(dict(config), "llm.seed")
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ModelConfigurationError("llm.seed must be an integer or null")
    if isinstance(value, float) and not value.is_integer():
        raise ModelConfigurationError("llm.seed must be an integer or null")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ModelConfigurationError("llm.seed must be an integer or null") from exc


def derive_vendor_family(model: str) -> str:
    """Derive a stable vendor-family label from a model id."""
    value = str(model).strip().lstrip("~")
    if not value:
        raise ModelConfigurationError("model id must be non-empty")
    return value.split("/", 1)[0]


def resolve_secret(
    config: dict[str, Any],
    value_path: str,
    *,
    keyring_path: str | None = None,
    env_path: str | None = None,
) -> str | None:
    """Resolve a secret by config value, then OS keyring, then environment.

    ``keyring_path`` and ``env_path`` point to config entries containing the
    keyring service name and environment variable name. The optional keyring
    dependency is imported lazily so non-secret commands do not require it.
    """
    explicit_value = get_config_value(config, value_path)
    if explicit_value:
        return str(explicit_value)

    keyring_name = get_config_value(config, keyring_path) if keyring_path else None
    if keyring_name:
        keyring_value = _read_keyring_secret(str(keyring_name))
        if keyring_value:
            return keyring_value

    env_name = get_config_value(config, env_path) if env_path else None
    if env_name:
        env_value = os.environ.get(str(env_name))
        if env_value:
            return env_value
        return _read_user_environment_secret(str(env_name))
    return None


def _read_keyring_secret(keyring_name: str) -> str | None:
    try:
        import keyring  # type: ignore[import-not-found]
    except ImportError:
        return None

    service, _, username = keyring_name.partition("/")
    if not service or not username:
        return None
    return keyring.get_password(service, username)


def _read_user_environment_secret(name: str) -> str | None:
    """Read a Windows user environment variable not loaded into this process."""
    if os.name != "nt":
        return None
    try:
        import winreg
    except ImportError:  # pragma: no cover - Windows-only fallback.
        return None

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _value_type = winreg.QueryValueEx(key, name)
    except OSError:
        return None
    return str(value) if value else None
