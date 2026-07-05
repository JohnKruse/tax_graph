"""OpenTaxSolver adapter primitives.

The live OTS executable is optional and gated outside the base test suite.
Offline M6 tests exercise parsing and installer behavior against committed
fixtures, while ``pytest -m oracle`` can invoke a configured local binary.
"""

from __future__ import annotations

import hashlib
import platform
import re
import shutil
import subprocess
import tarfile
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from tax_graph.config import get_config_value


FetchBytes = Callable[[str], bytes]
ParsedOtsOutput = dict[str, int | float]


class OtsInstallError(RuntimeError):
    """Raised when the pinned OTS release cannot be installed."""


class OtsRunError(RuntimeError):
    """Raised when the OTS subprocess does not produce a usable output file."""


@dataclass(frozen=True)
class OtsRelease:
    """Pinned OTS release information for one platform."""

    version: str
    url: str
    sha256: str
    install_dir: Path
    executable: Path | None = None


@dataclass(frozen=True)
class OtsRunResult:
    """Result of running a local OTS 1040 solver."""

    input_path: Path
    output_path: Path
    stdout: str
    stderr: str
    labels: ParsedOtsOutput


def release_from_config(
    config: Mapping[str, object],
    *,
    root: str | Path,
    year: str = "2025",
    system: str | None = None,
) -> OtsRelease:
    """Build an ``OtsRelease`` from ``oracles.opentaxsolver`` config.

    The URL and hash must be explicit so live oracle runs are reproducible.
    """

    root_path = Path(root)
    platform_name = ots_platform_key(system)
    base_path = "oracles.opentaxsolver"
    release_path = f"{base_path}.releases.{platform_name}"
    version = str(get_config_value(config, f"{base_path}.version", year))
    url = get_config_value(config, f"{release_path}.url")
    sha256 = get_config_value(config, f"{release_path}.sha256")
    install_dir_value = get_config_value(
        config,
        f"{base_path}.install_dir",
        f".cache/oracles/opentaxsolver/{version}",
    )
    executable_value = (
        get_config_value(config, f"{base_path}.executable")
        or get_config_value(config, f"{release_path}.executable")
    )
    if not url or not sha256:
        raise OtsInstallError(
            f"missing OTS release url/sha256 for platform {platform_name}; "
            "set oracles.opentaxsolver.releases.<platform>"
        )

    install_dir = _resolve_path(root_path, install_dir_value)
    executable = _resolve_path(root_path, executable_value) if executable_value else None
    return OtsRelease(
        version=version,
        url=str(url),
        sha256=str(sha256),
        install_dir=install_dir,
        executable=executable,
    )


def ots_platform_key(system: str | None = None) -> str:
    """Return the config key for the current OTS release platform."""

    name = (system or platform.system()).lower()
    if name.startswith("win"):
        return "windows"
    if name == "darwin":
        return "macos"
    if name == "linux":
        return "linux"
    return name


def install_ots_release(
    release: OtsRelease,
    *,
    fetch_bytes: FetchBytes | None = None,
    archive_path: str | Path | None = None,
) -> Path:
    """Download or read, hash-verify, and unpack a pinned OTS release."""

    archive_bytes = _read_archive_bytes(release, fetch_bytes=fetch_bytes, archive_path=archive_path)
    actual_sha256 = hashlib.sha256(archive_bytes).hexdigest()
    if actual_sha256.lower() != release.sha256.lower():
        raise OtsInstallError(
            f"sha256 mismatch for OTS {release.version}: "
            f"expected {release.sha256}, got {actual_sha256}"
        )

    release.install_dir.mkdir(parents=True, exist_ok=True)
    archive_name = Path(archive_path).name if archive_path else Path(_url_path(release.url)).name
    if not archive_name:
        archive_name = "opentaxsolver_release"
    cache_path = release.install_dir / archive_name
    cache_path.write_bytes(archive_bytes)
    _unpack_archive(cache_path, release.install_dir)
    return release.install_dir


def find_ots_executable(
    install_dir: str | Path,
    *,
    year: str = "2025",
    executable: str | Path | None = None,
) -> Path:
    """Find the 1040 solver executable inside an installed OTS tree."""

    if executable is not None:
        candidate = Path(executable)
        if candidate.exists():
            return candidate.resolve()
        raise OtsInstallError(f"configured OTS executable does not exist: {candidate}")

    root = Path(install_dir)
    candidate_names = {
        f"taxsolve_US_1040_{year}",
        f"taxsolve_US_1040_{year}.exe",
        f"taxsolve_usa_fed1040_{year}",
        f"taxsolve_usa_fed1040_{year}.exe",
    }
    lowered = {name.lower() for name in candidate_names}
    for path in root.rglob("*"):
        if path.is_file() and path.name.lower() in lowered:
            return path.resolve()
    raise OtsInstallError(f"no OTS US 1040 {year} executable found under {root}")


