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

**BALL: WORKER - M20-S89 (DELETE THE SELECTOR GATE). REAL-PROJECT ROUND.**
**THE GUARD BLOCK IS ANSWERED (2026-08-08); the ruling is at the end of the S89 spec.** Both
guards are superseded and rewritten, the compatibility shim is rejected in favour of one accessor,
and the provider floor measurement is mine to run, not yours.
**THE LEGACY-TELEMETRY QUESTION IS ANSWERED TOO (see Open for Architect): assert 13, my 12 was
stale.** Remaining before this round can be accepted: the root-header guard, the full suite, and
then hand back for the provider floor run.
**S88 ACCEPTED at `49ff88a`.** The harness was correct; the Architect ran the three arms, since the
Worker sandbox still cannot reach the provider or write `C:	mp`.

**THE ANSWER: 27 of 32 missed formulas recover with TODAY'S CONTEXT, for about nine cents.** All
three arms recovered the same 27. Arm A - the line-anchored section we already build - had zero
regressions and zero wrong-line quotes. Widening lost rows and provenance. **Ship arm A; delete the
gate.**

**COVERAGE: ~64% -> ~90% EXPECTED.** Report it against all printed anchors. The
derived-over-attempted denominator is exactly what hid 32 formulas.

**TWO ARCHITECT CLAIMS WERE WRONG THIS ROUND AND THE DATA CORRECTED BOTH.** Buffers were argued
safe because a model treats overlap as context - wrong-line quotes went **0 -> 2 -> 6** as the
window widened. And a wider region was expected to help 6251 most, since arm C reached 34 anchors
versus 24; it recovered no more and broke five rows.

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

**M20-S89 SPECCED BY ARCHITECT (2026-08-08). DELETE THE SELECTOR GATE.**
**REAL-PROJECT ROUND** - touches `tax_graph/`, so the **full-suite floor applies.**

**S88 SETTLED IT WITH NUMBERS. ARM A WON OUTRIGHT.** Same 157 anchors, three context arms, selector
bypassed, live provider:

