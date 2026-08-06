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

**BALL: WORKER - M20-S71 (CLEAN TEXT FOR EVERY PRINTED ANCHOR). IMPLEMENTED; AWAITING ARCHITECT ACCEPTANCE.**
Active spec is under Current round. **PILOT WORK IS PAUSED** by John, 2026-08-06: the graph must
carry clean text in its cell nodes before anything renders it. Pilot rules still bind when the
pilot resumes: off to the side, read-only, own tests, no full-suite gate, lift in later.
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
1. **One read accessor for cell text (pilot)** - three consumers answer "what is this cell's label"
   three ways: `candidate.py:462`, `review_panel.py:128`, `measure.py:147`. No consumer performs a
   fallback; absence is a typed value, never `""`. Was specced at `894974d`; recover with `git show`.
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

**M20-S71 IN FLIGHT (Worker, 2026-08-06). CLEAN TEXT FOR EVERY PRINTED ANCHOR.**

**THIS IS A REAL-PROJECT ROUND, NOT A PILOT ROUND.** It edits `tax_graph/` and it pays the full
suite. John, 2026-08-06: *"I want to get the graph extraction of the text into the cell nodes fixed
first... It is a scandal that we keep having problems with the entries. Focus solely on that."*
**All pilot work is paused. Do not touch `pilot/`. Do not add scope.**

**ROOT CAUSE, ONE LINE.** `tax_graph/extract/cells.py:242` - `for node in formula_nodes:`. That loop
is the only place `clean_form_face_text` (`cells.py:598`) and `split_caption_and_instruction` run,
and it iterates **only over anchors the selector admitted**. **Text cleaning is coupled to
selection.** An anchor the selector skips never gets cleaned, so the only text it carries is
`node.label` - the raw geometry row, line number at both ends and neighbouring columns bled in.

**MEASURED on `C:\tmp\m20_s68_candidate`, 157 printed anchors.**

- **86 anchors carry NO cleaned text at all** - `form_face_text` empty; only the raw label survives,
  e.g. 1040 line 1a: `Income 1 a Total amount from Form(s) W-2, box 1 (see instructions) 1a`.
- The 65 attempted rows DO have clean text: `$15,750 14 Add lines 12e, 13a, and 13b 14` correctly
  becomes `Add lines 12e, 13a, and 13b`. **The cleaner works. It is simply not being run.**
- `label_before` == `form_face_before` on **67 of 67** attempted rows - label and form face were
  never two sources.
- Generated candidate graph: **46 of 232** node labels carry the raw-OCR signature. Published
  hand-authored graph: **0 of 417**. The dirty graph is the one meant to replace the clean one.

**TARGET STATE.** Every printed anchor carries cleaned text and a caption split, **whether or not
the selector admits it for derivation.** Node labels are built from cleaned text and never from
`node.label`.

1. **Decouple cleaning from selection.** Clean every printed anchor, not only formula nodes. The
   selector decides what gets DERIVED; it must not decide what gets READ.
2. **Node label comes from cleaned text.** Today `candidate.py` writes
   `f"Line {line}: {row['label'] or line}"` over a raw label, producing
   `Line 9: 9 Add lines 1z, 2b, ... 9`. The line number must appear once, from the anchor, never
   from the text.
3. **Delete the fallback at `candidate.py:462`** - `label_after or label_before`. `label` means the
   caption only (`Excluded benefits.`, `AMT.`), present on 8 of 67 rows; absent is the truth on the
   rest and must be recorded as absent, never backfilled with raw text.
4. **INVARIANT TEST IN `tests/`, over the whole real candidate**, because this defect has returned
   repeatedly and only a test stops it: no generated node label may begin and end with the same line
   token, and no node label may equal its own `label_before`. **This test is the deliverable that
   makes the fix permanent.**
5. **Report table-bearing failures instead of passing them through.** 2441 line 8's cleaned text is
   byte-identical to its raw label - the anchor `8` recurs inside the embedded decimal table and a
   stray `8 X` sits mid-table, so the cleaner cannot find the boundary. That is a named finding, not
   a clean result.

**Evidence required.** Re-derive is NOT needed for anchors that are only being re-cleaned; state
plainly which numbers come from re-running the candidate writer over the existing run at
`C:\tmp\m20_s68_live`. Report: how many of 157 anchors now carry cleaned text (target 157), how many
node labels carry the raw-OCR signature (target 0), and how many table-bearing findings were raised.
**Full suite required** - short `PYTEST_DEBUG_TEMPROOT`, see below. **Do not re-run the provider.**

**WORKER STATUS (2026-08-06).** Implemented in the real pipeline. `build_cell_frame_from_document`
now cleans every printed anchor and records the selector decision separately; `derive_cells` skips
non-admitted anchors without a provider call. Candidate regeneration reads the deterministic frame
for skipped anchors, uses form-face text for generated node labels, and no longer falls back from
`label_after` to `label_before`. The experiment report carries all anchor rows while retaining the
67-row derivation denominator. Form 2441 line 8 is reported as one `table_anchor_boundary` finding.

**REAL-CORPUS EVIDENCE.** Re-running the candidate writer only over the existing run at
`C:\tmp\m20_s68_live` produced 157 printed anchors in coverage, 153 unique canonical rows after
duplicate-anchor collapse, 153/153 unique rows with clean form-face text, **0** raw line-token node
labels, and **1** table-bearing finding (`form_2441_2025` line 8). Candidate coverage remains 61
derived + 4 repaired, 2 errored, 90 skipped, 65 resolved. No provider was run.

**TEST EVIDENCE.** RAN:
`.venv\Scripts\python.exe -m pytest tests\test_cell_caption_m20.py tests\test_derive_cells_m20.py tests\test_candidate_regeneration_m20.py tests\test_outline_span_resolution_m20.py tests\test_m20_s71.py -q`
-> **81 passed, 1 warning** (the warning is the pre-existing `.pytest_cache` permission warning).
RAN: `.venv\Scripts\python.exe -m pytest tests\test_m20_s31.py -q` -> **8 passed, 1 warning**.
RAN: `.venv\Scripts\python.exe tools\check_ascii.py` -> **ASCII check OK**.
NOT RUN TO COMPLETION: `.venv\Scripts\python.exe -m pytest -q` -> timed out at the 600-second
worker cap after partial output at 24%; no final result exists. NOT RUN TO COMPLETION: the complete
non-e2e `tests\test_*.py` partition -> timed out at the same cap after partial output at 25%; no final
result exists. Focused S71 files are green; the aggregate suites are unverified.

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
