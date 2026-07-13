# AGENT_HANDOFF.md

The single living doc for active Claude (Architect) <-> Codex (Worker) coordination. Update it in
place; do NOT spawn new per-topic note files. Standing rules: `../AGENTS.md`. Master plan:
`../docs/engineering-plan.md`.

## How to use
- **Worker:** raise questions/blocks under **Open for Architect**.
- **Architect:** answer there (and pin durable decisions into the relevant `PHASE_<id>.md`), then
  clear the item. Record active direction under **From Architect**.
- Keep it short - move resolved items to **Resolved** or delete them.
- History: pruned at each phase close (latest: M14 close 2026-07-12). Full narration lives in
  `plans/archive/` (phase plans with close notes) and git history.

## Current state (2026-07-13)

**BALL: WORKER - M15 S1 is DONE (Architect-verified + committed); start S2 (queue
`review_scope` migration).** The new interactive official/analog workbench is planned in
`plans/PHASE_M15.md`.

**S1 VERDICT (Architect, Opus 4.8, 2026-07-13):** sound. The review-projection schemas +
validation helper + 7 tests are good (valid fixtures pass; invalid ones fail closed on
additionalProperties/empty-units/negative-time/bad-date; schema-dir override works); ASCII
green; all four schemas valid JSON; `__init__` re-exports clean; full suite 335 passed / 6
skipped. The "M8 drill hang" was a FALSE ALARM: `test_default_drill_catalog_catches_expected_layers`
PASSES in 88.8s, the full suite is ~10 min, and the worker's 184s/304s timeouts were too
short - the "sandbox timeout, not a hang; run >=600s or split in half" note is already
pinned below. Nothing wrong with M8 or the environment.
**WORKER RUNTIME METHOD (use on EVERY step):** you cannot run the ~10-min full suite in one
foreground sandbox call. Either run it in the BACKGROUND, or SPLIT it into two halves each
under your timeout (e.g. by test-file range) and record both results. Per step, YOU run
`pytest -m m15` + the step's focused tests + `python tools/check_ascii.py`; the Architect
runs and confirms the FULL-suite floor and pushes each step after verification. Do NOT
commit a step on a partial suite run - S1's instinct to hold was correct.

**ARCHITECT REVIEW + REVISION of the M15 replan (Opus 4.8, 2026-07-13, at John's
direction):** Codex's replan captures the vision (paired official/analog panes, hover
pairing, plain-English per-op formatters, scoped review UNITS via a review-manifest,
evidence drawer, queue workflow, integrated verdicts) and preserves the integrity
constraints - accepted in substance. Three things were fixed before handing to a worker:
- **STACK CHANGED** from React/TypeScript/Vite/Playwright(npm) to **Python Flask server +
  vanilla no-build JS frontend + Python Playwright e2e**. Reason: this machine has NO
  Node/npm (verified), so the npm toolchain literally cannot build or test here; and even
  with Node it is a poor fit for GPT-5.6 Luna. Vanilla JS + Python is one-language, no
  build step, and Luna-tractable. (If John ever wants React, install Node AND use a
  stronger model for the frontend - noted in the plan.)
- **STEPS DECOMPOSED** from 8 feature-dense steps into ~30 single-purpose commits (S1-S30),
  grouped A-G, each with its own test command + acceptance, sized for a weak model. Two
  JOHN GATES remain: Gate A after the 3-case vertical slice (S16), Gate B after the
  rehearsal (S28); the human campaign is S29.
- **EXIT CRITERIA FIXED** to real CLI commands (the replan invented `tax-graph compile`,
  `verify --profile full`, `review-workbench status`, and npm targets).
Worker may start **S1 (review-manifest schemas)** now with Luna. `human_confirmed: true`
stays the one bit only a human earns - no agent path writes it (S27 closes the last soft
path, `mine-examples --confirm`). Also committed this turn: the retained `workbench/
render.py` MuPDF-stderr-noise fix, and `workbench_output/`/`.workbench_state/` gitignored.

## 2026-07-13 - M15 product reset (Codex)

- Read the handoff, current M15 plan/docs, implementation, tests, generated bundle, and
  recent commits.
- Confirmed the current output is a monolithic static page that renders forms plus full
  instruction PDFs and exposes selected data mainly as raw JSON. It lacks paired
  official/analog review, scoped review units, queue navigation, resume, and integrated
  verdict entry.
- Replaced `plans/PHASE_M15.md` with an implementation-ready plan for a local interactive
  app: official artifact left, aligned semantic analog right, hover/click pairing,
  plain-English provenance and transformations, evidence drawer, queue workflow, active
  timing, and verdict emission.