| arm | recovered of 32 | regressions | wrong-line quotes | cost |
| --- | --- | --- | --- | --- |
| **A - line section only (today's context)** | **27** | **0** | **0** | $0.095 |
| B - section plus 8-line buffers | 27 | 1 | 2 | $0.072 |
| C - raw 12-line region, no sectioner | 27 | 5 | 6, plus 9 unattributable | $0.074 |

**THE CONTEXT WAS NEVER THE PROBLEM; THE GATE WAS.** Every arm recovered the same 27. Widening
bought nothing and cost progressively more.

**AN ARCHITECT CLAIM WAS MEASURABLY WRONG, AND THE MEASUREMENT IS WHY WE KNOW.** The spec argued
buffers were safe because a model, unlike a parser, treats overlap as context rather than
contamination. **False: wrong-line quotes went 0 -> 2 -> 6 as the window widened**, and arm C also
produced 9 quotes whose provenance could not be established. **Do not widen the context. Do not
revisit buffers without new evidence.**

**THE CHANGE.**
1. **Every printed anchor goes to derivation.** `selector_no_formula_cue` stops existing as a skip.
   The keyword cue lists at `outline_pipeline.py:51` stop gating derivation. **Delete the gate; do
   not widen the cue list** - a longer substring list is the same defect.
2. **"This line is an input" becomes a FIRST-CLASS MODEL-STATED OUTCOME**, carrying its evidence,
   not a silent keyword drop and not an error. **A skip that reports as success is the exact defect
   that hid 32 formulas for months.**
3. **CONTEXT ASSEMBLY IS UNCHANGED.** Arm A is what ships. No buffers, no region fallback.
4. **STRUCTURAL SKIPS STAY SKIPS** - the 7 `structure_duplicate_anchor`, `structure_header_anchor`
   and `structure_non_cell_anchor` rows are extraction artifacts, not formula questions.
5. **The review surface must distinguish a MODEL-ASSERTED input line from a STRUCTURAL skip.** They
   are different claims with different trust: one is a judgment that can be wrong, the other is a
   fact about the printed page.

**THE FLOOR, and it is a floor not a target.**
- **The 63 rows that derive or repair today MUST NOT regress.** Report any that do, by line.
- **The 27 recovered in S88 must derive.** They are named in `pilot/context_arms.py`
  `KNOWN_MISSED_FORMULAS`.
- **Expected real coverage: ~64% -> ~90%** (63 of ~99 to ~90 of ~99). **Report the coverage number
  against ALL printed anchors, not against attempted** - the attempted denominator is what hid this.
- **Cost rises from about $0.04 to about $0.09 per run.** That is the whole price of the gate.

**OUT OF SCOPE.** The 5 that no arm recovered - 1040 `27a`, `38`; 6251 `1a`, `10`, `25` - **errored
rather than skipped**, so the model saw them and failed. That is derivation, not routing. **Queue
it; do not widen this round.** Also queued and untouched: the run-together instruction headings
(`**Line 2dDepletion**`), which cost 6251 ten instruction sections.

**THE RISK TO WATCH, stated honestly.** 157 anchors instead of 67 means more rows that can error,
and an "input line" answer must earn the same trust as an expression. **Spot-check a sample of
model-asserted input lines against the printed form** and report the rate, rather than assuming the
new outcome is reliable because the recovery number looks good.

**ARCHITECT RULING ON THE S89 GUARD CONTRACT (2026-08-08). Asked and answered; the round is not
blocked.** The Worker measured the slice at **1040 58 admitted / 1 structural; 2441 32 / 3;
6251 60 / 3**, route denominator 67 -> 150, seven structural rows preserved. That is the intended
shape.

**1. S89 SUPERSEDES BOTH GUARDS. Rewrite them; do not delete them.** A test asserting that a
no-cue anchor is skipped is asserting the defect this round exists to remove, and it is exactly
the test that let 32 formulas hide. The replacement assertions:

- `tests/test_m20_s51.py::test_denominator_reports_legacy_and_widened_selector_decisions` -
  anchor `9` is now routed. Assert `by_anchor["9"]["skip_reason"] == ""`,
  `derivation_admitted is True`, and `legacy_selector_admits is False`; report totals become
  `admitted == 3`, `skipped == 0`, `legacy_admitted == 0`. **The cue telemetry stays asserted** -
  that is the part of this test still worth having.
- `tests/test_m20_s51.py::test_form_2441_denominator_names_the_newly_visible_rows` - assert the
  measured `admitted == 32`, `skipped == 3`, `legacy_admitted == 12`,
  `skipped_by_reason` containing only `structure_*` keys, and anchor `1` carrying
  `skip_reason == ""` with `legacy_selector_admits is False`. Assert what you measure, not what
  this ruling arithmetic-ed.
- `tests/test_m20_s71.py::test_selector_skips_provider_but_retains_clean_cell_text` - rename to
  name the structural case, set the fixture metadata to a `structure_non_cell_anchor` reason, and
  keep every assertion (skipped, clean text, zero provider calls, `attempted == 0`).
  **Then add the inverse guard in the same file: a row with no formula cue and no structural
  reason DOES reach the provider and IS counted in `attempted`.** That pair is the contract.

**2. NO. The old selector counts do NOT survive as a compatibility projection, and the slice's
current shim is the thing I am rejecting.** It keeps `selector_admitted`, `selector_cue` and
`selector_skip_reason` next to new `structural_skip_reason` and `legacy_selector_*`, and then
`derive_cells` improvises `structural_skip_reason or (selector_skip_reason if it startswith
"structure_")`. **That is one accessor's job done by every consumer, which is the recurring defect
we already ruled on.** Worse, `selector_admitted` was redefined in place: same key, new meaning,
so `test_outline_span_resolution_m20.py:245`, `test_derive_cells_m20.py:1510` and
`pilot/review_panel.py` all still read it and now silently get a different answer.

**The shape I want:** one accessor decides routing for a row - a single function returning the
structural skip reason, where absence is a typed empty result and empty means "route it". Delete
`selector_admitted` and `selector_skip_reason` from cell metadata rather than redefining them; the
cue survives only inside `build_derivation_denominator` under `legacy_selector_*`, explicitly
labelled measurement. Drop the redefined `selector_admits` from the report and let
`derivation_admitted` be the only routing field. **No `.get(a, .get(b))` chains and no
`startswith("structure_")` sniffing anywhere** - the reason is present or it is not. Put the
invariant test at the accessor.

**3. `model_stated_input` is right, and the machinery already existed** - `REQUIRE_INPUT` is a
registered operation and `prompts/derive_cells.md` already instructs it. Labelling the outcome is
the whole change; keep it that small.

**4. `pilot/review_panel.py` still categorizes holes as `selector_no_formula_cue`, which now has
no producer.** That is spec point 5 and it stays in this round, but do it AFTER the run, against
real rows: a model-asserted input is an outcome, not a hole, and only `structure_*` rows remain
holes.

**ORDER OF WORK.** Land the accessor cleanup and the rewritten guards, then the full suite
(real-project floor), then report. **Do not attempt the provider run** - your sandbox cannot reach
it, and I will run the floor measurement myself as I did for S88: the 63 non-regressing rows, the
27 recovered, coverage against all 157 printed anchors, cost, and the spot-check rate for
model-asserted input lines.

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

**S89 WORKER STATUS (2026-08-08):** The selector gate cleanup is implemented in the working
tree. `get_structural_skip_reason` is the sole row routing accessor; cell metadata no longer
contains `selector_admitted`, `selector_cue`, or `selector_skip_reason`; denominator telemetry is
under `legacy_selector_*`; no-cue rows route and record `model_stated_input`; root header duplicate
handling preserves the measured 58/1, 32/3, and 60/3 document slices. Pilot context metadata
keeps historical selector data only under `pilot_original_legacy_*` and does not reintroduce it
as routing. The pilot labels retired selector holes as `historical_selector` and tells the reviewer
to regenerate; current `model_stated_input` rows are outcomes, not holes.

**ANSWERED - ASSERT 13. The `12` was mine to get wrong and I told you not to copy it.** The ruling
said assert what you measure; 12 came from the old S51 test and I echoed it without re-measuring.
**S89 did not move this number and could not have:** the diff leaves `_formula_selector_decision`
and the anchor list untouched, and `legacy_admitted` reads only `before`, which no part of the
slice touches. **Architect verified independently** on the current artifact: 35 anchors, 13 legacy
admitted, 32 admitted, 3 structural (2 duplicate, 1 header). All 13 are ordinary form lines with
genuine cues - 5 `amount_from_line`, 9a `multiply_line`, 9c/28 `add_line`, 11/17/31
`smaller_of_line`, 15 `combine_line`, 19 `amount_from_line`, 23/25/26/29 `subtract_line`.
**Take no form-specific subtraction. You were right not to add one.**

**THE REAL FINDING UNDER IT: this guard pins numbers to an UNTRACKED artifact.**
`.cache/raw/2025/form_2441_2025.txt` is not in git; the 13 is measured against whichever local
copy exists. Any such expectation drifts silently when a document is re-acquired or the extractor
changes, and the test reports it as a code regression. **Queued, not this round:** decide whether
artifact-pinned counts get a tracked fixture or stop being asserted.

**ROOT-HEADER GUARD ADDED.** The
`root_header_present` exemption is not cosmetic - it fires on `form_2441_2025` anchor `21` and
`form_6251_2025` anchor `32`, rescuing two real cells that the form header's repeated sequence
number would otherwise mark `structure_duplicate_anchor`. The named parameterized test
`test_root_header_duplicate_does_not_consume_real_cell` now guards both anchors.

**S89 TEST EVIDENCE:** RAN
`$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp2'; .venv\Scripts\python.exe -m pytest tests\test_m20_s51.py -q`
-> **6 passed in 1.64s**. RAN
`$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp2'; .venv\Scripts\python.exe -m pytest tests\test_m20_s51.py tests\test_m20_s71.py tests\test_derive_cells_m20.py tests\test_candidate_regeneration_m20.py tests\test_outline_span_resolution_m20.py pilot\test_context_arms.py pilot\test_review_panel.py pilot\constructions\test_measure.py -q`
-> **112 passed, 1 failed in 25.93s**; the single failure is the known environment boundary in
`test_real_candidate_node_labels_use_clean_text`, which writes a candidate under the repository
temp root and is correctly rejected by the external-output guard. The same command with the
external `C:\Users\devbox\AppData\Local\Temp\tgpt` root was **100 passed, 13 environment errors**
because that root is ACL-poisoned for this account. RAN
`.venv\Scripts\python.exe tools\check_ascii.py` -> **ASCII check OK**. The full suite was NOT RUN:
the last measured full suite was 0:57:21, beyond the 600-second Worker command cap.

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
