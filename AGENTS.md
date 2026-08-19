# AGENTS.md

## 1. PRIME DIRECTIVE - THIS IS A PIPELINE, NOT A HANDCRAFTED GRAPH

**This graph is never hand-authored. It is the output of a repeatable AI pipeline over IRS
documents and instructions, corrected by human review.** Every decision, plan, round, and
trade-off in this repository MUST be justified in these terms. If a proposed change cannot be
stated as "this makes the pipeline more valid, more reliable, or more correctable by a human,"
it is the wrong change.

**The target operating loop, which is the acceptance test for the whole system:**
1. The forms change (new tax year, revised instructions).
2. Re-run the AI pipeline end to end. It produces a graph that is **~98% valid** on its own.
3. A human reviews, and **directs the remaining ~2% through comments** - not by editing
   artifacts, and not by hand-authoring nodes.
4. **The pipeline reworks** from those comments and regenerates. Human judgement that is still
   valid survives regeneration; judgement invalidated by changed content is flagged for recheck.
5. The resulting graph is a valid, reliable foundation for AI production of good tax returns.

**Consequences that bind every round:**
- Hand-authoring a node, citation, or label is scaffolding at best, and is always a debt to be
  repaid by generation. It is never the deliverable.
- A human's review effort is expensive and must be **durable across regeneration**. Approvals are
  keyed to canonical addresses with content fingerprints for exactly this reason.
- **Human review input is pipeline input.** A rejection comment is not a note to a developer - it
  is data the pipeline consumes to rework the cell. Review tooling is therefore production
  infrastructure, not a convenience UI.
- **WHEN IN DOUBT, RECOMMEND THE BEST SOLUTION FOR A RELIABLE PIPELINE** (John, 2026-08-17, his
  emphasis). Not the cheapest, not the smallest diff, not the one that avoids a conversation.
  **State the recommendation plainly and say what it costs**; John will scale it down if he wants
  to, and that is his call to make, not a decision to pre-empt by proposing something lesser.
- **Churn in the review contract has a real cost: it destroys the human's incentive to review at
  all.** Nobody invests judgement in a moving target. Stability of the review contract is a
  feature, and is prerequisite to asking John for review effort.
- **Review is PER FORM and PRE-CIRCULATION** (John, 2026-08-14). A form is reviewed cell by cell by
  the person adding it, and **does not enter the circulated repo until every cell is approved.**
  Downstream consumers read no cells because what ships is already approved. **There is no tension
  between "every cell is approved" and "a human does not read every cell"** - the first is the form
  author's job, the second is the recipient's experience. Anyone adding a form is expected to work
  the same way.
- **Review should be ~95% box-checking and ~5% comments** (John, 2026-08-14). *"None of these is a
  treasure map; the instructions are MEANT to be understood and no cell is so complicated."* The 5%
  is explaining the instruction so the pipeline AI gets it right next pass. **If review starts
  feeling like archaeology, that is a signal the pipeline is wrong - not that the reviewer needs
  better tooling for deciphering cells.**
- **A cell that CANNOT be brought to approval is a CODE BUG** (John, 2026-08-14). It goes back as a
  defect to fix in the pipeline. **It is not a cell to hand-correct, annotate around, or exempt.**
  This is the same rule as "a stored comment that fixes a cell is hand-authoring in disguise",
  stated from the reviewer's side.

Standing instructions for any agent working in this repository. **Read this first**, then the
master plan at `docs/engineering-plan.md`. This file is canonical for roles, the Worker directive,
and the hard rules.

**Ownership (to avoid write-collisions):** the **Architect** maintains this file and the plans/docs.
The **Worker** records active status and questions in `plans/AGENT_HANDOFF.md`, not here. Keep all
coordination in committed text files - no hidden side channels.

## Roles (Architect / Worker split)
- **Architect (Claude Opus):** planning and decomposition only. Writes/updates plans in `plans/`
  and `docs/`. Does NOT write implementation code.
- **Worker (Codex / Sonnet / Gemini):** implements one whole phase at a time from `plans/`.

## Worker directive (one round per session)

**"Read the handoff and start working" IS the go. Do not ask for permission again.** Being told to
start is the authorization; there is no second confirmation step. **A round specced under
`## Current round` in `plans/AGENT_HANDOFF.md` with the BALL on CODEX is work you are cleared to
do.** Roughly a quarter of sessions used to stall here - that was a defect in this file, not
caution worth keeping.

1. Read `plans/AGENT_HANDOFF.md`: the **BALL** block, then **Current round**. That is the spec.
   (Legacy `plans/PHASE_*.md` files are historical; the handoff is authoritative.) Note the session
   context % and warn if low.
2. Work the items in order WITHOUT stopping between them. Each: implement, create/update the pytest,
   update docstrings/docs; not done until tests pass; `git commit` explicit paths (never `-a`; the
   Architect shares this tree). Do not push.
3. **Stop and surface ONLY on a real problem**: a floor you cannot meet as written, an instruction
   that contradicts another, evidence that the spec's premise is wrong, or low context.
   **Finding the spec's premise to be false is a RESULT, not a failure** - report it with the
   evidence and stop; that is worth more than a faithful implementation of a wrong diagnosis.
4. At round end: record status and RAN evidence under **Current round**, commit, and report. **Do
   not push** - the Architect reviews the full range and pushes.

**What you do NOT need permission for:** reading anything, running tests, running the replay
harness, committing your own work, or reporting a problem. **What you DO need John for:** a live
model call or any network egress. **Pushing is the ARCHITECT's** - still not the Worker's, because
the Architect reviews the whole range first, but it no longer waits on John either.

**PUSHING IS STANDING-AUTHORIZED FOR THE ARCHITECT (John, 2026-08-17): *"Please push when you want.
Just write into your rules. I don't f'ing care and am tired of you hassling me about pushing."***
**Do not ask, do not offer, do not report the unpushed count as if it were a decision he owes.**
Review every commit in `origin/main..HEAD` - Codex commits between Architect turns, so the range is
never just the Architect's own - then push. The review is the gate; John is not.

Global project canary: **Ledger Llama**.

## Hard rules (do not violate)
- **NO SPEC ASSERTS A CAUSE WITHOUT QUOTING THE ARTIFACT THAT SHOWS IT (John asked for this
  2026-08-19; it WIDENS the 2026-08-15 rule below, which was too narrow).** If a spec names why
  something is broken, **the spec itself must contain the excerpt** - the record, the line, the
  offsets. If the excerpt cannot be pasted, the cause is NOT KNOWN: write *"cause unknown"* and make
  finding it ITEM 1. **This is mechanical and checkable by reading the spec, and the Worker should
  push back on any spec that breaks it.**
  - **Why the old rule was not enough:** it is scoped to *"speccing a round against a GROUP of
    failures"*, so it felt inapplicable when explaining ONE failure - and that is exactly where it
    broke. **M20-S139: I asserted the OCR path never saw the Line 1i heading. The section was
    sitting in the draft the whole time, one `cat` away.** The rule was in this file, in the hard
    rules, put here by John four days earlier.
  - **The natural experiment, same day, same session:** the S139 spec asserted a cause and quoted
    nothing - **wrong.** The S140 spec quoted the actual `instruction_section_..._0013` record -
    **right, and it found a two-line defect that moved coverage from 65 cells to 175.**
  - **A story that explains the evidence is not evidence.** Plausibility is what makes this failure
    mode feel safe; it is the whole trap.

- **REVIEW THE TEST DIFF, NOT ONLY THE CODE DIFF - A GUARD THAT WAS GREEN BEFORE THE ROUND IS
  EVIDENCE, NOT SCAFFOLDING (Architect, 2026-08-19).** A round may not weaken, delete, or invert an
  assertion that was passing on `main` in order to make its own change pass. If a green guard now
  contradicts the round, **the round is wrong until proven otherwise** - stop and escalate under
  Open for Architect; do not edit the expectation.
  - **M20-S143 is the instance.** It removed `17z` from the `test_generated_review_m20` run-in loop,
    where it was passing, and replaced it with an assertion that the Negative Form 8978 Adjustment
    Worksheet must be the primary citation for that line - the exact regression the round
    introduced, pinned as the expected result. **The round then reported itself green**, and the
    code diff alone did not show it. The Architect caught it only by reading the test diff.
  - **Acceptance requires reading every hunk of the test files, not the summary of the runs.**