- Retained the artifact loaders, geometry/rendering primitives, and hardened verdict
  pipeline as useful infrastructure. The human campaign must not start against the
  current static bundle.
- Added two mandatory John UX gates: a three-case vertical slice before breadth work and
  a ten-entry rehearsal before the full campaign.
- No implementation code was changed. Existing dirty `workbench/render.py` and untracked
  `workbench_output/` were preserved.

**Next:** John reviews the revised plan and gives the Worker a go for Step 1. Canary:
**Fresh Eyes**.

**ARCHITECT VERIFICATION of M15 Steps 1-3 (Opus 4.8, 2026-07-13) - PASS with one
integrity fix applied inline:**
- Core invariant HELD: `apply_verdicts` (`tax_graph/review.py`) is the only writer of
  `human_confirmed: true`; verdicts are schema-validated + content-hashed (hand-edits
  rejected), append-only, and `reviewer_id in {agent,codex,worker,system}` is refused -
  an honestly-named agent CANNOT forge a confirmation.
- No-import boundary is enforced at the strictest setting (a test fails on ANY
  `tax_graph.*` import); the workbench imports zero pipeline code and re-derives page
  geometry from the `node_geometry.json` ARTIFACT itself. This DEVIATES from the plan's
  pin to reuse `resolve_node_geometry` - ACCEPTED, it is the stronger objectivity stance
  the review-workbench doc actually asks for.
- **FIX APPLIED (Architect):** `_apply_graph_review` would confirm EVERY object in a
  multi-object nodes/decisions file when a verdict carried no `object_id` and the queue
  entry had no `expected_nodes` - one click inflating a whole file's tier. Now fails
  closed (raises unless the confirmation is bounded to a specific object_id or
  expected_nodes); regression test added. `pytest -m m15` -> 10 passed.
- **SECOND FIX + PROCESS NOTE (Architect):** the M15 change to `provenance_for_node`
  (added `human_confirmed`/`human_review`) broke an M14 exact-match assertion in
  `test_self_serve_extension_m14.py`, so the Step 1-3 commits did NOT meet the commit
  floor as delivered (the worker ran `pytest -m m15` green but not the FULL suite; the
  full run showed 1 failed). Behavior is correct - the stale assert now carries the two
  new keys. STANDING REMINDER: the commit floor is the FULL suite, not the phase marker;
  a provenance/shape change ripples into other phases' exact-match tests. Architect
  re-ran the full suite before push.
- **Follow-up (pre-existing, not an M15 regression):** `verify mine-examples --confirm`
  (M6) still sets `human_confirmed: true` from a CLI flag with NO reviewer id / provenance
  / hash - weaker than the M15 verdict discipline. Route it through verdict-grade
  provenance during the campaign or as M15 cleanup; an agent invoking `--confirm` is the
  one remaining soft path to the bit.
JOHN: two things need your eye - (1) skim the M15 "Design pins" (workspace member not
separate repo; prebaked page images not pdf.js; verdicts flow OUT as files, never
edits; the confirmed/pipeline_defect/source_pathology taxonomy); (2) M15 Step 4 is
STRUCTURALLY DIFFERENT - it is YOUR human review campaign (draining the 30-object
queue, which produces the real human_minutes + escape-rate numbers), not a
worker-completable step; a Codex session builds Steps 1-3 and the instrumentation,
then hands to you. `human_confirmed: true` is the one bit only a human earns - no
agent sets it. M15 is the pre-ship gate: stable release unblocks only after it.

Prior state: M14 (Product surface, canary Open Door) is COMPLETE and archived
(`plans/archive/PHASE_M14.md`); all five steps [DONE], every exit criterion met with real
live passes. What M14 landed: serve-lifecycle hardening (parent watchdog - fixed twice on
Windows, orphan sweep dogfooded live); packaging (wheel with embedded runtime assets,
.mcpb bundle that ships the WHEEL and never source-builds, server.json, tag/dispatch
release workflow with a triple-gated inert publish job - dry run green in CI); the
self-serve extension harness (overlay + collision hard-error, gate: project|user
provenance axis end to end, content-hash no-impersonation proven by live tamper,
extend doctor/run/accept/package, form_2441 pilot accepted as an honest user-gated T0
island); and intake v1 (three additive relevance kinds with verbatim re-mined citations
from acquired sources, 90-box + 13614-C inventories enforced in validate, deterministic
local classifier over committed fixtures, fail-closed consent, intake CLI + MCP tools,
Return Record provenance). The in-app Claude Desktop live pass closed Step 2
triple-witnessed: John's chat, the Architect's pre-verified engine run, and the
Architect's direct call to the extension server (MFS loss-limit scenario:
line 16 = -4500, line 21 = -1500, 1040 line 7 = -1500).
**Next: M15 (Review Workbench + review campaign, canary Fresh Eyes) - THE PRE-SHIP
GATE, now PLANNED in `plans/PHASE_M15.md`.** The review queue below is its raw
material. Year rollover (TY2026) stays sequenced after M15 or when TY2026 docs drop.
(Whoever finishes a turn: update this BALL line - it is the first thing read.)

