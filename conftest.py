"""Root pytest configuration.

Pins the temporary-file root for the whole suite so that no test run depends on the
system temp directory.

WHY: this repo is worked by two OS accounts - the developer account and the Codex
sandbox account - and the sandbox denies the AppData temp root, so pytest's default
`tempfile.gettempdir()` location is unusable for the Worker. The previous workaround
passed `--basetemp=.pytest_tmp` on every command, which was worse: `--basetemp` makes
pytest DELETE and recreate that directory at session start, so its ownership flipped to
whichever account ran last. Once one account's ACLs landed on the root, every `tmp_path`
test on the other account failed with `PermissionError: [WinError 5]` while the code
under test was perfectly fine.

`PYTEST_DEBUG_TEMPROOT` sets the temp ROOT rather than the basetemp. pytest never wipes
the root; it creates `pytest-of-<username>/pytest-<N>` inside it and garbage-collects
only its own numbered directories. The username component keeps the two accounts apart
automatically, so nobody has to pass a flag and there is nothing to re-grant.

Consequence: run pytest plainly (`python -m pytest tests/... -q`). Do NOT pass
`--basetemp` - it re-enables the destructive wipe this exists to prevent.
"""

from __future__ import annotations

import os
from pathlib import Path

_TEMP_ROOT = Path(__file__).resolve().parent / ".test_tmp"

# Set before pytest builds its TempPathFactory (which reads this at session start).
# An explicit environment value from the caller still wins.
os.environ.setdefault("PYTEST_DEBUG_TEMPROOT", str(_TEMP_ROOT))
_TEMP_ROOT.mkdir(exist_ok=True)
