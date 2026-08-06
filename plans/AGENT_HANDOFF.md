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

**BALL: WORKER - M20-S70 (ONE READ ACCESSOR FOR CELL TEXT). PILOT ROUND, `pilot/` ONLY.**
Active spec is under Current round. **PILOT WORK RESUMES** (John, 2026-08-06): the graph now carries
clean text, so the remaining garbage is consumer-side. Pilot rules bind: off to the side, read-only,
own tests out of `tests/`, no full-suite run, no provider run, lift into the project later.

**S71 IS IMPLEMENTED AT `e79f2cd` AND VERIFIED ON THE REAL CORPUS, BUT NOT YET ACCEPTED.** The
Architect independently rebuilt the candidate: **153 of 153 rows carry clean form-face text** (was
67) and **0 of 194 node labels** carry the raw-OCR signature (was 46 of 232), with coverage
unchanged. Acceptance waits only on the full suite, which the Worker could not complete inside its
600-second cap. **Do not edit `tax_graph/` while that suite is running** - `pilot/` is not collected
by `testpaths`, which is why this round is safe to run alongside it.

**S71 PROVED THE ACCESSOR IS NECESSARY, ON REAL OUTPUT.** With the graph clean, **72 of 157 panels
still render `z Add lines 1a through 1h 1z`**. `pilot/review_panel.py:126` reads
`candidate_row.get("label") or source_row.get("label_after") or source_row.get("label_before")`.
S71 correctly made `label` empty because that row has no caption - and **`""` is falsy, so the chain
read "correctly absent" as "missing, try the next source"** and reached back into the raw run report
for the text the graph had just discarded. **This is the whole round in one line: fixing the source
does not help while consumers can re-derive the wrong answer.**
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
1. **Column 3 becomes the agreed notation** - the S69 flow is an edge dump: zero `<svg>`, zero
   diamonds, zero Yes/No arrows across all 157 panels; it renders `zero_floor` and node ids into the
   human column and re-narrates upstream lines. Must implement `docs/review-notation.md` rules 1-8,
   with phrasing read from the operation registry. Was specced at `41fffff`; recover with `git show`.
2. **LIFT the accessor into the project** - make `tax_graph/extract/candidate.py` use it so the
   GENERATED graph stops baking raw OCR into node labels (46 of 232 today), and move the invariant
   test into `tests/`. This is the round that pays the full-suite cost.
3. **Depth-normalized candidate diff** - all **5 of 5** overlapping rows report a false
   `expression_disagreement`, because the candidate expression refers to neighbours by node id while
   `_live_expression` inlines the handcrafted subtree; same rule, two depths. Compare at one depth.
4. **Round-trip renderer** - render a tree back to English from the operation registry and diff it
   against the printed source; disagreement becomes a review finding. Generation is deterministic
   even where parsing is not, so this is the reliability check the pipeline currently has no form of.
