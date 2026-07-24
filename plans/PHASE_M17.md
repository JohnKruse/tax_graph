# Phase M17 - Review Workbench v2 (cell-atomic review)

**Status:** ACTIVE (John approved the design 2026-07-24). This phase resumes and
supersedes the PAUSED M15 A12/A13 verdict-writing work with a redesigned UX. The
current shipped UI has a disabled "Verdicts not yet wired" bar and a drafts+toggle
drawer John rejected on review; that review is what started the whole M16 pipeline
detour. M15 stays the pre-ship gate; this is the surface that closes it.

## Why this phase exists

John's 2026-07 human review of the workbench exposed two things: the layout was wrong,
and there was no way to leave durable, per-item review comments. The redesign reframes
review around the **cell as the atomic unit**: the IRS designs forms as discrete cells,
so if each cell is individually verified, the form is verified. Review becomes per-cell
approve/reopen with a running count and jump-to-next, not a single form-level verdict.

## The approved design (mockup signed off 2026-07-24)

Three panes, left to right, 15 / 40 / 45:
- **LEFT (15%)** - a fixed dashboard on top (selected-document metadata: reviewed? by
  whom? when?; the approved-count stat; Cancel / Save progress / Submit) over a SCROLLING
  document picker (each row: status, approved-count, last-touched).
- **CENTER (40%)** - the ACTUAL rendered PDF page (the existing `/api/documents/<id>/
  pages/<n>.png` raster) with clickable translucent cell highlights positioned by each
  unit's `official_location` geometry. Needs zoom in/out + fit-width + pan.
- **RIGHT (45%)** - a scrolling "river" of atomic cell blocks. Each block: a meaningful
  label (`display_name`), a breadcrumb, a short quotable REF, the graph data/metadata,
  the M16-S4 structural flags for that cell, an approve switch, and a note box. Page and
  river selection are bidirectional.

Cross-cell correctness (line 3 = 1z + 2, totals, missing nodes) is NOT covered by per-cell
approval; it is exactly what the M16-S4 structural validators check, so the automated
flags shown in each block and the human per-cell approval are complementary.

## How it maps onto existing code (little is new)

- **Cells already exist:** manifest units (`workbench/manifest.py`) carry `unit_id`,
  `display_name`, `official_location` (page + geometry), `object_refs`, `address_id`.
- **The page viewer already exists:** `GET /api/documents/<id>/pages/<n>.png` + geometry.
- **Draft state already exists:** `workbench/sessions.py` + `schemas/session_state.schema.json`
  (non-authoritative resume state: current unit, page, zoom, a single `notes` string,
  visited units). The API round-trips it at `GET/PUT /api/sessions/<queue_id>`.
- **Finalized verdicts already exist:** append-only `workbench/verdicts.py` +
  `POST /api/verdicts`, schema'd with `object_ref`, `reviewer_id`, `reviewed_at`,
  `human_minutes`, `verdict`, `reason`.

The gap is the per-cell review layer between the two: mutable draft approve/note per unit
(sessions), finalized to append-only verdicts on Submit. The frontend is the other gap.

## Step sequence (just-in-time refined; backend before UI)

- **S1 - per-unit review state (backend, this round).** Extend `session_state.schema.json`
  with per-unit review records (unit_id, approved/open, note, updated_at); update
  `sessions.py` default + helpers; round-trip through the session GET/PUT API; expose a
  DERIVED progress summary (approved / total) computed on read, never stored. Tests only;
  no verdict-emission change, no manifest change, no frontend.
- **S2 - the quotable cell ref (backend, projection only).** A short, ASCII, stable ref
  per manifest unit, deterministic from the canonical address and unique within a
  document (notes/citations are ASCII-only, so the ref must be ASCII - no middot).
  Additive to the review projection; no authoritative writes.
- **S2b (deferred, NOT autonomous) - submit->verdict flow.** Wire Submit to emit one
  verdict per approved unit through the existing append-only verdict API; define the
  finalize/reopen semantics and the count. This touches the AUTHORITATIVE verdict path
  (the no-mutation boundary), so it is done with Architect review, not an unattended
  round - sequence it with or after the frontend Submit button that drives it.
- **S3+ - frontend rebuild to the approved mockup.** The three-pane shell, the dashboard +
  picker, the PDF viewer with geometry overlays + zoom, the review river with refs /
  switch / notes, bidirectional selection. Likely more than one step.
- **S-last - e2e coverage** for the new surface (the existing `tests/e2e` harness) and a
  live pass.

## Invariants carried in

- Sessions stay non-authoritative; `human_confirmed: true` is still earned only through the
  reviewed verdict pipeline. Verdicts stay append-only.
- ASCII only; the amended granular test-tier floor applies (Tier 1 focused files every
  commit, watched CI every push).
- Every fillable/checkable control carries exactly one population policy and is reviewable
  (the form-coverage invariant) - this phase is how that gets human-verified.
