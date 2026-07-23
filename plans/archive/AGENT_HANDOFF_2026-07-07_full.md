# AGENT_HANDOFF.md

The single living doc for active Claude (Architect) <-> Codex (Worker) coordination. Update it in
place; do NOT spawn new per-topic note files. Standing rules: `../AGENTS.md`. Master plan:
`../docs/engineering-plan.md`.

## How to use
- **Worker:** raise questions/blocks under **Open for Architect**.
- **Architect:** answer there (and pin durable decisions into the relevant `PHASE_<id>.md`), then
  clear the item. Record active direction under **From Architect**.
- Keep it short - move resolved items to **Resolved** or delete them.

## Current state (2026-07-01)
- **M4 (Extraction) is complete.** `plans/PHASE_M4.md` is marked `[COMPLETE]` and archived as
  `plans/archive/PHASE_M4.md`; the two older M4 worker notes are archived beside it.
- **M1 (Compile to SQLite + light runtime) is complete.** `plans/PHASE_M1.md` is marked
  `[COMPLETE]` and archived as `plans/archive/PHASE_M1.md`.
- **M1 Step 1 is done.** Runtime base dependencies are split from build-time extras, CLI imports for
  acquire/extract are lazy, CI is a Python 3.11/3.12/3.13 matrix, and `uv.lock` is committed.
- **M1 Step 2 is done.** `tax-graph build 2025` compiles authored YAML into
  `build/tax_graph_2025.sqlite` with per-kind tables plus FTS5 over node labels and citation quotes.
- **M1 Step 3 is done.** The engine can load YAML or compiled SQLite through the same `Graph`
  interface; `tax-graph run --source sqlite|yaml` is wired, with auto-select of SQLite when built.
- **M1 Step 4 is done.** Base-only `uv --no-dev` build/run passes, README documents runtime vs
  maintainer installs, and CI has a base-runtime build/run job.
- Step 7 outline-first extraction and Step 8 held-out validation are `[DONE]`. The final Step 8
  fix taught the outline builder to attach post-line table headers to real Form 8949 line 1 rows
  and taught assembly to normalize the common column (d) minus column (e) intermediate to stable
  code-assigned ids.
- Post-M4 usability slice: extraction now also writes a standalone `review.html` beside `review.md`
  to visually compare rendered source lines, extracted objects, outline, outbound flows, repeatable
  table row slots, and linked provenance evidence. This does not change promotion rules; drafts
  remain ignored under `_drafts`.
- **M2 Step 1 is done.** Added base `mcp` dependency, `tax-graph serve`, stdio FastMCP skeleton, and
  the exact M2 tool advertisements with runtime-light import guard. Next: M2 Step 2 read-only graph
  tools.
- **M2 Step 2 is done.** Read-only MCP tools now return documents, nodes, upstream dependencies,
  downstream reachability, citations, compiled FTS citation search, and `#row_key` base-node
  resolution. Next: M2 Step 3 execution + explanation tools.
- **M2 Step 3 is done.** Execution MCP tools delegate to `Engine`: `execute_tax_tree`,
  `list_required_inputs`, `explain_calculation`, and `export_audit_file` return values, missing
  inputs, trace/rule/citations, and human-readable audit text. Next: M2 Step 4 behavioral contract +
  decisions + light-runtime gate.
- **M2 (MCP server) is complete.** `plans/PHASE_M2.md` is marked `[COMPLETE]` and archived as
  `plans/archive/PHASE_M2.md`. John accepted the Desktop startup smoke + local stdio MCP client
  walkthrough as satisfying the human gate on 2026-07-05.
- **M2 Desktop startup smoke is done.** Claude Desktop read the local `tax-graph` MCP config and
  successfully initialized/listed tools after switching the config snippet to
  `uv --directory <repo-root> run python -m tax_graph.cli serve --year 2025`.
  A local stdio MCP client also walked the full capital-gains branch and returned 1040 line 7 =
  2000 with the 8949 SUBTRACT citation.
- Next core phase by milestone order: **M6b** (Repeatable tables, canary Tandem Abacus; plan
  written just-in-time by Architect). **M7** (Frontier registry + SOI-weighted coverage, Compass
  Rose - plan written, `plans/PHASE_M7.md`) is also live and may run alongside if John chooses it.
- **M5 Step 1 is done.** Added the base-runtime `tax_graph.record` model/builder, preserved fact
  provenance via `load_facts_document()` without breaking `load_facts()`, indexed graph documents /
  citations / decisions for record use, added `decision_resolutions.schema.json`, and covered
  deterministic builder output plus bad decision/option references. Next: M5 Step 2 memo renderer.
- **M5 Step 2 is done.** Added deterministic `render_memo(record)`, including metadata, facts,
  decisions, unsupported/deferred, outputs, trace summary, carryforward display, and elections.
  Golden fixture covers the capital-gains example; no-decision records render an explicit section.
  Next: M5 Step 3 carryforward YAML emission.
- **M5 Step 3 is done.** Carryforward blocks now validate against `carryforward.schema.json`,
  gain scenarios emit an empty `carryforwards: []` payload, and negative Schedule D line 16 emits a
  raw `capital_loss` entry with no `target_node` plus the explicit worksheet/$3000 caveat in the
  Unsupported section. Next: M5 Step 4 prior-record ingestion.
- **M5 Step 4 is done.** `tax-graph run --prior-record` validates carryforward YAML, primes
  resolvable `target_node` entries as facts with Return Record provenance, reports no-target/unknown
  carryforwards without guessing, and warns when explicit facts override primed values. Next: M5
  Step 5 CLI default emission + MCP tool + docs.
- **M5 Step 5 is done.** `tax-graph run` now writes `return_record_<year>.md` plus
  `return_record_<year>.carryforward.yaml` by default, supports `--record-dir`, `--no-record`, and
  `--prior-record`, and prints output paths. MCP adds `export_return_record`. README and
  `docs/return-record.md` document implemented-v0 behavior. Next: M5 phase exit checks.
- **M5 (Return Record) is complete.** `plans/PHASE_M5.md` is marked `[COMPLETE]` and archived as
  `plans/archive/PHASE_M5.md`; exit checks passed and local generated records stayed under
  gitignored `output/`.
- **M6 Step 1 is done.** Added `tax_graph.oracles.ots` with a config-pinned OTS release model,
  sha256-verified install/unpack helper, US 1040 subprocess runner, `_out.txt` path handling, and
  tolerant line-label parser. CLI now has `tax-graph oracle install`; README and example config
  document pinned SourceForge URLs/hashes. Offline fixture tests cover parser and installer hash
  behavior; live runner smoke is `@pytest.mark.oracle` and skipped unless `OTS_1040_2025_BIN` is
  set. Next: M6 Step 2 scenario model, dual renderers, and box map validation.
- **M6 Step 2 is done.** Added `CapitalGainScenario`, deterministic renderers for Tax Graph facts
  and OTS 1040 input + 8949 CSV, `oracles/box_map_2025.yaml`, and
  `oracles/ots_label_inventory_2025.txt`. Box-map validation checks Tax Graph node ids against the
  live graph and OTS labels against the inventory, including guard labels. README documents the
  oracle fixtures. Next: M6 Step 3 differ, guards, and deliberate-bug canaries.
- **M6 Step 3 is done.** Added `tax_graph.oracles.diff` with whole-dollar mapped-box comparison,
  guard-first scenario rejection, scenario payloads on disagreements, and structured statuses
  `agreed` / `disagreed` / `rejected`. Offline tests prove clean agreement, guard rejection,
  swapped 8949 SUBTRACT role detection at the 8949 mapped total, and the unmodeled capital-loss
  limit detected as a line 7 disagreement. Next: M6 Step 4 domain profile, seeded generator, and
  fuzz command.
