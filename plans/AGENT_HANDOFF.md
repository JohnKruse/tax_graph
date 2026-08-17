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

**BALL: JOHN, FOR ONE COMMAND, AND CODEX IN PARALLEL. M20-S124 IS ACCEPTED. The 1040 booklet is
built and windowed and needs its live run, which needs egress - that is the one thing only John can
release. M20-S125 is specced under Current round and does NOT wait on it.**

**M20-S124 IS ACCEPTED (`6006c87`, Architect, 2026-08-17), VERIFIED BY RECOMPUTATION.** I derived
the chapter boundaries in the raw-byte space my own way and checked them against the source rather
than against Codex's offset table: **five chapters, every boundary landing exactly on the raw line
that triggered the context change** - `# Instructions for Schedule 2` and the rest - tiling 0 to
683,265 with no gap. **71 windows, every one inside exactly one chapter, covering each chapter with
no gap.**
- **The CR conversion is right, and it is not a rounding detail.** 683,265 bytes on disk against
  675,580 characters after newline collapse, **7,685 CRs of drift** that accumulates: the Schedule 2
  boundary is at character 508,434 and byte 513,738. **A character offset passed into the byte API
  would have put every late chapter kilobytes off its heading.**
- **Item 2 landed in both directions, which is the part that was easy to get wrong.** Each chapter
  narrows the vocabulary from 18 documents to **14 - one form plus all 13 worksheets.** I drove my
  own synthetic booklet through it: a Schedule 3 claim inside the Schedule 2 chapter is rejected as
  `chapter_owner_disagreement` with the booklet still tiling around it, **and a worksheet owner in
  the same position is kept.** Narrowing the worksheet half too would have re-broken what S123 had
  just fixed.
- **The no-op floor holds exactly.** Schedule B 29 sections, Schedule D 93 from 104 raw claims, 0
  rejected, 0 `wrong_form_owner`, 58 `sibling_worksheet_owner`, byte conservation to EOF on both.
- **The prompt now names the chapter's form**, so the constraint reaches the model as a prior and
  not only as a punishment. Still document ids only; no cells.

**CODEX DID NOT COPY MY SPEC'S NUMBERS, AND IT WAS RIGHT NOT TO.** The chapter table I wrote into
S124 was in the collapsed-character space; the real raw-byte chapters are ~1% larger. It derived
them from the tracker instead of pinning my table.

**M20-S123 IS ACCEPTED (`129cb0f` + `72555bc`, Architect, 2026-08-17), VERIFIED BY RECOMPUTATION.**
I reimplemented the parser, the bounded heading repair, the dedup, the end-recomputation and the
owner split myself and reproduced every number Codex reported: Schedule B **29 raw claims -> 29
sections**, Schedule D **104 raw claims -> 93 sections, 0 rejected, 1 governs conflict**, both
tiling from byte 0 to EOF with every heading witnessed in the source. **The structural change did
what it was specced to do: a fixture that used to abort the booklet now completes with nothing
rejected at all.**
- **The `Line 4.` run-in label at byte 71963 is recovered**, owned by
  `unrecaptured_section_1250_gain_worksheet_2025`, governing `4`, end recomputed to 72117. That is
  the construct this whole line of rounds exists to reach, and it was being discarded over a field
  the code never used.
- **`verify_model_sections` is untouched** - byte conservation from 0 to EOF, the heading witness
  and the manifest owner check all still fail closed, and the rejection matrix proves a malformed
  section drops out while its neighbours still verify.
- **The owner split is real, not a relabelling.** `wrong_form_owner` is **0** on both booklets and
  all **58** `sibling_worksheet_owner` rows name one of the four Schedule D worksheets, which the
  manifest links to this booklet by `region.source_document_id`. **Not one names a foreign form.**

