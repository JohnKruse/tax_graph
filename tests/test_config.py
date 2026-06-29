from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from tax_graph import config as config_module
from tax_graph.config import get_config_value, load_config, resolve_secret


@pytest.mark.m0
def test_load_config_returns_empty_when_missing(tmp_path):
    assert load_config(root=tmp_path) == {}


@pytest.mark.m0
def test_load_config_finds_config_dir_file(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "tax-graph.config.yaml").write_text(
        "llm:\n  provider: openrouter\n",
        encoding="utf-8",
    )

    assert load_config(root=tmp_path)["llm"]["provider"] == "openrouter"


@pytest.mark.m0
def test_get_config_value_reads_dotted_paths():
    config = {"llm": {"api_key_env": "ANTHROPIC_API_KEY"}}

    assert get_config_value(config, "llm.api_key_env") == "ANTHROPIC_API_KEY"
    assert get_config_value(config, "missing.path", default="fallback") == "fallback"


@pytest.mark.m0
def test_resolve_secret_prefers_explicit_value(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "from-env")
    config = {
        "llm": {
            "api_key": "from-config",
            "api_key_env": "ANTHROPIC_API_KEY",
        }
    }

    assert (
        resolve_secret(config, "llm.api_key", env_path="llm.api_key_env")
        == "from-config"
    )


@pytest.mark.m0
def test_resolve_secret_uses_keyring_before_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "from-env")
    fake_keyring = SimpleNamespace(
        get_password=lambda service, username: "from-keyring"
        if (service, username) == ("tax-graph", "anthropic")
        else None
    )
    monkeypatch.setitem(sys.modules, "keyring", fake_keyring)
    config = {
        "llm": {
            "api_key": None,
            "api_key_keyring": "tax-graph/anthropic",
            "api_key_env": "ANTHROPIC_API_KEY",
        }
    }

    assert (
        resolve_secret(
            config,
            "llm.api_key",
            keyring_path="llm.api_key_keyring",
            env_path="llm.api_key_env",
        )
        == "from-keyring"
    )


@pytest.mark.m0
def test_resolve_secret_falls_back_to_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "from-env")
    config = {
        "llm": {
            "api_key": None,
            "api_key_keyring": None,
            "api_key_env": "ANTHROPIC_API_KEY",
        }
    }

    assert (
        resolve_secret(
            config,
            "llm.api_key",
            keyring_path="llm.api_key_keyring",
            env_path="llm.api_key_env",
        )
        == "from-env"
    )


@pytest.mark.m0
def test_resolve_secret_reads_user_env_fallback_when_process_env_missing(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(config_module, "_read_user_environment_secret", lambda name: "from-user-env")
    config = {
        "llm": {
            "api_key": None,
            "api_key_keyring": None,
            "api_key_env": "OPENROUTER_API_KEY",
        }
    }

    assert (
        resolve_secret(config, "llm.api_key", env_path="llm.api_key_env")
        == "from-user-env"
    )
