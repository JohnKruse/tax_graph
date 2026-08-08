from __future__ import annotations

from pathlib import Path
import json
import re
import shutil

import pytest

from tax_graph.cli import verify_nversion_command
from tax_graph.verify.nversion import corroboration_provenance, run_nversion_extraction
from tax_graph.extract.models import RelatedSourceInput, SourceDocumentInput


ROOT = Path(__file__).resolve().parents[1]


class PromptAwareClient:
    def __init__(self, *, swap_subtract_roles: bool = False):
        self.swap_subtract_roles = swap_subtract_roles
        self.calls: list[dict] = []

    def structured_completion(self, *, prompt, schema, model, max_tokens, temperature, purpose, seed=None):
        self.calls.append({"prompt": prompt, "model": model, "purpose": purpose})
        if "kind: totals" in prompt:
            span_id = re.search(r"- (span_[a-z0-9_]+): .*- 2: Totals", prompt).group(1)
            return {
                "operation_plan": [
                    {
                        "output": f"line_2_column_{column}_total",
                        "operation": "SUM",
                        "inputs": [{"name": f"line_1_column_{column}", "role": "addend"}],
                        "citation_span_ids": [span_id],
                    }
                    for column in ["d", "e", "g", "h"]
                ]
            }
        span_id = re.search(r"- (span_[a-z0-9_]+): .*Subtract column", prompt).group(1)
        d_role = "subtrahend" if self.swap_subtract_roles else "minuend"
        e_role = "minuend" if self.swap_subtract_roles else "subtrahend"
        return {
            "operation_plan": [
                {
                    "output": "column_h_before_adjustment",
                    "operation": "SUBTRACT",
                    "inputs": [
                        {"name": "column_d", "role": d_role},
                        {"name": "column_e", "role": e_role},
                    ],
                    "citation_span_ids": [span_id],
                },
                {
                    "output": "column_h",
                    "operation": "SUM",
                    "inputs": [
                        {"name": "column_h_before_adjustment", "role": "addend"},
                        {"name": "column_g", "role": "addend"},
                    ],
                    "citation_span_ids": [span_id],
                },
            ]
        }


@pytest.mark.m8
def test_nversion_agreement_records_corroboration():
    document = _document(Path("memory"))
    report = run_nversion_extraction(
        document,
        primary_client=PromptAwareClient(),
        secondary_client=PromptAwareClient(),
        config={
            "llm": {
                "model": "family-a/model",
                "micro_model": "family-a/model",
                "nversion_model": "family-b/model",
            }
        },
        root=ROOT,
    )

    assert report.ok
    assert report.primary_family == "family-a"
    assert report.secondary_family == "family-b"
    assert report.secondary_model == "family-b/model"
    primary_batch = run_nversion_extraction(
        document,
        primary_client=PromptAwareClient(),
        secondary_client=PromptAwareClient(),
        config={"llm": {"model": "family-a/model", "micro_model": "family-a/model", "nversion_model": "family-b/model"}},
        root=ROOT,
    )
    assert primary_batch.ok


@pytest.mark.m8
def test_nversion_disagreement_creates_side_by_side_review_entry():
    document = _document(Path("memory"))
    report = run_nversion_extraction(
        document,
        primary_client=PromptAwareClient(),
        secondary_client=PromptAwareClient(swap_subtract_roles=True),
        config={"llm": {"model": "family-a/model", "micro_model": "family-a/model", "nversion_model": "family-b/model"}},
        root=ROOT,
    )

    assert not report.ok
    assert report.review_entries
    diff = next(entry for entry in report.review_entries if entry.kind == "edges")
    assert diff.primary != diff.secondary
    assert diff.reason in {"payload_diff", "missing_primary", "missing_secondary"}


@pytest.mark.m8
def test_nversion_provenance_marks_disagreements():
    document = _document(Path("memory"))
    primary_client = PromptAwareClient()
    secondary_client = PromptAwareClient(swap_subtract_roles=True)
    report = run_nversion_extraction(
        document,
        primary_client=primary_client,
        secondary_client=secondary_client,
        config={"llm": {"model": "family-a/model", "micro_model": "family-a/model", "nversion_model": "family-b/model"}},
        root=ROOT,
    )
    agreed_report = run_nversion_extraction(
        document,
        primary_client=PromptAwareClient(),
        secondary_client=PromptAwareClient(),
        config={"llm": {"model": "family-a/model", "micro_model": "family-a/model", "nversion_model": "family-b/model"}},
        root=ROOT,
    )
    from tax_graph.extract.outline_pipeline import generate_outline_first_drafts

    batch = generate_outline_first_drafts(document, client=PromptAwareClient(), config={"llm": {"model": "family-a/model", "micro_model": "family-a/model"}}, root=ROOT)
    disagreed = corroboration_provenance(batch, report)
    agreed = corroboration_provenance(batch, agreed_report)

    assert any(item["nversion_status"] == "disagreed" for item in disagreed)
    assert all(item["nversion_status"] == "agreed" for item in agreed)