**THE COVERAGE NUMBER IS THE ONE TO READ, AND SCHEDULE B IS THE WHOLE CASE FOR THIS DIRECTION.**
Schedule B goes **0 -> 8 of 8**. **Schedule D goes 11 -> 12 of 24, and that is the ceiling, not a
shortfall** - the booklet writes instructions for exactly those twelve lines and the segmenter
finds all twelve, as I confirmed by opening every one of the other twelve on 2026-08-17. **Schedule
D was never the case for this work; the deterministic parser was already at 11 of 12 there.**

**I WROTE THE OWNER SPLIT DOWN BACKWARDS BEFORE I READ THE MANIFEST.** My first re-derivation
returned 58 `wrong_form_owner` and 0 sibling, the exact inverse, because I read `region_of` off the
top level of the entry when the manifest nests it under `region:`. **Codex was right and my
recomputation was wrong.** Same lesson as always: open the artifact before believing the number.

**M20-S122 (`13e0937`) AND M20-S121 (`faded97` + `119e88a` + `ad846d2`) ARE ACCEPTED, both verified
by recomputation and by live runs on both booklets - narration pruned 2026-08-17, all in git.
What survives of them:**
- **The direction John chose is proven end to end on the case it was chosen for.** On
  `instructions_schedule_b_2025` the deterministic parser finds **0 sections and 0 of 8 cells**;
  the model segments it live into 29 sections and **8 of 8 cells correctly owned**. Those line
  instructions are bold run-in labels inside a paragraph, which no heading parser can ever see.
- **The manifest owner constraint killed the owner-spelling problem outright** -
  `owner_conflict_count` is 0 on both booklets live - and the governs context tiebreak resolves
  every overlap conflict with none rejected for ambiguity.
- **The bounded unique-line-boundary heading repair keeps the anti-fabrication property.** Do not
  widen it.
- **The CLI persists each window BEFORE it verifies.** That paid for itself the same hour it
  landed: the next live failure kept its recording instead of burning 9 paid calls again.

**A RECORDING VERIFIES CODE PATHS AND NEVER MODEL BEHAVIOUR - THIS IS NOW THE THIRD TIME.** The
checked-in S121 recording contains **zero** governs conflicts on either booklet, so the entire
rework was covered only by synthetic tests until I ran it. S109 taught this with `production prompt
differs from recorded prompt` on 19 of 20 cases. **Never accept a reconciliation change on replay
evidence alone.** Related: seed 7 does NOT make this deterministic - Schedule D returned 93 raw
sections recorded and **105** live.

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

**M20-S125: MAKE THE COVERAGE METRIC HONEST BEFORE THE 1040 RUN, NOT AFTER. I JUST READ MY OWN
REPORT WRONG AND SPECCED A DEFECT THAT DOES NOT EXIST.**

**I QUEUED "THE SCHEDULE D JOIN IS THE NEXT COVERAGE DEFECT" ON THE STRENGTH OF 12 OF 24. I OPENED
THE 12 AND THERE IS NO DEFECT.** The Schedule D booklet writes dedicated instructions for exactly
twelve lines - `1a`, `1b`, `2`, `3`, `8a`, `8b`, `9`, `10`, `13`, `18`, `19`, `21` - **and the
segmenter finds all twelve.** The other twelve form lines are the arithmetic and carry lines
(`4`, `5`, `6`, `7`, `11`, `12`, `14`, `15`, `16`, `17`, `20`, `22`) that the IRS writes no
instruction for at all. **12 of 24 is not half a defect. It is twelve of twelve against what the
booklet actually contains, and the segmenter is at its ceiling on Schedule D.**

### ITEM 1 - `model_reachable` IS LYING AND IT IS THE NUMBER THAT FOOLED ME

`model_reachable` counts a cell as reached when **any** section governs its line token, **including
a foreign worksheet's own row number.** Schedule D reports **24 of 24 reachable** while twelve of
those cells have no `schedule_d_2025`-owned section anywhere in the booklet. The Schedule D Tax
Worksheet governs its rows `4`, `5`, `6`, `7`, `11`, `12`, `14`... which collide head-on with the
form's line numbers. **A match by a document that is not the cell's own document is not reach.**
Count reach only through a section owned by the cell's document.

