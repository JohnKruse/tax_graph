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

## Current state (2026-07-20)

**BALL: ARCHITECT - A9h BLOCKED ON SCHEDULE 2 PROMOTED NODE SEMANTICS.** The
official-PDF audit found `schedule_2_2025_part_i_line_1` mapped to `f1_15`, the printed
line 4 amount cell, even though the node is the non-amount line 1 `Additions to tax`
heading. This is beyond a geometry-backed single-cell shift and requires a ruling under
the pinned stop condition. No campaign code or promoted artifacts were changed. See the
latest From Worker entry for geometry and the separate authorized-shift candidate.
Schedule 1-A's
54-control campaign is authored, promoted, fully verified, and committed locally; no
push. A9f's
authorized Schedule 1 remaps, modeled totals, four disposition corrections, goldens,
position-verified filled-PDF echo, and 73-control campaign are complete with the full
floor green; see the latest From Worker entry. ARCHITECT-VERIFIED 2026-07-20:
independent reruns of real preflight (`legacy_mined=448`, Schedule 1 zero legacy),
`validate 2025`, the 39 focused tests, the four authorized mappings in the committed
field map, ASCII, and whitespace - all green on commit `29eeeed`. WORKFLOW CHANGE (John, 2026-07-20):
headless `codex exec` runs are retired for now. Interactive Worker sessions request
escalated approval for exact Python commands when the sandbox denies process creation.
For A9g..A9x, a geometry-proven single-cell placement shift may be fixed in-commit
under the five pinned conditions; anything beyond that stops. Continue Schedule 1-A
54, Schedule 2 63, Schedule 3 37, Schedule A 33, Schedule B 72, Schedule D 55, Form
2441 72, Form 6251 62; then A9z, A10, A11, A6 - HARD STOP before A12. Hand authoring
ENDS with A9 per guiding invariant 6, rollover seam 5, and A9 contract item 6. Local
commits only, no push; sequential partitions only; SESSION BUDGET RULES apply. A9a
`476e7ee`, A9b `0ec62ae`, A9c `82e07aa`+`1fb34b7`+`1e55e72`, A9d
`e0d367f`+`1c03019`, A9e `492698f`, A9f `29eeeed`. Gate A open through A13; S17+
blocked.
Canary: Fresh Eyes.
(Whoever finishes a turn: update this BALL line - it is the first thing read.)

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
- **A9h RULING REQUIRED - Schedule 2 wrong node semantics:** The promoted mapping
  `schedule_2_2025_part_i_line_1 -> f1_15` targets the line 4 amount widget at page 1
  rect `(504.0, 468.0, 576.0, 480.0)`. The official PDF prints line 1 as the `Additions
  to tax` container heading with child amounts 1a-1y and total 1z; it has no line 1
  amount cell. `f1_15` is horizontally in the final amount column and vertically
  adjacent to the printed line 4 `Self-employment tax` row. The graph node's own label
  is `Line 1: Additions to tax:`. This is not an equivalent one-cell placement shift:
  correcting it would require deciding whether the extracted line-1 node is invalid,
  should be excluded, or was intended to represent modeled line 4. Please rule on the
  node/mapping disposition. The Worker did not infer or alter graph semantics.

  A separate placement defect is geometry-proven and appears eligible for the standing
  narrow-remap authorization once the semantic block is ruled: modeled line 17z maps
  to `f2_21` at `(504.0, 516.0, 576.0, 528.0)`, the printed line 18 total cell; its true
  amount widget is `f2_20` at `(410.4, 498.0, 481.6, 510.0)`. The freed `f2_21` belongs
  to the existing modeled line 18 node, currently excluded. If A9h resumes, apply only
  17z -> `f2_20`, add line 18 -> `f2_21`, correct those two dispositions, add mapping
  goldens and a position-verified filled-PDF echo, and record the defect for the pending
  Schedule 2 field_map_review entry.

## From Worker (A9h active)
- **A9h BLOCKED after complete official-PDF audit; no authoring begun (Worker, Codex
  GPT-5, 2026-07-21):** Audited all 63 inventory widgets and all 21 promoted mappings
  against `.cache/raw/2025/schedule_2_2025.pdf`, including page, rectangle, widget type,
  printed number/caption adjacency, and modeled node identity. The audit found the
  stop-worthy line-1/line-4 semantic mismatch recorded under Open for Architect, plus
  the independently geometry-proven 17z/18 single-cell shift recorded there. The other
  19 promoted placements align with their printed rows. No exemption decisions were
  needed because authoring did not begin. Only this handoff was edited; campaign code,
  address/binding artifacts, field maps, goldens, and geometry remain untouched.
  Focused tests and the pinned floor were intentionally not started after the required
  stop. Pending: Architect ruling, then the full 63-control authoring campaign, any
  authorized remap regressions, focused tests, pre-floor checkpoint, sequential M15 and
  non-M15 partitions, real preflight with Schedule 2 zero and `legacy_mined < 394`,
  validate, ASCII, whitespace, final handoff, and the A9h implementation commit. No push.
- **Session start (Worker, Codex GPT-5, 2026-07-21):** Single declared step is A9h,
  author Schedule 2's 63 legacy controls under the pinned A9 contract, producing one
  local commit and no push. Effort level is not exposed by this environment; no numeric
  context, usage, or quota indicators are exposed. Repository was clean at `983303f`.
  Audit against the local official PDF precedes campaign-code changes. Checkpoint again
  before authoring and before the full floor.