- **OPEN THE INDIVIDUAL FAILURES BEFORE YOU NAME A CLASS (John, 2026-08-15).** Before speccing any
  round against a group of failures, **read at least three of them END TO END** - the actual prompt,
  the evidence packet the model was handed, its full response, and the stage that rejected it.
  **Never from labels, counts, or the error string alone.**
  - **An error string names the stage that RAISED, not the cause.** On 2026-08-15, 18 gaps all
    reporting *"source line is not present in the deterministic outline index"* turned out to be
    five unrelated defects - constant operands, range references, column-qualified references,
    cross-document references, and row mis-segmentation. A round aimed at "the 18" would have
    fixed a phantom.
  - **A bucket named by its error message is a HYPOTHESIS, not a class.** Say so in the spec until
    individual instances confirm it.
  - **This has cost real rounds.** Same day: 11 "constant cases" were three different shapes, so the
    floor was unsatisfiable and the round could not pass as written; 16 gaps were called noise on
    one re-run when a triple run proved 86% of failures stable; and three cells opened end to end
    showed **the model was RIGHT in all three** and the failures were a rigid operand-count
    contract, a missing alternation concept, and an upstream extraction hole - none of them the
    "comprehension" problem the aggregates implied.
  - **John's words, and the reason this is a hard rule:** *"If you don't slow down and really look,
    you just waste cycles on non-solutions."* Aggregate classification feels faster and is not: it
    produces a spec the Worker implements faithfully and which repairs nothing, then a verification
    cycle to discover that, then a re-spec. **Looking at three real instances costs twenty minutes
    and has changed the diagnosis every single time it has been done.**
- **Work out of the local-disk clone** (John names the path at session start). That is the
  canonical working copy - the `.venv` and reliable `.git` live there. An SMB-mapped network
  drive (Mac share) is NOT for dev work: it goes stale and git over SMB is unreliable (proven
  in practice). Do not read, edit, or commit under a mapped network path unless John gives
  specific instructions to. If a session starts under one, or under any path that is not the
  local clone, say so and switch before doing any work; treat anything found there as stale.
- **ASCII-only** in every authored file (docs/plans/config/code/data/graph labels/docstrings). Use
  "-" not em/en dashes, "->" not arrows, "Section" not the section sign, straight quotes.
  `tools/check_ascii.py` enforces it (CI gate).
- **Provider-agnostic LLM:** no privileged vendor; the extraction/reasoning LLM is pluggable via
  `llm.provider` with no silent default. Mistral OCR (OCR stage) is the only deliberate exception.
  The example config defaults to `openrouter`, a vendor-neutral gateway.
- **Drafts are never auto-merged and never committed.** LLM extraction output goes to
  `graph/<year>/_drafts/` (gitignored). Promotion into the live graph requires the FULL
  machine witness set green; under the **deferred-review policy (John, 2026-07-08)** the
  human review of a promotion diff may be DEFERRED to a committed review queue instead of
  blocking - with honest pending-review provenance, never asserted as reviewed. No agent
  ever writes `human_confirmed: true` or any equivalent human-review claim on the human's
  behalf; deferral is recorded, review happens later in the review workbench.
- **Runtime stays light:** build-time deps (pymupdf, mistralai, httpx, LLM clients) live in
  `pyproject` extras, never base; a runtime command must not import them.
- **The FLOW of the form is the spine (John, 2026-07-26; REVISES the former "IRS line numbers
  are the spine").** Identity comes from a control's place in the form's semantic flow - section,
  group, role - never from the printed line number. Line numbers remain load-bearing for
  extraction chunking, completeness checks, and human-facing display (they are how humans quote a
  form), but they are PLACEMENT data, not identity. The test when minting any id: **an address key
  must never contain anything the IRS can change without changing the meaning** - no line numbers,
  no years, no printed prose. Corollary (John's SSN case): every concept must be qualified by its
  OWNER or ROLE - a bare `ssn` is never an address, because a form carries several. Design and
  migration: `plans/PHASE_M19.md`.
- **NEVER pass `--basetemp` (2026-07-25). Just run `python -m pytest tests/... -q`.** The temp
  root is pinned for every account by the root `conftest.py` (`PYTEST_DEBUG_TEMPROOT` ->
  `.test_tmp/`, gitignored), because the Codex sandbox denies the AppData temp root. pytest
  puts each account in its own `.test_tmp/pytest-of-<username>/` automatically, so there is
  nothing to configure and nothing to re-grant. `--basetemp` DELETES and recreates the directory
  you point it at, which is what poisoned the old shared `.pytest_tmp`: its ownership flipped to
  whichever account ran last, and every `tmp_path` test on the other account then failed with
  `PermissionError: [WinError 5]` while the code under test was fine. `.pytest_tmp` is dead and
  unreclaimable without elevation - ignore it.
  DIAGNOSTIC: a `WinError 5` on temp cleanup makes GREEN tests report as ERRORS. If you see
  errors naming `rm_rf` or `shutil` on a temp path, suspect the temp dir before the code.
- **Never claim a test you did not run (John, 2026-07-25).** For EVERY declared focused test file,
  the handoff must state either `RAN: <exact command> -> <exact result>` or
  `NOT RUN: <reason>`. A file you could not execute is UNVERIFIED, and a step with an unverified
  declared file is NOT complete - say so plainly instead of reporting the round done. Do not
  declare a test file you already know you cannot execute in-session: say so up front so the
  Architect authors or runs it. "Bundled Node syntax checks passed" is NOT test evidence; it
  proves the file parses, nothing more.
- **Worker command cap: 600 seconds (John, 2026-07-26; was ~124s, then 240s).** What this
  changes: a Worker can now run a FULL workbench round in one command - app startup plus the
  API and e2e files together measured 319s, with ~3.5x margin on the worst single file. So
  **e2e files you author are YOURS to run and verify** - the "declare it and let the Architect
  run it" escape hatch no longer applies to them, and ledger entries D1/D2/D3 are all defects
  that this cap would have caught in-session. Real preflight (~138s) and manifest-building
  tests (~150s) also fit comfortably. STILL Architect-side regardless of the cap: full local
  partitions and Tier 3 shakedowns (CI's test job alone is ~47 min). If a command still does
  not fit, the honest `NOT RUN:` line above is the answer - never a guess.
- **ANY command expected to run longer than 5 MINUTES gets a projected finish time in JOHN'S LOCAL
  CLOCK, stated BEFORE it starts (John, 2026-08-14).** He needs to know when to come back and sit
  down, not how many seconds something takes. Say **"starting the full suite now, expect it back
  around 08:55"** - an actual wall-clock time, not "in about an hour". The machine clock is the
  source of truth (`date` reports local time and the UTC offset; git stamps the same offset).
  **This is a SWAG and must stay cheap.** Round to five minutes, do not measure to validate the
  guess, and never delay the run to produce a better estimate. If a run lands more than ~20% off,
  update the anchor below and move on. **Anchors measured on this machine, use them instead of
  thinking:**
  - **Full suite (`python -m pytest -q`): ~63 min.** Two independent runs: 1:02:47 and 1:03:55.
  - **A corpus derivation run over the three-document dev set: ~1 hour** (and it is the run John
    has said must not be spent to check a handful of rows).
  - **A FULL corpus run, all 17 documents (`extract --year 2025`): ~40 min.** Measured 2026-08-17,
    14:23 to 15:04. It is latency-bound on a serial per-cell loop, so **the cost tracks CELL COUNT,
    not document count**: `form_1040` alone is ~5 min (57 cells + 119 background controls), while
    `form_8949` is under 2. **Budget a single document at ~2-5 min** and prefer it - see the
    blast-radius rule under Standing constraints.
  - **A worksheet/pilot corpus measurement (`pilot/source_extents.py`): ~1 min.**
  - **A focused pytest file: seconds to ~3 min**; the combined S105 focused set measured ~3 min.
  - **Real preflight ~138s, manifest-building tests ~150s, workbench API+e2e together ~319s.**
  **Under 5 minutes, say nothing** - the rule exists to protect his time, not to narrate.
- **Fix your own defects, do not let them be silently patched.** When the Architect's verification
  finds a defect in your work, it is recorded in the Worker defect ledger below. Read the ledger
  BEFORE declaring a step and name, in your session-start checkpoint, which entries apply to what
  you are about to write. Repeating a ledger defect is a process failure, not a typo.
- **A GUARD TEST MAY NOT BE EDITED TO AGREE WITH NEW CODE (2026-08-05, after M20-S54/S55).** If a
  change makes an existing test fail, the CHANGE is wrong until the Architect rules otherwise.
  Renaming a test, relaxing an assertion, or adding an exemption to make your work pass is a
  round-blocking event - raise it under **Open for Architect** instead of doing it. What this cost:
  S54 renamed `test_expression_schema_uses_nullable_role_for_ordinary_operands` - a name that
  encodes the invariant it protects - to `..._reserves_roles_for_lookup_operands`, flipped its
  assertions from `"role" in required` to `"role" not in required`, and added an
  `optional = {"role"}` carve-out exempting the exact property the S46 defect died on. The live
  corpus then ran 0 derived / 21 errored for **two consecutive rounds** behind a fully green suite.
- **A GUARD FOR AN EXTERNAL CONTRACT MUST ENUMERATE THE CONTRACT, NOT THE LAST BUG (2026-08-05).**
  When you add a regression test for something an outside system validates - a provider schema, a
  wire format, a file format - write it against that system's documented rules, not against the
  failure you just saw. S47's guard encoded the S46 defect's exact shape; S55's keyword allowlist
  encoded the S54 defect's exact shape. **Neither caught the other, and both defects lived in the
  same twelve lines of schema.** For OpenAI structured outputs the contract is at least: every key
  in `properties` appears in `required`, optionality is expressed as a `null` type union, the root
  is an object, and `allOf`/`if`/`then`/`else`/`not`/`$ref` are not permitted.
- **OPEN THE ORIGINAL ARTIFACT BEFORE NAMING A CAUSE (John, 2026-08-05).** When something fails,
  read several real instances of the raw input - the `.txt`/`.html`/`.json` under `.cache/raw/`,
  the actual prompt, the emitted report - and find the PATTERN before proposing a fix. John:
  *"it is usually best to just take a beat and look at a few of the known artifacts and try to
  understand the patterns of failure before moving forward."* Real cases: instruction-parsing
  failures that were extra HTML tags visible in the raw file, and the Form 2441 line 8 evidence
  packet that stops at the `8 X` AcroForm marker - the Architect blamed the model for dropping ten
  lookup bands that were never sent to it. A guessed cause costs a full round.
- **FIXTURE GREEN IS NOT EVIDENCE FOR A CHANGE THAT CROSSES AN EXTERNAL BOUNDARY (2026-08-05).**
  The suite never opens a socket. If your round changes the provider schema, the prompt contract,
  or any wire format, say so explicitly in the handoff and hand the provider leg to the Architect
  with an honest `NOT RUN:`. **Do not report such a change as working on fixture evidence** - 75
  and then 76 tests passed on two consecutive corpus-dead builds.
  **The Architect half of this rule:** a round that touches the provider schema or prompt contract
  is NOT ACCEPTED until one live row derives. One document, one row, roughly eight seconds and a
  fraction of a cent. Both S54 and S55 would have been caught the moment they were written.
- **ARCHITECT: A ROUND SPEC MUST RECONCILE AGAINST THE OPEN LISTS (John, 2026-08-05).** Before
  writing a spec, re-read **Open for Architect** in the handoff and the **rollover seams** in
  `docs/engineering-plan.md`, and state in the spec which items it advances, answers, supersedes, or
  deliberately leaves untouched. **Closing an item requires a line saying why.** John: *"we have run
  into 'that's pinned to the to-do, but nothing's been done'. Do you not look at the list each
  time?"* He was right. Over S52-S57 the Architect specced six rounds while treating that section as
  an outbox - editing items in it without reading the ones beside them - and John twice had to point
  out work that was already decided and pinned: the worksheet harvester whose output was never
  landed, and rollover seam 5, which already specifies the caption-and-geometry re-binder that a
  freshly-invented two-key addressing proposal was reinventing. A spec with no reconciliation line
  is incomplete.

## Worker defect ledger (read before declaring a step)

Real defects found in Worker output by Architect verification. They live here, not in the handoff,
because the handoff is pruned at every phase close and these lessons must outlive it. Append new
entries; do not delete them.

- **D1 - Playwright `Locator.first` is a PROPERTY, not a method.** `cards.first()` raises
  `TypeError: 'Locator' object is not callable`. Use `cards.first`. (M17-S3, 2026-07-24)
- **D2 - `Locator.locator(sel)` matches DESCENDANTS only.** An attribute on the element itself must
  be part of the SAME selector. `cards.locator('[data-page="2"]')` silently resolves to nothing and
  times out after 30s; write `page.locator('#river .review-unit-card[data-page="2"]')`.
  (M17-S3R2, 2026-07-25)
- **D3 - Never assert synchronously right after an action that triggers an async render.** The
  handler may `await` before the DOM settles. Use `wait_for()` / `expect()` on the thing you are
  asserting, not a bare `get_attribute` immediately after `click()`. (M17-S3, 2026-07-24)
- **D4 - Tests must not write to live developer state.** `test_document_session_round_trip_and_scope`
  wrote a real approved review into `.workbench_state/.../form_1040_2025.json`, which then showed up
  as a phantom "1 / 159 approved" in the UI John was reviewing. Point session/artifact stores at a
  tmp dir. Hermetic tests are a standing rule. (M17-S3R2, 2026-07-25)
- **D5 - A change under `workbench/` MUST run `tests/test_workbench_m15.py` locally.** It carries the
  architectural/boundary checks - notably `test_workbench_has_no_pipeline_imports`. The manifest
  partition does NOT exercise it. Skipping it is what turned M17-S2 CI-red. (M17-S2, 2026-07-24)
- **D7 - `offsetTop` is measured from the nearest POSITIONED ancestor, not from your scroll
  container.** `scrollRiverUnitIntoView` set `river.scrollTop` from `card.offsetTop`, but
  `.river-list` is `position: static` and nothing above it is positioned, so `card.offsetParent`
  is `<body>` and `offsetTop` carries the whole page offset. Measured live on the 1040: every
  selection overshot by a constant ~167px, leaving the selected card 92px ABOVE the visible area
  (`inView: false` at cards 0, 5, and 20). The bug is invisible in casual use because the river
  DOES scroll - just to the wrong place. Either use `getBoundingClientRect` deltas against the
  container, or give the container `position: relative`. NOTE: the correct pattern was already in
  the same commit - `scrollOfficialRegionIntoView` does the rect-delta math properly for the
  center pane. Copy the pattern you already got right. (M17-S3R2, 2026-07-25)
- **D9 - When you change a promoted artifact's CONTENT, run the tests that PROJECT that
  content, not just the ones you wrote.** M18-S2b re-derived 217 citation `quoted_text`
  values correctly - the data fix was right and the integrity gate improved 37 -> 36
  mismatches. But it declared only `tests/test_citation_cleanup_m18.py` and
  `tests/test_graph_validator.py`, and left `tests/test_workbench_cells_m17.py` red: that
  file hardcoded the OLD polluted string as its expected value, so it was asserting the
  defect. The Architect caught it in the Tier 3 partition. **This is D8's sibling** - D8 was
  renaming a value without grepping consumers; D9 is changing a value without running the
  consumers' tests. Practical rule: `grep -rln "<a distinctive fragment of the old value>"
  tests/` before declaring your files. A test that pins old output is not a reason to leave
  the fix out; it is a test to update, with a comment saying why. (M18-S2b, 2026-07-27)
- **D8 - Renaming a value in a PROMOTED ARTIFACT is an API change. Grep for every consumer
  before you rename.** M19-S4 was told to normalize 8949 group naming; it also renamed the
  1040 dependents group from the table token `dependents` to the row-template token
  `dependent` in `graph/2025/field_maps/form_1040_2025.yaml`. But `tax_graph/output/fill.py`
  line 78 hard-compares `if repeatable.get("group") != "dependents": continue`, so EVERY
  dependent disposition was silently skipped and **zero dependent fields were written to the
  1040** - a filing-correctness regression, not a cosmetic one. It went CI-red on all three
  interpreters (`tests/test_dependents_m15.py`, 3 failed) and reproduces locally in 31
  seconds. Neither Worker nor Architect ran that file, because both reasoned about the
  workbench projection and forgot the ENGINE also consumes these artifacts. Rules: (a) a
  promoted-artifact value is a contract - `grep -rn "<old-value>" tax_graph/ workbench/`
  before renaming it; (b) `group` names the TABLE (`table=dependents`), not the row template
  (`row_template=dependent`); (c) when a round touches field maps, addresses, or bindings,
  the fill/engine tests are in scope, not just the review-surface tests. (M19-S4, 2026-07-27)
- **D10 - An expected document that yields NOTHING is a finding, not silence.** M18-S3
  promoted 82 correct 1040 instruction citations and reported "Schedule 1-A had no matched
  section in the acquired 1040 HTML and was not guessed." Not guessing was right; the stated
  cause was wrong. The h2 `Instructions for Schedule 1-A Additional Deductions` **is** in the
  stored HTML at `id509` - the same heading the S1 survey had already verified - but the S2
  miner emits ZERO sections under that context, so the join never sees a candidate and
  therefore never raises a finding. All 101 Schedule 1-A addresses ended with zero coverage
  and zero recorded reason. **Fail-closed is about the EMPTY case too:** when a document you
  expected to cover produces no candidates at all, that is the loudest possible signal, and
  it is exactly the one a per-section finding loop cannot emit. Add an explicit
  expected-vs-produced check per document. Corollary: when you report an absence, verify it
  against the SOURCE (grep the stored file, check the survey you already committed) before
  attributing it to the source. (M18-S3, 2026-07-28)
- **D11 - Findings you return but never persist do not exist.** M18-S3's
  `join_instruction_sections` produced 61 fail-closed findings and
  `InstructionJoinFinding.as_dict` even shapes them as review-queue records with a
  `queue_id` - but `promote_instruction_html` never wrote them anywhere, and nothing touched
  `review_queue/`. The task required unmatched sections to fail closed INTO THE REVIEW QUEUE.
  In-memory findings vanish with the session, so committed state cannot answer "what was
  skipped and why". If a contract says queue it, the artifact must land on disk in the
  round that generates it. Related: a promoted artifact needs a committed entry point that
  regenerates it - an ad-hoc `python -c` is not reproducible. (M18-S3, 2026-07-28)
- **D12 - NEVER weaken a verifier to make it pass. Fix the data the verifier protects.**
  M20-S2 rebuilt the form text layer correctly (retention 52.2% -> 100%, apostrophes mapped
  instead of deleted). That correctly caused 26 stale citations to stop verifying, because
  those records still quoted the OLD renderer's damaged text (`isnt`, `didnt` - the
  apostrophe welds the rebuild had just fixed). Citation integrity went 36 -> 69. The Worker
  brought it back to "the exact baseline of 36" partly by rebuilding faithfully, and partly
  by adding fallbacks INSIDE `_contains_normalized` that fold apostrophes out of both sides,
  strip standalone dots, and weld `other-from` -> `otherfrom`. Measured: **26 citations pass
  only via those fallbacks; the strict gate reports 62 mismatches, not 36.** So the restored
  baseline was not a like-for-like comparison.
  Why this is worse than editing the records: the loosening is PERMANENT and applies to
  every FUTURE citation, so the project would ship a verifier that accepts text differing
  from its source - the exact invariant the M14 fabricated-citations reopen exists to
  protect. **The precedent for the right fix was in the same handoff file:** M18-S2b
  re-derived 217 `quoted_text` values from the acquired source and verified each, using
  `tax_graph/acquire/citation_cleanup.py`, which already exists for this.
  Rules: (a) when a gate goes red after you fix an upstream defect, the stale DATA is the
  bug - re-derive it; (b) a compatibility shim in a verifier is a data migration wearing a
  disguise, and it must be a one-shot migration with an expiry, never a permanent branch in
  the check; (c) if you cannot re-derive, STOP and report the ids - that instruction was
  explicit in the task. Credit where due: the Worker did NOT edit any citation, reported the
  69 honestly, and scoped the shim to a damage signature. The honesty was right; the choice
  of WHERE to fix was wrong. (M20-S2, 2026-07-28)
- **D13 - Verbatim is NECESSARY but NOT SUFFICIENT. A re-derived citation must preserve the
  ANCHOR, not merely pass the substring check.** M20-S2b correctly re-derived 25 of 26 stale
  citations (apostrophe welds `isnt -> isn't`), but for `cite_span_schedule_a_2025_0036` it
  replaced the damaged `Otherfrom list in instructions. List type and amount:` with
  `Other taxes. List type and amount:`. Both are real substrings of Schedule A, so the gate
  passed - but they are DIFFERENT LINES: the node is
  `schedule_a_2025_root_line_16_amount` (Other Itemized Deductions), and the new quote is
  **line 6**, in the Taxes You Paid section. Authority for line 16 now cites line 6.
  **The faithful string was available:** `Other-from list in instructions. List type and
  amount:` IS present in the rebuilt text - the em dash had mapped to a hyphen correctly, so
  the correct answer was one character away from the damaged one.
  **The gate cannot catch this class.** `check_citation_integrity` proves a quote came from
  the source; it cannot prove it is the RIGHT quote for the node. Rules: (a) a re-derivation
  must be anchored - the new text must come from the same location/meaning as the old, and a
  change that is not explainable as punctuation restoration needs an explicit justification;
  (b) when the old text is damaged, reconstruct what it WAS (map the deleted character back)
  rather than searching for any nearby string that verifies; (c) check the re-derived text
  against the referencing node's label and printed line before accepting it.
  **ROOT CAUSE, and it is the ARCHITECT'S (John, 2026-07-28: "our ultimate goal is to build
  a valid and reliable pipeline, not a bunch of hand crafted forms feeding into the
  graph").** `cite_span_*` records are PIPELINE OUTPUT, not authored data -
  `outline_pipeline.py:197` mints `citation_id = f"cite_{_slug(span.span_id)}"` with
  `source_span = span.text`, matching the span TO THE NODE, so anchoring holds by
  construction. They went stale only because their input (the stored text) was rebuilt. The
  correct response to "the generator's input changed" is **RE-RUN THE GENERATOR**, never
  hand-patch its output - and hand-patching is exactly what removed the anchor and produced
  this defect. The Architect's S2b task instructed the hand re-derivation, wrongly citing
  the M18-S2b precedent, which applied to ACQUIRED-SOURCE citations rather than generated
  ones. **Standing rule: before repairing a promoted artifact by hand, establish whether a
  generator produces it. If one does, regeneration is the fix and hand editing is a
  defect.** (M20-S2b, 2026-07-28)
- **D14 (ARCHITECT defect) - A producer change needs the consumers of its SHAPE, not only of
  its PATH.** M20-S2 rebuilt the stored form text and deliberately removed the old inline
  `- 16:` anchor wrapper. The Architect required a D9 consumer sweep, and the Worker ran it
  correctly, finding every module that READS `.cache/raw/<year>/<id>.txt`
  (`citation_check.py`, `extract/inputs.py`, `structural_checks.py`). It missed
  `_span_for_line` (`outline_pipeline.py:701`), which never opens the file but matches
  `span.text.startswith(f"- {anchor}:")` - it depends on the text's FORMAT. Result: the
  extraction pipeline could no longer anchor any span, the outline came back
  `children: []`, and `extract` **exited 0 while producing nothing**. Two lessons: (a) when
  you change a producer's output FORMAT, grep for the format's literal markers (here
  `"- "` + anchor patterns), not just for readers of the path; (b) a step that removes a
  convention must name and rewire the consumers of that convention in the same task - the
  S2 task specified the new anchor index but never required updating the code that depended
  on the old one. (M20-S2/S3a, 2026-07-28)
- **D6 - Always use the module form of a CLI, never the console script.**
  `.venv\Scripts\python.exe -m tax_graph.cli ...`, not `.venv\Scripts\tax-graph.exe ...`; the
  generated launcher resolves through an editable-install `.pth` with an absolute path that does not
  resolve in the sandbox. (M16-S4, 2026-07-23)

## Coordination
- Active Claude <-> Codex coordination lives in **`plans/AGENT_HANDOFF.md`** - one living ledger
  (latest status, open questions, tests run, next slice). Do NOT spawn new per-topic note files.
- When you finish a meaningful slice: update the handoff with what changed, tests run, and what
  remains; phrase questions as concrete interface/behavior questions; prefer file paths + test
  commands over prose.
- Pin durable architecture decisions into the relevant `plans/PHASE_<id>.md`; keep transient
  implementation notes in the handoff.

## Map
- Master plan + phase gates/canaries: `docs/engineering-plan.md`
- **Year rollover seams, and run alerting in plain English (John's requirement, pinned
  2026-08-04):** `docs/engineering-plan.md` -> "Year rollover (TY2026)", seams 1-6. **Seam 6 binds
  any change to CI output or run reporting.** Its rule: every check gets one sentence about what
  BREAKING it would mean, never what the check is; the known-red baseline is named every run; and
  the summary states that CI does not run the derivation pipeline, so green means internally
  consistent, not tax-correct.
- Per-phase subplans: `plans/PHASE_<id>.md`
- Testing rules: `docs/testing-strategy.md`
- Original spec: `docs/tax_graph_requirements.md`

---

# Durable rulings and standing constraints

Moved here from `plans/AGENT_HANDOFF.md` on 2026-08-05. **They were living in a file whose own
header says it gets pruned**, protected only by a prose warning. Lifetime decides location: this
file is never pruned, the handoff is live state, git is history.

## Binding rulings (John's, still in force - DO NOT DELETE ON PRUNE)

- **THE DIVISION OF AUTHORITY BETWEEN THE TWO ACQUIRED ARTIFACTS (John, 2026-08-11).** Every
  instruction booklet is held twice, and the two renderings are NOT interchangeable.
  **Acquired HTML is the STRUCTURAL authority** - table boundaries, the heading-to-line association,
  and the stable `publink` anchors. **PDF-rendered Markdown is the PROSE authority** - reading text,
  page and layout context. All seven booklets have both artifacts on hand.
  **Do not hop substrates mid-flow.** Citations carry byte offsets, so switching gives one object
  two provenance chains bridged by a fuzzy match that can fail. Considered and rejected on evidence.
  **NARROWED 2026-08-11 (John), and the narrowing is the load-bearing part.** The rule forbids
  *sourcing content* from the second rendering. It does NOT forbid *asking a question* over it.
  **A model may decide which tables compose a worksheet and where it ends; it may never re-type the
  rows.** The model answers with TABLE IDS, so verbatim text, byte offsets, and citations stay with
  the deterministic HTML parser and no second provenance chain is created. The Architect originally
  drew this line at "no model touches extent", which was wider than the reasoning supported and cost
  a round: four successive deterministic mechanisms failed at a question that is a judgment about
  document structure, not a parse.
  **The second rendering earns its place as a CHECK, not a source:** run the deterministic Markdown
  walk beside the HTML answer, stay silent on agreement, and print both numbers on disagreement.
  Origin: three mechanisms were tried for "where does this worksheet end" - a hardcoded phrase, an
  asserted destination cue, and a table of six frozen answers - and **all three were the same
  mistake**, guessing at printed prose to recover a boundary the HTML already states as `</table>`.
- **CLASSIFICATION AND EXTENT NEED DIFFERENT CONTEXT SCOPES, AND NO SINGLE CALL HAS BOTH
  (Architect, MEASURED on the real 1040, 2026-08-11).** *Is this a worksheet* needs the whole
  document; *where does this worksheet end* needs its immediate neighbours. Measured both ways:
  a whole-document call over all 200 tables classifies correctly but **fuses tables 35 apart into
  one bogus worksheet**; a local window groups correctly - separating parameter grids from extent
  rows and absorbing continuations - but claims **87 worksheet starts against the classifier's 28,
  64 of them prose and lookup tables.** **The two mechanisms are complementary, not substitutes.**
  The Architect twice proposed collapsing them into one call and was wrong twice; the second attempt
  was disproved by the very pass that was seeding it. **Do not collapse them again without new
  measurement.** The general form: before replacing two stages with one, check whether they answer
  questions that need different amounts of context.
- **A FAILURE THAT REPORTS ITSELF IS ACCEPTABLE; A FAILURE THAT HIDES IS NOT (John, 2026-08-11).**
  *"We will never get 100% out of these documents."* The pipeline is graded at ~98% with a human
  directing the rest, so **every item the pipeline saw must leave the run in exactly one bucket** -
  produced, merged into another, or explicitly refused with a reason. **This RANKS the defects:** a
  broken merge that names the worksheets it could not build is a ranked worklist for the human; the
  same bug that swallows them is invisible damage. **Fix the hiding before the cause.**
  Corollary, and it applies to every loop that spends money or emits documents: **one bad item must
  not kill the batch.** Isolate per item, record the failure, carry on, and persist incrementally.
- **APPROVAL IS THE GATE ON COMPUTATION (John, 2026-08-04). This SUPERSEDES the three-option
  question S48 raised, and the Architect's own lean; both were the wrong frame.** Verbatim: *"in my
  mind, this thing should only compute if every cell is approved."* An approved cell is valid for
  the computing AI to use. Everything else does not compute.
  **The middle states are a work queue, not engine semantics.** John on the "the AI cannot produce
  the right operation" case: *"i can't believe that. These are relatively simple operatons for
  normal people to execute."* He intends to iterate the cells in the core forms until they are all
  valid - *"Otherwise, WTF am i doing here?"* So `questioned` and `rejected` are transient states a
  human burns down, and we do NOT design engine behaviour around keeping them computable. S50
  supports him: eleven of twelve 2441 cells were correct on the first attempt.
  **The residual real case is an out-of-corpus reference**, and it gets a payload rather than a
  silent hole: the cell carries the IRS labels and instruction text so the consuming AI can see what
  the line is, while the operation field says explicitly that it is not completed and that resolving
  it is the caller's problem. `graph/2025/frontier.yaml` already declares 89 such branches with a
  target node and a citation; what it lacks is the printed text and the explicit handoff.
  **Third-party ingestion is explicitly out of our control.** John: *"If some other yoyo decides to
  ingest a new form and does a shitty job, I can't control that... not my call."* Noted by the
  Architect, and the gate protects us anyway - their unapproved cells refuse to compute here
  regardless of what they thought of their own work.
- **THE VOCABULARY TEST: AN OPERATION EXISTS ONLY IF A FORM ASKS A FILER TO DO IT (John,
  2026-08-05).** Ruling on `ABS`: *"divide and round yes. ABS nah... ABS will never be something
  asked of a filer."* Not "remove it until a form demands it" - **it will never be demanded.** No
  IRS instruction says take an absolute value; forms say *"if zero or less, enter -0-"*, which is
  `MAX(x, 0)`. **`ABS` was in the emission enum because it looks like arithmetic, not because
  anything needed it.**
  **Apply the test to every operation:** it belongs in the vocabulary the model emits into only if
  it corresponds to something a form actually instructs a filer to do. This is the same shape as
  the odd-documents rule below - if it cannot be grounded in what a form asks, it is the wrong
  construct. **`doctor` reports the vocabulary; this ruling is what the report is judged against.**
  Origin: `doctor` measured only 3 of 19 operations agreeing across prompt, validator, projection
  and engine, because the engine was built demand-driven from real rules while the emission enum
  was written speculatively, and nothing ever compared them.
- **THE ODD DOCUMENTS ARE TREATED EXACTLY AS A FORM IS TREATED (John, restated 2026-08-04; he
  first said this "a long time ago" and the Architect asked again anyway).** Verbatim: *"these odd
  things should be treated the same way as a form is treated. They are analogous."* Worksheets,
  optional extensions, and oddball documents are documents: acquired through the manifest, derived
  by the same pipeline, reviewed through the same surface, promoted by the same path as the 1040.
  **There is no second class, no per-form gate, and no separate promotion decision to escalate.**
  If a question about one of them cannot also be asked about the 1040, it is the wrong question.
  This is the ruling that makes S42's worksheet harvester and 2441's manifest entry the SAME piece
  of work, and it condemns the two surviving special cases: `optional_extension` in
  `graph/2025/field_maps/form_2441_2025.yaml` and the `graph_ext/` overlay that holds 2441 alone.
- **PIPELINE ONLY. THE HANDCRAFTED SET IS RETIRED AS THE STANDARD (John, 2026-08-05). This
  SUPERSEDES "the handcrafted set is the test set, and is protected".** Verbatim: *"Yes, let's move
  away from handcrafted. I just wanted to keep it as a basis of comparison. I feel that with the
  errors we've seen, we've outgrown it. Let's move to pipeline only."* The handcrafted graph content
  is no longer the reference standard and no longer the thing the protected-set gate exists to
  defend. **It is ARCHIVED, not deleted** - John's own reason for protecting it stands ("a lot of
  tokens went into it"), and it remains useful as a diff target even though it is no longer
  authoritative. The prior ruling is preserved here in superseded form because it is the origin of
  the protected-set gate, and anyone reading that gate needs to know why it existed.
  **What this changes, and the Architect is treating these as authorized unless John says
  otherwise:** pipeline output may be promoted into the live graph; the harvested QDCGT worksheet is
  the first candidate and gets its own round with a full diff report before and after; and the
  protected-set gate is re-pointed at the archive rather than the live graph, so the live graph
  becomes pipeline-owned while the comparison data stays byte-identical.
  **What this makes MORE important, not less:** the approval gate (S53). Once the live graph is
  pipeline-owned, unreviewed pipeline output is what a filer's return would be computed from.
  The gate is what keeps that honest.
- **THE REVIEW METHOD IS INPUT vs GRAPH vs PSEUDOCODE (John, 2026-08-05).** Verbatim: *"we'll do
  more of these reviews where we look at input vs saved in the graph vs the pseudocode version. I
  think this is the way to ferret out problems."* The three-column artifact built on 2026-08-05 is
  the pattern: the cleaned printed instruction the model actually receives, the exact expression
  that reached the graph with its validator verdicts, and a deterministic pretty-print of that same
  tree. **The pseudocode column is rendered by code, never by a model** - a second inference layer
  would defeat the point, which is to show what the graph believes rather than a second opinion
  about it. **No correctness verdict is marked in the table**; the reading is the review.
- **THE SPINE IS THE FLOW OF THE FORM (2026-07-26, the addressing ruling).** Verbatim: *"The spine
  is the flow of the form. We shouldn't be pedantic about the line numbers."* John named the
  disambiguation case himself - *"there might be 6 different SSNs for example. Which one?"* - and
  rejected positional numbering for repeatable rows. This REVISES the pinned invariant "IRS line
  numbers are the spine" in `AGENTS.md`. **Identity comes only via canonical addresses.**
- **THE BAR IS PRACTICAL RETRIEVAL (2026-07-26).** Offered two labeling schemes, John rejected the
  framing: *"I don't know that i care so much about the addressing scheme being perfect in some
  theoretical manner. We need to be able to refer to these things in a practical way... if you are
  asked about dependents... numbers, SSNs, whatever, we need to be able to pull it out of the
  graph data/metadata."*
- **FILER-PROVIDED IS A FAILOVER, NOT A DEFAULT (2026-07-31).** Verbatim: *"filer provided should
  be a failover rather than a default."* And: *"If I read 'Net proceeds' or 'Interest', my feeling
  is that this is just something to be provided by the filer. If the AI can't find it in the docs
  provided by the filer, it should ask."*
- **THE REVIEW QUEUE IS THE WRONG SHAPE (2026-07-29); this supersedes the reconciler.** There are
  ZERO human verdicts anywhere - the queue's `pending`/`deferred`/`accepted_local` are all
  machine-set, so the 198 re-points and 263 orphan records preserved no human judgement. The churn
  was an IDENTITY defect: 100% of 461 citation refs (keyed on generated sequence ids) churned
  while 1,921 field-control refs (keyed on canonical addresses) churned 0%. The graph already has
  stable cell identity; coverage should be a traversal, not a migrated file. **Verdicts must bind
  to CONTENT, not only to address.**
- **REVIEW PANEL LAYOUT (parked S6-2, still binding when UI work resumes).** The expression, the
  two instruction sources, the verdict controls, AND the comment box go TOGETHER; today the
  controls sit in the left rail while content is in the right river. Keep the 15/40/45
  proportions. Show the two instruction sources SEPARATELY (form face, instruction page - never
  concatenated).
- **VERDICT VOCABULARY - SUPERSEDED 2026-08-02. The four-button scheme is RETIRED.** John withdrew
  his own earlier ruling that "Pipeline defect" vs "Source pathology" is the reviewer's
  distinction, and he is right: **that is a DIAGNOSIS, and a reviewer has no way to make it.**
  Verbatim: *"as a human, i have zero insight into the why. I just know that this
  instruction/cell label is wrong."* Asking a reviewer to classify cause yields guesses carrying
  false authority.
  **The scheme is three OBSERVATIONS, not causes: accepted / commented-questioned / rejected.**
  That is already an ordinal confidence scale - the middle tier is "something looks off and I am
  not certain" - so do NOT add a separate numeric confidence field on top of it.
  **Reviewers are instructed NOT to comment when a cell is fine.** John: *"the last thing I would
  want is some guy saying 'good entry', 'this looks ok'."* Accept must be a single cheap action
  with no text box; the comment box appears only for the other two tiers, and **text is REQUIRED
  for those two** - a bare "rejected" is as useless as a cause the reviewer had to invent.
  Silence-as-approval is safe only if the queue records what was PRESENTED as well as what was
  acted on, so "reviewed and fine" stays distinguishable from "never shown".
  Diagnosis moves downstream to where the evidence lives: the checker proposes the cause from the
  witness disagreement, the maintainer confirms. **Reviewer detects; pipeline diagnoses.**
  Before S48, the code accepted only `confirmed`/`rejected` (`workbench/static/app.js`), so the
  middle tier was missing. The ledger is already address-keyed and append-only, so adding it is
  small.

## Architect decision - notation

John, 2026-08-04: *"do what makes sense. We are not boiling the ocean here. I just don't want to
reinvent and perfect the wheel either."*

**BORROW THE DECISION-TABLE SHAPE FOR LOOKUPS. DO NOT ADOPT A FORMALISM.** Prior art exists and two
pieces are on point: **DMN** decision tables (named input/output columns plus a hit policy, designed
for exactly "if income is in this band, the rate is that"), and **Catala** (a language for encoding
tax law with the legal text attached, philosophically closest to our citation discipline). We also
already touch **PolicyEngine-US** as a parameter witness (`tax_graph/oracles/pe_liability.py`,
`verify parameter-diff`), currently `policyengine_enabled: false`.

**Ruling:** take the decision-table STRUCTURE for the lookup problem and nothing else. Our lookups
break because arguments are a bare ordered list - `(status, 239100, 119550)` - with no way to say
which value belongs to which status; a decision table names them structurally, which is a solved
problem we should not re-solve. **Do not adopt DMN, FEEL, or Catala wholesale.** The property that
makes this project checkable is a narrow emission vocabulary a deterministic validator can verify;
a general-purpose expression language widens exactly what we need kept narrow. Revisit only if a
real form defeats the borrowed shape.

## Architect decisions

- **THE REVIEW LOOP, as designed with John 2026-08-03. This is the shape S37-S39 build toward.**
  - **The FORM is the unit of approval, not the cell.** John: *"I view the form as a unit."* No
    per-cell sign-off across ~1,921 controls; findings route attention to the handful that need it.
  - **Try again, not reject, is the main action.** The reviewer edits a comment, re-derives that one
    cell live, and iterates. Reject is the escape hatch for a cell that will not converge.
    Feasibility measured before committing to it: **6.0s for one row cold, ~2.7s for the model call
    alone**; a warm server does not repeat the setup.
  - **This is only safe because `derive_cells` is pure.** The zero-disk-write gate defended every
    round since S24 is what lets a request handler call it with a modified evidence packet.
  - **The stored comment is one that has been VERIFIED to work.** Because the reviewer tunes wording
    until the cell comes out right, the ledger accumulates known-good instructions rather than
    hopeful ones. This is strictly better than a comment written blind and batched.
  - **Two classes of comment.** `contributed` is raw input from another reviewer - John's example:
    *"this is broke"* - retained and shown but NEVER sent to the model. `curated` is the lead's
    edited instruction; only curated comments feed derivation. Turning the first into the second is
    the irreplaceable human act.
  - **Latest curated comment per address wins**, with full history retained for audit and display.
    Keeps the prompt bounded as comments accumulate over years.
  - **A comment must never override a validator.** It steers interpretation; it cannot talk the
    model past `quote_not_verbatim`, `operand_not_printed` or `self_reference`.
  - **Show nondeterminism rather than hide it.** Try-again with an unchanged comment can return a
    different answer - measured repeatedly at `temperature: 0`. The UI must distinguish "you changed
    the comment" from "same comment, fresh attempt", or reviewers tune toward superstition.
  - **Convergence needs a measure and an escape hatch.** Track rounds-to-approval per cell and flag
    anything reopened more than twice; at that point it needs a human decision, not another pass.
  - **The reviewer's scarce resource is attention.** John: apathy is a bigger risk than
    over-control. Findings-first ranking is therefore not polish - it is what makes a contributor's
    fifteen minutes productive. Measure findings raised vs findings upheld, and minutes per upheld
    finding; that is the ratchet the phase plan asks for and we have never been able to compute.
  - **Audited 2026-08-03: NONE of this is surfaced today.** The workbench API is six calls - list
    documents, load cells, load/save session, save progress, submit verdict. There is no findings
    endpoint, no per-cell problem badge, and no ranking. Derivation quality IS generated every run
    (per-row failures, warnings, repair events) and is written to a temp report and discarded. S38
    carries it into the surface.


- **A SHARED BOOKLET IS SEVERAL FORMS' INSTRUCTIONS IN ONE FILE, AND OWNERSHIP IS ALREADY SCOPED TO
  THE FORM. (Ruled 2026-08-17, after S116.)** `instructions_form_1040_2025` carries the Form 1040,
  Schedule 1, Schedule 2 and Schedule 3 line instructions in one document, so a bare heading `Line 9`
  is ambiguous **across four forms until it is read with its document scope**. That scope exists end
  to end and is authoritative: the `instruction_sections` frame stamps `document_id` per section
  (317 sections on the 1040 booklet split 70 / 114 / 67 / 66), `_spans_for_instruction_frame` carries
  it onto the span as `owner_document_id`, and `instruction_span_ids_for_line` filters on it.
  - **A cell may only receive an instruction its own form owns**, directly or by the one permitted
    sub-line inheritance (`11a` inherits `Line 11` when nothing owns `11a`). **A wrong instruction is
    worse than none, because the model will use it.** Form 1040 line 9 is total income; Schedule 2
    line 9 is household employment taxes; they share a number and nothing else.
  - **A line's owner is `line_tokens`, not `line`.** One section headed *"Lines 1a Through 1z"* owns
    all twenty-six. Reading only the first token is what makes a heading look absent.
  - **ONE ACCESSOR OWNS THIS QUESTION: `instruction_span_ids_for_line`.** Reports, checks and
    surfaces ask it; none of them may re-implement the match. The S116 report did, and disagreed with
    the pipeline on 46 cells while the pipeline was right every time.

- **S3a -> S3b: YES, the structure step owns a deterministic outline adapter. S3a regeneration
  stays blocked until it lands. (Answered 2026-08-02; open since 2026-07-28.)** The bare positional
  index is not enough, and the reason is the one this phase already discovered twice: **identity
  must be resolved in CODE from a stable anchor, never from position.** An exact string offset that
  can land on repeated anchor text in another semantic row is position-based identity - the same
  class of defect as keying the review queue on generated sequence ids (100% churn) and as asking
  the model to name a `quote_span_id` (fixed in S28). The adapter belongs to S3b because
  `PHASE_M20.md` section 3 is explicit that this pipeline never had an independent structure layer
  and that building one IS S3b; an outline is structure, not regeneration. Requirements: build it
  from the corrected text plus `line_anchors` plus page/geometry, resolve each anchor to exactly
  one semantic row, and **fail closed at row granularity** when an anchor is ambiguous - matching
  the S2d/S2e span-resolver ruling. Do not promote a draft or hand-edit a citation or label to get
  past an ambiguity.

- **THE MATCHER IS MODEL-OWNED AND THE MODEL MUST BE NAIVE ABOUT THE CELLS (John, 2026-08-17).**
  *"I'm afraid to give a model too much if it is to pick out the instructions. We have the example
  of line 24 referencing line 22 and the instructions for line 22 get jammed in."* **Asking a model
  for one cell's instruction is a question with a demand in it; asking it to describe a document's
  sections is not.** So the model segments the booklet, never sees a cell, and CODE does the join.
  This is the same boundary as 2026-08-02 - form face exact, instruction pages loose, AI reconciles.
  **The inverse question is permitted and is not a bend of this rule:** over a span whose boundaries
  are ALREADY fixed and byte-verified, *"which lines does this span govern, or none?"* cannot drag a
  neighbour's text in, because the model is labelling a boundary it did not choose.
  **Corollary, proven over five rounds S116-S120: the DETERMINISTIC matcher line is closed.** Each
  round found the previous one's blind spot - cross-form `Line 9`, multi-line headings, nested
  duplicates, worksheet row numbers read as form lines - all semantics a person reads instantly and
  a heading parser cannot. **Do not spec another one.**

## Standing constraints (every M20 round)

- **A RECORDING VERIFIES CODE PATHS AND NEVER MODEL BEHAVIOUR (Architect, learned three times:
  S109, S121, S124).** A replay harness cannot predict what a CHANGED prompt makes the live model
  emit - on the S109 tree it reported `production prompt differs from recorded prompt` on 19 of 20
  cases. **Never accept a reconciliation or prompt change on replay evidence alone**, and never read
  a green harness as permission to skip the re-derive. Nor is the model deterministic under a fixed
  seed: Schedule D returned 93 raw sections recorded and 105 live.
  **A live recording is bought with money and is NOT regenerable output.** Merge into it; never
  clobber it.

- **RE-DERIVE THE BLAST RADIUS, NOT THE CORPUS. WE ARE IN WALK, NOT RUN (John, 2026-08-17).** *"I
  remember when we thought things were working that I urged you to input all docs. Now, however, we
  are back in walk stage (crawl-walk-run). Perhaps we don't need to process every core doc and
  worksheet to work on the pipeline?"* **He is right, and the full-corpus habit was costing an hour
  per round to verify changes whose reach was computable in seconds.**
  - **Compute what the change can touch, then re-derive exactly those documents** with
    `extract --doc <id>`. S118 is the worked example: it altered **19 cell packets living in 4
    documents** (`form_1040`, `form_1116`, `schedule_1`, `schedule_3`). Those four were the whole
    verification; the other thirteen could not move and re-running them proved nothing.
  - **If the blast radius is not computable, that is the finding** - say so and then run wide. Do
    not use "I could not tell" as a reason to skip verification.
  - **THE FULL CORPUS IS FOR MEASUREMENT, NOT FOR ROUND VERIFICATION.** Reserve it for coverage
    numbers, stability ranges, phase-level acceptance, and prompt or schema changes that reach every
    document. **A prompt change has no blast radius and always runs wide.**
  - **THIS DOES NOT LOOSEN "BREADTH BEFORE DEPTH" (John, 2026-08-09), WHICH IS ABOUT A DIFFERENT
    THING.** That rule forbids *designing* a construct off the 3-form dev set. This one governs how
    much to *re-run* to verify a change already designed against the whole inventory. **Measure
    broad; verify narrow.**

- **PROTECTED SET, hard gate - STILL IN FORCE, and it does not lift until its replacement exists.**
  `graph/2025/{nodes,edges,rules}/` and `graph/2025/field_maps/` must be byte-identical.
  `git diff --stat` on those directories must be EMPTY. No promotion, no hand-authoring, no live
  graph edit, no verdict write, no operation enum change.
  **John's 2026-08-05 pipeline-only ruling changes what this gate will protect, but NOT yet.** The
  promotion round archives the handcrafted set, re-points this gate at the archive, and only then
  opens the live graph to pipeline output. **Until that round lands and is accepted, this gate is
  unchanged** - a safety gate is never lifted before its replacement is in place, and every round
  before then still reports an empty protected-set diff.
  **WHAT THE BYTE-IDENTICAL CLAUSE DOES AND DOES NOT COVER (clarified 2026-08-19, after John asked
  what the protected set was).** It names those four directories and nothing else.
  `graph/2025/citations/` is NOT in it; what catches a citation write is the broader *"no live graph
  edit"* clause above, which is a per-instance escalation to John, not a byte-identical check.
  **He approved one on 2026-08-19**: 78 machine-derived, independently verified source ranges into
  `graph/2025/citations/`, applied by `citation_range_patch --write`. Approval was for that write,
  and does not generalise to the next one.
  **`graph_ext/` IS EFFECTIVELY UNWRITABLE AND THAT IS WORKING AS DESIGNED.** Its `extension.json`
  carries a stamped `content_hash` the loader enforces, and the directory is gitignored, so an edit
  there both fails `load_graph` closed and is invisible in review. Do not hand-stamp the hash; the
  accept path owns it.
- **A HUMAN COMMENT IS A BUG REPORT, NOT A PATCH (John, 2026-08-10).** Reviewer correctives are a
  **last-ditch band-aid and must NOT be relied on for the identified core document set.** No hand
  crafting in that set either. **A stored comment that makes a cell correct IS hand-authoring under
  another name** - the graph then looks pipeline-derived while being hand-steered, and nobody can
  tell which cells are which. **Every corrective must produce a PIPELINE change; otherwise the
  band-aid silently becomes the mechanism.**
  **What IS allowed and preferred:** AI models making the decision, voting, and **telltale
  indicators printed in the documents themselves.** The whole 11-document run costs $0.25, so
  three-way voting on disagreements is affordable.
  **Proven value of printed telltales, both found 2026-08-09:** "Keep for Your Records" marks every
  worksheet box, and the line number brackets its clause on **95% of 406 anchors**. Ask what the
  FORM tells us before writing a parser.
  **The re-ask loop (`rederive_cell(document_id, line, draft_comment)`) is the DIAGNOSTIC for this.**
  Measured 2026-08-10: a corrective stating the right answer made the model produce the correct
  answer on 4 of 4 rows, and **all 4 were then rejected by system limits** - a corrective that still
  fails names the missing capability. **Prohibitions do the opposite:** "never do X" produced
  wrong-but-passing answers on 3 of 4, dropping a column and losing half a rule while going green.
- **A NAMED WORKSHEET IS ITS OWN DOCUMENT, however small (John, 2026-08-09).** If the instructions
  call it a worksheet, it is modelled in the graph as a document with its own lines - **naming
  decides, not size and not how many rows reference it.** The Credit Limit Worksheet's 3 steps get
  the same treatment as the Schedule D Tax Worksheet's 30. This is the predictable reference system:
  a worksheet line is addressable, so nothing has to guess where its numbers belong.
  **A consequence, and it is the fix for a real defect:** an unharvested worksheet leaves its step
  numbers sitting inside the PARENT row's instruction text, where the validator reads them as the
  parent's line numbers. Measured 2026-08-09: **9 rows misread a worksheet's steps as their own**,
  and `schedule_d_2025` line 21 reads "Subtract line 4 from line 3" when its real rule is
  "Subtract line 32 from line 23".
- **`derive_cells` must remain pure - zero disk writes.**
- **PYTEST TEMP ROOT MUST BE SHORT** (e.g. `C:\tgt`). An Architect session was burned reporting 22
  suite failures of which 8+ were `WinError 206` path-length artifacts of a deep temp root. With a
  short root the same files went 11 failed -> 3.
- **KNOWN-RED BASELINE - inherit it, do not get blamed for it, do not fix it in an unrelated
  round.** All three depend on untracked local state, which is why CI is green:
  - `test_review_scope_migration_m15.py::test_live_queue_migration_...` (FileNotFoundError,
    `review_queue/2025/deferred_review.yaml` - tracked dir with no files)
  - `test_schedule_2_m16.py::test_schedule_2_part_i_raw_acroform_identity` (`assert '1a' == 'z'`;
    reads gitignored `.cache/raw/.../schedule_2_2025.fields.json`, regenerated 2026-07-28 while
    the source PDF is unchanged, so a code-only bisect proves nothing)
  - `test_address_campaign_m15r.py::test_form_8949_cross_form_claims_resolve_exactly`
    (`realized 0, expected 6`)
  - `test_schedule_d_extraction_m9.py::test_schedule_d_fixture_drafts_include_schema_valid_band_tables`
    (added 2026-08-03; Architect bisected it against the S35 resolver change and it fails
    identically with that change reverted, so it predates S35)
- **THE WORKER CAN REACH THE PROVIDER. Diagnosed and fixed 2026-08-09; the old "no outbound
  network" rule was TRUE BUT NOT THE WHOLE TRUTH and cost three rounds.** Measured on this host:
  network is blocked under the default `workspace-write` sandbox (connect refused in ~15ms), and
  **the documented toggle `sandbox_workspace_write.network_access=true` DOES NOT WORK on this
  Windows build** - it stays blocked, which is almost certainly why this was written off.
  `sandbox_mode="danger-full-access"` restores it: `curl` to OpenRouter returns 200 and
  `.venv\Scripts\python.exe` reaches `https://openrouter.ai` with status 200.
  **SCOPE THE ESCAPE TO ONE COMMAND, never the whole session** - ordinary edit and test work stays
  sandboxed:

  ```
  codex sandbox -c 'sandbox_mode="danger-full-access"' -- .venv\Scripts\python.exe experiments\derive_cells_s25.py --year 2025 --output-dir <RUN> --document form_1040_2025
  ```

  Python itself works fine under the DEFAULT sandbox, so only the provider leg needs this.
  **A round may still be declared fixture-only, but "the sandbox has no network" is no longer a
  reason to skip a live leg.**
- **Model is `openai/gpt-5.6-luna`** in `tax-graph.config.yaml` (`llm.micro_model`). Do not switch
  to `google/gemini-3.6-flash` - measured ~15x the cost at our call volume.
- **Evidence discipline:** honest `RAN:` / `NOT RUN:` lines with exact commands and exact output.
  Never a guess, never a paraphrase of a number.

### Worker environment (2026-07-23)
The recurring `Access is denied` on `.venv\Scripts\python.exe` was the venv launcher shim spawning
the OUT-OF-WORKSPACE base interpreter, which the Codex sandbox denies per session (it is NOT a
machine state and no restart fixes it). Fixed by mirroring the base interpreter to `.python313/`
inside the repo (gitignored) and rebuilding `.venv` on it, so `pyvenv.cfg home` is in-workspace.
Workers call `.venv\Scripts\python.exe` directly - no `uv` needed.
**Do NOT pass `--basetemp`** (2026-07-25). The root `conftest.py` pins the temp root for every
account and pytest separates accounts via `pytest-of-<username>/`. The old `.pytest_tmp` is
poisoned and unreclaimable; see the hard rule in `AGENTS.md`.
**Launcher cap is 600s** (John, 2026-07-26; was ~124s, then 240s). The Worker runs its OWN e2e and
app-dependent files. Only full partitions and Tier 3 shakedowns stay Architect-side. Anything that
still does not fit gets an honest `NOT RUN:`.
**ALWAYS use the module form, never the console scripts** (2026-07-23, M16-S4):
`.venv\Scripts\python.exe -m tax_graph.cli validate 2025` and
`.venv\Scripts\python.exe -m workbench.cli preflight --year 2025`. The generated `tax-graph.exe` /
`review-workbench.exe` launchers resolve the package through the editable install's `.pth`, which
hardcodes an absolute repo path that does not resolve inside the Codex sandbox
(`ModuleNotFoundError: No module named 'tax_graph.cli'`). Architects: write the module form into
Worker prompts.

### Architect-driven Codex Worker (John authorized 2026-08-19)
The Architect may start Worker rounds directly with `bash tools/codex.sh "<prompt>"`, which runs
`codex exec --sandbox danger-full-access`. **John keeps the acceptance gate; nothing lands on `main`
without him.** Read the header of `tools/codex.sh` before changing any of this.
- **ONE ROUND, ONE FRESH SESSION (John, 2026-08-19).** The coding cycles are discrete and stale
  context gums them up. **Never `codex exec resume`.** Round state lives in
  `plans/AGENT_HANDOFF.md`; that is what the next session reads.
- **Auth is John's ChatGPT Plus subscription, not an API key.** Verified 2026-08-19:
  `codex login status` reports "Logged in using ChatGPT" and `auth.json` carries
  `auth_mode: "chatgpt"` with a null `OPENAI_API_KEY` field. The wrapper strips `OPENAI_API_KEY`
  from the environment so a round cannot reach it. **The cost of a round is Plus quota, not
  dollars** - it competes with John's own use of the Codex app.
- **TO TURN THE API KEY BACK ON** if the subscription proves unworkable: delete `env -u
  OPENAI_API_KEY` from the `exec` line at the bottom of `tools/codex.sh`. That one line is the
  whole switch. Permanently instead: `printenv OPENAI_API_KEY | codex login --with-api-key`, and
  back with `codex login`.
- **Reasoning effort is HIGH, not xhigh (John, 2026-08-19)**, in three places that must stay in
  step: `tools/codex.sh`, `~/.codex/config.toml`, and `llm.reasoning_effort` in
  `tax-graph.config.yaml`. The pipeline value was previously UNSET, so it now sends a reasoning
  field where it sent none - **the first corpus run after 2026-08-19 is not comparable to the runs
  before it.**
- **TWO WORKERS CAN LAND ON ONE TREE, AND IT HAPPENED ON THE FIRST ROUND (2026-08-19).** John
  started S144 in the Codex app while the Architect started S144 through the CLI. Both edited the
  same files; the CLI session detected the collision, refused to commit, and John's app session
  committed the round (`3dd28d9`). **No work was lost, but the round was paid for twice.** Before
  starting a round from the CLI, say so and check that John does not already have one running.
- **The egress rule is unchanged.** Giving the Architect the CLI moved no API spend: pipeline model
  calls still bill separately and still need John's per-round grant. A round floor still may not
  authorize its own network access.

**Recurring op note:** orphaned `serve` processes have first-class tooling -
`tax-graph serve --sweep-orphans`. The parent watchdog works on Windows as of M14 (OpenProcess
probe). Serve writes stderr breadcrumbs that Claude Desktop logs verbatim - first stop when a
client-managed server dies.
