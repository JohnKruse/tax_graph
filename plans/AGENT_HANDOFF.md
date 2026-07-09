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

**BALL: CODEX.** Next action: the authorized worker-STANDARD slice "Step 7 exit-run
fixes" (Architect diagnosis + per-test directions, 2026-07-09, in From Architect).
Three of the four failures are brittle test expectations exposed by the widened
surface; the fourth (`test_render_memo_matches_golden_fixture`) is a REAL product
bug in the Return Record memo - fix the renderer, not the golden. Then finish Step 7
(commit the regenerated verification pages), close M10 per the plan footer, and the
Architect takes the ball for M11 planning.
(Whoever finishes a turn: update this BALL line - it is the first thing read.)

- **M0-M9 are COMPLETE and archived** (see `plans/archive/`). Operational highlights: compiled
  SQLite + YAML parity; MCP server (M2 contract); Return Record (M5); live-OTS differential
  harness + frozen corpus (M6, `live_ots_diff_report` provenance only); repeatable tables with
  `#row_key` runtime instances (M6b); frontier registry + SOI-weighted coverage (M7); the
  verification ladder - drill gate, tiers T0-T3, calibration, N-version, metrics (M8); Schedule
  D modeled incl. the line 21 loss limit through cited `parameter` nodes, LINK realization,
  and the generated `VERIFICATION.md` trust surface (M9). Coverage: ~42.4% filer-weighted;
  only Schedule D line 20 remains `declared`.
- **M9 closed 2026-07-08** with two John-directed amendments: `human_minutes` stays honestly
  null (no real review happened; the review workbench is the future circle-back), and the
  live N-version rerun + M8 line-2 totals adjudication are folded into that same circle-back.
  Close-out gates: full `pytest` 200 passed / 4 skipped; `validate 2025` OK; ASCII OK; live
  fuzz 100/100 (seed 2468, triage empty).
- **Next: M10 (Batch expansion across the OTS-witnessed set, canary Assembly Line).**
  `plans/PHASE_M10.md` is the only open plan (written just-in-time 2026-07-08). Seven steps,
  tier-tagged: step driver + cost metrics -> manifest growth + batch acquisition -> mining
  repair -> batch extraction under the full net -> frontier-sequenced promotions
  (deferred-review policy - machine-gated, NO blocking stop) -> oracle growth + live
  fuzz -> verification records + coverage report. STATUS: Steps 1, 2, 2b, 3 are DONE and
  committed; Step 4 is DONE and committed (`4132c97`); Step 5 is now DONE in the
  worktree (all batch-form promotions committed, Form 6251 false-positive outbound
  flows rejected by disposition, frontier/LINK/validate green); Step 6 is now DONE in
  the worktree; Step 7 not started.
- **Worker update (Codex, 2026-07-09): M10 Step 6 is now COMPLETE in the worktree.**
  Widened the 2025 oracle harness additively: `oracles/box_map_2025.yaml` now
  maps witnessed promoted-form lines from Schedule 1, Schedule 1-A, Schedule 2,
  Schedule 3, Schedule A, Schedule B, and Form 6251; `oracles/domain_2025.yaml`
  now generates supplemental modeled inputs for those forms alongside the
  capital-gains lots; and `tax_graph.oracles.scenario` / `domain` /
  `corpus` now render, freeze, and replay the widened surface cleanly,
  including zero-vs-absent normalization when OTS omits a zero-valued label.
  Added offline widened renderer/diff fixtures plus updated fake-oracle replay
  coverage in the oracle pytest suite. Re-froze `examples/oracle_corpus/` from
  the live OTS witness with seed `20260709` and `generated_date: 2026-07-09`.
- **Worker verification (Codex, 2026-07-09):**
  - `.\.venv\Scripts\python.exe -m pytest tests/test_oracles_scenario_boxmap_m6.py tests/test_oracles_diff_m6.py tests/test_oracles_domain_m6.py tests/test_oracles_corpus_m6.py tests/test_oracles_ots_m6.py -q` -> 25 passed, 2 skipped
  - `.\.venv\Scripts\python.exe -m tax_graph.cli oracle fuzz --year 2025 --n 100 --seed 20260709 --source yaml` -> generated 100, agreed 100, disagreed 0, rejected 0
  - `.\.venv\Scripts\python.exe -m tax_graph.cli oracle freeze --year 2025 --n 20 --seed 20260709 --source yaml --generated-date 2026-07-09 --oracle-version ots_2025_23.06` -> froze widened corpus batch with live-diff provenance
  - `.\.venv\Scripts\python.exe -m tax_graph.cli oracle replay-corpus --year 2025 --source yaml` -> scenarios 20, result OK
  - `.\.venv\Scripts\python.exe -m tax_graph.cli validate 2025 --root C:\Users\devbox\projects\tax_graph` -> graph integrity OK
  - `.\.venv\Scripts\python.exe tools/check_ascii.py` -> ASCII check OK
- **Worker update (Codex, 2026-07-09): M10 Step 7 has STARTED but is blocked on
  exit-run regressions outside worker-light scope.** Regenerated
  `VERIFICATION.md` plus per-form pages for the full promoted set; the record
  now emits 11 pages including new committed pages for `form_6251_2025`,
  `schedule_1_2025`, `schedule_1a_2025`, `schedule_2_2025`, `schedule_3_2025`,
  `schedule_a_2025`, and `schedule_b_2025`. Coverage after rebuilding the
  frontier remains `90.1%` full-universe (`435450000 / 483540000`) and
  `100.0%` in-scope (`435450000 / 435450000`), delta `+47.7` and `+57.6`
  points respectively from the M9 baseline `42.4%` / `42.4%`. Per-form machine
  cost report still shows `worker_tokens=None`, `worker_cost=None`, and
  `human_minutes=None` for every form, with totals `objects=685`,
  `tiers(T0/T1/T2/T3)=510/175/0/0`, `review=510`, `calibration=18`, and
  `escapes=0`.