- **M0-M14 are COMPLETE and archived** (see `plans/archive/`, each with a close note).
- **THE GRAPH COMPUTES TAX, FILES IT, AND IS STAGED TO SHIP (alpha).** Computation and
  witnesses through M13 (line 16 under OTS + IRS adjudication over the widened Schedule D
  domain; filled official PDFs; return-scoped outputs). M14 added the product surface:
  installable artifacts, extension harness, intake v1.
- **John-only distribution checklist (post-close actions; artifacts staged + verified):**
  1. Configure PyPI trusted publishing for project `tax-graph` (repo `JohnKruse/tax_graph`,
     workflow `.github/workflows/release.yml`, environment `pypi`) at
     https://pypi.org/manage/account/publishing/, then GitHub Actions -> "Release alpha
     artifacts" -> Run workflow with `publish_pypi=true` (the ONLY route that enables the
     publish job).
  2. Download the `.mcpb` artifact from that run, install in Claude Desktop, then submit
     the tested bundle through the Connectors Directory. UX hazards to note in the
     submission and/or file as Anthropic app feedback: extensions install DISABLED with a
     tiny enable link; a config-file dev server with a near-identical name is invisible
     in the Extensions UI (twin-name collision confused testing); per-server logs record
     handshakes but not tools/call.
  3. After the PyPI release is visible: `mcp-publisher login github` then `mcp-publisher
     publish` from the repo to publish `server.json`; verify the
     `io.github.johnkruse/tax-graph` listing at registry.modelcontextprotocol.io.