- **M6 Step 4 is done (verified + committed by the Architect, 2026-07-05).** Codex drafted
  `oracles/domain_2025.yaml`, `tax_graph.oracles.domain`, `tax_graph.oracles.fuzz`,
  `tax-graph oracle fuzz`, and offline/live tests, but its session hit the usage limit before it
  could run tests. Architect verification: `pytest -m m6` -> 17 passed, 2 skipped (gated
  live-oracle tests); full `pytest` -> 113 passed, 5 skipped; ASCII check OK; domain profile
  confirmed to cap net loss at -3000 with boundary values. Step 4 is marked `[DONE]` in
  `plans/PHASE_M6.md`. Next Codex session: Step 5 (corpus freeze + offline replay + triage log)
  - note the live fuzz >= 100 run and corpus freeze need an installed OTS
  (`tax-graph oracle install`, or set `OTS_1040_2025_BIN`).
- **M6 Step 5 is done.** Added `tax_graph.oracles.corpus`, `tax-graph oracle freeze`,
  `tax-graph oracle replay-corpus`, an empty `oracles/triage.yaml`, and a committed
  20-scenario frozen corpus under `examples/oracle_corpus/`. Tests cover freeze replay,
  corrupted expected failure, and rejection of disagreed candidates without disposition. Live OTS
  tests are wired but skipped here because `OTS_1040_2025_BIN` is not configured.
- **M6 live-gate closeout is done.** Codex fixed the live OTS grammar path by filling the installed
  `US_1040_template.txt`, switched freeze to require live OTS-agreed diff reports, updated live
  v23.06 labels (`D8bh`, `L7a`), regenerated the 20-scenario corpus with
  `source: live_ots_diff_report`, pinned the Windows SourceForge URL/sha256 in the example config,
  and verified `pytest -m oracle` with the installed executable. **M6 is complete** and archived as
  `plans/archive/PHASE_M6.md`.
- **M6b Step 1 is done.** Added `schemas/table.schema.json`, additive table-member fields on nodes,
  `tables` in taxpayer facts, `tables` as a loaded graph kind, semantic table/facts validation, and
  Step 1 tests in `tests/test_tables_schema_m6b.py`. SQLite now has a generic `tables` table and
  the SQLite loader tolerates older compiled artifacts that lack it. Next: M6b Step 2 compiler +
  loader parity tests/docs.
- **M6b Step 2 is done.** Added `tests/test_tables_compile_m6b.py` proving a graph containing an
  8949-style table subunit compiles to SQLite, loads back through `Graph.tables`, and preserves exact
  YAML/SQLite values and trace. README documents the SQLite `tables` projection. Next: M6b Step 3
  row-instance engine execution, totals aggregation, and trace/MCP tests.
- **M6b Step 3 is done (verified + committed by the Architect, 2026-07-05).** Codex authored the
  engine/MCP row-instance execution (table facts via `TABLE_FACTS_KEY`, instance traces
  `<template_node>#<row_key>`, totals aggregating instance operands, MCP explain/audit resolving
  instance ids, Return Record labels via the base node) but was sandbox-denied pytest. Architect
  verification: `pytest -m m6b` -> 12 passed; full `pytest` -> 131 passed, 5 skipped; ASCII OK;
  single-lot parity line 7 = 2000 with citation trace. Next Codex session: Step 4 (deterministic
  detector + column reconciler in extraction assembly), then Step 5 (promotion - JOHN's gate),
  Step 6 (multi-lot oracle widening - needs the installed OTS / `OTS_1040_2025_BIN`).
- **M6b Step 4 is done.** Added deterministic repeatable-table grouping to outline-first
  extraction. `tables` is now a draft kind; table subunits are emitted only when repeated field-grid
  row bands and the line-2 totals cue reconcile. A doctored totals cue that drops column (g) is
  flagged for review with no guessed table, and a single-row grid does not trigger. No live graph
  promotion happened. Next: Step 5 prepares the Form 8949 promotion diff and stops for JOHN's gate.
- **M6b Step 5 is done.** John approved the human gate. Form 8949 Part I/II are now promoted into
  live repeatable table subunits, Schedule D line 8b feeds from the promoted Part II column (h)
  total, and `examples/capital_gains_basic/facts.yaml` is one long-term table row (`lot_1`) with no
  scalar 1099-B compatibility path. The old M6 frozen corpus was mechanically migrated to one-row
  table facts so replay stays green until Step 6 replaces it with multi-lot scenarios. Next: Step 6
  widens the oracle harness to 1..15 lots with nonzero column (g), runs the live >=100 gate, and
  freezes a multi-lot corpus batch.
- **M6b (Repeatable tables) is complete.** Step 6 widened the oracle harness to 1..15 long-term
  lots, including scenarios that exceed the 11 printed Form 8949 slots and rows with nonzero column
  (g). Live OTS fuzz agreed 100/100 for seed 2468, and the committed oracle corpus was regenerated
  as seed 20260706 with `live_ots_diff_report` provenance. `plans/PHASE_M6b.md` is marked
  `[COMPLETE]` and archived as `plans/archive/PHASE_M6b.md`. Next by milestone order: M8
  (Skeptical Notary), with M7 (Compass Rose) still available as the parallel track.
- **M8 Step 1 is done.** Added `tax_graph.drills`, the seeded defect catalog, `tax-graph drill run`,
  in-memory drill mutations with layer attribution, and the inline-magic-number validator guard for
  IRS-sourced numeric literals in `rule.parameters`. The current L3 drill check is an explicit
  Form 8949 arithmetic stub until Step 3 replaces it with generated property checks. Next: Step 2
  both-direction structural completeness.
- **M8 Step 2 is done.** Added `tax_graph.verify.completeness`, validator/extraction hooks for
  AcroForm field-grid direction-two completeness, optional fixture-supplied MeF line inventory
  checks, and Form 8949 `not_modeled_fields` records for identity/status, non-arithmetic table
  columns, and deferred line totals. The deleted-node drill can now attribute to the
  `field_grid_completeness` L1 check when a field grid is supplied. No official MeF package is
  required by CI; the optional witness is skipped unless a clean official inventory is supplied.
  Next: Step 3 property tests from op semantics.
- **M8 Step 3 is done.** Added `tax_graph.verify.properties` and wired it into extraction
  deterministic checks plus the drill runner's L3 layer. Properties execute deterministic sample
  facts through the engine, then check COPY identity, SUM addend totals, SUBTRACT roles and
  antisymmetry, Form 8949 per-instance `h = d - e + g`, and table total aggregation. The swapped
  SUBTRACT drill is caught by the property layer. Next: Step 4 IRS worked-example miner.
- **M8 Step 4 is done.** Added deterministic IRS example segmentation, a gated mocked-in-tests
  example miner, `tax-graph verify mine-examples`, `tax-graph verify replay-examples`, and a
  confirmed frozen Form 8949 instruction Example 1 fixture under `examples/irs_examples/`.
  Mining still requires a configured LLM client and `--confirm` is the human-confirmation gate;
  replay is fully offline. Next: Step 5 N-version cross-vendor micro-extraction.
- **M8 (Verification ladder) is COMPLETE (2026-07-06).** Step 6 was implemented by the
  ARCHITECT at John's explicit direction (Codex out of messages; one-time role deviation,
  noted in the plan). Trust tiers T0-T3 assigned deterministically from check outcomes;
  confidence REMOVED from the auto-accept path (telemetry only, drill-proven no-op); seeded
  10%-min-5 calibration sampling; per-run `metrics.yaml`; `tax-graph verify report` +
  `verify diff-drafts` wired. Live exit runs: outline-first 8949 extraction -> 70 objects /
  0 flags / calibration 7; live cross-family N-version (gemini-flash vs gpt-mini) agreed on
  everything EXCEPT the Part I/II line-2 totals rule shape - **one review-queue adjudication
  PENDING for John** (primary matches the promoted graph); drill gate 100% caught; full
  pytest 168 passed / 5 skipped. Design refinement pinned: N-version diffs the SEMANTIC core
  only (free text + citation-span selection excluded). Hermeticity fix: test fixtures no
  longer inherit the developer's gitignored local config. `plans/PHASE_M8.md` is archived.
  **The drill gate is green: bulk extraction beyond the capital-gains set is UNLOCKED.**