### ITEM 2 - REPORT THE DENOMINATOR THAT MEANS SOMETHING

Add **`instructed_cell_count`**: cells whose line is governed by at least one section owned by the
cell's own document. **Report `model_correct` against BOTH** the full cell count and that
denominator. On Schedule D today that is 12 of 24 cells and **12 of 12 instructed cells**; on
Schedule B, 8 of 8 and 8 of 8. **Do not hardcode either pair** - they are outputs, and the 1040
booklet will have its own.

### ITEM 3 - THE ROW-NUMBER COLLISION IS THE STANDING HAZARD, SO NAME IT

Report **`row_number_collision_count`**: line tokens claimed by both the cell's own document and a
sibling worksheet. It is 12 on Schedule D. **This is the same semantic collision that killed the
deterministic matcher across S116-S120** - worksheet row numbers read as form lines - and on a
booklet with 13 worksheets it will be much larger. **Measure it now, before it is a surprise.**

---

**WHAT MUST NOT HAPPEN.**
- **Do not change the segmenter, the prompt, the chapters or the fixture.** This round touches
  scoring and reporting only. If a section count moves, the change is wrong.
- **Do not weaken `verify_model_sections`**, and do not re-record anything.
- **Do not "fix" the twelve uninstructed Schedule D lines.** They are the booklet's content, not a
  bug, and a round that makes them appear covered would be manufacturing the metric.

**THE FLOOR - ALL OF IT PROVABLE WITHOUT A MODEL CALL.**
- **Section counts unchanged**: Schedule B 29, Schedule D 93 from 104 raw claims, 0 rejected, byte
  conservation to EOF, `wrong_form_owner` 0 and `sibling_worksheet_owner` 58.
- **`model_reachable` on Schedule D drops from 24 to 12** and a test names why: a worksheet row
  number is not reach for a form cell.
- **`instructed_cell_count`, `row_number_collision_count` and the two-denominator `model_correct`
  are reported for both booklets**, computed, not pinned to a constant.
- **`tools/check_ascii.py` OK**, `git diff --check` clean, targeted tests only.

**ARCHITECT'S LEG.** The live 1040 run, once John releases egress. It is 71 windows and therefore
71 paid calls, and this round is what makes the report it produces readable.

## Open for Architect

Nothing open. Raise items here.

## Queued (ONE LINE each - do not spec ahead)

**`sibling_worksheet_owner` MASKS WORKSHEET-TO-WORKSHEET MISATTRIBUTION (Architect, measured
2026-08-17).** The bucket is correct today only because all four Schedule D worksheets have **0
cells** in the reconciliation population, so the denominator is zero. **The moment worksheet cells
enter it, a worksheet row attributed to the WRONG sibling worksheet scores as correct behaviour.**
Split it again then, or key it on whether the owner is the cell's own document.

**[WITHDRAWN 2026-08-17, THE SAME DAY I WROTE IT - THERE IS NO SCHEDULE D JOIN DEFECT.]** I read
"12 of 24 cells owned" as a shortfall without opening the twelve. They are the arithmetic and carry
lines the IRS writes no instruction for. **The metric that misled me is being fixed as M20-S125;
the round I nearly specced would have chased a defect that does not exist.**

**THE LIVE 1040 SEGMENTATION RUN (Architect owes this; blocked on John's egress only).** 71
windows, 71 paid calls, chapters and windows already built and verified at `6006c87`.

**`_write_recording` CLOBBERS THE FIXTURE INSTEAD OF MERGING INTO IT (Architect, read 2026-08-17).**
It writes a payload containing ONLY the booklet just run, so pointing `--output` at
`instruction_segmenter_live_recordings.json` would **destroy the paid Schedule B and D recordings**
that every floor since S121 rests on. A live recording is bought with money and is not regenerable
output. **Merge by `source_document_id`, and until then the 1040 run writes to its own path.**

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
