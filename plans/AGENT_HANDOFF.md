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

**BALL: CODEX (interim; one worker at a time in the clone).** Authorized action:
M11 **Step 4** closeout rerun (blocked on local-Python approval budget), then 5b -> 6.
Step 5a REWORK (PolicyEngine PARAMETER-DIFF) is DONE (Antigravity). Live PE fetch yielded 20/20 matches.
(Whoever finishes a turn: update this BALL line - it is the first thing read.)

- **M0-M10 are COMPLETE.** M10 closed with the batch OTS-witnessed set promoted: Schedule 1,
  Schedule 1-A, Schedule 2, Schedule 3, Schedule A, Schedule B, and Form 6251 are now live beside
  the existing 1040 / 1099-B / 8949 / Schedule D surface.
- **Step 5a REWORK completion (Antigravity, 2026-07-09):** Fixed API import and parameter paths in the mapping YAML to reflect the live `policyengine-us` interface. Re-ran `verify parameter-diff` LIVE and recorded 20/20 matches across all mapped parameters. Offline fixtures aligned to the real paths.
- **Coverage after M10:** `90.1%` full-universe (`435450000 / 483540000`) and `100.0%` in-scope
  (`435450000 / 435450000`), up `+47.7` and `+57.6` points from the M9 baseline `42.4%` /
  `42.4%`. The only remaining declared frontier item is the intentional deferred branch
  `schedule_d_2025 line 20`; rejected Form 6251 false-positive flows stay recorded as
  `rejected`, not declared.
- **M11 Step 1 completion (Codex, 2026-07-09):** Added the first live Form 1040
  taxable-income spine through line 15. The live graph now carries Form 1040 line 1a,
  line 1z, linked line 2b/3b/8/10/13b carry-ins, line 9 total income, line 11a/11b AGI,
  line 14 total deductions, and line 15 taxable income with the zero floor. The line 1a
  extraction gap was filled with an authored form span plus instruction citation, while
  the rest of the spine reuses promoted 1040 draft spans. New fixture:
  `examples/taxable_income_basic/`. New tests:
  `tests/test_form_1040_spine_m11.py`. Deferred-review queue entry added:
  `promotion_review_form_1040_2025`.
- **M11 Step 3 completion (Codex, 2026-07-09):** Landed the first live Form 1040
  line 16 branch. Engine ops added: `MULTIPLY`, `LOOKUP_BRACKET`, and `IF_ELSE`,
  plus a tax-table data-resource lookup seam that works on yaml and sqlite loads.
  Form 1040 line 12e is now driven by the new decision
  `decision_1040_deduction_method` (`standard` vs `itemized` via Schedule A line 17).
  The graph now executes the Qualified Dividends and Capital Gain Tax Worksheet line by
  line (`form_1040_2025_qdcgt_line_1` .. `line_25`) and routes Form 1040 line 16
  between QDCGT, tax-table, and bracket paths with cited parameter nodes. Step 2's
  architect directive is closed in code: `tax_graph/compile/tax_table.py` now reads the
  authored bracket parameter nodes instead of carrying its own bracket copy, and the
  bracket / QDCGT breakpoint citations are now value-bearing instruction quotes.
  New tests: `tests/test_tax_liability_m11.py`, plus M11 updates to
  `tests/test_form_1040_spine_m11.py` and `tests/test_tax_table_m11.py`.
- **M11 Step 4 implementation (Codex, 2026-07-09):** Widened the OTS oracle harness to
  the tax line. The scenario/domain layer now supports all five filing statuses plus
  wages, taxable interest, qualified dividends, ordinary dividends, and standard-deduction
  tax-line cases. `oracles/box_map_2025.yaml` now maps `L11b` / `L12` / `L15` / `L16`,
  and the label inventory was extended to match. Added new M11 renderer/diff fixtures for
  a QDCGT scenario and a regular-tax-table scenario, updated the existing M6/M10 oracle
  fixtures to the widened contract, and extended the fake OTS corpus runner so freeze/
  replay tests keep agreeing with the widened box map. Also folded in the Step 2 review
  follow-up: `tax_graph/compile/tax_table.py` now emits the published under-$25 bands
  `0-5 / 5-15 / 15-25`, and `graph/2025/tax_table.json` was regenerated.
