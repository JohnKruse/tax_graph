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

## Current state (2026-07-08)
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
  tier-tagged: step driver + cost metrics -> manifest growth + batch acquisition (absorbs the
  1099-B URL errand) -> example-mining endpoint repair -> batch extraction under the full
  net -> frontier-sequenced promotions (JOHN's gates; driver stops) -> oracle growth + live
  fuzz -> verification records + coverage report.
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

## Open for Architect
- (none)

## From Architect
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
