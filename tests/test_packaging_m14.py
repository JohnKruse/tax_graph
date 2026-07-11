"""Hermetic checks for M14 alpha packaging metadata."""

from __future__ import annotations

import json
from pathlib import Path
import tomllib

import pytest

from tax_graph import __version__
from tax_graph.config import project_root


ROOT = Path(__file__).resolve().parents[1]
ALPHA_NOTICE = "Not tax advice; verify before filing."


@pytest.mark.m14
def test_alpha_metadata_and_runtime_assets_are_packaged() -> None:
    """The published wheel must contain the keyless graph runtime assets."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    force_include = project["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]

    assert project["project"]["version"] == __version__ == "0.1.0a1"
    assert "Alpha" in project["project"]["description"]
    assert set(force_include) >= {"config", "data", "docs", "examples", "graph", "oracles", "schemas"}
    assert project_root() == ROOT


@pytest.mark.m14
def test_mcp_bundle_manifest_is_honest_and_uses_uv_runtime() -> None:
    """The bundle starts the packaged local server without an API key."""
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["version"] == "0.1.0-alpha.1"
    assert manifest["server"]["type"] == "uv"
    assert manifest["server"]["mcp_config"]["command"] == "uv"
    assert ALPHA_NOTICE in manifest["description"]
    assert ALPHA_NOTICE in manifest["long_description"]
    assert not manifest.get("user_config")


@pytest.mark.m14
def test_mcp_bundle_launches_from_wheel_never_source_builds() -> None:
    """Regression: the first in-app install failed because `uv run --directory`
    source-built the package inside the extension dir, where hatchling's
    force-include dirs are (correctly) absent. The bundle must launch from the
    shipped wheel and never trigger a build on the user's machine."""
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    args = manifest["server"]["mcp_config"]["args"]

    wheel = f"tax_graph-{__version__}-py3-none-any.whl"
    assert args[:3] == ["tool", "run", "--from"]
    assert args[3] == "${__dirname}/" + wheel
    assert "--directory" not in args
    assert manifest["server"]["entry_point"] == wheel
    # the release workflow must stage exactly that wheel into the bundle
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert f"cp dist/{wheel} dist/bundle/" in workflow
    assert "mcpb pack dist/bundle" in workflow


@pytest.mark.m14
def test_registry_descriptor_matches_pypi_and_readme_ownership_marker() -> None:
    """The future registry entry names the alpha PyPI distribution exactly."""
    descriptor = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    package = descriptor["packages"][0]
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert descriptor["name"] == "io.github.johnkruse/tax-graph"
    assert f"mcp-name: {descriptor['name']}" in readme
    assert package["registryType"] == "pypi"
    assert package["identifier"] == "tax-graph"
    assert package["version"] == descriptor["version"] == __version__
    assert package["runtimeHint"] == "uvx"
    assert ALPHA_NOTICE in descriptor["description"]


@pytest.mark.m14
def test_release_workflow_builds_and_checks_without_automatic_publish() -> None:
    """Tag runs stage artifacts while PyPI publication remains an explicit action."""
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "uv build" in workflow
    assert "twine check" in workflow
    assert "sha256sum dist/*" in workflow
    assert "mcpb pack" in workflow
    assert "check-jsonschema" in workflow
    assert "workflow_dispatch" in workflow
    assert "inputs.publish_pypi" in workflow
