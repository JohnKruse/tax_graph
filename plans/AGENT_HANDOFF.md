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

## Current state (2026-07-17)

**BALL: WORKER/CODEX - A9c CLOSED (ARCHITECT-HARDENED); EXTENDED RUN CONTINUES AT
A9d (1099-B/DIV/INT GROUP).** The W-2 reopen fix is verified: Box 15 carries both
State and Employer's state ID, Boxes 16-20 are pinned verbatim, Box 21 is absent, and
all six Box 9 widgets are authored `intentionally_blank` exemptions. ARCHITECT
AMENDMENT at HEAD: the caption-adjacency check was caption-only and could not catch a
fabricated box number on a correct caption (the exact A9c defect class - proven by
probe); it now matches the printed `<number> <caption>` sequence by default with an
explicit authored caption-only exception list, plus a committed regression proving
`21 Locality name` / `17 State wages` find no match. **A9d MUST use the check in this
number-bearing form for every 1099 box.** Real preflight remains green,
`legacy_mined=1081`. Continue A9d..A9x, A9z, A10, A11, A6 - HARD STOP before A12.
Local commits only, no push; sequential partitions only. A9a `476e7ee`, A9b
`0ec62ae`, A9c `82e07aa` + fix `1fb34b7` + hardening at HEAD; A8 pre-task and A8
verified (`fcf82f1`, `45e485f`, local). Gate A remains open through A13; S17+ stays
blocked. Canary: Fresh Eyes.
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
- (none)

## From Architect
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
- 2026-07-16: the open Architect M15R review request - ANSWERED (From Architect above).
- M15 S1 "full-suite blocker" - false alarm; the runtime method is pinned in Current state.
- M15 S2 over-scoped-queue reopen - fixed, re-verified, and pushed; narration in git history.
- M14 items (packaging defects, watchdog, fabricated-citations reopen, pilot findings,
  hash-ordering rule): `plans/archive/PHASE_M14.md` header + git history.
- M13 items (S1_21 ruling, SDTW gate-defect adjudication, Option B): `plans/archive/PHASE_M13.md`.
- Pre-M13: `plans/archive/` phase plans and prior handoff snapshots.
