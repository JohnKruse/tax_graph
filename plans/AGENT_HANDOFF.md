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

**BALL: CODEX. M20-S121 goes back - the mechanism is right, two verification
assumptions are contradicted by the first live run, and the real recordings are now checked in.**

**JOHN RULED THE FORK, 2026-08-17: THE MATCHER GOES MODEL-OWNED, AND THE MODEL MUST BE NAIVE ABOUT
THE CELLS.** He raised the objection that decides the design: *"I'm afraid to give a model too much
if it is to pick out the instructions. We have the example of line 24 referencing line 22 and the
instructions for line 22 get jammed in."* **Asking a model for one cell's instruction is a question
with a demand in it. Asking it to describe a document's sections is not.** So the model segments the
booklet, never sees a cell, and code does the join. **This is also the boundary John set on
2026-08-02** - the form face is exact, the instruction pages are loose, the AI reconciles.

**THE DETERMINISTIC MATCHER LINE IS CLOSED. Five rounds, S116 through S120, and every one found the
previous one's blind spot** - cross-form `Line 9`, multi-line headings, nested duplicates, worksheet
row numbers read as form lines. **Those are all semantics a person reads instantly and a heading
parser cannot. Do not spec another one.** The topic-organised booklets settle it: `schedule_1a`'s 48
cells and `schedule_b`'s 8 have no line token to match and **no deterministic matcher can ever
reach them.**

**M20-S120 IS ACCEPTED (`e2294b8`, Architect, 2026-08-17), VERIFIED BY RECOMPUTATION.** I re-tiled
every one of S119's **56** parent spans from the artifact myself: the **414** split rows are
contiguous, non-overlapping, hit the parent endpoints exactly and sum to the parent length, in every
booklet - **zero conservation failures**. All **81** cells are classified with **0 omitted and 0
extras** against S119's negatives, and the EIC table and front matter are marked non-actionable.
**9 passed.** The round did exactly what it was asked; **what it was asked was partly wrong, and
that is recorded under Current round.**

**M20-S119 IS ACCEPTED (`0d7aa76` + `77e56c8` + `8c70a70`, Architect, 2026-08-17), VERIFIED BY
RECOMPUTATION.** All 8 booklets reconcile against recomputed hashes and file sizes; every named
floor case holds. **Its finding stands and is the durable one: extent truncation is 10 of 91 cells,
all `form_1116`.**

**M20-S118 IS ACCEPTED (`3181169` + `a4cd008`), M20-S117 (`954c235`), M20-S116 (`6beb1f4` +
`29cbbcd`), M20-S114 (`9f856a9`), M20-S113 (`6b855b4`)** - all verified by recomputation, narration
in git. **What survives of them:**
- **Nested duplicates in evidence packets are gone** (17 -> 0) and `AMBIGUOUS` is 4, not 60.
- **The reconciliation report asks `instruction_span_ids_for_line` and nothing re-implements the
  match.** Report state equals packet state, asserted over every cell.
- **THE RULE COUNT IS NOT A QUALITY METRIC. NEVER USE IT AS A FLOOR AGAIN.**
- **A green replay harness is not evidence about a packet change** - check whether its cases even
  cover the changed cells first. On S118 the two sets were disjoint.
- **Verify an artifact by recomputing what it asserts**, not by checking it exists and is green.
  Three rounds in a row, that is what found the defect.

**CORPUS, ALL 17 DOCUMENTS, 2026-08-17: rules 74, edges 181, gaps 154**, 41 minutes. **Not
comparable to the S113 record of 78/224/153** - different counting method, four rounds between.
**Blast-radius check was clean: 17 of 19 changed cells derive**, `form_1040` 6b now derives, and the
two that do not are an outline-index defect and `schedule_1` line 1.

**M20-S115 IS DELIVERED AND WAS NEVER ACCEPTED (`4f7abf9`, Codex, 2026-08-16). ARCHITECT MISS,
CAUGHT WHILE REVIEWING THE PUSH RANGE 2026-08-17.** The review contract - `workbench/server.py`,
`generated_review.py`, the new `review_defects.py`, `test_m20_s115.py` and the workbench front end -
went in and the Architect specced S116 the next morning without verifying it. **It is on `main` and
now on the remote, unverified.** It touches the surface John reviews, so it needs a live check, not
a test read: **that is the Architect's leg and it is owed before the review contract is trusted** - and John does
not review while the contract keeps moving, so an unverified contract change is worse than none.

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

