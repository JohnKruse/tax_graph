from __future__ import annotations

import hashlib
import os
import zipfile
from pathlib import Path

import pytest

from tax_graph.oracles.ots import (
    OtsInstallError,
    OtsRelease,
    find_ots_1040_template,
    install_ots_release,
    parse_ots_output,
    run_ots_1040,
)
from tax_graph.oracles.scenario import CapitalGainScenario, write_ots_input_bundle


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "ots" / "ots_2025_single_lot_out.txt"


@pytest.mark.m6
def test_parse_ots_output_fixture():
    labels = parse_ots_output(FIXTURE.read_text(encoding="utf-8"))

    assert labels["F8949_2d"] == 12000
    assert labels["F8949_2e"] == 10000
    assert labels["F8949_2h"] == 2000
    assert labels["D16"] == 2000
    assert labels["L7a"] == 2000


@pytest.mark.m6
def test_install_ots_release_verifies_and_unpacks_zip(tmp_path):
    archive_path = tmp_path / "ots.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("OpenTaxSolver/bin/taxsolve_US_1040_2025.exe", "fake exe")
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    release = OtsRelease(
        version="test",
        url="https://example.invalid/ots.zip",
        sha256=digest,
        install_dir=tmp_path / "install",
    )

    install_dir = install_ots_release(release, archive_path=archive_path)

    assert (install_dir / "OpenTaxSolver" / "bin" / "taxsolve_US_1040_2025.exe").exists()


@pytest.mark.m6
def test_install_ots_release_rejects_bad_hash(tmp_path):
    archive_path = tmp_path / "ots.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("OpenTaxSolver/README.txt", "fake")
    release = OtsRelease(
        version="test",
        url="https://example.invalid/ots.zip",
        sha256="0" * 64,
        install_dir=tmp_path / "install",
    )

    with pytest.raises(OtsInstallError, match="sha256 mismatch"):
        install_ots_release(release, archive_path=archive_path)


@pytest.mark.m6
@pytest.mark.oracle
def test_ots_runner_smoke_with_env_binary(tmp_path):
    executable = os.environ.get("OTS_1040_2025_BIN")
    if not executable:
        pytest.skip("set OTS_1040_2025_BIN to run the live OTS smoke test")

    scenario = CapitalGainScenario(
        scenario_id="tax_graph_m6_ots_smoke",
        tax_year="2025",
        filing_status="single",
        description="Smoke LT lot",
        date_acquired="01/15/2024",
        date_sold="06/01/2025",
        proceeds=12000,
        cost=10000,
    )
    paths = write_ots_input_bundle(
        scenario,
        tmp_path,
        template_path=find_ots_1040_template(executable, year="2025"),
    )

    result = run_ots_1040(paths["input"], executable=executable)

    assert result.output_path.exists()
    assert result.labels
    assert "ERROR1" not in result.stdout
    assert "ERROR1" not in result.stderr
    assert "ERROR1" not in result.output_path.read_text(encoding="utf-8", errors="replace")
