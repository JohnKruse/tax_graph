from __future__ import annotations

import pytest

from tax_graph.acquire.soi import fetch_soi_csv_counts
from tax_graph.frontier.soi import load_form_id_map, load_soi_counts


from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.m7
def test_soi_reference_loads_core_forms_and_power_law():
    counts = load_soi_counts(ROOT)

    assert counts.soi_year == 2023
    assert "sample-based estimate" in counts.note
    for document_id in [
        "form_1040_2025",
        "schedule_d_2025",
        "form_8949_2025",
        "schedule_b_2025",
        "schedule_3_2025",
    ]:
        assert counts.counts[document_id] > 0
    assert counts.counts["form_1040_2025"] > counts.counts["form_1116_2025"]
    assert counts.counts["form_1116_2025"] > counts.counts["form_8396_2025"]


@pytest.mark.m7
def test_soi_acquire_parser_uses_label_map_without_runtime_httpx():
    mapping = load_form_id_map(ROOT)
    csv_text = 'label,returns\nSchedule D,"24,000"\nUnknown Form,10\n'

    counts = fetch_soi_csv_counts(
        "https://example.invalid/soi.csv",
        mapping=mapping,
        label_field="label",
        count_field="returns",
        fetch_text=lambda _url: csv_text,
    )

    assert counts == {"schedule_d_2025": 24000}