def run_ots_1040(
    input_path: str | Path,
    *,
    executable: str | Path,
    timeout_sec: int = 30,
) -> OtsRunResult:
    """Run a local OTS 1040 solver and parse its ``*_out.txt`` result."""

    input_file = Path(input_path).resolve()
    executable_path = Path(executable).resolve()
    if not input_file.exists():
        raise OtsRunError(f"OTS input file does not exist: {input_file}")
    if not executable_path.exists():
        raise OtsRunError(f"OTS executable does not exist: {executable_path}")

    completed = subprocess.run(
        [str(executable_path), str(input_file)],
        cwd=input_file.parent,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_sec,
    )
    out_path = output_path_for(input_file)
    if completed.returncode != 0:
        raise OtsRunError(
            f"OTS exited {completed.returncode}: {completed.stderr.strip() or completed.stdout.strip()}"
        )
    if not out_path.exists():
        raise OtsRunError(f"OTS did not write expected output file: {out_path}")

    text = out_path.read_text(encoding="utf-8", errors="replace")
    return OtsRunResult(
        input_path=input_file,
        output_path=out_path,
        stdout=completed.stdout,
        stderr=completed.stderr,
        labels=parse_ots_output(text),
    )


def output_path_for(input_path: str | Path) -> Path:
    """Return the OTS ``*_out.txt`` path for an input file."""

    path = Path(input_path)
    return path.with_name(f"{path.stem}_out.txt")


_LABEL_RE = re.compile(
    r"^\s*"
    r"(?P<label>[A-Za-z][A-Za-z0-9_]*)"
    r"\s*:?\s*(?:=)?\s*"
    r"(?P<value>\(?-?\$?\d[\d,]*(?:\.\d+)?\)?)"
    r"\s*(?:;)?(?:\s|$)"
)


def parse_ots_output(text: str) -> ParsedOtsOutput:
    """Parse line-labeled OTS output into ``{label: value}``.

    OTS output is text-first, so the parser accepts the common variants used in
    templates and result files: ``L7: 2000 ;``, ``L7 = 2000``, and aligned
    whitespace columns. Non-numeric narrative lines are ignored.
    """

    labels: ParsedOtsOutput = {}
    for raw_line in text.splitlines():
        line = _strip_brace_comment(raw_line).strip()
        if not line:
            continue
        match = _LABEL_RE.match(line)
        if not match:
            continue
        labels[match.group("label")] = _parse_number(match.group("value"))
    return labels


def _read_archive_bytes(
    release: OtsRelease,
    *,
    fetch_bytes: FetchBytes | None,
    archive_path: str | Path | None,
) -> bytes:
    if archive_path is not None:
        return Path(archive_path).read_bytes()
    if fetch_bytes is not None:
        return fetch_bytes(release.url)
    with urllib.request.urlopen(release.url, timeout=60) as response:
        return response.read()


def _unpack_archive(archive_path: Path, install_dir: Path) -> None:
    if zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path) as archive:
            _safe_extract_zip(archive, install_dir)
        return
    if tarfile.is_tarfile(archive_path):
        with tarfile.open(archive_path) as archive:
            _safe_extract_tar(archive, install_dir)
        return
    raise OtsInstallError(f"unsupported OTS archive format: {archive_path.name}")


def _safe_extract_zip(archive: zipfile.ZipFile, destination: Path) -> None:
    dest = destination.resolve()
    for member in archive.infolist():
        target = (dest / member.filename).resolve()
        if not _is_relative_to(target, dest):
            raise OtsInstallError(f"unsafe archive member path: {member.filename}")
    archive.extractall(dest)


def _safe_extract_tar(archive: tarfile.TarFile, destination: Path) -> None:
    dest = destination.resolve()
    for member in archive.getmembers():
        target = (dest / member.name).resolve()
        if not _is_relative_to(target, dest):
            raise OtsInstallError(f"unsafe archive member path: {member.name}")
    archive.extractall(dest)


def _strip_brace_comment(line: str) -> str:
    return re.sub(r"\{.*?\}", "", line)


def _parse_number(text: str) -> int | float:
    value_text = text.strip().replace("$", "").replace(",", "")
    negative = value_text.startswith("(") and value_text.endswith(")")
    if negative:
        value_text = value_text[1:-1]
    value = float(value_text)
    if negative:
        value = -value
    return int(value) if value.is_integer() else value


def _resolve_path(root: Path, value: object) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else root / path


def _url_path(url: str) -> str:
    return urllib.parse.urlparse(url).path


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def remove_install_dir(path: str | Path) -> None:
    """Remove an OTS install dir.

    This helper is intentionally unused by the CLI. Tests may use it for
    temporary directories, but user-facing cleanup should remain explicit.
    """

    shutil.rmtree(path)
