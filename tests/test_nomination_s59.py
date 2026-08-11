"""M20-S59 tests for evidence-backed region nominations."""

from __future__ import annotations

from pathlib import Path
import shutil

import pytest
import yaml

from tax_graph.acquire.fetch import fetch_manifest_documents
from tax_graph.acquire.manifest import load_manifest, validate_manifest_data
from tax_graph.cli import nomination_list_command
from tax_graph.ingest.nominations import (
    _document_id_for_title,
    _target_for_title,
    accept_nomination,
    drop_nomination,
    list_nominations,
)


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]
SOURCE_HTML = ROOT / ".cache" / "raw" / "2025" / "instructions_form_1040_2025.html"
QDCGT_TITLE = "Qualified Dividends and Capital Gain Tax Worksheet"
PARENT_ID = "instructions_form_1040_2025"
PARENT_URL = "https://www.irs.gov/pub/irs-prior/i1040gi--2025.pdf"
SCHEDULE_D_ID = "instructions_schedule_d_2025"
SCHEDULE_D_HTML = ROOT / ".cache" / "raw" / "2025" / f"{SCHEDULE_D_ID}.html"
SCHEDULE_D_TEXT = ROOT / ".cache" / "raw" / "2025" / f"{SCHEDULE_D_ID}.txt"
SCHEDULE_D_URL = "https://www.irs.gov/pub/irs-prior/i1040sd--2025.pdf"


def _manifest_data(
    *,
    parent_id: str = PARENT_ID,
    parent_url: str = PARENT_URL,
) -> dict:
    return {
        "tax_year": 2025,
        "documents": [
            {
                "document_id": parent_id,
                "kind": "instructions",
                "url": parent_url,
            }
        ],
    }


