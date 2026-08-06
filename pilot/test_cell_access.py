"""Tests for the pilot's single cell-text access boundary."""

from __future__ import annotations

import os
from pathlib import Path

from cell_access import form_face, join_rows, label
from review_panel import build_panel


CANDIDATE = Path(
    os.environ.get(
        "M20_S73_CANDIDATE",
        r"C:\Users\devbox\AppData\Local\Temp\claude\C--Users-devbox-projects-tax-graph\6e1d97d0-c72d-4855-a055-e0c64f6224f8\scratchpad\cand_s71",
    )
)


def test_empty_caption_is_typed_absence_and_does_not_fall_back() -> None:
    cell = join_rows(
        anchor={"label": "raw anchor fallback"},
        source={"label_after": "", "form_face_after": "Printed form text"},
        candidate={"label": "raw candidate fallback"},
    )

    caption = label(cell)
    assert caption.value is None
    assert caption.present is False
    assert form_face(cell).value == "Printed form text"


def test_real_candidate_caption_invariant_covers_every_panel() -> None:
    panel = build_panel(CANDIDATE)
    assert len(panel["panels"]) == 157
    assert panel["text_presence"]["caption"] + panel["text_absence"]["caption"] == 157

    for row in panel["panels"]:
        value = row["label"]
        if value is None:
            continue
        token = str(row["line"]).strip().lower()
        lowered = value.strip().lower()
        assert not (
            lowered.startswith(f"{token} ")
            and lowered.endswith(f" {token}")
        ), row["anchor_id"]
