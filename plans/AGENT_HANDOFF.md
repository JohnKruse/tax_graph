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

**BALL: WORKER - M20-S93 (a line value that is not a line must fail at derivation). SMALL round,
spec under Current round. Worksheets are staged as queue item 2, ready to promote after.**
**JOHN'S PRIORITY, 2026-08-10: get the CORE documents processing reliably. Every queued item is a
PIPELINE change - none is a per-cell human correction.**

**THE WIDE RUN IS DONE AND IT ANSWERED THE BREADTH QUESTION: 356 of 410 anchors (86.8%) across 11
documents for $0.2512, with the eight never-derived documents at 79-96%.** Quality generalized.
`...\cand`.**

**THE ANSWER TO YOUR OVERFITTING QUESTION: QUALITY GENERALIZED. 356 of 410 printed anchors (86.8%)
across 11 documents for $0.2512.** The eight documents we had NEVER derived came in at **79-96%**,
several ABOVE the three-form set that everything was tuned on.

| document | anchors | coverage | |
| --- | --- | --- | --- |
| `schedule_a_2025` | 28 | **96.4%** | first run |
| `form_6251_2025` | 63 | 92.1% | |
| `schedule_1a_2025` | 48 | **91.7%** | first run |
| `schedule_2_2025` | 45 | **91.1%** | first run |
| `schedule_1_2025` | 61 | **88.5%** | first run |
| `schedule_b_2025` | 8 | **87.5%** | first run |
| `form_1040_2025` | 59 | 86.4% | |
| `schedule_3_2025` | 35 | **82.9%** | first run |
| `schedule_d_2025` | 24 | **79.2%** | first run |
| `form_2441_2025` | 35 | 74.3% | |
| `form_8949_2025` | 4 | 0.0% | transactions table, expected |

**FLOOR: 3 of the 64 protected rows regressed, all on 2441 - lines 19, 21, 25. NOT ATTRIBUTED.**
Those exact rows have flipped in both directions across five runs now. **Treat 2441 19/21/25 as a
known-unstable set and stop reading them as signal.**

**BUT THE CANDIDATE WRITER FAILS ON THE WIDE CORPUS:**
`ValueError: candidate graph edge endpoint form_1040_nr_2025_root_line_tax_on_non_effectively_connected_income is not a canonical line address`

**THE CAUSE IS A REAL GAP BREADTH EXPOSED: 11 rows emit an operand whose "line" is a PHRASE, not a
line number** - and **10 of them are marked `derived`**, so derivation accepted what the graph
writer then rejected. **Two stages disagree about what a line is.**
- `form_1040_2025` `6b` -> `social_security_benefits_worksheet_2025` line **"taxable benefits"**
- `schedule_a_2025` `5e` -> `state_and_local_tax_deduction_worksheet` line **"amount"**
- `schedule_2_2025` `1d` -> `form_4255_2025` line **"2a, column (l)"**
- `schedule_3_2025` `13c` -> `form_3800_2025` line **"6, column (j)"**
- `schedule_2_2025` `17o` -> `form_1040_nr_2025` line **"tax on non-effectively connected income"**

**TWO DISTINCT CAUSES INSIDE THAT.**
1. **Worksheets again, from a new direction.** When a worksheet is not a document with addressable
   lines, the model DESCRIBES the value instead ("taxable benefits", "amount"). **More evidence for
   the worksheet ruling, arrived at independently.**
2. **COLUMN ADDRESSES.** Forms 4255, 3800 and 8949 carry values addressed by line AND column
   ("2a, column (l)"). **Our address grammar has no column. That is new and it is structural.**

**115 `unresolved_external_reference` warnings** - the stub path carrying the load it was built for.


