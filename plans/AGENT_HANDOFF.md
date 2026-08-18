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

**BALL: CODEX. M20-S132 IS ACCEPTED. M20-S133 UNDER CURRENT ROUND IS THE NEXT ROUND: THE CITATION
RANGE IS UNVERIFIED AND THE ONLY CODE THAT READS A CITATION IGNORES IT.**

**M20-S132 IS ACCEPTED (`85a8daa`, Architect, 2026-08-18), VERIFIED BY RECOMPUTATION.** I re-ran
every booklet and diffed S130 ownership against S132 section by section: **exactly 6 sections
changed, all six the Schedule D worked examples, all `rejected -> default_form`, and nothing else in
the corpus moved at all.** Rejections **29 -> 23**, Schedule D **6 -> 0**, Form 1116 **21 -> 21**,
Schedule A 2 -> 2. Per-document `line_anchored` unchanged on all 12, still summing to **288**.
**20 passed** across S128/S129/S130/S132; `check_ascii` OK; `git diff --check` clean.
- **The three-way rule is right and the fix is minimal.** Case 2 did not regress, which was the
  risk I named in the spec.
- **The mechanism Codex added that I did not spec is the load-bearing one and it is correct:** a
  document mention inside a LINE heading is not an ownership boundary. *"Lines 1a and 8a-
  Transactions Not Reported on Form 8949"* mentions Form 8949 while remaining Schedule D's own line
  instruction. Without that, case 3 could never fire under a line heading.
- **`foreign_owner_rejected` is the only rejection reason in the frame**, so reassigning every
  section's rejection cannot silently drop a different rejection class. I checked before accepting.

**HEADING EXTRACTION IS FINISHED. 288 OF 449, AND THE REMAINING GAP IS NOT REACHABLE BY FINDING MORE
HEADINGS.** Per document: `form_1040` 41, `form_1116` 17, `form_2441` 20, `form_6251` 37,
`form_8949` 4, `schedule_1` 52, `schedule_1a` 11, `schedule_2` 38, `schedule_3` 29, `schedule_a` 22,
`schedule_b` 5, `schedule_d` 12. **Against PDF-deterministic 255, with no model call.** S130 added
208 sections for +1 anchor - charts, worksheets and back matter, which is document coverage for the
stage-2 read and was never going to be line anchors. **Do not spec another heading round.**

**THE ARTIFACT WE SEGMENT IS THE DAMAGED COPY, AND THIS IS THE DURABLE ACQUISITION FINDING.** We pay
Mistral OCR to turn a PDF into markdown while the IRS publishes the same content as structured HTML
we already download (`.cache/raw/2025/*.html`, since 2026-08-14). **Every structural defect of six
rounds is an artifact of the OCR path**: injected `# Page N` markers at heading level 1, lost em
dashes (`Example 1Basis Reported to the IRS`), and run-in labels arriving as undifferentiated bold -
Schedule B's HTML tags exactly 7 `inlinehd` labels where the OCR emits 23 undifferentiated bold runs.
**John's OCR eval was right and is simply OBE: it measured WORDS (99.0% of Schedule B's OCR words
appear in the HTML) and segmentation depends on the distinction between KINDS of markup, which words
cannot carry.**
**DO NOT DELETE THE OCR PATH YET.** The lookup tables live in the PDF only - `2025 Tax Table`
appears 0 times in the HTML against 13 in the OCR text, and the EIC tables are referenced but not
reproduced. Check whether the IRS publishes those as their own pages first.

**KEEP THE MODEL, AND THE REMAINING GAP IS SCHEDULE 1-A.** On the four line-organised chapters the
model is at CEILING - every cell whose chapter contains a `Line N` heading is found, and all 38
unreached cells there are rollups and arithmetic the IRS writes nothing for. **Schedule 1-A is the
entire remaining gap: 37 of 48.** Its chapter segments into 51 byte-perfect sections of which only
11 carry a line token; the rest is topic prose (`Qualified Tips`, `Net income limitation.`), and
lines 3 and 38 are stated in BODY PROSE that no anchor scheme reaches.
**THE UNION OF BOTH MATCHERS IS OFF THE TABLE (John pushed back, and opening all four disagreements
proved him right): it buys 2 real cells and imports 3 wrong attributions**, all three the S116
cross-form collision still live in the baseline (`form_1040` 26, 31, 38 are Form 2441/8839/Schedule
1-A references the model resolves correctly to `1e`, `1f`, `13b`).

**`governs` IS ASKING TWO QUESTIONS AND ONLY ONE IS ANSWERABLE.** For `Line 4a.` it is a mechanical
copy out of the heading and the model never gets it wrong; for `Qualified Tips` it is a SEMANTIC
mapping to form lines, which needs the line inventory we deliberately withhold to keep the model
cell-naive. Given no way to say *"this governs lines I may not name"*, the model filled the field
with **93 distinct non-line values in three spellings**. **That is an under-specified field telling
us so, not misbehaviour.** The fix is two stages and it keeps John's ruling intact - segmentation
stays mechanical with `governs` constrained to a line token or EMPTY in the structured-output
schema, and attribution becomes its own stage over already-bounded spans. Both are queued.

**A CORRECTION I OWE, AND IT SHRINKS A ROUND I WAS ABOUT TO SPEC WRONG.** I wrote here that citation
`ranges` are in TWO coordinate systems and that roughly half the shipped citations point at the wrong
text. **Measured properly today: they are in ONE. 474 of 511 resolve as the schema already declares
them** - half-open CHARACTER offsets into the acquired `.txt` read with universal newlines - and
**none resolve as any system the schema does not declare.** My earlier split counted the same
citations twice under two readings of the same numbers. **The data is consistent; the CONSUMERS are
the hazard**, and that is what M20-S133 addresses.

**CORRECTION I OWE JOHN, STILL STANDING: I TOLD HIM TWICE THAT SCHEDULE B GOES 0 -> 8 OF 8 AND THAT
THIS WAS "THE WHOLE CASE FOR THIS DIRECTION." THE HONEST NUMBER IS 0 -> 5 LINE-LEVEL
INSTRUCTIONS**, plus three attributed to a Part heading. The direction holds; the headline was
overstated.

**M20-S115 IS DELIVERED AND WAS NEVER ACCEPTED (`4f7abf9`, Codex, 2026-08-16). ARCHITECT MISS.** The
review contract - `workbench/server.py`, `generated_review.py`, `review_defects.py`,
`test_m20_s115.py` and the workbench front end - is on `main` and on the remote, unverified. It
touches the surface John reviews, so it needs a LIVE check, not a test read. **That is the
Architect's leg and it is owed before the review contract is trusted**, because John does not review
while the contract keeps moving.

**THREE JOHN RULINGS, 2026-08-16, STILL QUEUED AS WORK:** `filer_entry` needs a reason taxonomy
(`derivation_failed` the defect vs `source_form_not_modelled` the scope fact); **`form_1040` 6b's
decline is a PACKET DEFECT** - it declined for want of the Social Security Benefits Worksheet, which
the graph contains, and *"we model the worksheets so that they can support the forms"*; and
**ROUTING IS ITS OWN CONSTRUCT** - `schedule_d` 17 is flow control, so `election` must be validated
until routing exists, or it keeps absorbing branches.

**THE 18-RED BASELINE, unchanged and still current.** Eleven `tests/e2e/*_m15.py`, plus:
`test_address_campaign_m15r::test_form_8949_cross_form_claims_resolve_exactly`,
`test_field_identity_m16::test_schedule_2_raw_cache_reproduces_target_fields`,
`test_m20_s71::test_real_candidate_node_labels_use_clean_text`,
`test_review_preflight_m15::test_real_2025_preflight_passes_with_all_coverage_dimensions`,
`test_review_scope_migration_m15::test_live_queue_migration_gives_every_pending_entry_a_primary_target`,
`test_schedule_2_m16::test_schedule_2_part_i_raw_acroform_identity`,
`test_schedule_d_extraction_m9::test_schedule_d_fixture_drafts_include_schema_valid_band_tables`.

## Current round

**M20-S133: THE CITATION RANGE IS UNVERIFIED, THE ONLY CODE THAT CHECKS A CITATION IGNORES IT, AND
FOUR SEPARATE SITES SLICE IT WITH THEIR OWN IDEA OF WHAT THE TEXT IS.**

**MEASURED BY THE ARCHITECT, 2026-08-18, over `graph/2025/citations/*.yaml` - 511 citations carrying
both a `quoted_text` and a `ranges`.**

- **The stored ranges are ONE coordinate system and it is the one the schema already declares.**
  **474 of 511** resolve as half-open CHARACTER offsets into the acquired `.txt` read with universal
  newlines. **Zero** resolve under any other reading. My earlier note in this file claiming two
  coordinate systems was wrong and is corrected in BALL.
- **THE HAZARD IS THE CONSUMERS, AND IT IS THE S124 TRAP SITTING LIVE IN THE CODE.** Four booklets
  carry CRLF - `instructions_form_1040_2025` is **683,265 bytes against 675,580 characters, 7,685
  CRs of drift** - so any consumer that byte-slices a stored range lands kilobytes off its heading.
  The remaining fourteen sources have zero CRs, where byte and character coincide, **which is
  exactly why nothing has caught this.**
- **`tax_graph/acquire/citation_check.py` NEVER READS `ranges`.** It searches the WHOLE FILE for
  `quoted_text` across `.txt`, then `.html`, then `.pdf`. **A citation whose range points at a
  neighbouring worksheet row passes this check today.** That is the "line 22's text under line 24"
  failure, unguarded, in the artifact the agent reads.
- **FOUR SITES IMPROVISE THE SLICE INDEPENDENTLY:** `extract/inputs.py:333`
  (`source_text[start:end]`, source read as **ascii**), `ingest/worksheet_harvest.py`
  `_source_quote_for_ranges` (**ascii**), `ingest/core_source_ranges.py:89` (**utf-8**), plus the
  writers in `extract/assembly.py:635`, `extract/outline.py:683`,
  `extract/outline_pipeline.py:1221`. **They agree today by luck** - all happen to use `read_text`.
- **The 37 that do not resolve are ONE class, and in every one I opened THE RANGE IS RIGHT.** The
  stored quote is a de-noised reading of a span that carries table pipes and empty cells:
  `cite_schedule_d_carryover_line_3_4`'s span reads
  *"3. Combine lines 1 and 2. If zero or less, enter -0- | 3. _____ | | 4. Enter the smaller..."*
  and the quote drops the `| 3. _____ | |`. `cite_schedule_d_line20_gate`'s span **starts exactly at
  the quote's first character** and is merely too wide - it covers both the `Yes.` and `No.`
  branches and the quote keeps only `No.`

### ITEM 1 - ONE ACCESSOR, AND IT IS THE ONLY THING THAT MAY TURN A RANGE INTO TEXT

`resolve_source_range(source_document_id, start, end) -> str` in ONE module. It decides the
coordinate system ONCE and states it in the docstring. **Absence is typed, never `""`**: a missing
source file and an out-of-bounds range are distinct, named failures that a caller cannot mistake for
empty text. **No substrate fallback** - it reads the acquired `.txt` and does not silently try
`.html` or `.pdf`. The invariant test lives AT the accessor: the coordinate contract on a CRLF file
and on a CR-free one, and both absence cases.

### ITEM 2 - REWIRE THE CONSUMERS, DO NOT ADD A SECOND PATH

`check_citation_integrity` verifies the quote against **the span**, not the file. **The whole-file
search is DELETED, not kept as a fallback** - keeping it would let a wrong range keep passing, which
is the entire defect. The three improvising slice sites in ITEM 1's list call the accessor.
**`grep` evidence in the round report that no `[start:end]` slice of a source text survives outside
it.**

### ITEM 3 - THE 37 GET A STATED RULE, DECIDED FROM THE ARTIFACT

**Open at least 5 more of the 37 end to end and report the real class of each BEFORE choosing a
rule** - AGENTS.md hard rule, and a list of counts does not satisfy it. If they are all
quote-elision as the four I opened were, the rule is that **the quote's tokens appear IN ORDER
within the span**, stated in the schema description. **If any turn out to be a genuine range error,
name them by `citation_id` with the correct span and do NOT let the elision rule paper over them.**

**WHATEVER RULE YOU CHOOSE MUST STILL REJECT A RANGE THAT POINTS AT THE WRONG ROW.** Prove it:
perturb a known-good range by a few hundred characters and the check must FAIL. **A rule that
cannot fail is not a check.**

### ITEM 4 - SAY IT IN THE SCHEMA

`schemas/citation.schema.json` says *"half-open character ranges"*. Add **which text** (the acquired
`.txt` for `source_document_id`) and **which newline handling** (universal newlines), so the next
consumer does not have to guess.

---

**WHAT MUST NOT HAPPEN.**
- **No re-authoring of `graph/2025/citations/`.** Protected set, and the ranges are not the defect.
- **Do not "fix" the 37 by editing `quoted_text`.**
- **No model call and no network.**
- **No second resolver.** One accessor is the point of the round.

**THE FLOOR.**
- **One accessor, and every range-to-text path goes through it**, with grep evidence.
- **511 of 511 verified THROUGH THE SPAN** - 474 by containment plus the 37 by the stated rule, or a
  named list of genuine range errors.
- **A perturbed range FAILS the check.**
- **The whole-file quote search is gone from `citation_check.py`.**
- **Full suite against the 18-red baseline** - this touches `tax_graph/`.
- **Protected set byte-identical**, `tools/check_ascii.py` OK, `git diff --check` clean.

**ARCHITECT'S LEG, OWED IN PARALLEL.**
1. **Open Schedule 1-A's 37 unreached cells.** It is the whole remaining coverage gap and I have
   never opened them. It may be the instruction ceiling that made Schedule D's 12 of 24 a full
   score, or a real gap - and I must not spec it as a defect before opening several.
2. **The live check on the S115 review contract**, still unverified on the remote.

## Open for Architect

Nothing open. Raise items here.

## Queued (ONE LINE each - do not spec ahead)

**JOHN'S PRIORITY, 2026-08-10: get the CORE documents processing reliably.** Ordered for that.
**Every item below is a PIPELINE change - none of them is a per-cell human correction.**

**THE ACQUISITION FINDING AND THE SCOREBOARD IT PRODUCED LIVE IN BALL.** What remains queued off it:

- **CONSTRAIN `governs` TO A LINE TOKEN OR EMPTY IN THE STRUCTURED-OUTPUT SCHEMA (Architect,
  measured 2026-08-18).** 93 distinct non-line values are in the live 1040 frame; the join key
  accepts free text today. **Prompt/schema change - no blast radius, runs wide, needs a live call.**
- **ATTRIBUTION AS ITS OWN STAGE OVER BOUNDED SPANS (Architect, 2026-08-18).** *"Which lines does
  THIS span govern, or none?"* over boundaries already fixed. **Permitted by the 2026-08-17 binding
  ruling now pinned in AGENTS.md, but it is the inverse of a question John vetoed, so it gets his
  yes before it is specced.** It is the only thing that reaches Schedule 1-A's remaining 37 cells.
- **SCHEDULE 1-A IS 11 OF 48 AND NOBODY HAS OPENED THE OTHER 37 (Architect, 2026-08-17).** May be
  the instruction ceiling that made Schedule D's 12 of 24 a full score, or a real gap. **Architect's
  leg, and it gates the item above.**
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
