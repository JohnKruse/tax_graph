# AGENT_HANDOFF.md

The single living doc for active Claude (Architect) <-> Codex (Worker) coordination. Update it in
place; do NOT spawn new per-topic note files. Standing rules: `../AGENTS.md`. Master plan:
`../docs/engineering-plan.md`. Phase plan: `PHASE_M20.md`.

## How to use
- **Worker:** raise questions/blocks under **Open for Architect**.
- **Architect:** answer there (and pin durable decisions into the relevant `PHASE_<id>.md`), then
  clear the item. Record active direction under **From Architect**.
- **THIS FILE IS LIVE STATE ONLY.** The ball, the round in flight, the open questions, and the
  ONE task spec being worked. Durable rulings and standing constraints live in `../AGENTS.md`
  and are never pruned. History lives in git. **Queued future rounds are ONE LINE each** - a
  full spec written rounds ahead goes stale, which is exactly what happened to S57.
- **Keep it short.** A round that completes gets its narration DELETED, not appended - the
  accepted hash is the record and `git show <hash>` recovers everything. Only the current round,
  the standing constraints, and the binding rulings live here.
- **Prune at every acceptance, not "at phase close".** Pruned 2026-07-23 to 1,198 lines, then
  grew to 7,520 by 2026-08-02 because acceptance never triggered a prune. That is the failure
  mode this section exists to prevent.

## BALL

**BALL: WORKER - M20-S64 (REGENERATE A CANDIDATE GRAPH FROM A FULL RUN).** Active spec is under
Current round. **S67 is ACCEPTED at `bb3daca`; the corpus is recovered.**

**Live: 67 attempted, 60 derived, 2 repaired, 5 errored.** `form_1040_2025` back to **17/17 with
zero repairs**, 2441 **18/21**, 6251 **25/29**. `doctor` gained a **`roles`** column, so the
layer-disagreement that caused S66 is now a check rather than a lesson.

**THE S54 COMPLETENESS VALIDATOR FIRED ON REAL DATA FOR THE FIRST TIME**, and correctly. 2441 line 8
produced all sixteen bands as CUMULATIVE thresholds (`under_15000=0.35, under_17000=0.34, ...`)
rather than the source's explicit ranges, and the validator refused it -
`lookup_table_band_overlap`, `lookup_table_missing_bands`, `lookup_table_bounds_mismatch`. Under
first-match semantics "under 17,000" contains "under 15,000", so the refusal is right. **The row has
still never derived, but it now fails for the correct reason.**

**QUEUE - one line each.**
1. **S64 candidate regeneration** - first full run; expect ~121 of 478 anchors.
2. **Construction grammar (Architect measuring first)** - John, 2026-08-05: a checkbox is boolean and
   the PDF says so (2441 carries 57 Text and **15 CheckBox** widgets); punctuation carries the
   structure, and `BASE (VARIANT if CONDITION)` is a systematic parenthetical construction that maps
   onto the lookup shape that already works.
3. **Construction drift detection** - John: reviews must call out new punctuation and usage as a
   ranked finding with system-filed evidence, against a VERSIONED construction inventory.
4. **Column and grid recovery**; **phrase obligations**; **S53 approval gate**; **known-red cleanup**.

**STANDING FAILURES, unchanged and honest.** 2441 line 25 wrong for the **seventh** consecutive run.
6251 lines 13 and 20 still fail closed on the worksheet references, which regeneration addresses.

## Current round

**M20-S64 IN FLIGHT (Worker, 2026-08-06).** Canary: **Ground Truth**.

This round implements S3a regeneration and the pipeline-only operating loop. It consumes a
completed provider run and writes a candidate outside the published graph; it does not call a
provider, tune the selector, hand-author graph objects, publish, or touch the protected live graph.

1. Build a deterministic candidate writer from completed derive reports. Preserve the per-document
   printed-anchor denominator and report attempted, derived, repaired, gapped, errored, and skipped
   anchors with explicit skip reasons. Candidate expression and citation evidence must stay paired;
   a derived row without a citation is a named candidate finding, never an accepted candidate row.
2. Emit a candidate draft layout usable by the read-only review projection, and copy only the
   manifest's harvested worksheet drafts into the candidate workspace. No candidate file is written
   under `graph/<year>/_drafts`.
