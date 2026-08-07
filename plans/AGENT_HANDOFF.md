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

**BALL: WORKER - M20-S76 (LIFT THE INSTRUCTION PARSER). REAL-PROJECT ROUND.**
**S75 ACCEPTED at `b2982c6`. S74 implemented at `b153e94` and STILL UNACCEPTED** - its suite was
stopped deliberately so the lift could proceed; ONE full-suite run now gates both rounds.
Active spec is under Current round. **PILOT WORK IS PAUSED**; S76 edits `tax_graph/extract` and
pays the full suite. John's arc, 2026-08-07: **fix column 1, then assess column 2, and column 3
should then fall out.** S76 is the column-1 fix reaching production. Pilot rules still bind when the
pilot resumes.

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
1. **`form_13614_c_2025` yields 0 printed anchors** - a manifest document producing nothing.
2. **Column 3 becomes the agreed notation** - the S69 flow is an edge dump: zero `<svg>`, zero
   diamonds, zero Yes/No arrows across all 157 panels; it renders `zero_floor` and node ids into the
   human column and re-narrates upstream lines. Must implement `docs/review-notation.md` rules 1-8,
   with phrasing read from the operation registry. Was specced at `41fffff`; recover with `git show`.
3. **LIFT the accessor into the project** - make `tax_graph/extract/candidate.py` use it so the
   GENERATED graph stops baking raw OCR into node labels (46 of 232 today), and move the invariant
   test into `tests/`. This is the round that pays the full-suite cost.
4. **Depth-normalized candidate diff** - all **5 of 5** overlapping rows report a false
   `expression_disagreement`, because the candidate expression refers to neighbours by node id while
   `_live_expression` inlines the handcrafted subtree; same rule, two depths. Compare at one depth.
5. **Round-trip renderer** - render a tree back to English from the operation registry and diff it
   against the printed source; disagreement becomes a review finding. Generation is deterministic
   even where parsing is not, so this is the reliability check the pipeline currently has no form of.
6. **Sibling subexpression recovery (CSE)** - 2441 line 25's `UNRESOLVED` block is `MIN(line 20, line
   21)`, sitting in the sibling branch. Hashing subtrees recovers deterministically what a human gets
   by reading across. Same machinery as item 3; do them together or not at all.
7. **Construction drift detection** - reviews call out new punctuation and usage as a ranked finding
   with system-filed evidence, against the versioned inventory S68 produces.
8. **Column and grid recovery**; **phrase obligations**; **S53 approval gate**; **known-red cleanup**.

**STANDING FAILURES, honest.** 2441 line 25 wrong for the **eighth** consecutive run - now
`LOOKUP_TABLE arguments must be named leaf operands with a role`, after one repair. 6251 lines 13 and
20 **no longer fail closed**; both repair to a cross-document reference (`max(form_1040_2025 line 4,
0)` and `max(form_1040_nr_2025 line 15, 0)`). That is a status change, not a win: the references
resolve now, and whether they resolve to the RIGHT line is unreviewed.

## Current round

**M20-S76 IN FLIGHT (Worker, 2026-08-07). LIFT THE INSTRUCTION PARSER INTO THE PROJECT.**
**REAL-PROJECT ROUND** - touches `tax_graph/extract/instruction_sections.py` and its callers.
**Pays the full suite, and that suite is ALSO S74's gate** (see below).

**S75 IS ACCEPTED at `b2982c6`**, verified independently by the Architect. Lift
`pilot/instruction_parser.py` into production. The pilot stays where it is; this round moves the
behaviour, not the file.

**THE THREE FIXES TO LIFT.** All are ours; none is an OCR failure.
1. **Read bold-only lines as headings.** Mistral emits `**Depletion**` where our `_HEADING_RE` only
   matches `^#`.
2. **Canonicalize anchors against the form's KNOWN PRINTED LINES.** Deterministic, not heuristic.
3. **Parse the cached HTML as a SECOND source with provenance** (`html` / `ocr`) on every section.
   All 7 instruction documents have HTML cached.

**MEASURED EFFECT THE LIFT MUST REPRODUCE IN PRODUCTION.**
- **106 phantom anchors -> 0.** 101 of them on the 1040 alone, from alpha-range expansion inventing
  `1j`-`1y`, `6e`-`6y`, `13e`-`13y`, `17b`-`17y`, `24l`-`24y`; 5 on 6251 from lost em-dashes
  (`3o`, `4a`, `5e`, `8a`, `11a`).
- **1040 line sections 256 -> 143**, matching HTML 143. **The current parser reports nearly twice
  the sections the document actually has.**
- **6251 30 -> 35**, matching HTML, gaining lines **2d, 2f, 2g, 2l, 3, 4, 5, 8, 11, 15**. Lines 4 and
  11 are cells we derive.
- **Schedule D 11 -> 12.** **All seven documents match the HTML count exactly.**

**STORE BOTH, NEVER "EITHER".** Sections carry provenance and consumers must not fall back between
sources. 32 disagreements were recorded, **31 HTML-richer and 1 OCR-richer** (`schedule_a_2025`
line 1: OCR has `Line 1 Medical and Dental Expenses`, HTML has bare `Line 1`). **Neither source
dominates**, which is why both are kept and why a fallback would silently pick the poorer one.

1. **THE INVARIANT TEST IS THE DELIVERABLE.** In `tests/`, over the real cached corpus: **no
   instruction section may be filed under a line absent from that form's printed-line inventory.**
   That is what makes 106 phantoms unable to come back, and it is the same shape as the S71 label
   invariant that stopped the raw-OCR regression.
2. **EXISTING TESTS WILL CHANGE, AND THAT IS EXPECTED - BUT NEVER BY WEAKENING.**
   `tests/test_instruction_sections_m20.py` and the coverage assertions encode the OLD, phantom-laden
   counts. Update them to the measured truth and **state the reason in the diff**. A count that drops
   because phantoms disappeared is a fix; a deleted assertion is not.
3. **`instructions_schedule_b_2025` produces no line sections from either source.** Surface it as
   `document_without_line_sections`. Silence is not an acceptable answer for a manifest document.
4. **Report the effect on cell coverage** - how many anchors gain an instruction section, per
   document. Do NOT run the provider; the Architect will run the canary afterwards to see whether the
   recovered 6251 sections change any derivation.

**FULL SUITE REQUIRED, AND IT GATES TWO ROUNDS.** **S74 is implemented at `b153e94` and still
UNACCEPTED** - its suite was stopped deliberately by the Architect so this lift could proceed,
because both rounds touch `tax_graph/extract` and one run validates the state that actually ships.
Baseline is **20 pre-existing failures**; anything outside that set is a regression. If it fails,
attribute by test name - `instruction_sections`/`outline` points at S76, `cells`/`derive` at S74.
Short `PYTEST_DEBUG_TEMPROOT`; see below.

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

**Nothing is open for the Architect.** The three items `doctor` flagged STALE at 73 commits on
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
