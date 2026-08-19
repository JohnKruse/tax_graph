# AGENT_HANDOFF.md

The single living doc for active Claude (Architect) <-> Codex (Worker) coordination. Update it in
place; do NOT spawn new per-topic note files. Standing rules: `../AGENTS.md`. Master plan:
`../docs/engineering-plan.md`. Phase plan: `PHASE_M20.md`.

## How to use
- **Worker:** raise questions/blocks under **Open for Architect**.
- **Architect:** answer there (and pin durable decisions into the relevant `PHASE_<id>.md`), then
  clear the item. Record active direction under **From Architect**.
- **THIS FILE IS LIVE STATE ONLY.** The ball, the round in flight, the open questions, and the
  ONE task spec being worked. Durable rulings and standing constraints live in `../AGENTS.md`
  and are never pruned. History lives in git. **Queued future rounds are ONE LINE each** - a
  full spec written rounds ahead goes stale, which is exactly what happened to S57.
- **Keep it short.** A round that completes gets its narration DELETED, not appended - the
  accepted hash is the record and `git show <hash>` recovers everything. Only the current round,
  the standing constraints, and the binding rulings live here.
- **Prune at every acceptance, not "at phase close".** Pruned 2026-07-23 to 1,198 lines, then
  grew to 7,520 by 2026-08-02 because acceptance never triggered a prune. That is the failure
  mode this section exists to prevent.

## BALL

**BALL: CODEX. M20-S143 is implemented and verified below. The narrowest owner is now primary;
family spans remain as context.**

**M20-S142 IS ACCEPTED (`c613c78`, Architect, 2026-08-19), VERIFIED BY RECOMPUTATION AND BY OPENING
THE CELLS.** My independent count reproduces Codex's table to the cell: `form_1040` 55/22,
`schedule_1` 31/30, `schedule_2` 39/3, `schedule_3` 29/2 - **line-level 106 -> 154, block-level
105 -> 57, covered total unchanged at 211.** I then opened the projected text rather than trusting
the count. Schedule 2 line `17f` now reads *"**Line 17f.** Enter any additional tax on Medicare
Advantage MSA distributions from Form 8853, line 13b"*; before it read line 17a's recapture text.
**The exact failure John named is gone from Schedule 2 and Schedule 3.** ITEM 2 held: Schedule 1's
`8a` through `8z` have no run-in label in their span and correctly kept the block.

**THE METRIC I GAVE CODEX OVERCOUNTS AND I AM CORRECTING IT BEFORE IT SETS.** "Block-level" counted
CELLS sharing a citation, but several physical cells legitimately carry the SAME line (`4c` is four
cells), and one citation across four cells of one line is not the jamming defect. **Counted over
DISTINCT LINES, which is the honest denominator: 189 covered lines, 151 own their text, 38 share a
block across lines.** Per document: `form_1040` 56/6, `schedule_1` 30/30, `schedule_2` 38/0,
`schedule_3` 27/2. **S142 was better than its own table said**, and **30 of the 38 remaining are
Schedule 1**. Use lines, not cells, from here on.

**THE 30 ARE NOT AN ACQUISITION GAP AND NOT A SPLITTING PROBLEM - THE RIGHT SPAN IS ALREADY THERE
AND WE PICK THE WRONG ONE.** `instruction_ids_by_line["8j"]` holds TWO spans: the 433-character
family preamble `section_0067`, whose `owner_lines` lists all 26 of `8a`-`8z`, and `section_0077`,
whose `owner_lines` is exactly `['8j']` and whose text is *"#### Line 8j - **Activity not engaged in
for profit income.** See Pub. 535"*. **The projection takes `[0]`, and `[0]` is whichever span comes
first, which is always the family.** Same shape at `24a`-`24z` (`section_0109` versus `section_0110`
onward). That is the whole of Schedule 1's residue.

**FULL SUITE RED BASELINE IS 22, AND THE SUITE SITS AT 28.** The difference is the six broken S115
workbench cases - a defect awaiting a round, not an accepted red. Eleven `tests/e2e/*_m15.py`, plus
`test_address_campaign_m15r::test_form_8949_cross_form_claims_resolve_exactly`,
`test_field_identity_m16::test_schedule_2_raw_cache_reproduces_target_fields`,
`test_m20_s71::test_real_candidate_node_labels_use_clean_text`,
`test_review_preflight_m15::test_real_2025_preflight_passes_with_all_coverage_dimensions`,
`test_review_scope_migration_m15::test_live_queue_migration_gives_every_pending_entry_a_primary_target`,
`test_schedule_2_m16::test_schedule_2_part_i_raw_acroform_identity`,
`test_schedule_d_extraction_m9::test_schedule_d_fixture_drafts_include_schema_valid_band_tables`,
`test_extract_outline_m4::test_instruction_section_body_survives_deeper_heading`,
`test_citation_cleanup_m18::test_real_citation_corpus_has_source_verified_cleanups`, and both
`test_generated_review_m20` line 1a is red for the reason in
Queued below (W-2 box 1 versus `entered by filer`); do not silence it.**

**STILL OWED, UNCHANGED:** the S115 review contract needs a LIVE check, not a test read - six cases
die at `workbench/server.py:640` on `object_ref` and cannot be bisected because they skip without
`_drafts` and error at setup with it. **That is the surface John reviews and it has been unverified
since 2026-08-16.**

**THE CITATION RANGE BACKLOG IS APPLIED (John approved 2026-08-19).** `citation_range_patch --write`
put **78** ranges into `graph/2025/citations/instruction-form-1040-html.yaml` (71) and
`intake.yaml` (7). **Unverifiable citations 114 -> 36; checked 515 -> 593, zero mismatches, and the
bad-provenance findings stay at exactly 2** - none of the added ranges introduced one. The
protected set (`nodes`, `edges`, `rules`, `field_maps`) has an empty diff and the edit is additive:
242 insertions, 0 deletions.

**I TOLD JOHN 114 -> 14 AND THE HONEST NUMBER IS 114 -> 36. TWO CORRECTIONS I OWE.** The proposal
was **100, not 99** - the S136 follow-up (`b3050d5`) added one. And **22 of the 100 could not be
written**: they live in `graph_ext/2025/form_2441_2025/citations.yaml`, which carries a stamped
`content_hash` the loader enforces and which is **gitignored**. Writing there broke `load_graph`
closed on the first attempt; I reverted it and **proved the revert byte-identical by recomputing
the extension hash against the stamp**. The applier now defers overlay-held citations by design
rather than raising. **14 of the remaining 36 are HTML-only and no range can fix them; the other 22
are the 2441 overlay and they land in the round that retires it** - `AGENTS.md` already condemns
that overlay as a surviving special case.

**Durable findings from S128-S142 are now pinned in `PHASE_M20.md` section 4.2** - the OCR-damage
acquisition finding, the mentioning-versus-governing result, Schedule 1-A's real ceiling, and the
do-not-drop-`quoted_text` constraint. They are no longer repeated here.

## Current round

**M20-S143 IS ACCEPTED.** `instruction_ids_by_line` now orders candidates by the number of
explicit or inferred owner lines. Equal-width ties prefer a content-bearing span over a heading
stub, then retain artifact order. The family citation is never dropped.

Distinct-line recomputation (covered / own text / shared block):

- `form_1040`: 62/56/6 -> 62/56/6
- `schedule_1`: 60/30/30 -> 60/60/0
- `schedule_2`: 38/38/0 -> 38/38/0
- `schedule_3`: 29/27/2 -> 29/27/2
- total: 189/151/38 -> 189/181/8

The 1040 generated gap-cell count stayed 55 before and after. The three opened Schedule 1
projections changed as follows:

- `8j`: the family preamble was primary; now `#### Line 8j` and `Activity not engaged in for
  profit income. See Pub. 525.` is primary, with the family span retained second.
- `24z`: the `Lines 24a Through 24z` block was primary; now `Line 24z` / `Leave line 24z blank.`
  is primary, with the family span retained second.
- `1`: the empty `#### Line 1` stub was primary; the deliberate content-over-stub tie-break now
  makes the 30,083-character State and Local Income Tax Refund Worksheet primary. The existing
  third cross-document candidate and the heading stub remain later in the list; no citation was
  dropped and no artifact was edited.

RAN: `.venv\Scripts\python.exe -m pytest tests/test_m20_s143.py -q` -> 3 passed in 2.63s.
RAN: `.venv\Scripts\python.exe -m pytest tests/test_m20_s142.py tests/test_m20_s143.py tests/test_generated_review_m20.py -q` -> 15 passed, 1 failed; the only failure is the known line 1a W-2-box-1 guard red, not S143.
RAN: `.venv\Scripts\python.exe -m pytest tests/test_workbench_m15.py -q` -> 4 passed in 0.38s.
RAN: `.venv\Scripts\python.exe -m pytest tests/test_workbench_cells_api_m17.py tests/test_workbench_write_api_m15.py tests/e2e/test_workbench_v2_m17.py -q` -> 18 passed, 1 xpassed in 360.78s.
RAN: `.venv\Scripts\python.exe tools/check_ascii.py workbench/generated_review.py tests/test_generated_review_m20.py tests/test_m20_s143.py` -> ASCII check OK.
RAN: `git diff --check` -> clean.
NOT RUN: full suite -> prohibited for this round.

---

**WHAT MUST NOT HAPPEN.**
- **No draft regeneration or hand-edit**, no promoted-artifact write, no review-contract change.
- **Do not drop a family citation** to make the ratio look better.
- **Do not derive ownership from line references in prose.** See `PHASE_M20.md` 4.2 - it scores well
  and is wrong in every instance. Ownership comes from `owner_lines` and headings only.
- **No model call, no network.**

**THE FLOOR.**
- **Per-line counts per document, before and after**, and the three quoted cells from ITEM 4.
- **The 1040 gap ceiling guard stays `<=`** and does not grow.
- **Focused workbench, API and e2e sets green** against their known reds.
- **NO FULL SUITE FROM THE WORKER OR THE ARCHITECT THIS ROUND.** The Worker's focused sets plus the
  Architect's recomputation are the check.
- **`check_ascii` OK**, `git diff --check` clean, protected set byte-identical.

## Open for Architect

- **ANSWERED 2026-08-19, see Current round: the guards are stale, not the drafts.** They were
  committed 2026-08-16 and the drafts were regenerated 2026-08-17 14:31 by the accepted corpus run.
  Codex was right to refuse the hand fix and right to escalate.

## Queued (ONE LINE each - do not spec ahead)

- **[SUPERSEDED 2026-08-19 - THE FRAME WAS NEVER THE PROBLEM; SEE M20-S140.]** I queued this as
  "the pilot frame is not wired in". Wrong: the draft's own `instruction_sections.yaml` already
  holds the `Line 1i` section, text and all. **The gap is the section-to-citation join, 39 of 54
  lines**, and it is the current round.

- **DOES 1040 LINE 1a DERIVE FROM W-2 BOX 1, OR IS `filer_entry` CORRECT? (Architect, 2026-08-19.)**
  The line reads *"Total amount from Form(s) W-2, box 1"*, `form_w2_2025` IS in the manifest, and
  the 2026-08-17 draft carries a node and a `1a -> 1z` addend edge but **no rule at all**. Under
  John's 2026-08-16 taxonomy that is **`derivation_failed`, a defect - not
  `source_form_not_modelled`.** Surfaced by an S115 workbench guard that expected
  `line 1a = W-2 box 1`; **the guard is being relaxed in M20-S138 and this question must not go with
  it.** Needs a re-derive, so it needs John's egress.

**JOHN'S PRIORITY, 2026-08-10: get the CORE documents processing reliably.** Ordered for that.
**Every item below is a PIPELINE change - none of them is a per-cell human correction.**

**THE ACQUISITION FINDING AND THE SCOREBOARD IT PRODUCED LIVE IN BALL.** What remains queued off it:

- **CONSTRAIN `governs` TO A LINE TOKEN OR EMPTY IN THE STRUCTURED-OUTPUT SCHEMA (Architect,
  measured 2026-08-18).** 93 distinct non-line values are in the live 1040 frame; the join key
  accepts free text today. **Prompt/schema change - no blast radius, runs wide, needs a live call.**
- **[APPROVED BY JOHN 2026-08-18 - THE NEXT ROUND AFTER M20-S133] ATTRIBUTION AS ITS OWN STAGE OVER
  BOUNDED SPANS.** Ask, of a span whose boundaries are ALREADY fixed and byte-verified, *"which of
  this form's lines does this span govern, or none?"* **Permitted by the binding ruling pinned in
  AGENTS.md**: the model is labelling a boundary it did not choose, so it cannot drag a neighbour's
  text in. **Its honest prize is 19 Schedule 1-A cells, not 37** - see BALL.
  **FOUR CONSTRAINTS, ALL FROM OPENING THE 37, AND THE FIRST IS THE ROUND:**
  1. **IT MUST NOT BE A LINE-REFERENCE MINER.** Measured: in this chapter, prose that GOVERNS a
     line never names it, and prose that NAMES a line does not govern it. A miner reaches none of
     the 19 and gets every mention wrong. **If the round produces a regex over body prose, it has
     failed regardless of its score.**
  2. **THE MODEL NEEDS THE FORM'S LINE INVENTORY AND THAT DOES NOT BREAK CELL-NAIVETY.** It cannot
     answer *"which lines does this govern"* without knowing which lines exist. **A closed menu
     attached to a fixed span is a lookup; a demand to go find one cell's instruction is not.**
     The inventory is the printed anchors we already hold - no model call to build it.
  3. **EMPTY IS A FIRST-CLASS ANSWER AND MOST SPANS MUST TAKE IT.** 18 of 37 cells have no prose at
     all, and 50 of the 69 sections govern no line. **A run where few spans answer "none" is
     evidence of fabrication, not coverage** - report the "none" rate as a headline, not a footnote.
  4. **SCORE IT AGAINST WHAT THE PROSE ACTUALLY SAYS, NOT AGAINST 48.** The reference answer is the
     19, and the 18 arithmetic cells are a CEILING - reaching them would mean the model invented an
     instruction. **Do not write a floor that counts them as misses.**
  **NEEDS JOHN'S EGRESS - it is a live model call**, and it changes the prompt, so it has no blast
  radius and runs wide.
- **[DONE 2026-08-18 - see BALL] SCHEDULE 1-A'S 37 UNREACHED CELLS ARE OPENED.** 19 have governing
  prose, 18 are the instruction ceiling, and mentioning a line is anti-correlated with governing it.
- **DOES THE IRS PUBLISH THE LOOKUP TABLES AS THEIR OWN PAGES?** The 2025 Tax Table and the EIC
  tables are the only content the HTML does not carry, and they are the last thing holding the OCR
  path open. **The tax table itself is already modelled** - `tax_graph/compile/tax_table.py` builds
  2,062 bands from the authored brackets and the engine matches OTS - so what a clean copy buys is
  verification against something other than our own inputs, not a new capability.
- **NO MCP TOOL RESOLVES A RANGE TO TEXT (Architect, 2026-08-18).** `get_document` returns a
  document object and `get_citation` the stored record. Attaching augmenting context BY REFERENCE
  needs the accessor M20-S133 builds, exposed as a tool.
- **`sibling_worksheet_owner` MASKS WORKSHEET-TO-WORKSHEET MISATTRIBUTION (Architect, measured
  2026-08-17).** Correct today only because all four Schedule D worksheets have 0 cells in the
  reconciliation population. **The moment worksheet cells enter it, a row attributed to the WRONG
  sibling scores as correct.** Key it on whether the owner is the cell's own document.
- **[SPECCED, DEFERRED - full spec at `5e9230c`] M20-S125: MAKE THE COVERAGE METRIC HONEST.**
  `model_reachable` counts a foreign worksheet's row number as reach.
- **`_write_recording` CLOBBERS THE FIXTURE INSTEAD OF MERGING (Architect, read 2026-08-17).** It
  writes only the booklet just run, so pointing `--output` at
  `instruction_segmenter_live_recordings.json` **destroys the paid Schedule B and D recordings**
  every floor since S121 rests on. Merge by `source_document_id`; until then write to a new path.

**DIRECTION PINNED 2026-08-13 IN `../docs/source-extents.md`. DO NOT REDESIGN IT HERE.** A citation
should record WHERE its text is, not carry a copy of it, and a source chunk that is not a numbered
row should say what it is and what it governs. **ORDER MATTERS AND M20-S133 IS THE FIRST STEP:
dropping `quoted_text` before the ranges are checkable would freeze an unverified range where
nothing can ever see it.** The stored copy is the only reason the defect was detectable at all.
**The queue has NOT been reshaped around the doc yet - that is John's call.** What the doc settles
is that items 2, 3, 6 and the recurring extent defects are one root cause and should stop being
specced as separate cue-matching repairs.

**ITEM 1 IS DELIVERED.** Prior-year documents were M20-S102, accepted at `ee6eb55`. The graph now
has the concept, the gate is correct on the real rows, and `status: unresolved` prior-year stubs
carry their own year. **The four documents item 1 also named remain open** and belong to items 4
and 6: `schedule_se_2025` and `form_6252_2025` are real IRS forms absent from the manifest;
`form_w2_2025` and `form_1099_g_2025` are information returns, which
`../docs/source-extents.md` records as NOT covered by the extents work.

1. **[SPECCED AS M20-S102, 2026-08-12 - see Current round]
   PRIOR-YEAR DOCUMENTS ARE A CATEGORY THE GRAPH HAS NO CONCEPT OF** (Architect, measured
   2026-08-11 on the live derivation of the promoted worksheets). Simplified Method lines 2 and 6
   fail with `operand_document_not_found: simplified_method_worksheet_2024` because the printed row
   says *"enter the amount from line 4 of last year's worksheet"* - **the model read it correctly
   and the graph has nowhere to put it.** This recurs anywhere a worksheet carries a balance
   forward. **It is NOT the out-of-corpus stub case** (item 6): the document exists, it is just a
   different tax year. Decide whether a prior-year reference is an input the filer supplies, a
   distinct document, or an edge to the same document in another year.
   **The same run named four genuinely missing documents:** `schedule_se_2025` and `form_6252_2025`
   are real IRS forms absent from the manifest (the Form 1116 case in item 4); `form_w2_2025` and
   `form_1099_g_2025` are information returns and belong to the stub work.

2. **170 OF 404 PRINTED ANCHORS (42%) DERIVE WITH AN EMPTY INSTRUCTION PACKET** (Architect,
   measured 2026-08-11 on the production path, `for_line` at `cells.py:291`). Per form empty:
   6251 61%, schedule_d 54%, 2441 45%, schedule_a 32%, 1040 29%, schedule_3 23%, schedule_2 16%,
   schedule_1 13% - and **schedule_1a and schedule_b are 100%, all 56 anchors, zero sections**.
   **Not a parser bug: `instruction_sections` creates a slice only under a heading that NAMES a
   form line**, and Schedule B and Schedule 1-A organise their booklets by Part and topic
   (`Part I. Interest`, `No Tax on Tips`), naming no lines. **HTML does not fix it** - the same
   headings appear there, so this is the IRS's organisation, not our rendering. Same defect family
   as S97: keying on a printed cue and silently dropping everything the cue misses.
   **MEASURED 2026-08-11 (Architect, live A/B, 6 rows that are BOTH broken AND empty-packet). THE
   ANSWER IS DISAPPOINTING AND IT SETTLES THE ORDERING: DO NOT JUMP THIS AHEAD.** Arm A is
   production today; arm B injects the booklet text that actually discusses the line.
   **ONE clean win in 6:** `schedule_b_2025` `8` error -> repaired as `require_input`, and that IS
   right - the form face reads "foreign trust? If 'Yes,' you may have to file Form 3520", a filer
   question, not a computation.
   **ONE DEGENERATE PASS, and counting it would be lying:** `form_6251_2025` `8` error -> derived as
   `require_input`. The form face is "Alternative minimum tax foreign tax credit", which comes from
   an AMT Form 1116. Arm A failed HONESTLY with `operand_document_not_found: form_1116_2025`;
   arm B went green by declaring the value filer-supplied and **dropping the cross-form rule**. That
   is the wrong-but-passing shape AGENTS.md already warns about. Its real fix is queue item 4.
   **ONE ARM INVALID:** `schedule_b_2025` `5` arm B died on `missing_instruction_locator` - my
   injected text carried no locator, so that row measured my harness, not the question.
   **THREE FAIL FOR REASONS INSTRUCTIONS CANNOT TOUCH:** `form_6251_2025` `1a` and
   `schedule_1a_2025` `14a` are `incomplete_evidence` on the FORM FACE, identical in both arms;
   `schedule_d_2025` `4` is `operand_document_not_found` for `form_4684_2025`, identical in both
   arms. **The dominant blockers in this sample are form-face completeness and out-of-corpus form
   stubs - already queued as items 3 and 9 - not the missing instructions.**
   **CAVEAT, stated so nobody over-reads it:** n=6, one arm invalidated, one sample per arm and no
   repeat runs. Indicative, not conclusive. **It is enough to keep this behind the worksheet line,
   not enough to close the item** - 170 anchors still derive blind and that remains a real defect.
3. **UNTITLED COMPUTATIONS THAT CARRY WORKSHEET WEIGHT** (Architect, 2026-08-11). The EIC
   `## Step N` blocks compute real quantities - `Step 2 Investment Income` sums 1040 `2a`+`2b`+`3b`
   +`7a` with a floor rule and an $11,950 threshold - but have no title and no local line numbers,
   and `Step 5 Earned Income` contains an **untitled worksheet** whose lines 1-5 interleave with the
   surrounding question numbering. **This is the other half of the 4-row validator-scope cluster**
   (1040 `5a`, `5b`, `27a`, 2441 `10`): unharvested because there is no title to key on.
   **Proposed rule: a printed address decides.** Titled and line-numbered becomes a document;
   untitled becomes an intermediate node owned by the line it feeds. **The false-positive fixture is
   Schedule D `Wash Sales`**, a numbered list 1-4 that is conditions, not arithmetic.
4. **MARK THE CORE SET IN THE MANIFEST, AND ACQUIRE FORM 1116** (John, 2026-08-11).
   **JOHN'S RULING:** core is Tier 1 + Tier 2 of `docs/tax_graph_requirements.md` section 9,
   **PLUS Schedule A, Schedule 1-A, and Form 6251**. **Form 2441 is NOT core** - review-cycle tier.
   **ACQUIRE Form 1116 and its instructions:** documented first-phase in Tier 4, never added to the
   manifest, and it is already causing failures - the 2026-08-11 A/B shows `form_6251_2025` `8`
   dying on `operand_document_not_found: form_1116_2025`. **That is a missing CORE document, not an
   out-of-corpus form; do not stub it.**
   **THE GATE THE MARKING BUYS: core means ZERO UNREPORTED refusals.** Non-core may refuse, but the
   refusal must surface for review (item 5). John, 2026-08-11: *"a few extra is not a problem. I
   just didn't want to become the maintainer of everything."* **So the field should express
   OWNERSHIP, not only priority** - project-maintained, review-cycle, or community-contributed.
   **HEADS-UP, verified 2026-08-11:** `schemas/manifest.schema.json` `$defs.document` sets
   `additionalProperties: false` with 7 keys, so this is a SCHEMA change, not a YAML edit.
   **The tier list and the manifest have already drifted** - Schedule A, Schedule 1-A, 2441, and
   6251 are in the run and in no tier; 1116 and Pub 514 are in a tier and not in the manifest.
   **Fix the drift in the same round or it recurs.**
5. **[MOSTLY DELIVERED BY S100] A REFUSED WORKSHEET REACHING A HUMAN.** `pilot/review_panel.py`
   now reads `worksheet-discovery*.yaml` and separates promoted from refused with their reasons.
   **The RESIDUAL is the third clause only: a clear confirmation when a later run FIXES one.**
   Original entry, kept for its reasoning: (Architect, verified 2026-08-11). The
   harvester builds a `WorksheetFinding` with the reason and **the reason dies on the console**.
   `_copy_worksheet_drafts` only tracks documents ALREADY in the manifest, so a worksheet that was
   never built is not even reported missing - it is absent from the universe. `pilot/review_panel.py`
   has **zero** mentions of worksheets. **This is the alerting John asked for and it does not
   exist.** Needs: refusal reasons carried into the candidate, surfaced in the review UI, and a
   clear confirmation when a later run fixes one.
6. **STUBS FOR OUT-OF-CORPUS FORMS, and fix the `Form(s) X` alias.** 1040 `25c` hard-fails because
   the evidence says "Form(s) W-2G" and the matcher builds `form w2g`. Same "(s)" quirk that spared
   1040 `1a` from the reference guard.
7. **A LEAF MEANING "SUPPLIED HERE".** The only genuinely NEW vocabulary; needs the enum gate.
   Blocks 2441 `5`, where `REQUIRE_INPUT` is legal as a whole rule but not as a lookup branch.
8. **SKIP HUMAN-VERIFIED CELLS ON RERUN** - the step S94 deliberately left out. It must read the
   review ledger, **not a prior run's status**, because re-deriving an approved cell could silently
   replace an approved answer.
9. **Repair calls that return an unchanged payload** must be detected and not spent (2441 `5`).
10. **`CASE` / alternation** - still HELD; revisit with the wide-run evidence.
11. **"Report issue" from a reviewer corrective** (John, 2026-08-10) - optional and **never hidden**;
   emit a ready-to-paste GitHub body, no network and no auth to maintain. **Cluster by failure kind
   and answer shape, not by form**, so 50 reports of one cause collapse into one issue. Derivation
   runs on BLANK forms so the payload carries no filer data; **the reviewer's own comment is the one
   field needing a preview before sending.** Product work - after the core set is reliable.
12. **SHAREABLE FORM PACKAGES + THE FORM DIRECTORY** (John, 2026-08-11). Design PINNED in
    `docs/distribution.md`; **do not redesign it here.** Two build items only: an `install` verb
    that consumes another publisher's package, and a machine-readable index the README page is
    GENERATED from. **Product work - explicitly after the core set is reliable**, since a directory
    advertises a capability that a booklet silently dropping 26 of 28 worksheets cannot back.
13. **TWO S99 REPORTING NITS, neither changes what gets written** (Architect, measured 2026-08-11).
   **(a) An empty oracle result is still labelled `disagree`.** `worksheet_harvest.py:200` treats
   only `None` as `unavailable`, so a title found in the Markdown with zero numbered rows reads as
   a disagreement. **Four 1040 worksheets carry a bogus disagreement** (Qualified Tips, Multiple
   Trades, both Overtime), all with `markdown_lines=[]`. Cosmetic now that findings are advisory,
   but it dilutes a review queue that is meant to be a ranked worklist.
   **(b) Table 183's malformed claim counts as a refusal** even though its worksheet WAS harvested
   from table 182's window, so `refused=4` reads as four missing worksheets when two are the
   out-of-scope EIC blocks and one is this duplicate. **The overlap check should run BEFORE the
   validity check** - t183 was already owned, so it should have been a `window_claim_overlap`.
14. **THE `REFERENCES` EDGES ARE WRITTEN AND READ BY NOTHING** (Architect, verified 2026-08-11,
   carried forward unanswered from the S100 rework). `worksheet_harvest.py` mints them into every
   draft, `promote-worksheet` excludes them from promotion, and **no code in `tax_graph/` consumes
   that relationship** - the only other matches are SQL foreign keys. The exclusion's stated reason
   (that promoting them would make an unruled field look computed) does not hold. **Promote them or
   stop minting them; do not leave a dead relationship being written to disk.**
15. **Housekeeping:** `pilot/context_arms.py` still scores `REQUIRE_INPUT` as a recovered formula;
   run-together instruction headings (`**Line 2dDepletion**`) - **now explained: a PDF-render
   artifact, the HTML separates them cleanly (`28% Rate Gain Worksheet-Line 18`), so S97's division
   of authority may retire this**; artifact-pinned test counts measured
   against untracked `.cache/raw`; `form_8949_2025` needs table-form treatment (4 anchors, 0
   admitted); 2441 `19`/`21`/`25` are a KNOWN-UNSTABLE set - do not read them as signal.
16. **A MISSING CONFIG SECTION REPORTS AS A MISSING API KEY** (Architect, diagnosed 2026-08-12;
   John queued it the same day). The three-tier secret fallback John wanted **already exists** -
   `resolve_secret` (`tax_graph/config.py:167`) tries an explicit `api_key`, then the keyring named
   by `api_key_keyring`, then the env var named by `api_key_env`, then the persisted user
   environment - and `config/tax-graph.config.example.yaml` already documents it identically for
   `llm` and `ocr`. **Nothing is missing from the design.** What failed is the diagnostic: the local
   config had no `ocr:` section at all, so all three lookups returned `None` and the renderer said
   `RendererUnavailable: Mistral OCR requires an API key`. **That one string covers three different
   user mistakes** - no section, a section with no key source, and a key source that resolved empty -
   and it cost two sessions hunting for a key that was set the whole time. **Fix the message to name
   the actual condition, and add a `doctor` check that diffs the live config's sections against the
   example's** - verified 2026-08-12 that `doctor` has no config validation today, so this is the
   general cure rather than a per-section patch.

**REPORT EVERY ROUND WITH `pilot/run_report.py`** - per-document coverage against every printed
anchor, plus a row-level floor check. Validated against four real runs.

```
.venv\Scripts\python.exe pilot\run_report.py <RUN> --baseline C:\tmp\m20_s81_rest --baseline C:\tmp\m20_s81_run
```

**TEST FIXES ONE CELL AT A TIME, NOT WITH A CORPUS RUN.**
`rederive_cell(document_id, line, draft_comment)` is a discrete call - cents and seconds.
`pilot/row_bench.py` replays a recorded row for free. **An hour-long run to check a handful of rows
is not acceptable** (John, 2026-08-10).


## Standing operational notes

**NO DUPLICATE FULL SUITES, AND THE ARCHITECT STOPS RUNNING ONE PER ROUND (Architect, 2026-08-19).**
I started three full suites today and **every one was invalidated by the Worker committing under
it** - the tree moves the moment John launches the next round, and pytest collects at start, so the
run measures a mix. **Two of them also ran concurrently with the Worker's own suite, contending for
CPU and workbench ports.** Net yield of ~3.5 hours of CPU: nothing that the focused sets and
recomputation did not already show.
- **The Architect's job is recomputation, not a second suite.** Re-derive the round's claims from
  the artifacts, diff failure SETS when a suite exists, and verify the blast radius.
- **When a full suite IS wanted, it runs in the gap between rounds and John is told to hold the next
  launch until it lands.** Otherwise it is not a quiet window, it is a race.
- **The one full-suite result that ever caught something the focused sets missed was S133's item 5**
  - a check that had stopped checking. **That is the case that justifies the occasional run**, at a
  phase boundary, not every round.


**ONLY ONE FULL SUITE RUNS AT A TIME, AND IT BELONGS TO WHOEVER'S ROUND FLOOR DEMANDS IT
(Architect, 2026-08-19, after wasting ~40 minutes of CPU and nearly corrupting a Worker run).**
I had a suite going from 11:52 while Codex started its own at 12:23. **Two full suites on one
working tree contend for CPU and both write review state and bind workbench ports, so each can make
the other fail spuriously** - and mine was void regardless, because Codex was editing source files
underneath it. **I killed mine and left the Worker's running.**
- **The Worker's run is the authoritative one when a round is in flight.** It covers the new code;
  an Architect run started before the round does not.
- **The Architect's quiet-window run is for the interval between rounds** - after a round lands and
  before the next is launched. **John starts Codex, so that window is real and schedulable.**
- **Before starting a suite, check for a python process already running one.**

**A GUARD I SPECCED IN M20-S139 WENT STALE IN ONE ROUND, WHICH IS THE FASTEST YET.** I had the round
assert `len(missing) == 39`. S140 fixed the join and the number is now **5**, so my own guard is the
new red. **Codex was right to refuse to rewrite it and to escalate instead.**
**THE RULING: replace it with a non-increasing assertion** - the gap is reported, and it does not
GROW - plus the designed `xfail`, which is the part that carries information. **A measured number
belongs in the round report, never frozen into a guard.** This is the third time a snapshot
assertion has cost a round (S138's three, S139's one), and the previous two were inherited; **this
one I wrote myself, one round after writing the rule against it.**


**THE FULL SUITE CANNOT BE RUN IN A GIT WORKTREE, AND MY ATTEMPT TO PIN IT THERE PRODUCED A VOID
RESULT (Architect, measured 2026-08-19).** I moved the run into a worktree pinned to `cb93fea` so
Codex could not change files underneath it. **It came back `31 failed, 989 passed, 11 skipped,
34 errors` in 46:47 - and every one of those numbers is meaningless as a baseline.** The 34 errors
are collection failures in exactly the files that need untracked live state - all of `tests/e2e/*`,
`test_workbench_cells_api_m17`, `test_workbench_page_evidence_m15`, `test_review_preflight_m15`,
`test_verify_record_m9`, `test_self_serve_extension_m14`. **A naive set-diff makes it look like 28
tests "cleared" and 10 went "new"; nothing cleared - those tests never ran.** The 46-minute runtime
against the ~70-minute anchor is the tell.
- **Junctioning `.cache` and copying `graph/2025/_drafts` is NOT enough.** The suite also reads live
  `output/`, `review_queue/`, `workbench_output/` and `review_context/` CONTENT, none of it tracked
  and none of it enumerated anywhere.
- **So the full suite is only meaningful in the working tree, which means it is only meaningful
  while the Worker is IDLE.** John starts Codex, so the quiet window is real and schedulable: run
  it after a round lands and before the next is launched.
- **THIS IS THE SAME FINDING AS THE S115 WORKBENCH DEBT, ARRIVING AGAIN.** A test suite that cannot
  be reproduced from a clean checkout is not a gate, it is a local ritual. **Enumerating what
  untracked state the suite requires is worth a round of its own** - and it is the precondition for
  ever running this in CI.


**WORKER COMPLETION (2026-08-08; M20-S84 implementation, awaiting Architect acceptance).** The
pilot review page now has one full-width Tree and Math column. The retired positional renderer,
flow-only summary fields, SVG output, moderator-role constant, arrow glyph, and flow-only CSS/data
are removed from `pilot/review_panel.py`. Tree headers are left aligned, child indentation is
32px, and informative graph roles remain while position-implied roles stay suppressed. Holes
render their stored reason: the real cand_s71 workspace reports 83 `selector_no_formula_cue`, 7
structural, and 2 derivation rows. `--top N` ranks by operation count then operand count and keeps
the full 157-anchor totals in the summary. Default output is `C:\tmp\m20_s84\review_panel.html`.
The root `.gitignore` now ignores only `.test_tmp/` and ignores the empty root `tmp/` directory.

**S84 REAL-CORPUS EVIDENCE.** RAN:
`.venv\Scripts\python.exe pilot\review_panel.py 'C:\Users\devbox\AppData\Local\Temp\claude\C--Users-devbox-projects-tax-graph\6e1d97d0-c72d-4855-a055-e0c64f6224f8\scratchpad\cand_s71' --output C:\tmp\m20_s84\review_panel.html`
-> **157 anchors; 65 operation rows; operation counts 1: 51, 2: 12, 6: 2; 92 holes; hole reasons
83 selector_no_formula_cue / 7 structural / 2 derivation; max operands 23**. RAN the same command
with `--top 14` and `--top 25` -> **14 and 25 rendered operation rows respectively**, with the
full 157-anchor summary retained. The generated full page has **zero** `flow-svg`, `flow-edge`,
`MODERATOR_ROLES`, and `<svg` occurrences. Role counts are unchanged from the pre-S84 page, and
the longest Math line is **392 characters before and after**. Form 6251 line 18 renders as a Tree
with `threshold`, `key`, and `filing status` present.

**S84 TEST EVIDENCE.** RAN:
`$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp2'; $env:M20_S73_CANDIDATE='C:\Users\devbox\AppData\Local\Temp\claude\C--Users-devbox-projects-tax-graph\6e1d97d0-c72d-4855-a055-e0c64f6224f8\scratchpad\cand_s71'; .venv\Scripts\python.exe -m pytest pilot\test_review_panel.py -q`
-> **13 passed, 1 warning**. RAN:
`$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp2'; $env:M20_S73_CANDIDATE='C:\Users\devbox\AppData\Local\Temp\claude\C--Users-devbox-projects-tax-graph\6e1d97d0-c72d-4855-a055-e0c64f6224f8\scratchpad\cand_s71'; .venv\Scripts\python.exe -m pytest pilot -q`
-> **34 passed, 1 warning**. RAN `.venv\Scripts\python.exe tools\check_ascii.py`
-> **ASCII check OK**. The warning is the known permission failure writing the pre-existing
`.pytest_cache`; no provider run and no full suite were performed, per pilot rules.

**How to rebuild a candidate** - the two commands, in order, because the second is worthless
without a run from current code:

```
.venv\Scripts\python.exe experiments\derive_cells_s25.py --year 2025 --output-dir <RUN> --document form_1040_2025 --document form_2441_2025 --document form_6251_2025
.venv\Scripts\python.exe -m tax_graph.cli regenerate-candidate --run-dir <RUN> --output-dir <CAND> --expected-document form_1040_2025 --expected-document form_2441_2025 --expected-document form_6251_2025
```

**FULL-SUITE BASELINE (Architect, 2026-08-11, at `5e72db3`): 17 failed, 923 passed, 8 skipped,
1 xfailed in 58:22.** Supersedes the 21/841 baseline. **All 17 are environment or artifact reds and
NONE is ours** - the triage, the A/B recipe, and the named test ids are in BALL above. The former
"one red is ours", `test_m20_s31.py::test_all_prompt_templates_render_with_representative_values`,
is **green** (8 passed); the `operation_documentation` fixture no longer diverges from the prompt.
`test_review_scope_migration_m15.py` is **no longer UNCOMPARABLE** - it fails identically in both
arms on a `review_queue/2025/deferred_review.yaml` that exists in neither tree.

**PYTEST_DEBUG_TEMPROOT must be a SHORT path.** A run rooted under the Claude session scratchpad
produced **70 failures across 28 files**, every one of them `shutil.Error ... [WinError 3]` from
MAX_PATH overflow while copying `graph/2025/_drafts` into the fixture project. The same tests pass
on `C:\Users\devbox\AppData\Local\Temp\tgpt`. A long temp root does not fail a few tests, it fails
whole files at once - that shape is the signature, not a code regression.

**WORKER COMPLETION (2026-08-06; awaiting Architect acceptance).** M20-S70 is implemented under
`pilot/` as `cell_access.py`, the rewired `review_panel.py` and `constructions/measure.py`, their
tests, and README updates. `CellText.value is None` is typed absence; the label accessor reads
`label_after` only, so an absent caption cannot fall through to candidate or anchor text. The
accessor also owns form-face, instruction, expression, rendered wording, findings, status, and
graph operand reads. No provider was run and no candidate or graph artifact was written.

**REAL-CORPUS EVIDENCE.** RAN:
`.venv\Scripts\python.exe pilot\review_panel.py C:\tmp\m20_s68_candidate --output .test_tmp2\m20_s70_review_panel.html`
-> **157 anchors; 9 diagrams / 36 chains / 112 none; 92 holes; captions 8 present / 149 absent;
instruction sections 17 present / 140 absent; operations 65 present / 92 absent**. RAN:
`.venv\Scripts\python.exe pilot\constructions\measure.py C:\tmp\m20_s68_candidate --output .test_tmp2\m20_s70_constructions.yaml`
-> **construction inventory written**. The panel invariant covers all 157 anchors and no returned
caption begins and ends with the same printed line token.

**TEST EVIDENCE.** RAN:
`$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp2'; .venv\Scripts\python.exe -m pytest pilot\test_cell_access.py -q`
-> **2 passed, 1 warning**. RAN:
`$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp2'; .venv\Scripts\python.exe -m pytest pilot\test_review_panel.py -q`
-> **5 passed, 1 warning**. RAN:
`$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp2'; .venv\Scripts\python.exe -m pytest pilot\constructions\test_measure.py -q`
-> **4 passed, 1 warning**. RAN:
`.venv\Scripts\python.exe tools\check_ascii.py` -> **ASCII check OK**. The warning is the known
permission failure writing the pre-existing `.pytest_cache`; the short override avoided the poisoned
`.test_tmp`. No provider run and no full suite were performed, per pilot rules.

**WORKER COMPLETION (2026-08-06; M20-S72 implementation, awaiting Architect acceptance).** The
pilot now stops graph expansion at nested plain form-line references, renders them as `line X`,
and hashes repeated operation subtrees so later occurrences say `same expression as above`.
Column 3 emits no graph node ids; the `zero_floor` modelling oddity remains reported in the
summary and the graph is unchanged. `build_panel` records per-panel arrow counts and their
distribution. The summary and CLI now call the accessor-resolved count **instruction rows**;
the S71 candidate has 17 such rows (4/8/5 by document) and 16 unique locators. The alleged 84
rows is not present in this candidate's 67 `rows_detail` records, so no second section count is
carried into the panel. Changes are limited to `pilot/` and pilot tests/docs.

**S72 REAL-CORPUS EVIDENCE.** RAN against the S71 candidate at the path above. Before the fix,
45 diagram/chain panels had distribution `{4: 3, 5: 1, 6: 4, 7: 1, 8: 1, 9: 1, 10: 2, 11: 2,
12: 1, 13: 1, 14: 1, 16: 3, 17: 1, 18: 2, 19: 1, 20: 1, 23: 2, 24: 1, 26: 2, 27: 1,
28: 2, 33: 1, 35: 1, 47: 1, 48: 1, 53: 1, 55: 1, 107: 1, 109: 1, 111: 1, 233: 1, 251: 1}`
with max 251 and modes 9 diagrams / 36 chains / 112 none. After the fix, distribution is
`{4: 9, 5: 2, 6: 1, 16: 2, 17: 1}`, max 17, with modes 4 diagrams / 11 chains / 142 none.
The residual max 17 is still above the rough dozen target and is reported plainly; further
notation/CSE work remains queued. The 157 generated flow sections contain no node-id leakage.

**S72 TEST EVIDENCE.** RAN:
`$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp2'; .venv\Scripts\python.exe -m pytest pilot\test_review_panel.py -q`
-> **7 passed, 1 warning**. RAN:
`$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp2'; .venv\Scripts\python.exe -m pytest pilot\test_cell_access.py -q`
-> **2 passed, 1 warning**. RAN:
`$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp2'; .venv\Scripts\python.exe -m pytest pilot\constructions\test_measure.py -q`
-> **4 passed, 1 warning**. RAN:
`.venv\Scripts\python.exe tools\check_ascii.py` -> **ASCII check OK**. The warnings are the
known permission failure writing the pre-existing `.pytest_cache`; no provider run or full suite
was performed, per pilot rules.

## From Architect

**ACTIVE DIRECTION: M20-S133 UNDER CURRENT ROUND.** Heading extraction is finished; the citation
range is the next thing that is wrong in the artifact the agent actually reads.

**A PRECEDENT THAT BINDS M20-S133 DIRECTLY, AND IT IS WHY THE SPEC FORBIDS TOUCHING `quoted_text`.**
The S106 rework was REJECTED for truncating real quotes to fit wrong ranges. S107 was allowed to
change `quoted_text` only in the opposite direction - replacing hand-authored paraphrase with what
the document actually says, with the source pinned and the changed set asserted to be exactly the
named 30. **When a quote and a range disagree, the range is the thing under suspicion; editing the
quote to make a check pass is how the defect gets buried.**

**A NOTE TO MYSELF THAT KEEPS EARNING ITS PLACE.** Repeated specs have set a floor the data could
not meet - `7ba64be`, S106, S112, S130 - and twice this week I specced a floor item that was ALREADY
SATISFIED. **Before writing the next floor, check that the corpus can satisfy it and that the
machinery does not already exist.** S131 is the worst case: I hand-rolled a formula, compared THAT
against OTS, never ran the engine, and specced a round to rebuild a tax table the repo already had.

## History

Everything before M20-S23, and all per-round Worker narration, lives in git history. This file was
pruned from 7,520 lines on 2026-08-02 at S28 acceptance; `git show 12240ef:plans/AGENT_HANDOFF.md`
is the last unpruned copy. Earlier prune: 2026-07-23, from 1,198 lines, for public-repo prep.
Durable rulings were carried forward into **Binding rulings** above rather than deleted; A9
rulings remain pinned in `plans/PHASE_M15.md`; the defect ledger (D6, D9, D10, D12, D13, D14) is
in `AGENTS.md`.
