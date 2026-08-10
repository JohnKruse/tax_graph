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

**BALL: JOHN - S93 AND S94 BOTH ACCEPTED. THE WIDE CORPUS IS WRITABLE FOR THE FIRST TIME.
Worksheets are next and their spec is staged as queue item 2.**

**S93 ACCEPTED** (`cb57f8e`, `079525a`) - a line value that is not a line now fails at derivation
instead of crashing the graph writer. **S94 ACCEPTED** (`c97d01c`, `010785f`) - `--process
broken|all`, default `all`.
**Architect fixes alongside them:** `b1cc7b8` one canonical line-id builder, `c6d4e4e` a stub
survives per LINE not per document, `4a09e9b` per-pass accounting.

**FULL PASS, 11 documents:** **351 of 410 printed anchors (85.6%)**, cost **$0.2505**,
**1 regression** against the 64 protected rows - `form_2441_2025` line 19, the known-unstable row.
Coverage fell from 356 because `operand_line_not_canonical` fired **35 times**; **those rows were
passing while unwritable, so this is the round working.**

**THE CANDIDATE BUILDS FROM A FRESH RUN: 588 nodes, 846 edges, 581 operands, ZERO dangling ids**,
11 source documents, 61 stub documents, lifecycle 89 unresolved / 4 ingested. **Every operand
resolves to something real or stubbed, and each stub already carries the address its real version
will occupy.**

**FULL SUITE 2026-08-10: 18 failed, 910 passed, 8 skipped, 1 xfailed in 0:58:36** - the documented
pre-existing families, **zero new failures**, passes 894 -> 910, and
`test_m20_s71::test_real_candidate_node_labels_use_clean_text` **now passes** after failing the
last three suites.

**A BROKEN PASS CANNOT SEE A CHANGE THAT AFFECTS PASSING ROWS, and we proved it the hard way.** The
id fix changed stub minting for SUCCESSFUL rows, so a broken-only pass carried the stale ids forward
and the candidate still failed. **Codex was right and the Architect was wrong to call that stale.**
**This is exactly why the default is `all`.**

**PER-PASS ACCOUNTING NOW EXISTS** - `pass_rows_sent`, `pass_rows_attempted`, `pass_cost`,
`pass_row_status_counts`, beside the merged totals. A full pass reads **410 rows / $0.2505**;
without these a broken pass and a full pass were indistinguishable except by the mode flag.


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

**M20-S93 WORKER VERIFICATION (2026-08-10):** The derivation guard is present at `cb57f8e` and
the canonical external line-id correction is at `b1cc7b8`. Added regression coverage for both
same-form noncanonical phrases and source-backed worksheet stub ids. The real S93 candidate
regeneration still stops on the OLD stored stub id, exactly as the S94 seam predicts; do not
hand-edit that promoted run artifact. The required next action is the planned broken-only
re-derivation, then candidate regeneration and `pilot/run_report.py`.

RAN: `$env:PYTEST_DEBUG_TEMPROOT=(Resolve-Path .test_tmp_codex).Path; .venv\Scripts\python.exe -m pytest tests\test_derive_cells_m20.py -q` -> **76 passed, 1 warning**.
RAN: `$env:PYTEST_DEBUG_TEMPROOT=(Resolve-Path .test_tmp_codex).Path; .venv\Scripts\python.exe -m pytest tests\test_derive_cells_m20.py tests\test_candidate_regeneration_m20.py tests\test_m20_s90b.py tests\test_m20_s90c.py -q` -> **92 passed, 1 warning**.
RAN: `.venv\Scripts\python.exe tools\check_ascii.py` -> **ASCII check OK**.
RAN: `git diff --check` -> **clean**.
RAN: `.venv\Scripts\python.exe -m tax_graph.cli regenerate-candidate --run-dir C:\tmp\m20_s93\run --output-dir C:\Users\devbox\.codex\visualizations\2026\08\10\019feafa-3685-7523-a9c7-72fa3f22a1ce\m20_s93_candidate --expected-document form_1040_2025 --expected-document form_2441_2025 --expected-document form_6251_2025 --expected-document schedule_a_2025 --expected-document schedule_1a_2025 --expected-document schedule_1_2025 --expected-document schedule_2_2025 --expected-document schedule_3_2025 --expected-document schedule_b_2025 --expected-document schedule_d_2025 --expected-document form_8949_2025` -> **exit 1**, `ValueError: external stub id form_social_security_benefits_worksheet_2025_root_line_18 does not match canonical id social_security_benefits_worksheet_2025_root_line_18`.
NOT RUN: full suite and provider/corpus re-derivation; the S93 acceptance seam requires the S94 broken-only implementation and a network-capable provider leg.

**M20-S94 WORKER STATUS (2026-08-10):** Implemented `--process all|broken` in
`experiments/derive_cells_s25.py`, with `all` as the default. Broken mode reads the prior
document report, sends only rows whose recorded status is not `derived` or `repaired`, and
merges untouched successful rows back into the complete current report. The report records
`process_mode`; `pilot/run_report.py` displays it. Missing or malformed prior reports fail closed.
Repeated printed lines are rederived as one flow group because their occurrence is the only stable
local disambiguator available in the report format. No graph, draft, review, or promoted artifact
was changed.

