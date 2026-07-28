from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from tax_graph.acquire.measure_form import (
    build_snapshot,
    measure_form_pdf,
    measure_robustness_corpus,
    write_snapshot,
)


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.m20
def test_measurement_uses_word_multiset_and_pdf_metadata(tmp_path: Path) -> None:
    fitz = pytest.importorskip("fitz")
    pdf_path = tmp_path / "sample.pdf"
    document = fitz.open()
    page = document.new_page(width=612, height=792)
    page.insert_text((72, 72), "Before 1 Alpha beta")
    page.insert_text((72, 92), "2 Gamma")
    widget = fitz.Widget()
    widget.field_name = "sample"
    widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
    widget.rect = fitz.Rect(300, 66, 360, 84)
    page.add_widget(widget)
    document.save(pdf_path)
    document.close()

    measurement = measure_form_pdf(pdf_path, document_id="sample")

    assert measurement.document_id == "sample"
    assert measurement.ground_truth_words == 6
    assert measurement.preserved_words == 6
    assert measurement.missing_words == 0
    assert measurement.fabricated_words == 0
    assert measurement.page_count == 1
    assert measurement.widget_count == 1
    assert measurement.layers["text"]["status"] == "present"
    assert measurement.layers["widgets"]["status"] == "present"
    assert measurement.table_probe_status == "ok"


@pytest.mark.m20
def test_measurement_tokenizer_keeps_currency_commas() -> None:
    from tax_graph.acquire.measure_form import _word_counter

    assert _word_counter("$1,000 $20 5") == {"$1,000": 1, "$20": 1, "5": 1}


@pytest.mark.m20
def test_snapshot_writes_machine_and_human_reports(tmp_path: Path) -> None:
    fitz = pytest.importorskip("fitz")
    pdf_path = tmp_path / "sample.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "1 Alpha")
    document.save(pdf_path)
    document.close()

    snapshot = build_snapshot([measure_form_pdf(pdf_path, document_id="sample")])
    json_path, markdown_path = write_snapshot(snapshot, tmp_path / "out")

    assert json.loads(json_path.read_text(encoding="utf-8"))["form_count"] == 1
    assert "M20-S1 extraction measurement snapshot" in markdown_path.read_text(encoding="utf-8")
    assert json_path.parent == markdown_path.parent


@pytest.mark.m20
def test_separate_robustness_corpus_reports_layers() -> None:
    corpus_dir = ROOT / "tests" / "fixtures" / "m20_producer_corpus"
    measurements = measure_robustness_corpus(corpus_dir, root=ROOT)

    assert [item.document_id for item in measurements] == [
        "california_form_540_2024",
        "irs_form_1040_1999",
    ]
    assert all(item.layers["text"]["status"] == "present" for item in measurements)
    assert all(item.layers["widgets"]["status"] == "present" for item in measurements)
    assert all(
        item.layers["structure"]["status"] in {"present", "absent", "unavailable"}
        for item in measurements
    )
    assert {item.producer for item in measurements} == {"Adobe PDF Library 15.0", "APJavaScript 2.2.1 Windows SPDF_1112 Oct  3 2005"}


@pytest.mark.m20
def test_module_form_cli_writes_snapshot_for_an_explicit_input_dir(tmp_path: Path) -> None:
    fitz = pytest.importorskip("fitz")
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    pdf_path = input_dir / "sample.pdf"
    document = fitz.open()
    document.new_page().insert_text((72, 72), "1 Alpha")
    document.save(pdf_path)
    document.close()
    output_dir = tmp_path / "output"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tax_graph.cli",
            "measure-extraction",
            "--input-dir",
            str(input_dir),
            "--corpus-dir",
            str(tmp_path / "missing-corpus"),
            "--output-dir",
            str(output_dir),
            "--root",
            str(ROOT),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "measured form PDFs: 1" in result.stdout
    assert (output_dir / "M20_S1_MEASUREMENTS.json").is_file()
