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

**BALL: WORKER - M20-S69 (GENERATE THE THREE-COLUMN REVIEW PANEL, PILOT UNDER `pilot/`).**
Active spec is under Current round. **Pilot rules bind every round in this line of work**, not just
this one: off to the side, read-only, own tests, no full-suite gate, lift into the project later.
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
1. **Depth-normalized candidate diff** - all **5 of 5** overlapping rows report a false
   `expression_disagreement`, because the candidate expression refers to neighbours by node id while
   `_live_expression` inlines the handcrafted subtree; same rule, two depths. Compare at one depth.
2. **Round-trip renderer** - render a tree back to English from the operation registry and diff it
   against the printed source; disagreement becomes a review finding. Generation is deterministic
   even where parsing is not, so this is the reliability check the pipeline currently has no form of.
3. **Sibling subexpression recovery (CSE)** - 2441 line 25's `UNRESOLVED` block is `MIN(line 20, line
   21)`, sitting in the sibling branch. Hashing subtrees recovers deterministically what a human gets
   by reading across. Same machinery as item 1; do them together or not at all.
4. **Construction drift detection** - reviews call out new punctuation and usage as a ranked finding
   with system-filed evidence, against the versioned inventory S68 produces.
5. **Column and grid recovery**; **phrase obligations**; **S53 approval gate**; **known-red cleanup**.

**STANDING FAILURES, honest.** 2441 line 25 wrong for the **eighth** consecutive run - now
`LOOKUP_TABLE arguments must be named leaf operands with a role`, after one repair. 6251 lines 13 and
20 **no longer fail closed**; both repair to a cross-document reference (`max(form_1040_2025 line 4,
0)` and `max(form_1040_nr_2025 line 15, 0)`). That is a status change, not a win: the references
resolve now, and whether they resolve to the RIGHT line is unreviewed.

## Current round

**M20-S69 IN FLIGHT (Worker, 2026-08-06). GENERATE THE THREE-COLUMN REVIEW PANEL - PILOT.**
Reference: S68 pilot at `f0174ab`.

**PILOT RULES BIND (see BALL).** Everything lands under `pilot/`; nothing outside it changes; tests
live in the pilot and stay out of `tests/`; no full-suite run; plain script entry point.

**WHY THIS ROUND EXISTS.** John, 2026-08-06, wants to review cells as three columns: IRS text, the
saved/inferred operation, and the flowchart. The Architect hand-built a three-cell mock to agree the
layout. **That mock is exactly the artifact the prime directive forbids** - handcrafted, three cells
chosen by the Architect, HTML written by hand. It cannot be trusted as a projection and does not
scale to 157 anchors. This round replaces it with generated output.

**END STATE.** A pilot script that reads a candidate workspace and writes one self-contained HTML
file containing a three-column panel per printed anchor. Every character in every column comes from
the graph or the run report. **Nothing is authored, nothing is paraphrased.**

1. **Column 1 - IRS text, verbatim and never concatenated.** Label, form face, and instruction page
   as separate headed blocks. Where no instruction section is joined, say so explicitly; an empty
   block is a finding, not a gap to hide. Showing these separately is what exposed the 1040-NR
   defect on 6251 line 18, and that only works while they stay apart.
2. **Column 2 - the operation exactly as the graph holds it.** The rendered expression, the operand
   node ids with the edge role each one carries, and the rule id. No prettifying that loses a name.
   Role coverage is uneven and the panel must show that honestly: SUBTRACT carries `minuend` and
   `subtrahend`, MIN and MAX carry `candidate` for every operand.
3. **Column 3 - flow, and RULE 9 DECIDES WHETHER THERE IS ONE.** A diagram only where the cell
   branches. A linear step chain where depth is greater than 1 with no branch. An explicit "depth 1,
   no diagram" otherwise - `docs/review-notation.md` rule 9: a flowchart for `line 15 - line 22` is
   worse than the text. Report the three-way split across all anchors.
4. **A cell with no operation still gets a panel.** `form_2441_2025` line 25 is `review_gap` after
   eight failed runs and 90 anchors are skipped. Render the hole, name the finding, and never let an
   absent operation render as an empty column that reads like nothing was wrong.
5. **Rename the jargon in the pilot.** The S68 construction id `zero_or_less_floor` uses `floor`,
   banned by rule 8 - the rule John gave with the sixty-year-old-MBA line, and the one
   `review-notation.md` says must stop at the human boundary. **Also REPORT, do not fix, the same
   word inside the graph itself**: nodes `form_2441_2025_zero_floor` and
   `form_2441_2025_root_line_26_pre_floor`. Those are outside the pilot boundary and are a later
   round.

**Evidence required.** Run over all 157 anchors from `C:\tmp\m20_s68_candidate`. State the
diagram / chain / none split, and the count of panels rendering a hole. **Do not re-run the
provider.**

**DO NOT BUILD AGAINST A SYNTHETIC FIXTURE.** Standing S64 lesson: tests green on a toy row that no
real report resembles proved nothing, and the writer emitted an empty graph on real data.

**INPUT ARTIFACTS ALREADY EXIST.** `C:\tmp\m20_s68_live` (run) and `C:\tmp\m20_s68_candidate`
(candidate workspace: `candidate.yaml`, `coverage.yaml`, `diff.yaml`, and
`graph/2025/_drafts/<document>/` with rows, nodes, edges, rules, citations).

**S68 IS ACCEPTED at `f0174ab`**, fixture fix at `f2ac122`. Denominator 157 printed anchors.
Cross-tab, count then derived/repaired/errored/skipped: checkbox **15; 6/1/1/7**, zero-or-less
**14; 9/2/2/1**, parenthetical **13; 8/2/0/3**, smaller/smallest **13; 11/0/1/1**, If/Otherwise
**7; 2/1/1/3**. Comparator gap **36 anchors**, 25 of which produced a graph that cannot record
which comparison the text asked for.

**WHAT THE S68 NUMBERS MEAN, and it is the answer to John's pick-two question so far.**
`smaller of` derives 11 of 13; `If ... Otherwise` derives 2 of 7. **Failure concentrates on
branching, not on complexity.** Straight mappings to a named operation succeed; branches do not,
and branches are exactly where `IF_ELSE` stores no comparator and where the depth ceiling bit 2441
line 25. Three symptoms, one location.

**John's parenthetical hypothesis comes back QUALIFIED.** The pattern matched 13 anchors, but 4 of
the 15 distinct phrases behind them are prose asides, not computational variants - "(if you or your
spouse was a student or was disabled, see the instructions)" and "(in other words, ...)".
**Punctuation locates the construction but does not separate computation from commentary.**

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

**WORKER COMPLETION (2026-08-06; awaiting Architect acceptance).** S69 is implemented under
`pilot/` as `review_panel.py`, `test_review_panel.py`, and `README.md`. It reads the real
`C:\tmp\m20_s68_candidate` source reports and candidate drafts, emits one self-contained HTML
panel for every printed anchor, preserves separate label/form-face/instruction blocks, projects
only promoted graph operations and edge roles, and renders held-back rows as named holes. It does
not re-run the provider or write candidate/graph artifacts.

**REAL-CORPUS EVIDENCE.** The generated artifact is at
`C:\Users\devbox\.codex\visualizations\2026\08\06\019fd7ff-15d7-7d62-8122-8cb2b270f6a6\m20_s69_review_panel.html`:
157 anchors, 9 diagrams, 36 chains, 112 none, and 92 panels with a hole. The HTML has 157 review
articles. The graph terminology report lists 10 node ids containing `floor`, including
`form_2441_2025_zero_floor` and `form_2441_2025_root_line_26_pre_floor`; no graph artifact was
changed.

**TEST EVIDENCE.** RAN:
`.venv\Scripts\python.exe -m pytest pilot\test_review_panel.py -q` -> **5 passed, 1 warning**
(2.51s). The warning is the known permission failure writing the pre-existing `.pytest_cache`;
the first run also hit the known poisoned `.test_tmp` during `tmp_path` setup, so the CLI test was
made hermetic by using the writable visualization scratch path and leaves no artifact. RAN:
`.venv\Scripts\python.exe pilot\review_panel.py C:\tmp\m20_s68_candidate --output C:\Users\devbox\.codex\visualizations\2026\08\06\019fd7ff-15d7-7d62-8122-8cb2b270f6a6\m20_s69_review_panel.html`
-> **157 anchors; 9 diagrams / 36 chains / 112 none; 92 holes**. RAN:
`.venv\Scripts\python.exe tools\check_ascii.py` -> **ASCII check OK**. No provider run and no
full suite were performed, per pilot rules.

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
