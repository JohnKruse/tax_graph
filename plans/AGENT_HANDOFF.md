# AGENT_HANDOFF.md

The single living doc for active Claude (Architect) <-> Codex (Worker) coordination. Update it in
place; do NOT spawn new per-topic note files. Standing rules: `../AGENTS.md`. Master plan:
`../docs/engineering-plan.md`.

## How to use
- **Worker:** raise questions/blocks under **Open for Architect**.
- **Architect:** answer there (and pin durable decisions into the relevant `PHASE_<id>.md`), then
  clear the item. Record active direction under **From Architect**.
- Keep it short - move resolved items to **Resolved** or delete them.
- History: pruned at each phase close (latest: 2026-07-23). Full narration lives in
  `plans/archive/` (phase plans with close notes) and git history.

## Current state (2026-07-23)

**BALL: JOHN - two items, then the M16-S4 Worker round.**
1. **GitHub Actions is blocked on account billing.** CI for `0f7ce2c` failed at job
   STARTUP with "recent account payments have failed or your spending limit needs to
   be increased" - zero steps ran; this is NOT a code failure. Fix Billing and plans,
   or make the repo public (public repos get free unlimited Actions), then
   `gh run rerun 30001728782` and watch it green. Local Tier 1 on `0f7ce2c` was fully
   green. No autonomous Worker round launches while Tier 2 is unavailable, per the
   amended commit floor.
2. **Review `plans/M16_S3_RESOLVER_REPORT.md`** - its findings define the M16-S4
   validator contracts (8949 table columns, W-2 box templates, and 13614-C wrapperless
   fields are the honest unresolved blocks awaiting a contract).

Then: Architect drafts **M16-S4** (Stream B fail-closed structural validators).

**M16 status:** ACTIVE (`plans/PHASE_M16.md`, canary Straight Line).
- **S1 [DONE] `17d2351`** - Schedule 2 Part I characterization + strict-xfail acceptance
  fixture (`tests/test_schedule_2_m16.py`). It stays xfail until regenerated artifacts land.
- **S2 [DONE] `fc2a6c1`** - Stream A extraction typing: headings become non-fillable
  concepts instead of currency form_lines, `value_type` is inferred from the printed
  control, and PDF-present totals are emitted or explicitly out-of-profile. Also fixed
  the OCR anchor split (`z` -> `1z`) that was swallowing the Schedule 2 line 1z total.
- **S3 [DONE] `0f7ce2c`** - Stream B resolver core, read-only:
  `tax_graph/output/field_identity.py` derives each control's `(line, role)` from
  qualified field-name structure, same-row wrapper inheritance, and caption adjacency -
  never geometry or label mining - and returns `unresolved` rather than guessing. Ships
  with the read-only 9-form corpus comparison report.
- **NEXT: S4** - fail-closed structural validators; then S5 corpus regeneration.

**Step ledger:** M15 S1-S16 and A1-A3 are [DONE] and pushed; M15R R1-R15 are [DONE] and
archived. M15 Gate A is PAUSED and DECOUPLED from remaining-form completion (John,
2026-07-21): it closes on the workbench plus the forms already done, and the M16 pipeline
finishes the rest into the same surface. The A9h..A9z hand campaign is RETIRED/superseded
by M16 (marked in `plans/PHASE_M15.md`); A9a-A9g (9 of 15 forms, `legacy_mined` 1443 ->
394; commits `476e7ee`, `0ec62ae`, `82e07aa`+`1fb34b7`+`1e55e72`, `e0d367f`+`1c03019`,
`492698f`, `29eeeed`, `983303f`) STAND as the regression corpus the resolver must
reproduce. A10, A11, A6 are PAUSED, not cancelled. Gate A open through A13; S17+ blocked.

**Durable context:** John's 2026-07-14 Form 1040 review exposed the label/node-id/
PDF-field-name identity defect that M15R fixed with canonical addresses. His Gate A
feedback and the all-forms scope clarification are pinned as the correction invariants in
`plans/PHASE_M15.md`; the 2026-07-16 round-2 feedback is pinned in that plan's Gate A
round-2 section. Every fillable/checkable control on every exposed form must carry exactly
one population policy and be reviewable - no undefined cells, ever.

