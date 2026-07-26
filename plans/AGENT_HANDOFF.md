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

## Current state (2026-07-26)

**BALL: WORKER - M19-S3a (structured-form concept minting). Plan: `plans/PHASE_M19.md`
(S3a + the new Decisions section). Task block under From Architect.**

**Worker session checkpoint - M19-S3a (2026-07-26):** Codex, default effort; usage/quota/context
indicators are not exposed. Global canary: Ledger Llama. Single declared step: mint and promote
concept identities for the structured-form scope, demote matching addresses to placements, define
repeatable-row occurrence behavior, and surface row-template widgets in the workbench without
touching line-oriented forms, verdict emission, or graph semantics. Applicable defect-ledger
entries: D4 (tests must not write live developer state), D5 (any `workbench/` change requires
`tests/test_workbench_m15.py`), D6 (module-form CLI only), and the exact `RAN:`/`NOT RUN:` evidence
rule. D1-D3 and D7 are not expected to apply unless this scope unexpectedly changes frontend
behavior. John gave go via the current task request.

**M19-S3a implementation checkpoint (2026-07-26):** Added provider-independent structured concept
minting and promotion for 7 documents. Concept ids are path-style, flow-based, year/line/box/prose
free, and owner-qualified; printed line/box data is retained only in placement metadata. Repeated
rows carry entity-keyed occurrence metadata and concept review granularity. Promoted inventories
and address/field-map projections are generated under `graph/2025/`; line-oriented documents are
untouched. Workbench cell inventory now exposes reviewable row-template widgets while preserving
the physical-widget denominator and the 166 unaddressed coverage gaps. No verdicts, graph nodes,
or human-review claims were written.

Verification evidence:

- RAN: `$env:PYTEST_DEBUG_TEMPROOT = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\26\\019fa012-3d6f-7953-884f-ab234aac8713\\tax_graph_m19_test_tmp'; .venv\\Scripts\\python.exe -m pytest tests/test_concepts_m19.py tests/test_workbench_m15.py tests/test_workbench_identity_m19.py -q` -> 14 passed.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\26\\019fa012-3d6f-7953-884f-ab234aac8713\\tax_graph_m19_test_tmp'; .venv\\Scripts\\python.exe -m pytest tests/test_address_registry_m15r.py tests/test_address_campaign_m15r.py -q` -> 28 passed.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\26\\019fa012-3d6f-7953-884f-ab234aac8713\\tax_graph_m19_test_tmp'; .venv\\Scripts\\python.exe -m workbench.cli --year 2025 preflight` -> review preflight passed; 35 entries, 3243 units.
- RAN: `.venv\\Scripts\\python.exe tools/check_ascii.py` -> exit 0, `ASCII check OK`.
- RAN: `git diff --check` -> exit 0, no output.
- RAN: `.venv\\Scripts\\python.exe -m tax_graph.cli validate 2025` -> exit 0; graph integrity OK.
- NOT RUN: full `tests/test_review_manifest_m15.py` verification -> external-temp attempt reached 6 passed before the 600-second worker cap; the final test is unverified and is left for Architect-side/shared-partition verification.

**ARCHITECT VERIFICATION - M19-S2 (Claude Opus 5, 2026-07-26). ACCEPTED.** Reviewed the
full diff, not just the tests. The fix is real: both `enumerate` indices are gone from the
unit loops; ids are a SHA-256 over the canonical address plus a
`review_kind:role:object_type:token` qualifier, with a distinct `unit_unaddressed_` prefix
so the 166 unaddressed widgets stay visible and countable rather than papered over. The
collision guard fails closed on duplicates AND on positional patterns, and cannot
false-positive (it matches literal `ref`/`loc` tokens; a hex digest contains no `r`, `l`,
or `o`). Migration does the dangerous part correctly: a review moves only on an
exactly-one-match with an unused target, the old id is recorded in the destination's
`aliases`, and everything else lands in `orphaned_unit_reviews` with a reason and the
original id - never a silent re-point. It also correctly requires the OLD manifest, since
a positional id cannot be decoded standalone. Third clean process round running: the
Worker declared the manifest file `NOT RUN` and handed it over rather than claiming it.

**ARCHITECT-INTRODUCED REGRESSION, FOUND AND FIXED THIS ROUND.**
`tests/test_review_manifest_m15.py::test_manifest_hash_pins_every_file_in_example_artifact_directory`
failed (1 failed, 6 passed). Cause was the Architect's own `conftest.py` temp-root change,
not the Worker's work: moving the pytest temp root inside the repo makes
`_source_artifacts` relativize the example-directory paths, while the test hardcoded
absolute ones. Product behavior is correct - every file is still pinned, just spelled
repo-relative. Fixed by asserting the pinning INVARIANT rather than one path spelling.
**The Worker diagnosed this correctly and the Architect initially waved it off** as a test
assumption, reasoning that CI's 444-passing run had cleared the temp root. That reasoning
was WRONG: the test is `skipif`'d on `graph/2025/_drafts` being present, which is exactly
what a fresh CI checkout lacks, so CI has never executed it.

**SYSTEMIC GAP WORTH SIZING (for John, not blocking):** every test gated on `_drafts` or
acquired PDFs is invisible to CI and runs only on a developer machine. This class of test
can regress silently on any environment change. Worth measuring how many there are before
the review campaign leans on them.

**Worker session checkpoint - M19-S2 (2026-07-26):** John said resume via the current task
request. Model GPT-5 Codex, default effort; usage/quota/context indicators are not exposed.
Global canary: Ledger Llama. Single declared step: replace positional manifest unit ids with
identity-derived ids, mark unaddressed units without positional fallback, add fail-closed
collision checks, and implement certain migration/orphan handling for saved reviews. Focused
tests declared: `tests/test_workbench_identity_m19.py` and the mandatory `tests/test_workbench_m15.py`.
Applicable defect-ledger entries: D4 (tests must not write live developer state), D5 (any
`workbench/` change requires the boundary file), D6 (module-form CLI only), and the exact
`RAN:`/`NOT RUN:` evidence rule. D1-D3 and D7 are not exercised by this backend-only slice.

**M19-S2 implementation checkpoint (2026-07-26):** Manifest identity now derives from the
canonical address plus review kind/role/object type, with document-qualified field/object
fallbacks for unaddressed units. Units expose address status/source/qualifier and aliases;
manifest construction rejects positional ids and duplicate ids per document. Session migration
maps only a unique identity match, records the old id in destination aliases, and emits
`orphaned_unit_reviews` for missing or ambiguous matches. No graph, promoted artifact, verdict,
or live session was touched.

Verification so far:

- RAN: `$env:PYTEST_DEBUG_TEMPROOT = 'C:\\Users\\devbox\\projects\\tax_graph\\m19_test_tmp'; .venv\\Scripts\\python.exe -m pytest tests/test_workbench_identity_m19.py -q` -> 5 passed.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT = 'C:\\Users\\devbox\\projects\\tax_graph\\m19_test_tmp'; .venv\\Scripts\\python.exe -m pytest tests/test_workbench_m15.py -q` -> 4 passed.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT = 'C:\\Users\\devbox\\projects\\tax_graph\\m19_test_tmp'; .venv\\Scripts\\python.exe -m pytest tests/test_workbench_sessions_m17.py -q` -> 4 passed.
- NOT RUN: `.venv\\Scripts\\python.exe -m pytest tests/test_review_manifest_m15.py -q` -> timed out at 120 seconds after four tests; rerun with the 600-second worker cap is pending.

**M19-S2 correction checkpoint (2026-07-26):** The first real manifest run caught a collision:
repeated physical controls can share one canonical address. The identity qualifier now also
contains the stable scoped object/field token, while retaining no ref/location index. Focused
identity + session + boundary rerun is green: 13 passed. The real manifest file is the next
expensive check and remains pending after this correction.

**M19-S2 correction 2 checkpoint (2026-07-26):** The second real manifest run caught the
remaining repeated-location case: one scoped object may have multiple AcroForm locations. The
identity token now includes `official_location.locator_text` when present (the stable field name,
not a position index), and migration reconstructs it from the old location. Focused identity +
session + boundary rerun remains green: 13 passed. The real manifest file is pending again.

**M19-S2 shared-surface evidence (2026-07-26):** RAN the real manifest file under the writable
in-repository temp root -> 6 passed, 1 failed. All identity-sensitive tests passed; the one
failure was the pre-existing source-artifact path assertion, because this temp root is inside
the repository while that test expects its copied example directory to be outside the root and
therefore absolute. Rerun is pending with an external writable temp root.

**M19-S2 final verification (2026-07-26):** The external-temp rerun reached 6 passed and then
timed out at the 600-second worker cap on the final example-hash test. That file is UNVERIFIED
as a whole; no identity-sensitive test failed. The declared focused files are green:

- RAN: `$env:PYTEST_DEBUG_TEMPROOT = 'C:\\Users\\devbox\\projects\\tax_graph\\m19_test_tmp'; .venv\\Scripts\\python.exe -m pytest tests/test_workbench_identity_m19.py tests/test_workbench_m15.py tests/test_workbench_sessions_m17.py -q` -> 13 passed.
- RAN: `.venv\\Scripts\\python.exe tools/check_ascii.py` -> exit 0, `ASCII check OK`.
- RAN: `git diff --check` -> exit 0, no output.
- RAN: `.venv\\Scripts\\python.exe -m tax_graph.cli validate 2025` -> exit 0; graph integrity
  OK - all references resolve.
- NOT RUN: full `tests/test_review_manifest_m15.py` verification -> external-temp attempt
  reached 6 passed before the 600-second cap; the final test is unverified and is left for
  Architect-side/shared-partition verification.

**M19-S2 complete (2026-07-26):** The local commit contains the identity-derived manifest ids,
explicit unaddressed markers, fail-closed collision checks, schema additions, session migration
helpers, focused tests, and this evidence. No push was made. Next slice is M19-S3a, structured
form concept minting, per the corrected sequencing ruling above.

**ARCHITECT VERIFICATION - M19-S1 (Claude Opus 5, 2026-07-26). ACCEPTED.** The Worker's
round was process-clean: ledger entries named in the checkpoint, only the three specified
gates run, and an honest `NOT RUN:` for pytest with the correct reason rather than padding
the round. Report is `plans/M19_S1_CONCEPT_INVENTORY.md`; nothing was minted or mutated.
Architect re-derived the headline claim independently rather than accepting it: stripping
line/box tokens leaves form_6251 with **49 amount controls in ONE group**, schedule_1 with
`amount` x60 of 73, and form_1040 with `amount` x58 of 157.

**THE SURVEY CORRECTED THE ARCHITECT'S SEQUENCING RULING.** The Architect had ruled "M19
before M18" outright. S1 proved that holds only for STRUCTURED forms. Line-oriented forms
have NO semantic material to mint a concept from - and it is not hiding in the graph
either: node ids are line-keyed too (`form_6251_2025_part_i_line_1a`), with scraped prose
labels, some corrupt ("Line 14: 1a"). The instructions are the only machine-readable
source that names those lines, so **M18 is a PREREQUISITE for S3b, not a follow-on.**
S3 is therefore split: **S3a (structured forms, no M18 dependency - this is where the 434
hidden controls and John's SSN disambiguation land) and S3b (line-oriented, blocked on
M18).** Revised order: S2 -> S3a -> M18 -> S3b -> S4/S5 -> M16-S5.

**SECOND COVERAGE HOLE FOUND BY S1:** 166 of 1921 widgets have NO address record at all -
**form_2441 has 72 widgets and no address registry whatsoever**, schedule_b is missing 56,
and 38 more are scattered. This is a DIFFERENT set from the 434 hidden by container-kind
(one class has a container address, the other has none), so roughly 600 of 1921 widgets
are either invisible or unidentified. S2 must give the unaddressed ones stable ids without
inventing addresses; S3a owns actually authoring them.

**Worker session checkpoint - M19-S1 (2026-07-26):** John said go via the current task
request. Model GPT-5 Codex, default effort; usage/quota/context indicators are not exposed.
Single declared step: produce the read-only concept-inventory report from existing resolver,
address, and geometry data. Global canary: Ledger Llama. Applicable defect-ledger entries:
D4 (inspection/report work must not write live developer state), D6 (module-form CLI only),
and the RAN/NOT RUN rule; S1 declares no new test file. No promoted artifact, graph, verdict,
or implementation change is in scope.

**M19-S1 survey checkpoint (2026-07-26):** `node_geometry.json` contains 1,921 widgets across
16 documents. Existing address registries cover 1,755 widgets; 166 widgets have no address
record, including all 72 `form_2441_2025` widgets because that registry is absent. Removing
`line`/`box` placement tokens from current paths exposes generic collisions (`amount`/`value`)
and repeatable-table collisions (Dependents, 8949, W-2, and 1099 copies). The report will
retain those as explicit collision findings and will not mint artifacts or tests.

**M19-S1 complete (2026-07-26):** Added the read-only survey report at
`plans/M19_S1_CONCEPT_INVENTORY.md`. It records the 1,921-widget inventory, 1,755 mapped
widgets, 166 unresolved widgets, flow-shape proposals, collision classes, never-contains
findings, and the S3 work list. No promoted artifact, graph object, field map, verdict, or
session was changed. No pytest file is declared for S1 per `plans/PHASE_M19.md`.

Verification evidence:

- RAN: `.venv\Scripts\python.exe tools\check_ascii.py` -> exit 0, `ASCII check OK`.
- RAN: `git diff --check` -> exit 0, no output.
- RAN: `.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> exit 0; graph
  integrity OK - all references resolve.
- NOT RUN: pytest -> S1 is explicitly read-only and declares no new test file; testing
  starts at M19-S3 when promoted schema/artifact surfaces exist.

**JOHN'S THIRD REVIEW (2026-07-26) - THE ADDRESSING RULING.** John reviewed the live 1040
and returned four issues. Issue 1 turned out to be a real defect with a root cause that
reaches past the workbench into the addressing model, and John then ruled on the model
itself: **"The spine is the flow of the form. We shouldn't be pedantic about the line
numbers."** He also named the disambiguation case himself - "there might be 6 different
SSNs for example. Which one?" - and rejected positional numbering for repeatable rows.
This REVISES the pinned invariant "IRS line numbers are the spine" in `AGENTS.md`.