**M20-S108 (`c2dc0d8` ...), S107 (delivered, not accepted), S106 (`d8accca`), S105 (`98d81dc` +
`82962eb`) - narration pruned 2026-08-17, all in git. **What survives: the corpus varies +/-2 rules and
+/-5 edges run to run, so a single-run delta smaller than that is not evidence; and `prompt-bench`
accepts rows the corpus then rejects, so never quote its verdict as the corpus verdict.**

**THE 18-RED BASELINE, unchanged and still current.** Eleven `tests/e2e/*_m15.py`, plus:
`test_address_campaign_m15r::test_form_8949_cross_form_claims_resolve_exactly`,
`test_field_identity_m16::test_schedule_2_raw_cache_reproduces_target_fields`,
`test_m20_s71::test_real_candidate_node_labels_use_clean_text`,
`test_review_preflight_m15::test_real_2025_preflight_passes_with_all_coverage_dimensions`,
`test_review_scope_migration_m15::test_live_queue_migration_gives_every_pending_entry_a_primary_target`,
`test_schedule_2_m16::test_schedule_2_part_i_raw_acroform_identity`,
`test_schedule_d_extraction_m9::test_schedule_d_fixture_drafts_include_schema_valid_band_tables`.

## Current round

**M20-S121 IS NOT ACCEPTED. THE MECHANISM IS BUILT AND THE PROVIDER-FREE LEG IS GREEN, BUT THE FIRST
LIVE RUN CONTRADICTS TWO OF ITS VERIFICATION ASSUMPTIONS.** Codex's work is sound and the design is
right; **the fixtures it had to invent encoded assumptions the real model does not share.** Finish
it against the real recordings, now checked in.

**THE HEADLINE, AND IT IS GOOD NEWS: THE APPROACH REACHES WHAT THE PARSER STRUCTURALLY CANNOT.**
Live on `instructions_schedule_b_2025`, where the deterministic parser finds **0 sections and 0 of 8
cells**, the model returned **31 sections and found the line instructions** - lines **1, 3, 5, 7a,
7b**. It found them because in that booklet the line instructions are **bold run-in labels inside a
paragraph** (`**Line 1.** Report on line 1 all of your taxable interest...`), **not headings.** No
heading parser can ever see those. **This is the case John chose this direction for, and it works.**

**AND IT DID NOT MAKE THE MISTAKE JOHN FEARED.** On `instructions_schedule_d_2025` the model claimed
line tokens up to **47**, which Schedule D does not have. **Those are worksheet rows, and the model
attributed them to the worksheet, not to Schedule D** - `document_id: 'Schedule D Tax Worksheet'`
on exactly the sections carrying 23-47. **The line-24-referencing-line-22 confusion did not happen.**
Cell-naive segmentation appears to be doing the job it was chosen for.

---

### DEFECT 1 - `document_id` IS FREE TEXT, AND THE JOIN CANNOT USE IT

Across 93 live Schedule D sections the model returned **six different spellings of the owner**:
`instructions_schedule_d_2025` (45), `schedule_d_2025` (28), `Schedule D (Form 1040)` (13),
`Schedule D Tax Worksheet` (4), `Schedule D` (2), `unrecaptured_section_1250_gain_worksheet_2025`
(1). **The model knows who owns what; it is saying so in English.**

**Constrain `document_id` to the manifest's document ids** - pass the valid ids for that booklet in
the prompt and reject anything outside the set. **This does NOT break cell-naivety**: a document id
is document identity, not a cell, an outline, an address or an unmatched list. **Note that
`instructions_schedule_d_2025` is the SOURCE, never an owner**; that value must be rejected outright.

### DEFECT 2 - THE VERIFIER ASSUMES HEADINGS ARE MARKDOWN HEADING LINES

`verify_model_sections` compares the response heading against the whole source line and fails closed.
Two ways that fires on real output:
- **Markup**: model returns `Page 1`, source line is `# Page 1`. **Cosmetic** - and note the
  PRODUCTION frame stores headings without the hashes, so the model matches our own convention and
  the pilot is stricter than the pipeline.
- **Run-in labels**: model returns `Line 1.`, source line is the entire paragraph
  `**Line 1.** Report on line 1 all of your taxable interest...`. **This is the Schedule B case and
  it is the whole point of the round.**

**Keep the anti-fabrication property** - the heading must still be found at that byte - **but match
it as a prefix of the source line after normalising markup, not as whole-line equality.** A section
whose heading is not present at its start byte must still fail.

