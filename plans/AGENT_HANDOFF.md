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

**BALL: ARCHITECT - M17-S2 (quotable cell ref) IMPLEMENTED BY THE ARCHITECT and
verified; committing/pushing. Next is the frontend (S3, John-in-the-loop, uses the
approved mockup) and the deferred S2b submit->verdict flow.** The Worker could NOT
run this round: building the real 2025 manifest exceeds its ~124s launcher cap
(exit 124) before any code - a STRUCTURAL block on Codex doing workbench rounds
that need the live manifest. The ACL fix HELD (no flask PermissionError this time).
John's env question (2026-07-24) answered: the S1 flask error was the venv-rebuild
ACL regression; re-granted `CodexSandboxUsers` read+execute on `.venv` + `.python313`
(re-run after any venv rebuild - pinned in the Worker environment note). WORKFLOW
IMPLICATION for John: while the manifest-build cap stands, backend workbench rounds
are Architect-run (or need Codex's cap raised, or a cached-manifest fixture); the
big pipeline rounds (M16-S5) remain Codex's when John gives dispositions. M17-S1 is
ACCEPTED, pushed (`66042d1`), CI-GREEN (run 30082666775).

What M17-S2 landed: `workbench/refs.py` derives a short ASCII quotable ref per unit
deterministically from the canonical address (`sch2/4/amount`, doc abbreviated
injectively, role kept so two controls on one line stay distinct); `manifest.py`
sets `unit["ref"]` on addressed units; both unit schemas gained `ref` (printable
ASCII). Real-data finding: the contract is one ref per ADDRESS, not per unit - 386
cases are the same cell reviewed under two review_kinds and correctly share a ref;
`ambiguous_refs` flags only a ref spanning two DISTINCT addresses (zero across the
live 3,243-unit manifest). Tier-1 + manifest/workbench partition + gates green;
`legacy_mined=394` unchanged.

**Superseded (kept as history):** M17-S1 ACCEPTED/pushed BALL -

**Superseded (kept as history):** M17-S1 ACCEPTED/pushed BALL - The Worker's stop was environment
only (a sandbox `PermissionError` importing flask + the 124s cap; both work in the
Architect env). Work was complete and in-boundary: `unit_reviews` added to the
session schema (optional -> backward-compatible; ASCII-only note; approved/open
enum), sessions.py helpers (approve/reopen preserve note, fail closed on unknown
unit), a derived progress summary added to the GET/PUT RESPONSE only (popped before
persist, never schema-validated), and the existing write-api test updated to match.
Architect ran the full Tier-1 floor: declared focused files 15 passed; ASCII;
diff-check; module-form validate; real preflight `legacy_mined=394` unchanged. One
commit, pushed; CI watched. M16-S5 stays PARKED behind John's dispositions from
`plans/M16_S4_VALIDATOR_REPORT.md` (the first artifact-mutating step; resumes after
the workbench lands).

**Superseded (kept as history):** M16-S4 done + park-S5 BALL -
was: M16-S4 ACCEPTED, pushed, CI-GREEN; M16-S5 deliberately not launched as the
first artifact-mutating step.
Why S5 breaks the autonomous pattern: S1-S4 were additive and read-only (new
modules, tests, reports), so the worst case was a module needing revision. S5
rewrites field maps, bindings, and addresses - the load-bearing tax data - where
a bad regeneration can silently change what a filer's form prints. It is a Tier 3
diff by John's own amended floor (promoted artifacts / shared surfaces), it will
deliberately move the preflight ratchet below `legacy_mined=394` for the first
time, and the S3/S4 reports contain judgment calls only John can make: which
unresolved blocks get a structural contract (8949 table columns, W-2 box
templates) versus an explicit out-of-profile disposition (13614-C's 297
wrapperless controls). JOHN: read `plans/M16_S4_VALIDATOR_REPORT.md` (the S5 work
list, per-document finding counts) and `plans/M16_S3_RESOLVER_REPORT.md`, then
tell the Architect the dispositions and S5 gets drafted and sequenced.
Historical note for the S4 round: The Worker's
blocker was NOT an environment failure: it ran the console script
`.venv\Scripts\tax-graph.exe`, whose editable-install `.pth` hardcodes an
absolute repo path that does not resolve inside the Codex sandbox. The module
form (`python -m tax_graph.cli` / `python -m workbench.cli`) puts CWD on
sys.path and always works - it is what every other Worker command used. The
Architect prompt said "tax-graph validate 2025", so the Architect caused it;
the invocation rule is now pinned under Worker environment below. Architect
completed the two pending gates (validate green; real preflight
`legacy_mined=394` unchanged), reviewed the diff clean against every boundary
(no promoted artifacts, no call sites in validate/preflight/manifest, S1
fixture still strict-xfail), and fixed two things inline: renamed
`structural_checks.validate_field_maps` -> `check_document_structure` (it
collided with the existing `field_maps.validate_field_maps` and would have
confused the S5 wiring; the collision came from ambiguous Architect phrasing),
and fixed an operator-precedence bug that made three evidence fallbacks
unreachable. Focused tests 10 passed / 1 strict xfail after the rename.
Standing item for John (does not block S5): review
`plans/M16_S3_RESOLVER_REPORT.md` - 8949 table columns, W-2 box templates, and
13614-C wrapperless fields are honest unresolved blocks whose contracts S4/S5
must define. Optional CI quick win, now for feedback speed rather than cost:
the per-push matrix runs three Python versions at ~40-55 min each (3.12 is
always the straggler); trimming per-push to 3.13 with the full matrix nightly,
plus caching the playwright browser download, would cut the loop substantially.

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
  **ALWAYS use the module form, never the console scripts** (2026-07-23, M16-S4):
  `.venv\Scripts\python.exe -m tax_graph.cli validate 2025` and
  `.venv\Scripts\python.exe -m workbench.cli preflight --year 2025`. The generated
  `tax-graph.exe` / `review-workbench.exe` launchers resolve the package through the
  editable install's `.pth`, which hardcodes an absolute repo path that does not resolve
  inside the Codex sandbox (`ModuleNotFoundError: No module named 'tax_graph.cli'`). The
  module form puts CWD on sys.path and works everywhere. Architects: write the module
  form into Worker prompts.
- **Recurring op note:** orphaned `serve` processes have first-class tooling -
  `tax-graph serve --sweep-orphans` (dogfooded live on a real orphan). The parent
  watchdog works on Windows as of M14 (OpenProcess probe; the os.kill(pid,0) probe was
  inert). Serve writes stderr breadcrumbs (`tax-graph serve: starting/...`) that Claude
  Desktop logs verbatim - first stop when a client-managed server dies.

## Open for Architect
- (none - the M17-S2 manifest-build launcher-cap blocker is ANSWERED: the Architect
  implemented S2 directly, see the BALL. The structural implication - Codex cannot build
  the live manifest within its ~124s cap, so backend workbench rounds are Architect-run
  until the cap is raised or a cached-manifest fixture exists - is recorded in the BALL for
  John.)
- **M17-S1 environment blocker (2026-07-24):** the split focused run passed 10
  schema/helper tests, then failed during the self-contained API fixture setup with
  `PermissionError: [Errno 13] Permission denied` importing
  `.venv\\Lib\\site-packages\\flask\\testing.py`. The earlier combined declared-file
  run exceeded the 120-second launcher cap after 7 tests and was terminated with no
  assertion failure output. Pending: rerun the new API test and the live
  `tests/test_workbench_write_api_m15.py`, then all Tier-1 gates, inspect/fix any
  failures, and make the single local commit. No commit was made.

### Worker session checkpoint - M17-S1 (2026-07-24)
- Declared step: M17-S1 per-unit review state only; backend only. Canary: Ledger Llama.
- Session-start checkpoint: model GPT-5 Codex, effort level default, and no usage/quota/context
  indicators are exposed.
- Pre-expensive-work checkpoint: M17 design and existing session/schema/server mapping read.
  Focused files declared for the Tier-1 floor: `tests/test_review_schemas_m15.py`,
  `tests/test_workbench_write_api_m15.py`, and new `tests/test_workbench_sessions_m17.py`;
  tests use the existing `m15` marker. Derived GET progress will not be persisted, and
  unknown per-unit review ids will fail closed against the queue manifest.

### Worker session checkpoint - M16-S4 (2026-07-23)
- Declared step: implement the four Stream B structural validators, focused Schedule 2 Part I
  tests, and the read-only promoted-corpus report; no validate/preflight/manifest call sites.
- Focused test files declared for the Tier-1 floor: `tests/test_structural_checks_m16.py`,
  `tests/test_field_identity_m16.py`, and `tests/test_schedule_2_m16.py` (the last remains
  strict-xfail and is not to be edited).
- Session-start checkpoint: model GPT-5 Codex, effort high, usage/quota/context indicators not
  exposed. Required handoff/phase/S3 documents read. Current worktree has only this expected
  handoff edit; implementation has not started.
- Implementation checkpoint: added `tax_graph/output/structural_checks.py` and
  `tests/test_structural_checks_m16.py`; the new focused file is green (3 passed). No promoted
  artifact, graph semantic, binding, citation, manifest, validate, or preflight call-site edit.
- Pending verification: resolver regression, unchanged strict-xfail Schedule 2 file, corpus report,
  ASCII/diff checks, `validate 2025`, and real preflight ratchet.

### Open for Architect - M16-S4 environment blocker (2026-07-23)
- Required command attempted: `.venv\\Scripts\\tax-graph.exe validate 2025`.
- Exact failure: `ModuleNotFoundError: No module named 'tax_graph.cli'` from the generated
  `.venv\\Scripts\\tax-graph.exe` launcher, despite `tax_graph\\cli.py` existing in the clone.
- Completed before the stop: `tests/test_structural_checks_m16.py` 3 passed; resolver file 6
  passed; Schedule 2 file 1 passed / 1 strict xfail; corpus report generated; ASCII and
  `git diff --check` green. No promoted artifacts or S1 fixture changed.
- Pending: required `validate 2025`, real preflight with `legacy_mined=394`, final handoff
  verification, and the single local commit. No workaround launcher was attempted after the
  environment failure, and no commit was made.

## From Architect

- **M17-S2 TASK - QUOTABLE CELL REF (Architect, Claude Opus 4.8, 2026-07-24;
  autonomous headless round, effort High).** Design in `plans/PHASE_M17.md` (S2).
  BACKEND, PROJECTION ONLY - additive to the review manifest; no authoritative
  writes, no frontend, no verdict change, no graph/promoted-artifact change.
  1. Derive a short, human-quotable REF for each manifest unit
     (`workbench/manifest.py`), deterministically from the unit's canonical
     address (`address_id`). Requirements: ASCII only (notes and citations are
     ASCII-enforced, so no middot - use `/`, `-`, or `:` separators); short and
     readable; STABLE across runs; and UNIQUE within a document. Expose it as a
     `ref` field on each unit (it then rides through the existing entry/manifest
     API and into the session/frontend later). Suggested shape, but you decide and
     state it: a document abbreviation + the line/box token + the role, e.g.
     `sch2/4/amount` or `sch2-4-amt`. When two units would collide, append the
     address's disambiguating qualifier (copy/row) rather than a bare counter, so
     the ref stays meaningful and deterministic.
  2. Enforce uniqueness: a deterministic check (test and/or a preflight predicate)
     that no two visible units in a document share a `ref`; a collision fails
     closed rather than silently emitting a dup.
  3. Tests (declare the files; `m15` marker to match the workbench suite or a new
     `m17` - your call, state it): ref is ASCII, deterministic/stable across two
     builds, unique within each document across the real 2025 manifest, and
     reconstructs from the address (not mined from labels). Reuse the pinned
     raw-cache / `_drafts` skip guards where a test needs live artifacts.
  4. Environment: the venv now grants `CodexSandboxUsers` read+execute, so Flask
     and full imports should work in your sandbox - if a `PermissionError [Errno
     13]` on a venv path recurs, record it under Open for Architect (it means the
     grant did not stick or a sandbox policy blocks it) and continue with whatever
     you can run. ALWAYS use the module form for CLIs
     (`.venv\Scripts\python.exe -m tax_graph.cli ...` /
     `... -m workbench.cli ...`), never the console scripts. `.pytest_tmp`
     basetemp; sequential pytest only; background or split anything near the ~124s
     cap and record honestly if it still cannot finish.
  Tier-1 floor before the single local commit: declared focused files green,
  ASCII, `git diff --check`, module-form `validate 2025`, and real preflight
  unchanged at `legacy_mined=394`. NOTE the manifest is a shared surface, so the
  Architect will additionally run the workbench/manifest partition at verify time -
  you are not required to. One local commit; no push. Uncommitted Architect edits
  to the handoff and `plans/PHASE_M17.md` are expected; leave them, they ride in
  your commit. Stop conditions: any need to change verdict emission, graph
  semantics, or promoted artifacts; a ref scheme that cannot be made deterministic
  AND unique; or a quota/environment failure.
- **M17-S1 TASK - PER-UNIT REVIEW STATE (Architect, Claude Opus 4.8, 2026-07-24;
  autonomous headless round, effort High).** Design + mapping are in
  `plans/PHASE_M17.md` - read it first. This round is BACKEND ONLY: the mutable
  per-cell review-state layer that the redesigned UI needs. No frontend, no
  verdict-emission change, no manifest change.
  1. Extend `schemas/session_state.schema.json` with per-unit review records. A
     `unit_reviews` collection keyed by `unit_id`, each record carrying the review
     status (approved vs open - a boolean or a small enum), a free-text `note`
     (ASCII), and an `updated_at` timestamp. Keep sessions NON-AUTHORITATIVE (they
     are resume state, not verdicts) and keep the existing fields.
  2. Update `workbench/sessions.py`: `default_session` initializes an empty
     `unit_reviews`; add small deterministic helpers to set/clear a unit's approval
     and note; preserve the atomic write and ASCII/sorted-keys serialization.
  3. Expose a DERIVED progress summary (approved count / total units for the
     document) computed on READ from `unit_reviews` against the manifest unit set -
     never stored, to avoid drift. Surface it through the session GET path (or a
     small read helper the API uses); do not add a new authoritative artifact.
  4. Round-trip through `GET/PUT /api/sessions/<queue_id>` in `workbench/server.py`
     (mostly schema + default; the PUT already validates and persists the payload).
     A note or approval for a `unit_id` not in the manifest must fail closed.
  5. Tests (mark them `m15` to match the workbench suite, or a new `m17` marker -
     your call, state it): schema accepts a valid `unit_reviews`; PUT then GET
     round-trips it; approve then reopen a unit; progress count is correct; an
     unknown `unit_id` is rejected; the note persists; nothing touches verdicts,
     the graph, or the preflight ratchet.
  DECLARE your focused test files in the handoff. Tier-1 floor: those files green,
  ASCII, `git diff --check`, module-form `validate 2025`
  (`.venv\Scripts\python.exe -m tax_graph.cli validate 2025`), and real preflight
  unchanged at `legacy_mined=394`. Use `.pytest_tmp` basetemp; sequential pytest
  only; no full partitions (Tier 2 is CI on the Architect's push). One local
  commit; no push. Stop conditions: any need to change verdict emission, the
  manifest, promoted artifacts, or graph semantics; a schema that cannot stay
  backward-compatible with existing saved sessions; or a quota/environment failure.
- **M16-S4 TASK - STREAM B FAIL-CLOSED STRUCTURAL VALIDATORS (Architect, Claude
  Opus 4.8, 2026-07-23; autonomous headless round, effort High).** Scope: the
  validators, focused tests, and a READ-ONLY corpus report. They FLAG this round;
  they are NOT wired as hard gates (see the ruling below).
  1. Implement the four structural validators from `plans/PHASE_M16.md` Stream B,
     consuming the S3 resolver (`tax_graph/output/field_identity.py`):
     a. **Heading integrity** - a heading/section/concept node may not own an
        amount cell.
     b. **Line coverage** - every printed amount line resolves to exactly one node
        OR carries an explicit out-of-profile disposition.
     c. **Total presence** - a form total present on the PDF has a node or is
        explicitly marked out-of-profile; never absent-and-unaccounted.
     d. **Line-identity triangle** - the node's bound line must equal the widget's
        resolver-derived line.
     Each finding is a structured, review-queue-shaped record (document, control,
     validator, observed vs expected, evidence) - never a silent pass and never a
     bare boolean. Suggested home: a new module (e.g.
     `tax_graph/output/structural_checks.py`) exposing a function
     `validate_field_maps` can call LATER; do not call it from there yet.
  2. **RULING - flag, do not enforce, this round.** The S3 report shows large
     honest unresolved blocks (8949 table columns, W-2 box templates, 13614-C
     wrapperless fields). Wiring these validators into `validate 2025` or preflight
     as hard failures now would red the floor on defects that S5 artifact
     regeneration is meant to fix. So: no call sites in `validate`, preflight, or
     the manifest this round; `validate 2025` and preflight must stay green and the
     ratchet must stay at `legacy_mined=394`.
  3. Focused tests with Schedule 2 Part I as the exemplar: the validators MUST flag
     today's real defects - the line-1 heading owning `f1_15`, the missing line-1z
     total node, and the far-right column line-identity mismatches. Prefer inline
     fixtures; any raw-cache read uses the ROOT-anchored skip-if-missing guard.
  4. Read-only corpus report `plans/M16_S4_VALIDATOR_REPORT.md`: run the validators
     over the promoted 2025 artifacts and count findings per document per validator,
     with exemplar rows. This is the S5 work list. Findings are FINDINGS - do not
     "fix" either side, and change no promoted artifact.
  5. Tier-1 floor per the amended standing rule: DECLARE your focused test files in
     this handoff, run them plus fast gates (ASCII, `git diff --check`,
     `validate 2025`, real preflight unchanged at `legacy_mined=394`). Use
     `.pytest_tmp` basetemp; sequential pytest only; no full partitions (Tier 2 is
     CI on the Architect's push). If a command exceeds your launcher cap, record the
     attempt and stop clean - the Architect completes it.
  6. Stop conditions: any need to touch promoted artifacts, graph semantics, or the
     M16-S1 fixture (it stays strict-xfail); a validator that cannot be made
     deterministic; or a quota/environment failure. Stop, record under Open for
     Architect, update the BALL. Exactly one local commit; no push. Session budget
     rules apply.
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