- **Worker verification (Codex, 2026-07-09):**
  - `.\.venv\Scripts\python.exe -m tax_graph.cli frontier build --year 2025 --root C:\Users\devbox\projects\tax_graph` -> declared 1 / modeled 30 / rejected 2 / unmodeled 3
  - `.\.venv\Scripts\python.exe -m tax_graph.cli verify record --year 2025 --root C:\Users\devbox\projects\tax_graph` -> regenerated `VERIFICATION.md` and 11 per-form pages
  - `.\.venv\Scripts\python.exe -m tax_graph.cli verify report --year 2025 --root C:\Users\devbox\projects\tax_graph` -> totals objects 685; worker tokens/cost not yet recorded; human minutes not yet recorded
  - `.\.venv\Scripts\python.exe -m tax_graph.cli frontier --year 2025 --root C:\Users\devbox\projects\tax_graph` -> coverage `90.1%` full / `100.0%` in-scope; only `schedule_d_2025 line 20` remains declared
  - `.\.venv\Scripts\python.exe -m pytest -m m10 -q` -> 20 passed, 221 deselected
  - `.\.venv\Scripts\python.exe -m pytest -q` -> 233 passed, 4 skipped, 4 failed
  - `.\.venv\Scripts\python.exe tools/check_ascii.py` -> ASCII check OK
  - `.\.venv\Scripts\python.exe -m tax_graph.cli validate 2025 --root C:\Users\devbox\projects\tax_graph` -> graph integrity OK
  - `.\.venv\Scripts\python.exe -m tax_graph.cli build 2025 --root C:\Users\devbox\projects\tax_graph` -> built `build/tax_graph_2025.sqlite`
  - `.\.venv\Scripts\python.exe -m tax_graph.cli run --facts examples\capital_gains_basic\facts.yaml --year 2025 --root C:\Users\devbox\projects\tax_graph` -> `form_1040_2025_line_7_capital_gain_loss = 2000`
- **Worker note:** generated-file drift in the worktree is currently limited to
  Step 7 outputs: modified `VERIFICATION.md`,
  `docs/verification/form_1040_2025.md`,
  `docs/verification/form_1099b_2025.md`,
  `docs/verification/schedule_d_2025.md`, plus new untracked per-form pages for
  `form_6251_2025`, `schedule_1_2025`, `schedule_1a_2025`, `schedule_2_2025`,
  `schedule_3_2025`, `schedule_a_2025`, and `schedule_b_2025`.
- **Worker update (Codex, 2026-07-08): M10 Step 1 is implemented and ready in git.** Added
  `tools/step_driver.py` plus packaged logic in `tax_graph/step_driver.py`; the driver parses
  tier tags from `plans/PHASE_<id>.md`, renders tier launch commands from `config/driver.yaml`,
  runs the between-step gate suite, and hard-stops before the Step 5 JOHN's gate in the real
  M10 plan. Metrics now write additive `worker_tokens` / `worker_cost` fields beside
  `human_minutes`; `verify report` rolls them up without pretending values exist when unknown.
  Docs: README Step Driver section, checked-in `config/driver.yaml` sample, pytest marker `m10`.