- **M8 Step 5 is done (verified + committed by the Architect, 2026-07-06).** Codex authored
  `tax_graph/verify/nversion.py`, `tax-graph verify nversion` CLI wiring, the
  `llm.nversion_model` / vendor-family config, and `tests/test_nversion_m8.py`, but its session
  hit the usage limit before committing. Architect verification: `pytest -m m8` -> 24 passed;
  full `pytest` -> 161 passed, 5 skipped; ASCII OK. Tests cover vendor-family tracking,
  agreement corroboration in provenance, and disagreement producing side-by-side review
  entries. NOTE: the gated LIVE N-version run for `form_8949_2025` has not run yet - execute it
  during Step 6's exit-criteria pass. Next Codex session: Step 6 (trust tiers + metrics +
  verify report - the routing change that removes confidence from auto-accept), then phase
  exit: drill gate, live N-version run, `verify report`, archive, push.
- **M7 (Frontier registry + SOI-weighted coverage) is complete.** Added committed SOI
  filing-frequency weights under `data/soi/`, a deterministic frontier registry builder,
  generated `graph/2025/frontier.yaml`, `tax-graph frontier build`, `tax-graph frontier`
  text/JSON worklist + coverage, frontier-aware validation, and engine `unresolved` trace entries
  for declared/unmodeled upstream dependencies. `plans/PHASE_M7.md` is marked `[COMPLETE]` and
  archived as `plans/archive/PHASE_M7.md`. Next by milestone order: post-M7 Form Verification
  Record or the next bulk extraction expansion plan, pending Architect direction.
- **M9 Step 1 is done.** Directly fetched the verified IRS Schedule D form/instructions PDFs
  (`f1040sd.pdf`, `i1040sd.pdf`) into the local raw cache, rendered the form with PyMuPDF, and
  rendered the instructions through configured Mistral OCR. Full `tax-graph acquire 2025 --check`
  was attempted first but stopped on the existing manifest URL for `form_1099b_2025`
  (`f1099b.pdf`) returning 404 before reaching Schedule D; review/fix that URL in a later
  acquisition cleanup. Added committed fixture slices under `tests/fixtures/schedule_d_bundle/`
  plus M9 tests proving loader wiring, front-matter retention, field-grid anchors, Parts I/II/III
  outline structure, 1b-3 and 8b-10 row bands, and the line 21 cue. Next: M9 Step 2 extraction under
  the full verification net.
- **M9 Step 2 is done.** Schedule D outline-first extraction now emits deterministic draft formulas
  and table groupings for the six Form 8949 landing row bands: Part I lines 1b/2/3 and Part II
  lines 8b/9/10. Schedule D-specific classification no longer treats every column-bearing line as a
  transaction table; out-of-scope Schedule D lines and identity/status fields are carried in a draft
  `documents.yaml` `not_modeled_fields` record, so both line and field-grid completeness pass without
  guessing. Live `tax-graph extract --doc schedule_d_2025` completed with 75 accepted drafts, 0
  review, 0 deterministic issues, and calibration sample 8; `human_minutes` remains null until the
  promotion gate per the phase exit criterion. N-version corroboration agreed with 0 diffs. Schedule
  D worked-example mining ran over 10 instruction examples and reported all 10 explicitly
  unmappable because the configured OpenRouter verifier endpoint could not satisfy the requested
  structured-output parameters; no examples were frozen. Next: M9 Step 3 parameter nodes + line 21.
- **M9 Step 3 is done.** Added the first live `parameter` nodes for the Schedule D line 21
  capital-loss limit (`3000` default, `1500` married filing separately), a filing-status fact,
  `LOOKUP_TABLE`/`NEGATE`/`MAX` engine support, and line 21 edges that cap net capital losses
  while leaving gains uncapped. Parameter traces carry citations, while the final Form 1040 line 7
  output keeps its pre-existing top-level citation surface. Deferred Schedule D line 20 is declared
  through `graph/2025/frontier-declarations.yaml`; the rebuilt frontier registry lets the engine
  emit a typed `unresolved` trace for that worksheet branch without feeding it into line 21.
  Follow-on repairs completed during closeout: fact coercion now preserves top-level
  `filing_status` across MCP/example/oracle helpers, the property-check executable shim now loads
  frontier data, the old M6 loss-limit disagreement canary is retired in favor of agreement on the
  modeled line 21 branch, and the Return Record golden fixture was refreshed to the new trace
  surface. Next: M9 Step 4 promotion gate + LINK realization.
- **M9 Step 4 is done.** John approved the promotion gate. Added `tax-graph link`, promoted
  Schedule D Form 8949 landing nodes for lines 1b/2/3/8b/9/10, generated six deterministic LINK
  FEEDS edges from the reviewed Form 8949 outbound-flow declarations, and rebuilt
  `graph/2025/frontier.yaml` so the 8949 outbound entries flip to `modeled`; only deferred Schedule
  D line 20 remains declared. The supported computation intentionally sums line 1b into line 7 and
  line 8b into line 15 for parity with the current one-table-per-part 8949 model; category rows
  2/3/9/10 are linked and visible but not yet downstream addends. Updated M7/M9 tests, drill
  catalog, oracle box map/corpus expected ids, Return Record golden, and README docs. Next: M9
  Step 5 widens the oracle harness to short-term lots and losses beyond $3000.
## Open for Architect
- (none open - the M6 closeout question is ANSWERED: the live gate is NOT deferrable, and
  running it found real defects. See From Architect "M6 live-gate ruling".)

## From Architect
- **NEW (2026-07-07) - Worker model tiers per step (John's call; token-metered Codex
  billing).** From the next plan onward, every phase-plan step carries a tier tag:
  **worker-light** (mechanical execution of a fully pinned spec: YAML/fixture/doc
  authoring, pattern-following tests, pipeline runs - safe because the M8 net checks
  correctness mechanically), **worker-standard** (typical implementation), or
  **worker-heavy** (new engine semantics, schema design, extraction logic,
  promotion-adjacent work). Tiers map to whatever harness/model John has cheapest at the
  time (provider-agnostic - e.g. Antigravity/Flash or Codex/mini for light); John owns
  the mapping. Rules: light-tier steps must be written fully prescriptive (exact files,
  exact shapes, no design latitude); a stuck worker STOPS and raises here instead of
  retry-looping (flail is the expensive failure mode on token billing); steps stay small
  and atomic (mid-step usage-limit deaths have cost three re-verification passes). At M9
  close: prune this file (archive completed-phase "Current state" narration and old
  "Latest verification" logs) - every worker session re-reads it, so its length is a
  per-session tax. M10 metrics should add a worker token/cost field beside human_minutes
  to tune the tier mapping with real data.
  **Pinned deliverable for M10 planning: a step DRIVER.** A thin script reads the phase
  plan's tier tags and launches each step as a fresh non-interactive worker session with
  the tier-mapped model (codex exec -m ... / agy --model ...), runs the verification
  gates between steps, and STOPS at any JOHN's-gate step. The tier-to-model map lives in
  a config block John owns. Side effects wanted: fresh minimal context per step (kills
  the handoff re-read tax within a phase) and atomic steps by construction.
  **QC contract for worker-light steps:** (1) the full gate suite passing is the floor;
  (2) light workers may NOT modify tests, expected fixtures, the drill catalog, or
  tax_graph/verify code unless the step explicitly authorizes it - any diff touching the
  verification net gets line-by-line Architect review; (3) the Architect checks the diff
  against the step spec for scope containment; (4) light-tier work is never
  self-committed - the Architect runs gates and commits; (5) M10 metrics track rework
  and escaped defects per tier so step types that misbehave on light get promoted back
  to standard.
  **In effect NOW:** M9 Steps 5 and 6 are retrofit-tagged [worker-standard] in
  `plans/PHASE_M9.md` (both touch the verification net or carry design latitude, so
  light is disallowed). **First worker-light TRIAL errand** (standalone, any time, ideal
  for Antigravity/Flash or Codex/mini): fix the `form_1099b_2025` manifest URL - the
  current `https://www.irs.gov/pub/irs-pdf/f1099b.pdf` returns 404 (found in M9 Step 1).
  Find the correct current IRS URL for the 1099-B PDF, update the acquisition manifest,
  and verify with `tax-graph acquire 2025 --check` completing past `form_1099b_2025`.
  Scope: the manifest entry ONLY - no test, fixture, or code edits authorized. Report
  the result and the session's token usage here so we get our first light-tier data
  point.
