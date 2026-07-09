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

**BALL: CODEX (when tokens refresh).** Next action: M11 Step 1 (1040 spine extraction +
promotion, worker-heavy), then Steps 3-6 in order. Step 2 is DONE: implemented by
Antigravity, Architect-reviewed line by line, ONE real error found and fixed (see
"Step 2 review findings" in From Architect - read them; three carry directives for
Step 3). Full pytest 242 passed / 4 skipped; both new drills caught at L3; ASCII green.
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
- **Step 2 review findings (Architect, 2026-07-09; line-by-line per the QC contract,
  net-touching diff).** Antigravity's slice was good overall; verified against the
  cached official 1040 instruction text. Findings:
  1. **FIXED - real value error:** the Head-of-Household 37% bracket floor was authored
     as 375800 (the MFS figure) in ALL THREE copies (graph node, `properties.py`
     expected dict, `tax_table.py` compiler constant). Source text confirms 626350
     ("Over $250,500 but not over $626,350 ... 35%"; "Over $626,350 ... 37%").
     Corrected everywhere (cumulative 187031.5). The generated tax table was
     unaffected (error sat above the $100k table ceiling). This is the
     same-author-both-sides circularity risk made real: the L3 expected dict CANNOT
     catch an error authored consistently into both places.
  2. **Directive for Step 3 (Codex): single-source the brackets.** Three copies of the
     bracket constants now exist. The `tax_table.py` compiler must READ the bracket
     parameter nodes from the graph instead of carrying its own copy; `properties.py`
     stays as the independent tripwire restatement (that one is deliberate).
  3. **Directive for Step 3/4: value-bearing citations.** `cite_1040_tax_brackets`
     quotes only the schedule section HEADERS, so citation integrity cannot witness
     the numbers. Add per-status citations quoting the actual schedule rows (the
     rendered instruction text has them; the HoH error would then be
     mechanically catchable).
  4. **Minor, fold into Step 4:** the generated table's sub-$25 rows use five $5 bands;
     the published table uses 0-5 / 5-15 / 15-25. Values are identical for all incomes
     (verified), but align the structure with the published table for exactness.
  Positive verification: generated cells match the PUBLISHED table (row 25200-25250 ->
  2789/2550/2789/2687 confirmed against cached instructions; midpoint + schoolbook
  rounding reproduces the IRS method); regeneration after the fix is byte-identical;
  QDCGT breakpoints, OBBBA-updated standard deductions, and all other bracket
  floors/cumulatives independently verified correct.
- **AUTHORIZED (2026-07-09): M11 Step 2 runs OUT OF ORDER on Antigravity (John's
  harness call; Codex token-limited for a few hours).** Step 2 is order-independent:
  its parameter nodes and data cite the 1040 instructions directly and nothing in it
  needs Step 1's extraction outputs. Scope guard: everything in the Step 2 spec EXCEPT
  wiring to the new engine ops - author the bracket/threshold data in the shape
  LOOKUP_BRACKET will consume, but the op itself and any rule using it wait for Step 3
  (Codex). Tests validate data shape, lookups-as-data, citations, and the two drills
  (`wrong_bracket_value`, `wrong_standard_deduction` - the L0 magic-number layer or
  parameter-diff layer may be the catcher until Step 3's execution paths exist; record
  which). One worker at a time in the clone - Antigravity stops and updates the BALL
  line before Codex resumes.
- **NEW (2026-07-09) - Distribution plan PINNED (John's call; canonical in
  `docs/distribution.md`).** Channels in priority order: PyPI (`tax-graph`, confirmed
  available; alpha `0.1.0a1` built, upload pending John's PyPI token) -> `.mcpb` Claude
  Desktop bundle + Connectors Directory -> official MCP Registry (namespace auto-owned
  via GitHub auth) -> aggregators. Packaging work lands in M14; STABLE release gates on
  M15. Hard lines: no taxpayer data leaves the machine, no e-file, seasonal versioning,
  alpha releases carry the not-tax-advice disclaimer. pyproject now carries alpha
  status + urls metadata (version `0.1.0a1`).
- **NEW (2026-07-09) - Roadmap M11-M15 + output goal PINNED (John's calls; canonical in
  engineering-plan "Roadmap M11-M15" and "Output goal").** Sequence: M11 first liability
  branch (QDCGT + line 16 + PolicyEngine second witness) -> M12 output layer (filled
  official PDFs as the FILING deliverable, OTS input sidecar, return-scoped output
  contract) -> M13 worksheet depth -> M14 product surface (self-serve + intake) ->
  M15 Review Workbench + review campaign (the PRE-SHIP GATE; review debt keeps
  accumulating in the queue until then, by design). E-file/MeF submission is explicitly
  OUT of scope (arm's-length stance); MeF stays a completeness witness only.
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