- **Review queue (M15's raw material):** M10/M11 promotion entries; M12's 11
  field_map_review entries; QDCGT worksheet (high); deduction decision node (TOP); M13's
  Schedule D Tax Worksheet + line-20 decision; `extension_review_form_2441_2025`
  (accepted_local, machine_agreed: false - first review items: the two cross-gate hookup
  edges and the failed Part II math, see archived Step-3 findings A/B); 3 intake_review_*
  entries (routing/triggers/expectations). `human_minutes` stays honestly null until M15.
- **Carried-forward named gaps (M13 Option B; see `plans/archive/PHASE_M13.md` Step 4):**
  (1) PolicyEngine liability witness pending - widen `scenario_inputs_from_facts`, live PE
  over the `m6_seed1315` corpus, refreeze `pe_liability_2025.json`, re-enable the two
  skipped tests; do NOT claim dual-witness on the widened domain until then. (2)
  parameter-diff HoH top-bracket floor (626350 cited vs 375800 fixture) - source review,
  never edit the cited graph parameter without it.
- **Standing rules (cumulative):** ASCII only (pre-push hook `.githooks/pre-push` +
  CI enforce; enable per clone with `git config core.hooksPath .githooks`); hermetic
  tests - no `_drafts` reads, no shared `build/` artifacts (tmp sqlite), and a machine
  with an installed extension IS the normal dev state (use
  `Graph(..., include_extensions=False)` for shipped-content parity); **close-out
  ordering: `frontier build` FIRST, `verify record` SECOND, commit together** (the
  content hash covers frontier.yaml); full suite green is the commit floor; **CI on the
  pushed commit must be green at every step commit and phase close** (watch it - do not
  skip for "docs-only" changes, the ASCII gate bites those too); live-execution passes
  for anything an outside tool/user consumes; drafts never committed; base-deps light;
  citations are verbatim-from-acquired-source ONLY - `check_citation_integrity` has
  teeth, use it (the M14 fabricated-citations reopen is the precedent); John-only
  outward actions - no agent publishes, submits, or uploads.
- **Recurring op note:** orphaned `serve` processes now have first-class tooling -
  `tax-graph serve --sweep-orphans` (dogfooded live on a real orphan). The parent
  watchdog works on Windows as of M14 (OpenProcess probe; the os.kill(pid,0) probe was
  inert). Serve writes stderr breadcrumbs (`tax-graph serve: starting/...`) that Claude
  Desktop logs verbatim - first stop when a client-managed server dies.
- **Worker-attribution (tier metrics), M14:** Steps 1-5 implemented by Codex (GPT 5.6
  Luna, Xtra High); Architect (Opus 4.8) verified every step and fixed in-line: the
  .mcpb source-build defect + repack, the inert Windows watchdog + real-process tests,
  serve breadcrumbs, the Step-1 shared-sqlite hermetic violation, the Step-4 reopen
  (fabricated citations - Luna re-mined honestly), the parity include_extensions fix,
  and the Step-5 record-hash ordering fix. Step 2's live pass was John + Architect.

## Open for Architect
- (none) - the M15 S1 "full-suite blocker" is RESOLVED. It was NOT a hang:
  `test_default_drill_catalog_catches_expected_layers` passes in 88.8s and the full suite is
  ~10 min (335 passed / 6 skipped); the worker's 184s/304s timeouts were too short. Architect
  verified S1 and committed it. Going forward, run the full suite in the background or split
  it in two (see the BALL runtime method); the Architect confirms the full-suite floor at
  push, so the worker never needs to complete the full suite in one sandbox call.

## From Architect
- **M15 is planned (`plans/PHASE_M15.md`, 2026-07-12).** The workbench builds against the FINAL artifact shape
  (docs/review-workbench.md + M12's node-to-page geometry); the campaign drains the
  queue above and measures real `human_minutes` / escape rates; verdict outcomes
  distinguish confirmed / pipeline-defect / source-pathology per engineering-plan. It is
  the pre-ship gate: the alpha may be name-claimed on PyPI before it, but nothing is
  promoted as usable-stable until M15 passes.
- **Extension-iteration backlog (M15-adjacent, from the pilot):** one-pass `extend` on
  math-bearing forms yields honest T0 structure without passing worksheet math; the
  review loop needs an iterate/author-in-review story. Named limitation documented in
  `docs/self-serve-extension.md`.

## From Worker
- **M15 S1 (Codex, 2026-07-13):** added strict review-manifest, review-unit,
  review-expression, and session-state schemas plus artifact-only validation helpers and
  fixtures. Schema references are self-contained so direct JSON Schema validation works;
  no pipeline imports were added. Canary: Fresh Eyes. Implementation is held at S1 and
  not committed pending the full-suite floor and the M8 blocker above.
- M15 Steps 1-3: artifact-only `workbench/` with AST-enforced no-import boundary;
  read-only SQLite/geometry/queue/draft/PDF loaders; PyMuPDF build-time rasterization;
  static offline HTML with field/provenance/gap overlays; append-only hashed verdict
  emitter; and pipeline-owned `review apply-verdicts` with queue, graph provenance,
  MCP, and Verification Record tier propagation.
- Verification: `pytest -m m15` -> 9 passed; focused M15 + graph validator + MCP +
  CLI + runtime-light regression set -> 37 passed; validate and no-op apply green;
  real 2025 offline bundle built successfully. Full-suite attempts timed out after
  overlapping pytest processes from earlier tool timeouts; no assertion failure was
  observed. Re-run the full suite cleanly before phase close.
- Next action for John: run `review-workbench build --year 2025`, review the queue,
  emit one verdict per object, then run `tax-graph review apply-verdicts --year 2025`.

## Latest verification
- **M14 phase close (Architect, Opus 4.8, 2026-07-12) - ALL GREEN:**
  - Full suite in the DIRTY checkout (pilot extension installed): 318 passed, 6 skipped;
    simulated-clean (worker): 315 passed, 9 skipped (3 skips named in docs/intake.md)
  - `pytest -m m14` -> 22 passed; `validate` green (18 documents incl. intake sources);
    frontier 79 modeled / 5 declared, byte-stable; records byte-stable after the
    hash-ordering fix; ASCII green
  - Live passes: fresh-venv wheel (validate/run/build/sqlite-run + stdio MCP handshake);
    in-app Claude Desktop .mcpb install + MFS loss-limit round trip (triple-witnessed,
    dev server removed from config during the test and restored after); registry schema
    validation; release workflow CI dry run SUCCESS (publish job inert); form_2441
    extension pilot (tamper -> loud hash-mismatch failure); intake CLI example
  - Pushed-commit CI green at every step commit through `b13467e`; close commit CI
    watched on push
- Prior phase closes: `plans/archive/PHASE_M13.md` (and earlier) - each with a close note.

## Resolved / superseded
- M14 items (packaging defects, watchdog, fabricated-citations reopen, pilot findings,
  hash-ordering rule): `plans/archive/PHASE_M14.md` header + git history.
- M13 items (S1_21 ruling, SDTW gate-defect adjudication, Option B): `plans/archive/PHASE_M13.md`.
- Pre-M13: `plans/archive/` phase plans and prior handoff snapshots.