@pytest.mark.m8
def test_verify_nversion_command_reports_disagreement(tmp_path, capsys):
    root = _make_project(tmp_path)

    exit_code = verify_nversion_command(
        doc="form_8949_2025",
        year="2025",
        root=root,
        primary_client=PromptAwareClient(),
        secondary_client=PromptAwareClient(swap_subtract_roles=True),
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "N-version extraction" in captured.out
    assert "status: disagreed" in captured.out
    assert "missing_" in captured.out or "payload_diff" in captured.out


def _document(tmp_path: Path) -> SourceDocumentInput:
    text_path = tmp_path / "form_8949_2025.txt"
    text = "\n".join(
        [
            "# Page 1",
            "Header: Part I Short-Term. Box A Box B Box C",
            "Header: (a) Description (d) Proceeds (e) Cost (g) Adjustment (h) Gain or loss",
            "- 1: Transaction table",
            "- 2: Totals. Add the amounts in columns (d), (e), (g), and (h)",
            "# Page 2",
            "Header: Part II Long-Term. Box D Box E Box F",
            "Header: (a) Description (d) Proceeds (e) Cost (g) Adjustment (h) Gain or loss",
            "- 1: Transaction table",
            "- 2: Totals. Add the amounts in columns (d), (e), (g), and (h)",
            "",
        ]
    )
    return SourceDocumentInput(
        document_id="form_8949_2025",
        kind="tax_form",
        year="2025",
        url="https://www.irs.gov/pub/irs-pdf/f8949.pdf",
        text=text,
        text_path=text_path,
        fields={"fields": _row_fields(), "line_anchors": _line_anchor_index(text)},
        related_sources=[
            RelatedSourceInput(
                document_id="instructions_form_8949_2025",
                kind="instructions",
                text="Column (h). Subtract column (e) from column (d), and include column (g).",
                text_path=tmp_path / "instructions_form_8949_2025.txt",
                relationship="instructions",
            )
        ],
    )


def _make_project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(ROOT / "config", root / "config")
    shutil.copyfile(
        root / "config" / "tax-graph.config.example.yaml",
        root / "config" / "tax-graph.config.yaml",
    )  # hermetic: never inherit the developer's gitignored local config
    shutil.copytree(ROOT / "schemas", root / "schemas")
    shutil.copytree(ROOT / "graph", root / "graph")
    raw_dir = root / ".cache" / "raw" / "2025"
    raw_dir.mkdir(parents=True)
    document = _document(raw_dir)
    (raw_dir / "form_8949_2025.txt").write_text(document.text, encoding="utf-8")
    (raw_dir / "form_8949_2025.fields.json").write_text(
        json.dumps({"fields": [], "line_anchors": _line_anchor_index(document.text)}) + "\n",
        encoding="utf-8",
    )
    (raw_dir / "instructions_form_8949_2025.txt").write_text(
        "Column (h). Subtract column (e) from column (d), and include column (g).\n",
        encoding="utf-8",
    )
    return root


def _row_fields() -> list[dict]:
    fields = []
    x_clusters = [25, 175, 225, 275, 350, 400, 450, 500]
    for part in [1, 2]:
        for index, x_cluster in enumerate(x_clusters, 1):
            fields.append(
                {
                    "field_name": (
                        f"topmostSubform[0].Page{part}[0].Table_Line1_Part{part}[0]"
                        f".Row1[0].f{part}_{index:02d}[0]"
                    ),
                    "page": part,
                    "x_cluster": x_cluster,
                    "y_cluster": 400,
                }
            )
    return fields


def _line_anchor_index(text: str) -> list[dict[str, int | str]]:
    return [
        {
            "anchor": match.group(1).lower(),
            "page": 1,
            "text_offset": match.start(1),
            "text_length": len(match.group(1)),
        }
        for match in re.finditer(r"^[-]\s+([0-9]+[a-z]?|[a-z]):", text, re.IGNORECASE | re.MULTILINE)
    ]