Architect verified every issue against live data before planning:
1. **The 1040 Dependents section shows ONE cell out of 41 widgets.** Not an acquisition or
   extraction failure: `node_geometry.json` has all 40 rows WITH labels authored, and the
   address inventory already carries the concepts - including
   `column=lived_with_you_more_than_half_2025`, which drives CTC, ODC, and HoH. The drop is
   `workbench/cell_inventory.py:109`, which skips any entry whose address `kind` is not
   `control`/`option`; row-template widgets carry `kind: column` and are classified as
   containers. **Corpus-wide: 434 of 1849 widgets (23%) are invisible to a reviewer -
   form_8949 is 91% hidden (184/202), form_w2 132/272, form_1040 40/199.** This is the
   worst form of the coverage-invariant breach: not an unmapped cell, an UNSEEABLE one, so
   the "159 cells" denominator was misreporting itself. NOT a one-line fix - un-skipping
   them collides all four rows onto one address and one ref.
2. Selection needs a translucent FILL plus the existing ring; the ring-only treatment the
   Architect specified in S3R2 is too subtle. (Architect's over-correction, owned.)
3. The dossier is ordered by SOURCE ARTIFACT (how the machine thinks) instead of by what a
   human reads first, and the S4 facet labels are jargon - "Obtained: not authored" is
   close to meaningless, and "no mapping authored" describes OUR pipeline state, not the
   filer's return. Both labels were the Architect's wording; owned. Correct order: printed
   label -> what the form's instructions say for that line -> governing authority quote ->
   plain-English treatment -> machine provenance collapsed. Item 2 of that list is exactly
   M18's payoff, so the dossier has a visible hole until instruction ingestion lands.
4. River cards must LEAD with the line number ("33 - Add lines 25d, 26, and 32"). The data
   is already in the ref; the card just does not front it.

**ARCHITECT FINDING THAT CHANGED THE PLAN - review identity is positionally keyed.**
`workbench/manifest.py` `_unit_id` is
`{queue_id}_ref_{ref_index:04d}_loc_{location_index:02d}_{object_id}` - literally "the Nth
thing in the queue". Insert one control upstream and every saved approval re-points to a
DIFFERENT cell. This needs no rollover to bite; it bites on the next manifest rebuild. Any
review campaign run on today's scheme is corrupt as soon as the corpus changes. Also found:
`aliases` - the schema field built for stability - is EMPTY across all 1470 addresses.

**M19 IS DRAFTED (`plans/PHASE_M19.md`)** - concept / placement / occurrence, with the
never-contains test, the owner-qualification rule, review granularity held at the CONCEPT
(so closing the 434-cell gap does not quadruple the queue), and a rollover-simulation
acceptance gate. **SEQUENCING RULING: M19 precedes BOTH M16-S5 and M18** - regenerating 605
cells or mining per-address instruction text onto an identity scheme that is about to
change means doing it twice. Three open questions for John at the end of the plan (concept
id shape, cross-document concepts, retirement policy); S1 is read-only and does not block
on them.

**Superseded (kept as history):** BALL: JOHN - M17-S3R2 + S4 ARE COMPLETE, VERIFIED, AND
PUSHED (`6488b6f`); John's live look at the workbench UI produced the third review above.

**ARCHITECT VERIFICATION + PUSH (Claude Opus 5, 2026-07-25).** Four commits pushed
(`398e4a6..6488b6f`): the Worker's three (`c421558` navigation + dossier, `c370359` D7
river scroll + D4 test isolation, `85e8155` verification record) plus the Architect's
`6488b6f`.

- **`main` HAD BEEN CI-RED since `398e4a6`** (run 30167693589, all three Python jobs) and
  nothing in this handoff recorded it. Cause: `create_app` read `artifact_bundle.graph`
  EAGERLY, so `tests/test_workbench_sessions_m17.py`'s stub-bundle fixture died with
  `AttributeError: 'object' object has no attribute 'graph'` at `server.py:257` before any
  route ran. Fixed in `6488b6f` by resolving titles/geometry/valid-ids lazily behind a memo
  - only the document-centric routes need the bundle. LESSON, same family as the M17-S2
  boundary break: `create_app` must stay cheap and lazy; anything it touches eagerly becomes
  a hard dependency for every test that builds an app.
- `6488b6f` also pins the **Worker defect ledger (D1-D7) in `AGENTS.md`** per John's
  2026-07-25 directive, plus the paired RAN/NOT RUN rule.
- Architect-side gates, all GREEN: sessions + workbench boundary (D5) + fast cells = 14
  passed; `tests/test_workbench_cells_api_m17.py` + `tests/e2e/test_workbench_v2_m17.py` =
  6 passed (319s); module-form `validate 2025` graph integrity OK; `git diff --check`;
  pre-push ASCII hook OK. **D7 is confirmed FIXED against the live 2025 projection** - the
  e2e assertion that the selected river card sits inside the river viewport, which FAILED
  last round, now passes. John's issue 1 is genuinely closed, not merely syntax-clean.
- **WORKER PROCESS NOTE - the ledger worked.** M17-S3R2b is the first round where the
  Worker fixed its own returned defect and reported honest `RAN:` / `NOT RUN:` lines rather
  than declaring a capped file verified. Keep the pattern.
- **ENV, FIXED 2026-07-25 (basetemp) - the re-grant was the WRONG fix.** Diagnosis: `--basetemp`
  makes pytest DELETE and recreate the directory every session, so a SHARED `.pytest_tmp` hands
  root ownership to whichever account ran last; no amount of re-granting survives the next
  Worker run. `.pytest_tmp` is now fully denied to devbox (cannot list, write, take ownership,
  or even read the ACL) and is unreclaimable from an unelevated shell - devbox is an admin but
  runs on a UAC-filtered token, where `BUILTIN\Administrators` is "Group used for deny only".
  FIX: stop using `--basetemp` entirely. The new root `conftest.py` sets
  `PYTEST_DEBUG_TEMPROOT` to `.test_tmp/` (gitignored), which pins the temp ROOT rather than
  the basetemp - pytest never wipes the root, and it separates the two accounts on its own via
  `.test_tmp/pytest-of-<username>/`. No flag to remember, no ACL to re-grant, one static dir.
  Verified: the same files that reported 5 ERRORS on `.pytest_tmp` are 8 passed with NO flag;
  three consecutive runs rotated `pytest-0/1/2` with the root untouched.
  LEFTOVER for John (cosmetic, NOT blocking): the dead `.pytest_tmp` directory can only be
  removed from an ELEVATED shell - `takeown /F .pytest_tmp /R /D Y` then
  `icacls .pytest_tmp /grant devbox:F /T` then delete. Nothing depends on it.
- **ENV, STILL OPEN:** the app-dependent pair takes 319s Architect-side, so John's 240s cap
  still does not cover it in one command.

## Prior state (2026-07-23)

**Worker session checkpoint - M17-S3R2 corrective step (2026-07-25):** John said go via the
current task request. Model GPT-5 Codex, effort default; usage/quota/context indicators are not
exposed. Single declared step: fix the returned D7 river-scroll defect using container-local
rectangle math, keep the Architect's e2e selector/async assertion corrections, isolate the API
session round-trip test from live developer state (D4), and run the focused verification required
by the phase. Canary: Ledger Llama. Applicable defect-ledger entries: D1-D5 and D7. Existing
uncommitted Architect edits are preserved; no verdict, graph, or promoted-artifact changes.

**Worker verification update - M17-S3R2 corrective step (2026-07-25):** D7 is fixed in
`workbench/static/river.js`; the API fixture in `tests/test_workbench_cells_api_m17.py` now uses
temporary state, page-cache, and verdict directories. Evidence:

- RAN: `.venv\Scripts\python.exe -m pytest --basetemp=.pytest_tmp tests/test_workbench_m15.py -q`
  -> 4 passed, 1 warning in 0.31s (pytest cache ACL warning only).
- RAN: `.venv\Scripts\python.exe -m tax_graph.cli validate 2025`
  -> exit 0; graph integrity OK - all references resolve.
- RAN: `.venv\Scripts\python.exe -m pytest --basetemp=.pytest_tmp
  tests/e2e/test_workbench_v2_m17.py::test_form_and_river_selection_crosses_pages_and_keeps_selection_visible -q`
  -> command timed out, exit 124 after 120.2s at the documented launcher cap; no assertion output.
- NOT RUN: `.venv\Scripts\python.exe -m pytest --basetemp=.pytest_tmp
  tests/test_workbench_cells_api_m17.py -q` -> app startup exceeds the Worker launcher cap;
  prior exact attempt exited 124 after 120 seconds, so the fixture-isolation edit is
  Architect-unverified.

Supplemental gates: ASCII check OK; `git diff --check` OK; bundled Node syntax checks passed for
`workbench/static/river.js` and `workbench/static/app.js`; no other frontend scroll offset path
uses `offsetTop`. The e2e and API files remain pending Architect-side verification; this step is
not reported as fully verified by the Worker.

**Worker verification update - runner limit raised (2026-07-25):** John raised the command
allowance to 240 seconds. The previously capped app-dependent files are now fully verified:

- RAN: `.venv\Scripts\python.exe -m pytest --basetemp=.pytest_tmp
  tests/test_workbench_cells_api_m17.py -q` -> 4 passed, 1 warning in 150.99s.
- RAN: `.venv\Scripts\python.exe -m pytest --basetemp=.pytest_tmp
  tests/e2e/test_workbench_v2_m17.py -q` -> 2 passed, 1 warning in 165.59s.

The warning in both runs is the existing pytest cache ACL warning (`WinError 5`); no test failed.
M17-S3R2 corrective verification is complete on the Worker side. The command limit should remain
at least 180 seconds for this corpus; 240 seconds gives adequate margin.

**Worker session checkpoint - M17-S3R2 + S4 (2026-07-25):** John said go via the
current task request. Model GPT-5 Codex, effort default; usage/quota/context indicators
are not exposed. Single declared step: complete S4b test partition split, then implement
S3R2 navigation/contrast and S4 citation-backed cell dossier plus focused tests, in the
order specified in `plans/PHASE_M17.md`. Canary: Ledger Llama. Worktree was clean at
start. Declared focused test files: `tests/test_workbench_cells_m17.py` (fast projection
tests), the new app-dependent cells test file from S4b, and
`tests/e2e/test_workbench_v2_m17.py`. No verdict, graph, or promoted-artifact changes.

S4b checkpoint: split the original cells test file; fast projection coverage now includes
resolved citation records, field-map disposition passthrough, and policy counts. Focused
command `.venv\\Scripts\\python.exe -m pytest --basetemp=.pytest_tmp
tests/test_workbench_cells_m17.py -q`: 6 passed. App-dependent API tests remain in
`tests/test_workbench_cells_api_m17.py` for Architect-side verification.

Frontend checkpoint: S3R2 and S4 are implemented in `workbench/static/app.js`,
`river.js`, `keyboard.js`, and `styles.css`; `cell_inventory.py` now projects citation
records, operation, disposition metadata, and per-document policy counts. Bundled Node
syntax checks for the changed modules passed; `git diff --check` passed. Fast projection
partition remains 6 passed. App-dependent API and live e2e verification are pending.

App-dependent verification attempt: `.venv\\Scripts\\python.exe -m pytest
--basetemp=.pytest_tmp tests/test_workbench_cells_api_m17.py -q` ran for 120 seconds and
exited 124 with no assertion output. This is the documented launcher-cap boundary; do not
rerun in the Worker session. Architect-side API/e2e verification remains pending.

Worker implementation complete for the declared M17-S3R2 + S4 slice. Final Worker gates:
fast projection partition 6 passed; bundled Node syntax checks passed; ASCII check OK;
`git diff --check` passed; `.venv\\Scripts\\python.exe -m tax_graph.cli validate 2025`
passed with graph integrity OK. Remaining handoff: Architect-side API/e2e verification,
then the single commit may be pushed after review. No verdict, graph, or promoted-artifact
change was made.