- **M11 Step 4 live-gate note (Codex, 2026-07-09):** A first live `oracle fuzz` run
  exposed a real renderer bug: when an OTS template omitted `L1a/L2b/L3a/L3b`, the
  renderer appended them after the Schedule D block instead of inserting them before
  `f8949_spreadsheet-A/D`, which OTS rejects. That insertion logic is now fixed in
  `tax_graph/oracles/scenario.py`. I could not run the post-fix rerun because the local
  Python approval budget was exhausted by the desktop tool reviewer. Next worker should
  rerun the oracle/corpus suites, then `tax-graph oracle fuzz --year 2025 --n 100 --seed 20260709`,
  and if clean re-freeze `examples/oracle_corpus/`.
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
- **Step 5a review findings (Architect, 2026-07-09) - REWORK REQUIRED on the live
  half; offline scaffolding accepted and committed.** Full pytest 244/4 green, ASCII
  green, seeded-wrong-value test works. But the live channel was hallucinated and
  never exercised: the Architect installed `policyengine-us` (left installed in the
  dev venv) and ran `verify parameter-diff` live -> 20/20 fetch errors. Two defects
  and the discovered GROUND TRUTH for the fix:
  1. **Wrong API.** `import policyengine_us; from policyengine_us import parameters`
     cannot read values (parameters are packaged YAML, not module attributes). The
     working pattern, verified live: `from policyengine_us.system import system`,
     then traverse `system.parameters` children and CALL the leaf with a date:
     `system.parameters.gov.irs.deductions.standard.amount.SINGLE("2025-01-01")`
     -> returns 15750 (live-confirmed).
  2. **Invented paths.** Real paths, verified live from the installed tree:
     - Standard deduction: `gov.irs.deductions.standard.amount.<STATUS>` with enum
       leafs `SINGLE | JOINT | SEPARATE | HEAD_OF_HOUSEHOLD | SURVIVING_SPOUSE`.
     - QDCGT breakpoints: `gov.irs.capital_gains.thresholds.<1|2>.<STATUS>` (1 = the
       0% top, 2 = the 15% top). Live values CONFIRM all ten of our Step 2 breakpoints
       exactly (e.g. 1.SINGLE=48350, 1.HEAD_OF_HOUSEHOLD=64750, 2.SEPARATE=300000,
       2.JOINT=600050).
     - Ordinary brackets: `gov.irs.income.bracket.rates.<1..7>` and
       `gov.irs.income.bracket.thresholds.<1..7>.<STATUS>` (thresholds.7 = inf).
       NOTE the offset semantics: OUR bracket entry floors correspond to PE's
       thresholds of the PREVIOUS index (floor of our bracket N = PE thresholds.N-1;
       our first floor 0 has no PE counterpart). The comparator must encode this
       offset explicitly - do not force-fit shapes. In the live run, verify
       `thresholds.6.HEAD_OF_HOUSEHOLD == 626350` and report it - that is the exact
       cell the Step 2 review corrected.
  3. Also fix: a PE fetch error must be its own status (`fetch_error`), not
     `disagree` - a disagreement means VALUES were compared; conflating them poisons
     the metric. Update the offline fixture to the REAL paths (it currently mirrors
     the invented ones - which is why offline tests could not catch any of this),
     regenerate, and keep the seeded-wrong-value test.
  Meta-lesson (recorded for the tier metrics): this is the second Antigravity slice
  whose self-checks were consistent-but-wrong (HoH value; now paths+fixture). The
  pattern: its own fixtures mirror its own assumptions. Slices whose correctness
  depends on an EXTERNAL interface must include a live probe or an
  Architect-supplied ground-truth fixture in the authorization.
