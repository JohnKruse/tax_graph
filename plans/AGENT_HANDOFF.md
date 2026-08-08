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

**BALL: WORKER - M20-S87 (KILL THE CONFIG-PATH ROOT CAUSE; AUDIT THE 83 SKIPS).**
**S86 ACCEPTED at `2d27205`, with the regression fixes at `b9cd181`.**

**STAGE-BY-STAGE STATE (Architect read for John, 2026-08-08).** None of the current suite noise is
extraction or derivation.
- **Text and anchors: FIXED**, as John believed - 153/153 rows clean form-face text, 0 of 194 node
  labels carrying raw OCR, anchors 12% -> 1% wrong.
- **Derivation: MEETING THE 98% BAR** - 66 attempted, 58 derived, 5 repaired, 4 errored, and the 4
  fail for stated reasons rather than repairing into something unverifiable.
- **Candidate/graph: working and newly stricter** - 5 of 5 branches carry a comparator.
- **Review surface: working** - Tree over Math, 65 operation rows, holes stating their real reason.
- **Selector: working, UNVERIFIED** - 83 of 157 anchors skipped on one unaudited judgment. **This is
  where the risk is.**
- **M15 review workbench: red, older milestone** - 11 e2e failures on an empty queue, unrelated to
  the extraction pipeline.

**WHAT TODAY BOUGHT, since it does not feel like progress:** a wrong tax number was found and fixed.
`form_6251_2025` line 18 computed the 26% arm when it owed 28%, inverted on every input, because the
comparator was unstored and the engine defaulted to `gt`. It is now derived from the instruction
(`le`), required by schema, named by the validator, and visible in the review as
`line 17 <= threshold`. **John found it by reading a tree and asking how a comparison is shown** -
which is what the review surface is for.

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

**M20-S87 SPECCED BY ARCHITECT (2026-08-08). KILL THE CONFIG-PATH ROOT CAUSE, THEN AUDIT THE SKIPS.**
John, 2026-08-08: *"The errors continue to be a whack a mole exercise. I am not feeling a lot of
progress."* **He is right, and the mole has ONE hole.** Part A closes it. Part B then moves to the
thing that actually carries risk, which is not the test suite.

**S86 IS ACCEPTED at `2d27205` with `b9cd181` on top.** The accessor raises `ModelConfigurationError`
on absence, `configured-llm` is gone from the tree, `seed` reaches the wire with the falsy-zero trap
avoided, `vendor_family` is derived, `doctor` resolves through the accessor, and the exact production
config - Luna, `only: [openai]`, `allow_fallbacks: false`, `require_parameters: true`, seed, strict
structured outputs - returns **HTTP 200 live**.

**S86 also shipped 11 new suite failures; `b9cd181` fixed nine.** Two remain, and they share Part A's
cause. The nine were two mistakes: S86 deleted the improvised `"configured-llm"` placeholder
(correct) AND the documented `micro -> primary` cascade (wrong - it made optional keys required and
would break the shipped example config), and it added `seed` to the client without updating 17 test
doubles.

### PART A - ONE ROOT CAUSE, THREE SYMPTOMS. **THERE ARE TWO FILES NAMED `tax-graph.config.yaml`.**

`tax_graph/config.py:default_config_path` resolves `<root>/tax-graph.config.yaml`. **Nothing reads
`config/tax-graph.config.yaml`**, which is longer, better commented, and looks authoritative. Three
symptoms, each of which looked unrelated until now:
1. **Two wasted provider runs.** The Architect diagnosed and edited the decoy twice, and reported a
   false "the model drifted to gemini at 15x cost" finding from it. The live config had Luna pinned
   all along. That claim is wrong in the `95991c8` commit message.
2. **John's recurring complaint** that model settings will not stick - *"I wanted it to be set in
   the config file, full stop."* A fix applied to the decoy changes nothing.
3. **The last two suite failures.** At least TEN hermetic fixtures do
   `copyfile(root/"config"/"tax-graph.config.example.yaml", root/"config"/"tax-graph.config.yaml")`
   and the loader never reads it - **so those tests have never had a config.** The
   `"configured-llm"` placeholder hid it; removing the placeholder exposed it. **This is exposure,
   not new breakage.**

1. **Point every fixture at the path the loader actually reads.** Expect this to change what config
   those tests see; **that is the point, and the blast radius is why this is its own round.**
2. **DELETE `config/tax-graph.config.yaml`.** It is a stray copy of the example, gitignored, read by
   nothing. **Ask John first - it is his local file.**
3. **MAKE IT UNREPEATABLE.** A guard that fails loudly when a config exists at a path that is not
   loaded. **Without this the third symptom simply waits for a fourth.** A round that only fixes the
   ten fixtures has not fixed anything.
4. **Full suite. Target: the known 20, no more.**

### PART B - AUDIT THE SKIPS. **83 OF 157 ANCHORS ARE SKIPPED ON ONE UNVERIFIED JUDGMENT.**

This is where the real risk is. Today's run: 157 printed anchors, 67 selected, 58 derived, 5
repaired, 4 errored, **90 skipped - 83 of them `selector_no_formula_cue`**. Nobody has ever checked
whether those 83 are genuinely input lines. **A skipped line looks identical to a clean run**, so
over half the corpus rests on an unaudited call that reports as success.

**The selector is a hardcoded substring list** - `_LEGACY_FORMULA_CUES` and `_WIDENED_FORMULA_CUES`
at `tax_graph/extract/outline_pipeline.py:51`, 16 phrases such as `"add line"`, `"subtract line"`,
`"smaller of line"`. **Any formula the IRS phrases differently is skipped silently**, and `"divide"`
appears nowhere in the list.

**DO NOT AUDIT WITH KEYWORD MATCHING.** The Architect screened for `"divide"` and got 14 hits that
were all the word **dividends** - the exact substring bug the selector itself has. **Auditing a
substring bug with substring matching reproduces it.** The audit reads the printed line and its
instruction text and judges.

1. **Classify every one of the 83** - this is pipeline work per the prime directive, not a hand
   audit: for each skipped anchor, decide **input line** (a number the filer copies from a source
   document - a correct and final answer) versus **missed formula** (the line computes from other
   lines), citing the instruction text that decides it.
2. **Report the miss rate with its denominator**, per document. **Lead with the misses, not the
   hits.**
3. **Name the cues that would have caught them.** The deliverable is evidence about the selector,
   not a patched cue list - **do not widen the cue list in this round.** A substring list is the
   defect; a longer one is the same defect.
4. **`form_6251_2025` line 7 is a named candidate**: its printed text is a conditional
   (*"If you reported capital gain distributions directly on Form 1040..."*) and it was skipped.

**EVIDENCE.** Part A: the ten-plus fixtures repointed, the decoy gone, the guard failing on a decoy
you plant deliberately, and a full suite at the known 20. Part B: 83 classified, a miss rate per
document, and the instruction text quoted for every miss.

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