**Project state:** M0-M14 are COMPLETE and archived (`plans/archive/`, each with a close
note). THE GRAPH COMPUTES TAX, FILES IT, AND IS STAGED TO SHIP (alpha): computation and
witnesses through M13 (line 16 under OTS + IRS adjudication over the widened Schedule D
domain; filled official PDFs; return-scoped outputs); M14 added the product surface
(installable artifacts, extension harness, intake v1). M15 (Review Workbench + review
campaign) is THE PRE-SHIP GATE. Year rollover (TY2026) stays sequenced after M15 or when
TY2026 docs drop.

- **Public-repo prep (John, 2026-07-23):** the repo is being readied to flip from private
  to public. Two independent audits (Architect + Worker) found NO secrets, keys, tokens,
  or taxpayer PII in the tree, in reachable history, or in dangling commits. Committed
  machine paths were removed from `README.md`, `AGENTS.md`, and `plans/archive/PHASE_M6.md`,
  and this handoff was pruned. Open judgment call left to John: commit-author emails remain
  in history (a rewrite would invalidate every SHA this doc cites - not recommended).
  Never include ignored local artifacts (`_drafts`, `.cache`, `output`, workbench output)
  in any archive or upload.
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
  never edit the cited graph parameter without it. (3) The form-2441 extension queue entry
  cannot derive object scope on a parity checkout (no installed extension); the live
  migration and contribution tests are GATED on `graph_ext/2025/form_2441_2025` being
  present, not fixed - it resurfaces when that review lands.
- **Standing rules (cumulative):** ASCII only (pre-push hook `.githooks/pre-push` +
  CI enforce; enable per clone with `git config core.hooksPath .githooks`); hermetic
  tests - no `_drafts` reads, no shared `build/` artifacts (tmp sqlite), and a machine
  with an installed extension IS the normal dev state (use
  `Graph(..., include_extensions=False)` for shipped-content parity); **close-out
  ordering: `frontier build` FIRST, `verify record` SECOND, commit together** (the
  content hash covers frontier.yaml); **commit floor (AMENDED v2 by John,
  2026-07-23, granular tiers): Tier 1 EVERY COMMIT = focused test FILES
  covering the changed modules + any new tests (the Worker DECLARES the
  chosen files in the handoff) + fast gates (ASCII, diff --check, validate,
  preflight); Tier 2 EVERY PUSH = full CI matrix on the pushed commit,
  Architect-watched to green; Tier 3 BIG SHAKEDOWN (full local partitions +
  fresh-checkout sim) ONLY for CI-red investigation, diffs touching promoted
  artifacts / shared surfaces (graph/, field maps, bindings, citations,
  manifest), phase closes/gates, or at John's request. Sequential pytest
  always - concurrent launches orphan children on this box**; **CI on the
  pushed commit must be green at every step commit and phase close** (watch it - do not
  skip for "docs-only" changes, the ASCII gate bites those too); live-execution passes
  for anything an outside tool/user consumes; drafts never committed; base-deps light;
  citations are verbatim-from-acquired-source ONLY - `check_citation_integrity` has
  teeth, use it (the M14 fabricated-citations reopen is the precedent); John-only
  outward actions - no agent publishes, submits, or uploads.
- **Worker environment (2026-07-23):** the recurring `Access is denied` on
  `.venv\Scripts\python.exe` was the venv launcher shim spawning the OUT-OF-WORKSPACE base
  interpreter, which the Codex sandbox denies per session (it is NOT a machine state and no
  restart fixes it). Fixed by mirroring the base interpreter to `.python313/` inside the
  repo (gitignored) and rebuilding `.venv` on it, so `pyvenv.cfg home` is in-workspace.
  Workers call `.venv\Scripts\python.exe` directly - no `uv` needed - and must use the
  workspace `.pytest_tmp` basetemp (the sandbox denies the AppData temp root). Commands
  exceeding the Worker's ~124s launcher cap (notably real preflight) are Architect-side:
  the Worker records the attempt and stops clean.
