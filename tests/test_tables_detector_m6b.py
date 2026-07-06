from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from tax_graph.extract.models import RelatedSourceInput, SourceDocumentInput
from tax_graph.extract.outline_pipeline import generate_outline_first_drafts
from tax_graph.extract.prompts import graph_object_schemas


ROOT = Path(__file__).resolve().parents[1]


class PromptAwareMicroClient:
    def __init__(self):
        self.calls: list[dict[str, Any]] = []

    def structured_completion(self, *, prompt, schema, model, max_tokens, temperature, purpose):
        self.calls.append(
            {
                "prompt": prompt,
                "schema": schema,
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "purpose": purpose,
            }
        )
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
        return {
            "operation_plan": [
                {
                    "output": "column_h_before_adjustment",
                    "operation": "SUBTRACT",
                    "inputs": [
                        {"name": "column_d", "role": "minuend"},
                        {"name": "column_e", "role": "subtrahend"},
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


@pytest.mark.m6b
def test_detector_groups_8949_parts_into_table_subunits(tmp_path):
    batch = generate_outline_first_drafts(
        _document(tmp_path),
        client=PromptAwareMicroClient(),
        config={"llm": {"model": "mock-model", "temperature": 0}},
        root=ROOT,
    )

    tables = batch.items("tables")

    assert [table.object_id for table in tables] == [
        "form_8949_2025_part_i_line_1",
        "form_8949_2025_part_ii_line_1",
    ]
    assert [column["column_id"] for column in tables[0].data["columns"]] == ["d", "e", "g", "h"]
    assert [total["column_id"] for total in tables[0].data["totals"]] == ["d", "e", "g", "h"]
    assert tables[0].data["columns"][0]["template_node"] == "form_8949_2025_part_i_line_1_column_d"
    assert tables[0].data["totals"][-1]["total_node"] == "form_8949_2025_part_i_line_2_line_2_column_h_total"
    nodes = {node.object_id: node.data for node in batch.items("nodes")}
    assert nodes["form_8949_2025_part_i_line_1_column_d"]["table_id"] == "form_8949_2025_part_i_line_1"
    assert nodes["form_8949_2025_part_i_line_1_column_d"]["role"] == "row_template"
    assert nodes["form_8949_2025_part_i_line_2_line_2_column_h_total"]["role"] == "total"
    schemas = graph_object_schemas(root=ROOT)
    for table in tables:
        jsonschema.validate(table.data, schemas["tables"])


@pytest.mark.m6b
def test_detector_flags_doctored_totals_cue_without_guessing(tmp_path):
    document = _document(tmp_path, totals_columns="(d), (e), and (h)")
    batch = generate_outline_first_drafts(
        document,
        client=PromptAwareMicroClient(),
        config={"llm": {"model": "mock-model", "temperature": 0}},
        root=ROOT,
    )

    assert batch.items("tables") == []
    flagged = [obj for obj in batch.objects if obj.flags]
    assert flagged
    assert any("missing cue columns g" in flag for obj in flagged for flag in obj.flags)


@pytest.mark.m6b
def test_detector_does_not_trigger_on_single_row_grid(tmp_path):
    batch = generate_outline_first_drafts(
        _document(tmp_path, row_count=1),
        client=PromptAwareMicroClient(),
        config={"llm": {"model": "mock-model", "temperature": 0}},
        root=ROOT,
    )

    assert batch.items("tables") == []
    assert not any(obj.flags for obj in batch.objects)


@pytest.mark.m6b
def test_detector_groups_local_cached_8949_artifacts_when_present():
    raw_dir = ROOT / ".cache" / "raw" / "2025"
    form_text = raw_dir / "form_8949_2025.txt"
    form_fields = raw_dir / "form_8949_2025.fields.json"
    instructions_text = raw_dir / "instructions_form_8949_2025.txt"
    if not form_text.exists() or not form_fields.exists() or not instructions_text.exists():
        pytest.skip("local rendered Form 8949 cache not present")
    document = SourceDocumentInput(
        document_id="form_8949_2025",
        kind="tax_form",
        year="2025",
        url="https://www.irs.gov/pub/irs-pdf/f8949.pdf",
        text=form_text.read_text(encoding="utf-8"),
        text_path=form_text,
        fields=json.loads(form_fields.read_text(encoding="utf-8")),
        fields_path=form_fields,
        related_sources=[
            RelatedSourceInput(
                document_id="instructions_form_8949_2025",
                kind="instructions",
                text=instructions_text.read_text(encoding="utf-8"),
                text_path=instructions_text,
                relationship="instructions",
            )
        ],
    )

    batch = generate_outline_first_drafts(
        document,
        client=PromptAwareMicroClient(),
        config={"llm": {"model": "mock-model", "temperature": 0}},
        root=ROOT,
    )

    assert [table.object_id for table in batch.items("tables")] == [
        "form_8949_2025_part_i_line_1",
        "form_8949_2025_part_ii_line_1",
    ]


def _document(tmp_path: Path, *, totals_columns: str = "(d), (e), (g), and (h)", row_count: int = 3) -> SourceDocumentInput:
    text_path = tmp_path / "form_8949_2025.txt"
    text = "\n".join(
        [
            "# Page 1",
            "Header: Part I Short-Term. Box A Box B Box C",
            "Header: (a) Description (d) Proceeds (e) Cost (g) Adjustment (h) Gain or loss",
            "- 1: Transaction table",
            f"- 2: Totals. Add the amounts in columns {totals_columns}",
            "Header: include on your Schedule D, line 1b",
            "- 3: (if Box C or Box I above is checked)",
            "# Page 2",
            "Header: Part II Long-Term. Box D Box E Box F",
            "Header: (a) Description (d) Proceeds (e) Cost (g) Adjustment (h) Gain or loss",
            "- 1: Transaction table",
            f"- 2: Totals. Add the amounts in columns {totals_columns}",
            "Header: include on your Schedule D, line 8b",
            "- 10: (if Box F or Box L above is checked)",
            "",
        ]
    )
    text_path.write_text(text, encoding="utf-8")
    return SourceDocumentInput(
        document_id="form_8949_2025",
        kind="tax_form",
        year="2025",
        url="https://www.irs.gov/pub/irs-pdf/f8949.pdf",
        text=text,
        text_path=text_path,
        fields={"fields": _form_8949_row_fields(row_count=row_count)},
        related_sources=[
            RelatedSourceInput(
                document_id="instructions_form_8949_2025",
                kind="instructions",
                text="\n".join(
                    [
                        "# Page 1",
                        "Column (h). Subtract column (e) from column (d), and include column (g).",
                        "Report the totals on Schedule D lines 1b, 2, and 3.",
                        "Report long-term totals on Schedule D lines 8b, 9, and 10.",
                        "",
                    ]
                ),
                text_path=tmp_path / "instructions_form_8949_2025.txt",
                relationship="instructions",
            )
        ],
    )


def _form_8949_row_fields(*, row_count: int) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    x_clusters = [25, 175, 225, 275, 350, 400, 450, 500]
    for part in [1, 2]:
        for row in range(1, row_count + 1):
            for index, x_cluster in enumerate(x_clusters, 1):
                fields.append(
                    {
                        "field_name": (
                            f"topmostSubform[0].Page{part}[0].Table_Line1_Part{part}[0]"
                            f".Row{row}[0].f{part}_{row:02d}_{index:02d}[0]"
                        ),
                        "page": part,
                        "x_cluster": x_cluster,
                        "y_cluster": 400 + row * 25,
                    }
                )
    return fields