**THE BIGGEST FINDING IS OURS, NOT THE MODEL'S.** 1040 `5a` fails `subtract_direction: instruction
says subtract line 6 from line 2`. Its instruction section is CORRECT but 11,424 chars long and
**embeds the Simplified Method Worksheet**, whose own numbered steps contain that phrase. **The
validator applies a worksheet's internal line numbers to the parent row.** 4 of the 15 rows share
that shape, and it would misfire on any line whose instructions embed a worksheet.

**M20-S91b ACCEPTED at `4e77e9e`. Extraction is done.**


**S91b, measured from `clause_extent`, not from an Architect harness.** **68 of 406 rows take the
bracket** (42 under S91), **35 faces changed**, and **ZERO rows took the bracket when the fallback
was longer** - the safety property held through both rounds. `( )` and mid-sentence fragments like
`'1 4361 2 4029 3'` are gone.
**Full suite 2026-08-09: 19 failed, 894 passed, 8 skipped, 1 xfailed in 0:56:58** - the SAME 19,
**zero new failures.**

**DERIVATION: 135 of 157 (86.0%), $0.1006, ZERO regressions against the protected 64.**
**I AM NOT CLAIMING S91b CAUSED THE +3.** Against the previous run 7 rows gained and 4 lost, and the
movement is not confined to rows whose text changed. **Rows churn between runs; report the
invariant, not the delta.**

**ONE CONTROLLED RESULT WORTH KEEPING. 2441 line 5 still fails identically** while its neighbours 19
and 25 now derive. **We changed its face text and its behaviour did not move** - which is what you
predict if the cause is the grammar, not extraction. **`REQUIRE_INPUT` can be a whole rule but not a
branch of one. That diagnosis is now confirmed by intervention, not by argument.**

**S92 - THE WIDE RUN - IS THE NEXT ROUND AND IT IS JOHN'S CALL.** All 11 acquired forms and
schedules, about $0.25-0.35. The command with the provider escape is under Queued. **This is the
round that tests whether three-form quality generalizes - the concern John raised on 2026-08-09,
which the extraction work has now cleared out of the way.**


**S90c ACCEPTED ON INVARIANTS, NOT ON A RUN DIFF.** Verified on a REAL candidate, not fixtures:
**22 stub nodes across 14 stub documents** at canonical `_root_line_` addresses, each carrying
"must be ingested or supplied by the caller"; integrity **230 nodes, 315 edges, 228 operands, ZERO
dangling ids**; the writer survives the corpus that crashed it; the document-only predicate raised
`unresolved_external_reference` warnings 8 -> 17. **Full suite 2026-08-09: 19 failed, 891 passed,
8 skipped, 1 xfailed in 0:57:21.** **One failure is NEW against the 18-failure baseline:**
`test_m20_s71::test_real_candidate_node_labels_use_clean_text`. **Named, not chased.**

**COVERAGE WAS 132 of 157 against S89's 139, AND I AM NOT ATTRIBUTING THE DIFFERENCE.** I twice
called the 2441 rows variance, then attributable, then variance again; the third run derived both.
**The handoff's own rule says prefer invariants that hold on ANY single run over diffs between two
runs, and I broke it twice. Judge rounds on invariants.**

**THE REAL FAILURE WAS INVISIBLE BECAUSE WE THREW THE EVIDENCE AWAY.** A rejected payload went out
of scope with the exception, so five rounds could only COUNT rejections. Fixed at `254877a`:
`attempted_payloads` keeps what the model actually answered, first attempt and repair.
**Immediate findings from ONE run with it on:** 2441 line 5's repair response is **byte-identical**
to its first attempt - the repair call can never succeed and is pure spend - and line 5's real
problem is that **`REQUIRE_INPUT` is legal as a whole rule but not as a branch of one**
(accepted on line 4, rejected inside `LOOKUP_TABLE` on line 5). **Both are queued, both are small.**


**WE HAVE ONLY EVER DERIVED 3 OF 11 ACQUIRED DOCUMENTS - 157 of 410 printed anchors.** Every number
in S88-S90b is measured on that 38%. **Eight forms and schedules are fully acquired and never
derived.** Going wider is now the priority; depth on the same three forms is not.

**M20-S90 NOT ACCEPTED at `056e3be`; S90b is uncommitted in the tree and its guard ruling is
answered.** The mechanism is right, the coverage floor is not met.


**IT COST 27 ROWS OF COVERAGE TO FIX 12 MISLABELLED ONES.** Live corpus run at
`C:\tmp\m20_s90\run`, temperature 0, $0.1032: **coverage 139 -> 112 of 157 (88.5% -> 71.3%)**,
**errors 11 -> 38**, model-stated inputs 67 -> 38.

**THE FLOOR IS BREACHED: 3 of the 64 protected rows regressed.** `form_6251_2025` line 13 is
**directly attributable** - it repaired to `max(qdcgt line 4, 0)` under S89 and now errors
`operand_document_not_found` because the model added `schedule_d_tax_worksheet`, a document
outside the inventory. `form_6251_2025` line 20 lost its floor and `form_2441_2025` line 25 threw a
LOOKUP_TABLE payload error; **both are plausibly sampling** - line 25 has failed nine prior runs -
**so I am not attributing them, only reporting them.**

**THE VALIDATOR GUARD NEVER FIRED. `external_reference_as_input` raised ZERO times in the run.**
The damage came entirely from the prompt clause telling the model to emit a canonical id even for
documents outside the inventory. It did - corpus-wide, not on the 12 targeted rows - producing
**59 `operand_document_not_found` and 10 `operand_inventory_unavailable`** failures.

**MY SPEC IS WHAT MADE THIS HAPPEN.** I wrote "must produce a NAMED FINDING, never a silent
`REQUIRE_INPUT`" without saying that a named finding must not be a HARD failure. An unresolvable
reference is a **known limit of the corpus**, not a defective derivation, and the two must not
share an outcome.


**THE GATE IS GONE AND NOTHING REGRESSED.** Against the S81 temperature-0 baseline, all **64** rows
that derived or repaired then still do - checked row by row, not by count. **Coverage 64 -> 139 of
157 printed anchors (88.5%)**, skips 90 -> the 7 structural rows, **cost $0.0954** over 142 priced
calls against the $0.09 predicted.
**Full suite 2026-08-08: 18 failed, 873 passed, 8 skipped, 1 xfailed in 0:56:59** - every failure
in the documented pre-existing families (the 4 named known-red, 11 `tests/e2e/*_m15` on the empty
queue, and the artifact-state `test_cli` / `test_field_identity_m16` / `test_review_preflight_m15`).
**Zero failures anywhere in `tax_graph/extract` or the m20 series**, passes 851 -> 873, protected-set
diff EMPTY.

**MY S88 HEADLINE WAS WRONG AND THE PRODUCTION RUN CORRECTED IT. "27 of 32 missed formulas recover"
was never a count of formulas.** `pilot/context_arms.py` scores recovery as any row reaching
`derived` or `repaired`, and `REQUIRE_INPUT` is a derivation - so the arms measured rows getting an
ANSWER. **Of the 32 named rows only 4 produce an expression** (1040 `16`; 6251 `5`, `7`, `19`); 23
answer `require_input`, 5 error. **This is the exact defect S89 was written to kill - a skip that
reports as success - reappearing one level up, in the measurement rather than the pipeline.**
Corpus-wide the deletion bought **13 new expressions and 67 model-asserted inputs**, and errors rose
**3 -> 11**.

**THE NEW OUTCOME HAS NOT EARNED ITS TRUST YET, which is what S90 is for.** 12 of 67 model-asserted
inputs (18%) have a printed face naming another form. **Do not read `model_stated_input` as fact.**

**S88 ACCEPTED at `49ff88a`.** Arm A shipped; context assembly unchanged. **Do not widen the context
or revisit buffers without new evidence** - wrong-line quotes went 0 -> 2 -> 6 as the window widened.
**The S89 floor run is at** `C:\tmp\m20_s89\run`.


**S81 ACCEPTED at `c89dd53`; temperature pinned at `50a64bf`.**
**Full suite 2026-08-07: 20 failed, 851 passed, 8 skipped, 1 xfailed in 0:57:21** - exactly the
known pre-existing set, zero new failures, passes 850 -> 851 on S81's own tests.

**2441 LINE 25 DERIVES after nine failed runs**, and the encoding sidesteps a gap we thought was
blocking: `max(0, if_else(line 22, 0, min(line 20, line 21), min(line 20, line 21) - line 24))`.
It tests **line 22 against 0** rather than needing a boolean predicate, using the form's own
structure - checking "No" makes line 22 read -0-, checking "Yes" makes it an amount. **Its
correctness still rests on the unstored comparator**, the same gap measured across 36 anchors.

**NEW DEFECT, from S74's inventory being too broadly scoped.** `form_6251_2025` line 13 now derives
`max(qdcgt line 4, instructions_schedule_d_2025 line 13, 0)` - an operand pointing at an
**instructions booklet**. A formula may reference forms and worksheets; it must never reference an
instructions document. Scope the inventory and make an instructions-document operand a named
finding.

**TEMPERATURE IS PINNED TO 0, AND THE CONFIG LINE ALONE WOULD NOT HAVE DONE IT.**
`derive_cells` was called without a `temperature` argument, so the derivation path used the
parameter default of `None` and never read `llm.temperature` - while `generator.py`, `critic.py`,
`micro.py` and `background.py` all did. Fixed, and the helper preserves an explicit zero because
**`0` is falsy** and a truthiness test would have discarded the pin silently. Live-verified that
`openai/gpt-5.6-luna` accepts it. **Caveats recorded in the example config:** this reduces variance
without removing it (batched inference is not bit-deterministic), and `allow_fallbacks: true` means
a routed endpoint may still reject or ignore it.

**BASELINE RESET. EVERY CROSS-RUN COMPARISON MADE BEFORE 2026-08-07 IS UNATTRIBUTABLE.** All prior
runs sampled at the provider default, so diffs conflated real change with sampling noise - including
the 2441 "1 error -> 4 errors" and `form_1040_2025` line 35a going `repaired -> error` under S81.
**Do not attribute those.** The next canary at temperature 0 is the new reference run.
**Prefer invariants that hold on ANY single run over diffs between two runs.**

**S74 ACCEPTED at `b153e94`. S75 ACCEPTED at `b2982c6`.**
**Full suite 2026-08-07: 20 failed, 850 passed, 8 skipped, 1 xfailed in 0:57:34** - exactly the
known pre-existing set, **zero new failures**, passes 846 -> 850 on S74's own tests.

**S74's acceptance test half-passed, and the other half was my error.** `form_6251_2025` line 13 now
derives `max(qualified_dividends_capital_gain_tax_worksheet line 4, 0)` - correct document, correct
line; the document inventory did its job. **Line 20 was never a wrong answer.** Its full text offers
three alternatives and ends *"If you did not complete either worksheet... enter the amount from Form
1040 or 1040-SR, line 15; if zero or less, enter -0-"*. It derived `max(form_1040_2025 line 15, 0)` -
the third branch, stated verbatim, floor included. S74 still improved it: yesterday it said
`form_1040_nr_2025`, the wrong filer's form. **The corpus now has ZERO known wrong references**; what
remains on line 20 is a three-way "whichever applies" the grammar cannot hold, which belongs with
named intermediates.

**UNRESOLVED and honest:** 2441 moved from 1 error to 4 (`self_reference` line 5,
`incomplete_evidence` line 8, `quote_not_verbatim` line 21, the standing line 25). The baseline run
predates BOTH S71 and S74, so the delta cannot be attributed without a third run. All four fail for
stated reasons rather than repairing into something unverifiable.
Active spec is under Current round. **S76 IS DEFERRED to queue position 1** (John, 2026-08-07);
**the S74 suite has FINISHED, so `tax_graph/` is free and S76 is unblocked whenever John wants it.**
John's arc, 2026-08-07: **fix column 1, then assess column 2, and column 3 should then fall out.**
S76 is the column-1 fix reaching production.

**S71 ACCEPTED at `e79f2cd`; S70 at `977e977`; S72 at `b18d9f1`; S73 at `78516bc`.**

**INSTRUCTION COVERAGE IS SETTLED: 84 of 153 candidate rows (55%)**, not 17. S73 found the cause -
the panel **discarded candidate rows whenever the denominator anchor carried a `skip_reason`** - and
a second alignment defect alongside it: the admitted `form_2441_2025` line 21 candidate was being
consumed by the preceding skipped header duplicate. Per document: **17/59 on 1040, 18/33 on 2441,
24/61 on 6251.** Verified independently by the Architect; S72's 17-arrow ceiling and S70/S71's
clean text both held, and 15 pilot tests pass.
**Full suite: 20 failed, 846 passed, 8 skipped, 1 xfailed in 1:01:19.** Those 20 are EXACTLY the
known pre-existing set minus `test_m20_s31`, which S71's sibling commit fixed - **zero new
failures**, and passes rose 841 -> 846 on S71's own tests. The 20 were triaged against
`origin/main` earlier with local artifacts junctioned in; 11 are `tests/e2e/*_m15` failing on an
empty review queue, the rest are artifact-state driven. `test_review_scope_migration_m15` remains
UNCOMPARABLE (skips at baseline) and is untriaged, not cleared.

**S71 verified on the real corpus:** 153 of 153 rows carry clean form-face text (was 67), 0 of 194
node labels carry the raw-OCR signature (was 46 of 232), coverage unchanged.
**S70 verified:** 0 of 157 panels render a raw label, down from 72; absence renders as absence.
**S70 carries one open defect into S72**: the panel reports 17 instruction sections present while
84 rows carry instruction text.

**S64 is ACCEPTED at `7189375`; S67 is ACCEPTED at `bb3daca`.**

**A candidate graph now exists.** Rebuilt from a fresh canary run: **194 nodes, 233 edges, 72 rules,
66 citations** across the three documents, with **65 of 67 attempted rows entering the candidate**
(61 derived, 4 repaired) and 2 held back as `review_gap` - one `quote_not_verbatim` on 2441, one
`self_reference` on 6251. Both are named findings, never silent drops.

**The first S64 measurement was invalid and the mistake is worth keeping.** The Architect ran the
candidate writer against the `s67-live` reports, which were produced BEFORE S64 taught
`derive_cells_s25.py` to carry `quote` and `quote_span_id` into `rows_detail`. Every derived row
therefore arrived with no citation, the pairing gate correctly demoted all 62, and the candidate came
out structurally empty - 0 nodes for every real document. **A run is only evidence for the code that
produced it.** Re-run derivation before measuring anything that consumes a report.

**Live: 67 attempted, 61 derived, 4 repaired, 2 errored.** `form_1040_2025` **17/17 with zero
repairs**, 2441 **20/21**, 6251 **28/29**. `doctor` gained a **`roles`** column, so the
layer-disagreement that caused S66 is now a check rather than a lesson.

**THE S54 COMPLETENESS VALIDATOR FIRED ON REAL DATA FOR THE FIRST TIME**, and correctly. 2441 line 8
produced all sixteen bands as CUMULATIVE thresholds (`under_15000=0.35, under_17000=0.34, ...`)
rather than the source's explicit ranges, and the validator refused it -
`lookup_table_band_overlap`, `lookup_table_missing_bands`, `lookup_table_bounds_mismatch`. Under
first-match semantics "under 17,000" contains "under 15,000", so the refusal is right. **The row has
still never derived, but it now fails for the correct reason.**

**TWO EXPRESSION NORMALIZERS ALREADY EXIST AND DISAGREE.** `workbench/address_verdicts.py:92`
`normalize_expression` speaks `kind`/`operation`/`operands` and **sorts commutative operands**;
`tax_graph/extract/candidate.py:573` `_normalize_candidate_expression` speaks `op`/`args` and does
not sort. Neither knows about the other. This is the S66 registry-versus-validator drift wearing new
clothes, and it is the reason the candidate diff cannot tell a real disagreement from a reordering.
**Whoever takes the diff round converges these rather than adding a third.**

**QUEUE - one line each. NOT SPECCED.**
1. **SCOPE THE DOCUMENT INVENTORY to forms and worksheets** - S74 included instructions booklets,
   so `form_6251_2025` line 13 derived an operand pointing at `instructions_schedule_d_2025`. An
   instructions-document operand must be a named finding. Small real-project round.
2. **S76 LIFT THE INSTRUCTION PARSER into `tax_graph/`** - deferred 2026-08-07, spec recoverable at
   `bcec03d`. Real-project; the invariant test is the deliverable: no instruction section filed under
   a line absent from that form's printed-line inventory. 106 phantoms -> 0, 1040 256 -> 143.
3. **`form_13614_c_2025` yields 0 printed anchors** - a manifest document producing nothing.
4. **Column 3 becomes the agreed notation** - the S69 flow is an edge dump: zero `<svg>`, zero
   diamonds, zero Yes/No arrows across all 157 panels; it renders `zero_floor` and node ids into the
   human column and re-narrates upstream lines. Must implement `docs/review-notation.md` rules 1-8,
   with phrasing read from the operation registry. Was specced at `41fffff`; recover with `git show`.
5. **LIFT the accessor into the project** - make `tax_graph/extract/candidate.py` use it so the
   GENERATED graph stops baking raw OCR into node labels (46 of 232 today), and move the invariant
   test into `tests/`. This is the round that pays the full-suite cost.
6. **Depth-normalized candidate diff** - all **5 of 5** overlapping rows report a false
   `expression_disagreement`, because the candidate expression refers to neighbours by node id while
   `_live_expression` inlines the handcrafted subtree; same rule, two depths. Compare at one depth.
7. **Round-trip renderer** - render a tree back to English from the operation registry and diff it
   against the printed source; disagreement becomes a review finding. Generation is deterministic
   even where parsing is not, so this is the reliability check the pipeline currently has no form of.
8. **Sibling subexpression recovery (CSE)** - 2441 line 25's `UNRESOLVED` block is `MIN(line 20, line
   21)`, sitting in the sibling branch. Hashing subtrees recovers deterministically what a human gets
   by reading across. Same machinery as item 3; do them together or not at all.
9. **Construction drift detection** - reviews call out new punctuation and usage as a ranked finding
   with system-filed evidence, against the versioned inventory S68 produces.
10. **Column and grid recovery**; **phrase obligations**; **S53 approval gate**; **known-red cleanup**.

**STANDING FAILURES, honest.** 2441 line 25 wrong for the **eighth** consecutive run - now
`LOOKUP_TABLE arguments must be named leaf operands with a role`, after one repair. 6251 lines 13 and
20 **no longer fail closed**; both repair to a cross-document reference (`max(form_1040_2025 line 4,
0)` and `max(form_1040_nr_2025 line 15, 0)`). That is a status change, not a win: the references
resolve now, and whether they resolve to the RIGHT line is unreviewed.

## Current round

**M20-S94 SPECCED BY ARCHITECT (2026-08-10), JOHN'S IDEA. RERUN ONLY THE BROKEN ROWS.**
**REAL-PROJECT ROUND** - full-suite floor applies.

**WHY, and the second reason matters more than the first.** The wide run is 410 anchors, $0.2574,
~35 minutes, and only ~54 rows fail - so a broken-only pass is about **$0.03 and 4 minutes**.
**The bigger win is stability: re-asking rows that already work is what makes the report drift.**
`form_2441_2025` `19`/`21`/`25` have flipped in both directions across six runs and **the Architect
misread that churn as signal twice.** Leave healthy rows alone and a changed number MEANS something.

**THE INTERFACE.** `--process all|broken`, **DEFAULT `all`** (John). With `broken`, take the prior
run directory and re-derive only rows whose recorded status is NOT `derived` or `repaired`.

**THE TWO THINGS IT MUST GET RIGHT.**
1. **MERGE, do not report the subset.** Carry the prior run's successful rows into the new report so
   coverage stays against **all 410 printed anchors**. A report of "40 of 54" is a false alarm.
   `pilot/run_report.py` must read a merged run unchanged.
2. **The default stays `all`, and S93 is exactly why.** That round changed a VALIDATOR, so rows that
   passed the day before now fail. **A broken-only pass would never have looked at them.**
   **Broken-only is for iterating on a fix; process-all is what a round is accepted on.**

**RECORD WHICH MODE PRODUCED THE REPORT** in the run output, so nobody compares a merged run against
a full one without knowing.

**OUT OF SCOPE: skipping human-VERIFIED cells.** That is stronger and separate - it must read the
review ledger, not a prior run's status, because re-deriving an approved cell could silently replace
an approved answer. **Queue it; do not fold it in here.**

**THE FLOOR.** A `broken` pass over the S93 run reproduces the same totals as a full run, minus the
rows it legitimately fixed. **Prove it on a real run dir, not a fixture.** Verify with
`pilot/run_report.py`.

**IMMEDIATE USE, so this pays for itself the day it lands:** S93's floor is still unproven because
the stored run carries stub ids minted by the OLD builder. **A broken-only pass over
`C:\tmp\m20_s93\run` is how we finish S93 for four minutes instead of thirty-five.**


## Queued (ONE LINE each - do not spec ahead)

**JOHN'S PRIORITY, 2026-08-10: get the CORE documents processing reliably.** Ordered for that.
**Every item below is a PIPELINE change - none of them is a per-cell human correction.**

1. **`column` ON AN OPERAND.** **BLOCKS the candidate writer on the wide corpus today**
   (`line "2a, column (l)"` is not a canonical address). The graph ALREADY addresses columns -
   `form_8949_2025_part_i_line_1_column_d`, `form_2441_2025_part_ii_line_3_column_d` - only the
   derivation operand cannot say it. **Plumbing, not new capability.**
2. **WORKSHEETS AS DOCUMENTS - NEXT ROUND, spec below is ready to promote** (John's ruling,
   AGENTS.md). Clears the **9 rows that misread a worksheet's steps as their own** AND the
   phrase-line references (1040 `6b`, Sch A `5e`).
   **Shape:** find each box by the printed telltale **"Keep for Your Records"** (23 hits, 2 are
   "Continued" pages, so ~21 boxes; **it is a FLOOR - the Credit Limit Worksheet lacks it**); hand
   the AI the text from the title and let it say where the worksheet ENDS. **Do not restore
   end-anchoring** - that is what made the current harvester a one-worksheet tool, and John already
   ruled extent is AI-harvested. **The reusable cue the model itself gave: a worksheet's LAST step
   names where its answer goes** ("Also enter this amount on Form 2441, line 10").
   **Proven 6 for 6** (`scratchpad/wsend.py`): Credit Limit 3 steps (verified against the source),
   6251 Exemption 6, Schedule D Tax 47, Simplified Method 11, 28% Rate Gain 15, Social Security
   Benefits 18. **Only Credit Limit is source-verified - check the rest against the PDFs.**
   **Floor:** each harvested worksheet is a document with addressable lines; 1040 `6b` resolves to
   a real worksheet line; the 9 misread rows stop misreading. **Watch 6251 `5`** - the Exemption
   Worksheet would replace a lookup table that already derives correctly.
   **Existing pieces: `harvest-worksheet` (title-selected, writes to `_drafts`), and QDCGT already
   modelled with 39 nodes as the reference shape.**
3. **STUBS FOR OUT-OF-CORPUS FORMS, and fix the `Form(s) X` alias.** 1040 `25c` hard-fails because
   the evidence says "Form(s) W-2G" and the matcher builds `form w2g`. Same "(s)" quirk that spared
   1040 `1a` from the reference guard.
4. **A LEAF MEANING "SUPPLIED HERE".** The only genuinely NEW vocabulary; needs the enum gate.
   Blocks 2441 `5`, where `REQUIRE_INPUT` is legal as a whole rule but not as a lookup branch.
5. **RERUN ONLY THE BROKEN ROWS** (John, 2026-08-10). `--process broken|all`, **default `all`**.
   **~10x win, measured:** the wide run is 410 anchors, $0.2512, ~35 min; only ~54 rows fail, so a
   broken-only pass is roughly $0.03 and 4 minutes. **The bigger benefit is stability** - re-running
   healthy rows is what produces the 2441 `19`/`21`/`25` churn the Architect has twice misread as
   signal; leave them alone and a changed number MEANS something.
   **MUST MERGE with the prior run, not report the subset** - otherwise coverage reads 40 of 54 and
   looks catastrophic; totals stay against all 410 printed anchors.
   **John's default is right and S93 is why:** a round that changes a VALIDATOR makes yesterday's
   passing rows fail, and broken-only would hide exactly that. **Broken-only is for iterating on a
   fix; process-all is what a round is accepted on.**
   **"Skip VERIFIED" is a separate, later step** - re-deriving a human-approved cell could silently
   replace an approved answer, so it must read the review ledger, not a prior run's status.
6. **Repair calls that return an unchanged payload** must be detected and not spent (2441 `5`).
7. **`CASE` / alternation** - still HELD; revisit with the wide-run evidence.
8. **"Report issue" from a reviewer corrective** (John, 2026-08-10) - optional and **never hidden**;
   emit a ready-to-paste GitHub body, no network and no auth to maintain. **Cluster by failure kind
   and answer shape, not by form**, so 50 reports of one cause collapse into one issue. Derivation
   runs on BLANK forms so the payload carries no filer data; **the reviewer's own comment is the one
   field needing a preview before sending.** Product work - after the core set is reliable.
9. **Housekeeping:** `pilot/context_arms.py` still scores `REQUIRE_INPUT` as a recovered formula;
   run-together instruction headings (`**Line 2dDepletion**`); artifact-pinned test counts measured
   against untracked `.cache/raw`; `form_8949_2025` needs table-form treatment (4 anchors, 0
   admitted); 2441 `19`/`21`/`25` are a KNOWN-UNSTABLE set - do not read them as signal.

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

**ONE RED IS OURS, and S64's evidence mislabelled it.**
`tests/test_m20_s31.py::test_all_prompt_templates_render_with_representative_values` fails with
`ValueError: prompt has unsupported placeholder: operation_documentation`. The Worker recorded it as
an "existing prompt fixture omission"; it is not existing. **It PASSES at `origin/main` (26eead7)
and fails on our tree**, because S66 added `<<operation_documentation>>` to `prompts/derive_cells.md`
without adding the token to the test's representative values. The pipeline path itself is fine - the
canary derived 65 rows through that same template - so this is the pinned vocabulary contract test
going red, not a product defect. Fix is the fixture, not the prompt.

**The other 20 are pre-existing**, established by A/B against `origin/main` in a worktree with the
local `.cache`, `graph/2025/_drafts`, and `build/` junctioned in so the comparison is fair: 3 fail
identically on a bare checkout, 5 more fail identically once the artifacts are present, and all 11
`tests/e2e/*_m15` fail identically with an empty review queue (0 documents, the known stale-queue
condition). `tests/test_review_scope_migration_m15.py` is UNCOMPARABLE - it skips at baseline for
missing 2441 extension artifacts and fails on ours, so it is untriaged, not cleared.

**Full suite on our tree: 21 failed, 841 passed, 8 skipped, 1 xfailed.**

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

## Open for Architect

**S92 [DONE] WORKER STATUS (2026-08-09), commit `6833dad`:** Implemented `pilot/row_bench.py` and
`pilot/test_row_bench.py`. Replay is read-only and uses the production `_render_cell_prompt`,
`_apply_payload`, and `validate_cell_output`; live mode delegates to production `derive_cells`
while capturing its prompts and responses. No production code, prompt, validator, graph, or
review state changed.

RAN: `.venv\Scripts\python.exe -m pytest pilot\test_row_bench.py -q` -> **3 passed, 1 warning**.
RAN: `.venv\Scripts\python.exe tools\check_ascii.py` -> **ASCII check OK**.
RAN: `git diff --check` -> **clean**.
RAN: `.venv\Scripts\python.exe pilot\row_bench.py form_1040_2025 --line 3b --line 5a --line 5b --line 12e --line 25c --line 27a --line 35a --line 38 --run-dir C:\tmp\m20_s91b\run` -> **exit 0**.
RAN: `.venv\Scripts\python.exe pilot\row_bench.py form_2441_2025 --line 5 --line 8 --line 10 --run-dir C:\tmp\m20_s91b\run` -> **exit 0**.
RAN: `.venv\Scripts\python.exe pilot\row_bench.py form_6251_2025 --line 1a --line 2h --line 8 --line 2 --run-dir C:\tmp\m20_s91b\run` -> **exit 0**.

**THE 15-ROW GROUPING IS CONFIRMED WITH ONE CORRECTION.** The embedded-worksheet validator
pattern is 1040 `5a`, `5b`, `27a`, and 2441 `10`; 1040 line `10` is derived and is not in the
15-row error set. The 1040 rows carry 11,424 and 43,748 character instruction packets that
embed Simplified Method and EIC worksheets. 2441 line 10 carries the Credit Limit Worksheet;
its internal line 3 says subtract line 2 from line 1, which the parent-row validator reads as
the row rule. This is the same validator scope defect, with a different worksheet.

The remaining groups match the spec: quote-not-verbatim on 1040 `3b`, `35a`; expression grammar
payload rejection on 1040 `12e`, 2441 `5`; unknown external document on 1040 `25c`, 6251 `8`;
source-side no-call evidence gaps on 2441 `8`, 6251 `1a`; line-format mismatch on 6251 `2h`,
`2`; and self-reference on 1040 `38`. Replay confirms first and repair payloads are rejected
under the same production validator for every provider-reached row.

Two source-backed qualifications are recorded. For 6251 `2`, printed `1z` is present in the
1040 field inventory, address map, and binding, but is absent from the promoted semantic node
inventory used by `build_reference_inventory`; the hard failure is therefore a graph inventory
shape gap, not a missing form control. For 6251 `8`, the acquired 6251 instructions do name
Form 1116, but the row's joined instruction text is empty, so the current payload is not
source-backed in the packet the model received and the hard failure is correct until that join
is fixed.

The 15 replay screens were produced from `C:\tmp\m20_s91b\run`; no provider leg was run. **ANSWERED - THREE DISTINCT FIXES, AND NONE OF THEM IN PRODUCTION YET.** Both of your
qualifications are Architect-verified: the reference inventory holds **42** printed lines for 1040
and `1z` is **not** among them (no node id contains it), and 6251 `2` and `8` both have **zero**
instruction characters. Your correction to my grouping is accepted - the worksheet cluster is 1040
`5a`, `5b`, `27a` and 2441 `10`; **1040 `10` was my error, it derives.**

**1. VALIDATOR SCOPE is the big one (4 rows), but "scope it to the row's own instruction section"
is not the rule** - the worksheet IS inside the row's own section. The rule is: **line-number
references inside an embedded worksheet block are the WORKSHEET's, not the parent row's.** The
blocks are titled ("Simplified Method Worksheet", "Credit Limit Worksheet"), so the boundary is
findable.
**2. INSTRUCTION JOINS** - 6251 `2` and `8` receive an empty packet. Upstream, separate.
**3. PROMOTED-NODE INVENTORY** - `1z` exists as a form line but not as a node the validator will
accept. Same family as the stub work.

**PROVE EACH ONE IN THE HARNESS FIRST. NO PRODUCTION CHANGE UNTIL A FIX IS DEMONSTRATED THERE.**
That is John's standing direction for this effort and replay mode makes it free: **extend
`row_bench.py` to take an experimental validator variant and report which of the 15 rows flip to
accepted.** A fix that cannot move a row in replay does not belong in `tax_graph/`.
model-quality change.

**S91b WORKER STATUS (2026-08-09):** Implemented the provider-free strict-substring extension to
the printed-bracket clause selector. `clean_form_face_text_with_extent` keeps the near-empty-face
rule and now also selects the bracket when the normalized fallback face is a strict substring of
the bracket face. `clause_extent` records `selection_reason` as `weak_fallback`,
`fallback_strict_substring`, or `fallback` alongside both candidate faces and the disagreement
direction. The real 2025 corpus selects **68** rows: the prior **42** weak-face repairs plus **26**
strict-substring repairs. The disagreement split remains **44 bracket-longer / 27 fallback-longer**.

RAN: `$env:PYTEST_DEBUG_TEMPROOT=(Resolve-Path .test_tmp_s91b).Path; .venv\Scripts\python.exe -m pytest tests\test_m20_s91.py tests\test_cell_caption_m20.py tests\test_derive_cells_m20.py tests\test_outline_span_resolution_m20.py tests\test_structure_m20.py tests\test_extract_outline_m4.py tests\test_extract_m16.py tests\test_acquire_citation_check.py tests\test_m20_s54.py tests\test_m20_s51.py -q` -> **166 passed, 1 warning**.
RAN: `$env:PYTEST_DEBUG_TEMPROOT=(Resolve-Path .test_tmp_s91b).Path; .venv\Scripts\python.exe -m pytest tests\test_m20_s91.py tests\test_derive_cells_m20.py -q` -> **75 passed, 1 warning**.
RAN: `.venv\Scripts\python.exe tools\check_ascii.py` -> **ASCII check OK**.
RAN: `git diff --check` -> **clean**.
NOT RUN: full suite; it exceeds the 600-second Worker command cap, and the latest accepted baseline
is already recorded in BALL. NOT RUN: provider leg; S91b is explicitly provider-free.

**S91 WORKER STATUS (2026-08-09):** Implemented the provider-free printed-bracket clause extent
selection. `_bracketed_source_text` uses neighboring indexed printed anchors, accepts a full anchor
or its trailing letter as the start, strips dot-leader-only rows, and ends at the full anchor. The
cell layer keeps the existing geometry cleanup as fallback, selects the bracket only for a weak
projected face when it is not shorter, and records both faces, selection method, and disagreement
direction in `clause_extent` metadata. The real 2025 corpus selected **42** repairs; the measured
disagreement split is **44 bracket-longer / 27 fallback-longer**. The cited good-face cases remain
on fallback where the bracket would over-capture.

RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp_codex'; .venv\Scripts\python.exe -m pytest tests\test_m20_s91.py -q` -> **3 passed, 1 warning**.
RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp_codex'; .venv\Scripts\python.exe -m pytest tests\test_outline_span_resolution_m20.py tests\test_structure_m20.py tests\test_derive_cells_m20.py -q` -> **112 passed, 1 warning**.
RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp_codex'; .venv\Scripts\python.exe -m pytest tests\test_extract_outline_m4.py tests\test_extract_m16.py tests\test_acquire_citation_check.py -q` -> **34 passed, 1 warning**.
RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp_codex'; .venv\Scripts\python.exe -m pytest tests\test_m20_s90b.py tests\test_m20_s90c.py tests\test_m20_s54.py tests\test_m20_s51.py -q` -> **26 passed, 1 warning**.
RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp_codex'; .venv\Scripts\python.exe -m pytest tests\test_m20_s91.py tests\test_cell_caption_m20.py tests\test_m20_s71.py -q -k "not real_candidate_node_labels_use_clean_text"` -> **12 passed, 1 deselected, 1 warning**.
RAN: `.venv\Scripts\python.exe tools\check_ascii.py` -> **ASCII check OK**.

KNOWN RED, NOT S91: the declared combined consumer command produced **132 passed, 1 failed** at
`tests\test_m20_s71.py::test_real_candidate_node_labels_use_clean_text`. With an external writable
pytest temp root, the same file produced **5 passed, 1 failed**; the failure is the existing S90c
candidate-writer integrity red: `form_1040_2025_root_line_4` is an unresolved operand. It is the
named full-suite baseline red in BALL, not a clause-extent failure.

NOT RUN: full suite; it exceeds the 600-second Worker command cap, and the latest accepted baseline
is already recorded in BALL. NOT RUN: provider leg; S91 is explicitly provider-free.

**S90c WORKER STATUS (2026-08-09):** The implementation is complete provider-free, and the
stale real S90c report now regenerates successfully. The candidate writer accepts a shared node id
when its identity payload agrees across documents (citation provenance may differ), rejects a real
payload collision, and synthesizes canonical document/line stubs for valid edge endpoints missing
from a partial candidate. The document-only external-reference predicate now lets the model obtain
the line from the external document while requiring source evidence to name the document.
Instructions booklets remain named `instructions_document_operand` findings and never mint stubs.

RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp_codex'; .venv\Scripts\python.exe -m pytest tests\test_m20_s90c.py tests\test_m20_s90b.py tests\test_candidate_regeneration_m20.py tests\test_derive_cells_m20.py tests\test_m20_s31.py tests\test_review_table_m20.py tests\test_run_summary_m20.py -q` -> **108 passed, 1 warning**.
RAN: `.venv\Scripts\python.exe tools\check_ascii.py` -> **ASCII check OK**.
RAN: `.venv\Scripts\python.exe -m tax_graph.cli regenerate-candidate --run-dir C:\tmp\m20_s90c\run --output-dir C:\Users\devbox\.codex\visualizations\2026\08\09\019fe5ae-61f8-7242-903c-df2b6142f862\m20_s90c_candidate_v2 --expected-document form_1040_2025 --expected-document form_2441_2025 --expected-document form_6251_2025` -> **exit 0**; real candidate has `graph_integrity: ok`, 230 unique semantic nodes, 315 edges, 228 operands, 22 unresolved stub documents, and zero dangling node ids.
RAN: `.venv\Scripts\python.exe pilot\run_report.py C:\tmp\m20_s90c\run` -> **127 of 157 printed anchors (80.9%), cost $0.1008**; this is the pre-change report and is not evidence of the document-only predicate.
RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp_codex'; .venv\Scripts\python.exe -m pytest tests\test_graph_validator.py -q` -> **3 passed, 11 failed**; all 11 fail before validator logic while copying protected `graph/2025/_drafts` directories with `WinError 5`.
NOT RUN: current-code live provider leg: `.venv\Scripts\python.exe experiments\derive_cells_s25.py --year 2025 --output-dir C:\Users\devbox\.codex\visualizations\2026\08\09\019fe5ae-61f8-7242-903c-df2b6142f862\run_s90c_current --document form_1040_2025 --document form_2441_2025 --document form_6251_2025` -> sandboxed command timed out at 600 seconds with no output; the escalated retry was rejected because it would send real tax-document contents to an unspecified external provider without explicit user authorization.
NOT RUN: full suite; it exceeds the Worker command cap and the graph-validator copy ACL family remains environment-red.

**S90b PREREQUISITE (2026-08-09):** Committed at `ad53a97`; its evidence-backed
out-of-inventory operands now produce the non-fatal `unresolved_external_reference` warning,
retain the structured `unresolved_external_nodes` record, remain `derived` without consuming a
repair, and are copied into candidate-row findings for the review surface. Unsourced unknown
documents remain hard `operand_document_not_found` failures. W-2, every 1099 suffix, and K-1 face
references are excluded from the REQUIRE_INPUT guard as filer-supplied information returns.

**ANSWERED - THAT GUARD IS SUPERSEDED. Rewrite it; the implementation is right.** You were right
to stop. `test_named_unseen_form_reference_mints_unresolved_external_node` is an **S74** guard, not
an S90 one, and its fixture is the exact case S90b redefines: the face reads "Attach Form 4684 and
enter the amount from line 18 of that form", so the reference is evidence-backed and Form 4684 is
simply outside the corpus. **Failing that row closed is the behaviour that cost 27 rows.**

**Replacement assertions.** Status `derived`, not `error`. **Exactly ONE provider call** - the
repair must not be consumed. `unresolved_external_reference` present in
`validator_warnings_by_kind`, `operand_document_not_found` ABSENT, `gapped == 0`. **Keep the
`unresolved_external_nodes` payload assertion byte-for-byte** - that record is what S74 actually
bought and S90b does not change it.

**Add the complementary guard in the same file, so the pair is visible:** an operand naming a
document the row's own evidence does NOT name stays a hard `operand_document_not_found` with
status `error`. That is the line `_legitimate_external_reference` draws, and reusing that existing
predicate rather than inventing a second one was the right call.

**The information-return rule is verified on real rows.** Architect ran it against the S89 corpus:
flagged rows drop **12 -> 11**, `form_6251_2025` line 2j is correctly no longer flagged, and
synthetic faces "from Form W-2, box 1", "from Form(s) W-2", "from Form 1099-R, box 1", "from Form
1099-DIV" and the K-1 face all read as inputs while "from Form 8863, line 8" still flags. **By
family, not by spelling, as specced.**

**The live leg was not run by the Worker.** S90b acceptance still rested on it: coverage back to at least
139 of 157, `form_6251_2025` line 13 back to `max(qdcgt line 4, 0)`, and the 64 plus 13 intact.

RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp_s90b'; .venv\Scripts\python.exe -m pytest tests/test_m20_s90b.py tests/test_candidate_regeneration_m20.py -q` -> 9 passed, 1 warning.
RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp_s90b'; .venv\Scripts\python.exe -m pytest tests/test_derive_cells_m20.py -q` -> 71 passed, 1 failed; the sole failure is the pre-S90b guard named above.
RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp_s90b'; .venv\Scripts\python.exe -m pytest tests/test_m20_s31.py tests/test_review_table_m20.py tests/test_run_summary_m20.py -q` -> 20 passed, 1 warning.
RAN: `.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK.
NOT RUN: live provider leg; requires the network-capable acceptance context.

**S90b acceptance remains a network-capable Architect check:** verify that the 12 S89 input rows
are repaired into cross-document operands or named unresolved-reference findings, with no silent
`REQUIRE_INPUT` result. S90c adds the candidate-graph stub and lifecycle gate above.

**S89 is accepted; its items are cleared. The record is `d2a077f` and the BALL block.**

**S85 Part C is open for the Architect:** the fresh three-document run used the pinned
`openai/gpt-5.6-luna` model but all 34 attempted rows failed with
`LlmUnavailable: OpenRouter request failed: Connection error.` The regenerated candidate is
empty of rules, so Form 6251 line 18 execution and the real-data comparator/checkbox proof remain
unverified. Rerun Part C in a network-capable context; no authorization escalation is needed. The
Worker also could not create or write under `C:\tmp` in this sandbox, so the mandated panel path
needs verification there. S86 remains after the full-suite result.

**S86 worker verification is open for Architect:** the impacted worker slice is 139 passed with 9
environment failures, all `WinError 5` while `test_examples_m8.py` and
`test_nversion_m8.py` copy ACL-protected `graph/2025/_drafts/` directories. The model accessor,
attribution, doctor, extraction, re-derivation, batch, prompt experiment, extension, workbench, and
offline example slices passed. Run the full suite against the known 20 baseline and verify the
provider leg in a network-capable context; the Worker did not run either under the 600-second cap.

The three items `doctor` flagged STALE at 73 commits on
2026-08-05 are closed: the **S36 denominator decision** (moot - S51 replaced the denominator
with 121 of 478 anchors and a named reason per skip); the **two scoping calls** (worksheets
closed by the S59 nomination chain; the filing-status constant answered by measurement -
`schedule_1a_2025` line 17 and `form_6251_2025` line 18 both emit correct role-keyed lookups);
and **"what is next"** (John chose option (b), structure and association, on 2026-08-05).

**Open for JOHN, not blocking:** during bootstrap, "every cell receives meaningful human
approval before use" and "a human does not read every new cell" cannot both hold. The pipeline
can eliminate RE-review - approve once against stable semantics, fingerprint the clauses, carry
the verdict while nothing changes - but not first review. That decision shapes S53.

## From Architect

**One spec at a time. The next round is specced when it is picked up.**

## History

Everything before M20-S23, and all per-round Worker narration, lives in git history. This file was
pruned from 7,520 lines on 2026-08-02 at S28 acceptance; `git show 12240ef:plans/AGENT_HANDOFF.md`
is the last unpruned copy. Earlier prune: 2026-07-23, from 1,198 lines, for public-repo prep.
Durable rulings were carried forward into **Binding rulings** above rather than deleted; A9
rulings remain pinned in `plans/PHASE_M15.md`; the defect ledger (D6, D9, D10, D12, D13, D14) is
in `AGENTS.md`.
