"""M14 serve lifecycle regressions for abandoned MCP processes."""

from __future__ import annotations

import threading
import time
import subprocess
import sys
from pathlib import Path

import pytest

from tax_graph.cli import serve_command
from tax_graph.compile.to_sqlite import build_sqlite
from tax_graph.mcp.lifecycle import (
    ParentWatchdog,
    ProcessInfo,
    orphaned_servers,
    parent_is_alive,
)


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
def test_parent_is_alive_against_real_processes() -> None:
    """Regression: the pre-fix Windows probe raised OSError winerror 87 for a
    genuinely dead pid (uncaught -> the watchdog thread died silently, leaving
    the watchdog inert on the exact platform the orphan incidents happened on).
    Probe REAL processes, not injected fakes."""
    assert parent_is_alive(subprocess.Popen(  # a live process
        [sys.executable, "-c", "import time; time.sleep(5)"]
    ).pid)  # noqa: it will be reaped by the OS after the sleep

    dead = subprocess.Popen([sys.executable, "-c", "pass"])
    dead.wait()
    dead_pid = dead.pid
    del dead  # release the handle so Windows can retire the pid object
    import gc

    gc.collect()
    time.sleep(0.2)
    assert parent_is_alive(dead_pid) is False


@pytest.mark.m14
def test_watchdog_fires_when_a_real_parent_process_dies() -> None:
    """End-to-end watchdog check with a real short-lived parent process."""
    parent = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.3)"])
    fired = threading.Event()
    watchdog = ParentWatchdog(
        parent_pid=parent.pid,
        interval=0.05,
        on_parent_exit=fired.set,
    )
    watchdog.start()
    try:
        parent.wait(timeout=5)
        assert fired.wait(timeout=5), "watchdog never noticed the dead parent"
    finally:
        watchdog.close()


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
def test_build_succeeds_immediately_after_serve_shutdown(tmp_path: Path) -> None:
    """A terminated stdio server must not retain a SQLite handle or build lock.

    Hermetic per the standing rule: the serve/rebuild contention runs against a
    throwaway sqlite under tmp_path, never the shared ``build/`` artifact - a
    live dev MCP server legitimately holds that file open whenever Claude
    Desktop is connected to this checkout, which is the normal dev state.
    """
    build_dir = tmp_path / "build"
    build_sqlite("2025", root=ROOT, build_dir=build_dir)
    assert (build_dir / "tax_graph_2025.sqlite").exists()
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "tax_graph.cli",
            "serve",
            "--year",
            "2025",
            "--root",
            str(tmp_path),
            "--source",
            "sqlite",
        ],
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(0.5)
    finally:
        server.terminate()
        server.wait(timeout=5)
    # Rewriting the same sqlite fails on Windows if the dead server kept its handle.
    build_sqlite("2025", root=ROOT, build_dir=build_dir)