### DEFECT 3 - THE FIXTURES WERE HAND-AUTHORED, AND THAT IS THE ARCHITECT'S DEFECT, NOT CODEX'S

My floor said *"runs from a RECORDED response fixture"* and gave it to an agent with **no egress and
therefore no way to record anything.** Codex wrote plausible responses by hand and was transparent
about the live leg being mine - **but hand-written fixtures test the author's assumptions, which is
exactly why 11 tests passed while the first live call failed on byte 0.** The reported
fixture scores (Schedule B model 7, gained 7) **are not evidence about the model and must not be
quoted.**

**THE REAL RECORDINGS ARE NOW CHECKED IN:** `pilot/fixtures/m20_s121_live_recorded_responses.json`
- live `openai/gpt-5.6-luna`, one call per window, `prompts/instruction_segmenter.md` unmodified,
2 windows / 31 sections for Schedule B and 9 windows / 93 sections for Schedule D, each with its
source hash. **Build the round against these. Delete the hand-authored fixtures** - keeping both
invites scoring against the wrong one.

---

**WHAT MUST NOT HAPPEN.**
- **Do not tune the prompt to make the numbers better.** Fix the two defects, rescore, report.
  **A prompt fitted to two booklets will not survive the third.**
- **Do not relax the verifier past "the heading is present at that byte".** Fabrication detection is
  the reason the model is allowed to choose at all.
- **Do not show the model cells, outlines, addresses or unmatched lists.** Document ids are allowed
  and nothing else is.

**THE FLOOR.**
- **The live recordings verify end to end** - both booklets, byte conservation holding, no manual
  edits to the recordings.
- **A fabricated section still fails**, proven by a test.
- **A `document_id` outside the manifest set fails**, proven by a test, `instructions_*` included.
- **The A/B is rescored on the live recordings and reported per booklet**, both directions, gained
  and wrongly-owned. **Report what it is; do not floor on the number.**
- **`tools/check_ascii.py` OK**, `git diff --check` clean, targeted tests only.

**ARCHITECT'S LEG.** Re-running live after the fixes, and the 1040 booklet - **which needs
chapter-scoped windows, not byte windows, and I owe that amendment; it is in Queued below.**

**CODEX STATUS (2026-08-17): PROVIDER-FREE LEG COMPLETE.** `pilot/model_instruction_segmenter.py`
now derives the booklet owner vocabulary from manifest relationships, puts that vocabulary in the
source-only prompt and structured schema, and rejects every other `document_id`, including the
instruction source id. Heading witnesses accept Markdown presentation and run-in labels only
when the claimed heading is a prefix of the source line at the claimed byte. The hand-authored
fixtures are deleted; the checked-in live recording is the only replay input.

Recorded replay preserves raw model output and makes the reconciliation explicit: duplicate
window observations are deduplicated by source-start heading, section ends are derived from the
next verified heading so the source tiles exactly, and source-unbacked proposals are dropped and
listed in coverage. The strict provider path still rejects those proposals. The live recording
has two such Schedule D proposals at bytes 33026 and 51283; they are recorded, not repaired in
the fixture.

RAN: `.venv\Scripts\python.exe -m pytest pilot\test_model_instruction_segmenter_m20_s121.py -q`
-> **15 passed, 1 warning in 0.89s**.

RAN: `.venv\Scripts\python.exe tools/check_ascii.py` -> **ASCII check OK**.

RAN: `git diff --check` -> **clean**.

Live A/B replay evidence: Schedule B is **28 canonical sections from 31 raw, 0 gained, 5
wrong-owner, 4 reachable cells**. Schedule D is **82 canonical sections from 93 raw, 0 gained,
34 wrong-owner, 24 reachable cells**. Both frames reconcile to the complete source bytes.

**CODEX REWORK COMPLETE (2026-08-17):** overlapping ``governs`` disagreements are now
reconciliation cases. The observation with the greatest following window context wins; ties and
sections touching a window edge in every observation are rejected with their competing claims.
The frame reports ``governs_conflict_count`` beside the existing owner count, never unions claims,
and keeps the rest of the source tileable. The provider-free S121 tests cover all three paths and
the checked-in live recordings.

RAN: `.venv\Scripts\python.exe -m pytest pilot\test_model_instruction_segmenter_m20_s121.py -q`
-> **18 passed, 1 warning in 0.93s**.

RAN: `.venv\Scripts\python.exe tools\check_ascii.py` -> **ASCII check OK**.

