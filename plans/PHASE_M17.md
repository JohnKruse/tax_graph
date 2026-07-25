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
- **S3 - three-pane shell (DONE, `b625584` and prior).** Drawer UI replaced with the
  15/40/45 shell, PDF viewer + geometry overlays, review river, bidirectional selection.
- **S3R - FORM-SOURCED CELL SPINE (this round, John's first-review correction).**
  John's first-minute review of the S3 shell found the review was sourced from the
  deferred-review QUEUE re-bucketed by a synthetic "check group" taxonomy, not from the
  form. Symptoms: orphan cells (center/right driven by different scopings), fully-parsed
  cells missing from review because they were never queued (combat zone, tax year,
  deceased), and identity fields miscategorized under "Calculations" (the `_check_group`
  default). Ruling: **the review unit is the form cell.** Changes:
  1. New `workbench/cell_inventory.py` assembles the form-complete, reading-order cell
     list per document by joining geometry (spine) + address inventory (label/line/role)
     + field dispositions (the one population policy) + node bindings (the computing
     node), all on `address_id`/`field_name`. Projection-only, stdlib+yaml only (respects
     the M17-S2 import boundary). Verified on the 1040: 159 physical cells, 100% with
     geometry, zero cells missing a policy, "First name and middle initial" is a
     `user_entered` identity input (not a calculation).
  2. New document-centric API in `workbench/server.py`: `GET /api/documents`,
     `GET /api/documents/<id>/cells`, and per-document session `GET/PUT
     /api/documents/<id>/session` (review state keyed by a sanitized `[a-z0-9_]` cell id,
     scoped to the document's cells, reusing the non-authoritative session machinery).
  3. Frontend re-sourced onto it (`app.js`, `panes.js`, `river.js`, `api.js`,
     `keyboard.js`, `index.html`): left rail picks a form; center renders every cell of
     the page as a clickable region; right river is the same cells top to bottom (page
     dividers) with per-cell approve + note; the detail panel shows what FEEDS the cell -
     policy + format for inputs, the operation + operand cells + citations for computed
     cells. The check-group layer (`navigation.py`) is no longer used by the UI.
  Tests: `tests/test_workbench_cells_m17.py` (`m17` marker).
- **S3R2 - NAVIGATION + SELECTION CONTRAST (John's second-review corrections 1 and 2).**
  Pure frontend; no API, no artifact, no data-model change.
  1. **The river must follow the form.** Today `app.js` `_selectionHandler` calls
     `selectRiverUnit` + `activateRiverUnit`, which set the `.selected` class and render
     the detail - but NOTHING scrolls the river. With 100+ cards the selected one is
     usually off-screen. Fix: after selection, scroll the card into view
     (`scrollIntoView({block: "center"})`) within the river's own scroll container only -
     it must not scroll the page or steal focus mid-typing in a note.
  2. **Cross-page selection is a dead end (the "completely hosed" case).** `app.js`
     `_riverSelectionHandler` does
     `document.querySelector('#official-pane [data-unit-id=...]')` and then
     `if (!official) return;` - so selecting a river card for a cell on a DIFFERENT page
     silently does nothing. Fix: resolve the cell's `page` from the model; if it is not
     the rendered page, `renderReview(cell.page, cell.cell_id)` first, then select. The
     same must hold in reverse and for keyboard next/prev: crossing a page boundary is a
     normal move, never a no-op. Watch the `syncingSelection` re-entrancy guard -
     `renderReview` rebinds both handlers, so the guard must not be left stuck true.
  3. **Selected-cell contrast.** `.official-region.policy-unsupported` uses
     `--accent: var(--danger)` (brick red) and `.official-region.pinned` uses
     `outline: 3px solid #c5452d` - red selection on a red cell. Fix: give selection a
     treatment that cannot collide with ANY policy hue - a distinct high-contrast ring
     (e.g. a double ring: dark inner + white/light outer halo so it reads over both black
     form ink and any fill), plus a non-color cue (weight/thickness) so it survives
     color-blindness and grayscale. Policy stays the fill/border hue; selection is the
     ring. Also scroll the selected region into view in the center pane when it is
     off-viewport at the current zoom.
  4. Tests: extend `tests/e2e/test_workbench_v2_m17.py` (`m17`) - selecting a river card
     for a cell on another page switches the center page and marks it selected; clicking a
     form region scrolls its river card into view; the selected ring class is distinct from
     the policy class.

- **S4 - THE CELL DOSSIER (John's corrections 3 and 4): labeled, sourced cell data.**
  John's report: the detail panel is "empty" and "rolled together" - values with no labels
  and no provenance ("I have no idea where it is coming from"). Confirmed in the code:
  `river.js` `renderDetail` emits unlabeled lines, and `cell_inventory._citations` returns
  bare citation IDs (`cite_span_form_1040_2025_0007`), never the quoted text.
  1. **Resolve citations to their text.** `graph/2025/citations/*.yaml` already carries
     `quoted_text`, `locator`, `url`, `retrieved_date`, `source_document_id` per
     `citation_id`. Load them in `cell_inventory.py` (stdlib+yaml, keeping the M17-S2
     import boundary) and return resolved records, not ids. Render each as quoted text +
     locator + source, with the id secondary. Never synthesize or paraphrase citation text
     - it is verbatim-from-acquired-source, `check_citation_integrity` has teeth (the M14
     fabricated-citations reopen is the precedent).
  2. **Label every datum, and name its source artifact.** The dossier gets explicit
     labelled groups, each field tagged with the artifact it came from, so the reviewer can
     always see where a value originated:
     - *Identity* - display name, quotable ref, `address_id`, AcroForm `field_name`
       (sources: addresses inventory, geometry)
     - *On the form* - printed line/box, section breadcrumb, control role, page + rect
       (sources: addresses, `node_geometry.json`)
     - *Population policy* - the policy, plus `reason`, `downstream_effect`, and
       `missing_capability`, which the field maps ALREADY carry and the UI currently drops
       entirely (source: `field_maps/<doc>.yaml`)
     - *Graph* - `node_id`, the operation, and operand cells as hoppable refs
       (sources: `bindings/nodes/<doc>.yaml`, calc edges)
     - *Authority* - the resolved citations from item 1
     Absent data must render as an explicit "not authored" state, never a blank line - a
     missing value is itself a review finding.
  3. **Reframe the policy vocabulary (UI only this round).** The policy enum conflates two
     different axes, which is what made "Unsupported" read as nonsense next to
     "Filer-entered". They are:
     - *How the value is obtained*: `user_entered`, `imported`, `copied`, `computed`,
       `decision_required`
     - *Coverage status*: `unsupported` (no mapping authored yet), `intentionally_blank`
       (deliberate)
     Show them as two labeled facets, not one flat badge. Critically, `unsupported` does
     NOT mean "the filer cannot enter this" - the generated reason says it plainly: the
     control "has no authored graph, filer-fact, or decision mapping." It is a COVERAGE
     GAP, i.e. a backlog marker, and the UI must say so in those words. John is right that
     "Presidential election campaign - You" is an ordinary filer checkbox that merely lacks
     a mapping. **Do not rename the enum values in the promoted artifacts this round** -
     that is a Tier 3 promoted-artifact change across 605 cells and it is exactly what
     M16-S5 regeneration will rewrite; churning it twice risks the load-bearing data.
  4. **Surface the coverage gap as a number.** Per-document counts by policy in the left
     rail / dashboard, so "31% of this form has no authored mapping" is visible rather than
     discovered cell by cell. Corpus-wide today: 696 imported, 605 unsupported, 528
     user_entered, 47 computed, 24 decision_required, 13 copied, 8 intentionally_blank.
  5. Tests: `tests/test_workbench_cells_m17.py` (`m17`) - citations resolve to quoted text
     with locator and source; the three field-map disposition fields survive into the cell
     payload; policy counts per document are correct.

- **S4b - TEST PARTITION SPLIT (enabler, do this first in the S4 round).**
  `tests/test_workbench_cells_m17.py` currently imports `create_app`, whose startup
  preflight + manifest build makes the file take ~157s - OVER the Worker's ~124s launcher
  cap, so the Worker cannot verify its own work. Split the pure `cell_inventory`
  projection tests (fast, no `create_app`) from the API tests that need the app, so the
  Worker can run the fast file inside the cap and the Architect runs the app-dependent
  file. This is what makes the round Worker-runnable at all.

- **S5-INSTR - PER-CELL INSTRUCTION TEXT (JOHN HAS RULED, 2026-07-25: this is ROUTINE
  PIPELINE WORK, not an optional enhancement).** John's ruling on seeing that the
  instructions explain the purpose and treatment of nearly every cell: instruction
  ingestion is a first-class, routine stage of the forms pipeline, on the same footing as
  ingesting the form itself. Pinned as guiding invariant 7 in `docs/engineering-plan.md`.
  What remains open is SEQUENCING against M16 (it writes promoted artifacts and overlaps
  S5 regeneration), not whether it happens. Design notes below stand.
  John asked "Did you not parse the instructions?" Honest answer: the instruction PDFs ARE
  acquired (`.cache/raw/2025/instructions_*.pdf/.txt/.ocr.json` for 1040, 2441, 6251, 8949,
  Schedules A/B/D), but only ONE instruction citation exists in the whole promoted corpus
  (`cite_instruction_form_1040_2025_line_1a`, out of 297 citations). So there is no
  systematic per-cell instruction linkage - the acquired text was never mined into cited
  spans. Doing it means mining instruction prose per printed line and promoting it through
  the citation machinery (verbatim, integrity-checked), then joining on the canonical
  address. That is a pipeline job of M16 size, it writes promoted artifacts, and it
  interacts with M16-S5 regeneration - so it is NOT an unattended round; the Architect
  drafts it as a phase (likely an M16 stream or its own M18) for John to sequence.
  Note the compounding payoff John identified: instruction text is also what lets a
  coverage-gap cell (the 605 `unsupported`) be RESOLVED rather than merely reported -
  the instructions say what the cell is for, which is the input S5 regeneration needs.
  So instruction mining should land BEFORE or WITH M16-S5, not after it.

- **S-last - e2e coverage** for the new surface (the existing `tests/e2e` harness) and a
  live pass.

## Invariants carried in

- Sessions stay non-authoritative; `human_confirmed: true` is still earned only through the
  reviewed verdict pipeline. Verdicts stay append-only.
- ASCII only; the amended granular test-tier floor applies (Tier 1 focused files every
  commit, watched CI every push).
- Every fillable/checkable control carries exactly one population policy and is reviewable
  (the form-coverage invariant) - this phase is how that gets human-verified.