5. **Sibling subexpression recovery (CSE)** - 2441 line 25's `UNRESOLVED` block is `MIN(line 20, line
   21)`, sitting in the sibling branch. Hashing subtrees recovers deterministically what a human gets
   by reading across. Same machinery as item 3; do them together or not at all.
6. **Construction drift detection** - reviews call out new punctuation and usage as a ranked finding
   with system-filed evidence, against the versioned inventory S68 produces.
7. **Column and grid recovery**; **phrase obligations**; **S53 approval gate**; **known-red cleanup**.

**STANDING FAILURES, honest.** 2441 line 25 wrong for the **eighth** consecutive run - now
`LOOKUP_TABLE arguments must be named leaf operands with a role`, after one repair. 6251 lines 13 and
20 **no longer fail closed**; both repair to a cross-document reference (`max(form_1040_2025 line 4,
0)` and `max(form_1040_nr_2025 line 15, 0)`). That is a status change, not a win: the references
resolve now, and whether they resolve to the RIGHT line is unreviewed.

## Current round

**M20-S70 IN FLIGHT (Worker, 2026-08-06). ONE READ ACCESSOR FOR CELL TEXT - PILOT.**
Reference: S69 generator at `af351d2`.

**PILOT RULES BIND (see BALL).** Everything under `pilot/`; nothing outside changes; tests in the
pilot, out of `tests/`; no full-suite run; no provider run. **Do not edit `tax_graph/` in this
round** - the generator fix is the lift round and is queued.

**WHY THIS ROUND EXISTS.** John, 2026-08-06: *"pulling text from the graph and putting into
something should be simple and reliable. Maybe we need some kind of fixed interface for the graph
related actions."* He is right, and the label defect is the symptom rather than the disease.

**THREE CONSUMERS ANSWER "WHAT IS THIS CELL'S LABEL" THREE DIFFERENT WAYS.**

- `tax_graph/extract/candidate.py:462` - `label_after or label_before or ""`
- `pilot/review_panel.py:128` - a four-step chain ending at `anchor.get("label_after")`
- `pilot/constructions/measure.py:147` - `value.get("label") or value.get("label_after") or ""`

Every new consumer invents a fourth. **This is the third instance of one architectural cause.** The
other two: `workbench/address_verdicts.py:92` and `tax_graph/extract/candidate.py:573` are two
independent expression normalizers that disagree about operand ordering; and S66 existed because the
operation registry and the validator disagreed about roles. S66 centralized and S67 aligned, and
that drift stopped. Same move here.

**MEASURED, so the round starts from fact.**

- `label_before` == `form_face_before` on **67 of 67** rows. Label and form face were never two
  sources; they are the same string shown twice.
- `form_face_after` is clean on **67 of 67**. The cleaner works: `$15,750 14 Add lines 12e, 13a, and
  13b 14` becomes `Add lines 12e, 13a, and 13b`.
- `label_after` is populated on only **8 of 67**, and when populated it is the real caption -
  `Excluded benefits.`, `Tentative minimum tax.`, `AMT.`
- The published hand-authored graph carries **0 of 417** raw-OCR node labels. The generated
  candidate graph carries **46 of 232**. **The clean graph is the one humans wrote and the dirty one
  is the thing meant to replace it.**

**LIVE PROOF FROM S71, and it is the sharpest evidence this round has.** With the graph now
clean, **72 of 157 panels still render `z Add lines 1a through 1h 1z`**. `review_panel.py:126` reads
`candidate_row.get("label") or source_row.get("label_after") or source_row.get("label_before")`.
S71 correctly set `label` to empty because that row genuinely has no caption, and **`""` is falsy**,
so the chain treated "correctly absent" as "missing, try the next source" and pulled back the raw
OCR the graph had just discarded. **Rule 3 below is not a style preference; it is the fix.**

**END STATE.** One read-only accessor in the pilot - `pilot/cell_access.py` - that is the only way
pilot code reads cell text, with `review_panel.py` and `measure.py` rewired onto it and their
fallback chains deleted.

1. **One function per question**: label, form face, instruction section, expression, rendered
   wording, operands with their edge roles, findings, status. A consumer asks one question and gets
   one answer.
2. **NO CONSUMER PERFORMS A FALLBACK.** The accessor decides once, in one place. A `x or y` chain
   over cell text anywhere outside the accessor is a defect in this round.
3. **ABSENCE IS A TYPED VALUE, NOT AN EMPTY STRING.** `""` is exactly what makes `a or b` possible;
   if absence cannot be coerced into a fallback chain, the bug class cannot recur. A missing caption
   must be reportable as missing, never substitutable.
4. **Label means the caption only.** `label_after` and nothing else. Absent on 59 of 67 rows is the
   truth and must render as absent.
5. **Invariant test at the accessor, over all 157 real anchors**: no label returned may begin and
   end with the same line token. One test, inherited by every consumer, instead of one per surface.
   This is what stops a fourth recurrence.
6. **Report absence as data**: how many anchors have a real caption, how many have no joined
   instruction section, how many have no operation. Absence becomes visible rather than filled in.

**Evidence required.** Regenerate the panel over all 157 anchors from `C:\tmp\m20_s68_candidate`.
State the caption/instruction/operation absence counts, and show that no fallback chain over cell
text remains in pilot code outside the accessor.

**DO NOT BUILD AGAINST A SYNTHETIC FIXTURE.** Standing S64 lesson.

**S69 IS ACCEPTED at `af351d2`.** The generator reproduces exactly: 157 anchors, 9 diagrams /
36 chains / 112 none, 92 holes. Columns 1 and 2 are structurally right; column 3 is a graph dump and
is the NEXT round, deliberately after this one - there is no point rendering better diagrams on top
of text fetched three different ways.

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