3. Compare candidate addresses and expressions with the handcrafted graph as a review list: in both,
   candidate-only, handcrafted-only, and expression disagreements listed individually rather than
   collapsed to a count.
4. Add an explicit candidate-root input to `review-table`, keeping the existing live-graph fallback.
   The command must render the candidate's actual expression or an explicit gap for each source row.
5. Record the publish path in the candidate manifest without taking it: publication would replace
   the live generated artifacts after review, and rollback is the prior committed tree. The candidate
   is never a human-confirmed claim.

Focused tests: `tests/test_candidate_regeneration_m20.py` and the existing
`tests/test_review_table_m20.py`.

Evidence from this Worker session:

- `RAN: $testTempRoot='C:\Users\devbox\.codex\visualizations\2026\08\06\019fd619-8ec3-7ee0-9f53-2611fa6a2ac9\pytest-temp'; $env:PYTEST_DEBUG_TEMPROOT=$testTempRoot; .venv\Scripts\python.exe -m pytest tests/test_candidate_regeneration_m20.py tests/test_review_table_m20.py tests/test_run_summary_m20.py tests/test_derive_cells_s30.py -q -> 18 passed, 1 warning.`
- `RAN: $testTempRoot='C:\Users\devbox\.codex\visualizations\2026\08\06\019fd619-8ec3-7ee0-9f53-2611fa6a2ac9\pytest-temp'; $env:PYTEST_DEBUG_TEMPROOT=$testTempRoot; .venv\Scripts\python.exe -m pytest tests/test_derive_cells_s30.py tests/test_m20_s31.py tests/test_cli.py -q -> 16 passed, 2 failed, 2 warnings.` The failures are the existing `operation_documentation` prompt fixture omission in `tests/test_m20_s31.py::test_all_prompt_templates_render_with_representative_values` and the existing missing temporary `config/manifest.yaml` in `tests/test_cli.py::test_harvest_worksheet_command_writes_only_a_draft`; neither was weakened.
- `RAN: .venv\Scripts\python.exe -m tax_graph.cli validate 2025 -> exit 0; documents=18, nodes=441, edges=409, rules=17, citations=401; graph integrity OK.`
- `RAN: .venv\Scripts\python.exe tools\check_ascii.py -> ASCII check OK.`
- `RAN: git diff --check -> clean.`
- `RAN: .venv\Scripts\python.exe -m tax_graph.cli --help`, `regenerate-candidate --help`, and `review-table --help` -> new options rendered successfully; CLI materialization and candidate-root review-table smoke -> exit 0.`
- `NOT RUN: provider execution and live full-corpus derivation; the provider leg is the Architect's.`

## Open for Architect

**Nothing is open for the Architect.** The three items `doctor` flagged STALE at 73 commits on
2026-08-05 are closed: the **S36 denominator decision** (moot - S51 replaced the denominator
with 121 of 478 anchors and a named reason per skip); the **two scoping calls** (worksheets
closed by the S59 nomination chain; the filing-status constant answered by measurement -
`schedule_1a_2025` line 17 and `form_6251_2025` line 18 both emit correct role-keyed lookups);
and **"what is next"** (John chose option (b), structure and association, on 2026-08-05).

**Open for JOHN, not blocking:** during bootstrap, "every cell receives meaningful human
approval before use" and "a human does not read every new cell" cannot both hold. The pipeline
can eliminate RE-review - approve once against stable semantics, fingerprint the clauses, carry
the verdict while nothing changes - but not first review. That decision shapes S53.

## From Architect

**One spec at a time. The next round is specced when it is picked up.**

## History

Everything before M20-S23, and all per-round Worker narration, lives in git history. This file was
pruned from 7,520 lines on 2026-08-02 at S28 acceptance; `git show 12240ef:plans/AGENT_HANDOFF.md`
is the last unpruned copy. Earlier prune: 2026-07-23, from 1,198 lines, for public-repo prep.
Durable rulings were carried forward into **Binding rulings** above rather than deleted; A9
rulings remain pinned in `plans/PHASE_M15.md`; the defect ledger (D6, D9, D10, D12, D13, D14) is
in `AGENTS.md`.
