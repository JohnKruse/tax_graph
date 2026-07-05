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
  `uv --directory C:\Users\devbox\projects\tax_graph run python -m tax_graph.cli serve --year 2025`.
  A local stdio MCP client also walked the full capital-gains branch and returned 1040 line 7 =
  2000 with the 8949 SUBTRACT citation.
- Next core phase by milestone order: **M5** (Return Record, canary Future Echo). Architect should
  generate `plans/PHASE_M5.md` next. **M7** (Frontier registry + SOI-weighted coverage, Compass
  Rose - plan written, `plans/PHASE_M7.md`) is also live and may run alongside if John chooses it.
- **M5 Step 1 is done.** Added the base-runtime `tax_graph.record` model/builder, preserved fact
  provenance via `load_facts_document()` without breaking `load_facts()`, indexed graph documents /
  citations / decisions for record use, added `decision_resolutions.schema.json`, and covered
  deterministic builder output plus bad decision/option references. Next: M5 Step 2 memo renderer.

## Open for Architect
- (none open - the PHASE_M5 request is RESOLVED: `plans/PHASE_M5.md` is written, canary Future
  Echo. See From Architect.)

## From Architect
- **Next: start M5 (Return Record, canary Future Echo).** John chose the core execution order
  (2026-07-05); `plans/PHASE_M5.md` is written. State the canary, wait for John's go, then work
  the 5 steps in order. Key pins to not miss: dual-format is law (memo prose + schema-validated
  YAML; the machine NEVER parses prose); never-wrong ingestion (v0 capital-loss entry has NO
  target_node so it is non-ingestible by construction; ingestion reports rather than guesses;
  explicit facts override primed ones with a warning); injectable date/version for deterministic
  tests; record module stays base-runtime; ASCII + LF output. The loss-scenario carryforward is
  STRUCTURE-ONLY (raw net loss, positive amount, derivation caveat) - the Carryover Worksheet /
  $3000 limit is NOT modeled and must not be improvised. M7 (Compass Rose) remains live as the
  parallel track if John redirects. After M5: M6 (Twin Witness), whose just-in-time plan folds
  in `docs/oracle-strategy.md`.
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
- M5 Step 1:
  - `.\.venv\Scripts\python.exe -m pytest -m m5` -> 2 passed, 85 deselected
  - `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK
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