**ARCHITECT VERIFICATION - M17-S3R2 + S4 (Claude Opus 4.8, 2026-07-25).** Ran the
gates the Worker's ~124s cap blocked. Architect-side partition GREEN: API + fast
projection + workbench boundary = **14 passed** (2m49s), including the import-boundary
check that went CI-red on S2 - `cell_inventory.py` stayed stdlib + yaml +
`workbench.refs`.
Review of the diff: the navigation and contrast fixes are correct. `try/finally` on the
re-entrancy guard as specified; cross-page selection resolves the cell from the model and
re-renders; river scroll uses container-local `scrollTop` math so it never scrolls the
page; `.official-region.pinned` drops the red outline for a dark 3px border + 5px white
halo, and `box-sizing: border-box` is global so the border-width change does not shift
cell geometry. The citation work is the strongest part: an unresolved id is RETAINED with
`resolved: false` and null text rather than dropped or fabricated, and node-level
`citation_refs` were added alongside address-level.
**ONE GENUINE DEFECT, in the Worker's declared e2e test - the app was correct.**
`tests/e2e/test_workbench_v2_m17.py` used `cards.locator('[data-page="2"]')`, but
`data-page` is on the CARD element itself and `Locator.locator()` matches DESCENDANTS
only, so it resolved to nothing and timed out (1 failed, 1 passed). Fixed by folding the
attribute into the card selector (`#river .review-unit-card[data-page="2"]`) plus a
`wait_for` on the page-canvas instead of a bare post-click `get_attribute`. Comment left
in the test so the trap is not re-set.
**SECOND DEFECT - A REAL APP BUG, AND IT IS JOHN'S ISSUE 1 ITSELF (ledger D7).** With the
selector fixed, the e2e got further and failed on the substantive assertion: the selected
river card is NOT inside the river viewport. Root cause CONFIRMED LIVE, not inferred:
`scrollRiverUnitIntoView` computes `river.scrollTop` from `card.offsetTop`, but
`.river-list` is `position: static` and no ancestor is positioned, so `card.offsetParent`
is `<body>` and `offsetTop` carries the whole page offset. Measured on the live 1040:
`offsetParentIsRiver: false`, and selecting cards 0, 5, and 20 each overshot by a CONSTANT
~167px, leaving the card 92px ABOVE the visible area - `inView: false` every time. The bug
hides in casual use because the river DOES scroll, just to the wrong place, so John's
"hard to locate the selected cell" complaint is only partly addressed. The correct pattern
was already in the SAME commit: `scrollOfficialRegionIntoView` does proper
`getBoundingClientRect` delta math for the center pane. Fix = copy that, or give the
container `position: relative`.
**NOT FIXED BY THE ARCHITECT - RETURNED TO THE WORKER (John's directive, 2026-07-25).**
John asked that Codex be made to confront its own errors rather than have them silently
patched. So D7 is logged and this goes back for the Worker to fix. The Architect fixed ONLY
the e2e selector (D2), because that fix was needed to expose D7 at all.
**PATTERN - SECOND ROUND RUNNING.** S3 and now S3R2 both shipped an e2e file the Worker
could not execute (the cap), and both times the ONLY defects were in that unrunnable
test file while the app was correct. S4b fixed this for the projection tests; e2e is
still out of reach. RECOMMENDATION for John: until the cap is raised, e2e authorship
should be Architect-side, or the Worker should stop declaring e2e files it cannot run.
**HYGIENE FINDING (not blocking):** `tests/test_workbench_cells_api_m17.py`
`test_document_session_round_trip_and_scope` writes a real approved review into the
DEVELOPER's live session store
(`.workbench_state/2025/sessions/documents/form_1040_2025.json`). That is the source of
the phantom "1 / 159 cells approved" John saw on a fresh load of the live UI - test
residue (`note: "ok"` on `f1_01`), not a real count. Gitignored so nothing leaks into the
repo, but it crosses the hermetic-tests standing rule and pollutes the surface John
reviews. Fix next round: point the session store at a tmp dir.
**ENV NOTE:** `.pytest_tmp` now fails cleanup with `PermissionError: [WinError 5]`
(leftover Codex sandbox ACLs), which makes clean files LOOK like errors - the boundary
file reported 3 spurious errors until re-run on a different basetemp. Workers are
instructed to use `.pytest_tmp`, so this needs a re-grant.

**Superseded BALL (kept for John's four issues, which are the review checklist) - the
round is DONE and pushed at `6488b6f`; see Current state.** Was: BALL: WORKER -
M17-S3R2 + S4 (John's second-review corrections). John reviewed the
live S3R UI on 2026-07-25 and returned four issues; the design is NOT rejected - the
form-sourced cell spine stands, and every complaint is about navigation, contrast,
labeling, and data depth. Plan is written in `plans/PHASE_M17.md` (S3R2, S4, S4b, and
the parked S5-INSTR); the Worker task block is under From Architect.** Architect
verified each issue against the code before planning:
1. River does not follow form selection (`app.js` `_selectionHandler` never scrolls the
   river) AND cross-page river selection silently no-ops (`_riverSelectionHandler` bails
   at `if (!official) return;` when the cell is on another page) - John's "completely
   hosed" case. Both are small, precise frontend fixes.
2. Selection ring collides with policy color: `.official-region.policy-unsupported` is
   `var(--danger)` and `.official-region.pinned` is `outline: 3px solid #c5452d` - red on
   red. Confirmed in `styles.css:84-86`.
3. "Unsupported" is a MISLABEL, and John's instinct is correct. The generated reason
   says the control "has no authored graph, filer-fact, or decision mapping" - it is a
   COVERAGE GAP, not a statement about the filer. 605 of 1921 corpus cells carry it
   (~31%). The UI must say "no mapping authored" in those words. RULING: relabel in the
   UI only this round; do NOT rename the enum in promoted artifacts - that is Tier 3
   across 605 cells and M16-S5 regeneration is what actually fills these in. **This is
   the direct link between John's UI review and the parked M16-S5: the workbench
   EXPOSES the gap, S5 CLOSES it.**
4. The dossier is genuinely thin, and worse than John knew: `cell_inventory._citations`
   returns bare citation IDs, never the `quoted_text` the citation records already
   carry, and the UI drops `reason` / `downstream_effect` / `missing_capability` from
   the field maps entirely. S4 labels every datum and names its source artifact.
On "did you not parse the instructions": the instruction PDFs ARE acquired for 7
documents, but only ONE instruction citation exists in the promoted corpus (out of 297).
There is no systematic per-cell instruction linkage. **JOHN RULED (2026-07-25): the
instructions explain the purpose and treatment of nearly every cell, so ingesting them
is ROUTINE PIPELINE WORK, not an enhancement.** Pinned as guiding invariant 7 in
`docs/engineering-plan.md` (alongside invariant 6, the pipeline end-state). Open item is
SEQUENCING, not whether: instruction text is also the input that lets a coverage-gap
cell be RESOLVED rather than merely reported, so it should land BEFORE or WITH M16-S5
regeneration. **DRAFTED: `plans/PHASE_M18.md` (Instruction ingestion), awaiting John's
sequencing.** Survey findings already in it: 7 documents acquired with per-page markdown;
`## Line X` anchors number 73 on the 1040 but ZERO on Schedule B, so heading conventions
are not uniform and per-doc detection is required; column-break hyphenation must be
repaired before any text is quoted or citation integrity will (correctly) reject it.
Architect recommendation in the doc: run M18 S1+S2 (read-only) in parallel with the M17
workbench rounds, then land S3 immediately BEFORE M16-S5. Three sequencing questions are
listed at the end of PHASE_M18 for John.
PREREQUISITE: the S3R working tree is still UNCOMMITTED (4 new files, 10 modified);
its focused test is green (8 passed, 157s). The Architect should land S3R as the base
commit before the Worker starts, so Codex is not building on an uncommitted tree.
NOTE the ~124s cap now bites the workbench tests themselves (the cells file takes 157s
because it imports `create_app`) - S4b splits it so the Worker can verify its own work.

**Worker session checkpoint - M17-S3 frontend shell (2026-07-24):** John said go.
Model GPT-5 Codex, effort default; usage/quota/context indicators are not exposed.
Single declared step: replace the current drawer-based static UI with the approved
three-pane review shell, using existing queue, entry, page-image, and session APIs.
Submit/verdict emission remains out of scope. Canary: Ledger Llama. Worktree was
clean at start.

Implementation checkpoint: replaced the drawer UI with the M17 three-pane shell in
`workbench/static/index.html`, `styles.css`, `app.js`, and new `river.js`; added
session load/save calls in `static/api.js`; the shell receives the local write token
from `workbench/server.py` for non-authoritative session persistence; added
`tests/e2e/test_workbench_v2_m17.py` under the new `m17` marker. Submit/verdict
emission remains untouched.

Verification: bundled Node syntax checks for `app.js`, `river.js`, and `api.js`
passed; ASCII, `git diff --check`, and module-form `validate 2025` passed. A
temporary cached-manifest preview with preflight monkeypatched passed 1 UI test,
including river selection and approve state. The real focused e2e partition hit
the documented launcher cap (exit 124; no assertion failure output), after the
cheaper session/ref command had emitted 8 passing dots before the same cap. The
cached manifest preview also exposes pre-existing `invalid_display_name` preflight
findings, so the real M17 e2e and real preflight are still pending. No commit yet.

**ARCHITECT VERIFICATION (Claude Opus 4.8, 2026-07-24) - GREEN, HOLDING FOR JOHN.**
Ran the two Architect-side gates the Worker's ~124s cap blocked:
- Real preflight (2m18s): PASSED, 3,243 units, `legacy_mined=394` (ratchet
  UNCHANGED). The `invalid_display_name` findings were a STALE CACHED-MANIFEST
  artifact, not a real defect - the freshly built manifest is clean, so
  `create_app`'s startup preflight passes and the e2e fixture builds the app.
- Real m17 e2e against the live 2025 projection: 1 passed, AFTER fixing two
  genuine defects in the Worker's declared test file (`tests/e2e/
  test_workbench_v2_m17.py`) - the app itself was correct in both:
  1. `cards.first()` / `card = cards.first()` - Playwright sync `Locator.first`
     is a PROPERTY, not a method (`TypeError: 'Locator' object is not callable`).
  2. `#river-detail .drawer-heading` asserted synchronously right after the
     select click, but `renderDetail` awaits `loadEvidence` before appending the
     heading - a race. Fixed with a `wait_for()` on the heading. (Sidenote: the
     first `object_ref` on addressed units is an `address`, which the evidence
     endpoint does not resolve, so it 404s and is caught gracefully - the heading
     still renders. Not a bug, but a frontend efficiency question for John.)
Remaining Tier-1 floor all GREEN: workbench boundary + write-api + m17 session
partition 12 passed (incl. the import-boundary check that bit M17-S2); ASCII;
`git diff --check`; module-form `validate 2025` (graph integrity OK). Diff is
in-boundary: `server.py` only serves the shell with the injected local write
token and wires session GET/PUT; no verdict, graph, or promoted-artifact change.
NOT committed: S3 is John-in-the-loop (approved mockup) - awaiting John's review
of the actual UI before the single commit + push.

**Superseded BALL (history only - the live BALL is at the top of this file):** BALL:
ARCHITECT - M17-S2 (quotable cell ref) IMPLEMENTED BY THE ARCHITECT and
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
`legacy_mined=394` unchanged. NOTE: the first S2 push (`2103037`) went CI-RED on
`test_workbench_has_no_pipeline_imports` - `refs.py` imported `tax_graph.addressing`,
violating the workbench/pipeline decoupling. Fixed forward (`eeb5a73`) with a
stdlib-only address reader; ref behavior unchanged. LESSON (Tier-1 refinement):
a change under `workbench/` should run `tests/test_workbench_m15.py` locally (fast
architectural/boundary tests) in addition to the manifest partition - the manifest
partition does not exercise the import-boundary check. Verifying commit at HEAD is
`eeb5a73`; CI watched.

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
  Workers call `.venv\Scripts\python.exe` directly - no `uv` needed. **UPDATED 2026-07-25: do
  NOT pass `--basetemp` any more.** The root `conftest.py` pins the temp root to `.test_tmp/`
  for every account, and pytest separates accounts automatically via
  `.test_tmp/pytest-of-<username>/`. The old `.pytest_tmp` is poisoned and unreclaimable; see
  the hard rule in `AGENTS.md`. **CAP RAISED TO 600s (John, 2026-07-26; was ~124s, then 240s)** -
  the Worker now runs its OWN e2e and app-dependent files (the full pair measured 319s). Only
  full partitions and Tier 3 shakedowns stay Architect-side. Anything that still does not fit
  gets an honest `NOT RUN:` line, never a guess.
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
- **RESOLVED 2026-07-26 by the 600s cap:** the manifest-build blocker that made backend
  workbench rounds Architect-run is GONE. Codex can now build the live manifest (~150s) and
  run its own app-dependent and e2e files. The two workflow rulings that existed only because
  of the old cap are RETIRED: (a) "backend workbench rounds are Architect-run", and (b) "e2e
  authorship should be Architect-side, or the Worker should stop declaring e2e files it cannot
  run". Workers own their e2e again, and are expected to run it. No cached-manifest fixture is
  needed.
- **RESOLVED (kept as history) - M17-S1 environment blocker (2026-07-24):** the venv ACL
  grant fixed the flask `PermissionError`, the 600s cap retired the launcher-cap half, and
  the pending work below was completed and pushed long ago. Nothing here is open. Was: the
  split focused run passed 10
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

- **M19-S3a TASK - CONCEPT MINTING FOR STRUCTURED FORMS (Architect, Claude Opus 5,
  2026-07-26).** Design in `plans/PHASE_M19.md` (S3a + the Decisions section, which is new
  and answers the three formerly-open questions). Read it, the revised spine invariant, and
  the Worker defect ledger in `AGENTS.md`; name applicable ledger entries in your
  checkpoint. **D5 applies: any `workbench/` change runs `tests/test_workbench_m15.py`.**
  Cap is 600s; you run your own app-dependent files. Tests ARE required this round.
  **SCOPE - STRUCTURED FORMS ONLY. Do NOT touch line-oriented forms** (6251, Schedules
  1/1-A/2/3/A/B/D, or the ~58 bare `amount` controls on the 1040). M19-S1 proved they have
  no semantic material to mint from, and M18 is their prerequisite. In scope: the 1040
  Dependents table, 8949 transaction columns, W-2 boxes and Box 12 rows, 1099-DIV/INT/B
  copies and state/local rows, schedule_1a's repeatable rows, and the
  `section=identity` singletons.
  1. **Mint concept ids** per the decided shape: path style
     (`form_1040/dependents/dependent/ssn`), enforcing BOTH rules with a validator, not by
     convention - the never-contains test (no line numbers, no years, no printed prose)
     and owner/role qualification (a bare `ssn` is never an address; the four dependent
     SSNs collapsing onto one address is the exemplar John raised).
  2. **Author the concept inventory as a promoted artifact** and demote the matching
     address records to PLACEMENTS carrying `concept_id` plus the printed line/box token.
     Keep `logical_key` as the compatibility bridge and populate `aliases` from it -
     `aliases` is currently empty across all 1470 addresses and is the mechanism that
     makes this survivable.
  3. **Occurrence contract for repeatable rows.** Row identity is the ENTITY, never the
     slot index. Define it so the four Dependents rows are occurrences of one concept.
     **Review granularity stays at the CONCEPT** - one review per column, with row widgets
     rendered as instances. Closing this gap must NOT multiply the review queue.
  4. **Fix `workbench/cell_inventory.py:109`** so row-template widgets surface as
     instances instead of being dropped as containers. Acceptance: the 434 previously
     hidden controls become visible and counted (8949 184/202, w2 132/272, 1040 40/199,
     1099-DIV/INT/B 24 each, schedule_1a 6), the 1040 Dependents table is fully
     reviewable, and the per-document cell counts rise by exactly that delta - explained,
     not drifting.
  5. **The 166 unaddressed widgets are OUT OF SCOPE for authoring** but must not regress.
     form_2441 (72, no registry at all) and schedule_b (56) stay reported as coverage
     gaps. Do not invent addresses for them.
  6. Cross-document facts use a `same_fact_as` edge; do not unify concepts across
     documents. Retired concepts stay in the inventory marked with the year they left.
  Tier-1 floor: declared focused files green with honest `RAN:`/`NOT RUN:` lines, ASCII,
  `git diff --check`, module-form `validate 2025`, real preflight. **This round DOES touch
  promoted artifacts, so it is Tier 3** - the Architect runs full local partitions and the
  manifest/workbench partition at verify time; expect the preflight ratchet to be
  discussed rather than assumed unchanged, and report `legacy_mined` explicitly rather
  than asserting it held. Run pytest plainly - no `--basetemp`. ONE local commit; no push.
  Stop conditions: any need to touch line-oriented forms, verdict emission, or graph
  semantics; a concept that cannot satisfy both minting rules (report it, do not force
  it); a citation whose text would change under re-keying (it must not); or a
  quota/environment failure.

- **[DONE `7b3f873`, Architect-verified] M19-S2 TASK - KILL THE POSITIONAL unit_id
  (Architect, Claude Opus 5, 2026-07-26).**
  Design in `plans/PHASE_M19.md` (S2) - read it, plus the revised spine invariant and the
  Worker defect ledger in `AGENTS.md`; name the applicable ledger entries in your
  session-start checkpoint. **D5 applies directly this round: a change under `workbench/`
  MUST run `tests/test_workbench_m15.py` locally** - it carries the import-boundary check
  that went CI-red on M17-S2. Your cap is 600s, so you run your own app-dependent files.
  **THIS ROUND DOES NEED TESTS.** John's "another set of tests is premature" applied to
  S1, where concept ids were an unaccepted proposal. S2 changes real backend behavior that
  review state depends on, so it is tested normally.
  **The bug:** `workbench/manifest.py` `_unit_id` builds
  `{queue_id}_ref_{ref_index:04d}_loc_{location_index:02d}_{object_id}` - the id means
  "the Nth thing in the queue". Insert one control upstream and every saved approval in
  `unit_reviews` silently re-points to a DIFFERENT cell. No rollover needed; it bites on
  the next manifest rebuild.
  1. Replace the derivation with a deterministic function of the unit's IDENTITY, not its
     position: `address_id` plus the review-kind/role qualifier needed to keep the 386
     known same-address/two-review-kind pairs distinct (the M17-S2 ref finding - one ref
     per ADDRESS, not per unit). **Key on `address_id`, NOT `concept_id`** - concepts do
     not exist until S3. Write it so the input can be swapped to `concept_id` later
     without changing the shape.
  2. **Units with no address (166 of 1921 widgets - all 72 of form_2441, 56 of schedule_b,
     and 38 others).** They still need an id and must NOT get a positional one. Derive
     from a stable within-year property (the AcroForm `field_name` is the obvious
     candidate) and MARK the unit as unaddressed so the gap stays visible and countable.
     Do not silently synthesize an address.
  3. **Fail-closed checks:** no two units in a document may share an id, and no id may
     contain a positional index. A collision fails closed rather than emitting a dup.
  4. **Migration - the dangerous part. Never silently re-point an existing review.** Old
     saved sessions key on positional ids. Where an old id can be mapped to its new one
     with certainty, migrate it and record the old key in `aliases`. Where it cannot,
     mark that review ORPHANED and surface it for re-review. A wrong mapping moves a human
     approval onto the wrong cell, which is worse than losing it. Fail closed.
  5. Boundary: `workbench/` must stay free of pipeline imports (stdlib + yaml +
     `workbench.refs` only). `workbench/refs.py` already has a stdlib address reader -
     reuse it rather than importing `tax_graph.addressing`.
  6. Verdicts are OUT OF SCOPE: `review_verdict.schema.json` keys on `object_ref`, not
     `unit_id`, so no emitted verdict changes. Do not touch verdict emission.
  Tests to declare and RUN (600s cap - these are yours): the workbench boundary file
  `tests/test_workbench_m15.py` (D5), plus focused coverage for determinism across two
  manifest builds, uniqueness within a document, the no-positional-index check, the
  unaddressed-unit path, and the migrate/orphan behavior. Honest `RAN:`/`NOT RUN:` lines
  for every declared file.
  Tier-1 floor: declared files green, ASCII, `git diff --check`, module-form
  `validate 2025`, real preflight unchanged at `legacy_mined=394`. The manifest is a
  SHARED SURFACE, so the Architect additionally runs the manifest/workbench partition at
  verify time. Run pytest plainly - do NOT pass `--basetemp`. Sequential pytest only.
  ONE local commit; no push.
  Stop conditions: any need to touch promoted artifacts, graph semantics, or verdict
  emission; a unit whose id cannot be made deterministic AND unique without a positional
  fallback (report it, do not paper over it); an old review that cannot be mapped with
  certainty (orphan it, do not guess); or a quota/environment failure.

- **[DONE `e17345b`, Architect-verified] M19-S1 TASK - CONCEPT INVENTORY AND FLOW-SPINE
  DERIVATION, READ-ONLY (Architect,
  Claude Opus 5, 2026-07-26).** Design in `plans/PHASE_M19.md` - READ IT FIRST, along with
  the revised spine invariant in `AGENTS.md` and the Worker defect ledger (name the
  applicable entries in your session-start checkpoint). **Your command cap is now 600s, so
  you run your OWN app-dependent and e2e files this round** - the old "declare it and let
  the Architect run it" escape hatch is retired.
  **This step changes NO artifact. It produces a module plus a report.**
  1. Derive each document's semantic FLOW - section / group / role - from structure that
     already exists: the AcroForm wrapper hierarchy the M16-S3 resolver reads
     (`tax_graph/output/field_identity.py`), the address `path` breadcrumb, and geometry
     reading order. Structure-first only: never mine labels or guess from geometry, and
     return `unresolved` rather than inventing a flow. That discipline is the M16-S3
     precedent and it holds here.
  2. Propose a CONCEPT ID per widget, applying the two rules from the plan: the
     never-contains test (no line numbers, no years, no printed prose) and
     owner/role qualification (a bare `ssn` is never an address).
  3. Emit a read-only report `plans/M19_S1_CONCEPT_REPORT.md`: proposed concept per
     control; every COLLISION (two widgets sharing a concept - the four dependent SSNs on
     the 1040 are the exemplar, and the 434 hidden row-template widgets are the bulk);
     every UNQUALIFIED concept (a role with no owner); every id failing the
     never-contains test; and per-document counts. Findings are FINDINGS - do not "fix"
     either side.
  4. Cover the 434 hidden widgets explicitly. Report them per document
     (8949 184/202, w2 132/272, 1040 40/199, 1099-DIV/INT/B 24 each, schedule_1a 6) and
     propose the concept each row-template instance would map to. Do NOT change
     `cell_inventory.py` this round - S4 owns that.
  5. Suggested home: a new read-only module (e.g. `tax_graph/output/concepts.py`) that S3
     can consume later. No call sites in validate, preflight, or the manifest.
  **NO NEW TEST SUITE THIS ROUND (John, 2026-07-26: "another set of tests is premature").**
  THE REPORT IS THE DELIVERABLE. Concept ids are a PROPOSAL until John answers the three
  open questions in `plans/PHASE_M19.md`, so tests written against them now would only be
  rewritten. Tests arrive with S3, when the shape is settled and something is actually
  promoted. Do not declare focused test files, and do not pad the round with them.
  Gates for this step, and only these: ASCII, `git diff --check`, and module-form
  `validate 2025`. Real preflight is NOT required - this step adds no call sites in
  validate, preflight, or the manifest, so it cannot move the ratchet. If you do run
  something, report it with an honest `RAN:` line as always. ONE local commit; no push.
  Stop conditions: any need to touch promoted artifacts, the workbench projection, graph
  semantics, or verdict emission; a document whose flow cannot be derived structurally
  (report it as unresolved, do not guess); or a quota/environment failure.

- **[DONE `c370359`, Architect-verified live] M17-S3R2b TASK - FIX D7, THE RIVER SCROLL
  (Architect, Claude Opus 4.8, 2026-07-25).**
  Small, surgical, and it is the fix for John's original issue 1. Read the **Worker defect
  ledger in `AGENTS.md`** first and state in your session-start checkpoint which entries
  apply - that is now a standing rule.
  1. Fix `scrollRiverUnitIntoView` in `workbench/static/river.js`. It uses `card.offsetTop`,
     which is measured from the nearest POSITIONED ancestor; `.river-list` is
     `position: static` with no positioned ancestor, so `offsetParent` is `<body>` and the
     scroll overshoots by a constant ~167px, putting the selected card ~92px ABOVE the
     visible area. Confirmed live on the 1040 at cards 0, 5, and 20 - `inView: false` every
     time. Use `getBoundingClientRect` deltas against the container (the pattern YOU already
     wrote correctly in `scrollOfficialRegionIntoView` in `app.js`), or set
     `position: relative` on `.river-list`. Prefer the rect-delta approach: it is robust to
     future layout changes. Clamp to `[0, scrollHeight - clientHeight]`.
  2. Re-check the same class of bug anywhere else you compute a scroll offset this round.
  3. Verify with `tests/e2e/test_workbench_v2_m17.py::test_form_and_river_selection_crosses_
     pages_and_keeps_selection_visible`, which already asserts the card is within the river
     rect and currently FAILS. **If the ~124s cap blocks that file, you MUST say
     `NOT RUN: <reason>` and NOT report the step complete** - do not declare it verified on a
     Node syntax check. The Architect will run it.
  Tier-1 floor: declared files with honest RAN/NOT RUN lines, ASCII, `git diff --check`,
  module-form `validate 2025`. One local commit; no push. Stop conditions unchanged.
- **[DONE `c421558`+`c370359`, Architect-verified] M17-S3R2 + S4 TASK - NAVIGATION,
  CONTRAST, AND THE CELL DOSSIER (Architect,
  Claude Opus 4.8, 2026-07-25). Source: John's live review of the S3R UI.** Full
  design in `plans/PHASE_M17.md` (steps S3R2, S4b, S4) - READ IT FIRST. Scope is
  the review PROJECTION and the frontend: no verdict-emission change, no graph
  change, and NO promoted-artifact change (field maps, addresses, bindings, and
  citations are read-only this round).
  **Sequence the round in this order - S4b first, or you cannot verify yourself.**
  1. **S4b (do first, enabler).** Split `tests/test_workbench_cells_m17.py`. The
     file imports `create_app`, whose startup preflight + manifest build makes it
     run ~157s - OVER your ~124s launcher cap. Put the pure `cell_inventory`
     projection tests (no `create_app` import) in the fast file and leave the
     app-dependent API tests in a second file. Keep the `m17` marker and the
     existing `_drafts` skip guard on both. Declare BOTH filenames in the handoff.
     You run the fast one; record the app-dependent one as Architect-side.
  2. **S3R2 - navigation (issue 1).** In `workbench/static/`: after any selection,
     scroll the selected river card into view within the RIVER's scroll container
     (`scrollIntoView({block: "center"})`) - do not scroll the page and do not
     steal focus while a note textarea has it. Then fix the cross-page dead end:
     `app.js` `_riverSelectionHandler` currently does `if (!official) return;`, so
     selecting a card for a cell on another page does nothing. Resolve the cell's
     `page` from the model and `renderReview(cell.page, cell.cell_id)` before
     selecting. Same for keyboard next/prev across a page boundary. CAREFUL:
     `renderReview` rebinds both handlers - make sure the `syncingSelection`
     re-entrancy guard cannot be left stuck `true` (a `try/finally`).
  3. **S3R2 - contrast (issue 2).** In `styles.css`, selection currently collides
     with the unsupported policy color (both red - lines 84-86). Make the selected
     ring a treatment that cannot collide with ANY policy hue: a double ring (dark
     inner + light outer halo, so it reads over black form ink and over any fill)
     plus a non-color weight cue so it survives grayscale/color-blindness. Policy
     keeps the fill/border hue; selection owns the ring. Also scroll the selected
     region into view in the center pane when it is off-viewport at the current
     zoom.
  4. **S4 - resolve citations (issue 4).** `cell_inventory._citations` returns bare
     ids. `graph/2025/citations/*.yaml` already carries `quoted_text`, `locator`,
     `url`, `retrieved_date`, `source_document_id` per `citation_id`. Load and
     resolve them (stdlib + yaml ONLY - the workbench must not import the pipeline
     package; that is the M17-S2 boundary lesson that went CI-red). Render quoted
     text + locator + source, id secondary. NEVER synthesize, paraphrase, or
     "fill in" citation text - verbatim from acquired source only.
  5. **S4 - label every datum and name its source (issue 4).** Rebuild
     `river.js` `renderDetail` into labeled groups - Identity / On the form /
     Population policy / Graph / Authority - per the PHASE_M17 S4 item 2 list, each
     field tagged with the artifact it came from. Carry through the three field-map
     fields the UI currently DROPS: `reason`, `downstream_effect`,
     `missing_capability`. Absent data renders as an explicit "not authored" state,
     never a blank line.
  6. **S4 - reframe the policy vocabulary, UI ONLY (issue 3).** Split the flat badge
     into two labeled facets: how the value is obtained (`user_entered`, `imported`,
     `copied`, `computed`, `decision_required`) vs coverage status (`unsupported`,
     `intentionally_blank`). Relabel `unsupported` to say plainly that no mapping has
     been authored yet - it is a coverage gap, NOT a statement that the filer cannot
     enter it. **STOP CONDITION: do not rename the enum values in
     `graph/2025/field_maps/*.yaml` or any promoted artifact.** That is Tier 3 across
     605 cells and M16-S5 owns it.
  7. **S4 - coverage counts.** Per-document counts by policy surfaced in the left
     rail / dashboard.
  Tests: extend `tests/e2e/test_workbench_v2_m17.py` for the navigation and ring
  behavior, and the fast cells file for citation resolution + disposition passthrough
  + per-document policy counts. Tier-1 floor before the single local commit: your
  declared focused files green, ASCII, `git diff --check`, module-form
  `validate 2025` (`.venv\Scripts\python.exe -m tax_graph.cli validate 2025`).
  Preflight and the app-dependent tests are Architect-side (the cap) - record the
  attempt honestly and stop clean rather than guessing. `.pytest_tmp` basetemp;
  sequential pytest only. ONE local commit; no push. Session budget rules apply:
  state your model/effort/indicators on first handoff touch, declare the step,
  checkpoint before every expensive phase.
  Stop conditions: any need to touch promoted artifacts, verdict emission, or graph
  semantics; a citation whose text cannot be resolved from the promoted records (do
  NOT invent it - report it); or a quota/environment failure.
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
- **DEFECT-LEDGER RULE (2026-07-25, at John's direction).** John: "I would prefer to force
  Codex to take notice of its errors in the instructions." Recurring Worker defects are now
  pinned in the **Worker defect ledger in `AGENTS.md`** (canonical, Architect-owned, and NOT
  pruned at phase close - unlike this handoff). Every Worker session: read the ledger BEFORE
  declaring a step, and name in your session-start checkpoint which entries apply to what you
  are about to write. Repeating a ledger defect is a process failure to be reported as such,
  not quietly fixed by the Architect. Paired hard rule, also in `AGENTS.md`: for EVERY declared
  focused test file state `RAN: <command> -> <result>` or `NOT RUN: <reason>`; an unverified
  declared file means the step is NOT complete; never declare a file you already know the cap
  prevents you from running - say so up front so the Architect authors or runs it. Node syntax
  checks are not test evidence. WHY THIS EXISTS: across M17-S3 and M17-S3R2 the Worker's app
  code was CORRECT both times and every defect was in an e2e file it could not execute, which
  the Architect then silently fixed - so the Worker never learned. Ledger entries D1-D6 are
  seeded from those rounds.
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