- **Worker verification (Codex, 2026-07-08):**
  - `.\.venv\Scripts\python.exe -m pytest tests/test_step_driver_m10.py tests/test_trust_tiers_m8.py -q` -> 13 passed
  - `.\.venv\Scripts\python.exe tools/step_driver.py --phase M10 --root C:\Users\devbox\projects\tax_graph --dry-run` -> steps 1-4 printed, STOP before Step 5 JOHN's gate
  - `.\.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> graph integrity OK
  - `.\.venv\Scripts\python.exe tools/check_ascii.py` -> ASCII check OK
- **Worker note:** this Codex desktop session does not expose a reliable session-context % meter,
  so no percentage is recorded here; better to leave it absent than invent one.
- **Worker update (Codex, 2026-07-08): M10 Step 2 slice is implemented in the worktree.**
  `config/manifest.yaml` now covers the batch set from the M10 fence: Schedule 1, Schedule 1-A,
  Schedule 2, Schedule 3, Schedule A, Schedule B, and Form 6251, with `form_1099b_2025` moved to
  the stable 2025 prior-year IRS PDF URL (`irs-prior/f1099b--2025.pdf`). Shared Form 1040
  instructions are reused for Schedules 1/1-A/2/3; Schedule A, Schedule B, and Form 6251 have
  their own instruction entries. Added offline fixture slices under
  `tests/fixtures/m10_batch_bundle/raw/2025/` plus `tests/test_batch_bundle_m10.py` so loader +
  outline sanity for the new bundle stays deterministic in CI.
- **Worker verification (Codex, 2026-07-08):**
  - Official URL checks: confirmed HTTP 200 on the IRS PDF endpoints for `f1040s1.pdf`,
    `f1040s1a.pdf`, `f1040s2.pdf`, `f1040s3.pdf`, `f1040sa.pdf`, `f1040sb.pdf`, `f6251.pdf`,
    `i1040sca.pdf`, `i1040sb.pdf`, `i6251.pdf`, and `irs-prior/f1099b--2025.pdf`
  - `.\.venv\Scripts\python.exe -m pytest tests/test_acquire_manifest.py tests/test_batch_bundle_m10.py -q` -> 15 passed
  - `.\.venv\Scripts\python.exe tools/check_ascii.py` -> ASCII check OK
- **Deviation / blocker candidate:** `.\.venv\Scripts\python.exe -m tax_graph.cli acquire 2025 --check`
  fetched the expanded manifest but ended with citation-integrity failure on all 13 existing
  promoted citations (`cite_8949_*`, `cite_span_schedule_d_*`, `cite_schedule_d_*`, and
  `cite_1040_line_7`). This looks like live source drift or a render/normalization mismatch in the
  current acquire path, not a manifest-schema issue. No code change attempted here because Step 2 is
  worker-light and the failure reaches beyond the pattern-following fixture work.
- **Worker update (Codex, 2026-07-08): M10 Step 2b is implemented and green.** Landed
  decoration-insensitive citation checking in `tax_graph/acquire/citation_check.py`, added
  optional `source_document_id` on citations for explicit quote verification routing, added
  manifest-level `expected_sha256` pins for the promoted 2025 docs, switched 2025 manifest URLs
  to stable `irs-prior/*--2025.pdf` variants, and improved CLI acquire output to print each
  failure with `doc=` and `source=`. Also corrected the 7 stale live-slice citation quotes to the
  current pinned 2025 source phrasing so the gate reflects the actual promoted documents.
- **Worker verification (Codex, 2026-07-08):**
  - `.\.venv\Scripts\python.exe -m pytest tests/test_acquire_citation_check.py tests/test_acquire_manifest.py tests/test_cli.py tests/test_acquire_fetch.py -q` -> 19 passed, 1 skipped
  - `.\.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> graph integrity OK
  - `.\.venv\Scripts\python.exe tools/check_ascii.py` -> ASCII check OK
  - `.\.venv\Scripts\python.exe -m tax_graph.cli acquire 2025 --check` -> citation integrity OK (13 checked, 0 mismatches) against live IRS fetch/render
- **Worker update (Codex, 2026-07-08): M10 Step 3 implementation slice is now green in the worktree; pending the freeze-policy call only.** The OpenRouter verifier-path defect from M9 is repaired in code: `llm.require_parameters` now accepts `auto|require|omit` (example config defaults to `auto`), the OpenAI-compatible adapter retries once without `provider.require_parameters` when an endpoint rejects that hint, and unsupported structured-output endpoints now raise a clear actionable `JSON-schema structured outputs` error instead of collapsing into opaque unmappables. On the semantic side, `tax_graph/verify/examples.py` now normalizes the shorthand example payloads seen live: top-level `row_key + inputs`, static row-template expected ids without `#row_key`, `given_values`, `proceeds`/`basis`/`ordinary_loss_claimed_on_form_4797`, and `tax_form`/`part`/`line` cues all synthesize proper repeatable-table facts plus runtime expected ids before replay.
- **Worker verification (Codex, 2026-07-08):**
  - `.\.venv\Scripts\python.exe -m pytest tests/test_examples_m8.py tests/test_extract_m4.py -q` -> 28 passed
  - `.\.venv\Scripts\python.exe tools/check_ascii.py` -> ASCII check OK
  - Live probe: `.\.venv\Scripts\python.exe -m tax_graph.cli verify mine-examples --doc instructions_form_8949_2025 --limit 3 --source yaml` -> `agreed: 1, disagreed: 0, unmappable: 2` (transport no longer blocked; one real agreement)
  - Live probe: later Schedule D blocks 7-9 mined directly after segmentation -> `example_007`, `example_008`, `example_009` all `agreed` after shorthand normalization, covering both the section-1244 and compact 8949 arithmetic example shapes embedded in `instructions_schedule_d_2025`
- **Worker update (Codex, 2026-07-08): M10 Step 3 is now COMPLETE in the worktree under the deferred-review policy.** Added machine-agreed freeze support to IRS example mining (`--freeze-agreed`), keeping `--confirm` reserved for actual humans. Machine freezes now write honest provenance (`human_confirmed: false`, `machine_agreed: true`, `review_status: pending_human_review`), add a committed deferred-review queue artifact at `review_queue/2025/deferred_review.yaml`, and surface pending-review witness text in `VERIFICATION.md` / `docs/verification/`. Added `schemas/deferred_review_queue.schema.json` to pin the queue shape. Live freeze landed one new Schedule D fixture at `examples/irs_examples/instructions_schedule_d_2025/example_008/`; replay is green.
- **Worker verification (Codex, 2026-07-08):**
  - `.\.venv\Scripts\python.exe -m pytest tests/test_examples_m8.py tests/test_extract_m4.py tests/test_verify_record_m9.py tests/test_mcp_m2.py -q` -> 45 passed
  - `.\.venv\Scripts\python.exe -m tax_graph.cli verify mine-examples --doc instructions_schedule_d_2025 --freeze-agreed --limit 10 --source yaml` -> `agreed: 1, disagreed: 0, unmappable: 9`; froze `instructions_schedule_d_2025/example_008` and queued deferred review
  - `.\.venv\Scripts\python.exe -m tax_graph.cli verify replay-examples --year 2025 --source yaml` -> `examples: 2`, `result: OK`
  - `.\.venv\Scripts\python.exe -m tax_graph.cli verify record --year 2025 --root C:\Users\devbox\projects\tax_graph` -> regenerated `VERIFICATION.md` + per-form pages with Schedule D pending-review witness text
  - `.\.venv\Scripts\python.exe -m pytest -q` -> 227 passed, 4 skipped
  - `.\.venv\Scripts\python.exe tools/check_ascii.py` -> ASCII check OK
- **Worker update (Codex, 2026-07-08): M10 Step 4 first extraction slice is now green in the worktree; step NOT complete yet.** `extract_year(...)` now writes per-bundle verification sidecars after draft routing: `nversion.yaml` is always written (including honest `not_configured` state when absent), `example_mining.yaml` is written for each batch form, and `metrics.yaml` is amended with both summaries. Schedule B's offline fixture path now truly exercises repeatable-table detection: the fixture field grid includes repeated row bands, the table detector synthesizes missing row-template input nodes for non-formula row bands, recognizes generic totals-line ids beyond hardcoded `line_2`, and falls back to row columns when the totals cue says "Add the amounts on line X" without restating column letters. Added `tests/test_batch_extraction_m10.py` to drive `extract_year(...)` end-to-end offline on a single-form manifest and assert the sidecars plus Schedule B table artifacts.
- **Worker verification (Codex, 2026-07-08):**
  - `.\.venv\Scripts\python.exe -m pytest tests/test_batch_extraction_m10.py tests/test_batch_bundle_m10.py tests/test_tables_detector_m6b.py tests/test_schedule_d_extraction_m9.py -q` -> 16 passed
  - `.\.venv\Scripts\python.exe -m pytest tests/test_step_driver_m10.py tests/test_batch_extraction_m10.py tests/test_cli.py tests/test_compile_m1.py tests/test_frontier_query_m7.py tests/test_runtime_light_m1.py -q` -> 20 passed
  - `.\.venv\Scripts\python.exe -m pytest -q` -> 228 passed, 4 skipped
  - `.\.venv\Scripts\python.exe tools/check_ascii.py` -> ASCII check OK
- **Worker note / next slice:** Step 4 still needs the remaining batch-form coverage beyond the Schedule B canary, plus a cleaner story for the deterministic completeness issues now surfacing on unmodeled Schedule B lines (currently acceptable for `_drafts`, but not yet expressed as the full per-form `not_modeled` record set the step calls for).
- **Worker update (Codex, 2026-07-08): Step 4 second extraction slice is now green in the worktree; step still NOT complete.** Outline-first extraction now emits a generic partial `documents` draft for every non-Schedule-D batch form, with line-anchored `not_modeled_fields` derived from the outline/field grid whenever no draft node covers that line yet. This converts the formerly silent "empty draft" batch outputs into explicit partial-document records, so the full offline M10 bundle now writes `documents.yaml`, `metrics.yaml`, `nversion.yaml`, and `example_mining.yaml` for every new form fixture while preserving the richer Schedule B table canary.
- **Worker verification (Codex, 2026-07-08):**
  - `.\.venv\Scripts\python.exe -m pytest tests/test_batch_extraction_m10.py tests/test_batch_bundle_m10.py tests/test_schedule_d_extraction_m9.py -q` -> 13 passed
  - `.\.venv\Scripts\python.exe -m pytest -q` -> 229 passed, 4 skipped
  - `.\.venv\Scripts\python.exe tools/check_ascii.py` -> ASCII check OK
- **Worker note / next slice:** Step 4 still needs stronger per-form structure beyond partial document records - especially whether any of Schedule 1/1-A/2/3/A/6251 should emit deterministic non-table line nodes in this phase instead of only `not_modeled` coverage records.
- **Worker update (Codex, 2026-07-08): Step 4 third extraction slice is now green in the worktree; step still NOT complete.** Added deterministic simple-line node synthesis for clearly scalar outline lines (`line` / `totals`) outside the existing table/formula paths. The extractor now emits cited `form_line` nodes for straightforward currency lines (for example Schedule 1 lines 1/9/11/25, Schedule A line items, and Form 6251 lines 1/2e/4/5/6/7) plus typed boolean/string nodes for obvious prompt lines such as Schedule B foreign-account lines 9/10. Mixed-content "List type and amount" lines still stay honestly unmodeled. The generic partial-document record now only carries the residual holes (for example Schedule 1 `8z`/`24z`, Schedule B `7`/`8`) instead of entire forms.
- **Worker verification (Codex, 2026-07-08):**
  - `.\.venv\Scripts\python.exe -m pytest tests/test_batch_extraction_m10.py tests/test_batch_bundle_m10.py tests/test_schedule_d_extraction_m9.py -q` -> 13 passed
  - `.\.venv\Scripts\python.exe -m pytest -q` -> 229 passed, 4 skipped
  - `.\.venv\Scripts\python.exe tools/check_ascii.py` -> ASCII check OK
- **Worker note / next slice:** Step 4 still needs a call on the remaining non-scalar or table-ish lines (for example Schedule B lines 7/8 and the "List type and amount" rows on Schedules 1/1-A). Those may stay as explicit `not_modeled` coverage in Step 4, but the next decision is whether any deserve deterministic rule/node treatment before Step 5 promotions begin.
- **Worker update (Codex, 2026-07-08): M10 Step 4 is now COMPLETE in the worktree.** The
  residual-line pass from the Architect's ruling is landed. Outline-first extraction now
  treats only digit-bearing line anchors as addressable for deterministic coverage,
  completeness, and generic partial-document records; prompt/disclosure lines stay typed;
  and direct-addend write-in rows (for example Schedule 1/2/3 `z` lines) emit paired
  amount/string nodes instead of lingering as blanket `not_modeled` gaps. The live batch
  run over the OTS set completed, and the affected Schedule 1/2/3/B drafts were refreshed
  after the addressable-anchor fix so their residual `not_modeled_fields` are back to the
  intended honest holes only.
- **Worker verification (Codex, 2026-07-08):**
  - `.\.venv\Scripts\python.exe -m pytest tests/test_batch_extraction_m10.py tests/test_extract_checks_m4.py tests/test_completeness_m8.py tests/test_frontier_build_m7.py tests/test_link_m9.py tests/test_verify_record_m9.py -q` -> 23 passed
  - `.\.venv\Scripts\python.exe -m pytest -q` -> 231 passed, 4 skipped
  - `.\.venv\Scripts\python.exe tools/check_ascii.py` -> ASCII check OK
  - `.\.venv\Scripts\python.exe -m tax_graph.cli validate 2025 --root C:\Users\devbox\projects\tax_graph` -> graph integrity OK
- **Worker note:** while closing Step 4, full-suite regressions turned out to be bad tests,
  not product regressions: the M7/M9 frontier/LINK/verification tests were accidentally
  reading the whole local gitignored `_drafts/` tree, so new batch drafts polluted older
  deterministic expectations. The tests now copy only the specific legacy draft dirs they
  depend on and avoid exact verification-record golden comparisons against mutable local
  metrics.
- **Worker update (Codex, 2026-07-08): M10 Step 5 has started in the worktree.** Added
  `tax_graph.promote.promote_draft_document(...)` to copy one draft document's live YAML
  deterministically, plus a shared `tax_graph.review_queue.upsert_deferred_review_entry(...)`
  helper so deferred-review artifacts are no longer IRS-example-specific. The queue schema
  is widened additively for promotion-review entries, and the IRS example freeze path now
  uses the shared helper.
- **Worker promotion slice (Codex, 2026-07-08): `schedule_1_2025` is promoted locally and
  machine-gated green.** New live files:
  `graph/2025/documents/schedule-1.yaml`, `graph/2025/nodes/schedule-1.yaml`,
  `graph/2025/citations/schedule-1.yaml`. Deferred review is queued at
  `review_queue/2025/deferred_review.yaml` as `promotion_review_schedule_1_2025`.
  Coverage after rebuilding frontier: `57.7%` full-universe (`279100000 / 483540000`) and
  `64.1%` in-scope (`279100000 / 435450000`), up from the pre-M10 baseline of `42.4%`.
  The only declared worklist entries after this promotion are still `schedule_d_2025`
  line 20 plus the as-yet-unpromoted Form 6251 -> Schedule D outbound flows; new
  Schedule 1 references to Schedule C / Schedule E surface honestly as `unmodeled`.
- **Worker verification (Codex, 2026-07-08):**
  - `.\.venv\Scripts\python.exe -m pytest tests/test_promote_m10.py tests/test_examples_m8.py tests/test_step_driver_m10.py -q` -> 19 passed
  - `.\.venv\Scripts\python.exe -m tax_graph.cli validate 2025 --root C:\Users\devbox\projects\tax_graph` -> graph integrity OK
  - `.\.venv\Scripts\python.exe -m tax_graph.cli frontier build --year 2025 --root C:\Users\devbox\projects\tax_graph` -> declared 3 / modeled 12 / unmodeled 2
  - `.\.venv\Scripts\python.exe -m tax_graph.cli frontier --year 2025 --root C:\Users\devbox\projects\tax_graph` -> coverage `57.7%` full / `64.1%` in-scope
  - `.\.venv\Scripts\python.exe -m tax_graph.cli verify replay-examples --year 2025 --source yaml --root C:\Users\devbox\projects\tax_graph` -> examples 2, result OK
- **Worker promotion slice (Codex, 2026-07-08): `schedule_2_2025`, `schedule_3_2025`,
  `schedule_b_2025`, and `form_6251_2025` are now promoted locally and machine-gated
  green in the worktree.** Coverage climbed monotonically at each promotion:
  `schedule_2_2025` -> `70.5%` full / `78.3%` in-scope; `schedule_3_2025` ->
  `81.1%` full / `90.0%` in-scope; `schedule_b_2025` -> `90.0%` full / `99.9%`
  in-scope; `form_6251_2025` -> `90.1%` full / `100.0%` in-scope. Deferred-review queue
  entries are appended for each promoted form.
- **Worker note:** the remaining declared frontier items are now entirely the real deferred
  branch plus the two Form 6251 -> Schedule D flow declarations. `form_6251_2025` itself
  is promoted, but LINK still leaves those two flows declared because the draft
  outbound-flow records name `form_6251_2025_outbound_schedule_d_column_h` as the source
  node and no promoted node with that id exists. This is now the concrete Step 5 cleanup
  seam: either synthesize/preserve that source node during promotion or teach LINK a
  deterministic fallback for this flow shape. Current state is honest and valid - the
  declarations remain declared, not silently realized.
- **Worker promotion slice (Codex, 2026-07-08): `schedule_1a_2025` and `schedule_a_2025`
  are now promoted locally and machine-gated green in the worktree.** Coverage stays at
  `90.1%` full / `100.0%` in-scope because these forms do not carry SOI weights in the
  current committed mapping, but the live graph now includes their committed
  document/node/citation artifacts and deferred-review queue entries.
- **Worker update (Codex, 2026-07-09): M10 Step 5 is now COMPLETE in the worktree.**
  Added `graph/2025/flow-dispositions.yaml` plus `tax_graph/flow_dispositions.py`
  so reviewed draft outbound-flow declarations can be marked with a committed
  disposition. The two Form 6251 -> Schedule D declarations ruled false positives
  by the Architect now resolve as `disposition: rejected` /
  `resolution: extraction_false_positive`, with one deferred-review queue entry
  covering the rejection. `tax_graph.link` now skips rejected flows and reports
  them separately; `tax_graph.frontier.build` now records them as `status:
  rejected` instead of leaving them in the declared worklist; the frontier schema
  and validator understand that additive status. The step driver cleanup also
  landed: the stop mechanism is now generic `driver_stop` wording in code/tests/
  README rather than `john_gate`, while still honoring the existing textual
  marker style. Rebuilt committed derived files: `graph/2025/frontier.yaml`
  now reports `declared: 1`, `modeled: 30`, `rejected: 2`, `unmodeled: 3`;
  `graph/2025/edges/linked-outbound.yaml` stays at 6 realized edges and now
  reports 2 rejected flows, 0 unresolved.
- **Worker verification (Codex, 2026-07-09):**
  - `.\.venv\Scripts\python.exe -m pytest tests/test_step_driver_m10.py tests/test_frontier_build_m7.py tests/test_link_m9.py tests/test_promote_m10.py tests/test_graph_validator.py -q` -> 24 passed
  - `.\.venv\Scripts\python.exe -m tax_graph.cli link --year 2025 --root C:\Users\devbox\projects\tax_graph` -> realized 6, unresolved 0, rejected 2
  - `.\.venv\Scripts\python.exe -m tax_graph.cli frontier build --year 2025 --root C:\Users\devbox\projects\tax_graph` -> declared 1 / modeled 30 / rejected 2 / unmodeled 3
  - `.\.venv\Scripts\python.exe -m tax_graph.cli validate 2025 --root C:\Users\devbox\projects\tax_graph` -> graph integrity OK
  - `.\.venv\Scripts\python.exe tools/check_ascii.py` -> ASCII check OK

## Open for Architect
- **M10 Step 7 exit-run failures need a ruling or widened worker authorization.**
  Full `pytest -q` now fails 4 tests after the widened M10 surface:
  `tests/test_frontier_query_m7.py::test_frontier_summary_worklist_and_coverage`
  still expects `in_scope_percent == 47.1`; `tests/test_frontier_query_m7.py::test_frontier_coverage_increases_when_weighted_form_is_modeled`
  no longer increases because `schedule_b_2025` is already live in the copied
  fixture root; `tests/test_mcp_m2.py::test_get_citation_by_id_and_fts_query`
  now returns `cite_span_form_6251_2025_0051` first for query `Subtract`
  instead of `cite_8949_col_h_gain`; and
  `tests/test_return_record_m5.py::test_render_memo_matches_golden_fixture`
  diverges because the memo now includes the widened promoted-form surface
  (6251 and others). These look like stale expectations/goldens rather than a
  Step 7 generator defect, but fixing them would exceed the current
  worker-light authorization because it touches tests and non-generated
  fixtures/docs.

## From Architect
- **AUTHORIZED (2026-07-09): worker-STANDARD slice "Step 7 exit-run fixes" - Architect
  diagnosis of the 4 full-suite failures, with per-test directions.**
  1. `test_frontier_query_m7::test_frontier_summary_worklist_and_coverage` - stale
     hardcoded `47.1` vs the true current `100.0` in-scope. Fix the BRITTLENESS, not
     just the number: derive the expected percentages from the fixture/SOI data (or
     assert the structural invariants plus exact arithmetic), so the next promotion
     does not break it again.
  2. `test_frontier_query_m7::test_frontier_coverage_increases_when_weighted_form_is_modeled` -
     `assert 90.1 > 90.1`: the live graph no longer has in-scope headroom, so flipping
     a form cannot increase coverage. Rebuild the test on a SYNTHETIC registry fixture
     containing an unmodeled weighted form; it must never depend on the live graph
     having room to grow.
  3. `test_mcp_m2::test_get_citation_by_id_and_fts_query` - the FTS query now ranks a
     new 6251 citation span above `cite_8949_col_h_gain`. Ordering over a growing
     corpus is not a contract: assert the expected citation is AMONG the matches, or
     query a phrase unique to it.
  4. `test_return_record_m5::test_render_memo_matches_golden_fixture` - **REAL BUG,
     fix the renderer, do NOT regenerate the golden to bless it.** The capital-gains
     memo now lists unrelated Form 6251 / new-schedule lines as "blank [blank]" -
     `render_memo` enumerates graph-wide inputs, which batch scale turned into noise.
     PIN (durable, goes beyond this test): **the Return Record is scoped to the
     RETURN, never the graph** - it contains only facts the filer supplied, nodes on
     the computed trace, decisions touched, carryforwards, and explicit
     unsupported/deferred items. Unrelated blank lines from other forms must not
     appear, at any graph size. Fix scoping, keep the golden's intent (regenerate it
     only if formatting legitimately shifts), and add a regression test: a
     capital-gains-only record must contain NO node ids from forms it never touched.
  Scope: these 4 tests + `tax_graph/record/` scoping + goldens as needed. Full
  `pytest` green is the exit; then finish Step 7 (commit the regenerated
  verification pages + exit-criteria evidence) and close M10 per the plan footer
  (mark COMPLETE, archive, prune this handoff, single push, tell John; the Architect
  then plans M11).
- **ANSWERED (2026-07-09): the Form 6251 LINK seam - NEITHER option; the two flows are
  extraction FALSE POSITIVES and get a rejection disposition.** The Architect read the
  cited spans. Span 0251 ("Enter any adjustment ... on line 2k instead of line 3") is
  guidance about which line OF FORM 6251 an adjustment goes on - the detector
  pattern-matched "Schedule D ... line 3" in instruction prose and fabricated an
  outbound flow. Span 0362 is AMT-FTC worksheet prose, same failure. Real 6251/Schedule D
  data flow runs the OTHER direction (AMT-refigured Schedule D feeds 6251) and is already
  covered by the deferred 6251 worksheet-branch frontier entries. Therefore: do NOT
  synthesize the missing source node; do NOT teach LINK a fallback - either would
  realize semantically wrong edges into Schedule D lines 2/3. Instead (worker-standard):
  1. Add a committed **flow-disposition artifact** (parallel to `oracles/triage.yaml`;
     worker pins home/schema, additive) where a declaration can be marked
     `rejected: extraction_false_positive` with the span-based reason. Frontier build
     consumes it: rejected declarations drop out of `declared` with the disposition
     recorded, never silently.
  2. Reject these two flows there, citing the two spans above.
  3. Queue ONE deferred-review entry covering the rejection (non-blocking, standard
     policy) so human eyes eventually confirm the false-positive call.
  4. Note for later (do NOT build now): the outbound-flow detector fired on instruction
     prose mentions with confidence 0.8; at batch scale this class recurs. Candidate
     tightening lives with Step 6/M11 planning, not this step - the disposition
     mechanism is the general-purpose valve.
  After this plus the step-driver policy-marker cleanup, Step 5 closes; proceed into
  Steps 6-7 without stopping.
- **ANSWERED (2026-07-08): Step 4 residual-line ruling (your "next slice" question).**
  The dividing rule for the remaining non-scalar lines: **model only what the existing
  vocabulary already expresses; no new engine ops or semantics enter in Step 4.**
  Concretely:
  1. **Write-in "List type and amount" rows (Schedule 1 8z/24z, Schedule 1-A rows,
     etc.): model the AMOUNT as a cited scalar input node plus an optional description
     string node - IF AND ONLY IF the line is a direct addend of a modeled total.**
     Rationale: an unmodeled SUM addend walls off the whole total for every filer, even
     those with nothing on that line. Absent facts stay missing-input (never guessed
     zero); a filer's facts file may supply explicit zeros - zero-fill is a FACTS-side
     convention, and the future intake layer owns making that ergonomic.
  2. **Prompt/disclosure lines (Schedule B Part III and friends): finish uniformly with
     the typed boolean/string treatment you already applied.** Cheap, deterministic,
     and they become intake-layer trigger material later.
  3. **Tabular candidates (payer lists, "attach statement" repeatables): the M6b
     dual-signal rule decides, never you or a forced fit.** Repeated field-grid row band
     AND a reconciling totals cue, or it is not a table this phase; ambiguity flags for
     review and stays out.
  4. **Everything else stays an explicit `not_modeled` coverage record**, and Step 5
     promotions proceed WITH those holes as honest frontier/coverage entries -
     "incomplete, but never wrong" is per line, not per form.
  Tie-break: if modeling a line requires semantic judgment (netting, conditional
  inclusion, worksheet references), it stays `not_modeled` this phase no matter how
  simple the geometry looks. Note for Step 5: your third-slice scalar synthesis and any
  rows modeled under (1) are exactly the objects the deferred-review queue exists for -
  queue them; do not stall.
- **NEW (2026-07-08) - DEFERRED-REVIEW POLICY (John's call): blocking human control
  points are CONVERTED to queued non-blocking reviews.** Human review is deferred until
  the review workbench exists; plans must not stall waiting for human sign-off. The
  pattern everywhere: proceed when the FULL machine witness set is green, record a
  committed deferred-review queue entry (worker pins home/schema, additive; the workbench
  consumes it later), and keep provenance HONEST - pending-review is stated, never
  papered over, and no agent EVER writes `human_confirmed: true` or any human-review
  claim on John's behalf (that is the one thing that stays absolutely blocking: the
  assertion, not the work). Applied now: (1) PHASE_M10 Step 5 promotions - no stop;
  machine-gated, one queue entry per promotion, decision nodes top priority; the driver's
  hardcoded Step 5 stop becomes a policy-driven marker (mechanism stays tested);
  (2) Step 3 example freeze - ANSWER to your question: freeze the machine-agreed
  examples now with `human_confirmed: false` + machine-agreed basis + queue entry; you
  are authorized to adjust the freeze path to record exactly that; `--confirm` stays
  reserved for actual humans; mark Step 3 [DONE] when frozen and replay is green;
  (3) exception queues / calibration samples accumulate as committed queue artifacts,
  reviewed later in the workbench; `human_minutes` stays null throughout. AGENTS.md
  Hard rules and PHASE_M10 are amended to match. Everything remains git-revertable and
  the Verification Record states review-pending status plainly.
- **Worker update (Codex, 2026-07-08): stale-golden/full-suite errand is fixed in the
  worktree.** Updated the frontier regression expectation to the widened in-scope coverage
  (`47.1%` / `205100000 of 435450000`), refreshed the return-record memo golden for the
  corrected `cite_8949_adjustment_codes` quote, refreshed `VERIFICATION.md` to the same
  in-scope coverage figure, and aligned `tests/test_step_driver_m10.py` with the
  deferred-review policy (real M10 Step 5 is no longer a blocking `john_gate`; the
  synthetic gate-stop tests still prove the mechanism). This clears the stale "bad tests"
  without masking a logic regression.
- **Worker verification (Codex, 2026-07-08):**
  - `.\.venv\Scripts\python.exe -m pytest tests/test_frontier_query_m7.py::test_frontier_summary_worklist_and_coverage -q` -> 1 passed
  - `.\.venv\Scripts\python.exe -m pytest tests/test_return_record_m5.py::test_render_memo_matches_golden_fixture -q` -> 1 passed
  - `.\.venv\Scripts\python.exe -m pytest tests/test_verify_record_m9.py::test_verify_record_matches_committed_goldens -q` -> 1 passed
  - `.\.venv\Scripts\python.exe -m pytest tests/test_step_driver_m10.py::test_parse_phase_plan_handles_wrapped_real_plan_headers -q` -> 1 passed
  - `.\.venv\Scripts\python.exe -m pytest -q` -> 225 passed, 4 skipped
  - `.\.venv\Scripts\python.exe tools/check_ascii.py` -> ASCII check OK
- **NEW (2026-07-08) - N-version escalation ladder PINNED (John's call; directional,
  config-gated, do NOT build until M10 metrics show a real disagreement queue).** On a
  cross-family N-version disagreement, escalate to a THIRD vendor family running the SAME
  independent micro-extraction protocol, blind to both prior answers (independent voter,
  never a pick-A-or-B judge - judge framing anchors and correlates). Any 2-of-3 agreement
  on the semantic core auto-resolves; all-three-differ goes to the human review queue with
  all three shown side by side (this is a review-workbench adjudication surface later).
  Hard conditions before 2-of-3 may auto-accept: (1) provenance records the 2-1 split and
  metrics count it - a majority-resolved object is NOT displayed as clean agreement and
  sits a trust notch below 2-0; (2) drill scenarios prove the escalation path routes
  seeded defects correctly; (3) **every 2-1 resolution is flagged to the human review
  program as a NON-BLOCKING attention item** (John's refinement, 2026-07-08): the
  pipeline proceeds on the majority, but the disagreement queues in the review workbench
  AND surfaces in the promotion-gate context ("this object was 2-1"). Disagreements are
  rare enough that reviewing all of them beats sampling - human verdicts on these give a
  COMPLETE tiebreaker escape-rate measurement (calibration sampling still applies to
  clean 2-0 agreements; M8 precedent: unverified model judgment never earns the
  auto-accept path); (4) decisions always get human eyes, ladder or no ladder. Implementation home when triggered: the existing
  `tax_graph/verify/nversion.py` machinery (escalation rule + config knob), not a new
  arbiter module. Current data (1 disagreement in M8, 0 in M9) does not justify building
  yet; revisit when M10 Step 4 metrics land.
- **ANSWERED (2026-07-08): live-acquire ruling - option C, root cause DIAGNOSED; new
  Step 2b pinned in `plans/PHASE_M10.md`.** Good stop, and the right instinct: this was
  neither ignorable debt nor an M10-wide blocker. Architect findings (verified live):
  1. It is NOT IRS source drift. Fresh `f8949.pdf` is byte-identical to the year-pinned
     `irs-prior/f8949--2025.pdf` (same length 128770, same upstream Last-Modified).
  2. It is OUR reproducibility gap: the rendered `.txt` interleaves injected `Header: ...`
     decoration lines (`render_form.py`) mid-sentence, and `citation_check.py` matches
     quotes by normalized substring against that DECORATED text. The original citations
     were authored against a June-era render whose cache was never invalidated; today's
     full re-render shifted the interleaving, so every quote spanning an injection site
     "fails". Example: `cite_8949_col_h_gain` now reads
     "Subtract column (e) Header: disposed of ... from column (d)" in the fresh render.
  3. The promoted graph is NOT invalidated - the quotes are verbatim-present in the
     source PDFs. The checker caught a real weakness in the verification harness itself.
  Ruling: **fix before Step 4, not before Step 3.** Step 3 (mining endpoint) is
  independent - proceed with it in either order. Step 4 (batch extraction) is BLOCKED on
  the new **Step 2b [worker-standard]**: decoration-insensitive quote matching, sha256
  source pinning with an explicit `source drift` error class, year-pinning promoted-year
  manifest URLs to `irs-prior` (the bare URLs WILL rotate to TY2026 - 1099-B was the
  canary), per-citation reasons in CLI output, and a live-green `acquire 2025 --check`.
  Authoring 7 forms of new citations on the current fragile contract would bake the
  brittleness in at scale - that is why 2b outranks batch throughput. Full spec in the
  plan. One extra datum for 2b: direct `check_graph_citations` shows 7 mismatches while
  the CLI reported 13 - reconcile (suspect the CLI `source_map` for span citations).
- **WORKING DIRECTORY (John's call, 2026-07-08; also pinned in AGENTS.md Hard rules).** All
  work happens in the local clone `C:\Users\devbox\projects\tax_graph`. The SMB-mapped `M:`
  drive is unreliable for dev (stale snapshots; git-on-SMB risk) and is NOT to be used unless
  John specifically says so. A session that finds itself under `M:` must say so and switch
  before doing anything.
- **Reviewer-tool direction (John, 2026-07-08).** Never invent `human_minutes` or assume a
  grindy paper-drill review workflow in plans. The future standalone review workbench
  (design sketch: `docs/review-workbench.md`, candidate canary Fresh Eyes - directional,
  UNSCHEDULED, not a build spec) is what will make real human review cheap; it is planned
  late, shaped by the end state. Folded into its circle-back: the M8 N-version line-2 totals
  adjudication and the first real `human_minutes` measurement.
- **Worker model tiers per step (John's call, 2026-07-07; in force).** Tags: worker-light
  (mechanical, fully prescriptive spec; may NOT touch tests/fixtures/drills/verify code
  unless the step authorizes; never self-committed), worker-standard, worker-heavy. John
  owns the tier-to-model mapping (provider-agnostic). A stuck worker STOPS and raises here.
  M10 Step 1 builds the pinned step DRIVER that operationalizes this.
- **Self-serve extension + intake directions PINNED (John, 2026-07-07; post-M10 flesh-out,
  do NOT build now).** Verified core + extension harness (users run the same pipeline at
  their own promotion gate; extensions carry a distinct trust tier and can never impersonate
  project-verified forms) - stub `docs/self-serve-extension.md`. Doc-drop intake via a
  relevance layer of additive kinds in the same graph - stub `docs/intake.md`. Seams: typed
  unresolved traces stay specific; document schema stays additive; provider-agnostic config.
- **Standing seams (do not violate):** parameter nodes with citations, never inline IRS magic
  numbers in `rule.parameters` (drill-enforced); node_type/document schema stay additive; do
  not strip form front-matter from rendered text; live graph stays referentially closed
  (frontier registry is DERIVED); `#` banned in static node ids (`#row_key` runtime-only);
  box map is the single auditable oracle comparison definition; freezes require live-diff
  provenance; disagreements never freeze without a triage disposition.

## Latest verification
- M9 phase close (Architect, 2026-07-08):
  - `pytest -q` -> 200 passed, 4 skipped
  - `validate 2025` -> OK; documents=5 nodes=35 tables=2 edges=29 rules=6 citations=13
    decisions=1; ASCII check OK
  - `frontier --year 2025` -> worklist = Schedule D line 20 only; coverage 42.4%
    filer-weighted (SOI 2023 provenance)
  - Live oracle gate (worker, 2026-07-08): `oracle fuzz --n 100 --seed 2468` -> 100/100
    agreed, triage empty; committed corpus seed 20260706, `live_ots_diff_report`

## Resolved / superseded
- M9 items: see `plans/archive/PHASE_M9.md` (close note included) and git history.
- The worker-light 1099-B URL trial errand -> absorbed into M10 Step 2.
- The "Pending for John" N-version adjudication -> deferred into the review-workbench
  circle-back (John, 2026-07-08); not a blocker anywhere.
- Pre-M9 items: `plans/archive/AGENT_HANDOFF_2026-07-07_full.md`.