- **Recurring op note:** orphaned `serve` processes have first-class tooling -
  `tax-graph serve --sweep-orphans` (dogfooded live on a real orphan). The parent
  watchdog works on Windows as of M14 (OpenProcess probe; the os.kill(pid,0) probe was
  inert). Serve writes stderr breadcrumbs (`tax-graph serve: starting/...`) that Claude
  Desktop logs verbatim - first stop when a client-managed server dies.

## Open for Architect
- (none)

## From Architect

- **SCHEDULE 2 RULING + PIPELINE PIVOT (2026-07-21; John decided "pause campaign, fix
  pipeline") - the reason M16 exists.** Verified independently against
  `.cache/raw/2025/schedule_2_2025.fields.json` (raw AcroForm rects), MCP `get_node`, and
  citations:
  1. **CONFIRMED extraction/promotion defect, broader than one cell.** `f1_15` (page 1,
     x504-576 y468-480) is LINE 4 Self-employment tax: the PDF groups the row's controls
     under a wrapper named `Line4_ReadOrder`, and its checkboxes `c1_3/c1_4/c1_5` carry
     Form `4361`/`4029` (the SE-tax exemption boxes). Yet the field map binds `f1_15` to
     `schedule_2_2025_part_i_line_1` as `user_entered` currency - and that node is a bare
     heading (citation `cite_span_..._0004`: "- 1: Additions to tax:"). The
     mis-attribution spans the whole Part I far-right column: `f1_13` (really line 3) is
     labeled "Line 1z - line 17 ... 3"; `f1_11` is the line 1z total; the Line 4 exemption
     boxes are all labeled "Line 1". There is NO `line_1z` node though the form has one.
  2. **CONFIRMED clean single-cell shift.** Line 17z binds to `f2_21` (the line 18 total
     cell); its true amount cell is `f2_20`. Same family as the Schedule 1 8z->9 shift.
     NOT applied by hand - it rides along when the resolver reprocesses Schedule 2.
  **DECISION (John):** stop hand-authoring forms one at a time; build the structure-first
  field-identity resolver plus fail-closed structural validators. This is rollover seam 5 /
  guiding invariant 6 pulled forward, not a detour.
- **FORMS-PIPELINE END-STATE PINNED (2026-07-20, at John's direction):** the desired
  end-state is a valid, reliable forms pipeline into the tax graph - yearly IRS document
  updates via the rollover re-binder, user-brought forms via the extension harness - never
  recurring per-form hand transcription. The A9 campaign's hand authoring was a bounded
  one-time recovery whose outputs are the re-binder's ground-truth corpus. Pinned in THREE
  places: guiding invariant 6 and Year-rollover seam 5 in `docs/engineering-plan.md`, and
  A9 contract item 6 in `plans/PHASE_M15.md`. Hand-authoring beyond the retired A9 list is
  a STOP condition, not a precedent.
- **SESSION BUDGET RULES (2026-07-19, at John's direction; every Worker session):**
  (1) Your FIRST handoff touch of a session states your model, effort level, and any
  usage/quota/context indicators your environment exposes - if none are exposed, say
  exactly that. (2) Declare the single step you will attempt before starting it.
  (3) Checkpoint the handoff BEFORE every expensive phase, not only at the end - a quota
  death mid-floor must never lose recorded state. (4) If any command is rejected for quota,
  STOP immediately, record exact completed/pending verification, and do not start new work.
  (5) Do not re-run already-green partitions to "refresh" them.
- **Extension-iteration backlog (M15-adjacent, from the pilot):** one-pass `extend` on
  math-bearing forms yields honest T0 structure without passing worksheet math; the review
  loop needs an iterate/author-in-review story. Named limitation documented in
  `docs/self-serve-extension.md`.
- **M15R hardening notes (opportunistic pickup, not blockers):** (1) duplicate widget
  bindings for one `(document_id, field_name)` are caught only by the SQLite primary key at
  compile time - add the same check to `_validate_artifacts` on the YAML load path; (2)
  node-binding cardinality per role is not validated beyond role compatibility (two `value`
  bindings to one address would pass) - add a per-role cardinality validator.

## Recent rounds (condensed; full narration in git history)
- **M16-S3 (Worker Codex Luna/High headless, Architect-verified, `0f7ce2c`):** first fully
  autonomous headless round. Resolver + focused tests (7 passed, 1 strict xfail) + the
  read-only 9-form report. Worker stopped honestly at real preflight (its launcher cap);
  Architect completed that gate, fixed a CWD-relative raw-cache test guard, and pushed.
- **M16-S2 (Worker, Architect-verified, `fc2a6c1`):** Stream A typing; local not-m15
  partition 370 passed / 6 skipped / 1 xfailed; preflight unchanged at `legacy_mined=394`.
- **M16-CI (Architect, `7087d9a`):** CI had been silently RED on every push since
  2026-07-14. Root causes: the `workbench` extra (flask/werkzeug) and `workbench-dev`
  (playwright) were never synced in CI, the sqlite artifact was never built, and tests
  requiring acquired PDFs / `_drafts` / the 2441 extension were unguarded. Fixed the
  workflow and guarded every fresh-checkout-hostile test on its TRUE dependency. First
  fully green matrix since 2026-07-14.
- **M16-S1 (Worker, Architect-verified, `17d2351`):** the Schedule 2 acceptance fixture.

## Latest verification
- **M16-S3 (2026-07-23):** Tier 1 green - focused `tests/test_field_identity_m16.py` +
  `tests/test_schedule_2_m16.py` 7 passed / 1 strict xfail; ASCII; `git diff --check`;
  `validate 2025`; real preflight 3,243 units, `legacy_mined=394` (ratchet unchanged).
  Tier 2 CI BLOCKED by GitHub billing - see the BALL.
- **M16-CI (2026-07-22):** fresh-checkout sim of the exact CI sequence green with zero
  failures (m15 68 passed / 45 skipped; not-m15 356 passed / 17 skipped); local floor m15
  113 passed / 0 skipped, not-m15 366 passed / 6 skipped / 1 xfailed; CI fully green on
  `7087d9a` (all four jobs) and on `f704968`.
- **M15R close (2026-07-15):** full suite 450 passed / 6 skipped; `pytest -m m15r` 47
  passed; ASCII, `validate 2025`, throwaway SQLite build, real workbench preflight,
  frontier rebuild, and Verification Record regeneration all green. Close commit `baa6fd5`.
- Prior phase closes: `plans/archive/PHASE_M13.md` and earlier - each with a close note.

## Resolved / superseded
- 2026-07-23: the recurring Worker Python `Access is denied` - RESOLVED by the
  in-workspace interpreter rebuild (pinned under Worker environment above).
- 2026-07-23: handoff pruned from 1,198 lines for the public-repo prep; session
  checkpoints, superseded BALL entries, per-round Worker narration, and the retired A9
  rulings were removed. The A9 rulings remain pinned in `plans/PHASE_M15.md`; everything
  else lives in git history.
- 2026-07-16: the open Architect M15R review request - ANSWERED (VERDICT: ACCEPTED; the
  two hardening notes are carried under From Architect).
- M15 S1 "full-suite blocker" - false alarm. M15 S2 over-scoped-queue reopen - fixed,
  re-verified, pushed.
- M14 items (packaging defects, watchdog, fabricated-citations reopen, pilot findings,
  hash-ordering rule): `plans/archive/PHASE_M14.md` header + git history.
- M13 items (S1_21 ruling, SDTW gate-defect adjudication, Option B): `plans/archive/PHASE_M13.md`.
- Pre-M13: `plans/archive/` phase plans and prior handoff snapshots.
