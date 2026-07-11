"""M14 serve lifecycle regressions for abandoned MCP processes."""

from __future__ import annotations

import time
import subprocess
import sys
from pathlib import Path

import pytest

from tax_graph.cli import serve_command
from tax_graph.mcp.lifecycle import ParentWatchdog, ProcessInfo, orphaned_servers


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.m14
def test_parent_watchdog_exits_within_bounded_interval() -> None:
    calls: list[str] = []
    checks = iter([True, False])
    watchdog = ParentWatchdog(
        parent_pid=123,
        interval=0.01,
        is_alive=lambda _pid: next(checks),
        on_parent_exit=lambda: calls.append("parent-exited"),
    )

    watchdog.start()
    deadline = time.monotonic() + 0.2
    while not calls and time.monotonic() < deadline:
        time.sleep(0.005)
    watchdog.close()

    assert calls == ["parent-exited"]


@pytest.mark.m14
def test_orphan_sweep_selects_only_abandoned_tax_graph_servers() -> None:
    processes = [
        ProcessInfo(1, 0, "init"),
        ProcessInfo(10, 1, "python -m tax_graph.cli serve"),
        ProcessInfo(11, 77, "tax-graph serve --year 2025"),
        ProcessInfo(12, 1, "python worker.py"),
        ProcessInfo(99, 1, "powershell"),
    ]

    assert orphaned_servers(processes, current_pid=99) == [processes[2]]


@pytest.mark.m14
def test_serve_sweep_command_does_not_start_mcp_server(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr("tax_graph.mcp.lifecycle.sweep_orphaned_servers", lambda: [101, 102])

    assert serve_command(sweep_orphans=True) == 0
    assert "stopped 2 orphaned" in capsys.readouterr().out


@pytest.mark.m14
def test_build_succeeds_immediately_after_serve_shutdown() -> None:
    """A terminated stdio server must not retain a SQLite handle or build lock."""
    subprocess.run(
        [sys.executable, "-m", "tax_graph.cli", "build", "2025", "--root", str(ROOT)],
        check=True,
        cwd=ROOT,
    )
    server = subprocess.Popen(
        [sys.executable, "-m", "tax_graph.cli", "serve", "--year", "2025", "--root", str(ROOT)],
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(0.2)
    finally:
        server.terminate()
        server.wait(timeout=5)
    result = subprocess.run(
        [sys.executable, "-m", "tax_graph.cli", "build", "2025", "--root", str(ROOT)],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr
