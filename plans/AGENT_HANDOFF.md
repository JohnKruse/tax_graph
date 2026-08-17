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

**BALL: ARCHITECT. M20-S118 is accepted; the next round is not specced yet.**

**M20-S118 IS ACCEPTED (`3181169` + `a4cd008`, Architect, 2026-08-17), VERIFIED BY RUNNING.**
Recomputed independently rather than read off the report: the three named cells behave exactly as
specced (`form_1040` 4a keeps `...0019` and drops `...0018`; `schedule_1` 8a keeps both, specific
first; `schedule_1` 1 keeps the worksheet and records the stub), **nested text duplicates in any
packet went 17 -> 0 across all 449 cells**, `AMBIGUOUS` went **60 -> 4** with `MATCHED` 202 -> 258
(the 56 reconcile exactly), the **S117 invariant still reports 0 disagreements** and
`test_m20_s117.py` is unmodified. **107 passed** across seven suites.

**THE HARNESS'S 25/0/0 HERE MEANS "NOT COVERED", NOT "NOTHING MOVED".** 19 cell packets changed and
**none of the 19 is among the harness's 25 cases** - disjoint sets, checked. **Do not read a green
harness as evidence about a packet change again; check the overlap first.**

**CORPUS, ALL 17 DOCUMENTS, 2026-08-17 (Architect's leg): rules 74, edges 181, gaps 154**, 41
minutes, exit 0, 1446 auto-accepted / 31 human-review. **Against the S113 record of 78 / 224 / 153 -
BUT THAT COMPARISON IS NOT SOUND AND MUST NOT BE QUOTED AS A DELTA**: these counts came from reading
the draft YAMLs, the S113 numbers came from another session's method, and four rounds sit between
them. **The sound check is the blast radius, and it is clean: 17 of the 19 changed cells derive with
no review gap**, including `form_1040` 6b, which used to decline.

**THE TWO THAT DID NOT, OPENED END TO END.** `form_1040` 5a fails with *"source line is not present
in the deterministic outline index"* - an outline defect, unrelated to packets. `schedule_1` 1 fails
with *"quote does not match the supplied form or instruction evidence"*, **and it is the finding of
this round.**

**M20-S117 IS ACCEPTED (`954c235`, Architect, 2026-08-17), VERIFIED BY RUNNING.** The Architect
re-ran the invariant independently against the checked-in artifact: **449 cells, 0 disagreements**
with `instruction_span_ids_for_line`, down from 46. `cell_buckets` and `instruction_buckets` each
sum to their own population in **all 12 documents**. `schedule_2_2025` `1b` and `1d` are `MATCHED`,
`direct`, both to section `...0122`, with no `other_form_document_ids`. **100 passed** across
`test_m20_s116`, `test_m20_s117`, `test_instruction_sections_m20`, `test_derive_cells_m20`,
`test_outline_span_resolution_m20`; replay harness **25/0/0**; ascii OK; `git diff --check` clean.
**The second matcher is gone, not repaired, which is what was asked.**

**THE CORRECTED NUMBERS, AND THEY RECONCILE EXACTLY.** Cells now read **MATCHED 202, parser gaps 91,
other-form 76, AMBIGUOUS 60, genuine absences 20**. The 46 misbucketed cells moved to `MATCHED` (4)
and `AMBIGUOUS` (42), which is the whole of the difference and is how we know nothing else shifted.

**M20-S115 IS DELIVERED AND WAS NEVER ACCEPTED (`4f7abf9`, Codex, 2026-08-16). ARCHITECT MISS,
CAUGHT WHILE REVIEWING THE PUSH RANGE 2026-08-17.** The review contract - `workbench/server.py`,
`generated_review.py`, the new `review_defects.py`, `test_m20_s115.py` and the workbench front end -
went in and the Architect specced S116 the next morning without verifying it. **It is on `main` and
now on the remote, unverified.** It touches the surface John reviews, so it needs a live check, not
a test read: **that is the Architect's leg and it is owed before the review contract is trusted** - and John does
not review while the contract keeps moving, so an unverified contract change is worse than none.

**M20-S116 IS ACCEPTED (`6beb1f4` + `29cbbcd`, Architect, 2026-08-17).** It built the two-sided
reconciliation report and its bucket taxonomy, covering all three families. **Its own matcher was
the defect S117 removed**; the lesson is pinned in `../AGENTS.md` and the narration is in
`git show c7bbc9b`.

**THE STANDING LESSON FROM S116-S117, and it is the third time this phase.** The report was accepted
on Codex's evidence and only disagreed with the pipeline **because the Architect re-derived its
central claim independently instead of reading its totals.** **Verify an artifact by recomputing
what it asserts, not by checking that it exists and is green.**

**M20-S114 IS ACCEPTED (`9f856a9`, Architect, 2026-08-16), VERIFIED BY RUNNING.** `/api/documents`
-> **HTTP 200, 9532 bytes, all 16 documents**. `schedule_a` reports **2 unplaceable rows, visible
with reasons** instead of raising; its SALT election is anchored to the real line 5a checkbox
(`generated_status: decision` on `f1_7[0]`) and the header duplicate is gone. Codex proved the new
test fails pre-fix with the exact `ValueError`. Replay harness still 25/0.
**NOTE: the 500 John kept hitting after the fix was the ARCHITECT's error** - `TaskStop` killed the
task wrapper but left the old python process holding port 8765, so three checks tested the PRE-FIX
server. Codex's 200 was correct throughout.

**M20-S113 IS ACCEPTED (`6b855b4`, Architect, 2026-08-16).** John ruled the reclassification
correct. Replay harness 25/0; 93 passed bare; corpus **rules 78, edges 224, gaps 153**. The model
classified **500 addressable lines** against the cue matcher's 141 and returned **filer_entry 134,
not_derivable 117, information_return 13, election 5**. `form_1040` 35a and 36 mint zero rules - the
wrong `COPY` is gone - and five elections were pipeline-produced.

**THE RULE COUNT IS NOT A QUALITY METRIC. NEVER USE IT AS A FLOOR AGAIN.** `rules >= 107` was
unsatisfiable by construction: the round's purpose was to stop treating non-computations as
computations. **That was the sixth floor written that the work could not satisfy.** Rulings are
pinned in `../docs/derivation-architecture.md`.

**THREE JOHN RULINGS, 2026-08-16, NOW QUEUED AS WORK:**
1. **`filer_entry` needs a reason taxonomy** - `derivation_failed` (a defect) vs
   `source_form_not_modelled` (a scope fact). `form_1040` 1f is the second: Form 8839 is not
   acquired. **Fold into S115 if cheap; otherwise its own round.**
2. **`form_1040` 6b's decline is a PACKET DEFECT.** It declined for want of the Social Security
   Benefits Worksheet, **which the graph contains**. *"We model the worksheets so that they can
   support the forms."* When a line's evidence names a worksheet the graph has, that worksheet
   belongs in the packet.
3. **ROUTING IS ITS OWN CONSTRUCT.** `schedule_d` 17 is flow control, not an election. Until routing
   exists, **`election` must be validated so it stops absorbing branches** - the same failure mode
   as `COPY` absorbing line 36.

**ARCHITECT NOTE.** John: *"do what you think best. I don't understand why this is such a big deal
for you."* **Acceptance is the Architect's call and was being escalated unnecessarily.** Bring John
decisions only where the answer changes what gets built.

**DIRECTION IS PINNED IN `../docs/derivation-architecture.md`. READ IT FIRST.** Sequencing: harness
(DONE, `80980e7`) -> model owns the path (DONE, `6b855b4`) -> **review surface (THIS ROUND)** ->
voting.

**M20-S112 IS ACCEPTED (`80980e7`, Architect, 2026-08-16), VERIFIED BY RUNNING.**
`pilot/replay_harness.py` -> **21 cases, 0 mismatches, 5 seconds, network_calls=0**, over the
production validator, resolver and assembler. Corpus untouched at **rules 108, edges 369, gaps 33**.
Codex proved the negative against `9b9333f`; the Architect additionally ran it against `c47f5fa`
(S109) -> **20 of 21 mismatches, exit 1**.

**KNOW THE HARNESS'S LIMIT.** It replays OLD responses and **cannot predict what a CHANGED PROMPT
will make the live model emit** - on the S109 tree it reports `production prompt differs from
recorded prompt` on 19 of 20 cases. **That tripwire is the point: the fixtures are stale, go run the
corpus. A GREEN HARNESS IS NEVER PERMISSION TO SKIP THE CORPUS RE-DERIVE**, and S113 changes the
prompt, which is exactly the case it cannot predict.

**ARCHITECT SPEC DEFECTS TO STOP REPEATING.** S112's floor said "NO model call" and also "run
`extract --year 2025`". Codex correctly took the conservative reading and said so - the fifth floor
written that the work could not satisfy as specified. **Corpus verification and bare test runs are
the Architect's leg and never belong in a Worker floor.**

**M20-S108 IS ACCEPTED** (`c2dc0d8` + `e2d0180` + `4377c30` + `7bfb9e8` + `7580a4d` + `b96fc59`,
Architect, 2026-08-15). `extract --year` completes all 17 documents; `accepted` moved 0 -> ~1670;
46 parameter nodes are minted and every plain printed constant now derives.

**STABILITY IS MEASURED NOW - USE RANGES, NOT SINGLE NUMBERS.** Triple corpus run, 2026-08-15:
**gaps 32 / 33 / 34, rules 109 / 108 / 107, edges 370 / 365 / 366.** Of a 36-gap union, **31 are
STABLE (3 of 3), 1 flaky, 4 appear once.** So **86% of failures are real defects, not noise** - and
**the corpus output itself varies +/-2 rules run to run**, concentrated in `form_1116`, `form_2441`
and `schedule_1a`. **A single-run delta smaller than that is not evidence.**

**`prompt-bench` AND THE CORPUS PATH DISAGREE.** `schedule_2` 1z is *accepted* by prompt-bench and
fails in the corpus, because prompt-bench stops at micro-extraction and the corpus then resolves
operands against the outline. **Use prompt-bench to see the prompt and the response; do NOT use its
verdict as the corpus verdict.**

**PRIORITY RESET, 2026-08-15.** John: *"I want to just concentrate on the derivation. It is the
true linchpin of this whole project."* **The S102-S107 provenance line is PARKED.** It was real
work and it found real fabrications, but fifteen rounds of it ran while derivation produced nothing
since 2026-08-01, and the Architect never put that in front of John. **Do not open another
citation/source-range round without an explicit instruction.**

**M20-S107 IS DELIVERED, NOT ACCEPTED** (`5c3f91b` + `f63ec79` + `ffc9cdd`, Codex, 2026-08-14). Its
full-suite evidence is unusable - `16 failed, 612 passed, 369 errors`, where the 369 are
`.test_tmp\pytest-of-devbox` ACL setup failures and 612 passed against a clean run's 973, so most of
the suite never executed. **Re-verification is deferred behind derivation and is NOT a blocker.**

**THE 1040 IS DERIVING AGAIN** (Architect, 2026-08-15, `4990f20`). One packet-assembly bug had
zeroed the whole phase; corpus is now **103 rules / 337 edges / 38 gaps**, and the failure class
that accounted for all of form_1040's rejections is at **zero corpus-wide**.

**M20-S106 IS ACCEPTED (`d8accca`, Architect, 2026-08-14). Verified by diffing the graph and
running the suite, not by reading the report.**
- **THE CORRECTION IS REAL AND I CHECKED THE PINNED SIDE.** Every citation `quoted_text` in the
  tree was diffed against `82962eb`: **607 citations, 607 in common, ZERO text changes.** The
  122-citation corruption that got the previous pass rejected is fully reverted. **461 core
  citations now carry acquired-source ranges.**
- **THE THREE CONSUMER GUARDS ARE GREEN** - `test_mcp_m2`, `test_return_record_m5`,
  `test_workbench_cells_m17`, 3 passed in 8.6s. Those are the real acceptance signal, and the
  reason they could finally run is environmental: a reboot released the ACL lock on
  `.test_tmp\pytest-of-devbox`, which had been erroring the MCP test out at collection.
- **FULL SUITE: 20 failed, 973 passed, 8 skipped, 1 xfailed in 1:06:58.** The **18-red baseline is
  intact** - 11 e2e plus the same 7 non-e2e ids, **zero baseline reds fixed, zero newly broken.**
  Outcomes moved 993 -> 1002 and **all 9 new outcomes are S106 tests**, which is what rules out
  hidden movement.
- **THE 2 REDS BEYOND THE BASELINE ARE ONE GUARD COUNTED TWICE.**
  `test_core_source_ranges_m106::test_core_citations_reconstruct_from_acquired_ranges` and
  `test_worksheet_ranges_s105::test_promoted_core_citations_reconstruct_from_source_ranges` fail on
  the **identical assertion at the identical citation** (`cite_schedule_d_carryover_line_1_2`,
  `assert []`). S106 wrote a second copy of its own core guard into the S105 file at `1822514`.
  **S107 deletes the duplicate; the guard lives in one place.**

**WHY IT IS ACCEPTED WITH ITS OWN GUARD RED, AND THIS IS MY ERROR TO OWN.** The floor I wrote said
**every** core citation binds to a range. **34 of them never can, because they are not quotes.** I
ran all 34 against the acquired text with a sliding best-match: **31 have their content in the
source** at similarity 0.47-0.98 - `cite_sdtw_line_19_breakpoint` is off by a character or two -
and **21 of those sit on a markdown table row**, the exact `row` region kind S105 already built.
The pinned text is a lightly edited copy of real acquired bytes. **They are hand-authored
paraphrases from the A9 scaffolding era, and S106 is the first thing that could see them.**
**This is the SECOND time this phase I specced a floor the data cannot satisfy** (the first was
`7ba64be`, the drop-to-zero target). The Worker did not overreach either time.

**THE FOUR TAX-BRACKET CITATIONS ARE A DIFFERENT ANIMAL AND DO NOT GET AN EXEMPTION.**
`cite_1040_tax_brackets_single`, `_joint_qss`, `_mfs`, `_hoh` score 0.42-0.47 because they are
genuine SYNTHESES over a rate table. `cite_1040_tax_brackets_single` quotes `$57,231.00`, a
cumulative base **that appears nowhere in the source**; the table cell holds `$30,452.75`. No range
will ever bind them. **Burying them in a legacy exemption would hide a real modeling gap**, so they
get a typed provenance kind of their own - see S107 item 3.

**M20-S105 IS ACCEPTED (`98d81dc` + correction `82962eb`, Architect, 2026-08-14). Verified by
running the suite and the corpus, not by reading the report.**
- **FULL SUITE, bare command, quiet tree: 18 failed, 966 passed, 8 skipped, 1 xfailed in 1:06:24.**
  **The 18 are EXACTLY the enumerated baseline** - 11 e2e plus the same 7 non-e2e ids, with **zero
  new reds and zero baseline reds fixed.** Outcomes moved 987 -> 993 and **all 6 new outcomes are
  the 6 new S105 tests, all passing.**
- **THE STORED BOUNDARY IS A RANGE NOW. 225 of 228 worksheet citations carry source ranges**, split
  **211 `row`, 12 `routing_sentence`, 2 `note`.** Simplified Method line 2's citation is no longer
  fused and the note is its own citation at `118266-118490` governing lines 3 and 4.
- **THE INVARIANT IS ENFORCED, NOT COUNTED.** `tests/test_worksheet_ranges_s105.py` validates every
  region citation against the schema and asserts **its ranges reconstruct `quoted_text` exactly.**
- **THE COMPENSATION IS GONE.** No persisted `form_face_text` on any node or in the node schema; the
  row face is derived from the citation ranges; the governed note is separate provenance assembled
  only onto the line its citation says it governs. **Driven by stored structure, not by matching the
  printed word `Note`.**
- **NO FACE MOVED.** All four checked worksheet faces are byte-identical to their pre-S105 values and
  **the prior-year gate still refuses Simplified Method line 2 and admits lines 4 and 6.**

**THE ROUND TOOK THREE PASSES AND THE MIDDLE ONE IS WORTH REMEMBERING.** The first pass met the
"faces unchanged" floor by **re-introducing the fused text on a new node field that the loader
preferred over the clean citation**, and by relocating the note logic rather than deleting it.
**The floor had said in those words: do not re-add the router to make the faces match.** The
Architect caught it by reading what the loader actually consumed rather than what the report
claimed, and the correction made the round SMALLER. **A green floor check is not evidence that the
mechanism under it is right.**

**THE 18-RED BASELINE, unchanged and still current.** Eleven `tests/e2e/*_m15.py`, plus:
`test_address_campaign_m15r::test_form_8949_cross_form_claims_resolve_exactly`,
`test_field_identity_m16::test_schedule_2_raw_cache_reproduces_target_fields`,
`test_m20_s71::test_real_candidate_node_labels_use_clean_text`,
`test_review_preflight_m15::test_real_2025_preflight_passes_with_all_coverage_dimensions`,
`test_review_scope_migration_m15::test_live_queue_migration_gives_every_pending_entry_a_primary_target`,
`test_schedule_2_m16::test_schedule_2_part_i_raw_acroform_identity`,
`test_schedule_d_extraction_m9::test_schedule_d_fixture_drafts_include_schema_valid_band_tables`.

## Current round

**NONE IN FLIGHT. The next round is not specced; the finding below is what it should be built on,
and it wants John's read on sequencing first.**

**THE FINDING: `STUB SECTION` IS LAUNDERING A PARSER TRUNCATION, AND IT IS PROBABLY THE ROOT OF THE
91 PARSER GAPS (Architect, 2026-08-17, opened end to end).**

`schedule_1` line 1 is the worked case. Its instruction section `...0060` is **13 bytes**:
`'#### Line 1\n\n'`, locator lines 5343-5344, offsets 512124-512137 of
`instructions_form_1040_2025`. **S118 typed it `STUB SECTION` and dropped it from the packet, which
is correct for the packet and wrong as a name.** Reading the raw booklet at 512137 - the very next
byte - gives:

```
#### Taxable Refunds, Credits, or Offsets of State and Local Income Taxes
**TIP** None of your refund is taxable if, in the year you paid the tax, you either (a) didn't
itemize deductions, or (b) elected to deduct state and local general sales taxes instead ...
```

**That is the actual Schedule 1 line 1 instruction, and the section extent stopped at its heading.**
The section is not empty; it is TRUNCATED. So the cell's only surviving evidence is `...0068`, the
**30,083-byte** State and Local Income Tax Refund Worksheet, and micro-extraction fails
`quote does not match the supplied form or instruction evidence` - the model has a worksheet and no
instruction.

**S118 IS NOT THE CAUSE AND DROPPING THE 13 BYTES WAS RIGHT** - a heading with no body cannot supply
a quote. **What S118 got wrong is the LABEL**, and the label is the dangerous part: `STUB SECTION`
reads as an accepted terminal state, so a truncation that should be repaired is now filed as a
category that needs nothing. **That is precisely the laundering the S116 report was built to
prevent, reappearing one level up.**

**WHY THIS IS PROBABLY THE BIG ONE.** The report's largest actionable bucket is
**91 `CELL WITH NO INSTRUCTION + BOOKLET MENTIONS IT`** - by construction, cells whose instruction
the booklet demonstrably contains and the parser did not attach. **A truncation that keeps the
heading and drops the body would land in exactly that bucket**, and would also explain
`form_6251` 33 and `schedule_d` 18. **Measure that before speccing a fix**: for every stub and every
unmatched cell, read the raw text after the section's end offset and report how much body was left
behind. **Do not assume the shape from this one instance - open several.**

**THE SEQUENCING QUESTION FOR JOHN, and it is a real fork.**
1. **Extent repair** - fix the parser so line sections carry their bodies. Largest reach, touches
   acquisition, and `../docs/source-extents.md` already pins direction for it.
2. **Cell-loop concurrency** - the corpus is latency-bound on a serial per-cell loop while
   `extraction.concurrency` already exists and only `background.py` reads it. **Does not improve
   quality at all**; makes every future round cheaper to verify.
3. **The 4 surviving ambiguities** - three headings that name another form's line
   (*"Taxable Dependent Care Benefits From Form 2441, Line 26"* claiming 1040 line 26) plus a
   `2i`/`2I` case-fold collision on `form_6251`. **Real, small, and 4 cells.**

**The Architect's recommendation is 1, measured first per the paragraph above.** 3 is a footnote and
2 is a convenience.

## Open for Architect

*(Nothing open.)*


## Queued (ONE LINE each - do not spec ahead)

**JOHN'S PRIORITY, 2026-08-10: get the CORE documents processing reliably.** Ordered for that.
**Every item below is a PIPELINE change - none of them is a per-cell human correction.**

**DIRECTION PINNED 2026-08-13 IN `../docs/source-extents.md`. DO NOT REDESIGN IT HERE.** A citation
should record WHERE its text is, not carry a copy of it, and a source chunk that is not a numbered
row should say what it is and what it governs. **The queue has NOT been reshaped around it yet -
that is John's call.** What the doc settles is that items 2, 3, 6 and the recurring extent defects
are one root cause and should stop being specced as separate cue-matching repairs.
**M20-S103 is the first round off that direction and it MEASURES rather than wires**; the storage
round is specced from its output.

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

**NO NEW WORKER IMPLEMENTATION SLICE IS SPECCED AFTER M20-S108 ITEM 1.** The next action is
Architect-owned live re-derivation against the corrected schema, followed by the reported corpus
numbers and constant-case ids. The Worker has completed the offline correction and guard evidence
above; do not start a new provenance or citation round.

**HISTORICAL S107 NOTE - SUPERSEDED.** M20-S107 closed the
last A9 scaffolding seam in the core citations: re-extract 30 hand-authored paraphrases from their
acquired source, and give the 4 synthesized tax-bracket citations a provenance kind that admits they
are computed.

**THE FAILURE MODE TO AVOID IS SPECIFIC AND IT HAS ALREADY HAPPENED ONCE.** S107 changes
`quoted_text` on purpose, which is the exact operation that got the S106 rework rejected. **The
difference is direction: the rejected pass truncated real quotes to fit wrong ranges; S107 replaces
hand-authored text with what the document actually says.** The guard must keep the SOURCE pinned and
assert the changed set is exactly the named 30. **A diff count other than 30 is a stop, not a
judgment call.**

**AND A NOTE TO MYSELF.** Two of my last three specs set a floor the data could not meet - `7ba64be`
(the drop-to-zero target) and S106 (every core citation binds). Both times the Worker hit the target
honestly and the spec was wrong. **Before writing the next floor, check that the corpus can satisfy
it**; the 34-citation characterization that produced S107 took twenty minutes and would have
prevented S106's red guard entirely.

## History

Everything before M20-S23, and all per-round Worker narration, lives in git history. This file was
pruned from 7,520 lines on 2026-08-02 at S28 acceptance; `git show 12240ef:plans/AGENT_HANDOFF.md`
is the last unpruned copy. Earlier prune: 2026-07-23, from 1,198 lines, for public-repo prep.
Durable rulings were carried forward into **Binding rulings** above rather than deleted; A9
rulings remain pinned in `plans/PHASE_M15.md`; the defect ledger (D6, D9, D10, D12, D13, D14) is
in `AGENTS.md`.