RAN: `git diff --check` -> **clean**.

S121 remains unaccepted until the Architect repeats the live leg; this rework has no provider run.

## Open for Architect

**ARCHITECT LIVE LEG RUN, 2026-08-17. S121 IS STILL NOT ACCEPTED - ONE NEW DEFECT, AND IT IS A
DESIGN CALL I OWE, NOT A CODEX ERROR.**

**WHAT PASSED, VERIFIED BY RECOMPUTING THE ARTIFACT, NOT BY READING THE REPORT.** Replay of the
checked-in recording reproduces Codex's numbers exactly: `schedule_b` **31 raw -> 28 unique**, 3
duplicates, 2 boundary-repaired, **0 rejected**; `schedule_d` **93 raw -> 82 unique**, 11 duplicates,
5 boundary-repaired, **2 rejected** (bytes 33026, 51283, disclosed and unrepaired).
**`reconciles_to_file_size` TRUE on both.** Provider-free suite **15 passed**.

**LIVE RE-RUN: `schedule_b` SUCCEEDED (29 sections). `schedule_d` FAILED CLOSED:**

```
SegmenterError: overlapping windows disagree about governs at 10062
```

**THE RECORDING COULD NOT HAVE PREDICTED THIS. I checked: the recording contains ZERO `governs`
disagreements on either booklet.** Its 3 and 4 conflicts are owner SPELLINGS
(`instructions_schedule_b_2025` vs `Schedule B (Form 1040)`), which defect 1's manifest constraint
already normalises. **This is a class that only a live call produces.**

**THE CAUSE IS STRUCTURAL AND WILL RECUR ON EVERY BOOKLET.** Windows are 12,000 bytes with 2,000
overlap. Byte 10062 is **62 bytes inside the overlap**: window 0 sees that section with ~1,900 bytes
of trailing context, window 1 sees it jammed against its own start edge with nothing before it.
**Two different views of the same text produce two different `governs`. That is not model
flakiness - it is the overlap doing what an overlap does.**

**RULING: A `governs` DISAGREEMENT IN AN OVERLAP IS A RECONCILIATION CASE, NOT A FATAL ERROR.**
Failing the whole booklet over one contested section is wrong: **82 verified sections are discarded
because of one.** The code already treats the analogous case correctly - `owner_conflict_count` is
counted and normalised, and source-unbacked proposals go to `rejected_sections` without killing the
run. **`governs` must behave the same way.**

**THE TIEBREAK, AND IT IS DETERMINISTIC - DO NOT PICK ARBITRARILY AND DO NOT UNION.**
1. **Prefer the observation from the window that gives the section the most following context** -
   i.e. the greatest distance from the section start to that window's end. A window that sees the
   whole section has better evidence than one that sees a fragment. At 10062 that is window 0.
2. **If the distances tie, or if the section abuts an edge in every window that saw it, REJECT that
   SECTION** - list it in `rejected_sections` with the competing claims - **and keep the rest of the
   booklet.**
3. **Never union the governs sets.** A union over-claims, and an over-claimed `governs` is exactly
   the wrong-instruction failure this whole line of rounds exists to prevent.
4. **Report the count** as `governs_conflict_count`, alongside `owner_conflict_count`.

**THE STANDING LESSON, NOW TWICE.** A recording verifies CODE PATHS and never MODEL BEHAVIOUR. The
replay harness taught this on S109 (`production prompt differs from recorded prompt` on 19 of 20
cases); S121 repeats it. **A green replay is never evidence that a live run will pass** - and the
Architect's leg exists precisely because Codex has no egress.

**ALSO OBSERVED, NOT A DEFECT:** live `schedule_b` produced **29** sections against the recording's
28. Ordinary run-to-run variance at the same order as the corpus's +/-2 rules.

## Queued (ONE LINE each - do not spec ahead)

**CHAPTER-SCOPED WINDOWS FOR THE 1040 BOOKLET (Architect owes this, 2026-08-17).** 675,580 bytes,
126 pages, four forms in one file. Byte windows can cut between `Instructions for Schedule 2` and its
`Line 9` section, which reintroduces the S116 wrong-form defect at segmentation time. **The
deterministic chapter split is the one part of the parser that has never failed** - 317 sections to
four documents, 70/114/67/66 - so window on chapters and cross-check the model's `document_id`
against the chapter a section physically sits in. Chapter sizes: 1040 252KB, Sch 1 48KB, Sch 2 19KB,
Sch 3 13KB.

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
