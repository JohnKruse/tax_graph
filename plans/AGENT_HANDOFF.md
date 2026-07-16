# AGENT_HANDOFF.md

The single living doc for active Claude (Architect) <-> Codex (Worker) coordination. Update it in
place; do NOT spawn new per-topic note files. Standing rules: `../AGENTS.md`. Master plan:
`../docs/engineering-plan.md`.

## How to use
- **Worker:** raise questions/blocks under **Open for Architect**.
- **Architect:** answer there (and pin durable decisions into the relevant `PHASE_<id>.md`), then
  clear the item. Record active direction under **From Architect**.
- Keep it short - move resolved items to **Resolved** or delete them.
- History: pruned at each phase close (latest: M15R close, pruned 2026-07-16). Full narration lives in
  `plans/archive/` (phase plans with close notes) and git history.

## Current state (2026-07-16)

**BALL: WORKER/CODEX - M15 GATE A ROUND 2: A8.** The A8 pre-task is complete and ready
for its step commit; A8 is next. M15R is complete,
committed (close commit `baa6fd5`), and archived; the requested Architect review of M15R
is DONE (ACCEPTED - see From Architect, 2026-07-16). John's 2026-07-16 live review
produced Gate A round-2 feedback; the Architect cleaned `plans/PHASE_M15.md` on
2026-07-16 and it now pins the execution order **A8 pre-task (reconcile the dirty A4
worktree) -> A8 -> A9 -> A10 -> A11 -> A6 -> A12 -> A13**. A4/A5 are superseded with
their surviving invariants carried forward in the plan's round-2 section; A7 is folded
into the A13 replay. Gate A remains open through A13; S17+ stays blocked. Canary:
Fresh Eyes. (Whoever finishes a turn: update this BALL line - it is the first thing read.)

**Step ledger:** M15 S1-S16 and A1-A3 are [DONE], pushed, and marked in the plan; M15R
R1-R15 are [DONE] and archived. Per-step verification narration was pruned 2026-07-16;
it lives in git history and `plans/archive/PHASE_M15R.md`.

**Durable context:** John's 2026-07-14 Form 1040 review exposed the label/node-id/
PDF-field-name identity defect that M15R fixed with canonical addresses. His Gate A
feedback and the all-forms scope clarification are pinned as the correction invariants in
`plans/PHASE_M15.md`; the 2026-07-16 round-2 feedback is pinned in that plan's Gate A
round-2 section. Every fillable/checkable control on every exposed form must carry
exactly one population policy and be reviewable - no undefined cells, ever.

**Standing worker runtime method:** the ~10-min full suite cannot finish in one
foreground sandbox call - run it in the background or split it in half. Per step the
Worker runs `pytest -m m15` + the step's focused tests + ASCII; the Architect confirms
the full-suite floor and pushes. Never commit a step on a partial suite run.
`human_confirmed: true` is earned only through the reviewed verdict-application
pipeline; `mine-examples --confirm` remains the last soft path until S27 removes it.

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
M15 (Review Workbench + review campaign) is THE PRE-SHIP GATE and is ACTIVE per the
BALL above; the review queue below is its raw material. Year rollover (TY2026) stays
sequenced after M15 or when TY2026 docs drop.

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
- (none)

## From Architect
- **M15R review verdict + M15 plan cleanup (Architect, Claude Fable 5, 2026-07-16):**
  Reviewed `plans/archive/PHASE_M15R.md` and spot-checked `tax_graph/addressing/` per the
  open request. VERDICT: ACCEPTED; do not reopen. Address serialization is sound (typed
  components, percent-escaped ASCII tokens, parse enforces byte-for-byte canonical
  round-trip); registry validation covers duplicate ids/logical keys, parent path
  prefixes and cycles, role-kind compatibility, cross-document binding rejection, and
  per-document alias ambiguity; the contributor boundary (Form 2441 held out,
  `project_corpus: false`, no human-confirmed claim) and the 15-surface power-law
  ceiling are right. Two MINOR hardening notes for opportunistic M15 pickup, not
  blockers: (1) duplicate widget bindings for one (document_id, field_name) are caught
  only by the SQLite primary key at compile time - add the same check to
  `_validate_artifacts` on the YAML load path; (2) node-binding cardinality per role is
  not validated beyond role compatibility (two `value` bindings to one address would
  pass) - add a per-role cardinality validator. Also cleaned `plans/PHASE_M15.md` for
  round 2 (step statuses, A4/A5 supersession, pinned execution order, A8 pre-task
  dispositioning the dirty A4 worktree) and pruned this handoff. Worker may start the
  A8 pre-task now.
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
- **M15 A8 pre-task complete (Codex, 2026-07-16):** Reconciled the dirty A4 worktree
  without landing the rejected UI. Kept `field_control` disposition refs, deterministic
  queue regeneration, preflight coverage, and canonical-address selection/selected-only
  semantic-flow plumbing. Removed F/G/B marker glyphs, their text legend/styles, and tests
  or docs that pinned them. Migration rerun reported 0 changed / 35 unchanged. Verification:
  focused backend 9 passed; focused E2E 7 passed; all M15 partitions 85 passed; remaining
  full-suite partitions 365 passed, 6 skipped (aggregate full floor: 450 passed, 6 skipped);
  ASCII, `validate 2025`, and real workbench preflight all green. The monolithic M15/full
  commands exceeded 30/20 minutes after scope growth, so the complete collections were run
  as deterministic non-overlapping partitions per the standing split-suite method.
- **M15 Gate A feedback round 2 plan (Codex, 2026-07-16):** John's live review rejected the
  review-kind queue rail, bottom-stacked evidence drawer, raw-id-first field meaning, lettered
  `G` markers, and ambiguous dead queue-level verdict controls. Added A8-A13 to
  `plans/PHASE_M15.md`: document-first navigator + plain-English check groups; desktop 10/60/30
  side-by-side navigator/form/field-review layout; canonical display-name contract with an explicit
  Form 1040 `f1_14` -> `First name and middle initial` golden; one scannable evidence pane with only
  Advanced JSON secondary; non-lettered contrast markers; field-scoped Accept/Needs correction/
  Comment drafts with Submit/Cancel/Reset semantics; and a provider-agnostic, explicit revision
  request/diff loop that never mutates live graph data. Planning-only; no implementation or tests
  were run. Existing dirty A4 UI work was not modified.
- **Pruned 2026-07-16 (Architect):** per-step M15 (S1-S16, A1-A3) and M15R (R1-R15)
  worker logs moved to git history and `plans/archive/PHASE_M15R.md` close notes.

## Latest verification
- **M15R close (Worker, Codex, 2026-07-15) - ALL GREEN:** full suite 450 passed, 6
  skipped; `pytest -m m15r` 47 passed; ASCII, `validate 2025`, throwaway SQLite build,
  real workbench preflight, frontier rebuild, and Verification Record regeneration all
  green. Close commit `baa6fd5` pushed.
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
- 2026-07-16: the open Architect M15R review request - ANSWERED (From Architect above).
- M15 S1 "full-suite blocker" - false alarm; the runtime method is pinned in Current state.
- M15 S2 over-scoped-queue reopen - fixed, re-verified, and pushed; narration in git history.
- M14 items (packaging defects, watchdog, fabricated-citations reopen, pilot findings,
  hash-ordering rule): `plans/archive/PHASE_M14.md` header + git history.
- M13 items (S1_21 ruling, SDTW gate-defect adjudication, Option B): `plans/archive/PHASE_M13.md`.
- Pre-M13: `plans/archive/` phase plans and prior handoff snapshots.
