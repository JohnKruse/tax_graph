from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tax_graph.mcp import M2_TOOL_NAMES, build_mcp_server


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.m2
def test_mcp_server_advertises_m2_tools():
    server = build_mcp_server(year="2025", root=ROOT, source="yaml")

    tools = asyncio.run(server.list_tools())

    assert tuple(sorted(tool.name for tool in tools)) == tuple(sorted(M2_TOOL_NAMES))


@pytest.mark.m2
def test_mcp_server_construction_is_runtime_light():
    script = """
import json
import sys
from tax_graph.mcp import build_mcp_server

server = build_mcp_server(year="2025", source="yaml")
loaded = [name for name in ("fitz", "mistralai") if name in sys.modules]
tools = sorted(tool.name for tool in __import__("asyncio").run(server.list_tools()))
print(json.dumps({"loaded": loaded, "tools": tools}))
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["loaded"] == []
    assert payload["tools"] == sorted(M2_TOOL_NAMES)