- **AUTHORIZED (2026-07-09): M11 Step 5a on Antigravity - PolicyEngine PARAMETER-DIFF
  channel only (split from Step 5; 5b liability diff waits for Step 3's line 16).**
  Scope: (1) new extras group for `policyengine-us` (NEVER base deps; import-guarded);
  (2) a mapping file (committed, schema'd) from our parameter node ids to PolicyEngine
  parameter paths - standard deductions, bracket rates/thresholds, QDCGT breakpoints;
  where PE has no clean counterpart, record `unmapped` honestly, never force a match;
  (3) `tax-graph verify parameter-diff --year 2025`: compare our `constant_value`s
  against PE's 2025-period values, whole-dollar exact for dollar amounts, exact for
  rates; output agree/disagree/unmapped per node with PE provenance (package version +
  parameter path); (4) offline tests use CANNED PE parameter fixtures (live run gated
  on the extra being installed); (5) a seeded wrong value in a fixture must be flagged
  (this channel is the mechanical witness that would have caught the HoH error).
  NOT in scope: scenario/liability diffing, engine changes, box map, any Step 1/3/4
  work. Full pytest green before stopping; report the live diff result (if run) in
  the handoff; update the BALL line to CODEX when done.
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
- M11 Step 1 closeout (worker, 2026-07-09):
  - `.\.venv\Scripts\python.exe -m pytest tests/test_form_1040_spine_m11.py -q` -> 4 passed
  - `.\.venv\Scripts\python.exe -m pytest tests/test_capital_gains_slice.py tests/test_compile_m1.py tests/test_form_1040_spine_m11.py -q` -> 12 passed
  - `.\.venv\Scripts\python.exe -m pytest -m m11 -q` -> 10 passed, 242 deselected
  - `.\.venv\Scripts\python.exe -m pytest -q` -> 248 passed, 4 skipped
  - `.\.venv\Scripts\python.exe tools/check_ascii.py` -> ASCII check OK
  - `.\.venv\Scripts\python.exe -m tax_graph.cli validate 2025 --root C:\Users\devbox\projects\tax_graph` -> graph integrity OK
  - `.\.venv\Scripts\python.exe -m tax_graph.cli run --facts examples\taxable_income_basic\facts.yaml --year 2025 --root C:\Users\devbox\projects\tax_graph --no-record` -> line 15 path computed; line 7 preserved at 2000
- M11 Step 3 closeout (worker, 2026-07-09):
  - `.\.venv\Scripts\pytest.exe tests\test_form_1040_spine_m11.py tests\test_tax_liability_m11.py tests\test_tax_table_m11.py -q` -> 12 passed
  - `.\.venv\Scripts\pytest.exe -m m11 -q` -> 14 passed, 242 deselected
  - `.\.venv\Scripts\pytest.exe -q` -> 252 passed, 4 skipped
  - `.\.venv\Scripts\tax-graph.exe validate 2025 --root C:\Users\devbox\projects\tax_graph` -> graph integrity OK
  - `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK
- M11 Step 4 mid-closeout (worker, 2026-07-09):
  - `.\.venv\Scripts\pytest.exe tests\test_tax_table_m11.py tests\test_tax_liability_m11.py tests\test_oracles_scenario_boxmap_m6.py tests\test_oracles_diff_m6.py tests\test_oracles_domain_m6.py -q` -> 28 passed, 1 skipped
  - `.\.venv\Scripts\pytest.exe -m m11 -q` -> 22 passed, 238 deselected
  - `.\.venv\Scripts\pytest.exe -q` -> 256 passed, 4 skipped
  - `C:\Users\devbox\AppData\Local\Programs\Python\Python313\python.exe tools\check_ascii.py` -> ASCII check OK
  - `.\.venv\Scripts\tax-graph.exe oracle fuzz --year 2025 --n 100 --seed 20260709 --root C:\Users\devbox\projects\tax_graph` -> FAILED before diffing: OTS rejected the rendered input order (`Found 'f8949_spreadsheet-A/D:' when expecting 'L1a'`)
  - Post-fix status: renderer insertion order fixed; re-run of oracle/corpus suites and live fuzz/freeze is still pending because the desktop approval reviewer hit the local-Python usage limit for this turn.
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