RAN: `$env:PYTEST_DEBUG_TEMPROOT=(Resolve-Path .test_tmp_codex).Path; .venv\Scripts\python.exe -m pytest tests\test_m20_s94.py tests\test_derive_cells_m20.py tests\test_candidate_regeneration_m20.py tests\test_m20_s90b.py tests\test_m20_s90c.py tests\test_derive_cells_s30.py tests\test_m20_s31.py tests\test_m20_s41.py pilot\test_run_report.py -q` -> **120 passed, 1 warning**.
RAN: `.venv\Scripts\python.exe tools\check_ascii.py` -> **ASCII check OK**.
RAN: `git diff --check` -> **clean**.
NOT RUN: provider/corpus re-derivation command against `C:\tmp\m20_s93\run`; the scoped
provider/network action was rejected by the safety review because it would send source-derived
prompts and payloads to an external destination without explicit egress approval. NOT RUN: full
suite; it exceeds the 600-second Worker command cap and the accepted known-red baseline remains
Architect-side.

**M20-S94 REWORK (2026-08-10):** The real S93 seam exposed two correctness gaps in the first
implementation. `form_8949_2025` contains repeated printed lines 1 and 2, so rejecting duplicate
prior lines prevented the immediate broken-only run. Repeated lines are now treated as one flow
group and all occurrences are rederived together. Successful rows are reusable only when their
source packet matches; legacy reports are checked by their source fields, and new reports carry a
SHA-256 source fingerprint. A missing current result, unexpected result line, malformed prior row,
or source mismatch fails closed rather than silently dropping or reusing a row.

RAN: `$env:PYTEST_DEBUG_TEMPROOT=(Resolve-Path .test_tmp_s94_rework).Path; .venv\Scripts\python.exe -m pytest tests\test_m20_s94.py -q` -> **11 passed, 1 warning**.
RAN: `$env:PYTEST_DEBUG_TEMPROOT=(Resolve-Path .test_tmp_s94_rework).Path; .venv\Scripts\python.exe -m pytest tests\test_m20_s94.py tests\test_derive_cells_m20.py tests\test_candidate_regeneration_m20.py tests\test_m20_s90b.py tests\test_m20_s90c.py tests\test_derive_cells_s30.py tests\test_m20_s31.py tests\test_m20_s41.py pilot\test_run_report.py -q` -> **124 passed, 1 warning**.
RAN: `.venv\Scripts\python.exe tools\check_ascii.py` -> **ASCII check OK**.
RAN: `git diff --check` -> **clean**.
RAN: real S93 local seam against `C:\tmp\m20_s93\run` with no provider calls -> **11 reports,
62 rows selected, merged output complete at 410 rows; form_8949 duplicate lines 1 and 2 handled
as one flow group**.
NOT RUN: provider/corpus re-derivation; it would send source-derived prompts to an external
provider and was not authorized. NOT RUN: full suite; it exceeds the 600-second Worker command
cap and the accepted known-red baseline remains Architect-side.

**M20-S95 WORKER STATUS (2026-08-10):** Implemented the queued column-qualified operand slice.
Line operands now carry a separate nullable lowercase `column` token in the provider schema and
prompt, while the validator remains compatible with legacy reports that omit the field. Graph
projection, external-input records, candidate normalization, and candidate line stubs preserve
the column and use `*_root_line_<line>_column_<column>` source-address ids. Existing exact graph
nodes remain available through the `node` operand; this slice adds the missing source-address
plumbing and does not hand-author or promote any graph object.

RAN: `$env:PYTEST_DEBUG_TEMPROOT=(Resolve-Path .test_tmp_codex).Path; .venv\Scripts\python.exe -m pytest tests\test_derive_cells_m20.py tests\test_candidate_regeneration_m20.py tests\test_m20_s31.py tests\test_m20_s41.py tests\test_m20_s51.py tests\test_m20_s54.py tests\test_m20_s85_comparator.py tests\test_m20_s90b.py tests\test_m20_s90c.py tests\test_m20_s94.py tests\test_derive_cells_s30.py pilot\test_run_report.py -q` -> **145 passed, 1 warning**.
RAN: `$env:PYTEST_DEBUG_TEMPROOT=(Resolve-Path .test_tmp_codex).Path; .venv\Scripts\python.exe -m pytest tests\test_doctor_m20.py tests\test_prompt_experiment_m20.py tests\test_operation_registry_m20.py -q` -> **34 passed, 1 warning**.
RAN: `.venv\Scripts\python.exe tools\check_ascii.py` -> **ASCII check OK**.
RAN: `git diff --check` -> **clean**.
NOT RUN: provider/corpus re-derivation; the new wire contract needs a live provider leg, and
source-derived prompts were not authorized for external egress in this Worker context. NOT RUN:
full suite; it exceeds the 600-second Worker command cap and the accepted known-red baseline
remains Architect-side.


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
