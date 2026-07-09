# AGENT_HANDOFF.md

The single living doc for active Claude (Architect) <-> Codex (Worker) coordination. Update it in
place; do NOT spawn new per-topic note files. Standing rules: `../AGENTS.md`. Master plan:
`../docs/engineering-plan.md`.

## How to use
- **Worker:** raise questions/blocks under **Open for Architect**.
- **Architect:** answer there (and pin durable decisions into the relevant `PHASE_<id>.md`), then
  clear the item. Record active direction under **From Architect**.
- Keep it short - move resolved items to **Resolved** or delete them.
- History: pruned 2026-07-07 (full snapshot: `plans/archive/AGENT_HANDOFF_2026-07-07_full.md`)
  and again at M9 close 2026-07-08 (M9 narration lives in `plans/archive/PHASE_M9.md` + git
  history). Archived phase plans: `plans/archive/PHASE_*.md`.

## Current state (2026-07-09)

**BALL: ARCHITECT.** Next action: plan M11 (await John's direction on scope). M10 is
CLOSED: Architect independently verified all exit criteria on 2026-07-09 (see Latest
verification) and pushed. John has been told.
(Whoever finishes a turn: update this BALL line - it is the first thing read.)

- **M0-M10 are COMPLETE.** M10 closed with the batch OTS-witnessed set promoted: Schedule 1,
  Schedule 1-A, Schedule 2, Schedule 3, Schedule A, Schedule B, and Form 6251 are now live beside
  the existing 1040 / 1099-B / 8949 / Schedule D surface.
- **Coverage after M10:** `90.1%` full-universe (`435450000 / 483540000`) and `100.0%` in-scope
  (`435450000 / 435450000`), up `+47.7` and `+57.6` points from the M9 baseline `42.4%` /
  `42.4%`. The only remaining declared frontier item is the intentional deferred branch
  `schedule_d_2025 line 20`; rejected Form 6251 false-positive flows stay recorded as
  `rejected`, not declared.
- **Step 7 exit-run fix summary (Codex, 2026-07-09):**
  - Hardened M7 coverage tests to derive expectations from fixture/SOI data and to use a
    synthetic unmodeled weighted-form scenario rather than assuming the live graph still has
    headroom.
  - Hardened the M2 citation FTS test to assert on a phrase unique to `cite_8949_col_h_gain`
    instead of corpus-order ranking.
  - Fixed the real M5 product bug in `tax_graph/record/return_record.py`: Return Record
    trace/unsupported sections are now scoped to the touched return target rather than dumping
    unrelated graph-wide blank nodes. Added a regression test that a capital-gains-only memo
    mentions no untouched forms.
  - Refreshed `tests/fixtures/return_record_capital_gains.md` to the corrected scoped memo shape.
- **Verification surface:** `VERIFICATION.md` and 11 per-form pages are regenerated and ready to
  commit, including new pages for `form_6251_2025`, `schedule_1_2025`, `schedule_1a_2025`,
  `schedule_2_2025`, `schedule_3_2025`, `schedule_a_2025`, and `schedule_b_2025`.
- **Machine-cost report:** `verify report` totals remain `objects=685`, `tiers(T0/T1/T2/T3)=510/175/0/0`,
  `review=510`, `calibration=18`, `escapes=0`, with `worker_tokens=None`, `worker_cost=None`,
  and `human_minutes=None` honestly unrecorded for every form.

## Open for Architect
- (none)

## From Architect
- Return Record durable pin (2026-07-09, now implemented): the Return Record is scoped to the
  return, never the full graph. It contains only supplied facts, nodes on the computed trace,
  decisions touched, carryforwards, and explicit unsupported/deferred items touched by that
  return.

## Latest verification
- M10 phase close, Architect independent verification (2026-07-09) - ALL GREEN:
  - Full `pytest -q` -> 238 passed, 4 skipped (after fixing one closeout-order test
    breakage: `test_parse_phase_plan_handles_wrapped_real_plan_headers` read the LIVE
    `plans/PHASE_M10.md`, which the archive move deleted; it now reads a frozen fixture
    `tests/fixtures/phase_plan_wrapped_headers_m10.md` - tests must never depend on the
    plans/ lifecycle)
  - `validate 2025` OK; `build 2025` OK; ASCII OK
  - Parity: line 7 = 2000 on yaml AND sqlite; multi-lot 250 on yaml
  - Base-deps `uv run --no-dev`: run -> line 7 = 2000; frontier -> 90.1%
  - `frontier` -> 90.1% full-universe / 100.0% in-scope (+47.7 / +57.6 vs M9 baseline)
  - `oracle replay-corpus` -> 20 scenarios OK (widened corpus, seed 20260709,
    `live_ots_diff_report`); `verify replay-examples` -> OK
  - `drill run` -> 11/11 caught with expected layer attribution (incl.
    `wrong_capital_loss_limit_parameter` at L3)
  - `verify record` regeneration -> BYTE-STABLE (zero git drift across the 11 pages)
- Observation noted for M11 planning (not a blocker): `run` CLI output lists
  other-form nodes as `= None` on a capital-gains-only run (e.g.
  `schedule_1_2025_part_i_line_7 = None`) - same graph-vs-return scoping class as the
  fixed memo bug, but in diagnostics output; decide the intended contract in M11.
- M10 closeout (worker, 2026-07-09):
  - `.\.venv\Scripts\python.exe -m pytest -m m10 -q` -> 20 passed, 222 deselected
  - `.\.venv\Scripts\python.exe -m pytest -q` -> 238 passed, 4 skipped
  - `.\.venv\Scripts\python.exe tools/check_ascii.py` -> ASCII check OK
  - `.\.venv\Scripts\python.exe -m tax_graph.cli validate 2025 --root C:\Users\devbox\projects\tax_graph` -> graph integrity OK
  - `.\.venv\Scripts\python.exe -m tax_graph.cli build 2025 --root C:\Users\devbox\projects\tax_graph` -> built `build/tax_graph_2025.sqlite`
  - `.\.venv\Scripts\python.exe -m tax_graph.cli run --facts examples\capital_gains_basic\facts.yaml --year 2025 --root C:\Users\devbox\projects\tax_graph` -> `form_1040_2025_line_7_capital_gain_loss = 2000`
  - `.\.venv\Scripts\python.exe -m tax_graph.cli frontier --year 2025 --root C:\Users\devbox\projects\tax_graph` -> coverage `90.1%` full / `100.0%` in-scope
  - `.\.venv\Scripts\python.exe -m tax_graph.cli verify record --year 2025 --root C:\Users\devbox\projects\tax_graph` -> regenerated `VERIFICATION.md` and 11 per-form pages
  - `.\.venv\Scripts\python.exe -m tax_graph.cli verify report --year 2025 --root C:\Users\devbox\projects\tax_graph` -> worker tokens/cost and human minutes not yet recorded

## Resolved / superseded
- M10 phase plan is archived at `plans/archive/PHASE_M10.md` once this closeout commit lands.
- Earlier detailed M10 narration is intentionally pruned; use git history plus archived phase
  plans for the full step-by-step record.
