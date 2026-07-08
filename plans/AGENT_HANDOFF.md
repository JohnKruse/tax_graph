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

## Open for Architect
- (none - the M10 live-acquire dilemma is ANSWERED; see "ANSWERED: live-acquire ruling"
  below and the new Step 2b in `plans/PHASE_M10.md`.)

## From Architect
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