- **NEW (2026-07-07) - Self-serve form extension direction PINNED (John's call).** The product
  is a VERIFIED CORE plus an EXTENSION HARNESS, not an encyclopedia. Users expand beyond the
  shipped form set by running the same acquire -> extract -> verify pipeline locally, standing
  at their own promotion gate, with honest machine-generated provenance (distinct trust tier;
  shipped artifacts hash-stamped; extensions can never impersonate project-verified forms).
  Stub target doc: `docs/self-serve-extension.md` (goals only - it is NOT a build plan).
  Do NOT build any of it now; the flesh-out pass happens after M10, which supplies the
  per-form human-minutes data that sizes the user gate. The only thing current work must
  respect: keep extraction config provider-agnostic and keep the unresolved-frontier trace
  typed and specific, since it becomes the user's "extract this yourself" entry point.
- **NEW (2026-07-07) - Intake direction PINNED (John's call; companion to self-serve).**
  Doc-drop onboarding: classify -> route -> gap-fill, driven by a RELEVANCE LAYER of
  additive kinds in the SAME graph (routing edges from information-return boxes, trigger
  nodes mined from Form 13614-C with obligation classes, expectation edges for
  claims-vs-docs reconciliation both directions). Required = must-resolve-before-filing,
  not must-ask-early; careless-user protection is a completeness gate. Stub target doc:
  `docs/intake.md`. Do NOT build now; same post-M10 flesh-out. Seam to respect: document
  schema stays additive (information returns are already document nodes).
- **Oracle comparison/recording mechanism AFFIRMED (John + Architect review, 2026-07-06).**
  Walked the full chain: `oracles/box_map_2025.yaml` is the single auditable definition of
  the comparison (machine-validated both ends); agreements freeze to
  `examples/oracle_corpus/` with `live_ots_diff_report` provenance (freeze RAISES without a
  live OTS executable); disagreements cannot freeze without a disposition in
  `oracles/triage.yaml` (currently empty - and the deliberate-bug canaries prove the differ
  catches, so empty means clean, not blind). Four GROWTH items pinned (not blockers):
  (1) the box map (9 boxes) must grow with every promoted form - M7's frontier registry is
  the natural enforcement point; (2) guards (1 entry) should be DERIVED from OTS's metadata
  fence list as the domain widens; (3) PolicyEngine is the second witness, triggered by the
  first liability branch; (4) metrics payoff fields (human_minutes, escapes) get first real
  data at the NEXT promotion - whoever runs it fills them in.
- **NEW (2026-07-06) - Form Verification Record decided (user-facing trust surface; build
  post-M7).** Design pinned in `docs/extraction-verification.md` Section 10: one GENERATED
  MD page per form + roll-up `VERIFICATION.md` (witness list per form - differential where
  an oracle covers it, IRS examples, N-version, properties, calibration; absences stated,
  never papered over; triage outcomes shown; plain-language tiers from the supported-branch
  bar; same data queryable over MCP). Generated from metrics/corpus/triage/drill/example
  data, no hand-authoring. Slots after M7; do NOT build during M7.
- **PINNED (2026-07-06, John's call): M9 is the LAST bespoke single-form phase.** M10 (plan
  just-in-time at M9 close) batch-runs the pipeline across the full OTS-witnessed set (the
  solver's metadata fence list: Schedules 1, 1-A, 2, 3, A, B, D/8949, Form 6251), with human
  effort limited to exception queues + calibration + promotion gates, promotions sequenced
  by the frontier. See engineering-plan "M10". M9's job is to land the six form-agnostic
  capabilities batch depends on (LINK, parameters/ops, second acquire run, record generator,
  growth mechanics) and MEASURE the per-form human cost that sizes M10.
- **Next: start M9 (Schedule D expansion + LINK + Verification Record, canary Daisy Chain).**
  `plans/PHASE_M9.md` is written (2026-07-06); milestone block + gate row added to the
  engineering plan. The Architect verified M7 closure first (12 passed on `-m m7`; full
  pytest 180 passed / 5 skipped; `tax-graph frontier` reports ~42.4% filer-weighted coverage
  with SOI provenance; worklist unanimous on Schedule D). Key pins: Schedule D artifacts
  were NEVER rendered (only the 8949 bundle exists in `.cache/raw/2025/`) - Step 1 acquires
  them (gated: network + Mistral OCR key); Step 2 records the FIRST real human-minutes in
  metrics.yaml; Step 3 introduces the first `parameter` nodes (line 21 loss limit,
  $3000/$1500 MFS, cited - no-magic-numbers flag enforced repo-wide + new
  wrong_parameter_value drill); **Step 4 promotion is JOHN's gate**, then LINK resolves the
  8949 declarations against the PROMOTED index only, frontier flips declared -> modeled and
  coverage rises; Step 5 widens the oracle domain (short-term lots; losses past $3000 become
  IN-domain; retire the old out-of-domain canary for a line 21 agreement test); Step 6 ships
  the generated `VERIFICATION.md` + per-form pages + MCP exposure (byte-stable regeneration;
  witness absences stated plainly). Deferred, do not build: tax liability/QDCGT, 1040 full
  extraction, PolicyEngine, Coverage Map render, carryover computation.
- **Superseded: start M7 direction (M7 is complete and archived).**
  `plans/PHASE_M7.md` is the only open plan (written 2026-07-05, two phases ahead of its
  turn - re-validate file/module references against the CURRENT repo at phase start; the
  codebase has since gained M5 records, M6 oracles, M6b tables, and M8 verify/drills).
  Work the 5 steps in order: SOI weight table (acquire, behind the `[acquire]` extra) ->
  frontier registry schema + deterministic builder -> `tax-graph frontier` worklist +
  coverage metric -> validator integration (registered frontier passes, dangling edge
  fails) -> engine `unresolved` trace entries (never compute through the wall). Key pins
  unchanged: live graph stays referentially CLOSED; the registry is DERIVED, rebuilt like
  the SQLite compile; weight = returns-filed, not dollars; SOI provenance labeled
  (sample-based, ~2yr lag); base-deps `validate`/`run`/`frontier` must work. Note the 8949
  outbound-flow declarations now live in the PROMOTED graph context (M6b) - registry
  entries target the live Schedule D lines. Why M7 now: the M8 drill gate unlocked bulk
  extraction, and M7 makes the expansion order data-driven (the Architect plans the
  form-set expansion phase just-in-time from M7's weighted worklist).
- **Pending for John (from the M8 live N-version run):** adjudicate the Part I/II line-2
  totals rule disagreement (primary = SUM/addend, matching the promoted graph; the
  mini-model secondary's alternative shape is the outlier). Seconds, not minutes.
- **Superseded: start M8 direction (M8 is complete and archived).** `plans/PHASE_M8.md` is
  written (2026-07-06). The Architect independently verified M6b closure first: full pytest
  137 passed / 5 skipped; `validate 2025` OK with tables=2; multi-lot example line 7 = 250
  through the promoted Part II column (h) total; live `pytest -m oracle` 2 passed. Read
  `docs/extraction-verification.md` FIRST - the plan only sequences it. Key pins: every drill
  asserts WHICH layer catches it, and a miss fails the gate honestly (never shrink the
  catalog); confidence comes OUT of the auto-accept path in Step 6 (telemetry only);
  vendor-FAMILY diversity for N-version (two families through OpenRouter is fine); mined
  worked examples freeze into `examples/irs_examples/` only after human confirmation and
  replay offline; MeF inventory is optional (official source or clean skip); the drill gate
  green UNLOCKS bulk extraction beyond capital gains. Adopted defaults (John may override):
  10% calibration sample (min 5), N=2 families, 100% drill bar. After M8: Schedule D + 1040
  extraction and the LINK step become the working set; M7 (Compass Rose) stays available in
  parallel.
- **Superseded: start M6b direction (M6b is complete and archived).** `plans/PHASE_M6b.md` was written
  (2026-07-05); the Architect independently re-verified M6 closure first (offline 23/2, live
  oracle gate 2 passed against the installed OTS, corpus provenance `live_ots_diff_report`,
  freeze refuses without a live executable). Read engineering-plan "Repeatable tables (decided
  2026-07-01)" before starting - the plan only sequences it. Key pins: static ids stay
  template-level (`#` banned); `row_key` is runtime-only and may exceed the 11 printed slots;
  facts rows are keyed by COLUMN ID from the table definition, computed columns in facts are an
  error; zero rows -> totals 0 with an explicit trace note; **Step 5 promotion is JOHN's gate**
  (prepare the diff, wait for approval - first-ever draft promotion; preserve the hand-authored
  FEEDS edges into Schedule D by retargeting to the promoted totals nodes); the single-lot
  example REAUTHORS as a one-row instance (no scalar-compat shim). Step 6 widens the M6 oracle
  harness to 1..15 lots with nonzero column (g) and freezes a multi-lot corpus batch
  (live-diff provenance only). After M6b: M8 (Skeptical Notary, just-in-time); M7 (Compass
  Rose) remains the parallel option.
- **M6 live-gate ruling (2026-07-05): do NOT close M6 on offline gates.** Cross-implementation
  agreement IS this phase; deferring the live run would close the phase without ever having
  witnessed a single OTS agreement. The Architect installed the pinned OTS (2025 v23.06,
  sha256-verified, `.cache/oracles/...`) and ran `pytest -m oracle`: **both live tests FAIL with
  real defects** - (F1) the OTS input renderer emits invalid grammar (`Status:` colon is fatal;
  required header question sequence missing; the 2025 spreadsheet label is
  `f8949_spreadsheet-A/D:`, not `f8949spreadsheet:`; title must start
  `US Federal 1040 Tax Form - 2025`), and (F2) `freeze_generated_corpus` computes expected
  values from OUR OWN ENGINE and stamps `status: agreed` + OTS provenance without OTS ever
  running - self-agreement with false provenance; the committed corpus must be REGENERATED
  against live OTS. Full findings + fix directions (template-filling render; freeze consumes a
  live diff report) are pinned in `plans/PHASE_M6.md` "Architect live-gate review". Next Codex
  session: fix F1-F3, run the live >=100 fuzz, regenerate + re-freeze the corpus, commit the
  OTS pin into the example config/README, THEN close M6. Set `OTS_1040_2025_BIN` to the
  installed exe to run the gate.
- **Next: start M6 (Differential harness, canary Twin Witness).** `plans/PHASE_M6.md` is written
  (2026-07-05); read `docs/oracle-strategy.md` FIRST (fencing, triage outcomes, corpus policy).
  State the canary, wait for John's go, then work the 5 steps in order. Key pins: pinned PREBUILT
  OTS release binaries (no vendored GPL source, no C toolchain - the corpus-factory repo timing is
  AMENDED to only-when-needed); `pytest -m m6` is fully offline (canned OTS fixtures), real OTS
  only behind `@pytest.mark.oracle`; whole-dollar exact diff; guard boxes reject out-of-domain
  scenarios BEFORE diffing; the loss-beyond-$3000 canary must be DETECTED (our slice has no loss
  limit - that divergence firing is the proof the harness sees unmodeled semantics); freeze >= 20
  agreed scenarios into `examples/oracle_corpus/`. PolicyEngine/Tax-Calculator adapters, parameter
  diffing, and OTS C-mining are explicitly DEFERRED - do not build them. Remaining sequence after
  M6: M6b (Tandem Abacus, just-in-time plan) -> M8 (Skeptical Notary, just-in-time plan); M7
  (Compass Rose, plan already live) may run parallel whenever John chooses.
- **M5 closure note:** M5 is archived complete as of 2026-07-05. The old "start M5" direction is
  superseded. Next core phase is M6 (Twin Witness), whose just-in-time plan should fold in
  `docs/oracle-strategy.md`; M7 (Compass Rose) remains live as the parallel track if John redirects.
- **NEW (2026-07-05) - Parameters and thresholds are first-class (decided; John's OTS C
  reading).** Pinned in engineering-plan "Parameters and thresholds (decided 2026-07-05)".
  Summary: IRS-sourced numbers (standard deduction, bracket tables, worksheet breakpoints,
  caps/floors, phaseouts) become `parameter` nodes (additive node_type) with individual
  citations, consumed via `LOOKUP_TABLE`/`LOOKUP_BRACKET` edges - NEVER inline magic numbers
  in `rule.parameters` (drill-enforced under M8). Bulk tables (under-$100k tax table) compile
  as data resources, not per-row nodes. New cheapest oracle channel in
  `docs/oracle-strategy.md`: diff parameter values against PolicyEngine-US parameters YAML +
  OTS C constants. No op-vocabulary change; engine grows ops when the first worksheet branch
  lands. Nothing to build NOW - the seam to respect: keep node_type additive and do not let
  any extraction/authoring write an IRS number inline into a rule.
- **NEW (2026-07-05) - Oracle strategy pinned (extends M6, no new milestone).** Design doc:
  `docs/oracle-strategy.md` (canonical); summary added to the M6 block in the engineering
  plan. Key rulings: OTS logic is imperative C (no ruleset diff possible), but its
  line-labeled I/O maps 1:1 to IRS line numbers, so scale comes from execution-level
  fuzzing: domain profile -> seeded scenario generator -> box-level diff (`box_map.yaml`,
  drill-tested) -> triage -> FREEZE agreed pairs as offline `examples/` fixtures. A separate
  **oracle corpus factory repo** (created at M6 start) holds oracle builds/GPL source/
  generator/corpus releases; main-repo CI only replays frozen data. NO IRS enrollment (ATS
  certifies transmission acceptance, not arithmetic); public ATS scenario PDFs + MeF schema
  are downloaded data only. OTS static C-mining = time-boxed, flag-only experiment. These
  shape `PHASE_M6.md` when it is written just-in-time. Proposed to John (defaults adopted
  unless vetoed): corpus repo at M6 start; arm's-length IRS stance; mining never
  load-bearing.
- **NEW (2026-07-05) - M8 Verification ladder planned (canary Skeptical Notary).** John's
  top concern: extraction accuracy cannot depend on hand-authored references or humans
  re-deriving forms - that is the exact bottleneck extraction exists to remove. Design doc:
  `docs/extraction-verification.md` (canonical); milestone block + gate row + sequencing in
  `docs/engineering-plan.md`. Core moves: (1) seeded-defect drills that mutation-test the
  check net itself (100% catalog catch rate required); (2) both-direction field-grid
  completeness + optional MeF schema box inventory; (3) engine-executed property tests from
  op semantics; (4) mine IRS instruction "Example." blocks into facts/expected fixtures and
  execute them through the extracted graph (authoritative numbers, human confirms in
  minutes, freeze into `examples/`); (5) cross-VENDOR N-version micro-extraction diffs; (6)
  trust tiers T1/T2/T3 + `metrics.yaml` + year-over-year delta verification. **Hard
  sequencing rule: no bulk extraction beyond the capital-gains form set until the M8 drill
  gate passes.** M8 slots after M6 (which supplies the differential layer), but steps 1-3
  are offline/independent and may be pulled forward. `PHASE_M8.md` is written just-in-time.
  Awaiting John's veto/OK on three defaults: 10% calibration sample (min 5), N=2 vendors,
  100% drill bar.
- **M2 closure note:** M2 is archived complete as of 2026-07-05 after John's acceptance of the
  Desktop startup smoke + local stdio MCP walkthrough. The old "start M2" direction is superseded.
- **DECIDED - repeatable-table addressing + detection** (answers your Open item; full policy in
  engineering-plan "Repeatable tables (decided)"; new milestone **M6b**, canary Tandem Abacus). Your
  (a)/(b)/(c)/(d) split and working proposal are adopted, with John's aggregate-subunit rule:
  - A repeatable table = **one aggregate subunit** (row-template columns at line 1 + totals row at
    line 2), NOT loose sibling nodes. Static ids stay flat/template-level
    (`..._part_i_line_1_column_d`, `..._line_2_column_d_total`).
  - Instances are **runtime-only** in a separate namespace: facts supply rows keyed by `row_key`; the
    trace/MCP address an instance as `<column_node>#<row_key>`; `#` is banned by the node_id pattern,
    so a runtime id can never collide with a static id. Physical printed slots (`line 1.01`..) are
    acquisition/review geometry only - never in ids / graph / facts.
  - **Detection is deterministic + dual-signal:** repeated field-grid row-band (geometry) AND an
    explicit totals cue ("Add the amounts in columns (d),(e),(g),(h)") or an aligned totals row. Your
    outline already emits `transaction_table` + `totals` - that IS the trigger. A cross-check
    reconciles totals columns vs grid + cue; ambiguity -> human-review flag, never a guess. Row count
    is never parsed (runtime fact). No LLM call / no second fetch to fire the trigger.
  - Home = **M6b** (schema `tables` object + facts instances + per-row engine + aggregation + promote
    8949); `PHASE_M6b.md` written just-in-time when M6b becomes next. NOT part of M1.
- **M1 seam (respect; do not build the table now):** keep the compiler generic over object kinds and
  the compiled `nodes` row additive (SQLite rebuilds from YAML, so it is free). Single-lot parity
  unchanged. Guardrail pinned in `PHASE_M1.md`.
- **M2 seam (for whoever authors PHASE_M2):** MCP node addressing speaks table + column + optional
  `#row_key` from day one, so no breaking change when M6b lands.
- **DO NOT promote `graph/2025/_drafts/form_8949_2025/` into live `graph/` before M6b** - those
  per-column nodes are correct as templates but would land as loose siblings without the subunit
  grouping. Leave them in `_drafts/` (gitignored).
- **Reconcile the uncommitted `review_html.py` WIP (Form Structure panel) with this decision.** It
  derives physical row slots from the AcroForm grid (`Table_Line1_Part1..RowN`) and labels them
  `part_i.line_1.row_01.column_h` / "line 1.01 through line 1.11". That is correct as concept (c)
  REVIEW-DISPLAY geometry and it confirms the deterministic geometry signal - good. Keep it SEPARATE
  from runtime addressing: the physical-slot shape (`.row_01.`, dotted) is NOT the instance address.
  Runtime/MCP instances are `<column_node>#<row_key>` with a runtime `row_key` (concept d) that can
  EXCEED the printed 11 slots (attachments). Do not let `row_01` become the instance key, and do not
  let the dotted display shape leak into node ids (static ids stay flat snake_case).
- **Reserved (post-MVP, nothing to build now): Coverage Map + form front-matter** (form `title` +
  verbatim-cited `purpose`/`who_must_file`). See engineering-plan "Reserved seams". The only thing
  current work must respect: keep the document schema additive, and do NOT add any filter that strips
  form front-matter ("Purpose of Form" / "Who Must File" / title) from rendered text.

## Latest verification
- M8 Step 1:
  - `.\.venv\Scripts\python.exe -m pytest -m m8` -> 4 passed, 142 deselected
  - `.\.venv\Scripts\python.exe -m tax_graph.cli drill run --year 2025` -> 11 drills, PASS, expected layer attribution
  - `.\.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> graph integrity OK; tables=2
  - `.\.venv\Scripts\python.exe -m pytest` -> 141 passed, 5 skipped
  - `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK
- M7 phase exit:
  - `.\.venv\Scripts\python.exe -m pytest -m m7` -> 12 passed, 173 deselected
  - `.\.venv\Scripts\python.exe -m tax_graph.cli frontier --year 2025` -> worklist printed; coverage ~42.4% full SOI universe / 100.0% in-scope
  - `.\.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> graph integrity OK
  - `.\.venv\Scripts\python.exe -m tax_graph.cli run --facts examples\capital_gains_basic\facts.yaml --source yaml --no-record` -> Form 1040 line 7 = 2000
  - `uv --directory <repo-root> run --no-dev python -m tax_graph.cli frontier --year 2025` -> base-runtime frontier query OK
  - `.\.venv\Scripts\python.exe -m pytest` -> 180 passed, 5 skipped
  - `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK
- M9 Step 1:
  - `.\.venv\Scripts\python.exe -m tax_graph.cli acquire 2025 --check` -> stopped on IRS 404 for `https://www.irs.gov/pub/irs-pdf/f1099b.pdf`
  - `Invoke-WebRequest https://www.irs.gov/pub/irs-pdf/f1040sd.pdf` -> wrote local Schedule D PDF
  - `Invoke-WebRequest https://www.irs.gov/pub/irs-pdf/i1040sd.pdf` -> wrote local Schedule D instructions PDF
  - `.\.venv\Scripts\python.exe -c "<render_form_pdf schedule_d_2025>"` -> emitted `.txt` and `.fields.json`
  - `.\.venv\Scripts\python.exe -c "<render_instructions_ocr instructions_schedule_d_2025>"` -> emitted `.txt`, `.pages/`, `.links.json`, `.ocr.json`
  - `.\.venv\Scripts\python.exe -m pytest tests\test_schedule_d_bundle_m9.py -m m9` -> 2 passed
- M9 Step 2:
  - `.\.venv\Scripts\python.exe -m pytest tests\test_schedule_d_bundle_m9.py tests\test_schedule_d_extraction_m9.py -m m9` -> 5 passed
  - `.\.venv\Scripts\python.exe -m pytest tests\test_extract_outline_m4.py tests\test_tables_detector_m6b.py -m "m4 or m6b"` -> 13 passed
  - `.\.venv\Scripts\python.exe -m pytest tests\test_trust_tiers_m8.py::test_metrics_capture_tiers_layers_and_telemetry` -> 1 passed
  - `.\.venv\Scripts\python.exe -m pytest tests\test_examples_m8.py -m m8` -> 5 passed
  - `.\.venv\Scripts\python.exe -m tax_graph.cli extract --doc schedule_d_2025` -> accepted=75, review=0, deterministic_issues=0; `metrics.yaml` written with calibration_sample=8
  - `.\.venv\Scripts\python.exe -m tax_graph.cli verify nversion --doc schedule_d_2025` -> agreed, diffs=0
  - `.\.venv\Scripts\python.exe -m tax_graph.cli verify mine-examples --doc schedule_d_2025 --limit 10 --source yaml` -> examples=10, agreed=0, disagreed=0, unmappable=10; no fixtures frozen
- M9 Step 3:
  - `.\.venv\Scripts\python.exe -m pytest -m m9` -> 11 passed
  - `.\.venv\Scripts\python.exe -m pytest tests\test_drills_m8.py -m m8` -> 3 passed
  - `.\.venv\Scripts\python.exe -m pytest tests\test_compile_m1.py tests\test_tables_compile_m6b.py tests\test_tables_engine_m6b.py -m "m1 or m6b"` -> 10 passed
  - `.\.venv\Scripts\python.exe -m pytest tests\test_examples_m8.py tests\test_graph_validator.py tests\test_mcp_m2.py tests\test_oracles_corpus_m6.py tests\test_oracles_diff_m6.py tests\test_return_record_m5.py` -> 49 passed
  - `.\.venv\Scripts\python.exe -m pytest` -> 193 passed, 4 skipped
  - `.\.venv\Scripts\python.exe -m tax_graph.cli drill run --year 2025` -> 12 drills, PASS
  - `.\.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> graph integrity OK; documents=5 nodes=30 tables=2 edges=23 rules=6 citations=7 decisions=1
  - `.\.venv\Scripts\python.exe -m tax_graph.cli frontier build --year 2025` -> declared=6, modeled=5
  - `.\.venv\Scripts\python.exe -m tax_graph.cli run --facts examples\capital_gains_basic\facts.yaml --source yaml --no-record` -> line 7 = 2000; parameter trace present
  - `.\.venv\Scripts\python.exe -m tax_graph.cli run --facts examples\capital_gains_multi_lot\facts.yaml --source yaml --no-record` -> line 7 = 250
  - `.\.venv\Scripts\python.exe -m tax_graph.cli run --facts examples\capital_gains_basic\facts.yaml --source sqlite --no-record` -> line 7 = 2000
  - `.\.venv\Scripts\python.exe -m tax_graph.cli run --facts examples\capital_gains_multi_lot\facts.yaml --source sqlite --no-record` -> line 7 = 250
  - `.\.venv\Scripts\python.exe -m tax_graph.cli build 2025` -> built SQLite graph
  - `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK
- M8 Step 2:
  - `.\.venv\Scripts\python.exe -m pytest -m m8` -> 12 passed, 142 deselected
  - `.\.venv\Scripts\python.exe -m pytest -m "m4 or m8"` -> 41 passed, 113 deselected
  - `.\.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> graph integrity OK; tables=2
  - `.\.venv\Scripts\python.exe -m pytest` -> 149 passed, 5 skipped
  - `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK
- M8 Step 3:
  - `.\.venv\Scripts\python.exe -m pytest -m m8` -> 16 passed, 142 deselected
  - `.\.venv\Scripts\python.exe -m pytest -m "m4 or m8"` -> 45 passed, 113 deselected
  - `.\.venv\Scripts\python.exe -m tax_graph.cli drill run --year 2025` -> 11 drills, PASS, L3 properties caught F3 drills
  - `.\.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> graph integrity OK; tables=2
  - `.\.venv\Scripts\python.exe -m pytest` -> 153 passed, 5 skipped
  - `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK
- M8 Step 4:
  - `.\.venv\Scripts\python.exe -m pytest -m m8` -> 20 passed, 142 deselected
  - `.\.venv\Scripts\python.exe -m tax_graph.cli verify replay-examples --year 2025 --source yaml` -> 1 example, OK
  - `.\.venv\Scripts\python.exe -m pytest -m "m4 or m8"` -> 49 passed, 113 deselected
  - `.\.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> graph integrity OK; tables=2
  - `.\.venv\Scripts\python.exe -m pytest` -> 157 passed, 5 skipped
  - `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK
- M6b Step 1:
  - `.\.venv\Scripts\python.exe -m pytest -m m6b` -> 7 passed, 124 deselected
  - `.\.venv\Scripts\python.exe -m pytest -m "m0 or m1"` -> 24 passed, 107 deselected
  - `.\.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> graph integrity OK; tables=0
  - `.\.venv\Scripts\python.exe -m pytest` -> 126 passed, 5 skipped
  - `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK
- M6b Step 2:
  - `.\.venv\Scripts\python.exe -m pytest -m m6b` -> 8 passed, 124 deselected
  - `.\.venv\Scripts\python.exe -m pytest -m m1` -> 6 passed, 126 deselected
  - `.\.venv\Scripts\python.exe -m pytest` -> 127 passed, 5 skipped
  - `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK
- M6b Step 3:
  - Architect verification: `.\.venv\Scripts\python.exe -m pytest -m m6b` -> 12 passed
  - Architect verification: `.\.venv\Scripts\python.exe -m pytest` -> 131 passed, 5 skipped
  - Architect verification: `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK
- M6b Step 4:
  - `.\.venv\Scripts\python.exe -m pytest -m m6b` -> 16 passed, 124 deselected
  - `.\.venv\Scripts\python.exe -m pytest -m m4` -> 29 passed, 111 deselected
  - `.\.venv\Scripts\python.exe -m pytest` -> 135 passed, 5 skipped
  - `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK
- M6b Step 5:
  - `.\.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> graph integrity OK; tables=2
  - `.\.venv\Scripts\python.exe -m tax_graph.cli build 2025` -> built SQLite graph with tables=2
  - `.\.venv\Scripts\python.exe -m pytest -m m6b` -> 17 passed, 124 deselected
  - `.\.venv\Scripts\python.exe -m pytest -m "m0 or m2 or m5 or m6"` -> 66 passed, 2 skipped, 73 deselected
  - `.\.venv\Scripts\python.exe -m tax_graph.cli run --facts examples\capital_gains_basic\facts.yaml --source yaml --no-record` -> Form 1040 line 7 = 2000 with `#lot_1` SUBTRACT trace
  - `.\.venv\Scripts\python.exe -m tax_graph.cli run --facts examples\capital_gains_basic\facts.yaml --source sqlite --no-record` -> Form 1040 line 7 = 2000 with `#lot_1` SUBTRACT trace
  - `.\.venv\Scripts\python.exe -m pytest` -> 136 passed, 5 skipped
  - `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK
- M6b Step 6 / phase exit:
  - `.\.venv\Scripts\python.exe -m pytest -m "m6 or m6b"` -> 41 passed, 2 skipped, 99 deselected
  - `.\.venv\Scripts\python.exe -m tax_graph.cli run --facts examples\capital_gains_multi_lot\facts.yaml --source yaml --no-record` -> Form 1040 line 7 = 250 with `#lot_gain`, `#lot_loss`, and `#lot_adjusted` traces
  - `.\.venv\Scripts\python.exe -m tax_graph.cli oracle fuzz --year 2025 --n 100 --seed 2468 --source yaml` -> generated=100, agreed=100, disagreed=0, rejected=0
  - `.\.venv\Scripts\python.exe -m tax_graph.cli oracle freeze --year 2025 --n 20 --seed 20260706 --generated-date 2026-07-06 --oracle-version ots_2025_23.06 --source yaml` -> wrote 20 live OTS-agreed multi-lot scenarios
  - `.\.venv\Scripts\python.exe -m tax_graph.cli oracle replay-corpus --year 2025 --source yaml` -> 20 scenarios, OK
  - `.\.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> graph integrity OK; tables=2
  - `.\.venv\Scripts\python.exe -m tax_graph.cli build 2025` -> built SQLite graph with tables=2
  - `.\.venv\Scripts\python.exe -m tax_graph.cli run --facts examples\capital_gains_basic\facts.yaml --source yaml --no-record` -> Form 1040 line 7 = 2000
  - `.\.venv\Scripts\python.exe -m tax_graph.cli run --facts examples\capital_gains_basic\facts.yaml --source sqlite --no-record` -> Form 1040 line 7 = 2000
  - `uv --directory <repo-root> run --no-dev python -m tax_graph.cli run --facts examples\capital_gains_basic\facts.yaml --source yaml --no-record` -> Form 1040 line 7 = 2000
  - `.\.venv\Scripts\python.exe -m pytest -m oracle` with `OTS_1040_2025_BIN` set -> 2 passed, 140 deselected
  - `.\.venv\Scripts\python.exe -m pytest` -> 137 passed, 5 skipped
  - `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK
- M6 phase exit / live-gate closeout:
  - `.\.venv\Scripts\python.exe -m pytest -m m6` -> 23 passed, 2 skipped, 99 deselected
  - `.\.venv\Scripts\python.exe -m pytest -m oracle` with `OTS_1040_2025_BIN` set -> 2 passed,
    122 deselected
  - `.\.venv\Scripts\python.exe -m tax_graph.cli oracle freeze --year 2025 --n 20 --seed 20250705 --generated-date 2026-07-05 --oracle-version ots_2025_23.06 --source yaml` -> wrote 20 live OTS-agreed scenarios
  - `.\.venv\Scripts\python.exe -m tax_graph.cli oracle replay-corpus --year 2025 --source yaml` -> 20 scenarios, OK
  - `.\.venv\Scripts\python.exe -m pytest` -> 119 passed, 5 skipped
  - `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK
  - `uv --directory <repo-root> run --no-dev python -m tax_graph.cli run --facts examples\capital_gains_basic\facts.yaml --source yaml --no-record` -> Form 1040 line 7 = 2000
- M5 Step 1:
  - `.\.venv\Scripts\python.exe -m pytest -m m5` -> 2 passed, 85 deselected
  - `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK
- M5 Step 2:
  - `.\.venv\Scripts\python.exe -m pytest -m m5` -> 4 passed, 85 deselected
  - `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK
- M5 Step 3:
  - `.\.venv\Scripts\python.exe -m pytest -m m5` -> 7 passed, 85 deselected
  - `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK
- M5 Step 4:
  - `.\.venv\Scripts\python.exe -m pytest -m m5` -> 11 passed, 85 deselected
  - `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK
- M5 Step 5:
  - `.\.venv\Scripts\python.exe -m pytest -m m5` -> 14 passed, 85 deselected
  - `.\.venv\Scripts\python.exe -m pytest -m m2` -> 11 passed, 88 deselected
  - `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK
- M5 phase exit:
  - `.\.venv\Scripts\python.exe -m pytest -m m5` -> 14 passed, 85 deselected
  - `.\.venv\Scripts\python.exe -m tax_graph.cli run --facts examples\capital_gains_basic\facts.yaml --source yaml --record-dir output\m5_exit` -> Form 1040 line 7 = 2000; memo + carryforward written
  - `uv --directory <repo-root> run --no-dev python -m tax_graph.cli run --facts examples\capital_gains_basic\facts.yaml --source yaml --record-dir output\m5_base` -> Form 1040 line 7 = 2000; memo + carryforward written
  - Generated `output\m5_exit\return_record_2025.carryforward.yaml` validated against `carryforward.schema.json`
  - `.\.venv\Scripts\python.exe -m pytest` -> 96 passed, 3 skipped
  - `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK
- M6 Step 1:
  - `.\.venv\Scripts\python.exe -m pytest -m m6` -> 3 passed, 1 skipped, 99 deselected
  - `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK
- M6 Step 2:
  - `.\.venv\Scripts\python.exe -m pytest -m m6` -> 10 passed, 1 skipped, 99 deselected
  - `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK
- M6 Step 3:
  - `.\.venv\Scripts\python.exe -m pytest -m m6` -> 14 passed, 1 skipped, 99 deselected
  - `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK
- M6 Step 5:
  - `.\.venv\Scripts\python.exe -m tax_graph.cli oracle freeze --year 2025 --n 20 --seed 20250705 --generated-date 2026-07-05 --oracle-version ots_2025_23.06 --source yaml` -> wrote 20 scenarios under `examples\oracle_corpus`
  - `.\.venv\Scripts\python.exe -m pytest -m m6` -> 22 passed, 2 skipped, 99 deselected
  - `.\.venv\Scripts\python.exe -m pytest` -> 118 passed, 5 skipped
  - `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK
  - `uv --directory <repo-root> run --no-dev python -m tax_graph.cli run --facts examples\capital_gains_basic\facts.yaml --source yaml --no-record` -> Form 1040 line 7 = 2000
  - `.\.venv\Scripts\python.exe -m pytest -m oracle` -> 2 skipped, 121 deselected (no `OTS_1040_2025_BIN` configured)
  - `.\.venv\Scripts\python.exe -m tax_graph.cli oracle replay-corpus --year 2025 --source yaml` -> 20 scenarios, OK
- M2 Step 1:
  - `uv run pytest -m m2` -> 2 passed, 74 deselected
  - `uv run pytest` -> 73 passed, 3 skipped
  - `uv run python tools\check_ascii.py` -> ASCII check OK
- M2 Step 2:
  - `uv run pytest -m m2` -> 5 passed, 74 deselected
  - Direct MCP tool tests cover document/node lookup, dependency/downstream traversal, citation id
    lookup, compiled FTS search, and `#row_key` base-node resolution
- M2 Step 3:
  - `uv run pytest -m m2` -> 9 passed, 74 deselected
  - Direct MCP tool tests cover `execute_tax_tree`, `list_required_inputs`, `explain_calculation`,
    and `export_audit_file` on `examples/capital_gains_basic/facts.yaml`
- M2 Step 4:
  - `uv run --no-dev python -c "<serve construction smoke>"` -> all M2 tools listed, no
    `fitz`/`mistralai` imports
  - `uv run pytest -m m2` -> 11 passed, 74 deselected
  - `uv run pytest` -> 82 passed, 3 skipped
  - `uv run python tools\check_ascii.py` -> ASCII check OK
- M2 Desktop startup smoke:
  - Claude Desktop log `logs\mcp-server-tax-graph.log` -> `tax-graph` initialized, returned
    `initialize`, and served `tools/list` using `uv --directory ... run python -m tax_graph.cli`.
  - Local stdio MCP client via SDK -> tools listed; `get_document`, `get_dependencies`,
    `get_downstream_effects`, `execute_tax_tree`, `explain_calculation`, and `export_audit_file`
    all passed; 1040 line 7 = 2000; citation `cite_8949_col_h_gain` present.
  - `uv run pytest -m m2` -> 11 passed, 74 deselected
  - `uv run python tools\check_ascii.py` -> ASCII check OK
- M2 phase exit:
  - John accepted the Desktop startup smoke + local stdio MCP client walkthrough as the human gate.
  - `.\.venv\Scripts\python.exe -m pytest -m m2` -> 11 passed, 74 deselected
  - `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK
  - `plans/archive/PHASE_M2.md` marked `[COMPLETE]`
- M1 phase exit:
  - `uv run pytest -m m1` -> 6 passed, 68 deselected
  - `uv run tax-graph build 2025` -> wrote `build/tax_graph_2025.sqlite`
  - `uv run tax-graph run --facts examples\capital_gains_basic\facts.yaml --source sqlite` -> Form
    1040 line 7 = 2000
  - `uv run python tools\check_ascii.py` -> ASCII check OK
- M1 Step 1:
  - `uv run pytest -m m1` -> 1 passed, 68 deselected
  - `uv run tax-graph validate 2025` -> graph integrity OK
  - `uv run tax-graph run --facts examples\capital_gains_basic\facts.yaml` -> Form 1040 line 7 =
    2000
  - `uv run pytest` -> 66 passed, 3 skipped (base-only env skips PyMuPDF render)
  - `uv run python tools\check_ascii.py` -> ASCII check OK
- M1 Step 2:
  - `uv run tax-graph build 2025` -> wrote `build/tax_graph_2025.sqlite`
  - SQLite FTS smoke -> `Subtract` citation search returns `cite_8949_col_h_gain`
  - `uv run pytest -m m1` -> 4 passed, 68 deselected
  - `uv run pytest` -> 69 passed, 3 skipped
  - `uv run python tools\check_ascii.py` -> ASCII check OK
- M1 Step 3:
  - SQLite vs YAML parity test compares exact `values` and `trace`
  - `uv run tax-graph run --facts examples\capital_gains_basic\facts.yaml --source sqlite` -> Form
    1040 line 7 = 2000
  - `uv run tax-graph run --facts examples\capital_gains_basic\facts.yaml --source yaml` -> Form
    1040 line 7 = 2000
  - `uv run pytest -m m1` -> 6 passed, 68 deselected
  - `uv run pytest` -> 71 passed, 3 skipped
  - `uv run python tools\check_ascii.py` -> ASCII check OK
- M1 Step 4:
  - `uv run --no-dev tax-graph build 2025` -> wrote `build/tax_graph_2025.sqlite`
  - `uv run --no-dev tax-graph run --facts examples\capital_gains_basic\facts.yaml --source sqlite`
    -> Form 1040 line 7 = 2000
  - `uv run pytest -m m1` -> 6 passed, 68 deselected
  - `uv run pytest` -> 71 passed, 3 skipped
  - `uv run python tools\check_ascii.py` -> ASCII check OK
- Live configured-provider `outline_first` extraction for `form_8949_2025` with bundled instructions
  -> `accepted=73`, `review=0`, `issues=0`; recovered Part I/II column (h) SUBTRACT then SUM,
  line-2 totals, line 3/10 cue nodes, and outbound declarations to Schedule D 1b/2/3/8b/9/10.
- Real cached `form_8949_2025` outline artifact check -> 0 issues; outbound targets exactly
  1b/2/3/8b/9/10.
- `pytest -m m4` -> 29 passed, 39 deselected
- `pytest` -> 66 passed, 2 skipped
- `python tools/check_ascii.py` -> ASCII check OK
- `review.html` smoke check for existing Form 8949 draft -> 418 source lines, 73 draft cards, Part
  I/II column (h), 2 transaction-table structure cards with 11 row slots each, outbound flow table,
  and Schedule D targets present.

## Resolved / superseded
- Repeatable-table addressing policy (your Open item, 2026-06-30) -> **DECIDED 2026-07-01.** Pinned
  in engineering-plan "Repeatable tables (decided)" + milestone M6b + gates row (Tandem Abacus); M1
  seam guardrail in `PHASE_M1.md`. See From Architect for the summary.
- `M4_WORKER_NOTE_FOR_CLAUDE.md` (form-only flaw) -> folded into M4 Steps 6-7 and archived.
- `M4_OUTLINE_FIRST_EXTRACTION_PROPOSAL_FOR_CLAUDE.md` -> adopted as Step 7 outline-first and
  archived.