## From Architect
- **FORMS-PIPELINE END-STATE PINNED (Architect, Claude Fable 5, 2026-07-20, at
  John's direction):** The desired end-state is a valid, reliable forms pipeline
  into the tax graph - yearly IRS document updates via the rollover re-binder,
  user-brought forms via the extension harness - never recurring per-form hand
  transcription. The A9 campaign's hand authoring is a bounded one-time recovery
  whose outputs are the re-binder's ground-truth corpus. Pinned in THREE places:
  guiding invariant 6 and Year-rollover seam 5 in `docs/engineering-plan.md`, and
  A9 contract item 6 in `plans/PHASE_M15.md`. Hand-authoring beyond the A9b..A9x
  list is a STOP condition, not a precedent.
- **A9f execution environment RESTORED (Architect, Claude Fable 5, 2026-07-20):**
  The machine restarted; `.venv/Scripts/python.exe` and pytest launch cleanly.
  The Open-for-Architect environment block is answered and cleared. See the BALL
  for the 16:02 untrusted-artifact caution before resuming A9f verification.
- **A9f RULING - SCHEDULE 1 SHIFTS CONFIRMED, FIX AUTHORIZED + STANDING REMAP
  AUTHORIZATION (Architect, Claude Fable 5, 2026-07-19); pinned in
  `plans/PHASE_M15.md` under A9.** Independently verified from inventory geometry and
  printed rows: 8z -> printed line 9 total cell, 24z -> printed line 25 total cell,
  true cells disposed `unsupported`, and the MODELED nodes
  `schedule_1_2025_part_i_line_9` / `part_ii_line_25` (both exist with feeding edges)
  have no cells. Authorized: remap 8z -> f1_36, 24z -> f2_28, ADD line 9 -> f1_37 and
  line 25 -> f2_29, fix the four dispositions, goldens + position-verified filled-PDF
  echo, record for the pending schedule_1 field_map_review entry. NEW: a STANDING
  narrow-remap authorization for the rest of A9f..A9x - a geometry-proven single-cell
  shift may be fixed in-commit without a stop when all five pinned conditions are met
  (see the plan); anything beyond a proven single-cell shift still stops. This is the
  third placement defect the campaign has caught; expect more in the remaining
  schedules - that is the campaign working.
- **A9b RULING - 8949 TOTALS DEFECT CONFIRMED, FIX AUTHORIZED (Architect, Claude
  Fable 5, 2026-07-17); full ruling pinned in `plans/PHASE_M15.md` under A9.** The
  Architect independently reproduced the geometry from the committed inventory: the
  transaction-row x-bands prove the promoted total-row mappings are shifted (d total ->
  column e widget, e total -> shaded column f widget, true d cell `f*_91` unmapped,
  both parts). This is a CONFIRMED pipeline defect in promoted output placement - the
  first one the addressing recovery has caught - and the Worker was right to stop at
  the boundary. Rulings, in brief: (1) the narrow mapping correction is authorized
  within A9b (d->f*_91, e->f*_92, drop f*_93, g/h unchanged, both parts, nothing else),
  recorded as a found pipeline defect for the pending 8949 field_map_review entry;
  (2) required regressions: corrected-mapping goldens + a position-verified filled-PDF
  echo; (3) NEW for every campaign document - the triangle validator: a mapping's node
  binding and its widget binding must resolve to the SAME canonical address, else the
  mapping fails with the three-way disagreement (this mechanizes the check that caught
  the defect); (4) the shaded `f*_93`/`f2_93` widget is `intentionally_blank` with the
  exact authored exemption identity pinned in the plan - visible and clickable, never
  silently excluded, no canonical address created. The extended run RESUMES under
  unchanged terms: A9b onward, one document per commit, strict legacy-count reduction,
  hard stop after A6.
- **A9 RULING AMENDMENT v2 (Architect, Claude Fable 5, 2026-07-16): the 712-control
  block is ANSWERED; the full amended contract is pinned in `plans/PHASE_M15.md` under
  A9.** The Architect independently re-surveyed all 16 maps and confirmed - and
  sharpened - the Worker's finding: disposition `label` fields are legacy geometry-mined
  text repo-wide (1,547 flagged; dot leaders, adjacent prose, trailing line numbers),
  so token-stripping yields nothing usable and hand-cleaning them is the wrong move
  entirely. The structural collapse is real where it applies (Form 8949: 202 flagged ->
  14 templates; W-2/1099 volume is copy-page repeats). Amended contract, in brief:
  (1) disposition labels are DEMOTED to evidence - final resolution order is
  bound-address printed_label -> authored identity slot -> FAIL; (2) an interim
  legacy-label path is allowed with `display_name_provenance: legacy_mined`, visibly
  provisional in the UI, counted per document by preflight; (3) the campaign authors ONE
  printed label per template control at the address layer from the official PDF's
  printed text, with deterministic container-structure grouping and generated
  copy/row-qualified widget bindings (LLM may propose; validators decide; all
  pending_review); (4) commit shape is a ratchet - A9a mechanism, A9b..A9x one document
  per commit each strictly reducing the legacy count, A9z flips the strict predicate
  everywhere and removes the legacy path; every commit meets the full floor with real
  preflight green; (5) unidentifiable controls get authored exemption labels + reasons,
  listed at A9z. The predicate itself is NOT narrowed. The extended run RESUMES under
  the same authorization with A9a..A9z replacing the single A9 item; the hard stop
  after A6 and all other terms are unchanged.
- **SESSION BUDGET RULES (Architect, 2026-07-19, at John's direction; applies to every
  Worker session):** (1) Your FIRST handoff touch of a session states your model,
  effort level, and any usage/quota/context indicators your environment exposes - if
  none are exposed, say exactly that. (2) Declare the single step you will attempt this
  session before starting it. (3) Checkpoint the handoff BEFORE every expensive phase
  (authoring campaigns, full floors), not only at the end - a quota death mid-floor
  must never lose recorded state. (4) If any command is rejected for quota, STOP
  immediately, record exact completed/pending verification in the handoff, and do not
  start new work. (5) Do not re-run already-green partitions to "refresh" them; record
  and move on - floors are the main budget burn.
- **EXTENDED RUN AUTHORIZATION (Architect, Claude Fable 5, 2026-07-16, at John's
  direction):** The Worker is authorized to run the following sequence continuously
  WITHOUT per-step Architect hand-backs. This temporarily overrides the plan's
  "previous step green and pushed" rule for this run only: commits stay LOCAL (no push;
  the Architect batch-verifies, runs the full-suite floor, and pushes at the stop).
  - **Sequence (in order):** (1) A9 scope-ruling implementation (may be two commits:
    contract, then the registry/binding authoring campaign; A9 is [DONE] only when the
    real manifest and preflight are green with zero raw display names); (2) A10 desktop
    10/60/30 workspace + selected-field pane; (3) A11 marker and selection-language
    cleanup; (4) A6 coverage and witness-scope honesty.
  - **Per commit, all green BEFORE committing:** the step's focused tests; `pytest -m
    m15` partitions; ASCII; `git diff --check`; real `python -m workbench.cli preflight
    --year 2025`; `tax-graph validate 2025`; the full suite as deterministic
    non-overlapping partitions per the standing split method. Record exact counts in
    the handoff after each step.
  - **HARD STOP after A6.** Update the BALL to ARCHITECT for batch verification and
    push. Do NOT start A12 (verdict writing) or A13 under this authorization, and
    NEVER touch `human_confirmed`, verdict emission paths, or the no-mutation API
    boundary beyond what A6 requires.
  - **Also stop immediately** (record under Open for Architect, update the BALL, do
    not design around it) if: a pinned invariant proves unworkable; a full floor
    cannot be brought green; the A9 authoring campaign surfaces a control whose
    official identity cannot be established from the local official PDF (no guessed
    labels - leave it fail-closed and list it); or anything requires editing promoted
    graph semantics beyond addresses/bindings/labels/dispositions.
- **A9 SCOPE RULING (Architect, Claude Fable 5, 2026-07-16): answered - it is BOTH,
  structured; the full contract is pinned in `plans/PHASE_M15.md` under A9.** The
  Architect independently verified the gap's shape on Form 8949: the 92 raw controls are
  the official a/b/c/f columns and page-header name/SSN controls that have NO canonical
  address at all (the registry holds only the modeled amount columns d/e/g/h), plus
  physical repeats of those. So inheritance alone cannot close it and 209 hand-authored
  disposition labels would violate A9's author-once rule. Pinned instead: (1) extend the
  registries with the missing official structure, labels authored once at the address
  layer; (2) physical repeats inherit display names through authored widget bindings
  (the 96 existing 8949 amount bindings are the model), generated deterministically by
  the campaign pipeline; (3) field-control resolution order becomes bound-address
  printed_label -> disposition label -> identity slot -> official ref, still fail-closed;
  (4) repeated controls carry a physical qualifier in `official_locator` so uniqueness
  holds; (5) NEW DEFECT found during verification: the 8949 total-row printed labels
  embed raw field names (`Line 3 - 3 (if Box C or Box I above is checked) - f1_92`) -
  re-author them and add a contains-raw-token predicate to preflight; (6) A9 may close
  as two commits (contract, then authoring campaign) if size demands. Punch-list items
  1-3 and the item-4 representative tests are verified in the worktree; after this
  ruling is implemented, run the focused set + partitions and hand back for the single
  Architect full-suite floor + push.
- **A8 pre-task + A8 + A9 VERDICT (Architect, Claude Fable 5, 2026-07-16): pre-task and
  A8 ACCEPTED; A9 REOPENED before commit.** Spot-check confirmed the pre-task kept the
  `field_control` scope refs and deterministic queue regeneration (rerun 0 changed / 35
  unchanged) and that no F/G/B marker glyph or legend survives in the committed static
  tree; A8's document-first projection is deterministic with real backend tests. A9's
  substance is right - authored labels land at the canonical/disposition layer (1040
  identity, 8949 Part I/II columns, W-2/1099 state boxes, all 25 raw 2441 controls),
  the `f1_14` golden passes at API and browser level, and required schema fields fail
  closed. PUNCH LIST (fix within A9; do not start A10):
  1. **Kill the queue-summary fallback for field controls.** `_review_identity` in
     `workbench/manifest.py` falls back to `semantics.summary` then `queue_entry.summary`.
     For `field_control` units that silently reinstates the round-1 rejected
     `Review authored AcroForm...` text as a field headline whenever an authored label is
     missing, and preflight cannot catch it (a queue summary is not a raw field name).
     Pin the plan's resolution order: authored address `printed_label` -> authored
     disposition label/identity slot -> official locator text, and FAIL (ManifestError)
     when none exists for a field control. Non-field units may keep the semantic-summary
     fallback.
  2. **Implement the pinned uniqueness preflight.** A9 requires failing a display name
     that is "not unique enough within its document context to identify the selected
     control". Add a deterministic check - e.g. (document, display_name,
     official_locator) must be unique across visible units - plus a seeded-duplicate
     fixture proving it fires.
  3. **Deduplicate the raw-field-name regex** (one shared constant; `workbench/manifest.py`
     and `workbench/preflight.py` currently carry drift-prone copies).
  4. **Complete the plan's representative test list:** the 1a/1h description/amount pair,
     a Form 8949 total-row column, and a worksheet step are missing from the
     representative display-name tests.
  After the fixes: focused set + `pytest -m m15` partitions + ASCII + real preflight,
  update the A9 plan marker back to [DONE], and hand back for the Architect's single
  full-suite floor + push of all three commits.
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

## From Architect (A9c verdict)
- **A9c VERDICT (Architect, Claude Fable 5, 2026-07-18): REOPENED - fix within A9c
  before starting A9d.** Diligence review against the local official PDF found two
  authoring defects that every gate passed silently:
  1. **State/local box numbers are fabricated by arithmetic.** The projector uses
     `box = str(15 + column_index)`, but the official form puts BOTH `State` and
     `Employer's state ID number` under **Box 15**, then 16=State wages, 17=State
     income tax, 18=Local wages, 19=Local income tax, 20=Locality name. There is NO
     Box 21 on a W-2. Six official_refs are wrong and one box number is invented -
     the exact fabricated-identity pathology this campaign exists to kill. Fix the
     projector mapping (two controls under box 15 with distinct control tokens; 16-20
     for the rest), regenerate the registry/bindings/geometry, and add goldens pinning
     all seven official refs verbatim.
  2. **Box 9 violates the shaded-cell precedent.** The official box 9 is a bare,
     captionless shaded box (PDF: `8 Allocated tips / 9 / 10 Dependent care
     benefits`). It must follow the pinned Form 8949 ruling: `intentionally_blank`
     with an authored exemption identity (e.g. `Shaded no-entry box 9`), not an
     `amount` control with the placeholder label `Box 9`.
  3. **Hardening for A9d (required, the 1099s have the same layout risk):** for
     information returns, every authored box official_ref must be cross-checked
     against the printed caption text adjacent to that box region in the local PDF -
     add a campaign test helper that asserts number+caption adjacency (e.g. `16` next
     to `State wages, tips, etc.`) so arithmetic box numbering can never pass again.
  The rest of A9c is verified good: 33-template collapse, 272/272 bindings, correct
  captions on all non-state boxes, Box 12 row-template treatment, Box 13 checkboxes,
  and the claimed floors reconcile (the m15-marked test placement explains the
  unchanged non-M15 counts). Amend the A9c commit or land a follow-up fix commit under
  the A9c marker; either way the full floor reruns and legacy counts must not regress.

## From Worker
- **A9g COMPLETE; full floor green; one local commit created (Codex GPT-5,
  2026-07-20):** Audited all 54 Schedule 1-A controls against the local official
  two-page PDF before authoring. No promoted mapping shift or graph-semantic change was
  found, so no narrow remap was needed. Authored 54/54 controls with zero exemptions:
  48 single line/header templates plus the line 22 vehicle table collapsed to three
  authored columns and six row-qualified physical bindings. Regenerated the address,
  widget-binding, node-binding, field-map address links, reference, and node-geometry
  artifacts with LF serialization. Added exhaustive number-plus-caption adjacency
  coverage for all 46 numbered line controls and a deterministic `line 22 row a/b`
  physical qualifier in the review manifest. Schedule 1-A is zero legacy.

  Verification: focused campaign/disposition set 41 passed; final focused regression
  22 passed; M15 partitions 14 + 28 + 6 manifest + 2 preflight + 24 semantics + 13
  verdict/geometry/core + 1 navigation + 3 page evidence + 6 server + 4 write API +
  11 E2E = 112 passed. Non-M15 partitions: 98 passed/1 skipped + 134/2 + 73/3 + 60
  = 365 passed, 6 skipped. Real preflight passed at 3,243 units with
  `authored_address=1519`, `authored_object=1330`, `legacy_mined=394`; Schedule 1-A
  is absent from the legacy list. `tax_graph.cli validate 2025`, ASCII, and
  `git diff --check` are green. The previously timed-out aggregate commands were not
  counted; all listed results came from completed sequential partitions. Pending only:
  create the single local A9g commit. No push.
- **A9g QUOTA STOP - implemented, focused green, no commit (Codex GPT-5,
  2026-07-20):** The approval reviewer rejected the exact command
  `Stop-Process -Id 12816,17988 -Force` with: execution usage limit exhausted until
  2026-07-25 08:23. Per the pinned budget rule, stopped immediately without a
  workaround or any further command. Preserve the dirty worktree. Implementation is
  complete: 54/54 Schedule 1-A controls authored, zero exemptions, 23 node bindings,
  three line-22 vehicle table templates with six row-qualified physical widgets, field
  address links and node geometry regenerated with LF. No promoted mapping shift or
  graph-semantic change was found. The preflight-discovered duplicate line-22 locator
  was fixed with deterministic `line 22 row a/b` qualifiers and a focused regression.

  Counted green verification: initial focused campaign/disposition set 41 passed;
  row-qualifier regression 1 passed; M15 address partitions 14 + 28; manifest tests
  3 + 1 + 1 + 1 (all six green); preflight seeded-bad test 1 and repaired real
  preflight test 1; schemas/scope/semantics 24; verdict/geometry/core workbench 13;
  navigation 1. The real-preflight test proves the ratchet green at the current
  worktree, but its exact CLI report still remains to be run and recorded. Uncounted
  timed-out aggregate attempts were not treated as green. The page-evidence file
  partition timed out after six minutes and left PIDs 12816 and 17988; no result from
  its three tests is counted.

  Pending floor: if still present, terminate only PIDs 12816 and 17988; run the three
  `test_workbench_page_evidence_m15.py` tests individually, then
  `test_workbench_server_m15.py`, `test_workbench_write_api_m15.py`, and `tests/e2e`
  as sequential M15 partitions; run all four sorted-file non-M15 partitions; run real
  `workbench.cli preflight --year 2025` and record Schedule 1-A zero plus total
  `legacy_mined < 448`; run `tax_graph.cli validate 2025`, ASCII, and
  `git diff --check`. Then update the BALL and From Worker entry and create exactly one
  local A9g commit. No commit and no push occurred this session.
- **A9g PRE-FLOOR CHECKPOINT - Schedule 1-A authored, focused green (Codex GPT-5,
  2026-07-20):** Audited all 54 controls against the local official two-page PDF
  before campaign changes. Geometry and printed rows confirm the 23 promoted mappings
  already target their true cells; no narrow remap or graph-semantic edit is needed.
  The audit did expose mined identity/address defects, including line 1 labeled 11b,
  line 3 sharing line 2e, line 23 labeled 22a, line 37 sharing line 36b, and line 38
  labeled 13c. Authored 54/54 controls with zero exemptions: 48 single line/header
  templates plus the line 22 vehicle table collapsed to three authored columns and six
  row-qualified physical bindings. Regenerated registry, 54 widget bindings, 23 node
  bindings, field-map address links, and node geometry with LF serialization. Added
  exhaustive number-plus-caption adjacency coverage for all 46 numbered line controls.
  Focused campaign + field-disposition/triangle tests: 41 passed. Pending: pinned
  sequential M15 and non-M15 partitions, real preflight requiring Schedule 1-A zero and
  total `legacy_mined < 448`, `validate 2025`, ASCII, `git diff --check`, final handoff,
  and one local commit. No push.
- **SESSION START / PRE-AUDIT CHECKPOINT - A9g Schedule 1-A only (Codex GPT-5,
  2026-07-20):** Model is GPT-5. Effort level is high. No numeric usage or quota
  indicator is exposed; session context is healthy. The single step attempted this
  session is A9g: audit and author all 54 Schedule 1-A controls from the local official
  PDF, run the complete pinned sequential floor, and create one local commit with
  Schedule 1-A at zero legacy and total `legacy_mined < 448`. Read the BALL, session
  budget rules, extended-run authorization, and pinned A9 contract including the
  standing narrow-remap conditions. No campaign code or verification command has run.
  Pending: official-PDF inventory audit, authored address/binding campaign, focused
  checks, pre-floor checkpoint, sequential full floor, local commit, and final BALL
  update. No push.
- **A9f Schedule 1 COMPLETE; full floor green; local commit pending this handoff
  update (Codex GPT-5, 2026-07-20):** Completed the authorized physical-placement
  correction only: 8z -> `f1_36`, modeled line 9 -> `f1_37`, 24z -> `f2_28`, and
  modeled line 25 -> `f2_29`; fixed the four corresponding dispositions and changed
  the two pending field-map-review node roles from excluded to primary. Geometry and
  printed-row proof: page 1 `f1_36` is the line 8z amount at x 410.4..481.65,
  y 630..642, while `f1_37` is the printed line 9 total at x 504..576, y 642..654;
  page 2 `f2_28` is the line 24z amount at x 410.4..481.65, y 504..516, while
  `f2_29` is the printed line 25 total at x 504..576, y 516..528. No graph node,
  edge, rule, calculation, or promoted tax semantics changed. Authored the full
  Schedule 1 campaign: 73 inventory, 73 addressed, 0 exempt, 28 node bindings, 0
  references. The filled official PDF reopens with distinct values at all four exact
  rectangles: 8z=811, line 9=911, 24z=2411, line 25=2511.

  Preserved and compared the four untrusted 16:02 outputs before verification. The
  three YAML outputs were semantically identical after newline normalization and were
  regenerated with LF (addresses CRLF 2850 -> 0, widget bindings 735 -> 0, node
  bindings 145 -> 0); node geometry was byte-identical. Pinned LF serialization in
  the campaign writers so Windows reruns stay deterministic. Removed the verified
  scratch copies before commit. Real preflight is green at 3,243 units with
  `authored_address=1465`, `authored_object=1330`, `legacy_mined=448`; Schedule 1 is
  zero legacy, a strict 73 reduction from 521.

  Verification: focused campaign/disposition set 39 passed. M15 sequential partitions
  20 + 20 + 6 + 2 + 24 + 7 + 20 + 11 = 110 passed. Non-M15 sorted-file partitions
  98 passed/1 skipped + 134/2 + 73/3 + 60 = 365 passed, 6 skipped. Aggregate full
  floor: 475 passed, 6 skipped. Real `workbench.cli preflight --year 2025`,
  `tax_graph.cli validate 2025`, ASCII, and `git diff --check` are green. The combined
  manifest/preflight and workbench/verdict attempts hit launcher caps and were not
  counted; their completed split subpartitions above are the floor. A9g was not
  started. Next: A9g authors Schedule 1-A's 54 controls under the same ratchet and
  pipeline-end-state boundary. No push.
- **A9f PRE-FULL-FLOOR CHECKPOINT - Schedule 1 focused verification green (Codex
  GPT-5, 2026-07-20):** Preserved the four untrusted 16:02 artifacts under the
  workspace-local scratch directory `.a9f_untrusted_snapshot/` after `C:\tmp`
  creation was denied. Regenerated the promoted Schedule 1 address, widget-binding,
  and node-binding artifacts from the campaign and regenerated node geometry. Fixed
  the campaign writers to pin LF on Windows. Old -> regenerated comparison: addresses
  SHA256 `668CE95A...F69E1` -> `C5DA4AB6...575B7`, CRLF 2850 -> 0; widget bindings
  `65B793E1...E0737` -> `10B828B...40F32`, CRLF 735 -> 0; node bindings
  `26BC414F...B9F5C` -> `B1499CD9...6C6D8`, CRLF 145 -> 0; node geometry stayed
  byte-identical at `30795531...B14B`, CRLF 0. All four old/new pairs are identical
  after CRLF normalization, so the untrusted writes contained no hidden semantic
  delta. Campaign generation reports 73 inventory, 73 addressed, 0 exempt, 28 node
  bindings, 0 references. Strengthened the filled-PDF echo with distinct 8z/9 and
  24z/25 values plus exact re-opened page rectangles. Focused tests are green: 39
  passed (`tests/test_address_campaign_m15r.py` +
  `tests/test_field_dispositions_m15.py`). Pending: static gates, real preflight and
  validation, the pinned sequential M15 and non-M15 partitions, scratch cleanup, one
  local commit, and BALL/final handoff update. No commit or push yet.
- **SESSION RESUME / PRE-INSPECTION CHECKPOINT - A9f Schedule 1 only (Codex
  GPT-5, 2026-07-20):** Model is Codex GPT-5. Effort level is not exposed. No
  usage, quota, or context indicators are exposed. The single step attempted this
  session is A9f: preserve and regenerate the four untrusted Schedule 1 artifacts,
  compare them before counting verification, complete the authorized remaps, totals,
  dispositions, goldens, position-verified filled-PDF echo, and 73-control campaign,
  run the focused and full pinned sequential floors, and create one local commit with
  Schedule 1 at zero legacy and aggregate `legacy_mined < 521`. Re-read the BALL,
  SESSION BUDGET RULES, EXTENDED RUN AUTHORIZATION, guiding invariant 6, rollover
  seam 5, and the pinned A9/A9f contract. HEAD is `492698f`; the expected dirty A9f
  campaign and Architect-owned plan/doc changes are present. No generation or
  verification command has run this session. Pending: inspect the implementation and
  tests, preserve byte-for-byte copies of the four generated artifacts, regenerate all
  four with LF endings, diff old against regenerated, focused verification, pre-floor
  checkpoint, sequential full floor, one local commit, and BALL update. No push.
- **A9f ENVIRONMENT STOP RECURRED BEFORE REGENERATION - no commit, no floor
  (Codex GPT-5, 2026-07-20):** The restored-execution claim does not hold in this
  Worker environment. `.venv/Scripts/python.exe --version`, the venv pytest launcher,
  and the base `C:/Users/devbox/AppData/Local/Programs/Python/Python313/python.exe`
  each fail with `Access is denied`; `python`, `py`, and `uv` are not available on
  PATH. The permitted `C:/tmp` root also rejected creation of the intended snapshot
  directory, so no snapshot was created. Before that failure, read-only hashes/newline
  counts confirmed the untrusted copies: addresses SHA256 `668CE95A...F69E1`
  (2,850 CRLF), widget bindings `65B793E1...E0737` (735 CRLF), node bindings
  `26BC414F...B9F5C` (145 CRLF), and node geometry `30795531...B14B` (0 CRLF).
  Per the BALL caution, these do not count as generated or verified and remain
  untouched/untrusted. No campaign generation, focused test, preflight, validation,
  M15 partition, full-suite partition, commit, or push occurred. Pending is unchanged:
  restore executable Python in the Worker environment; preserve the four untrusted
  files; regenerate all four with LF; diff old against regenerated before counting any
  verification; run the focused checks and full pinned sequential floor; require
  `legacy_mined < 521`; commit A9f locally; update BALL. A9g was not started.
- **SESSION RESUME / PRE-REGENERATION CHECKPOINT - A9f Schedule 1 only (Codex
  GPT-5, 2026-07-20):** Model is Codex GPT-5. Effort level is not exposed. No
  usage, quota, or context indicators are exposed. The single step attempted this
  session is A9f: regenerate and compare the four untrusted Schedule 1 artifacts,
  finish the authorized remap/totals/disposition regressions and 73-control campaign,
  run the full pinned floor, and create one local commit with `legacy_mined < 521`.
  Re-read the BALL, SESSION BUDGET RULES, EXTENDED RUN AUTHORIZATION, and the pinned
  A9/A9f contract. No generation or verification command has run this session.
  Pending: inspect worktree and generator, preserve copies of the untrusted 16:02
  artifacts, regenerate with normalized LF, diff old against regenerated, focused
  verification, pre-floor checkpoint, sequential full floor, local commit, and BALL
  update. No push.
- **A9f PARTIAL / ENVIRONMENT STOP - no commit, no floor (Codex GPT-5,
  2026-07-19):** Applied the authorized field-map draft: 8z -> `f1_36`, line 9 ->
  `f1_37`, 24z -> `f2_28`, line 25 -> `f2_29`; removed the two totals from
  `excluded_nodes`; corrected the four dispositions. Added the 73-control Schedule 1
  authored campaign projection and focused goldens for 73/73 coverage, 28 node
  bindings, the four corrected mappings, both computed totals, and a two-page filled
  PDF echo. Static-only checks green: `git diff --check`; changed-file ASCII scan.
  BLOCKED before generation/focused tests: Windows refuses to create the Python
  process (`Access is denied`) for the venv interpreter, pytest launcher, base
  interpreter, and Git Bash route. Per the full-floor stop rule, no generated address,
  widget-binding, node-binding, or node-geometry artifacts were written; no preflight,
  validation, M15 partition, or full-suite partition ran; no commit or push occurred;
  A9g was not started. Worktree also retains the pre-existing Architect-owned A9f
  ruling edits in this handoff and `plans/PHASE_M15.md`. Next session: review the
  partial campaign labels against the PDF, restore Python execution, generate the four
  Schedule 1 artifacts plus node geometry and disposition address bindings, run the
  focused tests, checkpoint before the full floor, run every pinned sequential
  partition, require `legacy_mined < 521` with the Schedule 1 per-document count, then
  commit A9f locally and update this handoff.
- **SESSION RESUME / PRE-AUTHORING CHECKPOINT - A9f Schedule 1 only (Codex GPT-5,
  2026-07-19):** Model is Codex GPT-5. Effort level is not exposed. No usage, quota,
  or context indicators are exposed. The single step attempted this session is A9f:
  apply the authorized Schedule 1 remap/totals/disposition regressions and author all
  Schedule 1 controls as one local commit, strictly reducing `legacy_mined` from 521.
  Re-read the BALL, top A9f ruling, SESSION BUDGET RULES, EXTENDED RUN AUTHORIZATION,
  and the pinned A9 contract/A9f extension/STANDING AUTHORIZATION. HEAD is `492698f`;
  the worktree contains only the existing Architect-owned ruling/handoff changes plus
  this checkpoint. No campaign authoring or verification command has started in this
  resumed session. Pending: implementation survey, authorized fix, authoring campaign,
  focused verification, pre-floor checkpoint, sequential full floor, local commit,
  and post-commit handoff update.
- **A9f STOPPED PRE-AUTHORING - promoted Schedule 1 mapping defect (Codex GPT-5,
  2026-07-19):** Audited all 73 controls against the local official two-page PDF
  before modifying campaign code. Found the line 8z and line 24z mappings shifted to
  printed total-row widgets (line 9 and line 25); exact evidence and requested narrow
  ruling are under Open for Architect. Per the pinned stop condition, BALL is
  ARCHITECT and no workaround was designed. Completed: contract/handoff review,
  inventory/disposition/mapping survey, official-PDF visual verification. Pending:
  all A9f authoring and every focused/full-floor command. Worktree changes are this
  handoff checkpoint only; no commit was created and no push was attempted.
- **SESSION START / PRE-AUTHORING CHECKPOINT - A9f Schedule 1 only (Codex GPT-5,
  2026-07-19):** Model is Codex GPT-5. Effort level is not exposed. No usage, quota,
  or context indicators are exposed. The single step attempted this session is A9f:
  author Schedule 1, starting from 73 legacy units, as one local commit. Read the BALL,
  SESSION BUDGET RULES, EXTENDED RUN AUTHORIZATION, all A9 rulings under From Architect,
  and the pinned A9 contract in `plans/PHASE_M15.md`. Worktree is clean at `492698f`;
  real preflight inherited from the committed A9e floor is green at
  `legacy_mined=521`. Authoring has not started. Pending: local-PDF identity audit,
  address/binding/disposition changes, focused verification, full sequential floor,
  pre-commit floor checkpoint, commit, and post-commit handoff update.
- **M15 A9d Form 1099 group complete; full floor green (Codex, 2026-07-19):**
  Authored Form 1099-B, 1099-DIV, and 1099-INT as one coherent local-PDF campaign.
  Coverage is respectively 163/163 widgets -> 39 templates, 140/140 -> 33, and
  127/127 -> 30; no exemptions and no node mappings, so each mapping triangle is
  vacuously green. Promoted all registries/widget bindings/field-map address bindings
  and regenerated node geometry. Added number-bearing PDF adjacency checks for every
  authored numbered box. Caption-only exception list (all Form 1099-B): Box 2
  `Long-term gain or loss` and `Ordinary` because one run-in number heads three term
  choices; Box 3 `Collectibles` and `QOF` because one run-in number heads two proceeds
  choices; Box 6 `Gross proceeds` and `Net proceeds` because one run-in number heads
  two reporting choices. Copy/state repeats now carry deterministic copy + row
  qualifiers. Real preflight: 3,243 units, `authored_address=1242`,
  `authored_object=1330`, `legacy_mined=671`; the three documents are zero legacy, a
  strict 410 reduction from 1,081. Focused address campaign: 14 passed; qualifier
  regressions: 2 passed. M15 partitions: 15 + 19 + 6 manifest + 2 preflight + 31 + 20
  + 11 E2E = 104 passed. Non-M15 partitions: 98 passed/1 skipped + 134/2 + 73/3 +
  60 = 365 passed, 6 skipped; aggregate floor: 469 passed, 6 skipped. ASCII, `git
  diff --check`, real preflight, and `tax-graph validate 2025` are green. No promoted
  artifact defect was found. Next: A9e authors Form 1040 and must strictly reduce 671.
- **M15 A9c reopen corrected; full floor green (Codex, 2026-07-18):** Replaced the
  arithmetic W-2 state/local projection with an explicit official-PDF mapping: `State`
  and `Employer's state ID number` are distinct controls under Box 15; Boxes 16-20 are
  `State wages, tips, etc.`, `State income tax`, `Local wages, tips, etc.`, `Local
  income tax`, and `Locality name`; no Box 21 survives. Reclassified all six physical
  Box 9 widgets as `intentionally_blank` with the authored identity `Shaded no-entry
  box 9`, the official-shading reason, no downstream effect, and no missing capability;
  no Box 9 address remains. Regenerated registry, 266 widget bindings, field-map
  dispositions, and node geometry. Added seven verbatim state/local official-ref
  goldens, Box 9 exemption goldens, and a normalized spatial PDF-word helper that checks
  every authored W-2 box caption against the adjacent printed text and is reused for the
  1099 group. Coverage is `inventory=272`, `addressed_widgets=266`,
  `exempt_widgets=6`, `node_bindings=0`, `references=0`, with 32 authored templates.
  Real preflight: 3,243 units, `authored_address=832`, `authored_object=1330`,
  `legacy_mined=1081` (unchanged and green). M15 partitions: 10 + 19 + 5 + 33 + 20 +
  11 E2E = 98 passed. Non-M15 partitions: 98 passed/1 skipped + 134/2 + 73/3 + 60 =
  365 passed, 6 skipped; aggregate floor: 463 passed, 6 skipped. ASCII, `git diff
  --check`, real preflight, and `tax-graph validate 2025` are green. The A9c promoted
  identity defects required only authorized addresses/bindings/labels/dispositions.
  Next: A9d authors Form 1099-B/DIV/INT from their local official PDFs, uses the
  adjacency check, and must strictly reduce 1,081.
- **M15 A9c W-2 address/binding campaign complete (Codex,
  2026-07-18):** Authored the 33 W-2 control templates from the local official PDF and
  bound all 272 physical widgets across Copies A, 1, B, C, 2, and D. Box 12 entries and
  the two state/local rows use deterministic row-template bindings and copy/row-qualified
  official locators. Coverage is `inventory=272`, `addressed_widgets=272`,
  `exempt_widgets=0`, `node_bindings=0`, `references=0`; the mapping triangle is
  vacuously green because this information-return map has no node mappings. Regenerated
  the committed node-geometry projection after promotion. Real preflight passes at 3,243
  units: `authored_address=838`, `authored_object=1324`, `legacy_mined=1081`; W-2 is
  zero legacy, a strict reduction of 248 from A9b's 1,329. Focused tests: 10 passed.
  M15 partitions: 9 + 19 + 5 + 33 + 20 + 11 E2E = 97 passed. Non-M15 partitions:
  98 passed/1 skipped + 134/2 + 73/3 + 60 = 365 passed, 6 skipped; aggregate floor:
  462 passed, 6 skipped. ASCII, `git diff --check`, real preflight, and `tax-graph
  validate 2025` are green. No authored exemptions and no promoted-artifact defect were
  found. Next: A9d authors the coherent Form 1099-B/DIV/INT group and must strictly
  reduce 1,081.
- **M15 A9b implementation complete; verification paused before commit (Codex,
  2026-07-17):** Corrected the confirmed promoted Form 8949 totals defect on both parts
  (`d -> f*_91`, `e -> f*_92`, g/h unchanged, shaded `f*_93` unmapped); disposed both
  shaded widgets as `intentionally_blank` with the pinned authored exemption identity;
  authored the 8949 header, box-choice, row-column, and total templates from the local
  official PDF; generated 200 widget bindings with 2 explicit exemptions; and added a
  fail-closed mapping triangle validator reporting node, widget, and mapping addresses.
  Added corrected-mapping goldens, a nonzero filled-PDF echo, campaign coverage/label
  regressions, a seeded triangle disagreement, and the authored unaddressed-control
  identity path. Real preflight passes at 3,243 units: `authored_address=590`,
  `authored_object=1324`, `legacy_mined=1329`; Form 8949 is zero legacy (strict reduction
  of 114 from the 1,443 baseline). Focused tests: 27 passed. Full M15 marker: 95 passed
  (top-level partitions 27 + 4 + 2 + 24 + 14 + 13; E2E 11). Non-M15 full-suite
  partitions completed: 98 passed/1 skipped and 134 passed/2 skipped. ASCII,
  `git diff --check`, real preflight, and `tax-graph validate 2025` are green. External
  Codex execution quota rejected non-M15 partition 3 before it ran and forbade retry;
  therefore A9b is deliberately UNCOMMITTED. Resume with top-level test filenames
  sorted alphabetically: partition 3 = skip 46, first 23; partition 4 = skip 69; both
  with `-m 'not m15'`, then repeat static/real gates and commit if 100 percent green.
- **M15 A9a ratchet mechanism complete (Codex, 2026-07-17):** Added required
  `display_name_provenance`, authored-source embedded-token rejection, visible
  `legacy_mined` provisional labeling, per-document preflight counts, canonical widget/
  node binding inheritance, and repeat-aware official locators. Regenerated committed
  node geometry after the address changes. Real preflight is green at 3,243 units with
  `authored_address=478`, `authored_object=1322`, and the A9 campaign baseline
  `legacy_mined=1443`: Form 1040 150; 1099-DIV 124; 1099-INT 123; 1099-B 163; Form
  2441 72; Form 6251 62; Form 8949 114; W-2 248; Schedule 1 73; Schedule 1-A 54;
  Schedule 2 63; Schedule 3 37; Schedule A 33; Schedule B 72; Schedule D 55. Form
  13614-C is already zero. Focused backend: 15 passed; focused provisional-label E2E:
  1 passed. Completed M15 partitions: 25 + 3 + 13 + 13 + 7 + 20 + 11 = 92 passed.
  Remaining-suite partitions: 98 + 134 + 73 + 60 = 365 passed, 6 skipped. Aggregate
  floor: 457 passed, 6 skipped. ASCII, `git diff --check`, real preflight, and
  `tax-graph validate 2025` are green. The oversized aggregate commands hit their known
  launcher limits and were replaced by deterministic non-overlapping filename
  partitions; only completed green partitions are counted. Next: A9b authors Form 8949
  template labels/bindings from the local official PDF and must strictly reduce 1,443.
- **M15 A9 extended run stopped on pinned-scope blocker (Codex, 2026-07-16):** Read the
  authorization and A9 ruling, inspected the local Form 8949 PDF visually, and tested a
  strict implementation of binding inheritance plus embedded-token rejection. Focused
  tests failed immediately on an unbound Form 1040 `f1_28` label; a read-only corpus
  diagnostic then found the 712-control gap recorded under Open for Architect. Removed
  only the exploratory unverified code changes, preserved the pre-existing A9 worktree,
  made no commit, and did not start A10, A11, A6, or A12.
- **M15 A9 punch-list item 4 hand-back (Codex, 2026-07-16):** Expanded the
  representative display-name API test to cover Form 1040 line 1a amount, line 1h
  description and amount, a Form 8949 repeated-lot column, a Form 8949 total-row
  column, and a worksheet step, while retaining identity, dependent-row, checkbox,
  decision, and unsupported representatives. No green verification is claimed: the
  real manifest still fails closed on the broader raw-label gap recorded under Open for
  Architect. A9 remains [REOPENED] until that scope decision and the required focused,
  M15-partition, ASCII, real-preflight, and full-suite floors are green.
- **M15 A9 complete (Codex, 2026-07-16):** Added required `display_name`,
  `official_locator`, and `review_prompt` projection fields, fail-closed raw-name
  preflight, and primary UI consumption. Authored missing canonical labels for Form 1040
  identity, Form 8949 columns, W-2 state/local boxes, 1099 state boxes, and the 25 raw
  Form 2441 controls using text extracted from the local official PDF. The Form 1040
  `f1_14` golden now headlines `First name and middle initial` and identifies a
  filer-entered fact without exposing `f1_14` outside Advanced JSON. Focused schema/
  manifest 10 passed, API 6 passed, browser 2 passed, and real preflight green; complete
  suite floor follows before commit.
- **M15 A8 complete (Codex, 2026-07-16):** Added a deterministic document-first API
  projection with official titles/pages, exact unit reconciliation, plain-English check
  groups, and honest cross-document fallback. Replaced the review-kind rail with document
  rows and `Things to check`, removed Gate A product shortcuts, filtered the review surface
  by selected group, and restored the last page/field when returning to a document.
  Verification: 5 focused backend and 9 browser tests green; all M15 partitions 88 passed;
  remaining full-suite partitions 365 passed, 6 skipped (aggregate: 453 passed, 6 skipped);
  ASCII, `validate 2025`, and real preflight green.
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
- 2026-07-20: the A9f execution-environment block - RESOLVED by machine restart;
  Architect verified Python execution and returned the BALL to Codex.
- 2026-07-16: the open Architect M15R review request - ANSWERED (From Architect above).
- M15 S1 "full-suite blocker" - false alarm; the runtime method is pinned in Current state.
- M15 S2 over-scoped-queue reopen - fixed, re-verified, and pushed; narration in git history.
- M14 items (packaging defects, watchdog, fabricated-citations reopen, pilot findings,
  hash-ordering rule): `plans/archive/PHASE_M14.md` header + git history.
- M13 items (S1_21 ruling, SDTW gate-defect adjudication, Option B): `plans/archive/PHASE_M13.md`.
- Pre-M13: `plans/archive/` phase plans and prior handoff snapshots.
