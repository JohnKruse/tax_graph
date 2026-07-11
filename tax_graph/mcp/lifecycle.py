"""Process-lifecycle helpers for the local stdio MCP server.

The server is intentionally a child of its MCP client.  If that client dies,
the watchdog interrupts the server so SQLite-backed builds are not left behind
by an abandoned process.  The orphan sweep is an explicit recovery command for
older sessions that predate the watchdog.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import signal
import subprocess
import sys
import threading
import _thread
from typing import Callable, Iterable


PARENT_CHECK_INTERVAL_SECONDS = 0.25


@dataclass(frozen=True)
class ProcessInfo:
    """The process fields needed to identify an abandoned MCP server."""

    pid: int
    parent_pid: int
    command_line: str


def parent_is_alive(pid: int) -> bool:
    """Return whether ``pid`` still names a process, without platform extras."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class ParentWatchdog:
    """Interrupt the server when the process that launched it disappears."""

    def __init__(
        self,
        parent_pid: int | None = None,
        *,
        interval: float = PARENT_CHECK_INTERVAL_SECONDS,
        is_alive: Callable[[int], bool] = parent_is_alive,
        on_parent_exit: Callable[[], None] | None = None,
    ) -> None:
        self.parent_pid = os.getppid() if parent_pid is None else parent_pid
        self.interval = interval
        self.is_alive = is_alive
        self.on_parent_exit = on_parent_exit or _interrupt_main
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="tax-graph-parent-watchdog", daemon=True)

    def start(self) -> None:
        """Start watching the recorded parent process."""
        self._thread.start()

    def close(self) -> None:
        """Stop the watchdog and wait briefly for its thread to finish."""
        self._stop.set()
        self._thread.join(timeout=self.interval * 2 + 0.1)

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            if not self.is_alive(self.parent_pid):
                self.on_parent_exit()
                return


def _interrupt_main() -> None:
    """Request normal Python shutdown from the main thread."""
    _thread.interrupt_main()


def list_processes() -> list[ProcessInfo]:
    """List processes using only OS-provided tooling available to this project."""
    if sys.platform == "win32":
        command = (
            "Get-CimInstance Win32_Process | "
            "Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout or "[]")
        rows = payload if isinstance(payload, list) else [payload]
        return [
            ProcessInfo(int(row["ProcessId"]), int(row["ParentProcessId"]), row.get("CommandLine") or "")
            for row in rows
        ]

    result = subprocess.run(
        ["ps", "-axo", "pid=,ppid=,command="],
        check=True,
        capture_output=True,
        text=True,
    )
    processes: list[ProcessInfo] = []
    for line in result.stdout.splitlines():
        fields = line.strip().split(maxsplit=2)
        if len(fields) == 3:
            processes.append(ProcessInfo(int(fields[0]), int(fields[1]), fields[2]))
    return processes


def is_tax_graph_serve(process: ProcessInfo) -> bool:
    """Return whether a process command line is a Tax Graph serve session."""
    command = process.command_line.lower()
    return "serve" in command and ("tax-graph" in command or "tax_graph.cli" in command)


def orphaned_servers(processes: Iterable[ProcessInfo], *, current_pid: int | None = None) -> list[ProcessInfo]:
    """Find Tax Graph server processes whose recorded parent no longer exists."""
    current_pid = os.getpid() if current_pid is None else current_pid
    rows = list(processes)
    known_pids = {process.pid for process in rows}
    return [
        process
        for process in rows
        if process.pid != current_pid and is_tax_graph_serve(process) and process.parent_pid not in known_pids
    ]


def stop_process(pid: int) -> None:
    """Stop one explicitly selected orphaned server process."""
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=True, capture_output=True, text=True)
    else:
        os.kill(pid, signal.SIGTERM)


def sweep_orphaned_servers() -> list[int]:
    """Stop abandoned Tax Graph server processes and return their process ids."""
    orphans = orphaned_servers(list_processes())
    for process in orphans:
        stop_process(process.pid)
    return [process.pid for process in orphans]