def _write_project(
    tmp_path: Path,
    *,
    parent_id: str = PARENT_ID,
    parent_url: str = PARENT_URL,
    source_html: Path = SOURCE_HTML,
    source_text: Path | None = None,
) -> Path:
    root = tmp_path / "project"
    (root / "config").mkdir(parents=True)
    (root / "schemas").mkdir()
    shutil.copy2(ROOT / "schemas" / "manifest.schema.json", root / "schemas" / "manifest.schema.json")
    (root / "config" / "manifest.yaml").write_text(
        yaml.safe_dump(
            _manifest_data(parent_id=parent_id, parent_url=parent_url),
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="ascii",
    )
    raw = root / ".cache" / "raw" / "2025"
    raw.mkdir(parents=True)
    shutil.copy2(source_html, raw / f"{parent_id}.html")
    if source_text is not None:
        shutil.copy2(source_text, raw / f"{parent_id}.txt")
    return root


def _write_evidence(
    tmp_path: Path,
    *,
    title: str = QDCGT_TITLE,
    document_id: str = "form_6251_2025",
) -> Path:
    path = tmp_path / "run" / "form_6251_2025_derive_cells_report.yaml"
    path.parent.mkdir()
    rows = []
    for line in ("13", "20", "27"):
        rows.append(
            {
                "line": line,
                "label_before": (
                    f"{line} Enter the amount from line 5 of the {title}."
                ),
                "form_face_before": "",
                "error": "validation gap after one repair: self_reference",
                "validation_failures": [],
            }
        )
    path.write_text(
        yaml.safe_dump(
            {"document_id": document_id, "rows_detail": rows},
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="ascii",
    )
    return path


def test_manifest_region_schema_requires_parent_and_has_no_url() -> None:
    data = _manifest_data()
    data["documents"].append(
        {
            "document_id": "worksheet_2025",
            "kind": "worksheet",
            "region": {
                "source_document_id": PARENT_ID,
                "title": QDCGT_TITLE,
                "parent_sha256": "a" * 64,
            },
        }
    )

    validate_manifest_data(data, root=ROOT)

    invalid = dict(data)
    invalid["documents"] = [dict(data["documents"][1], url=PARENT_URL)]
    with pytest.raises(Exception):
        validate_manifest_data(invalid, root=ROOT)


def test_worksheet_title_derives_document_id() -> None:
    target = _target_for_title(
        document_id=_document_id_for_title("Schedule D Tax Worksheet"),
        title="Schedule D Tax Worksheet",
        source_document_id="instructions_schedule_d_2025",
    )

    assert target.document_id == "schedule_d_tax_worksheet_2025"


def test_nomination_report_counts_real_citing_rows(tmp_path: Path) -> None:
    evidence_path = _write_evidence(tmp_path)

    nominations = list_nominations(year=2025, root=ROOT, run_dir=evidence_path.parent)

    qdcgt = next(item for item in nominations if item.title == QDCGT_TITLE)
    assert qdcgt.citing_rows == (
        "form_6251_2025 line 13",
        "form_6251_2025 line 20",
        "form_6251_2025 line 27",
    )
    assert qdcgt.count == 3
    assert any(QDCGT_TITLE in item for item in qdcgt.evidence)


def test_accept_region_pins_parent_and_is_fetch_skipped(tmp_path: Path) -> None:
    root = _write_project(tmp_path)
    evidence_path = _write_evidence(tmp_path)

    result = accept_nomination(
        title=QDCGT_TITLE,
        source_document_id=PARENT_ID,
        year=2025,
        root=root,
        run_dir=evidence_path.parent,
    )

    assert result["status"] == "accepted"
    manifest = load_manifest(root=root)
    region = manifest.by_document_id()["qualified_dividends_and_capital_gain_tax_worksheet_2025"]
    assert region.is_region
    assert region.url is None
    assert region.region_of == PARENT_ID
    assert region.region_title == QDCGT_TITLE
    assert len(region.region_parent_sha256 or "") == 64
    assert result["harvest"].as_dict()["counts"] == {
        "lines": 25,
        "constants": 13,
        "edges": 42,
        "citations": 13,
    }

    calls: list[str] = []
    fetched = fetch_manifest_documents(
        manifest.documents,
        year=2025,
        raw_store=tmp_path / "raw-store",
        fetch_bytes=lambda url, config: calls.append(url) or b"pdf",
    )
    assert [item.document_id for item in fetched] == [PARENT_ID]
    assert calls == [PARENT_URL]

    drop_nomination(region.document_id, root=root)
    assert region.document_id not in load_manifest(root=root).by_document_id()


def test_accept_source_verified_worksheet_uses_rendered_text_extent(tmp_path: Path) -> None:
    root = _write_project(
        tmp_path,
        parent_id=SCHEDULE_D_ID,
        parent_url=SCHEDULE_D_URL,
        source_html=SCHEDULE_D_HTML,
        source_text=SCHEDULE_D_TEXT,
    )
    evidence_path = _write_evidence(
        tmp_path,
        title="Schedule D Tax Worksheet",
        document_id="form_1040_2025",
    )

    result = accept_nomination(
        title="Schedule D Tax Worksheet",
        source_document_id=SCHEDULE_D_ID,
        year=2025,
        root=root,
        run_dir=evidence_path.parent,
    )

    assert result["status"] == "accepted"
    assert result["harvest"].as_dict()["counts"]["lines"] == 47
    region = load_manifest(root=root).by_document_id()["schedule_d_tax_worksheet_2025"]
    assert region.region_of == SCHEDULE_D_ID


def test_accept_requires_evidence_even_when_source_title_exists(tmp_path: Path) -> None:
    root = _write_project(tmp_path)

    with pytest.raises(ValueError, match="no citing row or frontier evidence"):
        accept_nomination(
            title=QDCGT_TITLE,
            source_document_id=PARENT_ID,
            year=2025,
            root=root,
        )


def test_cli_list_hides_an_already_accepted_region(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _write_project(tmp_path)
    evidence_path = _write_evidence(tmp_path)
    accept_nomination(
        title=QDCGT_TITLE,
        source_document_id=PARENT_ID,
        year=2025,
        root=root,
        run_dir=evidence_path.parent,
    )

    assert nomination_list_command(year=2025, root=root, run_dir=evidence_path.parent) == 0
    assert QDCGT_TITLE not in capsys.readouterr().out
