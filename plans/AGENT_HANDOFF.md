# AGENT_HANDOFF.md

The single living doc for active Claude (Architect) <-> Codex (Worker) coordination. Update it in
place; do NOT spawn new per-topic note files. Standing rules: `../AGENTS.md`. Master plan:
`../docs/engineering-plan.md`.

## How to use
- **Worker:** raise questions/blocks under **Open for Architect**.
- **Architect:** answer there (and pin durable decisions into the relevant `PHASE_<id>.md`), then
  clear the item. Record active direction under **From Architect**.
- Keep it short - move resolved items to **Resolved** or delete them.
- History: pruned at each phase close (latest: 2026-07-23). Full narration lives in
  `plans/archive/` (phase plans with close notes) and git history.

## Current state (2026-08-02)

**Architect acceptance of M20-S25 (Claude Opus 5, 2026-08-02).** Accepted at `ff62119`. Gates
re-verified rather than taken on trust: `cells.py` has zero `open`/`write_text`/`mkdir`/
`safe_dump`/`json.dump` calls, so the pure-function guarantee still holds after a 449-line
change; protected directories are byte-identical; the Worker's `RAN:` evidence is honest,
including the `WinError 5` escalation deviation, which is a pre-existing draft ACL and not a
regression.

Architect then diagnosed the derived=0 result directly against real 2025 data:
`build_instruction_sections_frame` yields 70 Form 1040 sections over 56 printed lines, and every
one is an INPUT line. `for_line('form_1040_2025', L)` returns empty for all of
`1z, 9, 11a, 11b, 14, 15, 18, 21, 22, 24, 25d, 32, 33`. **The instruction booklet does not
document computed lines; the form face does.** The hard `missing_instruction_text` check at
`tax_graph/extract/cells.py:455` is therefore the whole blocker, and the fix is to require at
least one cited evidence source rather than that specific one. S23's ownership rules stay exactly
as they are - they were right, and this is not a reason to loosen them. Full task: M20-S26 under
**From Architect**.

**Worker session checkpoint - M20-S25 implementation (2026-08-02):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort/quota/context indicators are not
exposed by this environment. John gave go via the current task request. Single declared step:
add property validators inside `derive_cells` with one repair attempt, persist the typed
`instruction_sections` frame and coverage report, retain the legacy owner parser only as an
explicit compatibility fallback, run the real 1040 frame/provider bench, and run the declared
consumer and gate set. Applicable defect-ledger entries: D9, D12, D13, D14, D6, and the exact
RAN/NOT RUN evidence rule. No promotion, hand-authoring, live graph edit, verdict write, or
operation enum change is in scope. Protected graph and field-map artifacts were byte-identical
at session start. Declared focused files: `tests/test_derive_cells_m20.py`,
`tests/test_instruction_sections_m20.py`, `tests/test_prompt_experiment_m20.py`,
`tests/test_extract_outline_m4.py`, `tests/test_extract_m16.py`, `tests/test_cli.py`, and
`tests/test_workbench_m15.py`.

**M20-S25 deterministic checkpoint (2026-08-02):** Added input-owner and output-expression
property validation, warning-only operand quote checks, one deterministic repair prompt, row
level repaired/gapped telemetry, and a real-1040 frame builder carrying mined evidence spans.
Provider transport failures remain row errors and do not consume the repair attempt. The legacy
owner parser is documented as compatibility-only for old synthetic spans and draft sidecars;
real instruction frame spans carry explicit ownership. RAN: `$testRoot='C:\Users\devbox\.codex\visualizations\2026\08\02\019fc200-5a5e-76f2-b1f5-528bde59d87e\m20_s25_unit6'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests\test_derive_cells_m20.py -q` -> `11 passed, 1 warning in 0.87s`. Pending the consumer set, artifact persistence, real provider bench, and fast gates. The handoff is checkpointed before those expensive operations.

**M20-S25 consumer and real-data checkpoint (2026-08-02):** RAN:
`$testRoot='C:\Users\devbox\.codex\visualizations\2026\08\02\019fc200-5a5e-76f2-b1f5-528bde59d87e\m20_s25_consumers'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests\test_derive_cells_m20.py tests\test_instruction_sections_m20.py tests\test_prompt_experiment_m20.py tests\test_extract_outline_m4.py tests\test_extract_m16.py tests\test_cli.py tests\test_workbench_m15.py -q` -> `52 passed, 1 warning in 19.99s`. RAN: `& .venv\Scripts\python.exe experiments\derive_cells_s25.py --root . --year 2025 --no-provider` -> persisted the instruction frame and coverage report. RAN: `& .venv\Scripts\python.exe experiments\derive_cells_s25.py --root . --year 2025` -> exit 0 in 32.9s, 17 real 1040 rows: derived=0, repaired=0, gapped=0, errored=17; 13 missing attributed instruction sections and 4 explicit OpenRouter connection errors. No draft, promoted artifact, graph, field-map, verdict, or operation enum changed. Pending fast gates, final artifact inspection, commit, and protected-set verification.

**M20-S25 final verification evidence (2026-08-02):**

- RAN: `$testRoot='C:\Users\devbox\.codex\visualizations\2026\08\02\019fc200-5a5e-76f2-b1f5-528bde59d87e\m20_s25_final'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests\test_derive_cells_m20.py tests\test_instruction_sections_m20.py tests\test_prompt_experiment_m20.py tests\test_extract_outline_m4.py tests\test_extract_m16.py tests\test_cli.py tests\test_workbench_m15.py -q` -> `53 passed, 1 warning in 19.20s`. Every declared focused file ran; no `NOT RUN` files.
- RAN: `& .venv\Scripts\python.exe tools\check_ascii.py; git diff --check; & .venv\Scripts\python.exe -m py_compile tax_graph\extract\cells.py tax_graph\extract\instruction_ownership.py experiments\derive_cells_s25.py tests\test_derive_cells_m20.py` -> `ASCII check OK`; diff check exit 0; compile exit 0.
- RAN: `& .venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> graph integrity OK, documents=18, nodes=441, edges=409, rules=17, citations=401.
- RAN: `& .venv\Scripts\python.exe -m workbench.cli --root . --year 2025 preflight` -> sandbox attempt failed on the pre-existing draft ACL with `WinError 5`; same read-only command rerun with escalation -> passed, units=2224, derived cells=2120, legacy_mined=394.
- RAN: `& .venv\Scripts\python.exe -c "from tax_graph.acquire.citation_check import check_graph_citations; result=check_graph_citations(year='2025',raw_store='.cache/raw',root='.'); print(f'checked={result.checked} strict_mismatches={len(result.mismatches)}')"` -> checked=401 strict_mismatches=36.
- RAN: `& .venv\Scripts\python.exe -c "from tax_graph.extract.instruction_sections import load_instruction_sections_artifact; f=load_instruction_sections_artifact('output/m20_s25_form_1040_2025_instruction_sections.yaml'); print('sections=%d collision_count=%d wrong_owner_after=%d source_path=%s' % (len(f.sections), f.coverage['collision_count'], f.coverage['wrong_owner_spans_after'], f.source_path))"` -> sections=317, collision_count=32, wrong_owner_after=0, repository-relative source path.
- Protected diff check: `git diff --name-only -- graph/2025/nodes graph/2025/edges graph/2025/rules graph/2025/field_maps` -> empty. Generated frame, coverage, and real-1040 report are the only forced output artifacts; no draft was promoted.
- Local commit: `8e03732` before this handoff-only amend; final amended hash is reported by the Worker.

**Worker session checkpoint - M20-S24 implementation (2026-08-02):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort/quota/context indicators are not
exposed by this environment. John gave go via the current task request. Single declared step:
extract `derive_cells(frame, prompt, api_key) -> frame` as a pure, no-write sub-pipeline with
row-level status/error, config-supplied prompting, bounded expression trees, and deterministic
tree-to-graph conversion, then run the fixture-only consumer and gate set. Applicable
defect-ledger entries: D9, D12, D13, D14, D6, and the exact RAN/NOT RUN evidence rule. No model
calls, promotion, hand-authoring, live graph edit, verdict write, or operation enum change is in
scope. Protected graph and field-map artifacts are untouched at session start. Declared focused
files: `tests/test_derive_cells_m20.py`, `tests/test_prompt_experiment_m20.py`,
`tests/test_extract_m16.py`, `tests/test_cli.py`, and `tests/test_workbench_m15.py`.

**M20-S24 implementation checkpoint (2026-08-02):** Added the pure typed boundary in
`tax_graph/extract/cells.py`, including `CellRecord`/`CellFrame`, config-loaded prompt helper,
row-isolated provider calls, bounded expression-tree schema/validation/rendering, and a
deterministic tree-to-graph projection using `_pre_floor` plus operation-derived roles. Added
`prompts/derive_cells.md`, the example-config key, and made `experiments/prompt_experiment.py`
and `experiments/to_graph.py` consume the shared tree/projection code. Added fixture-only S24
tests; no live provider, draft, promoted artifact, or review state was touched. Pending the
declared focused test and gate commands.

**M20-S24 verification evidence (2026-08-02):**

- RAN: `$testRoot='C:\Users\devbox\.codex\visualizations\2026\08\02\019fc1dd-54f9-7e50-885f-2fdc87fc2bd2\m20_s24_focused_r2'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests\test_derive_cells_m20.py tests\test_prompt_experiment_m20.py tests\test_extract_m16.py tests\test_cli.py tests\test_workbench_m15.py -q` -> `21 passed, 1 warning in 18.66s`. Every declared focused file ran; the warning is the known pytest cache ACL warning.
- RAN: `& .venv\Scripts\python.exe tools\check_ascii.py` -> `ASCII check OK`.
- RAN: `git diff --check` -> exit 0 (Git reported only the existing CRLF normalization warning for `experiments/prompt_experiment.py`).
- RAN: `& .venv\Scripts\python.exe -m py_compile tax_graph\extract\cells.py experiments\prompt_experiment.py experiments\to_graph.py tests\test_derive_cells_m20.py tests\test_prompt_experiment_m20.py` -> exit 0.
- RAN: `& .venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> `graph integrity OK`, documents=18, nodes=441, edges=409, rules=17, citations=401.
- RAN: `& .venv\Scripts\python.exe -m workbench.cli --root . --year 2025 preflight` -> initial sandbox attempt failed on the existing `graph/2025/_drafts/form_1040_2025` ACL with `WinError 5`; the same read-only command rerun with escalation -> `review preflight passed - 2025`, units=2224, derived cells=2120, review_gap=591, legacy_mined=394.

The second implementation pass rejects model-invented quote span ids and maps arithmetic trees
to the existing reusable rules with operation-derived operand roles. No model call, promotion,
hand-authoring, live graph edit, verdict write, or operation enum change occurred. No declared
focused file is unverified. Local commit was created; do not push.

**Worker session checkpoint - M20-S23 implementation (2026-08-02):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort/quota/context indicators are not
exposed by this environment. John gave go via the current task request. Single declared step:
build the deterministic `instruction_sections` frame from acquired instruction text, carry form
context through the join, persist the artifact and coverage report, retire the competing
instruction joins in the pipeline and experiment bench, then run the declared consumer and gate
set. Applicable defect-ledger entries: D9, D6, and the exact RAN/NOT RUN evidence rule. No model
calls, promotion, hand-authoring, live graph edit, verdict write, or operation enum change is in
scope. Protected graph and field-map artifacts are untouched at session start. Declared focused
files: `tests/test_instruction_sections_m20.py`, `tests/test_instruction_sections_m18.py`,
`tests/test_extract_outline_m4.py`, `tests/test_background_m20.py`, `tests/test_cli.py`,
`tests/test_form_completeness_m20.py`, and `tests/test_workbench_m15.py`.

**Worker result - M20-S23 implementation (2026-08-02):** Added
`tax_graph/extract/instruction_sections.py` as the deterministic typed frame. It preserves
acquired text verbatim with source line/offset/page locators, tracks explicit form or schedule
context, expands printed alpha ranges, ignores page markers as boundaries, and reports per-form
coverage, collisions, wrong-owner before/after, and explicit empty contexts. The real 1040 probe
produced 317 sections across Form 1040, Schedules 1, 1-A, 2, and 3; Schedule 1-A is recorded as
an explicit zero-section context rather than disappearing. Candidate spans, outline extraction,
completeness, background evidence, prompt bench, and both experiment paths now consume the frame
owner metadata. The legacy owner parser remains only as a compatibility fallback for old synthetic
spans and old draft sidecars; real pipeline spans use explicit frame ownership.

The known collision checks hold: Form 1040 line 9 excludes Household Employment Taxes, Form 1040
line 21 excludes Student Loan Interest Deduction text, Schedule 2 line 9 retains Household
Employment Taxes, and wrong-owner-after is 0. No model calls, promotion, live graph edit, verdict
write, or output artifact was performed. Protected `graph/2025/{nodes,edges,rules}/` and
`graph/2025/field_maps/` are byte-identical to HEAD.

**Verification evidence - M20-S23:**

- RAN: `$testRoot='C:\Users\devbox\.codex\visualizations\2026\08\02\019fc1a2-bc6c-7652-b3a5-31ff4364ef88\m20_s23_final_tests'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests\test_instruction_sections_m20.py tests\test_instruction_sections_m18.py tests\test_extract_outline_m4.py tests\test_background_m20.py tests\test_cli.py tests\test_form_completeness_m20.py tests\test_workbench_m15.py -q` -> `46 passed, 1 warning in 20.10s`. This single command ran every declared focused file: `tests/test_instruction_sections_m20.py`, `tests/test_instruction_sections_m18.py`, `tests/test_extract_outline_m4.py`, `tests/test_background_m20.py`, `tests/test_cli.py`, `tests/test_form_completeness_m20.py`, and `tests/test_workbench_m15.py`.
- RAN: `& .venv\Scripts\python.exe tools\check_ascii.py; git diff --check; & .venv\Scripts\python.exe -m py_compile tax_graph\extract\instruction_sections.py tax_graph\extract\instruction_ownership.py tax_graph\extract\outline.py tax_graph\extract\outline_pipeline.py tax_graph\extract\background.py tax_graph\extract\prompt_bench.py tax_graph\verify\form_completeness.py experiments\prompt_experiment.py experiments\to_graph.py tests\test_instruction_sections_m20.py; & .venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> `ASCII check OK`; compile passed; `graph integrity OK - all references resolve`.
- RAN: `& .venv\Scripts\python.exe -m workbench.cli --root . --year 2025 preflight` with read-only filesystem escalation after the sandbox hit the existing draft-directory ACL -> `review preflight passed - 2025`; derived manifest entries `18`, units `2224`, derived cells `2120`, approved `0`, needs_recheck `0`, review_gap `591`, unreviewed `1529`, legacy_mined `394`.
- RAN: `& .venv\Scripts\python.exe -c "from tax_graph.acquire.citation_check import check_graph_citations; result = check_graph_citations(year='2025', raw_store='.cache/raw', root='.'); print(f'checked={result.checked} strict_mismatches={len(result.mismatches)}')"` -> `checked=401 strict_mismatches=36`.
- RAN: real corpus frame probe -> `sections=317`, source documents `form_1040_2025`, `schedule_1_2025`, `schedule_1a_2025`, `schedule_2_2025`, `schedule_3_2025`; empty context `schedule_1a_2025`; collisions `32`; wrong-owner-after `0`.

No declared focused file is unverified. One local commit was created; its final hash is reported
in the Worker response. Do not push.

**Worker session checkpoint - M20-S22 implementation (2026-08-01):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort/quota/context indicators are not
exposed by this environment. John gave go via the current task request. Single declared step:
repair background evidence selection so the packet satisfies the form-face citation contract,
add a read-only prompt bench that exercises the real background prompt/validation path without
writing drafts or promoted artifacts, identify the two formula cells lost by S21, then run the
declared consumer and gate set. Applicable defect-ledger entries: D9, D6, and the exact
RAN/NOT RUN evidence rule. No prompt wording change, promotion, hand-authoring, live graph edit,
verdict write, or operation enum change is in scope. Protected graph and field-map artifacts
are untouched at session start. Declared focused files: `tests/test_background_m20.py`,
`tests/test_draft_route_m20.py`, `tests/test_extract_outline_m4.py`, `tests/test_extract_m16.py`,
`tests/test_cli.py`, `tests/test_generated_review_m20.py`, `tests/test_form_completeness_m20.py`,
`tests/test_workbench_cells_api_m17.py`, and `tests/test_workbench_m15.py`; the browser file
will be declared after the bench has a stable CLI surface and run if the generated projection
changes.

**M20-S22 implementation checkpoint (2026-08-01):** Evidence selection now reserves four
form-face slots and four instruction slots, with page-local source top-up; instruction spans no
longer outrank form-face spans. The read-only `verify prompt-bench` command accepts repeated
`--id` values for field-map controls or formula cell ids and prints the exact prompt, response,
matched spans, and validation result without entering extraction or writing state. Formula
assembly now recovers a printed percentage constant such as 7.5% as a parameter node when the
model returns the one source line, and explicit ranges such as "24a through 24z" ignore only
unprinted optional child letters while preserving the normal fail-closed path elsewhere. No
prompt wording was tuned.

**M20-S22 focused tests (2026-08-01):** RAN:
`$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\31\019fb9ea-080e-7013-9aa6-04af2d56e08f\m20_s22_unit8'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests\test_background_m20.py -q`
-> 7 passed, 1 warning in 0.41s. RAN:
`$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\31\019fb9ea-080e-7013-9aa6-04af2d56e08f\m20_s22_unit9'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests\test_background_m20.py tests\test_extract_outline_m4.py tests\test_extract_m16.py tests\test_cli.py -q`
-> 38 passed, 1 warning in 18.65s. RAN:
`$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\31\019fb9ea-080e-7013-9aa6-04af2d56e08f\m20_s22_unit11'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests\test_background_m20.py tests\test_draft_route_m20.py tests\test_extract_outline_m4.py tests\test_extract_m16.py tests\test_cli.py tests\test_generated_review_m20.py tests\test_form_completeness_m20.py tests\test_workbench_cells_api_m17.py tests\test_workbench_m15.py -q`
-> 58 passed, 1 warning in 139.86s. The first run of this exact set had one stale S21
histogram assertion; it was updated to the S22 regenerated projection and the rerun is green.
RAN:
`$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\31\019fb9ea-080e-7013-9aa6-04af2d56e08f\m20_s22_e2e'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests\e2e\test_workbench_v2_m17.py -q`
-> 4 passed in 132.83s. Every declared file was executed; no `NOT RUN` files.

**M20-S22 draft-only reruns (2026-08-01):** RAN:
`.venv\Scripts\python.exe -m tax_graph.cli extract --doc form_1040_2025 --year 2025 --root .`
-> exit 0 in 333.2s, auto_accepted=0, human_review=173, deterministic_issues=122;
17/17 formula cells, background attempted=119/succeeded=48/failed=42, transport_failures=0.
RAN:
`.venv\Scripts\python.exe -m tax_graph.cli extract --doc schedule_1_2025 --year 2025 --root .`
-> exit 0 in 57.3s, auto_accepted=0, human_review=189, deterministic_issues=32;
4/4 formula cells, background attempted=45/succeeded=25/failed=5, transport_failures=0.
RAN:
`.venv\Scripts\python.exe -m tax_graph.cli extract --doc schedule_a_2025 --year 2025 --root .`
-> exit 0 in 40.0s, auto_accepted=0, human_review=75, deterministic_issues=13;
7/7 formula cells, background attempted=21/succeeded=6/failed=3, transport_failures=0.
The two S21 losses were Schedule 1 line 25 (`24l` was treated as an unresolved source even
though the form prints only 24a-24k and 24z) and Schedule A line 3 (the model returned source
line 2 for the printed 7.5% multiplier and the validator required two source lines). Both now
recover through deterministic pipeline logic, not artifact edits. Totals: background attempted
185, succeeded 79, failed 50, transport failures 0; policy_derived=0, policy_defaulted=79.

**M20-S22 prompt bench evidence (2026-08-01):** RAN:
`.venv\Scripts\python.exe -m tax_graph.cli verify prompt-bench --doc schedule_a_2025 --id 3 --year 2025 --root .`
-> exit 0; the exact response was `MULTIPLY`, `source_lines=["2"]`, quote
`Multiply line 2 by 7.5% (0.075)`, accepted with the matched form-face span
`span_schedule_a_2025_0018`. RAN:
`.venv\Scripts\python.exe -m tax_graph.cli verify prompt-bench --doc form_1040_2025 --id 'topmostSubform[0].Page1[0].f1_04[0]' --year 2025 --root .`
-> exit 0; the packet printed source spans before instruction spans and the response was
accepted with matched form-face span `span_form_1040_2025_0006`. The bench wrote no drafts or
promoted artifacts.

**M20-S22 report and gates (2026-08-01):** RAN:
`.venv\Scripts\python.exe -m tax_graph.cli verify form-completeness --year 2025 --root .`
-> `output/m20_s20_form_completeness.yaml`, completeness=28/28 (100.0%), instruction=52/68
(76.5%), policy controls with policy=180/286, policy plus form-face citation=79/286, origins
derived=0/defaulted=79/authored=101, review_gap=106. RAN:
`.venv\Scripts\python.exe tools\check_ascii.py` -> `ASCII check OK`. RAN: `git diff --check`
-> exit 0. RAN: `.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> graph integrity
OK, documents=18, nodes=441, edges=409, rules=17, citations=401. RAN:
`.venv\Scripts\python.exe -m workbench.cli --root . --year 2025 preflight` -> passed,
entries=18, units=2224, derived cells=2120, approved=0, needs_recheck=0, review_gap=591,
unreviewed=1529, legacy_mined=394. RAN strict citation check via
`check_graph_citations(year='2025', raw_store='.cache/raw', root='.')` -> checked=401,
strict_mismatches=36, the existing baseline. Protected graph, field-map, and review-verdict
diffs are empty.

**Worker session checkpoint - M20-S21 implementation (2026-07-31):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort/quota/context indicators are not
exposed by this environment. John gave go via the current task request. Single declared step:
make draft-only extraction retry transient transport failures with bounded backoff and commit
new drafts atomically so a failed run preserves the previous draft, then rerun Form 1040,
Schedule 1, and Schedule A and verify every declared consumer. Applicable defect-ledger entries:
D9, D6, and the exact RAN/NOT RUN evidence rule. No promotion, hand-authoring, live graph
edit, verdict write, or operation enum change is in scope. Protected graph and field-map
artifacts are untouched at session start.

**M20-S21 focused-test declaration (2026-07-31):** Declared files are
`tests/test_draft_route_m20.py`, `tests/test_llm_attribution_m20.py`,
`tests/test_extract_outline_m4.py`, `tests/test_extract_m16.py`, `tests/test_cli.py`,
`tests/test_generated_review_m20.py`, `tests/test_form_completeness_m20.py`,
`tests/test_workbench_cells_api_m17.py`, and `tests/e2e/test_workbench_v2_m17.py`.
The set covers atomic draft rollback, adapter retry telemetry, outline/pipeline consumers,
CLI reporting, generated-review projection, completeness, the API consumer of restored drafts,
and the browser projection. `tests/test_workbench_m15.py` will also be run because the restored
draft surface is consumed by workbench code and D5 is a standing boundary check.

**M20-S21 deterministic implementation checkpoint (2026-07-31):** RAN:
`$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\31\019fb9ea-080e-7013-9aa6-04af2d56e08f\m20_s21_unit1'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests\test_draft_route_m20.py tests\test_llm_attribution_m20.py -q`
-> 11 passed, 1 warning in 0.45s. Pending the expensive phase: consumer regression tests,
then the three draft-only extraction reruns. No live graph or verdict artifact has changed.

**M20-S21 consumer checkpoint (2026-07-31):** RAN:
`$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\31\019fb9ea-080e-7013-9aa6-04af2d56e08f\m20_s21_unit2'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests\test_extract_outline_m4.py tests\test_extract_m16.py tests\test_cli.py -q`
-> 31 passed, 1 warning in 19.80s. Pending the expensive phase: draft-only extraction for
Form 1040, Schedule 1, and Schedule A. No live graph or verdict artifact has changed.

**M20-S21 first live attempt (2026-07-31):** RAN:
`& .venv\Scripts\python.exe -m tax_graph.cli extract --doc form_1040_2025 --year 2025 --root .`
-> exit 0 in 558.4s, but the sandbox could not reach OpenRouter: 57 calls failed after
114 transport retries, 0 recovered. The run produced explicit in-memory review gaps, but the
first implementation still swapped that completed-with-call-failures batch into the draft
directory; this is a S21 defect because the previous draft must remain intact on a failed run.
The retry logs correctly distinguish transport errors and report `transport_retry_attempts` and
`transport_retry_recovered`. Fixing the commit predicate before any further live rerun; no
promoted graph, field map, verdict, or operation enum changed.

**M20-S21 safety-fix checkpoint (2026-07-31):** Added an explicit transport-failure write
predicate: retries and failure gaps remain visible in the in-memory result and provider log,
but a batch with exhausted transport failures cannot replace an existing draft. The atomic
staging rollback test now covers both mid-write exceptions and transport-failed batches. RAN:
`$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\31\019fb9ea-080e-7013-9aa6-04af2d56e08f\m20_s21_unit3'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests\test_draft_route_m20.py tests\test_llm_attribution_m20.py tests\test_extract_outline_m4.py tests\test_extract_m16.py tests\test_cli.py -q`
-> 43 passed, 1 warning in 19.16s. Pending the approved-network reruns; no live graph or verdict
artifact has changed.

**M20-S21 approved-network swap checkpoint (2026-07-31):** RAN the approved-network Form 1040
command; it reached the provider and built a complete staged result, but exited 1 after 347.7s
when Windows temporarily denied renaming the existing draft directory. A read-only ACL/process
check found the directory owned by `CodexSandboxOffline` with the expected owner-rights ACL;
an exact sibling rename probe and restore both succeeded afterward. The staged result was removed
by the failure cleanup, so the extraction must be rerun; no protected artifact changed.

**M20-S21 Windows swap-fix checkpoint (2026-07-31):** The directory-level swap now falls back
to a rollback-safe file-set replacement when Windows denies renaming the existing draft
directory. The focused route/retry tests were rerun: RAN:
`$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\31\019fb9ea-080e-7013-9aa6-04af2d56e08f\m20_s21_unit4'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests\test_draft_route_m20.py tests\test_llm_attribution_m20.py -q`
-> 13 passed, 1 warning in 0.42s. Pending the third Form 1040 draft-only run; no live graph,
field map, verdict, or operation enum changed.

**M20-S21 second approved-network attempt (2026-07-31):** RAN the same Form 1040 command;
it exited 1 after 356.7s. The provider work completed far enough to reach the final swap, but
Windows denied both the directory listing in the fallback and the directory rename. The old
draft remained in place and the staged result was cleaned up. This is the remaining portability
defect; adding bounded retries around Windows draft listing/rename before the file-set fallback.

**M20-S21 Windows retry checkpoint (2026-07-31):** Added bounded retries around Windows draft
directory rename and listing operations. RAN:
`$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\31\019fb9ea-080e-7013-9aa6-04af2d56e08f\m20_s21_unit5'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests\test_draft_route_m20.py tests\test_llm_attribution_m20.py -q`
-> 13 passed, 1 warning in 0.43s. Pending the fourth Form 1040 draft-only run; no protected
artifact changed.

**M20-S21 recoverable draft isolation (2026-07-31):** The exact known-degraded
`graph/2025/_drafts/form_1040_2025` directory was moved, recoverably, to
`.m20_s21_backup_form_1040_2025` in the workspace so the canonical draft path is empty for the
next approved-network recovery run. The backup is not a promoted artifact and will not be
committed. No graph, field-map, verdict, or operation enum changed.

**M20-S21 Form 1040 recovery evidence (2026-07-31):** RAN the approved-network command
`& .venv\Scripts\python.exe -m tax_graph.cli extract --doc form_1040_2025 --year 2025 --root .`
-> exit 0 in 322.1s. The staged draft committed at the canonical path. Metrics show formula
`17/17` succeeded, source `39/40` succeeded, background `15` succeeded and `99` named gaps,
with `background_transport_failures=0`; policy origins are `authored=80`, `defaulted=15`,
`review_gap=104`, `derived=0`. The run logged 57 successful calls, 133887 tokens, cost
0.376842, and `transport_retry_attempts=0`; the draft contains 17 rules and 49 edges.
Metrics inspection required approved local access because the draft directory ACL was
intermittently denied to the sandbox account. No protected artifact changed.

**M20-S21 Schedule 1 and Schedule A recovery evidence (2026-07-31):** RAN the approved-network
commands. Schedule 1: `& .venv\Scripts\python.exe -m tax_graph.cli extract --doc schedule_1_2025 --year 2025 --root .`
-> exit 0 in 61.4s; formula `3/4`, background `3` succeeded and `38` gaps, origins
`authored=28`, `defaulted=3`, `review_gap=42`, `derived=0`, transport failures `0`,
11 recorded successful calls, 23598 tokens. Schedule A:
`& .venv\Scripts\python.exe -m tax_graph.cli extract --doc schedule_a_2025 --year 2025 --root .`
-> exit 0 in 44.4s; formula `6/7`, background `1` succeeded and `14` gaps, origins
`authored=12`, `defaulted=1`, `review_gap=20`, `derived=0`, transport failures `0`,
13 recorded successful calls, 18359 tokens. All three target drafts are present; no promoted
graph, field map, verdict, or operation enum changed.

**M20-S21 consumer correction (2026-07-31):** The first final non-browser consumer run was
NOT accepted: RAN the declared set through `tests/test_workbench_cells_api_m17.py` and found
one stale S20 histogram assertion (`computed=7`, `unsupported=102`, `user_entered=49`). The
recovered S21 projection is `computed=15`, `copied=7`, `decision_required=34`, `unsupported=88`,
`user_entered=55`; the assertion was updated with an M20-S21 explanation. RAN:
`$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\31\019fb9ea-080e-7013-9aa6-04af2d56e08f\m20_s21_api_rerun'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests\test_workbench_cells_api_m17.py -q`
-> 4 passed in 89.52s. The initial 58-pass/1-failure run is not acceptance evidence; rerunning
the full declared non-browser set is required.

**M20-S21 final consumer evidence (2026-07-31):** After the test update, RAN the full
declared non-browser set:
`$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\31\019fb9ea-080e-7013-9aa6-04af2d56e08f\m20_s21_final_unit_r2'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests\test_draft_route_m20.py tests\test_llm_attribution_m20.py tests\test_extract_outline_m4.py tests\test_extract_m16.py tests\test_cli.py tests\test_generated_review_m20.py tests\test_form_completeness_m20.py tests\test_workbench_cells_api_m17.py tests\test_workbench_m15.py -q`
-> 59 passed in 136.77s. RAN the declared browser consumer:
`$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\31\019fb9ea-080e-7013-9aa6-04af2d56e08f\m20_s21_final_e2e'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests\e2e\test_workbench_v2_m17.py -q`
-> 4 passed in 130.26s. Every declared focused file is now verified green.

**Worker session checkpoint - M20-S20 implementation (2026-07-31):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort/quota/context indicators are not
exposed by this environment. John gave go via the current task request. Single declared step:
make filer-provided handling an explicit failover after formula/source paths, split the existing
unsupported controls into decision, identity/admin, and filer-supplied-value outcomes, retain
computation labels as named gaps, run all three target forms, and report derived versus defaulted
policy coverage. Applicable defect-ledger entries: D9, D6, and the exact RAN/NOT RUN evidence
rule. No promotion, hand-authoring, live graph edit, verdict write, or operation enum change is
in scope. Protected graph and field-map artifacts are untouched at session start.

**M20-S20 implementation checkpoint (2026-07-31):** Added the draft-only filer failover
contract to `tax_graph/extract/background.py`. Unsupported controls now retain explicit
`policy_origin`, `policy_basis`, `policy_defaulted`, `policy_derived`, and `failover_class`
metadata. The three failover classes are `filer_election`, `filer_identity_admin`, and
`filer_supplied_value`; computation language is `computed_candidate` and remains a named
`review_gap`. Failover calls run after formula and non-formula source extraction in the
outline pipeline, and `workbench/generated_review.py` refuses to let a background record
replace a resolved formula or source cell. Full physical control projection now covers Form
1040, Schedule 1, and Schedule A. The workbench explains failover as an intake question and
shows origin, basis, and class. No graph, field-map, promotion, verdict, or operation enum
was edited.

**M20-S20 provider and extraction checkpoint (2026-07-31):** RAN:
`.venv\Scripts\python.exe -m tax_graph.cli extract --doc form_1040_2025 --year 2025 --root .`
-> exit 0, 119 background calls attempted, 0 succeeded, 119 failed; RAN:
`.venv\Scripts\python.exe -m tax_graph.cli extract --doc schedule_1_2025 --year 2025 --root .`
-> exit 0, 45 attempted, 0 succeeded, 45 failed; RAN:
`.venv\Scripts\python.exe -m tax_graph.cli extract --doc schedule_a_2025 --year 2025 --root .`
-> exit 0, 21 attempted, 0 succeeded, 21 failed. Each failure is persisted as an explicit
review gap in the ignored draft and no promoted artifact changed. The requested network retry
was rejected by the safety reviewer because it would transmit workspace-derived form data to
an external LLM; no workaround or fabricated response was used. This is a provider-blocked
draft result, not acceptance evidence for successful model classification.

**M20-S20 report checkpoint (2026-07-31):** RAN:
`.venv\Scripts\python.exe -m tax_graph.cli verify form-completeness --year 2025 --root .`
-> `output/m20_s20_form_completeness.yaml`, completeness `0/28`, instruction coverage
`52/68`, non-computed policy coverage `101/286`, policy plus form-face citation `0/286`.
Current report origin totals are `derived=0`, `defaulted=0`, `authored=101`, reflecting the
provider failure honestly. The current all-form policy mix is
`computed=12, copied=7, decision_required=24, unsupported=185, user_entered=77`, with
failover classes `computed_candidate=1, filer_election=60, filer_identity_admin=23,
filer_supplied_value=101`. The report is the required force-added, fail-closed artifact.

**M20-S20 focused-test evidence (2026-07-31):** The declared files are
`tests/test_generated_review_m20.py`, `tests/test_form_completeness_m20.py`,
`tests/test_extract_outline_m4.py`, `tests/test_extract_m16.py`, `tests/test_cli.py`,
`tests/test_workbench_cells_api_m17.py`, `tests/test_workbench_m15.py`, and
`tests/e2e/test_workbench_v2_m17.py`.

RAN: `$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\31\019fb9bd-1239-7c50-9667-182f491f1105\m20_s20_unit3'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; .venv\Scripts\python.exe -m pytest tests\test_extract_outline_m4.py tests\test_generated_review_m20.py tests\test_form_completeness_m20.py -q` -> 27 passed, 1 warning in 30.45s, before the provider-failure drafts overwrote the ignored successful drafts.

RAN: `$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\31\019fb9bd-1239-7c50-9667-182f491f1105\m20_s20_unit4'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; .venv\Scripts\python.exe -m pytest tests\test_extract_outline_m4.py tests\test_generated_review_m20.py tests\test_form_completeness_m20.py -q` -> 24 passed, 3 failed, 2 warnings in 30.14s. The three failures were generated-review assertions for line 1z, line 1a, and line 22, all caused by the current connection-error draft gaps.

RAN: `$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\31\019fb9bd-1239-7c50-9667-182f491f1105\m20_s20_unit7'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; .venv\Scripts\python.exe -m pytest tests\test_extract_outline_m4.py tests\test_form_completeness_m20.py -q` -> 22 passed, 1 warning in 0.86s. RAN: `$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\31\019fb9bd-1239-7c50-9667-182f491f1105\m20_s20_generated_fixture2'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; .venv\Scripts\python.exe -m pytest tests\test_generated_review_m20.py -q -k 'background_policy'` -> 1 passed, 5 deselected, 1 warning in 2.09s.

RAN: `$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\31\019fb9bd-1239-7c50-9667-182f491f1105\m20_s20_consumers1'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; .venv\Scripts\python.exe -m pytest tests\test_extract_m16.py tests\test_cli.py tests\test_workbench_cells_api_m17.py tests\test_workbench_m15.py tests\e2e\test_workbench_v2_m17.py -q` -> 20 passed, 2 failed, 2 warnings in 242.83s. The API histogram failure and the browser line 33 citation failure both depend on the provider-failure draft, not on a promoted artifact change. RAN: `$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\31\019fb9bd-1239-7c50-9667-182f491f1105\m20_s20_consumers2'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; .venv\Scripts\python.exe -m pytest tests\test_extract_m16.py tests\test_cli.py tests\test_workbench_m15.py -q` -> 14 passed, 1 warning in 18.72s. This includes the required D5 workbench boundary test.

**M20-S20 verification gates (2026-07-31):** RAN: `.venv\Scripts\python.exe tools\check_ascii.py` -> `ASCII check OK`; RAN: `git diff --check` -> exit 0; RAN: `.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> graph integrity OK, 18 documents, 441 nodes, 401 citations; RAN: `.venv\Scripts\python.exe -m workbench.cli --root . --year 2025 preflight` -> passed, 18 entries, 2224 units, 2120 cells, `legacy_mined=394`; RAN: strict `check_graph_citations(year=2025, raw_store='.cache/raw', root='.')` -> `checked=401, strict_mismatches=36` (baseline). Protected graph and field-map diff checks are empty. Single local commit: `443fda6af322b0ba583c89bc08b3fa679b02471e` (`M20-S20: add explicit filer failover policy`). No push.

**Worker session checkpoint - M20-S19 implementation (2026-07-31):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort/quota/context indicators are not
exposed by this environment. John gave go via the current task request. Single declared step:
bring the background controls back into generated review, classify the existing authored
policies without model calls, generate only unsupported controls with fail-closed gaps, extend
completeness for non-computed policy-plus-form-face citation coverage, and report the policy mix
before/after. Applicable defect-ledger entries: D9, D6, and the exact RAN/NOT RUN evidence rule;
D4 applies if session-backed workbench tests are touched. No draft promotion, hand-authoring,
live graph edit, verdict write, or operation enum change is in scope. Protected graph and live
verdict artifacts are untouched at session start.

**M20-S19 focused-test declaration (2026-07-31):** Declared files are
`tests/test_generated_review_m20.py`, `tests/test_form_completeness_m20.py`,
`tests/test_extract_outline_m4.py`, `tests/test_extract_m16.py`, `tests/test_cli.py`,
`tests/test_workbench_cells_api_m17.py`, `tests/test_workbench_m15.py`, and
`tests/e2e/test_workbench_v2_m17.py`.
The set covers policy projection and unsupported-control generation, the extended completeness
metric, outline-pipeline consumers, source extraction schema, CLI reporting, and the API/browser
consumers of the expanded generated review surface.

**M20-S19 deterministic implementation checkpoint (2026-07-31):** The draft-only background
policy stage and complete Form 1040 projection are in place. Authored policies are carried
without model calls; unsupported controls receive one bounded policy call with code-resolved
identity and a required verbatim form-face quote, while failures remain named gaps. RAN:
`$testRoot = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\31\\019fb8d5-ccf2-7073-8824-42fdb7d3f6fd\\m20_s19_unit_round4'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; & .venv\\Scripts\\python.exe -m pytest tests\\test_extract_outline_m4.py tests\\test_generated_review_m20.py tests\\test_form_completeness_m20.py -q` -> 26 passed, 1 warning in 28.77s. This was the deterministic pre-extraction checkpoint; no live graph or verdict artifact had changed.

**M20-S19 extraction-cap checkpoint (2026-07-31):** The first approved-network extraction
attempt was NOT RUN as acceptance evidence: the sequential 119-call background pass exceeded
the 600-second worker cap and was terminated with exit 124 before draft writeout. The persisted
observability log records the cause (`tax_graph_background_policy`, several-second calls), not
a silent success. The implementation now uses bounded concurrency (default 8, configurable)
with copied run context so every provider call remains attributed and results are serialized in
field-map order. RAN: `$testRoot = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\31\\019fb8d5-ccf2-7073-8824-42fdb7d3f6fd\\m20_s19_unit_round5'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; & .venv\\Scripts\\python.exe -m pytest tests\\test_extract_outline_m4.py tests\\test_generated_review_m20.py tests\\test_form_completeness_m20.py -q` -> 26 passed, 1 warning in 28.63s. No live graph or verdict artifact has changed.

**M20-S19 draft extraction checkpoint (2026-07-31):** RAN: `.venv\\Scripts\\python.exe -m tax_graph.cli extract --doc form_1040_2025 --year 2025 --root .` -> exit 0; `auto_accepted=0`, `human_review=173`, `deterministic_issues=122`, runtime 366.5s. The draft contains 199 physical controls: 80 carried authored policies, 17 newly resolved unsupported controls, and 102 named review gaps. Policy mix changed from `computed=7, copied=7, decision_required=24, unsupported=119, user_entered=42` to `computed=7, copied=7, decision_required=34, unsupported=102, user_entered=49`. No promoted graph, live verdict, or human-review claim changed.

**M20-S19 verification checkpoint (2026-07-31):** The first downstream consumer run found and corrected the pre-S19 API histogram assertion; the rerun is the acceptance evidence. RAN: `$testRoot = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\31\\019fb8d5-ccf2-7073-8824-42fdb7d3f6fd\\m20_s19_unit_round7'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; & .venv\\Scripts\\python.exe -m pytest tests\\test_extract_m16.py tests\\test_cli.py tests\\test_workbench_cells_api_m17.py tests\\test_workbench_m15.py -q` -> 18 passed, 1 warning in 104.41s. RAN: `$testRoot = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\31\\019fb8d5-ccf2-7073-8824-42fdb7d3f6fd\\m20_s19_e2e_round1'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; & .venv\\Scripts\\python.exe -m pytest tests\\e2e\\test_workbench_v2_m17.py -q` -> 4 passed, 1 warning in 127.65s. RAN: `$testRoot = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\31\\019fb8d5-ccf2-7073-8824-42fdb7d3f6fd\\m20_s19_unit_round8'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; & .venv\\Scripts\\python.exe -m pytest tests\\test_extract_outline_m4.py tests\\test_generated_review_m20.py tests\\test_form_completeness_m20.py -q` -> 26 passed, 1 warning in 29.37s. Every declared focused file is covered; `tests/test_workbench_m15.py` was added because D5 requires it for any `workbench/` change.

**M20-S19 gate checkpoint (2026-07-31):** RAN: `.venv\\Scripts\\python.exe -m tax_graph.cli verify form-completeness --year 2025 --root .` -> report `output/m20_s19_form_completeness.yaml`, primary `28/28 (100.0%)`, instruction `55/68 (80.9%)`, secondary non-computed policy `83/185 (44.9%)`, policy plus form-face citation `17/185 (9.2%)`. RAN: `.venv\\Scripts\\python.exe tools\\check_ascii.py` -> `ASCII check OK`. RAN: `git diff --check` -> exit 0. RAN: `.venv\\Scripts\\python.exe -m tax_graph.cli validate 2025` -> graph integrity OK, 18 documents, 441 nodes, 401 citations. RAN: `.venv\\Scripts\\python.exe -m workbench.cli --root . --year 2025 preflight` -> passed, 18 entries, 2224 units, 2120 cells, `legacy_mined=394`. RAN: strict citation check with `check_graph_citations(year=2025, raw_store='.cache/raw', root='.')` -> `checked=401, strict_mismatches=36` (existing baseline). Protected graph and `review_verdicts/2025` diffs are empty.

**Worker session checkpoint - M20-S18 implementation (2026-07-31):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort/quota/context indicators are not
exposed by this environment. John gave go via the current task request. Single declared step:
make instruction citations optional for completeness, repair parent/lettered-child line
resolution fail-closed, and run non-computed source extraction. Applicable defect-ledger entries:
D9 and the exact RAN/NOT RUN evidence rule. No draft promotion, hand-authoring, live graph edit,
or operation enum change is in scope. Protected graph and live verdict artifacts are untouched
at session start.

**M20-S18 focused-test declaration (2026-07-31):** Declared files are
`tests/test_extract_outline_m4.py`, `tests/test_form_completeness_m20.py`,
`tests/test_generated_review_m20.py`, `tests/test_extract_m16.py`, `tests/test_cli.py`,
`tests/test_workbench_cells_api_m17.py`, and `tests/e2e/test_workbench_v2_m17.py`.
The set covers line resolution and source extraction, the optional-instruction completeness
metric, generated review projection, outline-pipeline consumers, the CLI report contract, and
the API/browser consumers whose rendered source identity changed under D9.

**M20-S18 pre-extraction checkpoint (2026-07-31):** Mechanical implementation is in place.
RAN: `PYTEST_DEBUG_TEMPROOT=<session writable root>; .venv\\Scripts\\python.exe -m pytest
tests/test_extract_outline_m4.py tests/test_form_completeness_m20.py -q` -> 19 passed, 1 warning
in 0.78s. Pending the expensive phase: draft-only extraction for `form_1040_2025`, then
generated-review projection and the remaining declared files. No live graph or verdict artifact
has been changed.

**M20-S18 deterministic implementation checkpoint (2026-07-31):** The completeness report now
uses `expression + form-face citation` as its primary metric and reports instruction coverage
separately. Formula assembly resolves a missing parent to a deterministic lettered child when
safe, expands explicit heading parents only for expandable operations, and records
`resolved_line_refs`; ambiguous or fixed-arity cases still fail closed. Non-formula source
records now resolve explicit information-return boxes and external form lines to stable source
ids, while unresolved declarations retain a named gap. No live artifacts have been changed.

**M20-S18 deterministic test evidence (2026-07-31):** RAN: `$testRoot =
'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\31\\019fb85a-5d3d-7fa0-9fad-4fd08fbc198d\\m20-s18-unit-tests-r5'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; & .venv\\Scripts\\python.exe -m pytest tests\\test_form_completeness_m20.py tests\\test_extract_outline_m4.py -q` -> 19 passed, 1 warning in 0.83s. The prior temp-root attempt was NOT RUN as evidence because the repository `.test_tmp` and `C:\\tmp` were ACL-blocked; no `--basetemp` was used.

**M20-S18 first live extraction attempt (2026-07-31):** RAN: `& .venv\\Scripts\\python.exe -m tax_graph.cli extract --doc form_1040_2025 --year 2025 --root .` -> exit 0 in 94.8s, but all 17 formula calls and 40 source calls recorded `LlmUnavailable: OpenRouter request failed: Connection error.` The resulting draft is explicit fail-closed gaps (`source_cells_succeeded=0`, `source_cells_failed=40`), not source-extraction evidence. This sandbox attempt is not acceptance evidence; retrying with approved network execution.

**M20-S18 approved-network extraction evidence (2026-07-31):** RAN twice, each with the exact
module-form command `& .venv\\Scripts\\python.exe -m tax_graph.cli extract --doc
form_1040_2025 --year 2025` -> first run exit 0 in 254.2s and second run exit 0 in 267.2s;
both reported `auto_accepted=0`, `human_review=173`, `deterministic_issues=122`. The latest
sidecar measures 40 non-formula source calls, 39 successful, 24 canonical source identities,
1 extraction failure, 32 complete source cells, and 8 explicit review gaps. W-2 box 1 and
Form 2441 line 26 resolve as `form_w2_2025_box_1` and `form_2441_2025_root_line_26`.
Unresolved or quote-invalid model responses remain named gaps. No draft was promoted.

**M20-S18 final evidence (2026-07-31):** RAN: `$testRoot =
'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\31\\019fb85e-d10c-7221-be78-0ade35a446d0\\m20_s18_final_tests';
New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT =
$testRoot; & .venv\\Scripts\\python.exe -m pytest tests/test_extract_outline_m4.py
tests/test_form_completeness_m20.py tests/test_generated_review_m20.py tests/test_extract_m16.py
tests/test_cli.py tests/test_workbench_m15.py -q` -> 38 passed, 1 warning in 46.35s.
RAN: `$testRoot = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\31\\019fb85e-d10c-7221-be78-0ade35a446d0\\m20_s18_workbench_consumers';
New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT =
$testRoot; & .venv\\Scripts\\python.exe -m pytest tests/test_workbench_cells_api_m17.py -q` ->
4 passed, 1 warning in 91.64s. RAN: `$testRoot =
'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\31\\019fb85e-d10c-7221-be78-0ade35a446d0\\m20_s18_e2e';
New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT =
$testRoot; & .venv\\Scripts\\python.exe -m pytest tests/e2e/test_workbench_v2_m17.py -q` ->
4 passed, 1 warning in 137.52s. RAN: `& .venv\\Scripts\\python.exe tools/check_ascii.py` ->
ASCII check OK; `git diff --check` -> exit 0. RAN: `& .venv\\Scripts\\python.exe -m
tax_graph.cli validate 2025` -> graph integrity OK, documents=18, nodes=441, tables=2,
edges=409, rules=17, citations=401, decisions=2, routing_edges=90, triggers=12,
expectations=4. RAN: `& .venv\\Scripts\\python.exe -m workbench.cli --root . --year 2025
preflight` -> exit 0, entries=18, units=2224, derived cells=2120, review_gap=591,
unreviewed=1529, legacy_mined=394. RAN strict citation reporting -> `checked=401,
strict_mismatches=36`. RAN: `& .venv\\Scripts\\python.exe -m tax_graph.cli verify
form-completeness --year 2025 --root .` -> `output/m20_s18_form_completeness.yaml`,
completeness 28/28 (100.0%), instruction coverage 55/68 (80.9%). Protected
`graph/2025/{nodes,edges,rules}/` and live `review_verdicts/2025` diffs are empty. No
verdict was written and no live graph artifact changed.

**M20-S18 post-implementation verification (2026-07-31):** RAN the required Schedule 1
draft-only command `& .venv\\Scripts\\python.exe -m tax_graph.cli extract --doc
schedule_1_2025 --year 2025 --root .` -> exit 0 in 31.3s; all four formula calls succeeded,
with `line 2 -> 2a` and `line 19 -> 19a` recorded in `resolved_line_refs` and no unresolved
line findings. RAN: `$testRoot =
'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\31\\019fb85a-5d3d-7fa0-9fad-4fd08fbc198d\\m20-s18-final-unit-r2'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; & .venv\\Scripts\\python.exe -m pytest tests\\test_form_completeness_m20.py tests\\test_extract_outline_m4.py -q` -> 19 passed, 1 warning in 0.86s.
RAN: `$testRoot = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\31\\019fb85a-5d3d-7fa0-9fad-4fd08fbc198d\\m20-s18-final-extra'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; & .venv\\Scripts\\python.exe -m pytest tests\\test_extract_m16.py tests\\test_cli.py -q` -> 10 passed, 1 warning in 18.86s.
RAN: `$testRoot = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\31\\019fb85a-5d3d-7fa0-9fad-4fd08fbc198d\\m20-s18-final-consumers-r2'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; & .venv\\Scripts\\python.exe -m pytest tests\\test_generated_review_m20.py tests\\test_workbench_cells_api_m17.py -q` -> 9 passed, 1 warning in 118.15s.
RAN: `$testRoot = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\31\\019fb85a-5d3d-7fa0-9fad-4fd08fbc198d\\m20-s18-final-e2e'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; & .venv\\Scripts\\python.exe -m pytest tests\\e2e\\test_workbench_v2_m17.py -q` -> 4 passed, 1 warning in 137.83s. All declared focused files are now verified; no `--basetemp` was used.

The approved 1040 rerun measured 17/17 formula calls, 39/40 successful source calls, 24
canonical source identities, and one named quote-mismatch gap; line 1a is
`form_w2_2025_box_1` and line 1e is `form_2441_2025_root_line_26`. The promoted graph,
verdict store, and protected graph directories remain byte-identical. The implementation is
already in the single local commit `6d957e1`; no push or promotion was performed.

**Worker session checkpoint - M20-S17 implementation (2026-07-31):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort/quota/context indicators are not
exposed by this environment. John gave go via the current task request. Single declared step:
attach instruction sections to their exact printed lines, split form-face and instruction-page
completeness telemetry, then tighten the generated review UX to a compact 1/3 list and 2/3
review pane with Accept/Reject, automatic machine attribution, and corrected generated policy
counts. Applicable defect-ledger entries: D4, D6, D9, D11, and the exact RAN/NOT RUN evidence
rule. No draft promotion, hand-authoring, live graph edit, rollover implementation, or operation
enum change is in scope. Protected graph and live verdict artifacts are untouched at session start.

**M20-S17 focused-test declaration (2026-07-31):** Declared files are
`tests/test_extract_outline_m4.py`, `tests/test_generated_review_m20.py`,
`tests/test_review_verdicts_m20.py`, `tests/test_workbench_cells_api_m17.py`,
`tests/test_workbench_write_api_m15.py`, `tests/test_workbench_m15.py`,
`tests/test_form_completeness_m20.py`, `tests/test_llm_attribution_m20.py`,
`tests/test_draft_route_m20.py`, `tests/test_batch_extraction_m10.py`,
`tests/test_schedule_d_extraction_m9.py`, `tests/test_nversion_m8.py`,
`tests/test_tables_detector_m6b.py`, `tests/test_cli.py`,
`tests/test_review_workbench_verdicts_m15.py`, `tests/test_review_schemas_m15.py`, and
`tests/e2e/test_workbench_v2_m17.py`. The additional verdict-history and schema consumers
are in scope because S17 changes the public verdict enum, reviewer attribution, and tag
fields. No new browser e2e file was authored.

**M20-S17 implementation evidence (2026-07-31):** The extraction pipeline now carries a
deterministic set of exact printed-line owners for each instruction span. A `## Line X`
heading owns its body through deeper headings until the next same-or-higher heading; table
rows such as `| 1z.` own only that row. Mention-only references remain excluded, and an
unowned mention is missing coverage rather than a false wrong-owner finding. The workbench
rebuilds the same ownership map locally so its projection cannot trust stale draft ids.
Completeness now reports form-face and instruction-page citation slots separately. Form 1040
measures 17 formula cells, 12 with both citation types, and 48/57 instruction-review lines
covered (11/57 before exact ownership); wrong-owner mentions measure 45. Schedule 1
measures 2/4 formula cells with both citation types and 4/4 instruction coverage; Schedule A
measures 3/7 and 3/7 respectively. The aggregate report is 17/28 formula cells with both
citations and 55/68 instruction-review lines covered. Generated policy counts are Form 1040:
`computed=14`, `copied=2`, `review_gap=40`, `user_entered=1`.

**M20-S17 UX evidence (2026-07-31):** The river is one compact line per cell with printed
anchor, short label, risk swatch/name, and Open/Accepted state. The selected review pane is
the 2/3 region; the list is the 1/3 region. Arithmetic is red, review gaps are amber-brown
and hatched, and the selected detail shows separate form-face and instruction-page sources.
The generated verdict surface has only Accept and Reject. Reject first focuses the comment
prompt; an empty second attempt asks `Reject without telling the pipeline why?`. A comment is
strongly encouraged but not mandatory. The typed reviewer field and old pipeline-defect /
source-pathology buttons are retired from the UI. The API records a machine/session reviewer
id containing OS, host, user, and a unique session token, plus an optional batch tag and
automatic UTC timestamp; comments and tags stay outside the address content fingerprint.

**M20-S17 browser checkpoint (2026-07-31):** RAN: `$testRoot =
'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\31\\019fb7f0-f003-7831-aae8-62bace7039b8\\m20_s17_e2e';
New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT =
$testRoot; & .venv\\Scripts\\python.exe -m pytest tests/e2e/test_workbench_v2_m17.py -q` ->
4 passed, 1 warning in 125.46s. A read-only in-app browser check selected Form 1040 line 22,
confirmed the compact 1/3 list and 2/3 detail pane, verified both source sections and the
Accept/Reject controls, focused the Reject comment prompt, and opened then dismissed the
empty-rejection confirmation. A screenshot was captured. No verdict was submitted to the
live ledger; the existing live server was used only for selection and the dismissed dialog.

**M20-S17 focused-test evidence (2026-07-31):** RAN: `$testRoot =
'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\31\\019fb7f0-f003-7831-aae8-62bace7039b8\\m20_s17_final_tests';
New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT =
$testRoot; & .venv\\Scripts\\python.exe -m pytest tests/test_extract_outline_m4.py
tests/test_generated_review_m20.py tests/test_review_verdicts_m20.py
tests/test_workbench_cells_api_m17.py tests/test_workbench_write_api_m15.py
tests/test_workbench_m15.py tests/test_form_completeness_m20.py tests/test_llm_attribution_m20.py
tests/test_draft_route_m20.py tests/test_batch_extraction_m10.py
tests/test_schedule_d_extraction_m9.py tests/test_nversion_m8.py tests/test_tables_detector_m6b.py
tests/test_cli.py tests/test_review_workbench_verdicts_m15.py -q` -> 81 passed, 1 skipped,
1 warning in 307.95s. RAN: `$testRoot =
'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\31\\019fb7f0-f003-7831-aae8-62bace7039b8\\m20_s17_schema_tests';
New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT =
$testRoot; & .venv\\Scripts\\python.exe -m pytest tests/test_review_schemas_m15.py -q` ->
7 passed, 1 warning in 0.46s. Every declared non-browser file is covered by one of these
exact commands. The first exploratory core sweep found five implementation failures and is
not acceptance evidence; the ownership parser, metric fixture, and projection were corrected
before the successful reruns above.

**M20-S17 machine evidence (2026-07-31):** RAN: `& .venv\\Scripts\\python.exe
tools/check_ascii.py` -> ASCII check OK; `git diff --check` -> exit 0; bundled Node syntax
checks for `workbench/static/river.js` and `workbench/static/app.js` -> exit 0. RAN:
`& .venv\\Scripts\\python.exe -m tax_graph.cli validate 2025` -> graph integrity OK,
documents=18, nodes=441, tables=2, edges=409, rules=17, citations=401, decisions=2,
routing_edges=90, triggers=12, expectations=4. RAN: `& .venv\\Scripts\\python.exe -m
workbench.cli --root . --year 2025 preflight` -> exit 0, entries=18, units=2224, derived
cells=2120, review_gap=591, unreviewed=1529, legacy_mined=394. RAN: `&
.venv\\Scripts\\python.exe -c "from tax_graph.acquire.citation_check import
check_graph_citations; report=check_graph_citations(year='2025', raw_store='.cache/raw',
root='.'); print(f'checked={report.checked}, strict_mismatches={len(report.mismatches)}')"`
-> checked=401, strict_mismatches=36. RAN: `& .venv\\Scripts\\python.exe -m tax_graph.cli
verify form-completeness --year 2025 --root .` -> report written to
`output/m20_s14_form_completeness.yaml`, aggregate completeness 17/28 (60.7%), aggregate
instruction coverage 55/68 (80.9%). Protected `graph/2025/{nodes,edges,rules}/` diff is
empty and live `review_verdicts/2025` diff is empty. No draft was promoted and no live graph
artifact changed. One local commit will contain this implementation and evidence; no push.

**Worker session checkpoint - M20-S16 implementation (2026-07-31):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort/quota/context indicators are not
exposed by this environment. John gave go via the current task request. Single declared step:
implement M20-S16 in order - fix operand roles and ordering, replace raw outline descriptions
with deterministic human-readable rendering, add non-computed-line draft review, move controls
into the review area, enforce rejection reasons, recolor risk buckets, correct policy counts,
and remeasure completeness. Applicable defect-ledger entries: D4, D6, D9, D11, and the exact
RAN/NOT RUN evidence rule. No draft promotion, hand-authoring, live graph edit, rollover
implementation, or operation-enum change is in scope.

**M20-S16 focused-test declaration (2026-07-31):** Declared files are
`tests/test_extract_outline_m4.py`, `tests/test_generated_review_m20.py`,
`tests/test_review_verdicts_m20.py`, `tests/test_workbench_cells_api_m17.py`,
`tests/test_workbench_write_api_m15.py`, `tests/test_workbench_m15.py`,
`tests/test_form_completeness_m20.py`, `tests/test_llm_attribution_m20.py`,
`tests/test_draft_route_m20.py`, `tests/test_batch_extraction_m10.py`,
`tests/test_schedule_d_extraction_m9.py`, `tests/test_nversion_m8.py`,
`tests/test_tables_detector_m6b.py`, `tests/test_cli.py`, and
`tests/e2e/test_workbench_v2_m17.py`. The set covers the producer prompt/assembly, generated
projection, rejection API, workbench boundary/API, completeness telemetry, all known
outline/micro consumers, and the existing browser consumer for the moved review controls. No
new browser e2e file is being authored in this round.

**M20-S16 producer/projection checkpoint (2026-07-31):** RAN: `& .venv\\Scripts\\python.exe -m
pytest tests/test_extract_outline_m4.py tests/test_batch_extraction_m10.py
tests/test_schedule_d_extraction_m9.py -q` -> 18 passed, 1 warning in 78.42s. RAN: `&
.venv\\Scripts\\python.exe -m pytest tests/test_generated_review_m20.py
tests/test_review_verdicts_m20.py -q` -> 17 passed, 1 warning in 59.25s. The first attempt
using `C:\\tmp` is NOT RUN as evidence because pytest could not create its temp root; the
successful reruns used the writable visualization root and no `--basetemp`. The current live
projection renders line 22 as `line 22 = line 18 - line 21`; no promoted graph artifact changed.
Next is the app-dependent API/write consumer command.

**M20-S16 API/schema checkpoint (2026-07-31):** RAN: `& .venv\\Scripts\\python.exe -m pytest
tests/test_workbench_cells_api_m17.py tests/test_workbench_write_api_m15.py
tests/test_workbench_m15.py -q` -> 13 passed, 1 warning in 141.43s. RAN a read-only
generated-expression schema validation over all 57 Form 1040 projected cells -> 57 validated.
RAN a synthetic-reviewer verdict probe against the generated line-22 expression -> append-only
JSONL record validated in an isolated visualization directory; no real ledger or graph artifact
was touched. The rejection API now requires reason code plus non-empty comment for both rejection
routes. Next is the final declared focused set.

**M20-S16 browser checkpoint (2026-07-31):** RAN the local in-app browser against an isolated
workbench state and verdict directory under
`C:\Users\\devbox\\.codex\\visualizations\\2026\\07\\31\\019fb788-e07c-7d52-bdf6-1e3c44ef7df2\\m20_s16_browser`.
Form 1040 rendered 57 review cards; selected line 22 displayed `line 22 = line 18 - line 21`,
four verdict controls, and no card inputs/textareas. A rejection without a comment was blocked;
the same synthetic reviewer then recorded `pipeline_defect` with a reason comment to the isolated
JSONL store. Form 8949 verified that ordinary-cell approve/note controls live in the selected-cell
review area and that the card itself has zero controls; isolated session progress reached `1 / 202`.
No live verdict or graph artifact changed. RAN: `$testRoot =
'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\31\\019fb788-e07c-7d52-bdf6-1e3c44ef7df2\\m20_s16_e2e_r3';
New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT =
$testRoot; & .venv\\Scripts\\python.exe -m pytest tests/e2e/test_workbench_v2_m17.py -q` ->
4 passed, 1 warning in 126.17s. The existing browser consumer was updated for the moved controls;
no new browser e2e file was authored.

**M20-S16 final focused-test evidence (2026-07-31):** RAN: `$testRoot =
'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\31\\019fb788-e07c-7d52-bdf6-1e3c44ef7df2\\m20_s16_final_tests_r2';
New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT =
$testRoot; & .venv\\Scripts\\python.exe -m pytest tests/test_extract_outline_m4.py
tests/test_generated_review_m20.py tests/test_review_verdicts_m20.py
tests/test_workbench_cells_api_m17.py tests/test_workbench_write_api_m15.py
tests/test_workbench_m15.py tests/test_form_completeness_m20.py tests/test_llm_attribution_m20.py
tests/test_draft_route_m20.py tests/test_batch_extraction_m10.py
tests/test_schedule_d_extraction_m9.py tests/test_nversion_m8.py tests/test_tables_detector_m6b.py
tests/test_cli.py -q` -> 71 passed, 1 skipped, 1 warning in 306.51s. Every declared focused
file is covered by this exact command plus the browser command above; no `--basetemp` was used.

**M20-S16 final machine evidence (2026-07-31):** RAN: `& .venv\\Scripts\\python.exe
tools/check_ascii.py` -> ASCII check OK; `git diff --check` -> exit 0; strict citation command ->
`checked=401 strict_mismatches=36`; module-form `tax_graph.cli validate 2025` -> graph integrity
OK, documents=18, nodes=441, tables=2, edges=409, rules=17, citations=401, decisions=2,
routing_edges=90, triggers=12, expectations=4; module-form `workbench.cli --root . --year 2025
preflight` -> exit 0, entries=18, units=2224, derived cells=2120, review_gap=591,
unreviewed=1529, legacy_mined=394. Protected `graph/2025/{nodes,edges,rules}/` diff is empty,
and live `review_verdicts/2025` has no diff. No draft promotion or live graph artifact changed.

**Worker session checkpoint - M20-S14 implementation (2026-07-30):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort/quota/context indicators are not
exposed by this environment. John gave go via the current task request. Single declared step:
retire the handcrafted expression set as a score while retaining its diff as a review flag,
measure completeness against all formula-bearing lines, complete Form 1040, Schedule 1, and
Schedule A through draft-only generation with explicit review gaps, fix instruction-span
ownership, and resolve printed line references deterministically. Applicable defect-ledger
entries: D4, D6, D9, D11, and the exact RAN/NOT RUN evidence rule. No draft promotion,
hand-authoring, live graph edit, rollover implementation, review-contract change, UI change, or
operation-enum change is in scope.

**Worker session checkpoint - M20-S15 implementation (2026-07-30):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort/quota/context indicators are not
exposed by this environment. John gave go via the current task request. Single declared step:
fix the geometry outline's lettered sub-lines, make instruction-span ownership contextual, and
put the generated draft cells and verdict/comment controls in the review surface. Applicable
defect-ledger entries: D4, D5, D6, D9, D11, and the exact RAN/NOT RUN evidence rule. Declared
focused files: the outline tests, generated-review tests, review-verdict tests, workbench API
write/cell tests, workbench boundary tests, and any authored browser test. No draft promotion,
hand-authored expression/citation, live graph edit, or push is in scope.

**M20-S15 implementation result (2026-07-30):** The geometry header classifier now preserves
lettered rows whose captions mention a section. The outline-first micro prompt receives a
bounded neighboring form-line window, and instruction bodies inherit only their nearest
explicit line heading. Draft-only regeneration produced Form 1040 `17/17` complete, Schedule
1 `2/4` complete with explicit unresolved-source gaps for lines `2` and `19`, and Schedule A
`7/7` complete. Wrong-owner instruction spans fell from the prior `146` total to `139`
(`88` Form 1040, `37` Schedule 1, `14` Schedule A). No live graph artifact was edited.

**M20-S15 generated review surface (2026-07-30):** RAN: generated workbench projection ->
`17 + 4 + 7 = 28` draft-only formula cells, each carrying resolved model
`google/gemini-3.6-flash` and provider `Google AI Studio`. The right pane keeps the generated
expression, form-face citation slot, instruction-page citation slot, provenance, reviewer id,
comment, and the four verdict controls together. `POST /api/verdicts` accepts the optional
comment and mirrors generated address verdicts into the append-only JSONL ledger without
including the comment in `content_fingerprint`.

**M20-S15 browser verification (2026-07-30):** RAN in the local in-app browser against the
workbench server. Selected Form 1040 generated cell `1z`, confirmed the expression, separate
source slots, model/provider provenance, and enabled `Confirm`, `Pipeline defect`, `Source
pathology`, and `Save and next` controls. Entered reviewer `john` and comment `Generated
formula source is clear; confirming for pipeline review.` and submitted `Confirm`. The real
record landed at `review_verdicts/2025/address_verdicts.jsonl`; the review surface screenshot
was captured in the session.

**M20-S15 final focused-test evidence (2026-07-30):** RAN: `$testRoot =
'C:\Users\devbox\.codex\visualizations\2026\07\30\019fb4c9-2688-7903-a6dd-abd1329cbfd0\m20_s15_tests_final';
New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT =
$testRoot; & .venv\Scripts\python.exe -m pytest tests/test_extract_outline_m4.py
tests/test_generated_review_m20.py tests/test_review_verdicts_m20.py
tests/test_workbench_cells_api_m17.py tests/test_workbench_write_api_m15.py
tests/test_workbench_m15.py tests/test_form_completeness_m20.py tests/test_llm_attribution_m20.py
tests/test_draft_route_m20.py tests/test_batch_extraction_m10.py
tests/test_schedule_d_extraction_m9.py tests/test_nversion_m8.py tests/test_tables_detector_m6b.py
tests/test_cli.py -q` -> 69 passed, 1 skipped, 1 warning in 289.90s. Every declared focused
file is covered by this exact command; no browser e2e file was authored.

**M20-S15 final machine evidence (2026-07-30):** RAN: `& .venv\Scripts\python.exe
tools/check_ascii.py` -> ASCII check OK; `git diff --check` -> exit 0; module-form
`tax_graph.cli validate 2025` -> graph integrity OK, documents=18, nodes=441, tables=2,
edges=409, rules=17, citations=401; module-form `workbench.cli --root . --year 2025 preflight`
-> exit 0, entries=18, units=2224, derived cells=2120, review_gap=591, unreviewed=1529,
legacy_mined=394; direct strict citation report -> checked=401, strict_mismatches=36.
Protected `graph/2025/{nodes,edges,rules}/` diff is empty. One local commit contains this
implementation and the durable review verdict; no push was performed.

**M20-S14 final focused-test evidence (2026-07-30):** RAN: `$testRoot =
'C:\Users\devbox\.codex\visualizations\2026\07\30\019fb499-a143-7863-b5f8-8429b9be8574\m20_s14_tests_final_r2';
New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT =
$testRoot; & .venv\Scripts\python.exe -m pytest tests/test_extract_outline_m4.py
tests/test_form_completeness_m20.py tests/test_llm_attribution_m20.py tests/test_draft_route_m20.py
tests/test_batch_extraction_m10.py tests/test_schedule_d_extraction_m9.py tests/test_nversion_m8.py
tests/test_tables_detector_m6b.py tests/test_cli.py -q` -> 40 passed, 1 skipped, 1 warning in
96.28s. Every declared focused file is covered by this exact command. The initial plain pytest
attempt is NOT RUN as evidence because the repository `.test_tmp` root failed with WinError 5;
the final command used the writable per-session `PYTEST_DEBUG_TEMPROOT` without `--basetemp`.

**M20-S14 final live measurement (2026-07-30):** RAN, with approved network execution, one
exact module-form draft-only command each for `form_1040_2025`, `schedule_1_2025`, and
`schedule_a_2025`, followed by `& .venv\Scripts\python.exe -m tax_graph.cli verify
form-completeness --year 2025 --root .`. All three run envelopes ended success. The report
`output/m20_s14_form_completeness.yaml` measures 24/28 formula cells complete (expression plus
verbatim citation): Form 1040 17/17, Schedule 1 0/4 with four explicit unresolved-line review
gaps (`8n`, `2`, `24f`, `19`), and Schedule A 7/7. There were zero expression-without-citation
cells. All successful calls resolved to `google/gemini-3.6-flash` via Google AI Studio. The
handcrafted comparison remains under `handcrafted_diff.flag_only: true` and is not an accuracy
score. The final per-form telemetry is: Form 1040 17 calls, 11,642 total tokens, cost
0.070221; Schedule 1 4 calls, 2,989 total tokens, cost 0.0172335; Schedule A 7 calls, 3,669
total tokens, cost 0.0217455.

**M20-S14 final machine gates (2026-07-30):** RAN after the final code and draft measurement:
`& .venv\Scripts\python.exe tools/check_ascii.py` -> ASCII check OK; `git diff --check` ->
exit 0; module-form `tax_graph.cli validate 2025` -> graph integrity OK, documents=18,
nodes=441, tables=2, edges=409, rules=17, citations=401; module-form
`workbench.cli --root . --year 2025 preflight` -> exit 0, entries=18, units=2224,
derived cells=2120, review_gap=591, unreviewed=1529, legacy_mined=394; strict citation
report -> checked=401, strict_mismatches=36. Protected `graph/2025/{nodes,edges,rules}/`
diff is empty. One local commit contains the implementation, focused tests, report tooling, and
this evidence; no push.

**Worker session checkpoint - M20-S13 implementation (2026-07-30):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort/quota/context indicators are not
exposed by this environment. John gave go via the current task request. Single declared step:
replace the per-cell expression prompt with the human question, return source line numbers and
required quote, resolve identities deterministically with fail-closed findings, add target-cell
and normal-level request/response logging, then measure Form 1040 and the 15-form draft-only run.
Applicable defect-ledger entries: D4, D6, D9, D11, and the exact RAN/NOT RUN evidence rule. No
operation-enum change, node-id model vocabulary, draft promotion, hand-authoring, live graph
edit, rollover implementation, review-contract change, or UI change is in scope.

**M20-S13 focused-test declaration (2026-07-30):** Declared files are
`tests/test_extract_outline_m4.py`, `tests/test_llm_attribution_m20.py`,
`tests/test_draft_route_m20.py`, `tests/test_batch_extraction_m10.py`,
`tests/test_schedule_d_extraction_m9.py`, and `tests/test_cli.py`. They cover the micro prompt
and line-index consumer, telemetry/logging and draft provenance, batch and Schedule D consumers,
and the expression-agreement CLI. Final evidence for every declared file will be recorded below.
The consumer sweep additionally declares `tests/test_nversion_m8.py` and
`tests/test_tables_detector_m6b.py` because both exercise the outline micro route.

**M20-S13 pre-live checkpoint (2026-07-30):** The implementation is green on the declared
focused command plus the two additional micro consumers. RAN: `$testRoot =
'C:\Users\devbox\.codex\visualizations\2026\07\30\019fb469-6d33-7d61-a2d5-eddcf974c9b1\m20_s13_tests_r4';
New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT =
$testRoot; & .venv\Scripts\python.exe -m pytest tests/test_extract_outline_m4.py
tests/test_llm_attribution_m20.py tests/test_draft_route_m20.py tests/test_batch_extraction_m10.py
tests/test_schedule_d_extraction_m9.py tests/test_cli.py -q` -> 29 passed, 1 warning in 95.99s;
the additional `tests/test_nversion_m8.py tests/test_tables_detector_m6b.py` command -> 7 passed,
1 skipped, 1 warning in 2.01s. No protected graph directories changed. The retained table-specific
path is explicit for transaction-table/totals nodes; ordinary formula lines use the new shape.
The next command is the single Form 1040 draft-only live diagnostic, followed by log inspection.

**M20-S13 Form 1040 exchange (2026-07-30):** The final successful 1z micro exchange is
recorded here so John can inspect exactly what the model saw and returned. The JSONL source is
`output/logs/f59672d67d1544d18fa57e61a6e6a53b.jsonl`; `target_cell_id` is
`form_1040_2025_root_line_1z`.

Request prompt:
```text
Answer the human question for one form line.
Which printed lines does this line use, and what operation combines them?
Return operation, source_lines, and quote.
Use the form's printed line numbers in source_lines, never internal ids.

target line label: z Add lines 1a through 1h 1z

form face line:
z Add lines 1a through 1h 1z

instruction text:
|  ** Earned income includes wages, salaries, tips, professional fees, and other compensation received for personal services you performed. It also includes any taxable scholarship or fellowship grant. Generally, your earned income is the total of the amount(s) you reported on Form 1040 or 1040-SR, line 1z, and Schedule 1, lines 3, 6, 8r, 8t, and 8u minus the amount, if any, on Schedule 1, line 15.*  |   |
1. Enter the amount from Form 1040 or 1040-SR, line 1z ... 1. \_\_\_\_\_
Check the box on line 27b if you are (1) a minister, member of a religious order who has not taken a vow of poverty, or a Christian Science practitioner; and (2) filing Schedule SE and the amount on line 2 of that schedule includes an amount that was also reported on Form 1040 or 1040-SR, line 1z. See the instructions under Clergy, later, for how to determine the amount of your earned income.
```

Response content:
```json
{"operation":"SUM","source_lines":["1a","1b","1c","1d","1e","1f","1g","1h"],"quote":"Add lines 1a through 1h"}
```

Response telemetry: `finish_reason=stop`, `model=google/gemini-3.6-flash`,
`provider=Google AI Studio`, `prompt_tokens=354`, `completion_tokens=333`, `total_tokens=687`,
`cost=0.0030285`. The answer has the correct eight source lines and is resolved by code to
deterministic node ids; no internal id was sent to the model.

**M20-S13 final focused-test evidence (2026-07-30):** RAN: `$testRoot =
'C:\Users\devbox\.codex\visualizations\2026\07\30\019fb469-6d33-7d61-a2d5-eddcf974c9b1\m20_s13_tests_final_r2';
New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT =
$testRoot; & .venv\Scripts\python.exe -m pytest tests/test_extract_outline_m4.py
tests/test_llm_attribution_m20.py tests/test_draft_route_m20.py tests/test_batch_extraction_m10.py
tests/test_schedule_d_extraction_m9.py tests/test_cli.py tests/test_nversion_m8.py
tests/test_tables_detector_m6b.py -q` -> 36 passed, 1 skipped, 1 warning in 96.57s. Every
declared focused file is covered by that exact command. The skip is the existing guarded
environment-dependent test; no declared file is unverified.

**M20-S13 final live measurement (2026-07-30):** The sandbox-only Form 1040 command is NOT
RUN as final evidence: all 17 requests failed with a connection error before provider response.
RAN with approved network execution: the final Form 1040 command
`& .venv\Scripts\python.exe -m tax_graph.cli extract --doc form_1040_2025 --year 2025 --root .`
completed with 17/17 provider successes, no truncation, resolved model
`google/gemini-3.6-flash`, provider `Google AI Studio`. The cell result was 16 assembled
successes and 1 fail-closed self-reference finding. The final 1040 run averaged 273.5 prompt
tokens (range 127-499), with 1z at 354 tokens; its prompts were 432-1713 characters, average
936.7. Form 1040 expression report: coverage 10/80 (12.5%),
operation accuracy 8/10, full expression accuracy 2/10, `extra_in_draft=65`.

**M20-S13 15-form draft-only measurement (2026-07-30):** RAN in parallel, one exact
module-form command per manifest form document:
`& .venv\Scripts\python.exe -m tax_graph.cli extract --doc <document_id> --year 2025 --root .`.
All 15 run envelopes ended `success`; the set made 74 micro calls, 74 provider successes,
0 provider failures, 0 truncations, and 57 assembled cell successes with 17 fail-closed
identity findings/failures. Resolved model was `google/gemini-3.6-flash`; provider was
`Google AI Studio`. Prompt tokens fell from the prior S12 average/max 888.6/1542 to
247.3/596 in this round; current prompt chars averaged 858.9 with a 2280 maximum. Final
expression report: coverage 7/80 (8.8%), operation accuracy 5/7, full expression accuracy
2/7, `extra_in_draft=50`. The lower coverage is honest model variance plus fail-closed
identity resolution; no node id was requested from the model and no unresolved id was
fabricated.

**M20-S13 final machine gates (2026-07-30):** RAN: `& .venv\Scripts\python.exe
tools/check_ascii.py` -> ASCII check OK; `git diff --check` -> exit 0; module-form
`tax_graph.cli validate 2025` -> graph integrity OK, documents=18, nodes=441, tables=2,
edges=409, rules=17, citations=401; module-form `workbench.cli --root . --year 2025 preflight`
-> exit 0, entries=18, units=2224, derived cells=2120, review_gap=591, unreviewed=1529,
legacy_mined=394; strict citation command -> checked=401, strict_mismatches=36. Protected
`graph/2025/{nodes,edges,rules}/` diff is empty. The tracked
`output/m20_s8_expression_agreement.yaml` contains the final 15-form report. The single local
commit was created; its final hash is reported in the Worker response. No push was performed.

**Worker session checkpoint - M20-S12 implementation (2026-07-30):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort/quota/context indicators are not
exposed by this environment. John gave go via the current task request. Single declared step:
route expression derivation through the per-cell micro path, isolate failed cells, keep the
response cap at 4000, then measure Form 1040 and the 15-form draft-only run. Applicable
defect-ledger entries: D4, D6, D9, D11, and the exact RAN/NOT RUN evidence rule. No prompt
tuning beyond per-cell scoping, operation-enum change, draft promotion, hand-authoring, live
graph edit, rollover implementation, review-contract change, or UI change is in scope.

**M20-S12 pre-write checkpoint (2026-07-30):** The existing micro path is real but only visits
`transaction_table` and `totals` outline nodes. Geometry-derived Form 1040 has 60 outline rows
and zero such nodes, which explains S11's clean `calls=0`. The implementation will add a
deterministic formula-cue selector for line cells, include form/instruction spans plus stable
same-form operand candidates in each prompt, read `extraction.micro_max_tokens`, and persist
attempt/success/failure counts and failure reasons beside the draft metrics. The protected live
graph remains untouched.

**M20-S12 focused fast verification checkpoint (2026-07-30):** The first two pytest setup
attempts were NOT RUN as evidence: the repository `.test_tmp` root and then `C:\tmp` both
failed with ACL errors before collection. Final RAN: `$testRoot =
'C:\Users\devbox\.codex\visualizations\2026\07\30\019fb406-787b-7021-ab13-29c97ba76e82\m20_s12_tests';
New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT =
$testRoot; & .venv\Scripts\python.exe -m pytest tests/test_extract_outline_m4.py
tests/test_schedule_d_extraction_m9.py -q` -> 12 passed, 1 warning in 7.10s. The next
checkpoint is before the live Form 1040 diagnostic; no protected graph directories changed.

**M20-S12 pre-live checkpoint (2026-07-30):** The focused implementation consumers are green.
The ignored local config remains `openrouter` with concrete `google/gemini-3.6-flash`, strict
schema and required parameters, unpinned routing with fallbacks enabled, and
`extraction.micro_max_tokens: 4000`. The next command is the single Form 1040 draft-only
diagnostic. Its expected spend is materially above the prior zero-call run but should remain
small because the prompt is one cell at a time; the 15-form run will only start after its call,
success, token, cost, resolved-model, and failure metrics are inspected. No protected graph
directories or committed artifacts have been changed.

**M20-S12 Form 1040 live measurement (2026-07-30):** The first sandbox-only live attempt is
NOT RUN as final evidence: 17 per-cell requests all hit `OpenRouter request failed: Connection
error` and produced no expressions. RAN outside the sandbox with the pinned concrete
`google/gemini-3.6-flash`: after tightening the operand packet, `cells_attempted=17`,
`cells_succeeded=17`, `cells_failed=0`; no `finish_reason=length` occurred. Resolved providers
were Google and Google AI Studio. `verify expression-agreement` measured Form 1040 coverage
6/20 (30.0%), operation accuracy 5/6, full expression accuracy 0/6. The report-wide snapshot
is 10/80 coverage (12.5%), operation accuracy 9/10, full expression accuracy 0/10. The live
graph directories remain byte-identical. The 15-form command is next; local config now permits
15 documents and disables example mining for this draft-only expression measurement.

**M20-S12 focused-test declaration (2026-07-30):** Declared files are
`tests/test_extract_outline_m4.py`, `tests/test_schedule_d_extraction_m9.py`,
`tests/test_batch_extraction_m10.py`, `tests/test_draft_route_m20.py`,
`tests/test_llm_attribution_m20.py`, and `tests/test_cli.py`. They cover formula-cell selection,
bounded micro prompts, failure isolation, draft metrics/provenance, batch consumers, and the
expression-agreement CLI. Final evidence for every file will be recorded below.

**M20-S12 final focused-test evidence (2026-07-30):** RAN: `$testRoot =
'C:\Users\devbox\.codex\visualizations\2026\07\30\019fb406-787b-7021-ab13-29c97ba76e82\m20_s12_tests_final_r3';
New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT =
$testRoot; & .venv\Scripts\python.exe -m pytest tests/test_extract_outline_m4.py
tests/test_schedule_d_extraction_m9.py tests/test_batch_extraction_m10.py
tests/test_draft_route_m20.py tests/test_llm_attribution_m20.py tests/test_cli.py -q` -> 27
passed, 1 warning in 93.27s. Every declared focused file is covered by that exact command.
The prior consumer run found and corrected the model-node boundary regression; this final rerun
is the evidence after the correction.

**M20-S12 final measurement (2026-07-30):** RAN the exact module-form per-document command
`& .venv\Scripts\python.exe -m tax_graph.cli extract --doc <document_id> --year 2025 --root .`
for all 15 manifest form documents in parallel, with `example_mining_limit=0` and
`expression_mode=none`. All 15 exited 0. The final drafts record 74 cells attempted, 74
succeeded, 0 failed; no per-cell truncation occurred. The resolved model was
`google/gemini-3.6-flash`; providers were Google and Google AI Studio. RAN:
`& .venv\Scripts\python.exe -m tax_graph.cli verify expression-agreement --year 2025 --root .`
-> coverage 11/80 (13.8%), operation accuracy 9/11 (81.8%), full expression accuracy 0/11.
Form 1040 alone is 6/20 coverage (30.0%), operation accuracy 5/6, full expression accuracy
0/6. The sequential 15-form attempt exceeded the 600-second cap and is NOT RUN as final
evidence; the final per-document parallel run completed the same manifest set.

**M20-S12 final machine gates (2026-07-30):** RAN: `& .venv\Scripts\python.exe
tools/check_ascii.py` -> ASCII check OK; `git diff --check` -> exit 0; module-form
`tax_graph.cli validate 2025` -> graph integrity OK, documents=18, nodes=441, tables=2,
edges=409, rules=17, citations=401; module-form `workbench.cli --root . --year 2025 preflight`
-> exit 0, entries=18, units=2224, derived cells=2120, review_gap=591, unreviewed=1529,
legacy_mined=394; strict citation command -> checked=401, strict_mismatches=36. Protected
`graph/2025/{nodes,edges,rules}/` diff is empty. A single local commit was created for this
step; no push has been performed.

**Worker session checkpoint - M20-S11 implementation (2026-07-30):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort/quota/context indicators are not
exposed by this environment. John gave go via the current task request. Single declared step:
verify `x-ai/grok-4.5`, run the pinned Form 1040 draft-only diagnostic, and if the provider/model
fails, switch in the same session to the verified concrete `google/gemini-2.5-flash` fallback,
then run the 15-form draft-only baseline and separate expression coverage/accuracy report.
Applicable defect-ledger entries: D4, D6, D8, D9, D11, and the exact RAN/NOT RUN evidence rule.
No prompt tuning, operation-enum change, draft promotion, hand-authoring, live graph edit,
rollover implementation, review-contract change, or UI change is in scope.

**M20-S11 focused-test declaration (2026-07-30):** Declared files are
`tests/test_extract_m4.py`, `tests/test_llm_attribution_m20.py`, `tests/test_draft_route_m20.py`,
`tests/test_extract_outline_m4.py`, `tests/test_batch_extraction_m10.py`,
`tests/test_schedule_d_extraction_m9.py`, `tests/test_trust_tiers_m8.py`, and `tests/test_cli.py`.
They cover the provider routing, telemetry/provenance, draft/metrics, outline, batch, Schedule D,
trust-tier, and CLI consumers touched by the diagnostic configuration. Each file will have exact
final `RAN:` or `NOT RUN:` evidence below.

**M20-S11 pre-live checkpoint (2026-07-30):** The read-only OpenRouter model-list query verified
`x-ai/grok-4.5` (context 500000) and selected `google/gemini-2.5-flash` (context 1048576) as the
concrete fallback. The ignored local config now uses Grok, leaves provider routing unpinned with
`allow_fallbacks=true`, and retains `require_parameters=true`, `strict_schema=true`,
`max_tokens=24000`, and generator expression mode. Protected graph directories are clean.
The next command is the one-document draft-only diagnostic; provider failure is not a stop
condition for this round because the verified Flash fallback is available.

**M20-S11 Grok result (2026-07-30):** RAN: `& .venv\Scripts\python.exe -m tax_graph.cli
extract --doc form_1040_2025 --year 2025 --root .` -> exit 1 after the request reached xAI.
OpenRouter retained a provider-side HTTP 400: xAI rejected the strict schema because several
`$id` values were not URI references and local `$defs` references were unresolved. The log
records requested `x-ai/grok-4.5`, resolved `x-ai/grok-4.5-20260708`, and provider `xAI`.
No draft or promoted artifact was written. This is the permitted provider/model failure for
S11, so no schema or parameter relaxation was attempted; the ignored config is now pinned to
the verified concrete `google/gemini-2.5-flash`, with routing still unpinned and fallbacks on.
The next command is the same one-document draft-only diagnostic on Flash.

**M20-S11 fallback selection update (2026-07-30):** John selected the verified concrete
`google/gemini-3.6-flash` model instead of `google/gemini-2.5-flash`. The in-flight 2.5 Flash
diagnostic was terminated before completion and is NOT RUN as evidence. The ignored config now
pins 3.6 Flash; strict schema, required parameters, unpinned provider routing, and fallbacks
remain unchanged. The next command is the one-document draft-only diagnostic on 3.6 Flash.

**M20-S11 3.6 Flash result (2026-07-30):** RAN: `& .venv\Scripts\python.exe -m tax_graph.cli
extract --doc form_1040_2025 --year 2025 --root .` -> exit 1 after 145.3s. Gemini 3.6 reached
the provider but the structured response was truncated at the unchanged hard cap:
`finish_reason=length`, `completion_tokens=23937`, `max_tokens=24000`. No draft or promoted
artifact was written, and no schema/parameter relaxation was attempted. John-selected 3.6 was
therefore not usable for this diagnostic. The next same-session safety fallback is the already
verified concrete `google/gemini-2.5-flash`; strict schema, required parameters, unpinned routing,
and generator expression mode remain unchanged.

**M20-S11 Flash-cap diagnosis (2026-07-30):** RAN: the same one-document command on concrete
`google/gemini-2.5-flash` -> exit 1 after 131.7s with `finish_reason=length` and
`completion_tokens=23911`; it reproduced the 3.6 result (`completion_tokens=23937`). Neither
attempt wrote a draft or promoted artifact. The repeated boundary identifies the 24000 response
cap, not a provider route failure, as the immediate blocker. Per the one-stop config and without
loosening strict schema or required parameters, `max_tokens` is now raised to 48000 and the
ignored config is restored to John's selected concrete `google/gemini-3.6-flash`. The next
command is a fresh one-document diagnostic on 3.6 with the higher response budget.

**M20-S11 bundling diagnosis (2026-07-30):** The assembled generator prompt includes the full
rendered document, field grid, links, related sources, schema summary, and asks for all graph
kinds in one response. The outline-first pipeline already has a narrow `tax_graph_micro_formula`
call per formula outline node, carrying only that node and its candidate spans, but then the
`expression_mode=generator` branch redundantly calls the whole-document generator. The 24k
truncations came from that broad route, not from a paragraph-sized instruction lookup. Per
John's direction, the ignored config now sets `expression_mode=none`, restores `max_tokens=24000`,
and bounds the per-cell `micro_max_tokens` at 4000. The next diagnostic will exercise only the
cell-context micro path and deterministic assembly; no full-document generator call is allowed.

**M20-S11 cell-scoped diagnostic result (2026-07-30):** RAN: `& .venv\Scripts\python.exe -m
tax_graph.cli extract --doc form_1040_2025 --year 2025 --root .` -> exit 0 in 8.4s. The run
used `expression_mode=none`, produced only the outline-first deterministic draft, and logged
`calls=0`, `successful_calls=0`, `failed_calls=0`; the draft summary was `auto_accepted=0`,
`human_review=107`, `deterministic_issues=121`. No whole-document generator call occurred and
the protected graph was untouched. This is the first clean diagnostic of the bounded path.
The originally requested 15-form expression baseline is NOT RUN under this configuration because
expression generation is intentionally disabled; a zero-expression report would measure the
configuration switch, not model coverage.

**M20-S11 focused-test evidence (2026-07-30):** RAN: `$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\30\019fb3ea-8b2f-7dd2-a118-ff0938733d14\m20-s11-cell-tests'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests/test_extract_m4.py tests/test_llm_attribution_m20.py tests/test_draft_route_m20.py tests/test_extract_outline_m4.py tests/test_batch_extraction_m10.py tests/test_schedule_d_extraction_m9.py tests/test_trust_tiers_m8.py tests/test_cli.py -q` -> 58 passed, 1 warning in 103.04s. All declared files are covered by that exact command.

**Worker session checkpoint - M20-S10 implementation (2026-07-30):** Global canary: Ledger
Llama. Phase canary: Ground Truth. John gave go via the current task request. Single declared
step: verify current OpenRouter raw routing fields, expose provider routing and router metadata
in config, carry the resolved provider through telemetry/provenance/metrics, pin the ignored local
config to `decart` plus `fp4` with fallbacks disabled and strict parameter requirements, then run
the Form 1040 diagnostic and the 15-form draft-only baseline with separate coverage and accuracy.
Applicable defect-ledger entries: D4, D6, D8, D9, D11, and the exact RAN/NOT RUN evidence rule.
No prompt tuning, model swap, operation-enum change, draft promotion, hand-authoring, live graph
edit, rollover implementation, review-contract change, or UI change is in scope.

**M20-S10 focused-test declaration (2026-07-30):** Declared files are
`tests/test_extract_m4.py`, `tests/test_llm_attribution_m20.py`, `tests/test_draft_route_m20.py`,
`tests/test_extract_outline_m4.py`, `tests/test_batch_extraction_m10.py`,
`tests/test_schedule_d_extraction_m9.py`, `tests/test_trust_tiers_m8.py`, and `tests/test_cli.py`.
They cover the raw OpenRouter routing contract, resolved-provider telemetry/provenance, and all
consumer paths touched by the attribution shape. Each file will have exact final `RAN:` or
`NOT RUN:` evidence below; the local config and live graph remain protected.

**M20-S10 implementation checkpoint (2026-07-30):** Provider routing now emits the raw
OpenRouter `order`, `only`, `ignore`, `allow_fallbacks`, `quantizations`, and
`require_parameters` fields from `llm.provider_routing` / `llm.require_parameters`. The
`X-OpenRouter-Metadata: enabled` response envelope is requested by default for OpenRouter.
Selected provider identity flows through `LlmCallTelemetry`, JSONL calls, draft provenance,
and `metrics.yaml`; the run envelope records the routing preferences. The ignored local config
is pinned to `z-ai/glm-5.2`, `only/order=[decart]`, `allow_fallbacks=false`, `quantizations=[fp4]`,
`require_parameters=true`, and generator expression mode. No live graph artifact was edited.

**M20-S10 live diagnostic result (2026-07-30):** The sandbox-only attempt is NOT RUN as
pipeline evidence because socket access failed with `WinError 10013`. RAN with approved network
execution: `& .venv\Scripts\python.exe -m tax_graph.cli extract --doc form_1040_2025 --year 2025 --root .`
-> exit 1 after 9.2s with `LlmUnavailable: OpenAI response did not contain choices`; the retained
provider body is `502 Upstream error from Decart: Internal server error`. The log is
`output/logs/9409b7ad5450434aad089a7a03f83894.jsonl` and records the exact hard route, strict
schema request, 24000-token cap, and no fallback. No draft was written. Per the stop condition,
the provider was not retried, constraints were not loosened, the model was not swapped, and the
15-form baseline plus expression-agreement report are NOT RUN.

**M20-S10 focused-test evidence (2026-07-30):** RAN: `$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\30\019fb3c8-07f0-72f2-8a3a-a79a9e082e17\m20-s10-tests-r2'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests/test_extract_m4.py tests/test_llm_attribution_m20.py tests/test_draft_route_m20.py tests/test_extract_outline_m4.py tests/test_batch_extraction_m10.py tests/test_schedule_d_extraction_m9.py tests/test_trust_tiers_m8.py tests/test_cli.py -q` -> 58 passed, 1 warning in 105.88s. The first sweep was NOT RUN as final evidence because it found the test fixture omitted the new optional `resolved_provider` field; the fixture was corrected and the final rerun above passed. All declared files are covered by that exact command.

**M20-S10 final machine evidence (2026-07-30):** RAN: `& .venv\Scripts\python.exe tools/check_ascii.py` -> ASCII check OK; `git diff --check` -> exit 0; module-form `tax_graph.cli validate 2025` -> graph integrity OK, documents=18, nodes=441, tables=2, edges=409, rules=17, citations=401, decisions=2, routing_edges=90, triggers=12, expectations=4; module-form `workbench.cli --root . --year 2025 preflight` -> exit 0, entries=18, units=2224, derived cells=2120, review_gap=591, unreviewed=1529, legacy_mined=394; direct strict citation report -> checked=401, strict_mismatches=36; protected live graph diff -> empty. Local commit `1d9766d` was created; no push.

**Worker session checkpoint - M20-S9b implementation (2026-07-30):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort: default; usage/quota/context
indicators are not exposed. John gave go via the current task request. Single declared step:
build inspectable provider call/run logging, add prompt-token and truncation fail-fast guards,
raise the response cap as justified, clear the specified silent defaults/misleading telemetry,
run one pinned `form_1040_2025` draft-only diagnostic, record exact test evidence, and make one
local commit without pushing. Applicable defect-ledger entries: D4, D6, D8, D9, D11, and the
exact RAN/NOT RUN evidence rule. No 15-form baseline, model swap, prompt quality tuning, draft
promotion, hand-authoring, live graph edit, review-contract change, rollover implementation, or
UI change is in scope.

**M20-S9b focused-test declaration (2026-07-30):** Declared files are
`tests/test_llm_attribution_m20.py`, `tests/test_extract_m4.py`,
`tests/test_draft_route_m20.py`, `tests/test_extract_outline_m4.py`,
`tests/test_batch_extraction_m10.py`, `tests/test_schedule_d_extraction_m9.py`,
`tests/test_trust_tiers_m8.py`, `tests/test_expression_agreement_m20.py`, and
`tests/test_cli.py`. They cover the new run/call log and hard errors, provider adapter and
pipeline defaults, draft/metrics consumers, and the renamed S8 report path. All are runnable
within the 600-second cap and will have exact final evidence below.

**M20-S9b pre-live checkpoint (2026-07-30):** Standard-library JSONL logging now records a
run envelope plus provider calls under `output/logs/`; failures retain capped request and
response bodies at every configured level, successful bodies are DEBUG-only, and API keys and
client headers are never serialized. Prompt-token counts below 8 and `finish_reason: length`
raise named errors. The generator/critic/micro caps are 24000/8000/12000, strict schema and
generator expression mode default on, confidence is marked untrusted telemetry, and the S8
report writer/path is measurement-keyed. The ignored local config is pinned to `z-ai/glm-5.2`
and DEBUG for the one diagnostic. RAN: `$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\30\019fb390-b23e-7ca0-8ef7-d0082dbf5b12\m20-s9b-consumers-r2'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests/test_llm_attribution_m20.py tests/test_extract_m4.py tests/test_draft_route_m20.py tests/test_extract_outline_m4.py tests/test_batch_extraction_m10.py tests/test_schedule_d_extraction_m9.py tests/test_trust_tiers_m8.py tests/test_expression_agreement_m20.py tests/test_cli.py -q` -> 61 passed, 1 warning in 104.59s. RAN: `tools/check_ascii.py` -> ASCII check OK; `git diff --check` -> exit 0; protected live graph diff -> empty. The one-document diagnostic is next; no 15-form baseline will run.

**M20-S9b one-document diagnostic result (2026-07-30):** RAN: `&
.venv\Scripts\python.exe -m tax_graph.cli extract --doc form_1040_2025 --year 2025
--root .` -> exit 1 after 58.4s with `LlmUnavailable: OpenRouter response message content
was not text; finish_reason=error`. The retained log is
`output/logs/ebbeec2a143747fdab6eacd93d9e4a1e.jsonl`. It proves the request was not empty:
one well-formed attempt carried a 23065-character/5863-token prompt, strict `json_schema`,
seven required top-level response fields, `max_tokens=24000`, and
`provider.require_parameters=true`. OpenRouter resolved exactly `z-ai/glm-5.2` and routed to
Baidu. The response used 3 completion tokens, had `finish_reason=error`, null content, and no
native finish reason; latency was 54997.722ms and recorded cost was 0.0. The log contains no API
key, authorization, or client-header fields. This disproves the S9 empty-prompt diagnosis but
does not identify a deeper provider cause: the retained response supplied none. Per the S9b
boundary, no retry, parameter change, model swap, prompt tuning, or 15-form baseline followed.

**M20-S9b final focused-test evidence (2026-07-30):** The first `C:\tmp` attempt is NOT RUN as
test evidence because ACL denial prevented pytest temp setup. Final evidence used a fresh writable
short session root and no `--basetemp`: RAN: `$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\30\019fb390-b23e-7ca0-8ef7-d0082dbf5b12\m20-s9b-final'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests/test_llm_attribution_m20.py tests/test_extract_m4.py tests/test_draft_route_m20.py tests/test_extract_outline_m4.py tests/test_batch_extraction_m10.py tests/test_schedule_d_extraction_m9.py tests/test_trust_tiers_m8.py tests/test_expression_agreement_m20.py tests/test_cli.py -q` -> 61 passed, 1 warning in 105.73s.

**M20-S9b final machine gates (2026-07-30):** RAN: `tools/check_ascii.py` -> ASCII check OK;
`git diff --check` -> exit 0; module-form `tax_graph.cli validate 2025` -> graph integrity OK,
documents=18, nodes=441, tables=2, edges=409, rules=17, citations=401; module-form
`workbench.cli --root . --year 2025 preflight` -> exit 0, entries=18, units=2224,
derived cells=2120, review_gap=591, unreviewed=1529, `legacy_mined=394`; strict citation
report -> checked=401, strict_mismatches=36; protected graph diff -> empty. The tracked S8
measurement was moved from the lying `m20_s7_expression_agreement.yaml` filename to
`output/m20_s8_expression_agreement.yaml`; no draft was promoted and no live graph artifact was
edited. One local commit was created for the whole S9b step; no push was performed.

**Worker session checkpoint - M20-S9 implementation (2026-07-30):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort: default; usage/quota/context
indicators are not exposed. John gave go via the current task request. Single declared step:
capture provider response usage and resolved model ids, carry them through draft provenance and
metrics, switch the ignored live config to the pinned `z-ai/glm-5.2` with generator expression
mode, verify one cheap document call, then re-baseline the 15 manifest forms draft-only.
Applicable defect-ledger entries: D4, D6, D8, D9, D11, and the exact RAN/NOT RUN evidence rule.
No prompt tuning, coverage work, operation-enum change, draft promotion, hand-authoring, live
graph edit, review-contract change, rollover implementation, or UI change is in scope.

**M20-S9 focused-test declaration (2026-07-30):** Declared files are
`tests/test_llm_attribution_m20.py`, `tests/test_extract_m4.py`, `tests/test_draft_route_m20.py`,
`tests/test_extract_outline_m4.py`, `tests/test_batch_extraction_m10.py`,
`tests/test_schedule_d_extraction_m9.py`, and `tests/test_trust_tiers_m8.py`. The first two
cover response-envelope capture, resolved-model provenance, and generator behavior; the next
four cover batch propagation and metrics consumers; the last covers legacy null telemetry.
All will be run with a fresh writable `PYTEST_DEBUG_TEMPROOT`, sequentially, with no
`--basetemp`. Final evidence will be recorded as exact `RAN:` or `NOT RUN:` lines below.

**M20-S9 implementation checkpoint (2026-07-30):** The adapter now preserves a dict-compatible
structured response plus typed provider metadata; generator and critic calls append telemetry to
the extraction batch; resolved model fields flow into object provenance; and `metrics.yaml`
computes worker token/cost totals and records per-call telemetry. Initial RAN:
`$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\30\019fb2f4-74b3-7d10-925c-c4251310f17a\pytest-m20-s9-initial'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests/test_llm_attribution_m20.py tests/test_extract_m4.py tests/test_draft_route_m20.py -q` -> 28 passed, 1 warning in 6.02s. The outline, batch, Schedule D, and trust-tier consumer sweep remains pending before the live call.

**M20-S9 pre-live checkpoint (2026-07-30):** RAN:
`$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\30\019fb2f4-74b3-7d10-925c-c4251310f17a\pytest-m20-s9-consumers'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests/test_extract_outline_m4.py tests/test_batch_extraction_m10.py tests/test_schedule_d_extraction_m9.py tests/test_trust_tiers_m8.py -q` -> 21 passed, 1 warning in 89.83s. The ignored `config/tax-graph.config.yaml` now has exact model `z-ai/glm-5.2` and `extraction.expression_mode: generator`; the example config remains unchanged. No live call or draft regeneration has started. Next is the required cheap model-resolution call; if it fails, stop without a substitute.

**M20-S9 model probe checkpoint (2026-07-30):** RAN: approved direct OpenRouter structured
probe with requested `z-ai/glm-5.2` and purpose `m20_s9_model_probe` -> resolved model
`z-ai/glm-5.2`, prompt_tokens=31, completion_tokens=26, total_tokens=57, cost=0.00008648.
The pinned id resolves exactly. The next command is the approved four-worker, 15-form,
draft-only baseline; it will write only under `graph/2025/_drafts/` and will be followed by
the expression report. No live graph artifact has been touched.

**M20-S9 stop checkpoint (2026-07-30):** The four-worker 15-form draft-only command was
started after the successful probe, but stopped at 62.6s when a full extraction response could
not be parsed: `tax_graph.extract.llm_client.LlmUnavailable: OpenRouter response did not contain
JSON` from `structured_completion` while generating `tax_graph_draft`. This is an API/model
response failure under the S9 stop conditions; no retry, substitute model, prompt tuning, or
second baseline was attempted. The existing 16 ignored draft directories are prior-round state;
the new S9 run produced no `resolved_model` provenance records. Protected live graph diff is
empty. The 15-form S9 coverage/accuracy report and final machine gates are NOT RUN because of
this failure.

**M20-S9 focused-test evidence (2026-07-30):**

- RAN: `$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\30\019fb2f4-74b3-7d10-925c-c4251310f17a\pytest-m20-s9-initial'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests/test_llm_attribution_m20.py tests/test_extract_m4.py tests/test_draft_route_m20.py -q` -> 28 passed, 1 warning in 6.02s.
- RAN: `$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\30\019fb2f4-74b3-7d10-925c-c4251310f17a\pytest-m20-s9-consumers'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests/test_extract_outline_m4.py tests/test_batch_extraction_m10.py tests/test_schedule_d_extraction_m9.py tests/test_trust_tiers_m8.py -q` -> 21 passed, 1 warning in 89.83s.
- NOT RUN: final machine gates and the S9 expression baseline/report -> the pinned-model full extraction stopped on the non-JSON response above.

**Worker session checkpoint - M20-S8 implementation (2026-07-30):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort: default; usage/quota/context
indicators are not exposed. John gave go via the current task request. Single declared step:
diagnose the generated edge-target convention, implement only a data-driven canonical-address
bridge and operand-role emission needed to make expression scoring real, then re-measure and
commit the coverage/accuracy report. Applicable defect-ledger entries: D4, D6, D8, D9, D11,
and the exact RAN/NOT RUN evidence rule. No live graph edit, draft promotion, generated
artifact hand edit, prompt quality tuning, operation-enum change, review-contract change, or
UI change is in scope.

**M20-S8 focused-test declaration (2026-07-30):** Declared files are
`tests/test_expression_agreement_m20.py`, `tests/test_extract_m4.py`,
`tests/test_draft_route_m20.py`, and `tests/test_cli.py`. The first covers the
canonical-address bridge and separate coverage/accuracy report; the second covers generator
boundary role completion; the latter two are consumers of the draft/report output contract.
All will be run with a fresh writable `PYTEST_DEBUG_TEMPROOT`, sequentially, with no
`--basetemp`. Final evidence will be recorded as exact `RAN:` or `NOT RUN:` lines below.

**M20-S8 pre-expensive regeneration checkpoint (2026-07-30):** The bridge-only measurement
over the existing S7 drafts is now real: coverage is 7/80 (8.75%); among paired expressions,
operation agreement is 6/7 and full expression agreement is 0/7. The bridge resolved 39 of 80
unique generated endpoints through canonical address bindings and left 41 unresolved; no
hardcoded per-form map was used. The next command will regenerate the 15 manifest form
documents with the existing configured Flash/OpenRouter model, four concurrent workers, and
draft-only output. API spend is not exposed by the client. No live graph diff has occurred.

**M20-S8 regeneration correction (2026-07-30):** The first 15-document command completed
successfully but produced zero expression files because the local gitignored config omits the
example config's `extraction.expression_mode: generator`; its default is `none`. This is a
configuration-selection error, not a model or parser result. The corrective rerun will set that
existing mode explicitly in the in-memory settings, preserving draft-only output and the
protected live graph.

**M20-S8 expression-mode smoke checkpoint (2026-07-30):** The explicit generator-mode Form
1040 smoke run succeeded after approved network execution: `edges=7`, `rules=5`, and the
draft writer emitted both expression files. The sandbox-only attempt is NOT test evidence for
pipeline behavior; it failed before writing expressions with `WinError 10013`. The full
15-document rerun is now authorized in the same in-memory mode with four concurrent workers.

**M20-S8 regeneration and measurement result (2026-07-30):** RAN: the approved four-worker
generator-mode command using `FORM_KINDS` -> 15/15 manifest form documents completed in
495.5s; output remained under `graph/2025/_drafts/`. RAN: module-form `verify expression-agreement
--year 2025` -> coverage `7/80` (8.75%), operation accuracy `7/7` among paired expressions,
full expression accuracy `0/7`, categories `expression_agreement=0`,
`operation_agreement_operands_differ=7`, `operation_disagreement=0`, `missing_in_draft=73`,
`extra_in_draft=20`. The bridge resolved 27 of 49 unique generated endpoints through canonical
address bindings; 22 remained unresolved. Draft inventory is `edges=56`, `rules=26`, with 25
CALCULATES edges and zero missing roles. The protected live graph is unchanged.

**M20-S8 focused-test evidence (2026-07-30):** Final rerun used a fresh writable
`PYTEST_DEBUG_TEMPROOT` and no `--basetemp`:

- RAN: `$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\30\019fb286-e5f2-70c1-bc8e-50405160b1b3\pytest-m20-s8-final'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests/test_expression_agreement_m20.py -q` -> 4 passed, 1 warning in 0.27s.
- RAN: `$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\30\019fb286-e5f2-70c1-bc8e-50405160b1b3\pytest-m20-s8-final'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests/test_extract_m4.py -q` -> 23 passed, 1 warning in 5.74s.
- RAN: `$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\30\019fb286-e5f2-70c1-bc8e-50405160b1b3\pytest-m20-s8-final'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests/test_draft_route_m20.py -q` -> 2 passed, 1 warning in 0.23s.
- RAN: `$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\30\019fb286-e5f2-70c1-bc8e-50405160b1b3\pytest-m20-s8-final'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests/test_cli.py -q` -> 6 passed, 1 warning in 18.51s.

**M20-S8 machine gates (2026-07-30):** RAN: `tools/check_ascii.py` -> ASCII check OK;
`git diff --check` -> exit 0; module-form `tax_graph.cli validate 2025` -> graph integrity OK,
documents=18, nodes=441, tables=2, edges=409, rules=17, citations=401; module-form
`workbench.cli --root . --year 2025 preflight` -> exit 0, entries=18, units=2224,
derived cells=2120, review_gap=591, unreviewed=1529, legacy_mined=394; strict citation
report -> checked=401, strict_mismatches=36; protected graph diff -> empty.

**M20-S7 pre-expensive regeneration checkpoint (2026-07-30):** The expression-enabled
`form_1040_2025` run completed in 115.6s and wrote `edges=4` and `rules=3` to its ignored
draft directory; the live `graph/2025/{nodes,edges,rules}/` diff is empty. The first report
is honest and low: `expression_agreement=0`, `missing_in_draft=80`, `extra_in_draft=3`.
The generated ids do not match the protected canonical ids and the generated edges omitted
operand roles, so no normalization or hand repair will be applied. The client exposes no
token or price usage, so exact spend is unavailable. The full 16-form regeneration will use
four concurrent document workers, write only `_drafts`, and be followed by the committed
comparison report and declared gates.

**M20-S7 full regeneration result (2026-07-30):** RAN: the approved four-worker command
`$script = @' ... extract_document ... ' @; & .venv\Scripts\python.exe -c $script` ->
15/15 manifest form documents completed successfully in 527.8s; the manifest has 15 form
entries, not 16. Every form draft now has generated expression files. RAN: module-form
`verify expression-agreement --year 2025` -> `expression_agreement=0`,
`operation_agreement_operands_differ=0`, `operation_disagreement=0`, `missing_in_draft=80`,
`extra_in_draft=35`. The report is at `output/m20_s7_expression_agreement.yaml`; the live
`graph/2025/{nodes,edges,rules}/` diff remains empty. The zero agreement is retained as the
pipeline measurement: generated targets use a different id convention and do not yet join
the protected expression set. Generated non-COPY edges without roles are now explicit
deterministic review findings, not silently accepted operands.

**M20-S7 focused-test evidence so far (2026-07-30):** The first expression test attempt is
`NOT RUN as evidence`: `C:\tmp` creation was denied before pytest setup. Final reruns are
recorded as follows: `tests/test_expression_agreement_m20.py` -> 3 passed; `tests/test_extract_m4.py`
-> 22 passed; `tests/test_extract_outline_m4.py` -> 9 passed after the explicit-mode fix;
`tests/test_draft_route_m20.py` -> 2 passed; `tests/test_cli.py` -> 6 passed. All reruns used
fresh writable `PYTEST_DEBUG_TEMPROOT` paths and no `--basetemp`.

**M20-S7 final machine gates (2026-07-30):** RAN: `tools/check_ascii.py` -> ASCII check OK;
`git diff --check` -> exit 0; protected graph diff -> empty; module-form `tax_graph.cli
validate 2025` -> graph integrity OK, documents=18, nodes=441, tables=2, edges=409,
rules=17, citations=401; module-form `workbench.cli --root . --year 2025 preflight` ->
exit 0, entries=18, units=2224, derived cells=2120, review_gap=591, unreviewed=1529,
legacy_mined=394; strict citation report -> checked=401, strict_mismatches=36. No draft was
promoted and no live graph artifact was edited.

**M20-S7 local close (2026-07-30):** One local commit created for this step; no push was
performed. The next decision is whether the honest zero-agreement result warrants an address
identity bridge or a generator-prompt/structure round; this Worker did not alter the protected
handcrafted test set to improve the number.

**M20-S7 Step 1 diagnosis checkpoint (2026-07-30):** The configured OpenRouter model
`~google/gemini-flash-latest` returned a raw structured response for `form_1040_2025` with
`nodes=8`, `edges=4`, `rules=4`, `citations=5`, and `decisions=1`; the complete raw response is
captured at `C:\tmp\m20_s7_form_1040_raw.json`. `parse_generator_response` preserves all
`DRAFT_KINDS`, and `write_routed_drafts` writes every non-empty kind, so the one-pass path does
not drop edges or rules. The missing live draft expression layer is caused by the configured
`extraction.mode: outline_first`: `generate_outline_first_drafts` only creates formula edges
and rules for outline nodes classified as transaction tables or totals, and the 1040 outline
has neither, leaving only nodes/citations. Step 2 must therefore repair the production
outline-first plumbing or add an explicit expression-generation path; it must not alter the
protected live graph or hand-author expressions.

**Worker session checkpoint - M20-S6-1 implementation (2026-07-29):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort: default; usage/quota/context
indicators are not exposed. John gave go via the current task request. Single declared step:
make expression content (including normalized operation and operand refs) part of the approval
fingerprint, split form and instruction citations, restore geometry-free graph cells and the
separate routing review set, restore `zero_units`/`ambiguous_object`, emit `review_gap` and
`kind_bucket` projection data, and add/update tests and docs before one local commit. The
2025 address verdict store is absent (zero records), so the breaking fingerprint has no human
judgement migration. Applicable defect-ledger entries: D11, D4, D6, D8, D9, and the exact
RAN/NOT RUN evidence rule. D1-D3, D5, and D7 are not expected because `workbench/static/`
is out of scope. No draft promotion, generated citation or label hand edit, graph semantic,
geometry, field-map, or human-review claim is in scope.

**M20-S6-1 focused-test declaration (2026-07-29):** The implementation and first focused
round are complete enough for the consumer sweep. Declared files are
`tests/test_review_verdicts_m20.py`, `tests/test_review_preflight_m15.py`,
`tests/test_review_manifest_m15.py`, `tests/test_review_schemas_m15.py`,
`tests/test_workbench_m15.py`, `tests/test_workbench_server_m15.py`,
`tests/test_workbench_write_api_m15.py`, `tests/test_review_semantics_m15.py`,
`tests/test_review_semantics_remaining_m15.py`, `tests/test_workbench_identity_m19.py`,
`tests/test_workbench_refs_m17.py`, and `tests/test_workbench_cells_m17.py`.
`tests/test_workbench_cells_api_m17.py` is also declared because the manifest is exposed
through the document API. All will be run sequentially with a fresh writable
`PYTEST_DEBUG_TEMPROOT`; no `--basetemp` will be used. The exact final results are
recorded below.

- RAN: `$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\29\019faf5e-23ff-7d43-bcb7-f54ac64ac203\pytest-m20-r3'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests/test_review_verdicts_m20.py -q` -> 14 passed, 1 warning in 44.71s.
- RAN: `$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\29\019faf5e-23ff-7d43-bcb7-f54ac64ac203\pytest-preflight-r2'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests/test_review_preflight_m15.py -q` -> 2 passed, 1 warning in 106.08s.
- RAN: `$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\29\019faf5e-23ff-7d43-bcb7-f54ac64ac203\pytest-manifest-r3'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests/test_review_manifest_m15.py -q` -> 7 passed, 1 warning in 212.92s.
- RAN: `$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\29\019faf5e-23ff-7d43-bcb7-f54ac64ac203\pytest-schema-r2'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests/test_review_schemas_m15.py -q` -> 7 passed, 1 warning in 0.47s.
- RAN: `$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\29\019faf5e-23ff-7d43-bcb7-f54ac64ac203\pytest-workbench-r2'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests/test_workbench_m15.py -q` -> 4 passed, 1 warning in 0.34s.
- RAN: `$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\29\019faf5e-23ff-7d43-bcb7-f54ac64ac203\pytest-server-r1'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests/test_workbench_server_m15.py -q` -> 6 passed, 1 warning in 52.10s.
- RAN: `$testRoot='C:\Users\devbox\.codex\visualizations\2026\07\29\019faf5e-23ff-7d43-bcb7-f54ac64ac203\pytest-consumers-r1'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT=$testRoot; & .venv\Scripts\python.exe -m pytest tests/test_workbench_write_api_m15.py tests/test_review_semantics_m15.py tests/test_review_semantics_remaining_m15.py tests/test_workbench_identity_m19.py tests/test_workbench_refs_m17.py tests/test_workbench_cells_m17.py tests/test_workbench_cells_api_m17.py -q` -> 41 passed, 1 warning in 270.85s.

**M20-S6-1 machine gates (2026-07-29):**

- RAN: `& .venv\Scripts\python.exe -m workbench.cli --root . --year 2025 preflight` ->
  exit 0; entries=18, units=2224, derived cells=2120, states approved=0,
  needs_recheck=0, review_gap=591, unreviewed=1529, legacy_mined=394.
- RAN: `& .venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> exit 0; graph
  integrity OK, documents=18, nodes=441, tables=2, edges=409, rules=17, citations=401.
- RAN: `& .venv\Scripts\python.exe -c "from tax_graph.acquire.citation_check import check_graph_citations; report=check_graph_citations(year='2025', raw_store='.cache/raw', root='.'); print(f'checked={report.checked}, strict_mismatches={len(report.mismatches)}')"` ->
  checked=401, strict_mismatches=36.
- RAN: `& .venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK.
- RAN: `git diff --check` -> exit 0.
- `workbench/static/` has no changed files; no static/UI work is included in S6-1.

**M20-S6-1 implementation complete (2026-07-29):** The review contract now fingerprints
the normalized expression and separated citation slots, and the manifest carries those
same slots for physical and unlocated graph cells. The live projection is 2,120 form
cells plus a separate 104-unit routing set; 303 units are intentionally unlocated and
591 cells are explicit review gaps. Preflight restores zero-unit and ambiguous-object
fail-closed checks. No verdict migration was needed because the 2025 verdict store is
absent, no promoted artifact or generated citation was hand-edited, and no push was made.
One local commit is the remaining handoff action.

**Worker session checkpoint - M20-S5-2 implementation (2026-07-29):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort: default; usage/quota/context
indicators are not exposed. John gave go via the current task request. Single declared step:
carry all four non-derivable authored review records, fix address-verdict epoch ordering and
strict reviewed-content validation, switch preflight to derived coverage, remove the obsolete
queue/reconciler machinery, and add successor tests before one local commit. S5-1 is accepted
at `48af95b`; its dual gate is green and the queue has not yet been retired. Applicable
defect-ledger entries: D8, D9, D4, D6, D11, and the exact RAN/NOT RUN evidence rule. No
promoted artifact, generated citation, graph semantic, field-map, geometry, or human-review
claim is in scope.

**M20-S5-2 pre-write checkpoint (2026-07-29):** The precondition is satisfied on `main`:
S5-1 was accepted at `48af95b`, preflight reported queue `entries=35`, `units=2980`, derived
`1921` cells, `divergence_findings=0`, `legacy_mined=394`, and strict citation mismatches
`36`. Declared focused files are `tests/test_review_verdicts_m20.py`,
`tests/test_review_preflight_m15.py`, `tests/test_review_queue_reconciliation_m20.py`,
`tests/test_review_schemas_m15.py`, `tests/test_review_manifest_m15.py`,
`tests/test_workbench_m15.py`, and `tests/test_workbench_server_m15.py`; the queue test
will be replaced only after its behaviors have named green derived-path successors. No
implementation or test result is claimed yet.

**M20-S5-2 first-test checkpoint (2026-07-29):** The first parallel pytest attempt used the
poisoned default `.test_tmp\\pytest-of-devbox` and hit `WinError 5` during fixture setup. It
is not code evidence. The verdict test completed its first non-temp case (`1 passed`) before
the temp-dependent cases errored; `tests/test_workbench_m15.py` is NOT RUN as evidence because
three temp-dependent tests setup-errored for the same ACL. Rerun is required sequentially with
a fresh writable `PYTEST_DEBUG_TEMPROOT`; no `--basetemp` will be used.

- NOT RUN as evidence: `.venv\\Scripts\\python.exe -m pytest tests\\test_workbench_m15.py -q`
  -> 1 passed, 3 setup errors in 0.76s because the poisoned `.test_tmp\\pytest-of-devbox`
  directory denied access; this was the known temp-root failure, not code evidence.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\29\\019fadfc-9406-76f0-9295-928d7e10ebbd\\m20_s5_2_verdict'; .venv\\Scripts\\python.exe -m pytest tests\\test_review_verdicts_m20.py -q` -> 10 passed in 8.86s.
- NOT RUN as evidence: `$env:PYTEST_DEBUG_TEMPROOT='C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\29\\019fadfc-9406-76f0-9295-928d7e10ebbd\\m20_s5_2_workbench'; .venv\\Scripts\\python.exe -m pytest tests\\test_workbench_m15.py -q` -> 1 passed, 3 setup errors in 0.31s because the fresh temp-root directory had not yet been created; rerun required.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\29\\019fadfc-9406-76f0-9295-928d7e10ebbd\\m20_s5_2_workbench'; .venv\\Scripts\\python.exe -m pytest tests\\test_workbench_m15.py -q` -> 4 passed in 0.41s.

**M20-S5-2 manifest checkpoint (2026-07-29):** The first live manifest partition found a
real projection/test expectation mismatch: the derived form-cell manifest has 199 addressed
1040 cells, while the retired queue-sourced manifest had 223. The derived denominator remains
the authoritative 1,921 physical controls; the test expectation was updated to the measured
derived count. The first partition is NOT final evidence until rerun.

- NOT RUN as final evidence: `$env:PYTEST_DEBUG_TEMPROOT='C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\29\\019fadfc-9406-76f0-9295-928d7e10ebbd\\m20_s5_2_manifest'; .venv\\Scripts\\python.exe -m pytest tests\\test_review_manifest_m15.py -q -k "not manifest_writes_stable_json_and_keeps_scope_roles_out_of_public_refs and not manifest_hash_pins_every_file_in_example_artifact_directory"` -> 4 passed, 1 failed, 2 deselected in 95.37s; the test still asserted the retired queue's 223 addressed 1040 units, while derived projection measured 199.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\29\\019fadfc-9406-76f0-9295-928d7e10ebbd\\m20_s5_2_manifest_r3'; .venv\\Scripts\\python.exe -m pytest tests\\test_review_manifest_m15.py -q -k "not manifest_writes_stable_json_and_keeps_scope_roles_out_of_public_refs and not manifest_hash_pins_every_file_in_example_artifact_directory"` -> 5 passed, 2 deselected in 98.42s.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\29\\019fadfc-9406-76f0-9295-928d7e10ebbd\\m20_s5_2_manifest_stable'; .venv\\Scripts\\python.exe -m pytest tests\\test_review_manifest_m15.py::test_manifest_writes_stable_json_and_keeps_scope_roles_out_of_public_refs -q` -> 1 passed in 48.06s.
- NOT RUN as final evidence: `$env:PYTEST_DEBUG_TEMPROOT='C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\29\\019fadfc-9406-76f0-9295-928d7e10ebbd\\m20_s5_2_manifest_hash'; .venv\\Scripts\\python.exe -m pytest tests\\test_review_manifest_m15.py::test_manifest_hash_pins_every_file_in_example_artifact_directory -q` -> 1 failed in 0.25s because the test read the deleted queue file; replacement required.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\29\\019fadfc-9406-76f0-9295-928d7e10ebbd\\m20_s5_2_manifest_hash_r2'; .venv\\Scripts\\python.exe -m pytest tests\\test_review_manifest_m15.py::test_manifest_hash_pins_every_file_in_example_artifact_directory -q` -> 1 passed in 95.76s.

**M20-S5-2 preflight checkpoint (2026-07-29):** The first preflight run found repeated derived
labels without the old manifest's physical qualifier, producing actionable
`ambiguous_display_name` findings across repeated controls. The projection now reuses the
existing deterministic `_physical_qualifier`; the first run is NOT final evidence and must be
rerun.

- NOT RUN as final evidence: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fadfc-9406-76f0-9295-928d7e10ebbd\m20_s5_2_preflight_r2'; New-Item -ItemType Directory -Force -Path $env:PYTEST_DEBUG_TEMPROOT | Out-Null; .venv\Scripts\python.exe -m pytest tests\test_review_preflight_m15.py -q` -> 1 failed, 1 passed in 156.5s because the retired queue-era test still required a positive `by_geometry.unlocated` count, while the derived physical-cell projection has no unlocated units.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fadfc-9406-76f0-9295-928d7e10ebbd\m20_s5_2_preflight_r3'; New-Item -ItemType Directory -Force -Path $env:PYTEST_DEBUG_TEMPROOT | Out-Null; .venv\Scripts\python.exe -m pytest tests\test_review_preflight_m15.py -q` -> 2 passed in 155.96s.

**M20-S5-2 consumer checkpoint (2026-07-29):** Queue-shaped tests were converted to derived
physical-cell expectations. The server now exposes the 16 derived document entries, and the
static builder projects the manifest rather than an empty retired queue. The deleted
reconciliation test is replaced by `test_derived_projection_replaces_queue_matching_and_orphan_persistence`
in `tests/test_review_verdicts_m20.py`, plus the derived manifest, preflight, server, and write
API successors below. Legacy explicit-queue fixtures remain isolated for producer compatibility.

- NOT RUN as final evidence: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fadfc-9406-76f0-9295-928d7e10ebbd\m20_s5_2_server'; New-Item -ItemType Directory -Force -Path $env:PYTEST_DEBUG_TEMPROOT | Out-Null; .venv\Scripts\python.exe -m pytest tests\test_workbench_server_m15.py -q` -> 4 passed, 2 failed in 65.0s because tests still expected 15 queue entries and a non-physical worksheet-step unit.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fadfc-9406-76f0-9295-928d7e10ebbd\m20_s5_2_server_r2'; New-Item -ItemType Directory -Force -Path $env:PYTEST_DEBUG_TEMPROOT | Out-Null; .venv\Scripts\python.exe -m pytest tests\test_workbench_server_m15.py -q` -> 6 passed in 65.28s.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fadfc-9406-76f0-9295-928d7e10ebbd\m20_s5_2_schemas'; New-Item -ItemType Directory -Force -Path $env:PYTEST_DEBUG_TEMPROOT | Out-Null; .venv\Scripts\python.exe -m pytest tests\test_review_schemas_m15.py -q` -> 7 passed in 0.49s.
- NOT RUN as final evidence: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fadfc-9406-76f0-9295-928d7e10ebbd\m20_s5_2_consumers'; New-Item -ItemType Directory -Force -Path $env:PYTEST_DEBUG_TEMPROOT | Out-Null; .venv\Scripts\python.exe -m pytest tests\test_review_semantics_m15.py tests\test_review_semantics_remaining_m15.py tests\test_workbench_identity_m19.py tests\test_workbench_refs_m17.py tests\test_workbench_cells_m17.py tests\test_workbench_cells_api_m17.py -q` -> 35 passed, 2 failed in 246.04s because the derived projection intentionally omits graph-only operation kinds and unaddressed units do not have `address_id`.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fadfc-9406-76f0-9295-928d7e10ebbd\m20_s5_2_consumers_r2'; New-Item -ItemType Directory -Force -Path $env:PYTEST_DEBUG_TEMPROOT | Out-Null; .venv\Scripts\python.exe -m pytest tests\test_review_semantics_remaining_m15.py tests\test_workbench_refs_m17.py -q` -> 13 passed in 87.93s.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fadfc-9406-76f0-9295-928d7e10ebbd\m20_s5_2_consumers_r3'; New-Item -ItemType Directory -Force -Path $env:PYTEST_DEBUG_TEMPROOT | Out-Null; .venv\Scripts\python.exe -m pytest tests\test_review_semantics_m15.py tests\test_workbench_identity_m19.py tests\test_workbench_cells_m17.py tests\test_workbench_cells_api_m17.py -q` -> 24 passed in 134.43s.
- NOT RUN as final evidence: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fadfc-9406-76f0-9295-928d7e10ebbd\m20_s5_2_write_api'; New-Item -ItemType Directory -Force -Path $env:PYTEST_DEBUG_TEMPROOT | Out-Null; .venv\Scripts\python.exe -m pytest tests\test_workbench_write_api_m15.py -q` -> 3 passed, 1 failed in 58.33s because the write-invariant test still hashed the deleted live queue file.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fadfc-9406-76f0-9295-928d7e10ebbd\m20_s5_2_write_api_r2'; New-Item -ItemType Directory -Force -Path $env:PYTEST_DEBUG_TEMPROOT | Out-Null; .venv\Scripts\python.exe -m pytest tests\test_workbench_write_api_m15.py -q` -> 4 passed in 58.09s.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fadfc-9406-76f0-9295-928d7e10ebbd\m20_s5_2_legacy_verdicts'; New-Item -ItemType Directory -Force -Path $env:PYTEST_DEBUG_TEMPROOT | Out-Null; .venv\Scripts\python.exe -m pytest tests\test_review_workbench_verdicts_m15.py -q` -> 7 passed in 0.63s; this covers explicit temporary queue fixtures only.

**M20-S5-2 ratchet checkpoint (2026-07-29):** The first real CLI preflight after switching the
coverage report to the derived manifest measured `legacy_mined=402`, not the required `394`.
The eight extra records were deterministic shaded/no-entry geometry controls in Form 8949 and
W-2, not mined reviewer language. The projection now classifies exactly those eight as the
existing schema's `identity_slot` provenance; all other no-address fallbacks retain the legacy
classification. Preflight validation treats `identity_slot` as derived language, so authored
labels remain strict while the established ratchet is preserved.

- NOT RUN as final evidence: `.venv\Scripts\python.exe -m workbench.cli --root . --year 2025 preflight` -> exit 0 in 57.2s but reported `legacy_mined=402`; stop-condition violation, so the provenance correction was required.
- NOT RUN as final evidence: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fadfc-9406-76f0-9295-928d7e10ebbd\m20_s5_2_preflight_r4'; New-Item -ItemType Directory -Force -Path $env:PYTEST_DEBUG_TEMPROOT | Out-Null; .venv\Scripts\python.exe -m pytest tests\test_review_preflight_m15.py -q` -> 1 failed, 1 passed in 136.3s because the first provenance correction exposed derived labels as invalid authored names.
- NOT RUN as evidence: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fadfc-9406-76f0-9295-928d7e10ebbd\m20_s5_2_preflight_r5'; New-Item -ItemType Directory -Force -Path $env:PYTEST_DEBUG_TEMPROOT | Out-Null; .venv\Scripts\python.exe -m pytest tests\test_review_preflight_m15.py -q` -> collection `IndentationError` after the validation patch; indentation was corrected before the next run.
- NOT RUN as final evidence: `.venv\Scripts\python.exe -m workbench.cli --root . --year 2025 preflight` -> exit 0 in 56.3s but reported `legacy_mined=236`; an intermediate condition incorrectly classified safe no-address labels as authored and was corrected.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fadfc-9406-76f0-9295-928d7e10ebbd\m20_s5_2_preflight_r8'; New-Item -ItemType Directory -Force -Path $env:PYTEST_DEBUG_TEMPROOT | Out-Null; .venv\Scripts\python.exe -m pytest tests\test_review_preflight_m15.py -q` -> 2 passed in 135.19s.
- RAN: `.venv\Scripts\python.exe -m workbench.cli --root . --year 2025 preflight` -> exit 0 in 56.9s; `entries=16`, `units=1921`, `derived=1921`, states `approved=0, needs_recheck=0, unreviewed=1921`, `by_geometry=located:1921`, `legacy_mined=394`.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fadfc-9406-76f0-9295-928d7e10ebbd\m20_s5_2_manifest_final'; New-Item -ItemType Directory -Force -Path $env:PYTEST_DEBUG_TEMPROOT | Out-Null; .venv\Scripts\python.exe -m pytest tests\test_review_manifest_m15.py -q` -> 7 passed in 198.11s.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fadfc-9406-76f0-9295-928d7e10ebbd\m20_s5_2_server_final'; New-Item -ItemType Directory -Force -Path $env:PYTEST_DEBUG_TEMPROOT | Out-Null; .venv\Scripts\python.exe -m pytest tests\test_workbench_server_m15.py -q` -> 6 passed in 56.22s.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fadfc-9406-76f0-9295-928d7e10ebbd\m20_s5_2_workbench_final2'; New-Item -ItemType Directory -Force -Path $env:PYTEST_DEBUG_TEMPROOT | Out-Null; .venv\Scripts\python.exe -m pytest tests\test_workbench_m15.py -q` -> 4 passed in 0.34s.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fadfc-9406-76f0-9295-928d7e10ebbd\m20_s5_2_consumers_final'; New-Item -ItemType Directory -Force -Path $env:PYTEST_DEBUG_TEMPROOT | Out-Null; .venv\Scripts\python.exe -m pytest tests\test_review_semantics_remaining_m15.py tests\test_workbench_refs_m17.py tests\test_workbench_identity_m19.py tests\test_workbench_cells_m17.py tests\test_workbench_cells_api_m17.py -q` -> 32 passed in 176.76s.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fadfc-9406-76f0-9295-928d7e10ebbd\m20_s5_2_write_api_final'; New-Item -ItemType Directory -Force -Path $env:PYTEST_DEBUG_TEMPROOT | Out-Null; .venv\Scripts\python.exe -m pytest tests\test_workbench_write_api_m15.py -q` -> 4 passed in 56.47s.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fadfc-9406-76f0-9295-928d7e10ebbd\m20_s5_2_semantics_final'; New-Item -ItemType Directory -Force -Path $env:PYTEST_DEBUG_TEMPROOT | Out-Null; .venv\Scripts\python.exe -m pytest tests\test_review_semantics_m15.py -q` -> 5 passed in 40.26s.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fadfc-9406-76f0-9295-928d7e10ebbd\m20_s5_2_verdict_final2'; New-Item -ItemType Directory -Force -Path $env:PYTEST_DEBUG_TEMPROOT | Out-Null; .venv\Scripts\python.exe -m pytest tests\test_review_verdicts_m20.py -q` -> 10 passed in 7.43s; this is the final verdict-ledger run after tightening reviewed-content shape validation.

**M20-S5-2 implementation complete (2026-07-29):** The generated 2025 deferred queue and
reconciler machinery are retired from the workbench path; default artifacts, manifests, static
bundles, server projections, and preflight now use the physical-cell derived manifest. The four
curated authored records are carried by exact id, the address ledger orders normalized UTC epoch
seconds with file-order ties and requires reviewed content, and the eight deterministic shaded
controls no longer inflate the `legacy_mined=394` ratchet. Graph validation, strict citation
integrity, ASCII, and diff checks are green. Committed locally (no push).

**Worker session checkpoint - M20-S5-1 implementation (2026-07-29):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort: default; usage/quota/context
indicators are not exposed. John gave go via the current task request. Single declared step:
add the address-keyed verdict ledger, normalized fingerprints, graph-derived three-state cell
coverage, blast-radius report, rollover seam, and the three authored-record carryover ALONGSIDE
the existing queue path. Keep the existing queue gate, queue file, reconciler, and CLI untouched;
S5-2 owns retirement after this round is accepted. Applicable defect-ledger entries: D11, D13,
D4, D6, D8, D9, D10, and the exact RAN/NOT RUN evidence rule. D1-D3, D5, and D7 are not
expected unless the implementation unexpectedly crosses the frontend or session scroll surfaces.
No draft promotion, generated citation or label hand edit, graph semantic change, geometry
change, field-map change, or human-review claim is in scope.

**M20-S5-1 pre-write checkpoint (2026-07-29):** Read-only consumer mapping found the queue is
loaded by the workbench bundle, manifest, preflight, CLI, legacy verdict applier, scope migrator,
example verifier, extension path, and instruction promotion. This round will add the derived
path without removing or rewiring any of those consumers. Focused files declared for this round
are the new `tests/test_review_verdicts_m20.py`, `tests/test_review_preflight_m15.py`,
`tests/test_review_manifest_m15.py`, `tests/test_workbench_m15.py`, and
`tests/test_workbench_server_m15.py`; the existing queue reconciliation test remains in scope
and is not deleted or replaced in S5-1. No implementation or test result is claimed yet.

**M20-S5-1 implementation checkpoint (2026-07-29):** Added `workbench/address_verdicts.py` and
its schema for append-only JSONL address verdicts, normalized label/citation fingerprints,
three-state derived coverage, blast-radius reporting, and explicit rollover candidates. Added
`workbench/derived_reviews.py` to walk the 1,921 physical controls without reading the queue,
added dual-path derived coverage to preflight and CLI reporting, and preserved the three curated
Architect records in `review_context/2025/authored_reviews.yaml`. The existing queue gate,
manifest, reconciler, queue file, and queue CLI remain unchanged.

- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fad2c-003b-7471-a819-62a031ceac62\m20_s5_1_pytest2'; .venv\Scripts\python.exe -m pytest tests/test_review_verdicts_m20.py -q` -> 6 passed in 7.55s; one known pytest cache ACL warning.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fad2c-003b-7471-a819-62a031ceac62\m20_s5_1_preflight'; .venv\Scripts\python.exe -m pytest tests/test_review_preflight_m15.py -q` -> 2 passed in 482.05s; one known pytest cache ACL warning.

**M20-S5-1 pre-consumer checkpoint (2026-07-29):** The new ledger and dual gate are green on
the focused files. Before the remaining consumer tests and non-promoting gates, the expected
production invariants are unchanged: queue report `entries=35`, `units=2980`, derived denominator
`1921`, `derived states=unreviewed:1921, approved:0, needs_recheck:0`, `legacy_mined=394`, and
strict citation mismatches `36`. S5-2 queue retirement remains out of scope.

- NOT RUN as evidence: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fad2c-003b-7471-a819-62a031ceac62\m20_s5_1_consumers'; .venv\Scripts\python.exe -m pytest tests/test_workbench_m15.py tests/test_workbench_server_m15.py -q` -> 7 passed, 3 setup errors in 198.60s because the declared temp-root directory did not exist; rerun required.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fad2c-003b-7471-a819-62a031ceac62\m20_s5_1_consumers2'; .venv\Scripts\python.exe -m pytest tests/test_workbench_m15.py tests/test_workbench_server_m15.py -q` -> 10 passed in 202.61s; one known pytest cache ACL warning. This covers both declared consumer files.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fad2c-003b-7471-a819-62a031ceac62\m20_s5_1_manifest_a'; .venv\Scripts\python.exe -m pytest tests/test_review_manifest_m15.py -q -k "not manifest_writes_stable_json_and_keeps_scope_roles_out_of_public_refs and not manifest_hash_pins_every_file_in_example_artifact_directory"` -> 5 passed, 2 deselected in 360.12s; one known pytest cache ACL warning.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fad2c-003b-7471-a819-62a031ceac62\m20_s5_1_manifest_b'; .venv\Scripts\python.exe -m pytest tests/test_review_manifest_m15.py::test_manifest_writes_stable_json_and_keeps_scope_roles_out_of_public_refs -q` -> 1 passed in 182.09s; one known pytest cache ACL warning.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fad2c-003b-7471-a819-62a031ceac62\m20_s5_1_manifest_c'; .venv\Scripts\python.exe -m pytest tests/test_review_manifest_m15.py::test_manifest_hash_pins_every_file_in_example_artifact_directory -q` -> 1 passed in 358.68s; one known pytest cache ACL warning. Together these three commands verify all 7 tests in `tests/test_review_manifest_m15.py`.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fad2c-003b-7471-a819-62a031ceac62\m20_s5_1_queue'; .venv\Scripts\python.exe -m pytest tests/test_review_queue_reconciliation_m20.py -q` -> 2 passed in 0.18s; one known pytest cache ACL warning. The existing reconciler test remains green and unchanged, as required by S5-1.

**M20-S5-1 pre-gate checkpoint (2026-07-29):** All declared focused and consumer pytest files
are green, including the unchanged queue reconciler. The remaining checks are the module-form
real preflight/CLI output, graph validation, strict citation integrity, ASCII, and diff checks.
No queue file, generated draft, promoted artifact, graph semantic, geometry, field-map, or
reconciler code has been changed. S5-2 retirement is not being started.

**M20-S5-1 divergence correction checkpoint (2026-07-29):** The first production report counted
non-cell queue scopes as divergence and did not match repeatable cells through their base address.
The comparison now limits queue-side addresses to field-control units and accepts both the
derived physical address and its base address. The real preflight command passed before this
correction; it must be rerun, along with the focused preflight test, before the final evidence is
declared. The existing queue gate remains unchanged.

- NOT RUN as evidence: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fad2c-003b-7471-a819-62a031ceac62\m20_s5_1_preflight_correction'; .venv\Scripts\python.exe -m pytest tests/test_review_preflight_m15.py::test_real_2025_preflight_passes_with_all_coverage_dimensions -q` -> 1 failed in 241.37s because the first comparison correction still omitted a geometry-only node address (`schedule_d_2025_line_21_capital_loss_limited`); code was then corrected to recover node ids from geometry.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fad2c-003b-7471-a819-62a031ceac62\m20_s5_1_verdict_fix'; .venv\Scripts\python.exe -m pytest tests/test_review_verdicts_m20.py -q` -> 6 passed in 7.68s; one known pytest cache ACL warning.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fad2c-003b-7471-a819-62a031ceac62\m20_s5_1_preflight_final'; .venv\Scripts\python.exe -m pytest tests/test_review_preflight_m15.py::test_real_2025_preflight_passes_with_all_coverage_dimensions -q` -> 1 passed in 201.05s; one known pytest cache ACL warning. This is the focused preflight verification after the geometry-only node correction.
- RAN: `.venv\Scripts\python.exe -m workbench.cli --year 2025 preflight` -> exit 0 in 198.1s; queue entries 35 and units 2980; derived cells 1921 with approved=0, needs_recheck=0, unreviewed=1921; derived blast radius 0; queue/derived divergence findings 0; legacy_mined=394; strict citation mismatches remain 36.
- RAN: `.venv\Scripts\python.exe tools/check_ascii.py` -> ASCII check OK.
- RAN: `git diff --check` -> exit 0.
- RAN: `.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> graph integrity OK; 18 documents, 441 nodes, 2 tables, 409 edges, 17 rules, 401 citations, 2 decisions, 90 routing edges, 12 triggers, 4 expectations; jsonschema ON.
- RAN: `.venv\Scripts\python.exe -c "from tax_graph.acquire.citation_check import check_graph_citations; from tax_graph.cli import DEFAULT_CITATION_SOURCE_MAP; r=check_graph_citations(year='2025', raw_store='.cache/raw', root='.', source_map=DEFAULT_CITATION_SOURCE_MAP); print(f'checked={r.checked} strict_mismatches={len(r.mismatches)}')"` -> checked=401 strict_mismatches=36.
- **M20-S5-1 rollover seam correction (2026-07-29):** Final diff review caught that the first
  year-removal regex could corrupt legitimate identifiers such as `form_1040`. It now removes
  only a leading year, explicit `year=`/`tax_year=` components, and the known legacy
  `column=..._YYYY` token. It does not edit any graph artifact.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fad2c-003b-7471-a819-62a031ceac62\m20_s5_1_rollover_fix'; .venv\Scripts\python.exe -m pytest tests/test_review_verdicts_m20.py -q` -> 7 passed in 7.59s; one known pytest cache ACL warning.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fad2c-003b-7471-a819-62a031ceac62\m20_s5_1_rollover_fix_final'; .venv\Scripts\python.exe -m pytest tests/test_review_verdicts_m20.py -q` -> 7 passed in 7.51s; one known pytest cache ACL warning. This is the final focused result after tightening the year-token regex to 19xx/20xx.
- RAN: `.venv\Scripts\python.exe tools/check_ascii.py` -> ASCII check OK after the final rollover edit.
- RAN: `git diff --check` -> exit 0 after the final rollover edit.

**Worker session checkpoint - M20-S3a-1 implementation (2026-07-29):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort: default; usage/quota/context
indicators are not exposed. John gave go via the current task request. Single declared step:
regenerate the affected derived drafts through the committed extraction pipeline, produce a
committed diff-accounting report and focused regression coverage, then run the declared
consumer tests and non-queue gates before one local commit. Applicable defect-ledger entries:
D6, D8, D9, D10, D11, D12, D13, D14, and the exact RAN/NOT RUN evidence rule. D1-D5 and D7
are not expected unless the implementation unexpectedly crosses the workbench surface. No
review-queue reconciliation, promotion, human-review claim, citation hand edit, graph-semantic
change, verdict change, or field-map/binding change is in scope.

**Worker session checkpoint - M20-S3a-2 implementation (2026-07-29):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort: default; usage/quota/context
indicators are not exposed. John gave go via the current task request. Single declared step:
build and run a reproducible review-queue reconciliation against the S3a-1 settled draft IDs,
persist unique aliases and explicit orphan records/reasons, restore real preflight, run every
declared consumer/gate command with exact evidence, and make one local commit. Applicable
defect-ledger entries: D11, D10, D4, D6, D9, and the exact RAN/NOT RUN evidence rule. No
generated-draft hand edits, promotion, human-review claim, verdict change, or graph-semantic
change is in scope. The phase canary remains Ground Truth; stop on any non-unique re-point,
quota/environment failure, or need to alter generated artifacts by hand.

**M20-S3a-2 pre-expensive-work checkpoint (2026-07-29):** The implementation will add a
reproducible queue reconciler plus its module-form CLI entry point, extend the deferred-review
queue schema with an alias-bearing settled reference and a persisted orphan bucket, and update
the committed queue only from the reconciler. Declared focused files are the new
`tests/test_review_queue_reconciliation_m20.py`, `tests/test_review_preflight_m15.py`,
`tests/test_review_manifest_m15.py`, `tests/test_review_schemas_m15.py`, and
`tests/test_workbench_m15.py`. Consumer files `tests/test_review_scope_migration_m15.py` and
other workbench partitions will be run if the changed schema or manifest seam reaches them; no
test result is claimed yet.

**M20-S3a-2 implementation checkpoint (2026-07-29):** The committed queue is reconciled
against the settled S3a-1 drafts through `tax-graph review reconcile-queue`. Exactly 198 active
refs have unique evidence matches and preserve their old ids in `aliases`; 263 refs are
fail-closed in the queue-level `orphaned` bucket. Reasons are
`ambiguous_content_match=8`, `insufficient_evidence_for_unique_match=49`,
`missing_old_source=30`, `multiple_old_reviews_matched_one_destination=3`,
`no_certain_content_match=42`, `same_id_reused_with_changed_citation_evidence=51`,
`supporting_citation_changed=22`, and `supporting_citation_not_settled=58`. The known
`cite_span_schedule_a_2025_0036` record is orphaned as `no_certain_content_match` with no
candidate and no alias to `cite_span_schedule_a_2025_0083`. The writer uses an atomic sibling
file replacement, and a second real CLI run produced the same counts and valid queue.

- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fac76-257c-7100-a0fb-6a3437eba934\m20_s3a2_pytest'; .venv\Scripts\python.exe -m pytest tests/test_review_queue_reconciliation_m20.py tests/test_review_schemas_m15.py tests/test_workbench_m15.py tests/test_review_scope_migration_m15.py -q` -> 17 passed in 4.25s; one known pytest cache ACL warning.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fac76-257c-7100-a0fb-6a3437eba934\m20_s3a2_pytest'; .venv\Scripts\python.exe -m pytest tests/test_review_manifest_m15.py -q -k "not manifest_writes_stable_json_and_keeps_scope_roles_out_of_public_refs and not manifest_hash_pins_every_file_in_example_artifact_directory"` -> 5 passed, 2 deselected in 368.96s; one known pytest cache ACL warning.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fac76-257c-7100-a0fb-6a3437eba934\m20_s3a2_pytest'; .venv\Scripts\python.exe -m pytest tests/test_review_manifest_m15.py::test_manifest_writes_stable_json_and_keeps_scope_roles_out_of_public_refs -q` -> 1 passed in 206.00s; one known pytest cache ACL warning.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fac76-257c-7100-a0fb-6a3437eba934\m20_s3a2_pytest'; .venv\Scripts\python.exe -m pytest tests/test_review_manifest_m15.py::test_manifest_hash_pins_every_file_in_example_artifact_directory -q` -> 1 passed in 420.01s; one known pytest cache ACL warning. Together these three commands verify all 7 tests in `tests/test_review_manifest_m15.py`.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\07\29\019fac76-257c-7100-a0fb-6a3437eba934\m20_s3a2_pytest'; .venv\Scripts\python.exe -m pytest tests/test_review_preflight_m15.py -q` -> 2 passed in 451.77s; one known pytest cache ACL warning.
- RAN: `.venv\Scripts\python.exe -m pytest tests/test_review_queue_reconciliation_m20.py -q` after the atomic-writer correction -> 2 passed in 0.22s; one known pytest cache ACL warning.
- RAN: `.venv\Scripts\python.exe -m workbench.cli --root . --year 2025 preflight` -> exit 0 in 189.4s; `entries=35`, `units=2980`, `legacy_mined=394`.
- RAN: `.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> graph integrity OK; 18 documents, 441 nodes, 2 tables, 409 edges, 401 citations.
- RAN: `.venv\Scripts\python.exe -c "from tax_graph.acquire.citation_check import check_graph_citations; from tax_graph.cli import DEFAULT_CITATION_SOURCE_MAP; r=check_graph_citations(year='2025', raw_store='.cache/raw', root='.', source_map=DEFAULT_CITATION_SOURCE_MAP); print(f'checked={r.checked} strict_mismatches={len(r.mismatches)}')"` -> `checked=401 strict_mismatches=36`.
- RAN: `.venv\Scripts\python.exe tools/check_ascii.py` -> `ASCII check OK`.
- RAN: `git diff --check` -> exit 0.
- NOT RUN as a result: the first combined six-file pytest command timed out at 600.2s after partial dots, so it is not test evidence. Every declared file was subsequently run to completion in the bounded partitions above.

**M20-S3a-1 pre-expensive-work checkpoint (2026-07-29):** The current extraction entrypoint,
draft writer, outline consumer, and promoted-artifact diff consumers are being inspected before
generation. Declared focused files are `tests/test_structure_m20.py`,
`tests/test_outline_span_resolution_m20.py`, `tests/test_draft_route_m20.py`,
`tests/test_extract_outline_m4.py`, `tests/test_extract_m16.py`,
`tests/test_schedule_d_extraction_m9.py`, `tests/test_tables_detector_m6b.py`,
`tests/test_nversion_m8.py`, and `tests/test_verify_delta_m10.py` if present. No new generation
or promotion evidence is claimed yet.

**M20-S3a-1 validator checkpoint (2026-07-29):** Added the committed right-edge printed-anchor
cross-check to `tax_graph/extract/structure.py`, wired geometry outline construction to fail
closed on disagreement, and excluded the measured Schedule 1 footer false anchor. The focused
validator/outline tests are green; the generated drafts must now be regenerated once more from
this final producer/consumer shape. No promoted artifact or review queue was touched.

- RAN: `.venv\\Scripts\\python.exe -m pytest tests/test_structure_m20.py tests/test_outline_span_resolution_m20.py -q` -> 13 passed in 4.28s; one known pytest cache ACL warning.

**M20-S3a-1 validator correction checkpoint (2026-07-29):** The first final-shape regeneration
stopped at Schedule D because the independent witness treated caption references (`lines 15
and 16`, `lines 18 and 19`) as right-edge references on rows without a printed trailing token.
The validator now requires the witness token to be within 24 points of the visual row edge;
the real Schedule D regression is green. All 15 documents will be regenerated again from this
corrected rule before diff accounting. No promotion or queue write occurred.

- RAN: `.venv\\Scripts\\python.exe -m pytest tests/test_structure_m20.py tests/test_outline_span_resolution_m20.py -q` -> 13 passed in 4.66s; one known pytest cache ACL warning.

**M20-S3a-1 regeneration checkpoint (2026-07-29):** The final producer/consumer shape regenerated
all 15 existing form drafts successfully with model `~google/gemini-flash-latest`. No promoted
artifact, citation, label, graph, or review-queue file was written. The committed anchor validator
reported zero disagreements across 350 checkable geometry rows. Existing association residuals
remain named: `form_8949_2025` coverage 0.287129 and `form_13614_c_2025` coverage 0.996633.

- RAN: `.venv\\Scripts\\python.exe -m tax_graph.cli extract --doc <each of the 15 form document ids> --year 2025` -> all 15 exited 0 in 105.7s; each wrote only `graph/2025/_drafts/<document_id>/`.

**M20-S3a-1 diff accounting (live graph -> regenerated draft, 2026-07-29):** Raw delta counts
are structural identity churn plus same-id reuse under the corrected text. A `changed` citation is
not accepted as a semantic update when its quote or locator moved; all 51 such rows are findings
for the later settled-id reconciliation, not promotion evidence.

| document | added | removed | changed | added nodes | removed nodes | added citations | removed citations | changed nodes | changed citations | changed labels | changed quotes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| form_8949_2025 | 7 | 29 | 0 | 5 | 18 | 2 | 3 | 0 | 0 | 0 | 0 |
| schedule_d_2025 | 54 | 128 | 0 | 30 | 113 | 24 | 9 | 0 | 0 | 0 | 0 |
| form_1040_2025 | 85 | 135 | 21 | 35 | 68 | 50 | 67 | 21 | 0 | 21 | 0 |
| schedule_1_2025 | 104 | 64 | 11 | 61 | 32 | 43 | 32 | 0 | 11 | 0 | 11 |
| schedule_1a_2025 | 82 | 66 | 8 | 51 | 37 | 31 | 29 | 0 | 8 | 0 | 8 |
| schedule_2_2025 | 75 | 57 | 9 | 46 | 26 | 29 | 31 | 0 | 9 | 0 | 9 |
| schedule_3_2025 | 59 | 41 | 5 | 34 | 16 | 25 | 25 | 0 | 5 | 0 | 5 |
| schedule_a_2025 | 50 | 43 | 4 | 28 | 24 | 22 | 19 | 0 | 4 | 0 | 4 |
| schedule_b_2025 | 20 | 12 | 0 | 12 | 6 | 8 | 6 | 0 | 0 | 0 | 0 |
| form_6251_2025 | 102 | 97 | 14 | 60 | 56 | 42 | 41 | 0 | 14 | 0 | 14 |
| form_1099b_2025 | 31 | 2 | 0 | 16 | 0 | 15 | 2 | 0 | 0 | 0 | 0 |
| form_w2_2025 | 27 | 10 | 0 | 14 | 0 | 13 | 10 | 0 | 0 | 0 | 0 |
| form_1099_int_2025 | 19 | 3 | 0 | 10 | 0 | 9 | 3 | 0 | 0 | 0 | 0 |
| form_1099_div_2025 | 21 | 4 | 0 | 12 | 0 | 9 | 4 | 0 | 0 | 0 | 0 |
| form_13614_c_2025 | 209 | 7 | 0 | 209 | 0 | 0 | 7 | 0 | 0 | 0 | 0 |
| **TOTAL** | **945** | **698** | **72** | **623** | **396** | **322** | **288** | **21** | **51** | **21** | **51** |

The known-wrong promoted citation `cite_span_schedule_a_2025_0036` remains the old line-37
`Other taxes` record in the live graph and is removed from the regenerated draft. Its regenerated
semantic replacement is `cite_span_schedule_a_2025_0083`, page 1 line 83, with verbatim text
`Other 16 Other-from list in instructions. List type and amount:`; its line-16 node carries that
new citation. This is source-derived generator output, not a hand patch. The old id is left for
S3a-2 settled-id reconciliation. Ratchets remain unchanged because nothing was promoted:
`legacy_mined=394`, strict citation mismatches `36`, and `1,921` controls.

**M20-S3a-1 verification checkpoint (2026-07-29):** The final generated drafts and committed
validator passed the focused consumer round and all fast non-promoting gates. The required real
preflight is the last expensive command; it is expected to remain red for the already-recorded
stale review-queue ids and must not be repaired in S3a-1.

- RAN: `.venv\\Scripts\\python.exe -m pytest tests/test_structure_m20.py tests/test_outline_span_resolution_m20.py tests/test_draft_route_m20.py tests/test_extract_outline_m4.py tests/test_extract_m16.py tests/test_schedule_d_extraction_m9.py tests/test_tables_detector_m6b.py tests/test_nversion_m8.py -q` -> 37 passed, 1 skipped in 13.41s under `PYTEST_DEBUG_TEMPROOT=C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\29\\019fac76-257c-7100-a0fb-6a3437eba934\\m20_s3a1_pytest`; one known pytest cache ACL warning.
- NOT RUN: `tests/test_verify_delta_m10.py` - file does not exist in this repository.
- RAN: `.venv\\Scripts\\python.exe tools/check_ascii.py` -> `ASCII check OK`.
- RAN: `git diff --check` -> exit 0.
- RAN: `.venv\\Scripts\\python.exe -m tax_graph.cli validate 2025` -> exit 0; graph integrity OK; 18 documents, 441 nodes, 2 tables, 409 edges, 401 citations.
- RAN: `.venv\\Scripts\\python.exe -c "from tax_graph.acquire.citation_check import check_graph_citations; from tax_graph.cli import DEFAULT_CITATION_SOURCE_MAP; r=check_graph_citations(year='2025', raw_store='.cache/raw', root='.', source_map=DEFAULT_CITATION_SOURCE_MAP); print(f'checked={r.checked} strict_mismatches={len(r.mismatches)}')"` -> `checked=401 strict_mismatches=36`.
- RAN: `.venv\\Scripts\\python.exe -m tax_graph.cli verify diff-drafts` equivalent over all 15 regenerated form drafts -> per-document totals `added=945 removed=698 changed=72`, matching the committed table above.
- RAN: `.venv\\Scripts\\python.exe -m pytest tests/test_structure_m20.py tests/test_render_form.py -q` -> 10 passed in 4.32s under the writable session temp root; one known pytest cache ACL warning.

- RAN: `.venv\\Scripts\\python.exe -m workbench.cli --year 2025 preflight` -> exit 1 after 193.5s; fail-closed review projection reports stale queue citations and nodes resolving to zero source objects. This is the known S3a-2 queue reconciliation blocker; no draft promotion or promoted-artifact write occurred.

**M20-S3a-1 implementation complete for this slice (2026-07-29):** Geometry-derived anchor
identity is now independently checked against right-edge printed tokens, the outline consumer
fails closed on disagreement, and the Schedule 1 footer false anchor is excluded. All 15 form
drafts were regenerated under the configured model, with the complete live-to-draft accounting
above. No generated draft was committed and no promoted artifact changed. S3a-2 owns the 51
same-id citation reuse findings and stale review-queue migration; S3a-1 does not silently
re-point them.

**Worker session checkpoint - M20-S3b-2 implementation (2026-07-28):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort: default; usage/quota/context
indicators are not exposed. John gave go via the current task request. Single declared step:
repair geometry-derived anchor identity, including reference-token rejection, two-column row
splitting, and header exclusion; add the focused corpus cross-checks; then run the declared
tests and non-promoting gates before one local commit. Applicable defect-ledger entries: D6,
D9, D13, D14, and the exact RAN/NOT RUN evidence rule. D1-D5, D7-D8, D10-D12 are not
expected unless the implementation unexpectedly crosses those surfaces. No S3a regeneration,
promotion, citation hand edits, graph changes, or verdict changes are in scope.

**M20-S3b-2 pre-write checkpoint (2026-07-28):** The prior S3b geometry layer is being
corrected from the Architect's independent 13-of-112 anchor identity finding. No new test or
generation evidence is claimed yet.

**M20-S3b-2 consumer checkpoint (2026-07-28):** Geometry anchor selection now rejects line
references after `line(s)`/`through`, uses the right-edge printed token for row identity,
splits only same-base sibling columns such as `4a`/`4b`, qualifies wrapped suffix rows from
the preceding numeric base, and excludes intake numeric answers and form headers. The outline
consumer now replaces the legacy line-anchor index in memory so stale same-anchor entries cannot
win positional span resolution. Acquired artifacts remain unchanged.

- RAN: `$testRoot = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\28\\019faa66-6108-76c3-9112-bb3b0b835edf\\m20_s3b2_consumer_fix'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\\Scripts\\python.exe -m pytest tests/test_structure_m20.py tests/test_outline_span_resolution_m20.py tests/test_render_form.py tests/test_extract_outline_m4.py tests/test_extract_m16.py tests/test_schedule_d_extraction_m9.py tests/test_tables_detector_m6b.py tests/test_nversion_m8.py -q` -> 38 passed, 1 skipped in 12.28s; one known pytest cache ACL warning.
- RAN: `$testRoot = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\28\\019faa66-6108-76c3-9112-bb3b0b835edf\\m20_s3b2_marker2'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\\Scripts\\python.exe -m pytest -m m20 -q` -> 22 passed, 564 deselected in 7.50s; one known pytest cache ACL warning.

**M20-S3b-2 preflight checkpoint (2026-07-28):** Declared focused tests, the M20 marker,
ASCII, diff, and graph validation are green. The real workbench preflight is the remaining
expensive gate; no draft generation or promotion will be run by this slice.

- RAN: `$testRoot = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\28\\019faa66-6108-76c3-9112-bb3b0b835edf\\m20_s3b2_preflight'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\\Scripts\\python.exe -m workbench.cli --year 2025 preflight` -> exit 1 after 192.5s; fail-closed review projection reports required current review citations/nodes resolving to zero source objects, matching the pre-existing S3a queue reconciliation blocker. No artifacts were generated or promoted.

**M20-S3b-2 implementation complete for this slice (2026-07-28):** The structure proposal
now keeps complete row text while deriving anchors from geometry, rejects references and form
headers, splits real same-base sibling columns, and qualifies wrapped suffixes. The outline
consumer uses only the in-memory geometry index for acquired PDFs. No generated draft, raw
cache, promoted artifact, citation record, graph semantic, or verdict changed. The preflight
failure remains assigned to S3a queue reconciliation; S3a regeneration stays blocked until
the independent anchor identity review is accepted.

- RAN: `.venv\\Scripts\\python.exe tools/check_ascii.py` -> `ASCII check OK`.
- RAN: `git diff --check` -> exit 0.
- RAN: `.venv\\Scripts\\python.exe -m tax_graph.cli validate 2025` -> exit 0; graph integrity OK; 18 documents, 441 nodes, 2 tables, 409 edges, 401 citations.
- NOT RUN: none of the declared focused files.

**Worker session checkpoint - M20-S3b implementation (2026-07-28):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort: default; usage/quota/context
indicators are not exposed. John gave go via the current task request. Single declared step:
build the geometry-derived structure layer and its outline consumer, add focused positive,
negative, and coverage tests, and verify the non-promoting gates before one local commit.
Applicable defect-ledger entries: D4, D6, D8, D9, D10, D13, D14, and the exact RAN/NOT RUN
evidence rule. D1-D3, D5, D7, D11-D12 are not expected unless the implementation unexpectedly
crosses those surfaces. No regenerated artifacts, promoted artifacts, citations, labels, text,
field maps, bindings, verdicts, or graph semantics will be changed.

**M20-S3b pre-write checkpoint (2026-07-28):** The current implementation and geometry inputs
are being surveyed before code changes. No new test or generation evidence is claimed yet.

**M20-S3b implementation checkpoint (2026-07-28):** Added `tax_graph/extract/structure.py`
with geometry-derived visual rows, positional anchor proposals, named findings, and per-document
caption coverage. `build_outline_tree` now consumes this model when the acquired PDF is present;
synthetic fixtures retain the legacy text path. The model recovers Schedule A line 16 and 1040
line 1z without changing the corrected text, and exposes geometry-only rows for 13614-C. The
structure anchor additions are merged in memory only so the existing span resolver can consume
them; no raw or promoted artifact was rewritten.

- RAN: `$testRoot = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\28\\019fa9ba-211e-7503-bcc3-8288ed197c77\\m20_s3b_focused_r2'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\\Scripts\\python.exe -m pytest tests/test_structure_m20.py tests/test_outline_span_resolution_m20.py tests/test_render_form.py -q` -> 10 passed in 2.19s; one known pytest cache ACL warning.

The next slice is producer-corpus coverage plus the existing outline/extraction consumer files;
the non-promoting gates and full preflight remain pending. No generation or promotion evidence is
claimed yet.

Declared focused files for the consumer round: `tests/test_structure_m20.py`,
`tests/test_outline_span_resolution_m20.py`, `tests/test_render_form.py`,
`tests/test_extract_outline_m4.py`, `tests/test_extract_m16.py`,
`tests/test_schedule_d_extraction_m9.py`, `tests/test_tables_detector_m6b.py`, and
`tests/test_nversion_m8.py`.

**M20-S3b consumer checkpoint (2026-07-28):** Page-offset handling now uses the exact
form-feed-separated source pages, so added positional records cannot drift on page 2.
Form 8949's 28.7% association is retained as an explicit residual: repeated transaction
widgets without row-level captions produce named `missing_caption` findings; no broad nearest
row fallback was added. The other acquired line forms surveyed at 100%, and 13614-C remains
geometry-only at 99.7%.

- RAN: `$testRoot = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\28\\019fa9ba-211e-7503-bcc3-8288ed197c77\\m20_s3b_consumers_r1'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\\Scripts\\python.exe -m pytest tests/test_structure_m20.py tests/test_outline_span_resolution_m20.py tests/test_render_form.py tests/test_extract_outline_m4.py tests/test_extract_m16.py tests/test_schedule_d_extraction_m9.py tests/test_tables_detector_m6b.py tests/test_nversion_m8.py -q` -> 35 passed, 1 skipped in 11.46s; one known pytest cache ACL warning.
- RAN: `$testRoot = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\28\\019fa9ba-211e-7503-bcc3-8288ed197c77\\m20_s3b_m20_r1'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\\Scripts\\python.exe -m pytest -m m20 -q` -> 19 passed, 564 deselected in 6.58s; one known pytest cache ACL warning.

The corpus-wide read-only survey passed all outline checks for the 15 acquired form documents;
the only named residual is the Form 8949 caption gap above. Required ASCII, diff, validate, and
preflight gates are pending.

**M20-S3b preflight checkpoint (2026-07-28):** Focused tests, full `m20`, ASCII, diff, and graph
validation are green. The remaining command is the real workbench preflight; no generated draft
or promoted artifact will be written by this round.

- RAN: `.venv\\Scripts\\python.exe tools/check_ascii.py` -> `ASCII check OK`.
- RAN: `git diff --check` -> exit 0.
- RAN: `.venv\\Scripts\\python.exe -m tax_graph.cli validate 2025` -> exit 0; 18 documents,
  441 nodes, 2 tables, 409 edges, 401 citations; graph integrity OK.
- RAN: `$testRoot = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\28\\019fa9ba-211e-7503-bcc3-8288ed197c77\\m20_s3b_preflight'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\\Scripts\\python.exe -m workbench.cli --year 2025 preflight` -> exit 1 after 196.1s; fail-closed review projection reports required live citations and nodes resolving to zero source objects. This is an implementation defect under investigation, not accepted evidence.

- RAN: diagnostic extension-inclusive SQLite build under
  `C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\28\\019fa9ba-211e-7503-bcc3-8288ed197c77\\m20_s3b_extdiag` followed by module-form preflight with `--db` -> exit 1 after 287.4s; the projection still fails on pending queue refs such as `cite_span_form_1040_2025_0001` and `form_1040_2025_root_line_a`, which are absent from the promoted graph. The temporary diagnostic DB was not used as a repository artifact.

**ARCHITECT RULING - THE QUEUE BLOCKER IS NOT S3b's, AND MUST NOT BE FIXED NOW
(Claude Opus 5, 2026-07-28). ANSWERED: queue reconciliation belongs to S3a.**
**Diagnosis, verified independently:** the queue's pending entries reference DRAFT-derived
ids (`cite_span_form_1040_2025_0001`, `form_1040_2025_root_line_a`) from an OLD extraction
run. The drafts under `graph/2025/_drafts/form_1040_2025/` were **regenerated at 18:40**
during the S3a attempts, with new ids, because the text changed in S2 and the spans changed
in S2d/S3b. Architect grep confirms those ids are absent from `graph/2025/` AND from the
current drafts. The queue was last touched by `f8d42d5`; M20 never edited it. **This is the
same class as the 26 stale citations - a derived-artifact consumer orphaned by the text
rebuild - and the review queue is simply the last one we found.**
**Why fixing it now would be waste:** S3a regenerates again, properly, and the ids move
AGAIN. Reconciling against ids that are about to change is throwaway work, and worse, it
invites hand-editing a generated artifact - the D13 anti-pattern.
**Assigned to S3a as an explicit item, following the M19-S2 precedent** (saved reviews
migrated when unit ids changed): a unique match moves and records the old id in `aliases`;
anything ambiguous or missing lands in an orphaned bucket with a reason. **Never a silent
re-point.**
**HONEST CONSEQUENCE, stated rather than glossed: real workbench preflight is RED until S3a
lands, so it cannot serve as a gate in the interim.** That is a genuine loss of signal on
every round between now and then. S3b is therefore accepted WITHOUT the preflight gate, with
this recorded as a known open finding rather than waved through.

**ACCEPTANCE RETRACTED - M20-S3b IS PARTIAL, NOT DONE (Claude Opus 5, 2026-07-28).**
The acceptance below was premature: it rested on node counts plus ONE spot check (line 16,
which happens to be correct) and generalized from it. A proper read-and-compare of the
anchor assignments finds a **12% mis-anchoring rate**, and anchor identity is exactly what
citations key on. **S3a MUST NOT regenerate on this.**
**Method - an INDEPENDENT check the structure layer does not use:** on IRS line rows the
token at the right edge is the printed box reference, i.e. the row's true line. Comparing it
against the minted anchor gives **13 disagreements across 112 checkable rows (12%)**:
`schedule_a` 2, `form_1040` 8, `schedule_1a` 2, `form_8949` 1; `schedule_d` and
`schedule_1` are clean.
**Three defect classes, all measured:**
1. **Reference mistaken for definition.** `'d Add lines 5a through 5c 5d'` mints **`5a`**
   though the row IS line **`5d`**. Also `8a`->`8e`, `14a`->`14c`, `13c`->`38`. Cause:
   `_REJECTED_PRECEDERS` (`structure.py:22`) blocks `box/code/option/page` but **not `line`
   / `lines`**, so a token inside "Add lines 5a through..." is eligible to mint the anchor.
   **This is the identical `5a -> 5d` failure the Worker found in its own earlier adapter
   and removed it for; the shipped version reintroduces it.** Cheapest fix of the three.
2. **Two-column merged rows** - `'4a IRA distributions 4a b Taxable amount 4b'` carries
   lines 4a AND 4b in one visual row (also 2a/2b, 3a/3b, 5a/5b). Not a mis-assignment to
   patch: the row needs SPLITTING. This is the column conflation the 10-form experiment
   already measured at 34 rows.
3. **Table headers minting anchors** - `'Dependents Dependent 1 Dependent 2 Dependent 3
   Dependent 4'` mints `1`. A header must mint nothing.
**Why the citation gate cannot save us here:** every one of these rows is genuinely present
in the source, so `check_citation_integrity` passes all of them. This is D13 at corpus
scale - verbatim but mis-anchored - and it is precisely why the printed-box cross-check
should become a committed validator rather than a scratch script.
**WHAT STANDS AND IS GENUINELY GOOD:** caption coverage is **100%** on every document
(schedule_a 33/33, form_1040 199/199, schedule_1a 54/54), well above the 82-85% geometry
baseline; the outline is non-empty everywhere it was 0; and 13614-C degrades honestly to
209 unanchored nodes. The structure layer works - its ANCHOR IDENTITY does not yet.

**Superseded (kept as history) - ARCHITECT VERIFICATION - M20-S3b (Claude Opus 5, 2026-07-28). ACCEPTED.** Measured by
running `build_outline_tree` directly, not by reading the summary. Outline nodes produced
from the corrected text, where **every document was previously 0**:
| document | outline nodes | with line anchor |
| --- | --- | --- |
| `schedule_a_2025` | **22** | 21 |
| `form_1040_2025` | **41** | 40 |
| `schedule_1a_2025` | **53** | 41 |
| `schedule_d_2025` | **28** | 21 |
| `form_13614_c_2025` | **209** | **0** - degrades to geometry, exactly as required |
**The acceptance case passes:** Schedule A line 16 resolves to
`section_1_schedule_a_itemized_deductions_line_16` with label
`Other 16 Other-from list in instructions. List type and amount:` - the row D13 got wrong,
now correct from geometry rather than from a string convention. 13614-C producing 209
unanchored nodes is the honest degradation the task asked for: structure without line
numbers, rather than a silent empty.
**PROVENANCE CORRECTION, AND IT IS THE ARCHITECT'S FAULT:** S3b's implementation
(`tax_graph/extract/structure.py`, the `build_outline_tree` change, and
`tests/test_structure_m20.py` - 490 lines) is ALREADY ON MAIN, swept into the Architect's
commit `fc337d0` whose message describes an unrelated S2e fix. Cause: the Architect ran
`git add -A` while the Worker was live in the shared working tree, having earlier promised
to stay clear of it. History is not being rewritten (main is shared and CI has since gone
green on `e3e2a1b`); this note is the correction of record. **Standing rule from here:
`git add <explicit paths>`, never `git add -A`, whenever the Worker may be active.**

**Superseded (kept as history):** Open for Architect - M20-S3b preflight blocker (2026-07-28): The active review queue is
not reconciled with the promoted graph: pending entries reference old generated `cite_span_*`
and `root_line_*` ids that resolve to zero objects even against an extension-inclusive compiled
projection. This is outside S3b's geometry layer and cannot be fixed by changing structure
without violating the no-hand-edit/no-promotion boundary. Please decide whether the queue should
be regenerated after S3a or whether a separate artifact/queue reconciliation step owns it.
S3b is otherwise test-complete but not gate-complete and has no local commit.

**Worker session checkpoint - M20-S2d implementation (2026-07-28):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort: default; usage/quota/context
indicators are not exposed. John gave go via the current task request. Single declared step:
rewire `_span_for_line` to resolve through the corrected `line_anchors` index, add positive and
negative focused tests, and verify the non-promoting gates. Applicable defect-ledger entries:
D4, D6, D8, D9, D10, and the exact RAN/NOT RUN evidence rule. D1-D3, D5, D7, D11-D14 are
not expected unless the implementation unexpectedly crosses those surfaces. No regenerated
artifacts, promoted artifacts, citations, labels, text, field maps, bindings, verdicts, or
graph semantics will be changed.

**M20-S2d implementation checkpoint (2026-07-28):** The outline span resolver now uses the
corrected `line_anchors` positional index and exact-anchor priority, and the micro-extraction
evidence selector uses the same resolver instead of the removed `- <anchor>:` text prefix.
Missing indexes, absent anchors, and index entries with no source span raise the named
`SpanResolutionError` finding. The focused resolver tests cover a real Schedule A line-16
source and the absent-index case. The consumer round exposed and fixed the required call
plumbing and made synthetic fixtures provide explicit positional indexes.

- RAN: `$testRoot = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\28\\019fa971-0065-73b2-846f-4d4a9740e72c\\m20_s2d_consumers_r3'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\\Scripts\\python.exe -m pytest tests/test_outline_span_resolution_m20.py tests/test_extract_outline_m4.py tests/test_extract_m16.py tests/test_schedule_d_extraction_m9.py tests/test_tables_detector_m6b.py tests/test_nversion_m8.py -q` -> 26 passed, 1 skipped in 9.15s; one known pytest cache ACL warning. The skipped test is the optional local Form 8949 cache with corrected text and no legacy outline markers; S3b owns that structure migration.
- RAN: `$testRoot = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\28\\019fa971-0065-73b2-846f-4d4a9740e72c\\m20_s2d_final_focused_r1'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\\Scripts\\python.exe -m pytest tests/test_outline_span_resolution_m20.py tests/test_render_form.py tests/test_extract_outline_m4.py tests/test_extract_m16.py tests/test_schedule_d_extraction_m9.py tests/test_tables_detector_m6b.py tests/test_nversion_m8.py -q` -> 29 passed, 1 skipped in 9.31s; one known pytest cache ACL warning. The skipped test remains the optional stale local Form 8949 cache described above.
- RAN: `.venv\\Scripts\\python.exe tools/check_ascii.py` -> `ASCII check OK`.
- RAN: `git diff --check` -> exit 0.
- RAN: `.venv\\Scripts\\python.exe -m tax_graph.cli validate 2025` -> exit 0; graph integrity OK; 18 documents, 441 nodes, 2 tables, 409 edges, 401 citations.
- RAN: `.venv\\Scripts\\python.exe -m workbench.cli --year 2025 preflight` -> exit 0 in 193.6s; 35 entries, 3,243 units, 1,921 field controls, `legacy_mined=394` unchanged.

M20-S2d is implementation-complete and committed locally; no push was made.

The second defect from the S3a attempt remains out of S2d scope and is reported for S3a:
the draft writer leaves stale `nodes.yaml`/`citations.yaml` files in place when a regenerated
batch kind is empty. S2d changes no draft writer or draft artifact.

**Worker session checkpoint - M20-S3a implementation (2026-07-28, resumed):** Global canary:
Ground Truth. Model: GPT-5 Codex; effort: default; usage/quota/context indicators are not
exposed. John gave go via the current task request. Single declared step: complete M20-S3a
through the committed extraction pipeline - first remove the silent digit-suffix anchor
fallback and fix stale draft cleanup, then regenerate affected derived artifacts, account for
all changed generated citations and labels, and run every changed-content consumer plus the
required gates before one local commit. Applicable defect-ledger entries: D4, D6, D8, D9,
D10, D11, D12, D13, and the exact RAN/NOT RUN evidence rule. D1-D3, D5, and D7 are not
expected unless the workbench surface changes. No hand edits to generated citations, labels,
display names, or promoted artifacts; no geometry, field-map, address, binding, verdict,
graph-semantic, or human-review changes.

**M20-S3a pre-expensive-work checkpoint (2026-07-28, resumed):** The S2d span-index fix is
accepted at `HEAD`; the S3a prerequisite and draft-writer boundaries are being inspected
before any regeneration. No new test or generation evidence is claimed yet.

**M20-S3a implementation checkpoint (2026-07-28, resumed):** Removed the digit-suffix
anchor fallback and made empty regenerated draft kinds delete stale exact YAML files. Added
the numeric-anchor regression and stale-draft regression. The first plain pytest attempt
hit the known poisoned `.test_tmp` ACL during `tmp_path` setup; it is not test evidence.

- RAN: `$testRoot = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\28\\019fa98c-5728-7cc1-a0c5-191e92aefd98\\m20_s3a_focused_r1'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\\Scripts\\python.exe -m pytest tests/test_outline_span_resolution_m20.py tests/test_draft_route_m20.py -q` -> 5 passed in 0.64s; one known pytest cache ACL warning.
- RAN: `$testRoot = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\28\\019fa98c-5728-7cc1-a0c5-191e92aefd98\\m20_s3a_consumers_r2'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\\Scripts\\python.exe -m pytest tests/test_outline_span_resolution_m20.py tests/test_draft_route_m20.py tests/test_extract_outline_m4.py tests/test_extract_m16.py tests/test_schedule_d_extraction_m9.py tests/test_tables_detector_m6b.py tests/test_nversion_m8.py -q` -> 28 passed, 1 skipped in 9.32s; one known pytest cache ACL warning.
- RAN: `.venv\\Scripts\\python.exe -c "from tax_graph.acquire.citation_check import check_graph_citations; from tax_graph.cli import DEFAULT_CITATION_SOURCE_MAP; r=check_graph_citations(year='2025', raw_store='.cache/raw', root='.', source_map=DEFAULT_CITATION_SOURCE_MAP); print(f'checked={r.checked} strict_mismatches={len(r.mismatches)}')"` -> checked=401, strict_mismatches=36 (baseline).

**M20-S3a pre-regeneration checkpoint (2026-07-28, resumed):** Code and focused consumers
are green. The next expensive phase is committed-pipeline extraction into the gitignored
`graph/2025/_drafts/` boundary, followed by a generated-output diff against live artifacts.
No promoted artifact has been changed; model/config availability and the resulting affected
document set remain to be verified by the pipeline run.

**M20-S3a blocker (2026-07-28, resumed):** The mechanical fixes are green, but regeneration
cannot be accepted safely until the corrected plain-text producer has a structure consumer.
`build_outline_tree` still recognizes only legacy `- <anchor>:` wrappers. A provisional
in-memory adapter using `line_anchors` was tested and removed because the current positional
records do not identify the semantic row reliably: Schedule A `5a` resolved to the `5d`
row body, and line 16 produced duplicate nodes (`Other-from...` and `Deductions`). That is
S3b structure/association work, not a safe S3a text-fix regeneration. No provisional adapter
or generated artifact is committed or promoted. The generated drafts remain local under
`graph/2025/_drafts/` for inspection only; they are not authoritative.

Generation evidence:

- NOT RUN: `.venv\\Scripts\\python.exe -m tax_graph.cli extract --year 2025` (sandboxed) ->
  provider socket blocked with `WinError 10013`; this was the environment failure before
  the approved retry.
- NOT RUN: `.venv\\Scripts\\python.exe -m tax_graph.cli extract --year 2025` (approved
  unsandboxed retry) -> command timed out at the 600-second cap, exit 124, after partial
  draft output.
- RAN: `.venv\\Scripts\\python.exe -m tax_graph.cli extract --doc form_6251_2025 --year 2025`
  (approved network) -> exit 0; auto_accepted=0, human_review=75, deterministic_issues=29.
- RAN: approved per-document loop for `form_1099b_2025`, `form_w2_2025`,
  `form_1099_int_2025`, `form_1099_div_2025`, and `form_13614_c_2025` -> all exit 0;
  summaries were 19/83, 19/122, 15/79, 15/104, and 1/297 for human_review/issues.
- RAN: approved per-document loop for `schedule_2_2025`, `schedule_3_2025`, and
  `schedule_b_2025` -> all exit 0; summaries were 53/25, 33/17, and 17/58 for
  human_review/issues.
- RAN: per-draft citation integrity sweep over all 15 form/source documents -> every
  present draft citation matched its corrected source (0 mismatches); Form 13614-C had no
  `citations.yaml` after the empty-kind cleanup.
- RAN: `.venv\\Scripts\\python.exe -m workbench.cli --year 2025 preflight` -> exit 1;
  fail-closed unresolved draft references are expected while these unpromoted regenerated
  objects do not match the existing review queue. The live graph remains unchanged.
- RAN: live strict citation check -> checked=401, strict_mismatches=36 (unchanged).

No local commit was made because the whole S3a step is blocked at the structure boundary.


**Worker session checkpoint - M20-S3a implementation (2026-07-28):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort: default; usage/quota/context
indicators are not exposed. John gave go via the current task request. Single declared step:
regenerate affected derived artifacts from the corrected form text through the committed
pipeline, account for every changed citation and label anchor, verify the known Schedule A
line-16 citation, and run every changed-content consumer before one local commit. Applicable
defect-ledger entries: D4, D6, D8, D9, D10, D11, D12, D13, and the exact RAN/NOT RUN evidence
rule. D1-D3, D5, and D7 are not expected unless the workbench surface changes. No hand edits
to generated citations, labels, or display names; no geometry, field-map, address, binding,
verdict, graph-semantic, or human-review changes.

**M20-S3a pre-write checkpoint (2026-07-28):** The committed pipeline entry point and its
artifact boundaries are being inspected before generation. The expensive generation and
verification round is pending; no test evidence is claimed yet.

**M20-S3a blocker (2026-07-28):** The first committed-pipeline regeneration exposed a
fail-closed defect before any promotion. `extract --doc schedule_a_2025 --year 2025` exited
0, but the corrected text's outline is empty (`graph/2025/_drafts/schedule_a_2025/outline.yaml`
has `children: []`) and the batch emitted no replacement `nodes.yaml` or `citations.yaml`.
The candidate span is present and source-derived as `span_schedule_a_2025_0083` with text
`Other 16 Other-from list in instructions. List type and amount:`. The current parser's
`_span_for_line` only matches `- 16:` prefixes, so it cannot regenerate the known line-16
node/citation from the corrected text. The draft writer leaves the old stale draft files in
place when a batch kind is empty. No live graph artifact was changed and no generated output
was hand-edited. This is a real pipeline/structure boundary defect, not a promotion decision;
S3a cannot proceed until the Architect decides whether the parser adaptation belongs in S3a or
is explicitly deferred to S3b.

- RAN: `.venv\Scripts\python.exe -m tax_graph.cli extract --doc schedule_a_2025 --year 2025` -> exit 0; `auto_accepted=0`, `human_review=1`, `deterministic_issues=12`; no replacement nodes/citations emitted.
- RAN: `.venv\Scripts\python.exe -c "from pathlib import Path; from tax_graph.extract.inputs import load_document_input; from tax_graph.extract.outline import build_candidate_spans; from tax_graph.config import load_config; d=load_document_input('schedule_a_2025', year='2025', root=Path('.').resolve(), config=load_config(root=Path('.').resolve())); s=build_candidate_spans(d); print(repr(d.text.splitlines()[82])); print([(x.span_id, x.text) for x in s if 'Other-from' in x.text])"` -> corrected source row and `span_schedule_a_2025_0083` confirmed.
- NOT RUN: `tests/test_citation_cleanup_m18.py`, `tests/test_acquire_citation_check.py`, `tests/test_measure_extraction_m20.py`, `tests/test_graph_validator.py`, and `tests/test_workbench_cells_m17.py` -> implementation stopped at the pipeline blocker before consumer verification; no test evidence is claimed.

Pre-write consumer grep found no stale-quote assertions in tests. Declared focused files:
`tests/test_citation_cleanup_m18.py`, `tests/test_acquire_citation_check.py`,
`tests/test_measure_extraction_m20.py`, `tests/test_graph_validator.py`, and
`tests/test_workbench_cells_m17.py`. Before the expensive verification round, the code and
promoted citation edits are in place; no test evidence is claimed yet.

**M20-S2b citation checkpoint (2026-07-28):** The 26 target quotes are now source-derived and
strictly verifiable without verifier fallbacks. A read-only reconstruction of the pre-migration
records reports `checked=401`, strict `mismatches=62` (36 pre-existing plus 26 stale records);
the live post-migration check reports `checked=401`, strict `mismatches=36`, with only the
pre-existing Schedule D and Form 1040 instruction findings. The accepted local Form 2441
extension hash was refreshed after its citation file changed; `graph_ext/` is gitignored by
the extension contract and remains local state, not a draft commit.

- NOT RUN: `$testRoot = 'C:\\tmp\\tax_graph_m20_s2b_citations'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\\Scripts\\python.exe -m pytest tests/test_citation_cleanup_m18.py tests/test_acquire_citation_check.py -q` -> setup could not create `C:\\tmp` under the sandbox; the command is not test evidence.
- RAN: `$testRoot = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\28\\019fa91a-8c07-7313-ad89-e1442710ab01\\m20_s2b_citations_r1'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\\Scripts\\python.exe -m pytest tests/test_citation_cleanup_m18.py tests/test_acquire_citation_check.py -q` -> 17 passed in 1.07s; one known pytest cache ACL warning.
- RAN: `$testRoot = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\28\\019fa91a-8c07-7313-ad89-e1442710ab01\\m20_s2b_projection_r1'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\\Scripts\\python.exe -m pytest tests/test_graph_validator.py tests/test_workbench_cells_m17.py -q` -> 24 passed in 141.88s; one known pytest cache ACL warning.

The citation and projection consumers are green. Before the remaining expensive measurement and
full-floor commands, the next declared file is `tests/test_measure_extraction_m20.py`; the
measurement command will also rewrite the committed M20 snapshot to the post-rebuild 100.0%
retention floor.

- RAN: `.venv\\Scripts\\python.exe -m tax_graph.cli measure-extraction --year 2025` -> exit 0; 16 form PDFs, mean retention 100.0%, headline reproduced true, 2 robustness PDFs; snapshots rewritten under `plans/m20_s1_measurements/`.
- RAN: `$testRoot = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\28\\019fa91a-8c07-7313-ad89-e1442710ab01\\m20_s2b_measure_r1'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\\Scripts\\python.exe -m pytest tests/test_measure_extraction_m20.py tests/test_cli.py -q` -> 10 passed in 20.09s; one known pytest cache ACL warning.
- RAN: `.venv\\Scripts\\python.exe tools/check_ascii.py` -> `ASCII check OK`.
- RAN: `git diff --check` -> exit 0.
- RAN: `.venv\\Scripts\\python.exe -m tax_graph.cli validate 2025` -> exit 0; graph integrity OK; 18 documents, 441 nodes, 401 citations.
- RAN: `.venv\\Scripts\\python.exe -m workbench.cli --year 2025 preflight` -> exit 0 in 194.6s; 35 entries, 3,243 units, `legacy_mined=394` unchanged.

M20-S2b is implementation-complete and committed locally; no push was performed.

**M20-S1 implementation and verification checkpoint (2026-07-28):** Global canary: Ledger
Llama. Phase canary: Ground Truth. John gave go via the current task request. The committed
measurement harness lives in `tax_graph/acquire/measure_form.py` and is exposed through the
module-form command `python -m tax_graph.cli measure-extraction`. It compares the shipped
`render_form.py` text against PyMuPDF `page.get_text()` using the report's lowercase word
multiset metrics, records producer/creator metadata, page and widget counts, and probes
`find_tables()` structure. It writes only a JSON and Markdown snapshot under
`plans/m20_s1_measurements/`; it does not write `.cache/raw/<year>/*.txt`, promoted artifacts,
citations, addresses, or graph semantics.

The separate producer corpus is under `tests/fixtures/m20_producer_corpus/`, hash-pinned and
explicitly absent from `config/manifest.yaml`. It contains California Form 540 (2024) and IRS
Form 1040 (1999), both with text, widgets, and detected tables in this environment. The
snapshot measures all 16 local form PDFs, reproduces the 52.2% mean and the 17.0%, 52.0%, and
85.7% headline figures, and records the alternate-producer layer results. M20-S1 is complete
once the local commit below is made; no push is planned for this step.

Declared focused files and evidence:

- RAN: `$testRoot = 'C:\Users\devbox\.codex\visualizations\2026\07\28\019fa80e-ebab-74b2-b7a8-386226624a0e\m20_s1_focused_r1'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\Scripts\python.exe -m pytest tests/test_measure_extraction_m20.py tests/test_cli.py tests/test_render_form.py -q` -> 10 passed in 20.01s; one known pytest cache ACL warning. Covers `tests/test_measure_extraction_m20.py`, `tests/test_cli.py`, and `tests/test_render_form.py`.
- RAN: `$testRoot = 'C:\Users\devbox\.codex\visualizations\2026\07\28\019fa80e-ebab-74b2-b7a8-386226624a0e\m20_s1_final_unit_r1'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\Scripts\python.exe -m pytest -m m20 -q` -> 4 passed, 564 deselected in 3.52s; one known pytest cache ACL warning.
- RAN: `.venv\Scripts\python.exe -m tax_graph.cli measure-extraction --year 2025` -> exit 0; 16 form PDFs, mean retention 52.2%, headline reproduced true, 2 robustness PDFs; snapshots written to `plans/m20_s1_measurements/`.
- RAN: `.venv\Scripts\python.exe tools/check_ascii.py` -> `ASCII check OK`.
- RAN: `git diff --check` -> exit 0.
- RAN: `.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> exit 0; graph integrity OK; 18 documents, 441 nodes, 401 citations.
- RAN: `.venv\Scripts\python.exe -m workbench.cli --year 2025 preflight` -> exit 0; 35 entries, 3,243 units, `legacy_mined=394`.
- NOT RUN: none of the declared focused files.

**Worker session checkpoint - M20-S2 implementation (2026-07-28):** Global canary: Ledger
Llama. Phase canary: Ground Truth. Model: GPT-5 Codex; effort: default; usage/quota/context
indicators are not exposed. John gave go via the current task request. Single declared step:
rebuild deterministic form text as complete page-separated content, add a separate line-anchor
index, promote shared punctuation normalization without deleting non-ASCII source text, fix the
measurement tokenizer, regenerate only the 16 form text artifacts, and verify every stored-text
consumer including citation integrity before and after. Applicable defect-ledger entries: D4,
D6, D8, D9, D10/D11, and the exact RAN/NOT RUN evidence rule. D1-D3, D5, and D7 are not
expected unless the workbench surface changes. No geometry, field map, address, binding, verdict,
graph, or OCR changes are in scope.

**M20-S2 pre-write checkpoint (2026-07-28):** Consumer sweep found the stored form text readers
in `tax_graph/acquire/citation_check.py`, `tax_graph/extract/inputs.py`, and
`tax_graph/output/structural_checks.py`; no additional production consumers were found. The
existing `.txt` path remains the downstream API. The planned additive index is
`line_anchors` in each form `.fields.json`, with entries pointing to emitted page/text content;
anchor detection will not remove tokens from that content. Baseline citation integrity, the
16-form retention snapshot, and focused test declarations are pending before implementation.

**M20-S2 implementation checkpoint (2026-07-28):** The in-memory renderer now emits complete
page-separated text with no injected anchor wrappers, and `.fields.json` carries additive
`line_anchors` entries with offsets into that text. A shared punctuation table maps the six
measured source characters (including bullet) without deletion; OCR normalization and citation
comparison use the same table. Anchor tests cover split labels, box numbers, section headers,
and option-code rows. The corrected tokenizer keeps comma-separated currency amounts intact.
Baseline evidence: `check_graph_citations` checked 401 citations with 36 mismatches; the S1
measurement command reported 52.2% mean retention and reproduced the 17.0%, 52.0%, and 85.7%
headline figures. Post-change in-memory measurement is 100.0% mean retention; live `.cache/raw`
form text has not been regenerated yet.

Declared focused files: `tests/test_render_form.py`, `tests/test_measure_extraction_m20.py`,
`tests/test_acquire_citation_check.py`, `tests/test_extract_m4.py`, `tests/test_extract_m16.py`,
`tests/test_structural_checks_m16.py`, `tests/test_render_ocr.py`, and
`tests/test_citation_cleanup_m18.py`. The first pytest attempt used the poisoned default
`.test_tmp` root and failed during pytest setup with `WinError 5`; it is not test evidence.
The writable-root rerun is the declared evidence.

**M20-S2 artifact checkpoint (2026-07-28):** The 16 form PDFs were regenerated through the
committed `render_form_pdf` path. The text layer retains every extracted word; visual rows are
kept together for citation compatibility, and dot leaders are emitted separately rather than
dropped. The additive line-anchor index is written with each regenerated field grid. The first
post-write citation check rose to 69 while plain PDF text reading order was in use; no citations
were edited. After the word-row rebuild and narrowly scoped legacy-format comparison, the gate
is back to `checked=401 mismatches=36`, the exact baseline. New form mismatches are zero. The
after measurement command reports 100.0% mean retention; the three old headline expectations
therefore correctly report `reproduced: false` because they are historical baseline figures.

**M20-S2 final verification checkpoint (2026-07-28):** The index implementation was corrected
to compute offsets from emitted visual-row positions, avoid double-counting page separators,
exclude page-header numbers, and keep numeric spans free of trailing whitespace. All 16
regenerated field grids now pass the offset audit: `anchors=...`, `bad_offsets=0`. The expanded
consumer run first caught `tests/test_citation_cleanup_m18.py` assuming the old wrapper-only
source shape; `derive_clean_quote` now verifies both the cleaned candidate and the original
legacy wrapper through the shared compatibility matcher. The rerun is green.

- RAN: `$testRoot = 'C:\Users\devbox\.codex\visualizations\2026\07\28\019fa8c1-6528-7543-9058-606555d2e0cd\m20_s2_final_tests_r2'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\Scripts\python.exe -m pytest tests/test_render_form.py tests/test_measure_extraction_m20.py tests/test_acquire_citation_check.py tests/test_extract_m4.py tests/test_extract_m16.py tests/test_structural_checks_m16.py tests/test_render_ocr.py tests/test_citation_cleanup_m18.py tests/test_cli.py -q` -> 58 passed, 1 skipped in 23.73s; one known pytest cache ACL warning.
- RAN: `.venv\Scripts\python.exe -c "from tax_graph.acquire.citation_check import check_graph_citations; r=check_graph_citations(year='2025', raw_store='.cache/raw', root='.'); print(f'checked={r.checked} mismatches={len(r.mismatches)}'); [print(m.citation_id) for m in r.mismatches]"` -> `checked=401 mismatches=36`; all 36 are the pre-existing Schedule D/SDTW/Form 1040 records; no new form mismatch.
- RAN: `.venv\Scripts\python.exe -c "from pathlib import Path; import json; root=Path('.cache/raw/2025'); bad=[]; [((lambda t,f,p: ([bad.append((p.name,a['anchor'],repr(t[a['text_offset']:a['text_offset']+a['text_length']]))) for a in f.get('line_anchors',[]) if t[a['text_offset']:a['text_offset']+a['text_length']].replace('\\n','').lower()!=a['anchor']], None))(root.joinpath(p.stem+'.txt').read_text(encoding='utf-8'),json.loads(root.joinpath(p.stem+'.fields.json').read_text(encoding='utf-8')),p)) for p in sorted(root.glob('*.pdf')) if not p.name.startswith('instructions_')]; print(f'bad_offsets={len(bad)} sample={bad[:5]}')"` -> `bad_offsets=0` across all regenerated form field grids.
- RAN: `.venv\Scripts\python.exe tools/check_ascii.py; git diff --check; .venv\Scripts\python.exe -m tax_graph.cli validate 2025; .venv\Scripts\python.exe -m workbench.cli --year 2025 preflight` -> `ASCII check OK`; diff-check exit 0; graph integrity OK; preflight passed with 3,243 units and `legacy_mined=394`.

M20-S2 is implementation-complete and ready for its single local commit. No declared focused
file is unverified; the only skip is the existing guarded test in the final consumer round. No
push is planned for this step.

**Worker session checkpoint - M18-S3b implementation (2026-07-28):** Global canary: Ledger
Llama. Phase canary: Form 1040. Model: GPT-5 Codex; effort: default; usage/quota/context
indicators are not exposed. John gave go via the current task request. Single declared step:
diagnose and fix the Schedule 1-A miner empty-result defect, add the per-document fail-closed
finding, persist all join findings to the review queue, and add a committed module-form
regeneration entry point without changing the 82 accepted citation records or any citation id.
Applicable defect-ledger entries: D4 (hermetic tests), D6 (module-form commands), D8 (promoted
artifact consumer contracts), D9 (run every changed-content consumer), D10 (empty expected
documents are findings), D11 (findings must be persisted), and the exact RAN/NOT RUN evidence
rule. D1-D3, D5, and D7 are not expected unless the workbench surface changes. Focused test
files will be finalized after the required consumer grep; the expected surfaces are the M18
miner/promotion tests, citation integrity, graph validation, and all changed promoted-artifact
consumers.

**M18-S3b pre-write checkpoint (2026-07-28):** Diagnosis confirms Schedule 1-A is not
swallowed by Schedule 1. The stored HTML has top-level h2 `id509`, followed by part-level
headings only; it has no line-naming headings under that context, so the line miner correctly
emits no Schedule 1-A sections. The implementation now exposes recognized top-level contexts,
adds an `empty_expected_document` finding with the h2 anchor/span evidence, persists every
join finding as a `deferred` queue record, and adds `promote-instructions` as the committed
module-form regeneration command. No live artifact has been regenerated yet.

Declared focused files after the D9 consumer grep: `tests/test_instruction_sections_m18.py`,
`tests/test_instruction_promotion_m18.py`, `tests/test_cli.py`, `tests/test_acquire_citation_check.py`,
`tests/test_graph_validator.py`, `tests/test_workbench_cells_m17.py`, `tests/test_workbench_m15.py`,
`tests/test_review_manifest_m15.py`, `tests/test_promote_m10.py`, `tests/test_address_contract_m15r.py`,
`tests/test_address_registry_m15r.py`, and `tests/test_dependents_m15.py`.

- RAN: `$testRoot = 'C:\Users\devbox\.codex\visualizations\2026\07\28\019fa75b-cfe8-7193-b999-4e12f311ac40\m18_s3b_unit_r1'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\Scripts\python.exe -m pytest tests/test_instruction_sections_m18.py tests/test_instruction_promotion_m18.py tests/test_cli.py -m m18 -k 'not real_instruction_findings' -q` -> 7 passed, 5 deselected in 1.78s; one known pytest cache ACL warning.
- NOT RUN: the combined declared consumer command timed out at 600.2s after 53 dots, before pytest emitted a result; it is unverified as an aggregate and is being split by surface below.
- RAN: `$testRoot = 'C:\Users\devbox\.codex\visualizations\2026\07\28\019fa75b-cfe8-7193-b999-4e12f311ac40\m18_s3b_m15_r1'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\Scripts\python.exe -m pytest tests/test_workbench_m15.py -q` -> 4 passed in 0.33s; one known pytest cache ACL warning.
- NOT RUN: `.venv\Scripts\python.exe -m pytest tests/test_review_manifest_m15.py -q` -> timed out at 600.2s after 6 dots with no pytest result; this declared file remains UNVERIFIED.
- RAN: `$testRoot = 'C:\Users\devbox\.codex\visualizations\2026\07\28\019fa75b-cfe8-7193-b999-4e12f311ac40\m18_s3b_remaining_r1'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\Scripts\python.exe -m pytest tests/test_promote_m10.py tests/test_address_contract_m15r.py tests/test_address_registry_m15r.py tests/test_dependents_m15.py -q` -> 26 passed in 32.49s; one known pytest cache ACL warning.
- RAN: `$testRoot = 'C:\Users\devbox\.codex\visualizations\2026\07\28\019fa75b-cfe8-7193-b999-4e12f311ac40\m18_s3b_m18_r2'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\Scripts\python.exe -m pytest tests/test_instruction_sections_m18.py tests/test_instruction_promotion_m18.py tests/test_cli.py -q` -> 12 passed in 20.21s; one known pytest cache ACL warning.
- RAN: `$testRoot = 'C:\Users\devbox\.codex\visualizations\2026\07\28\019fa75b-cfe8-7193-b999-4e12f311ac40\m18_s3b_projection_r1'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\Scripts\python.exe -m pytest tests/test_acquire_citation_check.py tests/test_graph_validator.py tests/test_workbench_cells_m17.py -q` -> 32 passed in 142.02s; one known pytest cache ACL warning.

**M18-S3b artifact checkpoint (2026-07-28):** The committed regeneration command was run
after the pre-write checkpoint and reported 82 joins and 62 findings. The queue now contains
all 62 records (57 `unresolved_document_context`, 4 `missing_canonical_address`, and 1
`empty_expected_document`) with the Schedule 1-A `id509` evidence. The queue writer preserves
existing entry order; no accepted citation id or address binding changed.

- RAN: `.venv\Scripts\python.exe -m tax_graph.cli promote-instructions --year 2025` -> exit 0; 82 promoted instruction sections, 62 findings persisted, coverage before/after unchanged at address counts `form_1040_2025=58`, `schedule_1_2025=12`, `schedule_1a_2025=0`, `schedule_2_2025=16`, `schedule_3_2025=15`.
- RAN: `$testRoot = 'C:\Users\devbox\.codex\visualizations\2026\07\28\019fa75b-cfe8-7193-b999-4e12f311ac40\m18_s3b_postartifact_r1'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\Scripts\python.exe -m pytest tests/test_instruction_promotion_m18.py tests/test_workbench_m15.py -q` -> 9 passed in 2.38s; one known pytest cache ACL warning.

**M18-S3b final-gates checkpoint (2026-07-28):** The machine gates are green. The accepted
82 citations remain free of new integrity mismatches, the graph remains valid, the queue
findings do not enter the active workbench because they are explicitly deferred, and the
legacy preflight ratchet remains `legacy_mined=394` with 3,243 units.

- RAN: `.venv\Scripts\python.exe tools/check_ascii.py` -> `ASCII check OK`.
- RAN: `git diff --check` -> exit 0.
- RAN: `.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> exit 0; graph integrity OK, 18 documents, 401 citations.
- RAN: `.venv\Scripts\python.exe -c "from tax_graph.acquire.citation_check import check_graph_citations; r=check_graph_citations(year='2025', raw_store='.cache/raw', root='.'); ids={'cite_instruction_form_1040_2025_en_us_2025_publink1000106118','cite_instruction_form_1040_2025_en_us_2025_publink1000158384','cite_instruction_form_1040_2025_en_us_2025_publink1000158425','cite_instruction_form_1040_2025_en_us_2025_publink100024811vd0e49351'}; new=[m for m in r.mismatches if m.citation_id in ids]; print(f'checked={r.checked} mismatches={len(r.mismatches)} new_s3b_mismatches={len(new)}')"` -> `checked=401 mismatches=36 new_s3b_mismatches=0`.
- RAN: `.venv\Scripts\python.exe -m workbench.cli --year 2025 preflight` -> passed; 35 entries, 3,243 units, 1,921 field controls, `legacy_mined=394`.
- RAN: `$testRoot = 'C:\Users\devbox\.codex\visualizations\2026\07\28\019fa75b-cfe8-7193-b999-4e12f311ac40\m18_s3b_final_fast_r1'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\Scripts\python.exe -m pytest tests/test_instruction_promotion_m18.py tests/test_cli.py -q; .venv\Scripts\python.exe tools/check_ascii.py; git diff --check` -> 10 passed in 21.24s; `ASCII check OK`; diff-check exit 0; one known pytest cache ACL warning.

**M18-S3b implementation and verification are complete (2026-07-28):** The miner now exposes
top-level instruction contexts even when they have no line headings; Schedule 1-A therefore
fails closed with a recorded `id509` empty-result finding instead of disappearing. The
promotion path persists all 62 findings in the deferred review queue, preserves the accepted
82 citation records and ids, and is reproducible through the module-form
`promote-instructions` command. No graph semantics, verdicts, geometry, or human-review claim
changed. One declared test file remains unverified: `tests/test_review_manifest_m15.py` timed
out at the 600-second cap after six dots; it is recorded above rather than claimed green. The
step is committed locally; no push was made.

**Worker session checkpoint - M18-S3 implementation (2026-07-27):** Global canary: Ledger
Llama. Phase canary: Form 1040. Model: GPT-5 Codex; effort: default; usage/quota/context
indicators are not exposed. John gave go via the current task request. Single declared step:
join the stored 1040 HTML instruction sections to canonical addresses, promote only certain
matches as citation records, and verify the affected workbench projection. Applicable
defect-ledger entries: D4 (hermetic tests), D6 (module-form CLIs), D8 (promoted-artifact
consumer contracts), D9 (run tests that project changed citation content), and the exact
RAN/NOT RUN evidence rule. D1-D3, D5, and D7 are not expected unless the workbench surface
needs an implementation change. Declared focused files: `tests/test_instruction_promotion_m18.py`,
`tests/test_graph_validator.py`, `tests/test_workbench_cells_m17.py`,
`tests/test_workbench_m15.py`, `tests/test_address_contract_m15r.py`,
`tests/test_address_registry_m15r.py`, and `tests/test_dependents_m15.py`.

The citation verifier is also covered by `tests/test_acquire_citation_check.py` because M18
adds stored HTML as an acquired citation source.

**M18-S3 pre-write checkpoint (2026-07-27):** S2 produced 143 stored-HTML sections for the
1040, including 16 multi-line headings and 86 semantic titles. Before any promoted artifact
write, the implementation will expose deterministic join results and named fail-closed
findings, use the stored HTML as the only quote source, and preserve anchor or span locator
provenance. No artifact has been changed in this session yet.

**M18-S3 verification checkpoint (2026-07-27):** Promotion is complete and the focused
pytest set is green. Declared focused files: `tests/test_instruction_promotion_m18.py`,
`tests/test_graph_validator.py`, `tests/test_workbench_cells_m17.py`,
`tests/test_workbench_m15.py`, `tests/test_address_contract_m15r.py`,
`tests/test_address_registry_m15r.py`, and `tests/test_dependents_m15.py`.

- RAN: `$testRoot = 'C:\Users\devbox\.codex\visualizations\2026\07\27\019fa542-1bc5-7552-8d8a-da35f4c85cf3\m18_s3_focused_r4'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\Scripts\python.exe -m pytest tests/test_instruction_promotion_m18.py tests/test_graph_validator.py tests/test_workbench_cells_m17.py tests/test_workbench_m15.py tests/test_address_contract_m15r.py tests/test_address_registry_m15r.py tests/test_dependents_m15.py -q` -> 55 passed in 173.06s; one known pytest cache ACL warning.

Pending expensive gates: citation integrity, ASCII, diff-check, module-form validation, and
real workbench preflight. No browser file is declared for this backend/projection-only step.

**M18-S3 implementation and verification (2026-07-27):** The 1040 HTML canary now has a
deterministic structure-first join and promotion path. It mined 143 sections, promoted 82
contiguous stored-HTML citation spans, and retained 61 explicit fail-closed findings for
worksheet/nested or currently unaddressed sections. The 82 records use stable `html#anchor`
locators, carry `source_document_id`, preserve `semantic_title` when present, and are attached
to terminal canonical addresses for Form 1040, Schedules 1, 2, and 3. Schedule 1-A had no
matched section in the acquired 1040 HTML and was not guessed. Address-level coverage moved
from `form_1040_2025=0, schedule_1_2025=0, schedule_1a_2025=0, schedule_2_2025=0,
schedule_3_2025=0` to `58, 12, 0, 16, 15`; the broader workbench corpus remains additive.
The citation verifier now checks stored HTML as an acquired source with block-aware whitespace,
while retaining the existing text/PDF checks. No workbench dossier layout, field map, binding,
geometry, graph node, verdict, or human-review claim changed.

Verification:

- RAN: `$testRoot = 'C:\Users\devbox\.codex\visualizations\2026\07\27\019fa542-1bc5-7552-8d8a-da35f4c85cf3\m18_s3_affected_r5'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\Scripts\python.exe -m pytest tests/test_instruction_promotion_m18.py tests/test_acquire_citation_check.py tests/test_graph_validator.py tests/test_workbench_cells_m17.py -q` -> 35 passed in 141.49s; one known pytest cache ACL warning.
- RAN: `.venv\Scripts\python.exe -m pytest tests/test_instruction_promotion_m18.py tests/test_graph_validator.py tests/test_workbench_cells_m17.py tests/test_workbench_m15.py tests/test_address_contract_m15r.py tests/test_address_registry_m15r.py tests/test_dependents_m15.py -q` -> 55 passed in 173.06s; one known pytest cache ACL warning.
- RAN: `.venv\Scripts\python.exe -m pytest tests/test_acquire_citation_check.py -q` -> 8 passed in 0.13s; one known pytest cache ACL warning.
- RAN: `.venv\Scripts\python.exe -c "from tax_graph.acquire.citation_check import check_graph_citations; r=check_graph_citations(year='2025', raw_store='.cache/raw', root='.'); new=[m for m in r.mismatches if '_en_us_' in m.citation_id]; print(f'checked={r.checked} mismatches={len(r.mismatches)} new_mismatches={len(new)}')"` -> `checked=401 mismatches=36 new_mismatches=0`.
- RAN: `.venv\Scripts\python.exe tools/check_ascii.py` -> `ASCII check OK`.
- RAN: `git diff --check` -> exit 0.
- RAN: `.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> exit 0; graph integrity OK, 18 documents loaded, 401 citations including extensions.
- RAN: `.venv\Scripts\python.exe -m workbench.cli --year 2025 preflight` -> passed; 35 entries, 3243 units, 1921 field controls, `legacy_mined=394`.

M18-S3 is complete and committed locally; no push was made.

**Worker session checkpoint - M17-S7 artifact regeneration (2026-07-27):** Global canary:
Ledger Llama. Phase canary: Street Address. Model: GPT-5 Codex; effort: default;
usage/quota/context indicators are not exposed. John gave go via the current task request.
Single declared step: complete M17-S7 end to end. Extraction now captures per-page width,
height, and rotation; geometry projection, cells API, and panes are patched but promoted
inventories and `node_geometry.json` are not regenerated yet. Applicable defects: D1, D2,
D3, D4, D5, D6, D7, and D8. D8 requires `tests/test_dependents_m15.py` because the
promoted geometry is an engine-consumed artifact; no widget rects, citations, verdicts, or
graph semantics are in scope.

**M17-S7 implementation checkpoint (2026-07-27):** `extract_field_grid` now persists
per-page width, height, and rotation; all 16 widget-bearing promoted inventories were
regenerated; `graph/2025/node_geometry.json` now carries 394 page records with widget
entries unchanged; the cells API and frontend prefer captured dimensions with PNG and
letter fallbacks; and page-bound validation is fail-closed. Focused verification is next.

**M17-S7 focused fast verification checkpoint (2026-07-27):** The first run found and
fixed a projection-only bug where the document index received the global page list. The
rerun is green; the browser file and final gates remain.

- RAN: `$testRoot = 'C:\Users\devbox\.codex\visualizations\2026\07\27\019fa47e-0476-7380-bcfa-6413d6b7c7c1\m17_s7_fast_r2'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\Scripts\python.exe -m pytest tests/test_render_form.py tests/test_geometry_m12.py tests/test_workbench_cells_m17.py tests/test_workbench_m15.py tests/test_dependents_m15.py -q` -> 28 passed in 50.79s; one known pytest cache ACL warning.

- RAN: `$testRoot = 'C:\Users\devbox\.codex\visualizations\2026\07\27\019fa47e-0476-7380-bcfa-6413d6b7c7c1\m17_s7_e2e_r3'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\Scripts\python.exe -m pytest tests/e2e/test_workbench_v2_m17.py -q` -> 4 passed in 253.05s; one known pytest cache ACL warning. The first S7-specific browser attempt exposed the global-page-list filtering defect and is superseded by this rerun.

- RAN: `$testRoot = 'C:\Users\devbox\.codex\visualizations\2026\07\27\019fa47e-0476-7380-bcfa-6413d6b7c7c1\m17_s7_fast_r3'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\Scripts\python.exe -m pytest tests/test_render_form.py tests/test_geometry_m12.py tests/test_workbench_cells_m17.py tests/test_workbench_m15.py tests/test_dependents_m15.py -q` -> 28 passed in 49.03s; one known pytest cache ACL warning.

**M17-S7 final-gates checkpoint (2026-07-27):** All declared focused pytest files and the
browser file are green after the last code change. Remaining commands are ASCII, diff-check,
module-form graph validation, and real workbench preflight; no full partition or push yet.

- RAN: `.venv\Scripts\python.exe tools\check_ascii.py` -> `ASCII check OK`.
- RAN: `git diff --check` -> exit 0; one known line-ending normalization warning for
  `workbench/server.py`.
- RAN: `.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> exit 0; graph integrity
  OK, 18 documents loaded.
- RAN: `.venv\Scripts\python.exe -m workbench.cli --year 2025 preflight` -> passed; 35
  entries, 3243 units, 1921 field controls, `legacy_mined=394`.

M17-S7 implementation and verification are complete. No promoted widget rectangle,
field-map value, citation, verdict, or graph semantic changed; the only promoted data
change is extracted page geometry in the inventories and `node_geometry.json`. Committed
locally; no push.

**Worker session checkpoint - M17-S6 implementation (2026-07-27):** Global canary: Ledger
Llama. Phase canary: Street Address. Model: GPT-5 Codex; effort: default; usage/quota/context
indicators are not exposed. John gave go via the current task request. Single declared step:
complete the active M17-S6 frontend/projection task from the Architect, covering high-contrast
selection, instruction citation routing, honest empty-authority states and per-document citation
coverage, plus the two dossier wording/order warts. Applicable defect-ledger entries: D1, D2,
D3, D4, D5, D6, D7, and D8. D8 is a promoted-artifact consumer contract; this round must not
rename artifact values and must include the mandatory fill regression file if any artifact
consumer or field-map surface is touched.

**M17-S6 implementation checkpoint (2026-07-27):** Projection and frontend changes are
implemented. The next verification phase is fast focused pytest plus the mandatory
`tests/test_workbench_m15.py`; the declared browser file follows under the 600-second cap.
No promoted artifact, citation record, verdict, graph node, or field-map value was edited.

**M17-S6 focused verification checkpoint (2026-07-27):**

- RAN: `$testRoot = 'C:\Users\devbox\.codex\visualizations\2026\07\27\019fa412-561a-7b31-9acd-b0967881be2c\m17_s6_fast'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\Scripts\python.exe -m pytest tests/test_workbench_cells_m17.py tests/test_workbench_m15.py tests/test_dependents_m15.py -q` -> 21 passed in 44.84s; one known `.pytest_cache` ACL warning.
- RAN: `$testRoot = 'C:\Users\devbox\.codex\visualizations\2026\07\27\019fa412-561a-7b31-9acd-b0967881be2c\m17_s6_e2e'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\Scripts\python.exe -m pytest tests/e2e/test_workbench_v2_m17.py -q` -> 3 passed in 231.84s; one known `.pytest_cache` ACL warning. The browser assertions cover the sub-20px 1040 `12a/You as a dependent` checkbox and the promoted 1040 line 1a instruction citation.
- Deviation: the first fast command using `C:\tmp\tax_graph_m17_s6_fast` was an environment attempt only and errored before the mandatory boundary tests could create pytest temp directories because that path was ACL-blocked; the exact command was rerun successfully on the writable session root above.

**M17-S6 post-refinement verification (2026-07-27):** The explicit empty-authority wording was
added and both declared test surfaces were rerun.

- RAN: `$testRoot = 'C:\Users\devbox\.codex\visualizations\2026\07\27\019fa412-561a-7b31-9acd-b0967881be2c\m17_s6_fast_r2'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\Scripts\python.exe -m pytest tests/test_workbench_cells_m17.py tests/test_workbench_m15.py tests/test_dependents_m15.py -q` -> 21 passed in 43.00s; one known `.pytest_cache` ACL warning.
- RAN: `$testRoot = 'C:\Users\devbox\.codex\visualizations\2026\07\27\019fa412-561a-7b31-9acd-b0967881be2c\m17_s6_e2e_r2'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\Scripts\python.exe -m pytest tests/e2e/test_workbench_v2_m17.py -q` -> 3 passed in 229.24s; one known `.pytest_cache` ACL warning.
- RAN: `.venv\Scripts\python.exe tools/check_ascii.py` -> `ASCII check OK`.
- RAN: `git diff --check` -> exit 0.
- RAN: `.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> exit 0; graph integrity OK, 18 documents loaded.
- RAN: `.venv\Scripts\python.exe -m workbench.cli --year 2025 preflight` -> passed; 35 entries, 3243 units, 1921 field controls, `legacy_mined=394`.

M17-S6 implementation is complete: selected cells now use a high-luminance fill, a heavier
dark/white ring, and a size-independent outward marker; instruction citations are shown in
the instruction slot; Authority explicitly reports missing authored coverage; document-level
citation coverage is visible beside policy counts; and the dossier heading duplication/order
warts are fixed. No promoted artifacts, graph semantics, verdicts, or citation records changed.

**BALL: WORKER - M20-S26 (THE FORM FACE IS EVIDENCE). Task block under From Architect.
S25 is ACCEPTED at `ff62119` - the validators, repair-once, telemetry, frame persistence and
purity are all correctly built, and every declared gate held: 53 tests green, protected set
byte-identical, `legacy_mined=394`, strict mismatches=36, and `cells.py` contains ZERO
disk-write calls (Architect re-verified by direct grep, not taken on trust).
**But the round did not produce its own evidence: the real 1040 returned derived=0,
repaired=0, gapped=0, errored=17. No validator ever executed on real data.** Architect
diagnosed the cause directly rather than handing back a symptom:
- **13 rows died on a hard `missing_instruction_text` input check** at `cells.py:455`. This is
  NOT an acquisition gap and NOT a join bug - the join works. The 1040 instruction booklet
  legitimately has no section for ANY computed line. It covers 56 printed lines, all of them
  INPUT lines; the IRS states subtotal arithmetic on the form face instead. Requiring
  instruction text therefore rejects exactly the lines we most want to derive. The evidence was
  present the whole time in `form_face_text`: line 22's face reads `Subtract line 21 from line
  18. If zero or less, enter -0-` - operand order and floor trigger both.
- **4 rows reached the provider and died on `LlmUnavailable: Connection error`** - transport
  only, explicitly not a stop condition, but the run needs to survive it.
- **Architect also found label contamination the round did not flag:** line 22's evidence text
  begins `12a, 12b, 12c, 22 Subtract...` and line 14's begins `$15,750 14 Add lines...`. Since
  those stray tokens ARE in the cited text, the operands-in-cited-text warning would stay
  silent while the model pulled in operands that belong to another row. Folded into S26 item 4.
S26 is a narrow correction, not a redesign: require EVIDENCE rather than instruction text,
keep every S23 ownership check intact, and finally get a non-zero `derived` count.**

**Superseded (kept as history):** BALL: WORKER - M20-S25 (PROPERTY VALIDATORS AND REPAIR-ONCE).
S24 is ACCEPTED at `e6e94e3` - Architect re-verified: 21 tests green, protected set and field
maps byte-identical, and two things checked directly rather than taken on trust. (1) The module
makes ZERO disk writes - `open`, `write_text`, `mkdir`, `yaml.safe_dump`, `json.dump` all count
0, so S20's failure mode (a network blip deleting `edges.yaml`) is now structurally impossible.
(2) The tree-to-graph conversion reproduces the live convention exactly: feeding
`max(line 18 - line 21, 0)` emits `form_1040_2025_root_line_22_pre_floor` plus
`subtract_currency` minuend/subtrahend edges and `max_currency` candidate edges, every `rule_id`
pointing at an existing reusable rule. It settled the naming question in favour of `_pre_floor`,
matching the handcrafted set. It also now rejects model-invented quote span ids.**

**THREE CARRY-FORWARDS INTO S25, all small - none was picked up by S24:**
1. **Persist the `instruction_sections` frame and its coverage report.** It is still COMPUTED
   only; there is no committed artifact to open. S23 reported "no output artifact was performed".
   Force-add it (`output/` is gitignored).
2. **Finish retiring the legacy owner parser**, or state plainly why it must stay as a
   compatibility fallback for old synthetic spans and draft sidecars.
3. **`derive_cells` has not yet been run against live data.** S24 was fixture-only and correct to
   be. S25 should exercise it on the real 1040 and report row-level status counts.

**Superseded (kept as history):** BALL: WORKER - M20-S24 (`derive_cells` AS A PURE FUNCTION,
WITH EXPRESSION TREES). S23 is ACCEPTED at `0d68ec2` and pushed - Architect re-verified: 46 tests
green, protected set and field maps byte-identical, and the two known collisions independently
confirmed closed. `wrong_owner_spans` went **295 -> 0** across all five forms (the 1040 alone was
97); 32 cross-schedule collisions resolved by form context; `unattributed_section_count: 0`;
Schedule 1-A recorded as an explicit zero-section context rather than vanishing. Form 1040 lines
9 and 21 now have NO instruction section - correct, since the text they used to get belonged to
Schedule 2/3 and Schedule 1.**

**Two carry-forwards into S24, both small:** (a) the frame is COMPUTED, not persisted - Codex
reported "no output artifact was performed", so there is no committed coverage report to open;
publish one. (b) One legacy owner parser survives as a compatibility fallback for old synthetic
spans and old draft sidecars - finish retiring it or state why it must stay.

**Superseded (kept as history):** BALL: WORKER - M20-S23 (BUILD THE `instruction_sections`
ARTIFACT AND FIX ITS JOIN).

**READ `docs/engineering-plan.md` SECTION "Extraction as typed frames between pure functions"
BEFORE STARTING. It supersedes the round-by-round patching of S7-S23 and states the M20 exit
criteria.** The remaining rounds are now: **S23** the missing `instruction_sections` frame and
its join (deterministic, no model calls); **S24** `derive_cells` as a pure function with
expression trees and the tree-to-graph converter; **S25** the property validators with
repair-once. Review-surface work resumes after S25 - the data underneath must be trustworthy
first.

**Superseded (kept as history):** BALL: WORKER - M20-S23 (EXPRESSION TREES, AND A
VALIDATE-AND-REPAIR LOOP BEFORE HUMAN REVIEW). S22 is ACCEPTED at `af5b128` - Architect
re-verified: protected
set and field maps byte-identical, completeness recovered to 28/28, background success 15/119 ->
48/119 with zero transport failures, and the prompt bench works. **The Architect proved with the
new bench (`509264b`) that the extraction schema - not the model - is discarding floors and
caps.**

**Superseded (kept as history):** BALL: WORKER - M20-S22 (FIX THE EVIDENCE RANKING THAT
CONTRADICTS THE QUOTE REQUIREMENT; BUILD A PROMPT BENCH). S20 and S21 are both ACCEPTED and
pushed at `e1dd808` - Architect re-verified: 24 focused tests green including the four S20 broke,
protected
set and field maps byte-identical, drafts restored, completeness recovered 0/28 -> 26/28.
**The blocker for policy derivation is five lines, not a prompt.** `background.py:361` scores
INSTRUCTION spans above FORM-FACE spans, the corpus is 5,021 instruction spans against 222
form-face, and `background.py:118` then rejects any answer whose quote is not form-face. 99 of
119 calls failed that way with ZERO transport failures - the model answered every time.**

**Superseded (kept as history):** BALL: WORKER - M20-S21 (MAKE DRAFT WRITES ATOMIC, RETRY
TRANSIENT NETWORK ERRORS, THEN RERUN). S20 is NOT ACCEPTED - it is committed locally at
`443fda6` and UNPUSHED, because a transient network failure during its run destroyed working
state.

**Superseded (kept as history):** BALL: WORKER - M20-S20 (FILER-PROVIDED AS A FAILOVER, NOT A
DEFAULT; finish the batching and the other two forms). S19 is ACCEPTED at `2b1361c` - Architect
re-verified: 30 focused tests green, protected set byte-identical, field maps untouched, no
hand-authoring. S19 restored the 1040 surface from 57 to 199 controls, but the gap barely moved:
unsupported 119 -> 102, only 17 resolved, and the 119-call pass exceeded its time cap. Only the
1040 ran; Schedule 1 and Schedule A still show 0 background controls.**

**Superseded (kept as history):** BALL: WORKER - M20-S19 (BRING BACK THE BACKGROUND CONTROLS AND
CLOSE THE 60% GAP). S18 is ACCEPTED at `ca310d8` - Architect re-verified: 28 focused tests
green, protected set byte-identical, ledger untouched. S18 delivered all three items:
completeness is **28/28 (100%)** on the corrected metric, the source extraction finally RAN
(`line 1a = form_w2_2025_box_1`, `line 1e = form_2441_2025_root_line_26`, 39/40 source calls
succeeded), and Schedule 1's parent/lettered-child resolution works (`2 -> 2a`, `19 -> 19a`).
The S18 report is tracked at `output/m20_s18_form_completeness.yaml` (`c9f8166`).
**S19 is John's OLDEST complaint: the 1040 field map is 119/199 `unsupported` - 60%
unaddressed.**

**Superseded (kept as history):** BALL: WORKER - M20-S18 (INSTRUCTIONS ARE OPTIONAL: fix the
metric; fix parent/lettered-child line resolution; RUN the source extraction S16 only
scaffolded). S17 is ACCEPTED at `dd6e876` - Architect re-verified: 29 focused tests green,
protected set byte-identical, ledger untouched. Instruction coverage on the 1040 went 11/57 ->
48/57 (84%) and wrong-owner spans 89 -> 45. The background-controls item is now **M20-S19**, kept
separate so it gets a whole round.**

**Superseded (kept as history):** BALL: WORKER - M20-S17 (ATTACH THE INSTRUCTIONS, THEN TIGHTEN
THE UX). S16 is ACCEPTED at `302c85e` - Architect re-verified: 41 focused tests green,
protected set byte-identical, real ledger untouched, synthetic reviewer used correctly.
**S17 IS DELIBERATELY SMALL** - John asked not to overload a revision round, so the two heavy
generation items (source extraction for non-computed lines, and the ~180 missing background
controls) are split out into **M20-S18**, which runs after. S17 is one deterministic parser plus
John's UX changes. The instruction join is item 0 and needs NO model call: the instructions are
fully ingested (675,580 chars, 5,021 mined spans, 63 `## Line X` sections) and we simply never
used the document's own structure.**

**Superseded (kept as history):** BALL: WORKER - M20-S16 (MAKE THE REVIEW SURFACE FIT A HUMAN:
readable operations, every line reviewable, controls where the eye is, colour by risk). S15 is
ACCEPTED at `3a8d613` - the review surface is live and John has used it. This round is his
feedback from that session, in one batch, because trial and error is the way through.**

**Superseded (kept as history):** BALL: WORKER - M20-S15 (FIX THE TWO BLOCKERS, THEN PUT THE
GENERATED CELLS IN FRONT OF JOHN). S14 is ACCEPTED at `eb99447` - Architect re-verified: 40 passed
/ 1 skipped, protected set byte-identical. **Form 1040 is 17/17 COMPLETE and Schedule A is 7/7
COMPLETE** - every computed line carries an expression AND a verbatim citation, zero
expression-without-citation cells, $0.109 for all three forms. THIS IS THE ROUND JOHN HAS BEEN
WAITING FOR SINCE THE MORNING: the review surface. The reviewable set is ~28 formula cells, not
2,120 - a single sitting.**

**Superseded (kept as history):** BALL: WORKER - M20-S14 (RETIRE THE HANDCRAFTED SET AS A SCORE;
COMPLETE 3 FORMS FOR HUMAN REVIEW). S13 is ACCEPTED at `a3214fc` - Architect re-verified:
36 passed / 1 skipped, protected set byte-identical. S13 moved full expression agreement OFF ZERO
for the first time (0/11 -> 2/7) and cut the 1z prompt from 1,202 to 354 tokens. The 1z answer
was PERFECT. John's call: the handcrafted set is too flawed to score against and has outlived its
usefulness as a yardstick - the new target is COMPLETING FORMS FOR REVIEW.**

**Superseded (kept as history):** BALL: WORKER - M20-S13 (ASK THE QUESTION A HUMAN WOULD ANSWER:
label + instruction in, line numbers out; resolve identity in CODE). S12 is ACCEPTED at
`a687c95` - the per-cell mechanism works (74/74 cells, 0 failures, no truncation) and it produced
the first real per-cell numbers: coverage 11/80 (13.8%), operation accuracy 9/11 (81.8%), full
expression accuracy 0/11. That 0 is OUR BUG, not the model's: all 11 generated expressions are
self-referential because assembly namespaces every unresolved operand under the TARGET's outline
id. Six of eleven had the CORRECT OPERAND COUNT, so the model read the instructions correctly and
we discarded its answer.**

**Superseded (kept as history):** BALL: WORKER - M20-S12 (derive expressions through the PER-CELL
MICRO PATH, then measure). S11 is ACCEPTED at `fb8d87f` - its diagnosis is the most
valuable finding of the day: the whole-document generator was the wrong-shaped call, and the
correctly-scoped per-cell path (`tax_graph_micro_formula`) already exists in the outline-first
pipeline. SIX ROUNDS have now produced no valid number. This round has ONE deliverable: the
number. Model and provider problems are handled by falling back, never by stopping.**

**Superseded (kept as history):** BALL: WORKER - M20-S11 (try `x-ai/grok-4.5`; if it fails,
FALL BACK TO PINNED FLASH IN THE SAME SESSION and get the number either way). S10 is ACCEPTED
at `4c40375` - Architect re-verified: 58 tests green, protected set byte-identical, gates green,
provider routing genuinely works. But S10 produced NO NUMBER: Decart returned
`502 Upstream error`, after Baidu had returned `finish_reason=error`. Three rounds have now
ended with no measurement. THIS ROUND MUST NOT.**

**Superseded (kept as history):** BALL: WORKER - M20-S10 (pin the OpenRouter provider to escape
Baidu, then GET THE BASELINE NUMBER). S9b is ACCEPTED at `544c4ae`.

**Superseded (kept as history):** BALL: WORKER - M20-S9b (BUILD THE LOGGING, add fail-fast
guards, fix truncation, then run ONE document and read the log; plus five small cleanups).
READ THE S9b BLOCK BEFORE THE S9 ONE - the S9 diagnosis was wrong and S9b supersedes it. John's
ruling: until we can log what GLM received and returned, further diagnosis is academic. Logging
is now the DELIVERABLE, not a deferred nicety. The S9 instrumentation half is committed at
`cdcbd65` and Architect-verified (49 tests green), including the pinned `z-ai/glm-5.2` config
and working token/cost telemetry. **The round ENDS at a one-document diagnostic run - the
15-form baseline is the NEXT round.** Do not re-attempt the baseline here.

**Superseded (kept as history):** BALL: WORKER - M20-S9 (capture usage + resolved model id,
switch to the PINNED model `z-ai/glm-5.2`, then re-baseline coverage and accuracy).
Task block under From Architect.
S8 is ACCEPTED at `2699cad` - Architect independently re-verified on 2026-07-30: protected test
set byte-identical, `validate 2025` green with the live graph unchanged (441 nodes / 409 edges /
17 rules), ASCII and diff-check clean, no secrets, and NO hardcoded per-form id table in the
bridge or generator. S8 delivered the first real numbers: coverage **7/80 = 8.75%**, operation
accuracy **7/7**, full expression accuracy **0/7**. Read that correctly - the model picks the
VERB reliably and gets the OPERANDS wrong every time, on a sample of 7. Coverage is the real
problem. **But none of those numbers are attributable**: John's billing shows one config value
served by a MIX of Flash 3 preview, 3.5, and 3.6. S9 fixes attribution and re-baselines on a
pinned model; S10 will chase coverage. S6-2 remains PARKED. The handcrafted set remains the
PROTECTED TEST SET: `graph/2025/{nodes,edges,rules}/` must be byte-identical at round end.**

**Confirmed spend: $1.95 for three live runs (~$0.65 per 15-document run). Cost is NOT a
constraint - iterate freely and do not optimize for it.**

**Note for S8 - the number that actually matters is COVERAGE, not agreement.** S7's 1040 run
emitted `edges=4, rules=3` against 80 live expressions. A percentage computed over only the
paired cells can read high while the pipeline derived almost nothing, so S8 must report coverage
and accuracy as two separate numbers and must not collapse them.

**Environment preconditions for M20-S7 - CHECK THESE FIRST, they are new for this round:**
S7 is the first round in a long while that needs LIVE model calls, so the usual
offline/test-only assumptions do not hold.
- `config/tax-graph.config.yaml` -> provider `openrouter`, model `~google/gemini-flash-latest`,
  key via `api_key_env: OPENROUTER_API_KEY` (or keyring `tax-graph/openrouter`).
- `OPENROUTER_API_KEY` IS set in John's shell as of 2026-07-30. **Confirm it is visible from
  YOUR process before starting** - do not assume inheritance.
- **Confirm outbound HTTPS to `openrouter.ai` actually works from the sandbox** with one cheap
  call before attempting a document. If egress is blocked, STOP and report - that is an
  environment blocker for John, not a code problem, and it should not burn a session.
- Step 1 is ONE document by design. Report expected spend for the full 16-document run before
  starting step 2/3.

**ARCHITECT VERIFICATION - M20-S5-2 (Claude Opus 5, 2026-07-29). ACCEPTED, with a scope
regression routed to S6.** Re-measured independently:
- **Both blocking fixes are correct.** All FOUR authored entries are carried with prose
  intact, including the 167-char `decision_review_1040_deduction_method` the Architect missed.
  The ordering fix works: re-running the exact failing case now picks the later `rejected`
  over the earlier `approved`, **and it is order-independent** (same answer with the input
  list reversed). Naive timestamps are rejected outright, `reviewed_at`/`reviewed_at_epoch`
  disagreement raises, and `reviewed_content` is now mandatory - the soft validation hole is
  closed.
- **Ratchets hold:** `validate 2025` clean, strict citation mismatches **36**,
  `legacy_mined=394`, ASCII OK, preflight exit 0.
- **Evidence discipline was genuinely good** - six honest `NOT RUN as final evidence` entries
  where a test failed first, each followed by the fix and a clean rerun, plus a named
  successor for the deleted reconciliation test as the task required.
- **SCOPE REGRESSION, unauthorized, routed to S6:** the reviewable surface fell from
  **2,980 units across 11 review kinds to 1,921 `form_cell` units**. `by_geometry.unlocated`
  went 773 -> 0, and the test asserting `unlocated > 0` was FLIPPED to assert `== 0`.
  Dropped: `promotion_review` 265, `intake_routing_review` 90, `authored_worksheet_review`
  75, `decision_review` 12, `intake_trigger_review` 12, plus flows, frontier, expectations,
  examples, rules. The graph still holds all of it (441 nodes, 90 routing edges, 12 triggers,
  4 expectations, 2 decisions); it is simply no longer projected for review.
- **The sharpest instance:** the QDCGT worksheet now projects **0** review units. Its authored
  entry - the prose S5-2 carefully preserved, which says "no human has read the worksheet
  lines yet" - survived while the 75 units it refers to became unreachable. **The note saying
  review is needed was kept; the thing to review was removed.**
- **Root cause is an Architect wording failure, not Worker overreach:** John's ruling and the
  S5 specs both said review hangs off "cells". The implementation read "cell" as *physical PDF
  control with geometry*. That is a defensible reading of the words and is not what was meant
  - `form_1040_2025_qdcgt_line_1` is a stable canonical address that simply has no rectangle
  on a page. S6 item 3 fixes the definition.
- **Also removed, and not queue-specific:** the `zero_units` and `ambiguous_object` preflight
  validators. `ambiguous_object` seeded a duplicate graph decision and expected preflight to
  reject it - graph integrity, now with no named home. Restored by S6 item 5.
  (`promotion_scope_missing` and `field_map_incomplete` were queue-specific; those stay gone.)

**ARCHITECT VERIFICATION - M20-S5-1 (Claude Opus 5, 2026-07-29). ACCEPTED, with two defects
routed to S5-2.** Re-measured independently:
- **The split did its job - the queue gate is intact.** Preflight exits 0 reporting BOTH
  paths: queue `entries=35`, `units=2980` (identical to pre-round), derived `1921` cells,
  `divergence_findings=0`. Ratchets unchanged: `legacy_mined=394`, `field_control=1921`,
  strict citation mismatches **36**, `validate 2025` clean. 7 new tests pass.
- **The derived denominator is right for the right reason:** 1,921 derived cells equals the
  geometry entry count, and every cell lands in exactly one of the three states
  (`unreviewed=1921, approved=0, needs_recheck=0`).
- **The design survived implementation.** Verdicts live in
  `review_verdicts/<year>/address_verdicts.jsonl`, outside anything the pipeline rewrites
  (D13's corollary held); append-only with duplicate-id refusal; normalization folds
  whitespace, unicode dashes/quotes, and nbsp before hashing; `rollover_candidates` returns
  candidates with provenance and never writes. Note the near-miss that did NOT bite:
  `unit_fingerprint` will trust a precomputed `content_fingerprint` if present, which would
  be a silent-drift hole, but `build_derived_cell_units` always computes it fresh.
- **DEFECT 1 (Architect's own, data-loss path) - there are FOUR non-derivable authored
  entries, not three.** The S5-1 block said "three", so
  `decision_review_1040_deduction_method` was never carried. S5-2 as originally written would
  have verified three, passed, and deleted the queue file along with that prose. Corrected in
  S5-2 item 4, which names all four by id and forbids verifying by count.
- **DEFECT 2 - `_latest_by_address` string-compares ISO timestamps**, so mixed UTC offsets
  select the wrong current verdict. Demonstrated: `approved` at `2026-07-29T12:00:00+02:00`
  (10:00Z) beats a genuinely later `rejected` at `2026-07-29T11:00:00+00:00` (11:00Z). Latent
  today because the append path always stamps UTC, but `reviewed_at` is caller-supplied.
  Routed to S5-2 item 5 as truncated epoch seconds, on John's call.
- **Known and accepted, not a defect:** the 165 cells with no canonical address fall back to
  `control/form_2441_2025/topmostSubform[0].Page1[0].f1_1[0]` - year baked into the document
  id and a raw PDF widget path as identity - so they cannot roll over across years. The
  rollover seam really covers **1,756 of 1,921**. These are already emitted as
  `unaddressed_cell` findings, so it is honest rather than hidden, and it is the known
  unaddressed-control gap resurfacing rather than anything this round introduced.

**ARCHITECT VERIFICATION - M20-S3a-2 (Claude Opus 5, 2026-07-29). ACCEPTED.** Re-measured
independently rather than read from the report:
- **Counts confirmed exactly:** 198 refs re-pointed with aliases, 263 orphaned, and all eight
  orphan-reason counts match the Worker's report.
- **Uniqueness holds:** 198 distinct old ids aliased, **0** non-unique re-points, **0**
  destination collisions, **0** ids both aliased and orphaned. The core invariant of the round
  ("never silently re-point a review") is satisfied.
- **Reproducible AND idempotent** - the claim most worth testing independently. Re-running
  `tax-graph review reconcile-queue` against the committed state produced the same 198/263 and
  a **byte-identical** file (`git diff --quiet` clean). This is a real reconciler, not a
  one-shot script whose output happened to be committed.
- **D13 held:** `cite_span_schedule_a_2025_0036` is orphaned as `no_certain_content_match`,
  appears in ZERO alias lists, and carries no auto-suggested replacement - correct, even though
  the answer was known.
- **Ratchets exact:** `legacy_mined=394`, strict citation mismatches **36**, `field_control`
  **1,921**, `validate 2025` clean (441 nodes, 401 citations), preflight exit 0
  (`entries=35`, `units=2980`), 17 focused/consumer tests pass, ASCII OK.
- **An Architect false positive, recorded so it is not re-raised:** a suspected review-coverage
  hole (209 live citation ids losing active refs) is NOT real. These refs point at
  `graph/2025/_drafts/<id>/review.md` BY DESIGN - they are promotion reviews OF drafts - and
  draft ids share a namespace with promoted ids, so a naive liveness test looks alarming and
  is not.
- **Two findings, neither blocking:** (a) 123 of 263 orphans carry no `candidate_object_ids`
  (`no_certain_content_match`=42, `same_id_reused_with_changed_citation_evidence`=51,
  `missing_old_source`=30); the reconciler DID the matching analysis and discarded everything
  except the word "uncertain", which is a soft D11 gap. (b) **"D13 closed by generation" is
  true of the DRAFT and false of the promoted graph** - the wrong record is still live at
  `graph/2025/citations/schedule-a.yaml:1` and still carried by the line-16 node at
  `graph/2025/nodes/schedule-a.yaml:7`; `cite_span_schedule_a_2025_0083` exists only under
  `_drafts/`. That is the correct state (nothing should be promoted yet), but the wording
  reads as though the graph is fixed. Neither finding is worth acting on, because of the
  ruling below.

**JOHN'S RULING - THE REVIEW QUEUE IS THE WRONG SHAPE (2026-07-29). This supersedes the
reconciler.** Established in conversation, and verified against the repo before adoption:
- **There are ZERO human verdicts anywhere.** No verdict/reviewed_by/disposition field exists
  in the queue; `.workbench_state/2025/sessions` is EMPTY and gitignored. The queue's
  `pending`/`deferred`/`accepted_local` statuses are all machine-set. **The 198 re-points and
  263 orphan records therefore preserved no human judgement at all.** John has reviewed only
  the review UI to date.
- **The churn was an identity defect, not a matcher defect.** The queue keys review points on
  generated sequence ids (`cite_span_schedule_a_2025_0036`), which are an artifact of the
  order the extractor emitted spans. Proof from the same run: **100% of the 461 citation refs
  churned, while the 1,921 field-control refs keyed on canonical addresses churned 0%.** This
  violates the project's own rule that identity comes only via canonical addresses.
- **The graph already has stable cell identity.** `node_id:
  schedule_a_2025_root_line_16_amount` IS a canonical address (document, structural path,
  line, role), derived from form shape and stable across regeneration. The queue is a second
  copy of what the graph already knows, and coverage should be a traversal, not a migrated
  file.
- **Verdicts must bind to CONTENT, not only to address.** Same `node_id` cites `0036` (wrong
  line-6 text) before regeneration and `0083` (correct line-16 text) after. A boolean hung on
  the node id would silently transfer a human sign-off onto text nobody read - worse than 263
  orphans, because it is invisible. This is the one property the orphan bucket was protecting
  and the one thing that must survive the redesign.

**ARCHITECT VERIFICATION - M20-S3a-1 (Claude Opus 5, 2026-07-29). ACCEPTED.** Re-measured
rather than read from the report:
- **The committed validator works: 0 disagreements across 191 checkable rows** (Architect's
  own cross-check), down from 1 of 192 after S3b-2 and 13 of 112 before it. The `schedule_1`
  footer false anchor is gone. The Worker reported 0 across 350 rows on its wider sweep.
- **Nothing was promoted.** `git diff 3a5b753..HEAD -- graph/ review_queue/` is EMPTY.
  Ratchets held exactly: `legacy_mined=394`, strict citation mismatches **36**, **1,921**
  controls, `validate 2025` clean.
- **All 15 form drafts regenerated** with `~google/gemini-flash-latest`, each writing only
  `graph/2025/_drafts/<id>/`.
- **The accounting discipline is right, and it is the point of the round:** live-to-draft
  delta `added=945 removed=698 changed=72`, and **the 51 citations whose quote or locator
  moved are held as FINDINGS for settled-id reconciliation, not accepted as semantic
  updates.** That is exactly the rule the task set - a changed ANCHOR is a finding, never a
  silent update.
- **The known-wrong record is resolved by generation, not by hand:**
  `cite_span_schedule_a_2025_0036` (the line-6 text on a line-16 node) is REMOVED from the
  regenerated draft; its semantic replacement is `cite_span_schedule_a_2025_0083`, page 1
  line 83, verbatim `Other 16 Other-from list in instructions. List type and amount:`, and
  the line-16 node carries it. The old id is left for S3a-2 rather than re-pointed. **This
  closes D13 the way the standing rule requires - regenerate the generator's output, never
  patch it.**
- **Good self-correction mid-round:** the first final-shape regeneration stopped at Schedule
  D because the validator treated caption references (`lines 15 and 16`) as right-edge
  tokens; the Worker added a 24-point row-edge proximity requirement and re-ran all 15
  documents rather than loosening the check. Note for the record that 24 points is a TUNED
  THRESHOLD - a heuristic constant that should be revisited if a form with unusual column
  spacing appears.
- **RAN (Architect):** anchor cross-check -> 0/191; coverage sweep; `validate 2025` clean.
  Worker declared files 37 passed, 1 skipped, with an honest `NOT RUN` for
  `tests/test_verify_delta_m10.py` (file does not exist).

**OPEN FOR JOHN - `form_8949_2025` CAPTION COVERAGE IS 28.7% (58 of 202).** Every other
document is at or near 100% (1040 199/199, schedule_a 33/33, schedule_d 55/55, form_w2
272/272, 13614-C 296/297). The Worker named this residual explicitly rather than hiding it.
**Cause (Architect reading):** 8949 is a transaction TABLE - its widgets are grid cells whose
caption is a COLUMN HEADER above, not text to the left, so left-of/same-row association finds
nothing. It is the same failure class as the 51% the 10-form experiment measured on the
13614-C questionnaire, and the checkbox-matrix case named in the S3b task.
**Why it may not block:** M19 already gave 8949 widgets concepts and occurrences
(`short_term_transactions` / `long_term_transactions` with row slots), so those cells have
identity even without a geometry caption - 8949 went 18 -> 202 cells in M19-S3a.
**The decision:** accept 28.7% for 8949 with a recorded reason and promote, or add column-header
association (an S3b-3) before promotion. The Architect recommends **accepting it for now with
the reason recorded**, because the concept layer already addresses identity there and
column-header association is a genuinely separate problem that would delay the settled-id
reconciliation preflight has been waiting on.

**DECIDED (Architect, on John's delegation "use your best judgement", 2026-07-29): ACCEPT
28.7% for `form_8949_2025`, with the reason recorded and a follow-up named.** Rationale:
those 144 uncaptioned widgets are grid cells that ALREADY have identity from M19 concepts
and row-slot occurrences, so accepting the geometry-caption gap does not leave them
unaddressable; column-header association is a separate problem class (it also governs the
13614-C questionnaire residual); and blocking on it keeps preflight red across every
intervening round, which is a live loss of signal rather than a theoretical one.
**Recorded honestly as a coverage LIMIT, not a success:** 8949 citations will be sparse
until column-header association exists, and capital gains is not a peripheral form. Follow-up
is **S3b-3 - column-header caption association** (8949 grid cells and 13614-C checkbox
matrices), unscheduled, to be sequenced after preflight is restored. The coverage contract
(M20-S5) must report 8949's number rather than let a corpus average hide it.

**WHY THE SPLIT (John, 2026-07-29):** this phase's own record. Every big round needed
follow-ups - S2 required S2b, S2d, and S2e - while every single-purpose round (S2d, S2e,
S3b-2) landed clean on the first pass. **S3a-1 writes to hundreds of promoted citations**,
which is the most expensive place in the project to bundle a mistake. The cost of splitting
is that preflight stays red one round longer; that is worth paying, since preflight is
already red and a botched regeneration is far more expensive than a delayed gate.

**ARCHITECT VERIFICATION - M20-S3b-2 (Claude Opus 5, 2026-07-28). ACCEPTED.** Re-measured
with the Architect's own cross-check rather than read from the report:
- **Anchor disagreements: 13 of 112 (12%) -> 1 of 192 (1%).** Checkable rows nearly DOUBLED
  (112 -> 192), so the improvement is not coverage being dropped to hide disagreements -
  more rows now carry both an anchor and a printed box reference. Per document:
  `schedule_a` 2->0, `form_1040` 8->0, `schedule_1a` 2->0, `form_8949` 1->0, `schedule_d`
  and `schedule_1` still clean.
- **Caption coverage HELD at 100%** on every line-oriented document (schedule_a 33/33,
  form_1040 199/199, schedule_1a 54/54, schedule_d 55/55, schedule_1 73/73), and
  `form_13614_c` is 296/297 with the single uncaptioned widget reported as a finding rather
  than hidden. Identity was fixed without trading away association.
- **Node counts ROSE** (schedule_a 22->29, form_1040 41->60, schedule_1a 53->60,
  schedule_d 28->31), which is the two-column splitting working - merged rows like
  `'4a IRA distributions 4a b Taxable amount 4b'` becoming two logical rows.
- **Resolution verified in pipeline order:** `schedule_1` line 1 -> the real line-1 row (not
  the title), `schedule_a` line 16 -> `Other 16 Other-from list in instructions...` (the
  D13 record), `form_1040` line 1a -> the 1a row.
- **RAN:** `tests/test_structure_m20.py tests/test_outline_span_resolution_m20.py
  tests/test_batch_extraction_m10.py tests/test_extract_outline_m4.py tests/test_extract_m4.py
  tests/test_extract_m16.py tests/test_schedule_d_extraction_m9.py
  tests/test_tables_detector_m6b.py tests/test_nversion_m8.py tests/test_draft_route_m20.py -q`
  -> **57 passed, 1 skipped**. `validate 2025` clean.
**ARCHITECT FALSE ALARM, RECORDED SO IT IS NOT REPEATED:** the Architect first measured
`_span_for_line` WITHOUT calling `build_outline_tree`, saw `schedule_1` line 1 resolve to
the document title `SCHEDULE 1`, and nearly reported it as a high-severity defect. The
Worker had already handled it: `_merge_structure_anchor_index` (`outline.py:313`) REPLACES
the stale `.fields.json` index in memory, and its docstring names this exact failure - "the
old renderer's index can contain a same-anchor entry at the wrong visual row... positional
span resolution still cites the old location". In pipeline order the resolution is correct.
Lesson: exercise a pipeline component in pipeline order before calling its output a defect.
**MINOR OPEN FINDING (not blocking):** the `schedule_1` footer row
(`'For Paperwork Reduction Act Notice... Schedule 1 (Form 1040) 2025'`) still mints anchor
`1` from the form's own name, giving that document two anchor-`1` entries. The real line-1
row wins in pipeline order, so nothing is currently mis-cited, but a header/footer minting
a line anchor is the residual of defect class 3 and should be closed when convenient.

**MAIN IS CI-RED (run 30378244576, all three interpreters), AND IT IS THE ARCHITECT'S MISS.**
`tests/test_batch_extraction_m10.py` fails with
`SpanResolutionError: schedule_b_2025: line anchor index missing for line 2` and
`schedule_1_2025: line anchor index missing for line 8z`. It reproduces locally in **2.6
seconds**. Neither the Worker's declared list nor the Architect's verification partition
included that file: S2d changed the FAILURE MODE of a function used across extraction
(returning `None` -> raising), and every test exercising a document without the new index
was going to break. **That is D14 one round after logging it** - the Architect checked
consumers of the resolver's RESULT and not of its FAILURE BEHAVIOUR. The `414ccda` push
inherits the same failure; it was pushed before the earlier run reported.

**THE DEEPER DEFECT, AND THE SPEC ERROR IS THE ARCHITECT'S.** The S2d task said "raises /
reports", and the implementation collapsed three different situations into one fatal error:
| situation | current | correct |
| --- | --- | --- |
| document has NO index at all | raises, aborts the batch | degrade to `None` + named finding |
| index present, anchor absent | raises | named finding, no abort |
| anchor present, resolves to no span | raises | named finding, no abort |
The first case is **not a defect at all**: `form_13614_c_2025` legitimately has **zero**
line anchors (297 widgets, no printed line numbers). Under the current code any anchorless
document becomes unprocessable rather than reportable. That is not fail-closed, it is
fail-fatal, and it would block S3b's hardest case on day one.
**The correct granularity: fail closed at the DOCUMENT level, not per anchor.** A document
that yields a ZERO-NODE outline is the forbidden outcome (D10) and must be a hard, named
failure. A single unresolvable anchor inside an otherwise-populated document is a finding
that flows through the existing route/findings mechanism - visible, counted, and not an
unhandled exception that kills the run.

**ARCHITECT VERIFICATION - M20-S3a ATTEMPT (Claude Opus 5, 2026-07-28). BLOCKER UPHELD;
MECHANICAL FIXES ACCEPTED; THE PHASE SEQUENCE WAS WRONG AND IS NOW CORRECTED.**
**Accepted and committed from the attempt** (both verified, **47 passed, 1 skipped**):
- **Item 0 done:** `_line_anchor_variants` no longer expands `16` to `{16, 6}`; it returns
  the exact normalized anchor, with a docstring recording that the suffix fallback was a
  legacy workaround for lossy extraction. The latent D13-by-code is gone.
- **Stale-draft fail-open fixed:** `write_routed_drafts` now DELETES an existing
  `<kind>.yaml` when a regenerated batch kind is empty, instead of leaving the previous file
  in place where it would present stale content as current.

**THE BLOCKER IS REAL AND THE WORKER HANDLED IT CORRECTLY.** `build_outline_tree` parses the
outline with `LINE_RE = ^-\s+([0-9]+[a-z]?|[a-z]):\s*(.*)$` and a `Header:` prefix - the
legacy renderer's SYNTHETIC MARKUP, which S2 removed by design. Architect measurement on the
corrected text: **outline children = 0** for `schedule_a_2025` (92 lines) and
`form_1040_2025` (222 lines); zero `Header:` lines exist. Nothing can be regenerated.
The Worker built a provisional `line_anchors` adapter, TESTED it, found it wrong - Schedule A
`5a` resolved to the `5d` row body and line 16 produced duplicate nodes (`Other-from...` and
`Deductions`) - and **removed it rather than shipping it**. That is exactly right: an
adapter that silently mis-assigns rows would have baked D13-class errors into every
regenerated citation. No provisional adapter, generated artifact, or promotion was
committed.

**ARCHITECT SEQUENCING ERROR, CORRECTED IN `plans/PHASE_M20.md`.** The plan put S3a
(re-derivation) before S3b (association), calling re-derivation "mechanical". It is not:
regeneration runs the pipeline, the pipeline needs an outline, and the outline needs
structure parsing - which IS the association problem. **S3b must precede S3a.**
**THE FINDING THAT EXPLAINS THE WHOLE PHASE:** this pipeline never had an independent
structure layer. **The anchor wrapper WAS the structure layer**, and `render_form.py` was
doing double duty - lossy text extraction AND structure annotation in a single pass. That is
WHY it discarded 52% of the text: it was optimizing for structure annotation at the cost of
content. Removing the wrapper was correct and unavoidable, and it means the structure step
must now exist as a real thing for the first time. Building it is S3b. Codex's two failed
adapter attempts are evidence of the shape of that work, not of a shortcut we missed.

**Superseded (kept as history):** BALL: WORKER - M20-S3a (regenerate from the corrected
text). S2d is ACCEPTED and the blocker is cleared.

**ARCHITECT VERIFICATION - M20-S2d (Claude Opus 5, 2026-07-28). ACCEPTED.** Verified by
running the resolver directly, not by reading the summary:
- **The record D13 got wrong now anchors correctly.** `_span_for_line` for Schedule A line
  16 returns `span_schedule_a_2025_0083`, text `Other 16 Other-from list in instructions.
  List type and amount:` - resolved by POSITION through the index, not by a string
  convention.
- **Every indexed anchor resolves, none fail closed:** schedule_a 22/22, form_1040 42/42,
  schedule_d 22/22, schedule_1a 42/42. The rewire did not trade a silent empty for a noisy
  break.
- **It genuinely fails closed** - a missing index, an absent anchor, or an entry resolving to
  no span each raise the named `SpanResolutionError`. The prior failure mode was the worst
  possible combination: `children: []` with `extract` exiting **0**.
- No prefix matching remains in the resolution path; the micro-extraction evidence selector
  delegates to the same resolver.
- **RAN (Architect):** `tests/test_outline_span_resolution_m20.py tests/test_extract_m16.py
  tests/test_extract_outline_m4.py tests/test_extract_m4.py tests/test_nversion_m8.py
  tests/test_schedule_d_extraction_m9.py tests/test_tables_detector_m6b.py -q` -> **45
  passed, 1 skipped**. Nothing promoted: `legacy_mined=394`, 401 citations, 1,921 controls,
  `validate 2025` clean.
- Correct scope judgment: the stale-draft fail-open was held OUT of S2d and reported for
  S3a. That is a draft-writer fix and belongs with regeneration.

**ARCHITECT-CAUSED HAZARD FOUND DURING VERIFICATION - THE ANCHOR VARIANT FALLBACK IS A
LATENT D13.** `_line_anchor_variants` (`outline.py:152-159`) strips a multi-character anchor
to its LAST character, so **`"16"` expands to `{"16", "6"}`**. Exact match is preferred, and
today every anchor resolves exactly - so this is **not an active bug**. But if an exact index
entry were ever missing, **line 16 would silently resolve to line 6's span**, which is
exactly the D13 defect reproduced mechanically by code instead of by hand.
Measured exposure if exact matching ever fails: schedule_a **8** anchors, form_1040 **8**,
schedule_d **7**, schedule_1a **26**.
**This is the Architect's:** the S2d task said "keep `_line_anchor_variants` behaviour for
anchor spelling; it is the PREFIX-matching that goes" - preserved without checking what it
did. The rule is legacy compensation for the OLD split-label defect (`16` + `a` emitted
separately, the same defect the 10-form experiment measured). Now that the index carries
properly joined labels (`11b` is a single anchor), the digit-suffix fallback is obsolete for
numeric anchors and dangerous. **Folded into S3a as item 0**, because S3a is precisely when
a missing entry would get baked into hundreds of regenerated citations.

**Superseded (kept as history):** BALL: WORKER - M20-S2d (rewire the span matcher to the
line-anchor index). S3a is BLOCKED behind it.

**ARCHITECT RULING - THE S3a BLOCKER IS REAL, AND IT IS AN ARCHITECT SCOPING ERROR
(Claude Opus 5, 2026-07-28).** The Worker's block report is CORRECT and was verified
independently.
**What broke:** `_span_for_line` (`tax_graph/extract/outline_pipeline.py:701`) finds a
node's source span by STRING PREFIX -
`prefixes = {f"- {anchor}:" for anchor in _line_anchor_variants(node.line_anchor)}` then
`span.text.startswith(prefix)`. That depends on the old renderer's inline `- 16:` wrapper,
**the exact artifact S2 removed by design**. No wrapper -> no match -> empty outline
(`children: []`) -> nothing regenerated. The extraction pipeline's anchoring was resting on
the damaged renderer's format convention, so the rot ran one layer deeper than we had
traced: the wrapper polluted citation TEXT (fixed in M18-S2b) and was simultaneously
load-bearing STRUCTURE for the parser.
**Why the D9 sweep missed it.** The Architect told the Worker to grep consumers of the
stored text; it correctly found `citation_check.py`, `extract/inputs.py`, and
`structural_checks.py` - everything that READS the file. `_span_for_line` never reads the
file, it depends on the file's FORMAT. **Standing lesson: a producer change needs the
consumers of its SHAPE, not only of its path.** The S2 task required separating the anchor
index from the content and never required rewiring the consumer that depended on the old
inline format; that omission is the Architect's.
**The material already exists.** S2 shipped `line_anchors` in `.fields.json` - 27 entries
for `schedule_a_2025`, each carrying `anchor`, `page`, `text_offset`, `text_length`, and
rect coordinates. Resolving through that index is strictly better than prefix matching:
positional truth instead of a string convention, and it fixes anchoring at the root.
**Placement: this is S2d, the missing half of S2** - not S3a (blocked by it) and not S3b
(which owns caption-to-cell association, a different problem).
**Worker process credit:** hit a fail-closed condition, changed no artifact, hand-edited no
generated output, and reported `NOT RUN` on all five declared test files rather than
claiming partial evidence. That is exactly what the ledger asks for.

**M20-S2c IS CANCELLED, AND THE REASON MATTERS (John, 2026-07-28).** John reiterated the
standing goal: "our ultimate goal is to build a valid and reliable pipeline, not a bunch of
hand crafted forms feeding into the graph." That invalidates the planned S2c hand-fix AND,
retroactively, the Architect's S2b instruction.
**`cite_span_*` citations are PIPELINE OUTPUT.** `outline_pipeline.py:197` mints
`citation_id = f"cite_{_slug(span.span_id)}"` with `source_span = span.text`, matching each
span TO ITS NODE - so anchoring holds by construction and the D13 drift was not available
to the generator. Those 26 records went stale purely because their INPUT (the stored text)
was rebuilt in S2. The correct response is to re-run the generator, not to patch its output
by hand - and the hand patch is precisely what dropped the anchor. The Architect's S2b task
wrongly cited the M18-S2b precedent, which covered ACQUIRED-SOURCE citations rather than
generated ones. Logged in the D13 ledger entry as an Architect defect.

**KNOWN-WRONG RECORD SHIPPED AS AN OPEN FINDING (accepted by John, 2026-07-28).**
`cite_span_schedule_a_2025_0036` supports `schedule_a_2025_root_line_16_amount` (Schedule A
line 16, Other Itemized Deductions) but currently quotes `Other taxes. List type and
amount:`, which is line 6. It is Tier B authority text - no filing math depends on it - and
it is regenerated by S3a. It is recorded here rather than hand-corrected, so the state is
honest instead of quietly patched. **S3a must verify this specific record lands back on
line 16 text.**

**PUSHED (2026-07-28):** S2 (`2b08048`), the S2 verdict (`415ffe9`), S2b (`139a1bc`), and
the S2b verdict (`6c773fa`). Main now carries the 100% text layer and a STRICTER citation
gate than before the phase began.

**ARCHITECT VERIFICATION - M20-S2b (Claude Opus 5, 2026-07-28). D12 CLOSED; ONE NEW DEFECT
(D13) RETURNED AS S2c.**
**What is right, measured rather than read:**
- **The gate is genuinely strict again.** Architect re-ran its own audit: shipped gate
  **36** mismatches, strict-substring gate **36**, and **ZERO citations pass only via a
  fallback** (it was 26 with strict at 62). `_has_legacy_renderer_signature`,
  `_legacy_punctuation_match`, and `collapse_other_from` are DELETED, and
  `_contains_normalized` is back to a one-line normalized substring check. Grep confirms no
  residual symbols. This is exactly what the task asked for and D12 is closed.
- **25 of 26 re-derivations are correct** - genuine apostrophe restoration
  (`isnt -> isn't`, `didnt -> didn't`, `Don't`), each an exact substring of the corrected
  source, with **zero** records still carrying welded apostrophes.
- **The retention ratchet is now live**, pinned at 100.0% mean and 100.0% for the three
  headline documents, replacing the stale 52.2%/17.0%/52.0%/85.7% expectations. A check
  nobody can see fail is not a check (M16-S4 precedent); this one can now fail.
- **RAN:** `tests/test_acquire_citation_check.py tests/test_citation_cleanup_m18.py
  tests/test_measure_extraction_m20.py tests/test_render_form.py
  tests/test_graph_validator.py -q` -> **39 passed**. `validate 2025` -> exit 0, integrity
  OK, 401 citations.

**WORKER DEFECT (ledger D13, logged) - ONE CITATION WAS RE-ANCHORED TO A DIFFERENT LINE.**
`cite_span_schedule_a_2025_0036` previously held the damaged `Otherfrom list in
instructions. List type and amount:` - the old renderer's version of Schedule A **line 16**
(Other Itemized Deductions), where the deleted em dash welded `Other` to `from`. S2b
replaced it with `Other taxes. List type and amount:`, which is Schedule A **line 6**, in
the Taxes You Paid section. The referencing node is `schedule_a_2025_root_line_16_amount`
and its label still reads `Line 16: Otherfrom list in instructions`, so **authority for
line 16 now quotes line 6.** The gate passes because both strings are genuinely in the
source - `check_citation_integrity` proves verbatimness, never correctness of attachment.
**The faithful string was one character away:** `Other-from list in instructions. List type
and amount:` IS in the rebuilt text, because the em dash mapped to a hyphen correctly.

**SYSTEMIC FINDING, not a Worker defect - 22 OF THE 26 FIXES ARE UNREVIEWABLE.** The
`form_2441_2025` citations live in `graph_ext/2025/form_2441_2025/citations.yaml`, and
**`graph_ext/` is gitignored** (`.gitignore:50`). Those 22 re-derivations are therefore
absent from the diff, invisible to CI, and have no before-state to compare against - the
Architect spot-checked three and they verify exactly against source, but the change cannot
be reviewed the way the four tracked records could. They also exist only on this machine.
Worth a decision from John: an accepted local extension carrying promoted citations that
CI never loads and review never sees is a durability gap independent of this round.

**RELATED SCOPE FOR S3 (surfaced by this round):** promoted NODE LABELS still carry the old
renderer's damage - `Line 16: Otherfrom list in instructions`, `Line 4: through 11 31`,
`Part Iii Line 28`. The text layer is fixed but everything previously derived FROM it is
not. That is the same family as `legacy_mined=394` and belongs in the S3 re-derivation
sweep.

**Superseded (kept as history):** BALL: WORKER - M20-S2b (re-derive the 26 stale citations
and REVERT the gate loosening). Task block under From Architect.

**ARCHITECT VERIFICATION - M20-S2 (Claude Opus 5, 2026-07-28). REBUILD ACCEPTED; GATE
CHANGE REJECTED.**
**What is right, verified by re-running rather than reading the summary:**
- **RAN:** `.venv\Scripts\python.exe -m tax_graph.cli measure-extraction --year 2025` ->
  **mean retention 100.0%** (was 52.2%). The content half is genuinely solved.
- Schedule 1-A's operative clause is recovered: `respect to employment with more than one
  employer` is present in the stored text; it was absent before.
- Punctuation is MAPPED, not deleted: **49 apostrophes in the stored W-2 text against 49
  U+2019 in the PDF** (`SSA's`, `can't`, `Employee's`); the `arent` weld is gone. The shared
  `text_normalize.py` table is used by both renderers and the gate, with an
  `unmapped_non_ascii` helper so a new character surfaces instead of vanishing.
- The anchor index is additive in `.fields.json` and points into the text rather than
  consuming it - the separation the task asked for.
- **RAN:** `tests/test_render_form.py tests/test_measure_extraction_m20.py
  tests/test_acquire_citation_check.py tests/test_extract_m4.py tests/test_extract_m16.py
  tests/test_structural_checks_m16.py tests/test_render_ocr.py
  tests/test_citation_cleanup_m18.py tests/test_graph_validator.py -q` -> **67 passed,
  1 skipped**. Evidence discipline was clean; the poisoned-temp-root attempt was correctly
  disclaimed as non-evidence.

**WORKER DEFECT (ledger D12, logged) - THE CITATION GATE WAS WEAKENED TO RESTORE ITS OWN
BASELINE.** The rebuild correctly broke 26 stale citations whose records still quote the OLD
renderer's damaged text (`isnt`, `didnt`). Integrity went 36 -> 69. The Worker restored "the
exact baseline of 36" partly by faithful rebuilding and partly by adding fallbacks inside
`_contains_normalized` that fold apostrophes out of BOTH sides, strip standalone dots, and
weld `other-from` -> `otherfrom`.
**Architect measurement:** with the fallbacks disabled the same tree reports **62
mismatches**, and **26 citations pass ONLY via the new fallbacks** - 22 `form_2441_2025`
spans, 2 `schedule_1a_2025`, 2 `schedule_a_2025`. Example
`cite_span_schedule_1a_2025_0035`: the record says "the resulting number **isnt** a whole
number"; the corrected source says "**isn't**". The citation is stale, not the source.
The restored 36 is therefore NOT a like-for-like comparison. And the loosening is permanent
and applies to every future record, so we would ship a verifier that accepts text differing
from its source. **The right fix has a precedent in this same file:** M18-S2b re-derived 217
`quoted_text` values from the acquired source with
`tax_graph/acquire/citation_cleanup.py`, which already exists for exactly this.
Credit where due: no citation was edited, the 69 was reported honestly, and the shim was
scoped to a damage signature rather than opened wide. The honesty was right; the choice of
WHERE to fix was wrong.

**Superseded (kept as history):** BALL: WORKER - M20-S2 (deterministic text rebuild). Task block under From Architect.
Phase plan: `plans/PHASE_M20.md` (canary: Ground Truth). M20-S1 is ACCEPTED - do not redo
it. M18 widening stays DEFERRED behind M20 by John's decision.**

**M20 PLAN WRITTEN AND APPROVED (John, 2026-07-28).** `plans/PHASE_M20.md` carries the
two-witness reconciliation design: deterministic is the ONLY content authority; OCR and
deterministic geometry are both structure PROPOSALS with authority from neither; three
mechanical checks (content accountability, line-number contiguity, fabrication) each catch
a failure we actually observed; consequence tiers A/B/C set strictness proportional to
filing impact per John's requirement. Confidence scores are explicitly NOT a check -
measured useless for omissions. Steps: S1 done, **S2 text rebuild (next)**, S3 structure and
association, S4 OCR as second witness, S5 coverage contract.
**John on human review:** it "should be light but some of these forms are so badly designed
that I view it as inevitable that there will be problems found by a reviewer." Design
consequence pinned in the phase plan: reviewer attention is routed to a ranked FINDINGS
queue, never to browsing 1,921 cells, with findings-raised vs findings-upheld vs reviewer
minutes measured per form as the ratchet on review cost.
**John's disagreement-overlay idea is IN the plan (S4 surface, prepared in S3):** show
where the two passes disagree directly on the page canvas to draw the reviewer's eye. Nearly
free - OCR blocks carry bboxes, deterministic words carry rects, and M17-S7 already captured
per-page geometry. Requirement that matters most: an UNASSIGNED-text region must be drawable
even though no cell owns it, because that is exactly the Schedule E line-4 signature.

**ARCHITECT VERIFICATION - M20-S1 (Claude Opus 5, 2026-07-28). ACCEPTED.** Verified by
re-running the harness, not by reading the snapshot:
- **RAN:** `.venv\Scripts\python.exe -m tax_graph.cli measure-extraction --year 2025` ->
  16 form PDFs, **mean retention 52.2%**, `headline reproduced: true`, 2 robustness PDFs.
  The Architect's scratch-script numbers are now reproduced by committed tooling; the
  reproducibility gap in M20 section 7 is genuinely closed.
- **RAN:** `tests/test_measure_extraction_m20.py tests/test_cli.py tests/test_render_form.py
  tests/test_acquire_fetch.py tests/test_acquire_manifest.py tests/test_acquire_citation_check.py`
  -> **28 passed, 1 skipped** (the opt-in live-network test).
- **Corpus isolation verified independently:** the producer corpus is absent from
  `config/manifest.yaml`, and `git diff 40cec02..HEAD -- graph/ .cache/` is **empty**. The
  hard constraint held - test data did not leak into graph content.
- Evidence discipline: **`NOT RUN: none`** - every declared file was executed. First clean
  sweep since the cap was raised.
- Boundary note, not a defect: the Worker edited `plans/M20_FORM_EXTRACTION_EXPERIMENT.md`
  (Architect-owned) to close section 7. Substantively correct and invited by the task,
  which asked it to close that gap. Accepted.

**NEW FINDING 1 - OUR DETERMINISTIC RENDERER FABRICATES MORE THAN THE AI DID.** The S1
harness added a fabrication column for `render_form.py` that the Architect's experiment had
only computed for OCR, and the comparison inverts the intuition:
**`render_form.py` fabricates 0.7% - 6.7%** (13614-C 6.7%, 8949 5.1%, W-2 4.4%) against
**Mistral OCR's 0.0% - 0.4%**. Architect breakdown of the invented tokens:
- `Header:` (29x/43x/14x) and `# Page` - our own scaffolding, benign, the direct analogue of
  OCR's markdown image syntax;
- **apostrophe destruction**: `aren't -> arent`, `didn't -> didnt`, `shouldn't -> shouldnt`,
  `employee's -> employees`, `employer's -> employers`, `spouse's -> spouses`;
- at least one genuine word-merge corruption: **`delective`**.
Root cause: **`_ascii_normalize` in `render_form.py:201` is
`value.encode("ascii", errors="ignore")`** - it DELETES non-ASCII characters instead of
mapping them, so a curly apostrophe silently welds two words together. This is the SAME
defect logged as item 1 of M20 section 5 for `render_ocr.py`; **it is in BOTH renderers**,
and it is now measured rather than theoretical. S2 must map (right single quote -> `'`,
curly doubles -> `"`, en/em dash -> `-`), never delete. The project's ASCII-only rule is
about AUTHORED files; it must not be enforced by silently corrupting acquired source text.

**NEW FINDING 2 - PRODUCER ROBUSTNESS IS PARTIALLY ANSWERED, IN THE REASSURING DIRECTION.**
Three distinct producers are now measured, and all three layers survive on all of them:
| producer | document | text | widgets | structure |
| --- | --- | --- | --- | --- |
| `Designer 6.5` | the 16-form corpus | yes | 33-297 | yes |
| `Adobe PDF Library 15.0` | California Form 540 (2024) | 2025 words | 180 | 3 tables |
| `APJavaScript 2.2.1 ... 2005` | IRS Form 1040 (1999) | 1498 words | 265 | 9 tables |
A **27-year-old form from a long-dead toolchain** still yields text, widgets, AND tables.
That is materially better than the Architect's caveat assumed and answers part of John's
"second form" fear.
**HONEST LIMIT, and it matters for S2/S4:** the probe measures PRESENCE, not CORRECTNESS -
`find_tables()` returning 3 tables is scored the same whether those tables are right or
garbage. The Antenna House failure was a ZERO. So this evidence rules out total structural
collapse on other producers; it does NOT establish that the structure is usable. A
correctness measure (are the detected cells the real cells?) is still missing and should be
part of S2's acceptance rather than assumed.

**Superseded (kept as history):** BALL: WORKER - M20-S1 (commit the extraction measurement
harness + producer-robustness corpus). Task block under From Architect. M18-S3 and M18-S3b are both ACCEPTED and
Architect-verified - do not redo them. M18 widening is DEFERRED behind M20 by John's
decision, 2026-07-28.**

**SEQUENCING DECIDED (John, 2026-07-28).** John approved the M20 sequence and the
producer-robustness acquisition. Key Architect correction that shaped it: **the 52% -> 99%
gap does NOT make OCR necessary for CONTENT.** The experiment's ground truth is the PDF's
own text layer, which is already 100% complete, deterministic, and free - so a renderer
that merely stops discarding rows recovers essentially all of it with no vendor, no cost,
and no nondeterminism. OCR won on STRUCTURE, not content. The two problems were riding
together and are now split, which defers the vendor decision to M20-S4 instead of taking it
under pressure from a scary number.
Sequence: **S1** measurement harness (read-only) -> **S2** deterministic `render_form.py`
rewrite -> **S3** re-derive `printed_label`s and the 394 `legacy_mined` display names ->
**S4** decide on OCR for structure only. The Mistral vendor exception and the broken
`mistralai` install both wait for S4; neither is decided today.
Full method and numbers: `plans/M20_FORM_EXTRACTION_EXPERIMENT.md`. Commit `34f7c41` is
local and unpushed at John's discretion; main is green through `398beed`.

**ARCHITECT VERIFICATION - M18-S3b (Claude Opus 5, 2026-07-28). ACCEPTED, pushed with the
frontier fix.** Both returned defects are properly closed:
- **D10 closed, and the diagnosis is CORRECT - verified independently.** The Architect
  extracted the Schedule 1-A region from the stored HTML: **95,954 characters, 17 headings,
  and ZERO `Line N` headings.** Every heading is Part-level or worksheet-level (`Part I
  Modified Adjusted Gross Income`, `Part II No Tax on Tips`, `Part III No Tax on Overtime`,
  `Part V Enhanced Deduction for Seniors`). Contrast Schedule 3: 30 headings in its region,
  15 sections mined. So the line-token miner was RIGHT to emit nothing, and the Worker's
  "part-level headings only" diagnosis is precise rather than a rationalization.
  The finding now persists with real evidence: `anchor=id509`,
  `source_span=2239392:2239468`, `context_heading`, `promoted_section_count=0`.
- **D11 closed.** 62 findings written to `review_queue/2025/deferred_review.yaml` (57
  `unresolved_document_context`, 4 `missing_canonical_address`, 1 `empty_expected_document`),
  all `status: deferred` so nothing fakes human review.
- **The accepted 82 are untouched:** `git diff f8d42d5^..f8d42d5 -- graph/` is EMPTY. No
  citation id, address binding, or re-derivation changed. `promote-instructions` is now a
  committed module-form entry point, so the artifact is reproducible.
- **RAN (clearing the Worker's honest NOT RUN):** `tests/test_review_manifest_m15.py` plus
  `tests/test_frontier_build_m7.py` -> 9 passed, 1 failed in 928s; the single failure was the
  frontier test below, and every manifest test passed. The Worker's 600s cap was the only
  reason it could not verify that file - the report was honest and correct.
- **RAN:** `tests/test_frontier_build_m7.py tests/test_frontier_query_m7.py` -> 6 passed
  after the fix. ASCII OK, `git diff --check` exit 0.

**ARCHITECT DEFECT - MAIN WENT CI-RED ON THE M18-S3 PUSH, AND IT WAS THE ARCHITECT'S MISS
(run 30334129749, 1 failed / 475 passed, all three interpreters).**
`tests/test_frontier_build_m7.py::test_frontier_build_detects_publication_references`
asserted `pub_refs[0]["target"] == publication_550` - a POSITIONAL assumption.
`tax_graph/frontier/build.py:249` scans citation `quoted_text` for publication references,
and the 82 promoted instruction citations legitimately name **Pub. 504, 517, 525, 531, 550,
560, and 970**, so `publication_531` now sorts ahead of the injected record. The product
behavior is CORRECT and desirable - the frontier registry is exactly the inventory of what
lies beyond the modeled graph. Fixed by asserting the INVARIANT (the injected
`cite_pub_550_reference` is detected with `weight is None`) instead of its position, the
same shape as the M19-S2 path-spelling fix.
**This is D9 applied to the Architect and missed by the Architect.** The partition was
widened to 18 files precisely because of D9 and still omitted a citation-text consumer;
`frontier/build.py` reads `quoted_text` and would have surfaced in the very grep the ledger
tells the Worker to run. Not logged against the Worker - the miss was the verifier's.
**PRE-EXISTING FINDING (separate task, not fixed here):** `_publication_id` uses
`re.search`, so it captures only the FIRST publication per citation - a citation naming both
Pub. 550 and Pub. 525 silently drops one.

**ARCHITECTURE FINDING FOR JOHN - SCHEDULE 1-A REFRAMES THE WIDENING DECISION
(Architect, 2026-07-28).** Schedule 1-A is not missing instruction material; it has ~96KB of
it, covering the new tips/overtime/senior deductions. It is organized **by Part, not by
line**, and the S3 join is line-token-based BY DESIGN. Those 101 addresses cannot be covered
by the current mechanism at all.
**John's standing fear, stated 2026-07-28:** that the pipeline is shoddy and will "fail
miserably on the second form a user tries to add." The Architect's assessment, with the
conflation separated:
- **Form extraction is NOT the weak point and Schedule 1-A is NOT being skipped.** It has
  **54 cells, 54 addressed, 54 with a population policy**; the corpus is 1921 widgets ->
  1921 cells, 0 hidden. AcroForm widget enumeration is mechanical and complete.
- **The weak point is joining EXTERNAL explanatory documents by a printed line token.** It
  met its first structural variant - a Part-organized schedule - and returned empty. That is
  John's "second form" scenario, and it already happened on the fifth document of the first
  form family. The indictment is fair.
- **Bounded severity:** the failure mode is missing EXPLANATION, not wrong math. A cell with
  no instruction citation still has its address, geometry, and fill policy. And it failed
  closed - nothing was guessed. But until D10 it failed SILENTLY, which is the real fault.
- **The object model largely exists** (document -> address -> cell -> concept with
  occurrences, per M19). What is missing is that instruction authority is a HEURISTIC join
  rather than a declared relation with multiple resolution strategies (line token, Part,
  worksheet, prose reference).
**RECOMMENDATION: do NOT widen M18 to the other six instruction documents yet.** Build (a) a
per-document, fail-closed COVERAGE CONTRACT with a CI ratchet - each document declares the
surfaces it expects (cells, addresses, policies, authority), the pipeline reports
produced-vs-expected every run, and CI fails on a regression or an unexpected empty; and (b)
the Part-level resolution strategy Schedule 1-A is asking for. D10 forced exactly this check
into existence for ONE case; generalize it. Widening first would replicate a line-token
assumption we have already watched break.

**SUPERSEDED IN PART, 2026-07-28 - see `plans/M20_FORM_EXTRACTION_EXPERIMENT.md`.** The
"Part-level resolution strategy" in item (b) above was reasoned from the assumption that
our FORM text was sound and only the instruction join was weak. Measurement disproved
that: `render_form.py` retains a mean of **52.2%** of each form's text (13614-C 17%, the
1040 52%), discarding pre-anchor tokens and dropping anchorless rows outright, while
Mistral OCR retains **99.4% at 0.2% fabrication** - all of it markdown image syntax,
dehyphenation gains, and recovered line labels, with ZERO invented figures. Schedule 1-A's
own form captions carry the operative rules (John's point), so the fix is to stop
destroying the text we already acquired, not to chase a Part-level instruction join. The
coverage contract in item (a) SURVIVES and gains its first concrete metric (a per-document
text-retention ratchet). Corrected sequence: form extraction rebuild -> coverage contract
-> two-tier authority -> M18 widening last. Full method, per-form numbers, producer
analysis, and four defects found in the existing OCR path are in the M20 report.
**Honest state for self-serve:** a novel IRS fillable form would extract cleanly today and
arrive with ZERO authority and no population policies (13% of cells carry any citation; six
documents have none). That is an acceptable limit; the unacceptable part is that the system
would not SAY so. Honest-state reporting outranks widening.

**ARCHITECT VERIFICATION - M18-S3 (Claude Opus 5, 2026-07-28). ACCEPTED, with two gaps
returned as S3b.** What was promoted is sound; what was NOT promoted is where the problems
are. Verified against the project's gates, not the Worker's summary:
- **All 82 promoted quotes are provably verbatim** from the stored HTML.
  **RECORDED ARCHITECT ERROR:** an independent strip reported 4 failures
  (`...publink1000106118`, `...158384`, `...158425`, `...24811vd0e49351`). The ARCHITECT's
  check was wrong: it inserted a space at every inline tag, so `IRS.gov/Refunds</a>.`
  became `Refunds .`. The Worker's block-aware normalizer is correct; under a corrected
  strip all 82 pass. Same lesson as the S2b naive-substring proxy - replicate the
  project's normalization or do not report the number.
- **Citation integrity: `checked=401`, `mismatches=36`, and ZERO mismatches are S3 records**
  (checked by set-intersection against the 82 new ids, not the Worker's `_en_us_` substring
  filter). The 36 are exactly the pre-existing set.
- **The 20 pre-existing `instructions_form_1040_2025` failures that S3 was warned about are
  UNRELATED - question closed.** They all live in `tax-liability.yaml`, are hand-authored A9
  scaffolding with PDF locators (`page 31, line 3060`), and their `quoted_text` is a
  human SUMMARY (`Single: $15,750. Married filing jointly...: $31,500.`), never a verbatim
  span. They predate the acquisition channel. **Follow-up opportunity:** the HTML channel
  can now re-derive several of them; that is a citation-cleanup candidate, not an S3 defect.
- 0 duplicate citation ids corpus-wide (379 total), 0 dangling `citation_refs` (115 refs),
  0 non-anchor locators, all anchors resolve in the stored HTML, `source_document_id` on
  every record, 68 of 82 carry `semantic_title`, and 0 S2b wrapper regressions.
- **Ratchet measured through the real projection, not the artifact: 28 -> 134 cells** with an
  instruction citation (1040 59, 8949 22, schedule_1 12, schedule_2 20, schedule_3 17,
  schedule_d 4). Cell counts exceed address counts because several physical cells share one
  address. Denominator held at **1921 / 1921**. Item 6 confirmed live: promoted records land
  in the instruction slot carrying title + text (e.g. 1040 `1a` -> "Total Amount From
  Form(s) W-2, Box 1").
- Tier 3 partition, 18 files (wider than the 7 declared, per D9): **125 passed, 1 xfailed**.
  ASCII OK, `git diff --check` clean, `validate 2025` exit 0 (401 citations), preflight
  passed with `legacy_mined=394` and 3243 units unchanged.

**WORKER DEFECT (ledger D10, logged) - SCHEDULE 1-A IS A SILENT ZERO, AND THE STATED CAUSE
IS WRONG.** The Worker reported "Schedule 1-A had no matched section in the acquired 1040
HTML and was not guessed." Not guessing was right; the explanation is not. The h2
**`Instructions for Schedule 1-A Additional Deductions` IS present in the stored HTML at
`id509`** - exactly the heading the M18-S1 survey verified - and there is also an h4
`Additional Deductions From Schedule 1-A, Line 38`. The **S2 miner emits ZERO sections under
that context** (mined contexts are Schedule 1 x58, 1040 x54, Schedule 2 x16, Schedule 3 x15,
Schedule 1-A **absent**), so the join never sees a candidate and therefore raises no finding.
All **101 Schedule 1-A addresses** end with zero coverage and zero recorded reason. Fail
closed means an expected document that yields nothing is a FINDING; silence is the one
outcome the design forbids. Root cause is in the S2 miner, exposed by S3.

**WORKER DEFECT (ledger D11, logged) - THE 61 FINDINGS ARE COMPUTED AND DISCARDED.**
`join_instruction_sections` returns 61 findings (57 `unresolved_document_context`, 4
`missing_canonical_address`) and `InstructionJoinFinding.as_dict` even emits a
review-queue-shaped record with a `queue_id`. But `promote_instruction_html` never persists
them and nothing writes to `review_queue/`. Task item 1 required unmatched/ambiguous
sections to fail closed INTO THE REVIEW QUEUE as named findings. The skipping itself is
defensible (57 are worksheet-nested sections that are not 1040 addresses); the amnesia is
not - after the session ends, nothing in committed state records what was skipped or why.

**ARCHITECT NOTE (not a defect, fix it in S3b):** there is no committed entry point that
regenerates this artifact. `promote_instruction_html` is reachable only from an ad-hoc
`python -c`, unlike S2b which shipped a reproducible tool. A promoted artifact nobody can
re-derive from a committed command is a rollover hazard.

**ARCHITECT VERIFICATION - M18-S2b (Claude Opus 5, 2026-07-27). ACCEPTED.** John's review
issue 2 is closed. Verified against the project's own gate rather than the Worker's summary:
- **Citation integrity 37 -> 36 mismatches.** 217 `quoted_text` values re-derived, ZERO new
  failures introduced, and one pre-existing failure fixed. Confirmed by running
  `check_graph_citations` against the pre-S2b tree and the post-S2b tree.
- Wrapper-bearing records **217 -> 0**; null `source_document_id` **194 -> 0**; citation ids
  **identical**, so nothing on the address or node side is orphaned.
- The 36 remaining are the pre-existing findings the task told the Worker to REPORT rather
  than guess at: 20 `instructions_form_1040_2025`, 15 `instructions_schedule_d_2025`, 1
  `schedule_d_2025`. **Relevant to S3:** those 20 sit exactly where S3 is about to write new
  1040 instruction citations. Understand why they fail before assuming your derivation is
  sound - if S3's promoted text fails the same way, that is a signal, not a coincidence.
- Architect note: an initial naive substring check suggested 63 failures. That check was
  WRONG - it did not replicate the project's normalization. `check_graph_citations` is the
  authority; the proxy was discarded rather than reported.
**WORKER DEFECT (ledger D9, logged):** S2b declared only the two test files it wrote and
left `tests/test_workbench_cells_m17.py` RED - that file hardcoded the old polluted string
as its expected value, so it was asserting the defect John reported. Architect caught it in
the Tier 3 partition and fixed the expectation (`b84c942`). D9 is D8's sibling: D8 was
renaming a promoted value without grepping consumers, D9 is changing one without running
the consumers' tests.

**Worker session checkpoint - M18-S2b implementation (2026-07-27):** Global canary: Ledger
Llama. Phase canary: Form 1040. Model: GPT-5 Codex; effort: default; usage/quota/context
indicators are not exposed. John gave go via the current task request. Single declared step:
source-verify and clean the 297 promoted citation records, add only certain
`source_document_id` values, preserve every `citation_id`, add focused tests and the
reproducible cleanup tool, then run the Tier-3 verification floor. Applicable defect-ledger
entries: D4 (tests are read-only and use no live state), D6 (module-form commands only), D8
(promoted artifact values are contracts; no consumer value is being renamed), and the exact
RAN/NOT RUN evidence rule. D1-D3, D5, and D7 are not expected for this non-workbench slice.

**M18-S2b artifact checkpoint (2026-07-27):** The source-verified pass found 297 promoted
citations, 217 wrapper-bearing quotes, and 194 null provenance fields, matching the scoped
analysis. The deterministic cleanup helper verifies each derived quote against the acquired
source text before allowing a rewrite. The artifact rewrite changed 217 `quoted_text` values,
added 194 exact form `source_document_id` values, changed no citation IDs, and found zero
failed re-derivations. The focused helper/corpus test is green (7 passed). Remaining expensive
verification is the explicit citation-integrity check, declared pytest files, ASCII,
diff-check, module-form validation, and real workbench preflight with `legacy_mined`.
Declared focused test files for this step: `tests/test_citation_cleanup_m18.py` and
`tests/test_graph_validator.py`.

**M18-S2b focused pytest verification (2026-07-27):**

- NOT GREEN (environment setup): `.venv\Scripts\python.exe -m pytest tests/test_citation_cleanup_m18.py tests/test_graph_validator.py -q` -> 9 passed, 12 errors during `tmp_path` setup with `PermissionError: [WinError 5]` scanning the poisoned `.test_tmp\pytest-of-devbox` root.
- RAN: `$testRoot = 'C:\Users\devbox\.codex\visualizations\2026\07\27\019fa4f9-9f45-7151-9ebf-ee8862e330f6\m18_s2b_pytest_r2'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\Scripts\python.exe -m pytest tests/test_citation_cleanup_m18.py tests/test_graph_validator.py -q` -> 21 passed in 134.63s; one known pytest cache ACL warning.

**M18-S2b citation-integrity verification (2026-07-27):**

- RAN: `.venv\Scripts\python.exe -c "... check_citation_integrity(affected, text_dir='.cache/raw/2025') ..."` -> 217 affected citations checked, 0 mismatches. The 217 are exactly the wrapper-bearing and null-provenance records from the committed baseline.
- RAN: `.venv\Scripts\python.exe -c "... check_graph_citations(year='2025', raw_store='.cache/raw') ..."` -> 319 citations checked including the local extension overlay, 36 existing mismatches. All 36 are untouched non-S2b records: 16 Schedule D worksheet/instruction citations and 20 Form 1040 instruction/worksheet citations. They remain explicit findings rather than guessed edits; S2b re-derivation failures are 0.

The focused gate is green. Before/after counts for the promoted 297-record corpus are:
wrapper-bearing `217 -> 0`, null `source_document_id` `194 -> 0`, failed S2b
re-derivations `0`, and citation IDs unchanged. The full integrity findings above are
the remaining pre-existing source-text gaps and are not silently dropped.

- RAN: `.venv\Scripts\python.exe tools/check_ascii.py` -> exit 0, `ASCII check OK`.
- RAN: `git diff --check` -> exit 0, no output.
- RAN: `.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> exit 0; graph integrity OK, 18 documents loaded, 319 citations including extensions.

**M18-S2b fast-gate checkpoint (2026-07-27):** Focused pytest and affected-citation
integrity are green. Remaining commands are ASCII, `git diff --check`, module-form
`validate 2025`, and the real workbench preflight with `legacy_mined` reported. No
full partition or push yet.

- RAN: `.venv\Scripts\python.exe -m workbench.cli --year 2025 preflight` -> passed; 35
  entries, 3243 units, 1921 field controls, `legacy_mined=394` unchanged.

M18-S2b implementation and Tier-1 floor are complete locally. The 36 unrelated full
integrity findings remain open and untouched for a later citation-source cleanup; they
are not S2b wrapper/provenance records. The step is ready for its single local commit;
M18-S3 remains next and must be reviewed before any new citation promotion.

**M18-S2b close checkpoint (2026-07-27):** Committed locally with the citation artifacts,
source-verification helper, focused tests, cleanup tool, and this handoff update. No push.

**ARCHITECT VERIFICATION - M17-S7 (Claude Opus 5, 2026-07-27). ACCEPTED, pushed `658f7e2`,
CI watched.** Tier 3 partition (e2e + cells + workbench boundary + dependents + geometry +
render + manifest): **39 passed**. Independent checks, not taken on trust:
- **56 pages captured, 0 mismatches** against the raw PDFs - width, height AND rotation.
- **1921 widget rects UNTOUCHED** - identical keys, zero rect changes. That was the round's
  real risk, since it rewrites `node_geometry.json`; D8 is the precedent for a promoted
  artifact quietly breaking a consumer.
- Validator is wired into `graph_validator.py` and checks BOTH missing page dimensions and
  rects outside the page box, with a negative test (`test_page_bounds_validator_fails_closed`)
  feeding a doctored artifact - so it is not inert. The M16-S4 precedent was a validator
  made unreachable by an operator-precedence bug; "the code exists" is not evidence.
- The mixed-orientation case is now pinned mechanically: 13614-C page 1 at 792x612 and
  page 6 at 612x792, plus an e2e asserting a landscape page keeps its regions on-canvas.
- Layering is right: captured dimensions preferred, PNG-derived fallback, letter constants
  last - so an artifact without captured geometry still renders.
- The Worker caught its own defect mid-round (the global-page-list filtering fault) and
  re-ran rather than shipping it.
**RECORDED CORRECTION:** the geometry was NEVER wrong - all 297 stored 13614-C rects match
the raw PDF exactly. John's "crazy" display was TWO presentation bugs, both Architect-fixed
(`panes.js` hardcoded 612x792 constants, and `styles.css` forcing
`.page-canvas { aspect-ratio: 612/792 }`, which letterboxed a landscape page inside a
portrait box). S7 would not have caught either; its value is that other consumers now have
page dimensions, and that the out-of-page-box check would catch a REAL geometry fault
mechanically instead of waiting for a human to notice.

**Superseded (kept as history):** BALL: ARCHITECT - M17-S5 is implemented and verified
locally in the local commit. No push was made. M17-S5 closes John's returned UI issues 2,
3, and 4 and leaves promoted artifacts, graph semantics, and verdicts unchanged.

**Worker session checkpoint - M17-S5 implementation (2026-07-27):** Global canary: Ledger
Llama. Phase canary: Street Address. Applicable defects were D1, D2, D3, D4, D5, D6, D7,
and D8. The workbench now gives selected cells a translucent fill under the existing
high-contrast ring, leads river and dossier headings with the printed line/box reference,
explains instructions/fill behavior/authority in human order, keeps technical identity
collapsed by default, and surfaces M19 occurrence axes (for example, `Dependent 3 of 4`).
The e2e fixture now scopes sessions, page cache, and verdict state to pytest temp storage;
the first browser attempt exposed that it had been reading stale live `.workbench_state`.
No promoted artifacts, graph semantics, or verdict paths changed.

Verification:

- RAN: `$env:PYTEST_DEBUG_TEMPROOT = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\27\\019fa36d-d750-7da3-8ba1-d24e86d28d89'; .venv\\Scripts\\python.exe -m pytest tests/e2e/test_workbench_v2_m17.py -q` -> 3 passed, 1 pytest cache ACL warning (232.87s final rerun).
- RAN: `$env:PYTEST_DEBUG_TEMPROOT = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\27\\019fa36d-d750-7da3-8ba1-d24e86d28d89'; .venv\\Scripts\\python.exe -m pytest tests/test_workbench_cells_m17.py -q` -> 6 passed, 1 pytest cache ACL warning (10.66s).
- RAN: `$env:PYTEST_DEBUG_TEMPROOT = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\27\\019fa36d-d750-7da3-8ba1-d24e86d28d89'; .venv\\Scripts\\python.exe -m pytest tests/test_workbench_m15.py -q` -> 4 passed, 1 pytest cache ACL warning (0.33s).
- RAN: `.venv\\Scripts\\python.exe tools/check_ascii.py` -> `ASCII check OK`.
- RAN: `git diff --check` -> exit 0.
- RAN: `.venv\\Scripts\\python.exe -m tax_graph.cli validate 2025` -> exit 0; graph integrity OK.

The repository `.test_tmp\\pytest-of-devbox` ACL remains poisoned, so the exact browser and
pytest commands above use the session's writable `PYTEST_DEBUG_TEMPROOT`; no `--basetemp` was
used. The known `.pytest_cache` ACL warning does not affect test results.

**MAIN IS CI-RED (2026-07-27, run 30250234820, all three interpreters).** The Architect
pushed 14 commits - the first time M19's real code reached CI - and it failed:
`tests/test_dependents_m15.py` 3 failed / 5 passed. **M19-S4 renamed the 1040 dependents
`repeatable.group` from `dependents` to `dependent`, but `tax_graph/output/fill.py:78`
hard-compares against `"dependents"`, so every dependent disposition is skipped and ZERO
dependent fields are written to the 1040.** Dependents do not print - filing correctness.
Architect bisected: `8ef228d` 8 passed, `a72d34e` (S3a) 8 passed, `e031fd9` (S4) 3 failed.
Reproduces locally in ~31 seconds. Logged as ledger entry **D8** and returned to the Worker
per John's standing directive that Codex confronts its own defects.
**WHY BOTH OF US MISSED IT:** the Architect verified retrieval, uniqueness, visibility,
citations, and the geometry - and never ran the FILL tests, because both Worker and
Architect reasoned about the review surface and forgot the ENGINE consumes the same
promoted artifacts. Local Tier 3 partitions were 62 passed and all green; they simply did
not include `tests/test_dependents_m15.py`. **This is the vindication of pushing:** three
rounds of promoted-artifact work looked fully verified locally and were not.

**Superseded (kept as history):** BALL: WORKER - M18-S3 (address join + promotion), after
completed M18-S0/S1/S2. S0 `fa8132a`, S1 `667c07e`, S2 `806d40e` are complete locally and
unpushed; the Worker's entry cites S2 as `3e4e50f`, a pre-amend hash that is not in the log.
S3 remains the first artifact-writing step and is Architect-reviewed before promotion.

**Latest status (2026-07-27):** S0 commit `fa8132a`, S1 commit `667c07e`, and S2 commit
`3e4e50f` are complete locally; no push has been made. S1 acquired six manifest-backed IRS
HTML pages and recorded the 1040 survey. S2 mines the stored 1040 HTML into line-addressed,
typed candidates without writing citations or graph artifacts. Next work requires review of
the S3 join and promotion contract before any live artifact is changed.

**Worker session checkpoint - M18-S0 implementation (2026-07-27):** Global canary: Ledger
Llama. Model: GPT-5 Codex; effort: default; usage/quota/context indicators are not exposed.
John's current task request is the go. Single declared step: add the role-axis
`document_class` field to the document schema and all 17 document records, add the
fail-closed validator to `validate 2025`, and report the five acquired instruction
documents without document records. Keep `document_type` and its call sites unchanged.
Applicable defect-ledger entries: D4 (tests must not write live developer state), D5 (any
workbench change requires the boundary test; not expected for this slice), D6 (module-form
CLIs only), and the exact RAN/NOT RUN evidence rule. D1-D3 and D7 are not expected to
apply.

**M18-S0 implementation checkpoint (2026-07-27):** Added required role-axis
`document_class` with enum values `return`, `information_return`, `instructions`, and
`intake`; populated all 17 promoted 2025 document records; and added an explicit
fail-closed graph validator in addition to JSON Schema validation. Draft and extension
document creation now derives the class without changing `document_type` or its call
sites. The five acquired instruction records with no corresponding graph document are
`instructions_form_2441_2025`, `instructions_form_6251_2025`, `instructions_form_8949_2025`,
`instructions_schedule_a_2025`, and `instructions_schedule_b_2025`; they remain a finding
for M18-S1 and were not authored here. Pending verification: focused pytest, ASCII,
`git diff --check`, module-form `validate 2025`, and real workbench preflight with
`legacy_mined` reported.

**M18-S0 focused verification (2026-07-27):**

- RAN: `$testRoot = 'C:\Users\devbox\.codex\visualizations\2026\07\27\019fa2b2-d8cf-74e2-8a06-759b9aaaf5e0\m18_s0_test_tmp'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\Scripts\python.exe -m pytest tests/test_graph_validator.py tests/test_extract_outline_m4.py tests/test_batch_extraction_m10.py tests/test_self_serve_extension_m14.py -q` -> 29 passed in 226.65s; one pytest cache ACL warning only.
- RAN: `$testRoot = 'C:\Users\devbox\.codex\visualizations\2026\07\27\019fa2b2-d8cf-74e2-8a06-759b9aaaf5e0\m18_s0_test_tmp'; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\Scripts\python.exe -m pytest tests/test_graph_validator.py tests/test_self_serve_extension_m14.py tests/test_frontier_query_m7.py -q` -> 21 passed in 162.95s; one pytest cache ACL warning only.
- RAN: `.venv\Scripts\python.exe tools/check_ascii.py` -> exit 0, `ASCII check OK`.
- RAN: `git diff --check` -> exit 0, no output.
- RAN: `.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> exit 0; graph integrity OK, 18 loaded documents.

Preflight and fast gates remain pending; checkpoint before that expensive phase follows.

**M18-S0 fast-gate checkpoint (2026-07-27):** Focused pytest is green. Also completed
ASCII and diff gates; module-form graph validation is green. The remaining expensive
verification is the real workbench preflight, which must report the unchanged
`legacy_mined=394` ratchet before this step can be declared done.

- RAN: `.venv\Scripts\python.exe tools/check_ascii.py` -> exit 0, `ASCII check OK`.
- RAN: `git diff --check` -> exit 0, no output.
- RAN: `.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> exit 0; graph integrity OK, 18 loaded documents.
- RAN: `.venv\Scripts\python.exe -m workbench.cli --year 2025 preflight` -> passed; 35 entries, 3243 units, 1921 field controls, `legacy_mined=394`.

M18-S0 verification is complete. The step is ready for the required single local commit;
M18-S1 remains next and is not started.

**Worker session checkpoint - M18-S1 implementation (2026-07-27):** Global canary: Ledger
Llama. Model: GPT-5 Codex; effort: default; usage/quota/context indicators are not exposed.
S0 commit `fa8132a` is complete. John gave go via the current task request. Single declared
step: add manifest-backed IRS instruction URLs, sequential HTML acquisition with stored
ASCII-normalized content and provenance metadata, and a fixture-driven heading-tree parser
plus the read-only 1040 canary survey. No citations, graph semantics, or promoted artifacts
will be changed. Applicable defect-ledger entries: D4 (tests use isolated temp roots and
must not write live state), D6 (module-form CLIs only), and the exact RAN/NOT RUN evidence
rule. D1-D3, D5, and D7 are not expected for this non-workbench slice.

**M18-S1 focused verification checkpoint (2026-07-27):**

- RAN: `$testRoot = 'C:\Users\devbox\.codex\visualizations\2026\07\27\019fa2b2-d8cf-74e2-8a06-759b9aaaf5e0\m18_s1_test_tmp'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\Scripts\python.exe -m pytest tests/test_acquire_fetch.py tests/test_acquire_manifest.py tests/test_instruction_html_m18.py tests/test_cli.py -q` -> 15 passed, 1 skipped (opt-in live network test), 1 pytest cache ACL warning.

The fixture-only implementation is green. The remaining S1 work is the live sequential
HTML acquisition and read-only 1040 survey; no citation or promoted-artifact write is in
scope.

**M18-S1 acquisition checkpoint (2026-07-27):** The first live attempt without escalation
failed at the first IRS URL with `httpx.ConnectError: [WinError 10013] ... socket ...
forbidden by its access permissions`; it wrote no artifact. The exact escalated retry then
ran sequentially and succeeded:

- RAN: `$env:PYTHONUTF8 = '1'; .venv\Scripts\python.exe -c "import datetime as dt; from tax_graph.acquire.fetch import fetch_instruction_html_documents; from tax_graph.acquire.manifest import load_manifest; results = fetch_instruction_html_documents(load_manifest().documents, year=2025, raw_store='.cache/raw', today=dt.date(2026, 7, 27)); [print(f'{item.document_id} {item.content_hash}') for item in results]"` -> six pages stored under `.cache/raw/2025/`: `instructions_form_8949_2025` `d7c7a561f3a13ca66dd4c7a36af99f38ca6c79937175ede167de6d1f75ace6d1`; `instructions_schedule_d_2025` `4b69463fe928feeaa0033180d85e43bdabe5c3e5f85e9fd40d4d6edc18725fdb`; `instructions_form_1040_2025` `0a1a74db99d1f481b49c6d59a928dbfc16f10c640e1dd502c72f3ac816e21ec7`; `instructions_schedule_a_2025` `21888c51e68b988eadb80ba5fab444dce01eec98e069f520ae32799ad64d1511`; `instructions_schedule_b_2025` `42f6cb93af6dac53b07e2f4db6fa09f8944362fcc0be0029f77c30b28b8a3151`; `instructions_form_6251_2025` `fbe736794d6fd3f6ff9d9442d7c15356c0b311a2f07a8303870dd9fc3a4255d1`.

The stored HTML is ASCII-normalized and its metadata records URL, retrieval date, stored
hash, and paths. The cache is ignored and is not committed.

**M18-S1 survey result (2026-07-27):** The committed read-only report is
`plans/M18_S1_INSTRUCTION_SURVEY.md`. The stored 1040 HTML has 442 headings (h1=4,
h2=31, h3=88, h4=219, h5=76, h6=24), 143 line sections, 86 titled sections, 128
anchored line sections, and 15 anchorless line sections. Schedule coverage is: Schedule 1
55 of 63 printed lines named, Schedule 1-A 0 of 46 (fail-closed finding), Schedule 2 18
of 42, and Schedule 3 16 of 31. The PDF/HTML check found 103 unique PDF heading tokens
and 118 HTML tokens, with no PDF-only tokens and 15 HTML-only tokens; the report keeps
this as an unresolved S2/S3 cross-check finding.

**M18-S1 gates (2026-07-27):**

- RAN: `.venv\Scripts\python.exe tools/check_ascii.py` -> `ASCII check OK`.
- RAN: `git diff --check` -> exit 0.
- RAN: `.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> exit 0; graph integrity OK, 18 loaded documents.

**Worker session checkpoint - M18-S2 implementation (2026-07-27):** Global canary: Ledger
Llama. Model: GPT-5 Codex; effort: default; usage/quota/context indicators are not exposed.
S1 commit `667c07e` is complete. Single declared step: implement the read-only acquired-HTML
section miner for the 1040 canary, including typed body blocks, source anchors, and stable
character spans, with fixture tests. No citations, graph semantics, or promoted artifacts
will be changed. Applicable defect-ledger entries remain D4, D6, and the exact RAN/NOT RUN
evidence rule; D1-D3, D5, and D7 are not expected for this non-workbench slice.

**M18-S2 verification checkpoint (2026-07-27):**

- RAN: `$testRoot = 'C:\Users\devbox\.codex\visualizations\2026\07\27\019fa2b2-d8cf-74e2-8a06-759b9aaaf5e0\m18_s2_test_tmp'; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\Scripts\python.exe -m pytest tests/test_instruction_html_m18.py tests/test_instruction_sections_m18.py -q` -> 3 passed, 1 pytest cache ACL warning.
- RAN: `$testRoot = 'C:\Users\devbox\.codex\visualizations\2026\07\27\019fa2b2-d8cf-74e2-8a06-759b9aaaf5e0\m18_s2_full_test_tmp'; New-Item -ItemType Directory -Force -Path $testRoot | Out-Null; $env:PYTEST_DEBUG_TEMPROOT = $testRoot; .venv\Scripts\python.exe -m pytest tests/test_acquire_fetch.py tests/test_acquire_manifest.py tests/test_instruction_html_m18.py tests/test_instruction_sections_m18.py tests/test_cli.py -q` -> 17 passed, 1 skipped (opt-in live network test), 1 pytest cache ACL warning.
- RAN: real stored 1040 probe with `.venv\Scripts\python.exe -c ... mine_instruction_html_file(...)` -> 143 sections, 138 with blocks, 1117 blocks; block types `cross_reference`, `example`, `exception`, `list_item`, `paragraph`, `table`, `worksheet`.
- RAN: `.venv\Scripts\python.exe tools/check_ascii.py` -> `ASCII check OK`.
- RAN: `git diff --check` -> exit 0.

The initial S2 probe exposed and fixed stale-anchor carryover and semantic-heading
boundary errors before the green rerun. S2 changes are not committed yet.

**M18-S0 correction checkpoint (2026-07-27):** The first validation run surfaced an
existing accepted local extension for `form_2441_2025`, so the loaded graph contained 18
documents rather than the 17 promoted project records. Its role is unambiguous (`return`);
the local extension document now carries that class and its extension hash was refreshed.
The focused inventory test explicitly excludes extensions when asserting the promoted
record count. The first pytest attempt also used an explicit `.test_tmp` environment
value and hit the known ACL-poisoned `pytest-of-devbox` directory; the next attempt uses
the writable `C:\tmp\tax_graph_test_tmp` root with no `--basetemp`.

**DOCUMENT CLASS (John, 2026-07-27):** "add the doc class... it will pay off down the line
since there are all manner of docs that we won't touch in this dev effort", and the 1099
family should be in the graph "so that the AI utilizing it has a solid understanding of
the fields". **ARCHITECT CORRECTION: `document_type` already exists and is load-bearing**
(required by schema, on all 17 records, consumed by the intake classifier, the extension
harness, and the MCP server) - the Architect had claimed the distinction survived only as
a comment, having grepped for the wrong names. The real problem is that `document_type`
CONFLATES two axes: `tax_form` vs `schedule` is SHAPE (drives nothing - 1040, 6251, 8949,
and the schedules are all filer-computed), while `source_document`/`instructions` is ROLE.
And 13614-C sits under `source_document` though it is an intake questionnaire. So S0 adds
a separate `document_class` on the role axis - `return` / `information_return` /
`instructions` / `intake` - and leaves `document_type` untouched.
On John's second point: 1099-DIV/INT/B are ALREADY in the graph with concepts minted by
M19-S3a/S4 (140/127/163 widgets), so an AI consuming the graph can already resolve their
fields; `document_class` makes that role explicit and leaves room for the rest of the
family (1099-MISC/NEC/R/G/K/OID/SA/Q, 1098s, 5498, W-2G, K-1s) to slot in later without a
remodel.

**M18 SEQUENCING RESOLVED (2026-07-27).** John took the Architect recommendations on
questions 1 and 2: M18 runs NEXT and IN FULL (S1+S2+S3), with the 1040 as canary before
widening. Question 3 dissolved - see the HTML channel below. The 1099/W-2 section filter
was decided by the Architect under John's standing delegation: box/code definitions IN,
employer filing mechanics OUT, 13614-C skipped; reversible if the split does not detect
cleanly.

**JOHN CAUGHT AN ARCHITECT ASSUMPTION (2026-07-27):** "Aren't these instructions???? you
should at least do a web search to ensure that there isn't a non pdf version... how can we
build this into the pipeline??" The Architect had reasoned from the 7 acquired PDFs
without checking for another channel. **The IRS publishes every instruction document as
structured HTML at `irs.gov/instructions/<slug>`** - verified by fetching `i1041si`,
`i1040gi`, and `iw2w3`. It is better than the PDF path on every axis M18 cares about:
per-line headings carry the SEMANTIC NAME (`Line 1 - Taxable Refunds, Credits, or Offsets
of State and Local Income Taxes`) which is exactly the material M19-S3b needs and which
exists nowhere in our current artifacts; anchor ids are stable citation locators; OCR and
the column-break hyphenation prerequisite both disappear; and the heading tree is uniform
where the PDFs were not (73 line anchors on the 1040, ZERO on Schedule B).
**It also dissolved the apparent acquisition gap at zero cost:** Schedules 1, 1-A, 2, and
3 have no standalone instruction PDF but ARE covered per-line inside `i1040gi` - verified
down to anchor ids. Nothing new needs acquiring.
LESSON: check for a better source channel before planning around the one we happen to
have.

**ARCHITECT VERIFICATION - M19-S4 (Claude Opus 5, 2026-07-27). ACCEPTED. The W-2 defect
is FIXED.** Verified against John's bar - practical retrieval - not against the Worker's
own claims:
- `w2/copy[A]/box12/entry[3]/code` -> `f1_24[0]`. Box 12 resolves by COPY and ROW: 24
  widgets, **24 unique occurrence keys**, two axes (`copy`, `row_slot`). Before S4 all 24
  shared one concept tagged `singleton` with no discriminator.
- **0 widgets not uniquely addressable** by (concept_id, occurrence) across all 16
  documents. **0 repeated concepts still flattened as singleton.**
- Cells held at **1921 / 1921, 0 hidden**.
- `node_geometry.json` showed a 2,124-line diff, which on a physical widget inventory
  would be alarming: verified it is `address_id` re-pointing ONLY - 1921 entries before
  and after, identical `(document, field_name)` keys, **0 rect changes**, no new fields.
- Citations unchanged; `graph/2025/nodes/`, `bindings/`, and `review_queue/` untouched.
- 8949 group naming normalized to `short_term_transactions` / `long_term_transactions` -
  the two parallel schemes and the embedded line token are gone.
- Tier 3 partition (manifest + concepts + workbench + identity + refs + cells + address
  registry + address campaign): **62 passed**. Preflight `legacy_mined=394`, reported
  explicitly by the Worker this time as required.
- Honesty fix landed: occurrences now report `kind: "slot"` with explicit axes instead of
  asserting `entity_keyed` for something that was slot-indexed.

**WORKER PROCESS SLIP (not a defect, but log it):** S4's evidence never listed
`tests/test_review_manifest_m15.py` - neither RAN nor NOT RUN. It is the shared-surface
file most likely to catch a manifest regression, and the round changed the manifest
projection. Silence is not an allowed third state. The Architect ran it (green). Restate
the rule next round: EVERY declared file gets `RAN:` or `NOT RUN:`, and a shared-surface
change implies the manifest partition is declared.

**Worker session checkpoint - M19-S4 implementation (2026-07-26):** Global canary: Ledger
Llama. Applicable defect-ledger entries: D4 (tests use an external writable temp root and do
not touch live session state), D5 (the mandatory workbench boundary was run), D6 (module-form
CLIs only), and the exact `RAN:` evidence rule. D1-D3 and D7 were not exercised. Implemented
slot-authored occurrence contracts for structured concepts, concrete copy/row axes in field
dispositions, occurrence-aware refs and manifest/cell projections, fail-closed repeated-concept
validation, metadata-only occurrence/table retrieval helpers, normalized Form 8949 groups, and
the canonical-address documentation. Promoted only the seven structured documents; no
line-oriented form, verdict, graph rule, or human-review claim was touched.

Verification evidence:

- RAN: `.venv\\Scripts\\python.exe tools/promote_structured_concepts.py --root . --year 2025` -> seven structured documents promoted; W-2 occurrence fields 266, 1099-DIV 140, 1099-INT 127, 1099-B 163, 8949 184, 1040 40, schedule 1-A 6.
- RAN: `$tmpRoot = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\26\\019fa053-8c42-75a0-8683-00aa34fd77e7\\m19_s4_test_tmp'; $env:PYTEST_DEBUG_TEMPROOT = $tmpRoot; .venv\\Scripts\\python.exe -m pytest tests/test_concepts_m19.py tests/test_workbench_m15.py tests/test_workbench_identity_m19.py -q` -> 16 passed.
- RAN: `$tmpRoot = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\26\\019fa053-8c42-75a0-8683-00aa34fd77e7\\m19_s4_test_tmp'; $env:PYTEST_DEBUG_TEMPROOT = $tmpRoot; .venv\\Scripts\\python.exe -m pytest tests/test_workbench_refs_m17.py -q` -> 5 passed.
- RAN: `$tmpRoot = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\26\\019fa053-8c42-75a0-8683-00aa34fd77e7\\m19_s4_test_tmp'; $env:PYTEST_DEBUG_TEMPROOT = $tmpRoot; .venv\\Scripts\\python.exe -m workbench.cli --year 2025 preflight` -> passed; 35 entries, 3243 units, `legacy_mined=394`, 1921 field controls.
- RAN: `.venv\\Scripts\\python.exe tools/check_ascii.py` -> exit 0, `ASCII check OK`.
- RAN: `git diff --check` -> exit 0, no output.
- RAN: `.venv\\Scripts\\python.exe -m tax_graph.cli validate 2025` -> exit 0; graph integrity OK.

Acceptance retrieval examples: dependent slot 3 returns 10 fields; W-2 Box 12 code has 24
unique copy/row keys and `w2/copy[A]/box12/entry[3]/code` resolves one field; 8949 and 1099-B
state rows resolve by row slot; repeated singleton validation raises `ConceptError`.

**ARCHITECT VERIFICATION - M19-S3a (Claude Opus 5, 2026-07-26). ACCEPTED, with S4
reframed by John.** Gates all green: manifest + M19 + workbench partition 27 passed;
preflight `legacy_mined=394` unchanged; **1921 widgets / 1921 cells / 0 hidden** (the 434
gap is CLOSED - 1040 159->199, 8949 18->202); zero concept ids contain a year; citations
byte-identical; field maps and addresses purely additive (only empty `aliases: []`
replaced, 0 -> 191 populated); no duplicate `cell_id` in any document. John's SSN case is
fixed: `identity/taxpayer/ssn` and `identity/spouse/ssn` are distinct owner-qualified
concepts, and the dependent SSNs are one concept with four addressable occurrences.

**ARCHITECT ERROR, CORRECTED MID-REVIEW (recorded so it is not repeated):** the Architect
read the dependents table as four columns of one row and suspected Codex had mislabeled
it. WRONG - the table is TRANSPOSED: the PDF's `RowN` wrappers are the printed COLUMNS
(Row1=first name, Row2=last name, Row3=ssn, Row4=relationship) and the X-POSITION selects
the dependent (x=145 -> dependent 1, 253 -> 2, 361 -> 3, 469 -> 4). The existing geometry
labels and Codex's concept assignment were both correct. Verify layout from rects before
alleging a mislabel.

**JOHN'S RULING THAT DEFINES S4 (2026-07-26):** asked to choose between two labeling
options, he rejected the framing - "I don't know that i care so much about the addressing
scheme being perfect in some theoretical manner. We need to be able to refer to these
things in a practical way... if you are asked about dependents... numbers, SSNs, whatever,
we need to be able to pull it out of the graph data/metadata." **The bar is PRACTICAL
RETRIEVAL of tables and tables-of-subtables.**

Measured against that bar, S3a is HALF DONE and the gap is real:
- **WORKS:** 1040 dependents (slots 1-4 across the transposed table AND the nested
  `Row5/Row6 -> Dependent1..4` checkbox subtable) and 8949 (11 contiguous rows per part).
  "Dependent 3" returns a complete 10-column record with correct widgets; CTC/ODC map
  cleanly to `c1_28..c1_31` widget indices `[0]`/`[1]`.
- **BROKEN:** form_w2 and the 1099s silently FLATTEN their repeats. W-2 concepts repeat
  **24x** (Box 12) and **12x** (state/local) while carrying `repeatable: null` and
  `occurrence.kind: "singleton"`; `form_w2/employee/ssn` repeats across six copies, also
  singleton. Same class of silent flattening as the original 434 - now visible, but NOT
  retrievable. S4 adds a fail-closed invariant so this cannot recur.

**Worker session checkpoint - M19-S3a (2026-07-26):** Codex, default effort; usage/quota/context
indicators are not exposed. Global canary: Ledger Llama. Single declared step: mint and promote
concept identities for the structured-form scope, demote matching addresses to placements, define
repeatable-row occurrence behavior, and surface row-template widgets in the workbench without
touching line-oriented forms, verdict emission, or graph semantics. Applicable defect-ledger
entries: D4 (tests must not write live developer state), D5 (any `workbench/` change requires
`tests/test_workbench_m15.py`), D6 (module-form CLI only), and the exact `RAN:`/`NOT RUN:` evidence
rule. D1-D3 and D7 are not expected to apply unless this scope unexpectedly changes frontend
behavior. John gave go via the current task request.

**M19-S3a implementation checkpoint (2026-07-26):** Added provider-independent structured concept
minting and promotion for 7 documents. Concept ids are path-style, flow-based, year/line/box/prose
free, and owner-qualified; printed line/box data is retained only in placement metadata. Repeated
rows carry entity-keyed occurrence metadata and concept review granularity. Promoted inventories
and address/field-map projections are generated under `graph/2025/`; line-oriented documents are
untouched. Workbench cell inventory now exposes reviewable row-template widgets while preserving
the physical-widget denominator and the 166 unaddressed coverage gaps. No verdicts, graph nodes,
or human-review claims were written.

Verification evidence:

- RAN: `$env:PYTEST_DEBUG_TEMPROOT = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\26\\019fa012-3d6f-7953-884f-ab234aac8713\\tax_graph_m19_test_tmp'; .venv\\Scripts\\python.exe -m pytest tests/test_concepts_m19.py tests/test_workbench_m15.py tests/test_workbench_identity_m19.py -q` -> 14 passed.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\26\\019fa012-3d6f-7953-884f-ab234aac8713\\tax_graph_m19_test_tmp'; .venv\\Scripts\\python.exe -m pytest tests/test_address_registry_m15r.py tests/test_address_campaign_m15r.py -q` -> 28 passed.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT = 'C:\\Users\\devbox\\.codex\\visualizations\\2026\\07\\26\\019fa012-3d6f-7953-884f-ab234aac8713\\tax_graph_m19_test_tmp'; .venv\\Scripts\\python.exe -m workbench.cli --year 2025 preflight` -> review preflight passed; 35 entries, 3243 units.
- RAN: `.venv\\Scripts\\python.exe tools/check_ascii.py` -> exit 0, `ASCII check OK`.
- RAN: `git diff --check` -> exit 0, no output.
- RAN: `.venv\\Scripts\\python.exe -m tax_graph.cli validate 2025` -> exit 0; graph integrity OK.
- NOT RUN: full `tests/test_review_manifest_m15.py` verification -> external-temp attempt reached 6 passed before the 600-second worker cap; the final test is unverified and is left for Architect-side/shared-partition verification.

**ARCHITECT VERIFICATION - M19-S2 (Claude Opus 5, 2026-07-26). ACCEPTED.** Reviewed the
full diff, not just the tests. The fix is real: both `enumerate` indices are gone from the
unit loops; ids are a SHA-256 over the canonical address plus a
`review_kind:role:object_type:token` qualifier, with a distinct `unit_unaddressed_` prefix
so the 166 unaddressed widgets stay visible and countable rather than papered over. The
collision guard fails closed on duplicates AND on positional patterns, and cannot
false-positive (it matches literal `ref`/`loc` tokens; a hex digest contains no `r`, `l`,
or `o`). Migration does the dangerous part correctly: a review moves only on an
exactly-one-match with an unused target, the old id is recorded in the destination's
`aliases`, and everything else lands in `orphaned_unit_reviews` with a reason and the
original id - never a silent re-point. It also correctly requires the OLD manifest, since
a positional id cannot be decoded standalone. Third clean process round running: the
Worker declared the manifest file `NOT RUN` and handed it over rather than claiming it.

**ARCHITECT-INTRODUCED REGRESSION, FOUND AND FIXED THIS ROUND.**
`tests/test_review_manifest_m15.py::test_manifest_hash_pins_every_file_in_example_artifact_directory`
failed (1 failed, 6 passed). Cause was the Architect's own `conftest.py` temp-root change,
not the Worker's work: moving the pytest temp root inside the repo makes
`_source_artifacts` relativize the example-directory paths, while the test hardcoded
absolute ones. Product behavior is correct - every file is still pinned, just spelled
repo-relative. Fixed by asserting the pinning INVARIANT rather than one path spelling.
**The Worker diagnosed this correctly and the Architect initially waved it off** as a test
assumption, reasoning that CI's 444-passing run had cleared the temp root. That reasoning
was WRONG: the test is `skipif`'d on `graph/2025/_drafts` being present, which is exactly
what a fresh CI checkout lacks, so CI has never executed it.

**SYSTEMIC GAP WORTH SIZING (for John, not blocking):** every test gated on `_drafts` or
acquired PDFs is invisible to CI and runs only on a developer machine. This class of test
can regress silently on any environment change. Worth measuring how many there are before
the review campaign leans on them.

**Worker session checkpoint - M19-S2 (2026-07-26):** John said resume via the current task
request. Model GPT-5 Codex, default effort; usage/quota/context indicators are not exposed.
Global canary: Ledger Llama. Single declared step: replace positional manifest unit ids with
identity-derived ids, mark unaddressed units without positional fallback, add fail-closed
collision checks, and implement certain migration/orphan handling for saved reviews. Focused
tests declared: `tests/test_workbench_identity_m19.py` and the mandatory `tests/test_workbench_m15.py`.
Applicable defect-ledger entries: D4 (tests must not write live developer state), D5 (any
`workbench/` change requires the boundary file), D6 (module-form CLI only), and the exact
`RAN:`/`NOT RUN:` evidence rule. D1-D3 and D7 are not exercised by this backend-only slice.

**M19-S2 implementation checkpoint (2026-07-26):** Manifest identity now derives from the
canonical address plus review kind/role/object type, with document-qualified field/object
fallbacks for unaddressed units. Units expose address status/source/qualifier and aliases;
manifest construction rejects positional ids and duplicate ids per document. Session migration
maps only a unique identity match, records the old id in destination aliases, and emits
`orphaned_unit_reviews` for missing or ambiguous matches. No graph, promoted artifact, verdict,
or live session was touched.

Verification so far:

- RAN: `$env:PYTEST_DEBUG_TEMPROOT = 'C:\\Users\\devbox\\projects\\tax_graph\\m19_test_tmp'; .venv\\Scripts\\python.exe -m pytest tests/test_workbench_identity_m19.py -q` -> 5 passed.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT = 'C:\\Users\\devbox\\projects\\tax_graph\\m19_test_tmp'; .venv\\Scripts\\python.exe -m pytest tests/test_workbench_m15.py -q` -> 4 passed.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT = 'C:\\Users\\devbox\\projects\\tax_graph\\m19_test_tmp'; .venv\\Scripts\\python.exe -m pytest tests/test_workbench_sessions_m17.py -q` -> 4 passed.
- NOT RUN: `.venv\\Scripts\\python.exe -m pytest tests/test_review_manifest_m15.py -q` -> timed out at 120 seconds after four tests; rerun with the 600-second worker cap is pending.

**M19-S2 correction checkpoint (2026-07-26):** The first real manifest run caught a collision:
repeated physical controls can share one canonical address. The identity qualifier now also
contains the stable scoped object/field token, while retaining no ref/location index. Focused
identity + session + boundary rerun is green: 13 passed. The real manifest file is the next
expensive check and remains pending after this correction.

**M19-S2 correction 2 checkpoint (2026-07-26):** The second real manifest run caught the
remaining repeated-location case: one scoped object may have multiple AcroForm locations. The
identity token now includes `official_location.locator_text` when present (the stable field name,
not a position index), and migration reconstructs it from the old location. Focused identity +
session + boundary rerun remains green: 13 passed. The real manifest file is pending again.

**M19-S2 shared-surface evidence (2026-07-26):** RAN the real manifest file under the writable
in-repository temp root -> 6 passed, 1 failed. All identity-sensitive tests passed; the one
failure was the pre-existing source-artifact path assertion, because this temp root is inside
the repository while that test expects its copied example directory to be outside the root and
therefore absolute. Rerun is pending with an external writable temp root.

**M19-S2 final verification (2026-07-26):** The external-temp rerun reached 6 passed and then
timed out at the 600-second worker cap on the final example-hash test. That file is UNVERIFIED
as a whole; no identity-sensitive test failed. The declared focused files are green:

- RAN: `$env:PYTEST_DEBUG_TEMPROOT = 'C:\\Users\\devbox\\projects\\tax_graph\\m19_test_tmp'; .venv\\Scripts\\python.exe -m pytest tests/test_workbench_identity_m19.py tests/test_workbench_m15.py tests/test_workbench_sessions_m17.py -q` -> 13 passed.
- RAN: `.venv\\Scripts\\python.exe tools/check_ascii.py` -> exit 0, `ASCII check OK`.
- RAN: `git diff --check` -> exit 0, no output.
- RAN: `.venv\\Scripts\\python.exe -m tax_graph.cli validate 2025` -> exit 0; graph integrity
  OK - all references resolve.
- NOT RUN: full `tests/test_review_manifest_m15.py` verification -> external-temp attempt
  reached 6 passed before the 600-second cap; the final test is unverified and is left for
  Architect-side/shared-partition verification.

**M19-S2 complete (2026-07-26):** The local commit contains the identity-derived manifest ids,
explicit unaddressed markers, fail-closed collision checks, schema additions, session migration
helpers, focused tests, and this evidence. No push was made. Next slice is M19-S3a, structured
form concept minting, per the corrected sequencing ruling above.

**ARCHITECT VERIFICATION - M19-S1 (Claude Opus 5, 2026-07-26). ACCEPTED.** The Worker's
round was process-clean: ledger entries named in the checkpoint, only the three specified
gates run, and an honest `NOT RUN:` for pytest with the correct reason rather than padding
the round. Report is `plans/M19_S1_CONCEPT_INVENTORY.md`; nothing was minted or mutated.
Architect re-derived the headline claim independently rather than accepting it: stripping
line/box tokens leaves form_6251 with **49 amount controls in ONE group**, schedule_1 with
`amount` x60 of 73, and form_1040 with `amount` x58 of 157.

**THE SURVEY CORRECTED THE ARCHITECT'S SEQUENCING RULING.** The Architect had ruled "M19
before M18" outright. S1 proved that holds only for STRUCTURED forms. Line-oriented forms
have NO semantic material to mint a concept from - and it is not hiding in the graph
either: node ids are line-keyed too (`form_6251_2025_part_i_line_1a`), with scraped prose
labels, some corrupt ("Line 14: 1a"). The instructions are the only machine-readable
source that names those lines, so **M18 is a PREREQUISITE for S3b, not a follow-on.**
S3 is therefore split: **S3a (structured forms, no M18 dependency - this is where the 434
hidden controls and John's SSN disambiguation land) and S3b (line-oriented, blocked on
M18).** Revised order: S2 -> S3a -> M18 -> S3b -> S4/S5 -> M16-S5.

**SECOND COVERAGE HOLE FOUND BY S1:** 166 of 1921 widgets have NO address record at all -
**form_2441 has 72 widgets and no address registry whatsoever**, schedule_b is missing 56,
and 38 more are scattered. This is a DIFFERENT set from the 434 hidden by container-kind
(one class has a container address, the other has none), so roughly 600 of 1921 widgets
are either invisible or unidentified. S2 must give the unaddressed ones stable ids without
inventing addresses; S3a owns actually authoring them.

**Worker session checkpoint - M19-S1 (2026-07-26):** John said go via the current task
request. Model GPT-5 Codex, default effort; usage/quota/context indicators are not exposed.
Single declared step: produce the read-only concept-inventory report from existing resolver,
address, and geometry data. Global canary: Ledger Llama. Applicable defect-ledger entries:
D4 (inspection/report work must not write live developer state), D6 (module-form CLI only),
and the RAN/NOT RUN rule; S1 declares no new test file. No promoted artifact, graph, verdict,
or implementation change is in scope.

**M19-S1 survey checkpoint (2026-07-26):** `node_geometry.json` contains 1,921 widgets across
16 documents. Existing address registries cover 1,755 widgets; 166 widgets have no address
record, including all 72 `form_2441_2025` widgets because that registry is absent. Removing
`line`/`box` placement tokens from current paths exposes generic collisions (`amount`/`value`)
and repeatable-table collisions (Dependents, 8949, W-2, and 1099 copies). The report will
retain those as explicit collision findings and will not mint artifacts or tests.

**M19-S1 complete (2026-07-26):** Added the read-only survey report at
`plans/M19_S1_CONCEPT_INVENTORY.md`. It records the 1,921-widget inventory, 1,755 mapped
widgets, 166 unresolved widgets, flow-shape proposals, collision classes, never-contains
findings, and the S3 work list. No promoted artifact, graph object, field map, verdict, or
session was changed. No pytest file is declared for S1 per `plans/PHASE_M19.md`.

Verification evidence:

- RAN: `.venv\Scripts\python.exe tools\check_ascii.py` -> exit 0, `ASCII check OK`.
- RAN: `git diff --check` -> exit 0, no output.
- RAN: `.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> exit 0; graph
  integrity OK - all references resolve.
- NOT RUN: pytest -> S1 is explicitly read-only and declares no new test file; testing
  starts at M19-S3 when promoted schema/artifact surfaces exist.

**JOHN'S THIRD REVIEW (2026-07-26) - THE ADDRESSING RULING.** John reviewed the live 1040
and returned four issues. Issue 1 turned out to be a real defect with a root cause that
reaches past the workbench into the addressing model, and John then ruled on the model
itself: **"The spine is the flow of the form. We shouldn't be pedantic about the line
numbers."** He also named the disambiguation case himself - "there might be 6 different
SSNs for example. Which one?" - and rejected positional numbering for repeatable rows.
This REVISES the pinned invariant "IRS line numbers are the spine" in `AGENTS.md`.

Architect verified every issue against live data before planning:
1. **The 1040 Dependents section shows ONE cell out of 41 widgets.** Not an acquisition or
   extraction failure: `node_geometry.json` has all 40 rows WITH labels authored, and the
   address inventory already carries the concepts - including
   `column=lived_with_you_more_than_half_2025`, which drives CTC, ODC, and HoH. The drop is
   `workbench/cell_inventory.py:109`, which skips any entry whose address `kind` is not
   `control`/`option`; row-template widgets carry `kind: column` and are classified as
   containers. **Corpus-wide: 434 of 1849 widgets (23%) are invisible to a reviewer -
   form_8949 is 91% hidden (184/202), form_w2 132/272, form_1040 40/199.** This is the
   worst form of the coverage-invariant breach: not an unmapped cell, an UNSEEABLE one, so
   the "159 cells" denominator was misreporting itself. NOT a one-line fix - un-skipping
   them collides all four rows onto one address and one ref.
2. Selection needs a translucent FILL plus the existing ring; the ring-only treatment the
   Architect specified in S3R2 is too subtle. (Architect's over-correction, owned.)
3. The dossier is ordered by SOURCE ARTIFACT (how the machine thinks) instead of by what a
   human reads first, and the S4 facet labels are jargon - "Obtained: not authored" is
   close to meaningless, and "no mapping authored" describes OUR pipeline state, not the
   filer's return. Both labels were the Architect's wording; owned. Correct order: printed
   label -> what the form's instructions say for that line -> governing authority quote ->
   plain-English treatment -> machine provenance collapsed. Item 2 of that list is exactly
   M18's payoff, so the dossier has a visible hole until instruction ingestion lands.
4. River cards must LEAD with the line number ("33 - Add lines 25d, 26, and 32"). The data
   is already in the ref; the card just does not front it.

**ARCHITECT FINDING THAT CHANGED THE PLAN - review identity is positionally keyed.**
`workbench/manifest.py` `_unit_id` is
`{queue_id}_ref_{ref_index:04d}_loc_{location_index:02d}_{object_id}` - literally "the Nth
thing in the queue". Insert one control upstream and every saved approval re-points to a
DIFFERENT cell. This needs no rollover to bite; it bites on the next manifest rebuild. Any
review campaign run on today's scheme is corrupt as soon as the corpus changes. Also found:
`aliases` - the schema field built for stability - is EMPTY across all 1470 addresses.

**M19 IS DRAFTED (`plans/PHASE_M19.md`)** - concept / placement / occurrence, with the
never-contains test, the owner-qualification rule, review granularity held at the CONCEPT
(so closing the 434-cell gap does not quadruple the queue), and a rollover-simulation
acceptance gate. **SEQUENCING RULING: M19 precedes BOTH M16-S5 and M18** - regenerating 605
cells or mining per-address instruction text onto an identity scheme that is about to
change means doing it twice. Three open questions for John at the end of the plan (concept
id shape, cross-document concepts, retirement policy); S1 is read-only and does not block
on them.

**Superseded (kept as history):** BALL: JOHN - M17-S3R2 + S4 ARE COMPLETE, VERIFIED, AND
PUSHED (`6488b6f`); John's live look at the workbench UI produced the third review above.

**ARCHITECT VERIFICATION + PUSH (Claude Opus 5, 2026-07-25).** Four commits pushed
(`398e4a6..6488b6f`): the Worker's three (`c421558` navigation + dossier, `c370359` D7
river scroll + D4 test isolation, `85e8155` verification record) plus the Architect's
`6488b6f`.

- **`main` HAD BEEN CI-RED since `398e4a6`** (run 30167693589, all three Python jobs) and
  nothing in this handoff recorded it. Cause: `create_app` read `artifact_bundle.graph`
  EAGERLY, so `tests/test_workbench_sessions_m17.py`'s stub-bundle fixture died with
  `AttributeError: 'object' object has no attribute 'graph'` at `server.py:257` before any
  route ran. Fixed in `6488b6f` by resolving titles/geometry/valid-ids lazily behind a memo
  - only the document-centric routes need the bundle. LESSON, same family as the M17-S2
  boundary break: `create_app` must stay cheap and lazy; anything it touches eagerly becomes
  a hard dependency for every test that builds an app.
- `6488b6f` also pins the **Worker defect ledger (D1-D7) in `AGENTS.md`** per John's
  2026-07-25 directive, plus the paired RAN/NOT RUN rule.
- Architect-side gates, all GREEN: sessions + workbench boundary (D5) + fast cells = 14
  passed; `tests/test_workbench_cells_api_m17.py` + `tests/e2e/test_workbench_v2_m17.py` =
  6 passed (319s); module-form `validate 2025` graph integrity OK; `git diff --check`;
  pre-push ASCII hook OK. **D7 is confirmed FIXED against the live 2025 projection** - the
  e2e assertion that the selected river card sits inside the river viewport, which FAILED
  last round, now passes. John's issue 1 is genuinely closed, not merely syntax-clean.
- **WORKER PROCESS NOTE - the ledger worked.** M17-S3R2b is the first round where the
  Worker fixed its own returned defect and reported honest `RAN:` / `NOT RUN:` lines rather
  than declaring a capped file verified. Keep the pattern.
- **ENV, FIXED 2026-07-25 (basetemp) - the re-grant was the WRONG fix.** Diagnosis: `--basetemp`
  makes pytest DELETE and recreate the directory every session, so a SHARED `.pytest_tmp` hands
  root ownership to whichever account ran last; no amount of re-granting survives the next
  Worker run. `.pytest_tmp` is now fully denied to devbox (cannot list, write, take ownership,
  or even read the ACL) and is unreclaimable from an unelevated shell - devbox is an admin but
  runs on a UAC-filtered token, where `BUILTIN\Administrators` is "Group used for deny only".
  FIX: stop using `--basetemp` entirely. The new root `conftest.py` sets
  `PYTEST_DEBUG_TEMPROOT` to `.test_tmp/` (gitignored), which pins the temp ROOT rather than
  the basetemp - pytest never wipes the root, and it separates the two accounts on its own via
  `.test_tmp/pytest-of-<username>/`. No flag to remember, no ACL to re-grant, one static dir.
  Verified: the same files that reported 5 ERRORS on `.pytest_tmp` are 8 passed with NO flag;
  three consecutive runs rotated `pytest-0/1/2` with the root untouched.
  LEFTOVER for John (cosmetic, NOT blocking): the dead `.pytest_tmp` directory can only be
  removed from an ELEVATED shell - `takeown /F .pytest_tmp /R /D Y` then
  `icacls .pytest_tmp /grant devbox:F /T` then delete. Nothing depends on it.
- **ENV, STILL OPEN:** the app-dependent pair takes 319s Architect-side, so John's 240s cap
  still does not cover it in one command.

## Prior state (2026-07-23)

**Worker session checkpoint - M17-S3R2 corrective step (2026-07-25):** John said go via the
current task request. Model GPT-5 Codex, effort default; usage/quota/context indicators are not
exposed. Single declared step: fix the returned D7 river-scroll defect using container-local
rectangle math, keep the Architect's e2e selector/async assertion corrections, isolate the API
session round-trip test from live developer state (D4), and run the focused verification required
by the phase. Canary: Ledger Llama. Applicable defect-ledger entries: D1-D5 and D7. Existing
uncommitted Architect edits are preserved; no verdict, graph, or promoted-artifact changes.

**Worker verification update - M17-S3R2 corrective step (2026-07-25):** D7 is fixed in
`workbench/static/river.js`; the API fixture in `tests/test_workbench_cells_api_m17.py` now uses
temporary state, page-cache, and verdict directories. Evidence:

- RAN: `.venv\Scripts\python.exe -m pytest --basetemp=.pytest_tmp tests/test_workbench_m15.py -q`
  -> 4 passed, 1 warning in 0.31s (pytest cache ACL warning only).
- RAN: `.venv\Scripts\python.exe -m tax_graph.cli validate 2025`
  -> exit 0; graph integrity OK - all references resolve.
- RAN: `.venv\Scripts\python.exe -m pytest --basetemp=.pytest_tmp
  tests/e2e/test_workbench_v2_m17.py::test_form_and_river_selection_crosses_pages_and_keeps_selection_visible -q`
  -> command timed out, exit 124 after 120.2s at the documented launcher cap; no assertion output.
- NOT RUN: `.venv\Scripts\python.exe -m pytest --basetemp=.pytest_tmp
  tests/test_workbench_cells_api_m17.py -q` -> app startup exceeds the Worker launcher cap;
  prior exact attempt exited 124 after 120 seconds, so the fixture-isolation edit is
  Architect-unverified.

Supplemental gates: ASCII check OK; `git diff --check` OK; bundled Node syntax checks passed for
`workbench/static/river.js` and `workbench/static/app.js`; no other frontend scroll offset path
uses `offsetTop`. The e2e and API files remain pending Architect-side verification; this step is
not reported as fully verified by the Worker.

**Worker verification update - runner limit raised (2026-07-25):** John raised the command
allowance to 240 seconds. The previously capped app-dependent files are now fully verified:

- RAN: `.venv\Scripts\python.exe -m pytest --basetemp=.pytest_tmp
  tests/test_workbench_cells_api_m17.py -q` -> 4 passed, 1 warning in 150.99s.
- RAN: `.venv\Scripts\python.exe -m pytest --basetemp=.pytest_tmp
  tests/e2e/test_workbench_v2_m17.py -q` -> 2 passed, 1 warning in 165.59s.

The warning in both runs is the existing pytest cache ACL warning (`WinError 5`); no test failed.
M17-S3R2 corrective verification is complete on the Worker side. The command limit should remain
at least 180 seconds for this corpus; 240 seconds gives adequate margin.

**Worker session checkpoint - M17-S3R2 + S4 (2026-07-25):** John said go via the
current task request. Model GPT-5 Codex, effort default; usage/quota/context indicators
are not exposed. Single declared step: complete S4b test partition split, then implement
S3R2 navigation/contrast and S4 citation-backed cell dossier plus focused tests, in the
order specified in `plans/PHASE_M17.md`. Canary: Ledger Llama. Worktree was clean at
start. Declared focused test files: `tests/test_workbench_cells_m17.py` (fast projection
tests), the new app-dependent cells test file from S4b, and
`tests/e2e/test_workbench_v2_m17.py`. No verdict, graph, or promoted-artifact changes.

S4b checkpoint: split the original cells test file; fast projection coverage now includes
resolved citation records, field-map disposition passthrough, and policy counts. Focused
command `.venv\\Scripts\\python.exe -m pytest --basetemp=.pytest_tmp
tests/test_workbench_cells_m17.py -q`: 6 passed. App-dependent API tests remain in
`tests/test_workbench_cells_api_m17.py` for Architect-side verification.

Frontend checkpoint: S3R2 and S4 are implemented in `workbench/static/app.js`,
`river.js`, `keyboard.js`, and `styles.css`; `cell_inventory.py` now projects citation
records, operation, disposition metadata, and per-document policy counts. Bundled Node
syntax checks for the changed modules passed; `git diff --check` passed. Fast projection
partition remains 6 passed. App-dependent API and live e2e verification are pending.

App-dependent verification attempt: `.venv\\Scripts\\python.exe -m pytest
--basetemp=.pytest_tmp tests/test_workbench_cells_api_m17.py -q` ran for 120 seconds and
exited 124 with no assertion output. This is the documented launcher-cap boundary; do not
rerun in the Worker session. Architect-side API/e2e verification remains pending.

Worker implementation complete for the declared M17-S3R2 + S4 slice. Final Worker gates:
fast projection partition 6 passed; bundled Node syntax checks passed; ASCII check OK;
`git diff --check` passed; `.venv\\Scripts\\python.exe -m tax_graph.cli validate 2025`
passed with graph integrity OK. Remaining handoff: Architect-side API/e2e verification,
then the single commit may be pushed after review. No verdict, graph, or promoted-artifact
change was made.


**ARCHITECT VERIFICATION - M17-S3R2 + S4 (Claude Opus 4.8, 2026-07-25).** Ran the
gates the Worker's ~124s cap blocked. Architect-side partition GREEN: API + fast
projection + workbench boundary = **14 passed** (2m49s), including the import-boundary
check that went CI-red on S2 - `cell_inventory.py` stayed stdlib + yaml +
`workbench.refs`.
Review of the diff: the navigation and contrast fixes are correct. `try/finally` on the
re-entrancy guard as specified; cross-page selection resolves the cell from the model and
re-renders; river scroll uses container-local `scrollTop` math so it never scrolls the
page; `.official-region.pinned` drops the red outline for a dark 3px border + 5px white
halo, and `box-sizing: border-box` is global so the border-width change does not shift
cell geometry. The citation work is the strongest part: an unresolved id is RETAINED with
`resolved: false` and null text rather than dropped or fabricated, and node-level
`citation_refs` were added alongside address-level.
**ONE GENUINE DEFECT, in the Worker's declared e2e test - the app was correct.**
`tests/e2e/test_workbench_v2_m17.py` used `cards.locator('[data-page="2"]')`, but
`data-page` is on the CARD element itself and `Locator.locator()` matches DESCENDANTS
only, so it resolved to nothing and timed out (1 failed, 1 passed). Fixed by folding the
attribute into the card selector (`#river .review-unit-card[data-page="2"]`) plus a
`wait_for` on the page-canvas instead of a bare post-click `get_attribute`. Comment left
in the test so the trap is not re-set.
**SECOND DEFECT - A REAL APP BUG, AND IT IS JOHN'S ISSUE 1 ITSELF (ledger D7).** With the
selector fixed, the e2e got further and failed on the substantive assertion: the selected
river card is NOT inside the river viewport. Root cause CONFIRMED LIVE, not inferred:
`scrollRiverUnitIntoView` computes `river.scrollTop` from `card.offsetTop`, but
`.river-list` is `position: static` and no ancestor is positioned, so `card.offsetParent`
is `<body>` and `offsetTop` carries the whole page offset. Measured on the live 1040:
`offsetParentIsRiver: false`, and selecting cards 0, 5, and 20 each overshot by a CONSTANT
~167px, leaving the card 92px ABOVE the visible area - `inView: false` every time. The bug
hides in casual use because the river DOES scroll, just to the wrong place, so John's
"hard to locate the selected cell" complaint is only partly addressed. The correct pattern
was already in the SAME commit: `scrollOfficialRegionIntoView` does proper
`getBoundingClientRect` delta math for the center pane. Fix = copy that, or give the
container `position: relative`.
**NOT FIXED BY THE ARCHITECT - RETURNED TO THE WORKER (John's directive, 2026-07-25).**
John asked that Codex be made to confront its own errors rather than have them silently
patched. So D7 is logged and this goes back for the Worker to fix. The Architect fixed ONLY
the e2e selector (D2), because that fix was needed to expose D7 at all.
**PATTERN - SECOND ROUND RUNNING.** S3 and now S3R2 both shipped an e2e file the Worker
could not execute (the cap), and both times the ONLY defects were in that unrunnable
test file while the app was correct. S4b fixed this for the projection tests; e2e is
still out of reach. RECOMMENDATION for John: until the cap is raised, e2e authorship
should be Architect-side, or the Worker should stop declaring e2e files it cannot run.
**HYGIENE FINDING (not blocking):** `tests/test_workbench_cells_api_m17.py`
`test_document_session_round_trip_and_scope` writes a real approved review into the
DEVELOPER's live session store
(`.workbench_state/2025/sessions/documents/form_1040_2025.json`). That is the source of
the phantom "1 / 159 cells approved" John saw on a fresh load of the live UI - test
residue (`note: "ok"` on `f1_01`), not a real count. Gitignored so nothing leaks into the
repo, but it crosses the hermetic-tests standing rule and pollutes the surface John
reviews. Fix next round: point the session store at a tmp dir.
**ENV NOTE:** `.pytest_tmp` now fails cleanup with `PermissionError: [WinError 5]`
(leftover Codex sandbox ACLs), which makes clean files LOOK like errors - the boundary
file reported 3 spurious errors until re-run on a different basetemp. Workers are
instructed to use `.pytest_tmp`, so this needs a re-grant.

**Superseded BALL (kept for John's four issues, which are the review checklist) - the
round is DONE and pushed at `6488b6f`; see Current state.** Was: BALL: WORKER -
M17-S3R2 + S4 (John's second-review corrections). John reviewed the
live S3R UI on 2026-07-25 and returned four issues; the design is NOT rejected - the
form-sourced cell spine stands, and every complaint is about navigation, contrast,
labeling, and data depth. Plan is written in `plans/PHASE_M17.md` (S3R2, S4, S4b, and
the parked S5-INSTR); the Worker task block is under From Architect.** Architect
verified each issue against the code before planning:
1. River does not follow form selection (`app.js` `_selectionHandler` never scrolls the
   river) AND cross-page river selection silently no-ops (`_riverSelectionHandler` bails
   at `if (!official) return;` when the cell is on another page) - John's "completely
   hosed" case. Both are small, precise frontend fixes.
2. Selection ring collides with policy color: `.official-region.policy-unsupported` is
   `var(--danger)` and `.official-region.pinned` is `outline: 3px solid #c5452d` - red on
   red. Confirmed in `styles.css:84-86`.
3. "Unsupported" is a MISLABEL, and John's instinct is correct. The generated reason
   says the control "has no authored graph, filer-fact, or decision mapping" - it is a
   COVERAGE GAP, not a statement about the filer. 605 of 1921 corpus cells carry it
   (~31%). The UI must say "no mapping authored" in those words. RULING: relabel in the
   UI only this round; do NOT rename the enum in promoted artifacts - that is Tier 3
   across 605 cells and M16-S5 regeneration is what actually fills these in. **This is
   the direct link between John's UI review and the parked M16-S5: the workbench
   EXPOSES the gap, S5 CLOSES it.**
4. The dossier is genuinely thin, and worse than John knew: `cell_inventory._citations`
   returns bare citation IDs, never the `quoted_text` the citation records already
   carry, and the UI drops `reason` / `downstream_effect` / `missing_capability` from
   the field maps entirely. S4 labels every datum and names its source artifact.
On "did you not parse the instructions": the instruction PDFs ARE acquired for 7
documents, but only ONE instruction citation exists in the promoted corpus (out of 297).
There is no systematic per-cell instruction linkage. **JOHN RULED (2026-07-25): the
instructions explain the purpose and treatment of nearly every cell, so ingesting them
is ROUTINE PIPELINE WORK, not an enhancement.** Pinned as guiding invariant 7 in
`docs/engineering-plan.md` (alongside invariant 6, the pipeline end-state). Open item is
SEQUENCING, not whether: instruction text is also the input that lets a coverage-gap
cell be RESOLVED rather than merely reported, so it should land BEFORE or WITH M16-S5
regeneration. **DRAFTED: `plans/PHASE_M18.md` (Instruction ingestion), awaiting John's
sequencing.** Survey findings already in it: 7 documents acquired with per-page markdown;
`## Line X` anchors number 73 on the 1040 but ZERO on Schedule B, so heading conventions
are not uniform and per-doc detection is required; column-break hyphenation must be
repaired before any text is quoted or citation integrity will (correctly) reject it.
Architect recommendation in the doc: run M18 S1+S2 (read-only) in parallel with the M17
workbench rounds, then land S3 immediately BEFORE M16-S5. Three sequencing questions are
listed at the end of PHASE_M18 for John.
PREREQUISITE: the S3R working tree is still UNCOMMITTED (4 new files, 10 modified);
its focused test is green (8 passed, 157s). The Architect should land S3R as the base
commit before the Worker starts, so Codex is not building on an uncommitted tree.
NOTE the ~124s cap now bites the workbench tests themselves (the cells file takes 157s
because it imports `create_app`) - S4b splits it so the Worker can verify its own work.

**Worker session checkpoint - M17-S3 frontend shell (2026-07-24):** John said go.
Model GPT-5 Codex, effort default; usage/quota/context indicators are not exposed.
Single declared step: replace the current drawer-based static UI with the approved
three-pane review shell, using existing queue, entry, page-image, and session APIs.
Submit/verdict emission remains out of scope. Canary: Ledger Llama. Worktree was
clean at start.

Implementation checkpoint: replaced the drawer UI with the M17 three-pane shell in
`workbench/static/index.html`, `styles.css`, `app.js`, and new `river.js`; added
session load/save calls in `static/api.js`; the shell receives the local write token
from `workbench/server.py` for non-authoritative session persistence; added
`tests/e2e/test_workbench_v2_m17.py` under the new `m17` marker. Submit/verdict
emission remains untouched.

Verification: bundled Node syntax checks for `app.js`, `river.js`, and `api.js`
passed; ASCII, `git diff --check`, and module-form `validate 2025` passed. A
temporary cached-manifest preview with preflight monkeypatched passed 1 UI test,
including river selection and approve state. The real focused e2e partition hit
the documented launcher cap (exit 124; no assertion failure output), after the
cheaper session/ref command had emitted 8 passing dots before the same cap. The
cached manifest preview also exposes pre-existing `invalid_display_name` preflight
findings, so the real M17 e2e and real preflight are still pending. No commit yet.

**ARCHITECT VERIFICATION (Claude Opus 4.8, 2026-07-24) - GREEN, HOLDING FOR JOHN.**
Ran the two Architect-side gates the Worker's ~124s cap blocked:
- Real preflight (2m18s): PASSED, 3,243 units, `legacy_mined=394` (ratchet
  UNCHANGED). The `invalid_display_name` findings were a STALE CACHED-MANIFEST
  artifact, not a real defect - the freshly built manifest is clean, so
  `create_app`'s startup preflight passes and the e2e fixture builds the app.
- Real m17 e2e against the live 2025 projection: 1 passed, AFTER fixing two
  genuine defects in the Worker's declared test file (`tests/e2e/
  test_workbench_v2_m17.py`) - the app itself was correct in both:
  1. `cards.first()` / `card = cards.first()` - Playwright sync `Locator.first`
     is a PROPERTY, not a method (`TypeError: 'Locator' object is not callable`).
  2. `#river-detail .drawer-heading` asserted synchronously right after the
     select click, but `renderDetail` awaits `loadEvidence` before appending the
     heading - a race. Fixed with a `wait_for()` on the heading. (Sidenote: the
     first `object_ref` on addressed units is an `address`, which the evidence
     endpoint does not resolve, so it 404s and is caught gracefully - the heading
     still renders. Not a bug, but a frontend efficiency question for John.)
Remaining Tier-1 floor all GREEN: workbench boundary + write-api + m17 session
partition 12 passed (incl. the import-boundary check that bit M17-S2); ASCII;
`git diff --check`; module-form `validate 2025` (graph integrity OK). Diff is
in-boundary: `server.py` only serves the shell with the injected local write
token and wires session GET/PUT; no verdict, graph, or promoted-artifact change.
NOT committed: S3 is John-in-the-loop (approved mockup) - awaiting John's review
of the actual UI before the single commit + push.

**Superseded BALL (history only - the live BALL is at the top of this file):** BALL:
ARCHITECT - M17-S2 (quotable cell ref) IMPLEMENTED BY THE ARCHITECT and
verified; committing/pushing. Next is the frontend (S3, John-in-the-loop, uses the
approved mockup) and the deferred S2b submit->verdict flow.** The Worker could NOT
run this round: building the real 2025 manifest exceeds its ~124s launcher cap
(exit 124) before any code - a STRUCTURAL block on Codex doing workbench rounds
that need the live manifest. The ACL fix HELD (no flask PermissionError this time).
John's env question (2026-07-24) answered: the S1 flask error was the venv-rebuild
ACL regression; re-granted `CodexSandboxUsers` read+execute on `.venv` + `.python313`
(re-run after any venv rebuild - pinned in the Worker environment note). WORKFLOW
IMPLICATION for John: while the manifest-build cap stands, backend workbench rounds
are Architect-run (or need Codex's cap raised, or a cached-manifest fixture); the
big pipeline rounds (M16-S5) remain Codex's when John gives dispositions. M17-S1 is
ACCEPTED, pushed (`66042d1`), CI-GREEN (run 30082666775).

What M17-S2 landed: `workbench/refs.py` derives a short ASCII quotable ref per unit
deterministically from the canonical address (`sch2/4/amount`, doc abbreviated
injectively, role kept so two controls on one line stay distinct); `manifest.py`
sets `unit["ref"]` on addressed units; both unit schemas gained `ref` (printable
ASCII). Real-data finding: the contract is one ref per ADDRESS, not per unit - 386
cases are the same cell reviewed under two review_kinds and correctly share a ref;
`ambiguous_refs` flags only a ref spanning two DISTINCT addresses (zero across the
live 3,243-unit manifest). Tier-1 + manifest/workbench partition + gates green;
`legacy_mined=394` unchanged. NOTE: the first S2 push (`2103037`) went CI-RED on
`test_workbench_has_no_pipeline_imports` - `refs.py` imported `tax_graph.addressing`,
violating the workbench/pipeline decoupling. Fixed forward (`eeb5a73`) with a
stdlib-only address reader; ref behavior unchanged. LESSON (Tier-1 refinement):
a change under `workbench/` should run `tests/test_workbench_m15.py` locally (fast
architectural/boundary tests) in addition to the manifest partition - the manifest
partition does not exercise the import-boundary check. Verifying commit at HEAD is
`eeb5a73`; CI watched.

**Superseded (kept as history):** M17-S1 ACCEPTED/pushed BALL -

**Superseded (kept as history):** M17-S1 ACCEPTED/pushed BALL - The Worker's stop was environment
only (a sandbox `PermissionError` importing flask + the 124s cap; both work in the
Architect env). Work was complete and in-boundary: `unit_reviews` added to the
session schema (optional -> backward-compatible; ASCII-only note; approved/open
enum), sessions.py helpers (approve/reopen preserve note, fail closed on unknown
unit), a derived progress summary added to the GET/PUT RESPONSE only (popped before
persist, never schema-validated), and the existing write-api test updated to match.
Architect ran the full Tier-1 floor: declared focused files 15 passed; ASCII;
diff-check; module-form validate; real preflight `legacy_mined=394` unchanged. One
commit, pushed; CI watched. M16-S5 stays PARKED behind John's dispositions from
`plans/M16_S4_VALIDATOR_REPORT.md` (the first artifact-mutating step; resumes after
the workbench lands).

**Superseded (kept as history):** M16-S4 done + park-S5 BALL -
was: M16-S4 ACCEPTED, pushed, CI-GREEN; M16-S5 deliberately not launched as the
first artifact-mutating step.
Why S5 breaks the autonomous pattern: S1-S4 were additive and read-only (new
modules, tests, reports), so the worst case was a module needing revision. S5
rewrites field maps, bindings, and addresses - the load-bearing tax data - where
a bad regeneration can silently change what a filer's form prints. It is a Tier 3
diff by John's own amended floor (promoted artifacts / shared surfaces), it will
deliberately move the preflight ratchet below `legacy_mined=394` for the first
time, and the S3/S4 reports contain judgment calls only John can make: which
unresolved blocks get a structural contract (8949 table columns, W-2 box
templates) versus an explicit out-of-profile disposition (13614-C's 297
wrapperless controls). JOHN: read `plans/M16_S4_VALIDATOR_REPORT.md` (the S5 work
list, per-document finding counts) and `plans/M16_S3_RESOLVER_REPORT.md`, then
tell the Architect the dispositions and S5 gets drafted and sequenced.
Historical note for the S4 round: The Worker's
blocker was NOT an environment failure: it ran the console script
`.venv\Scripts\tax-graph.exe`, whose editable-install `.pth` hardcodes an
absolute repo path that does not resolve inside the Codex sandbox. The module
form (`python -m tax_graph.cli` / `python -m workbench.cli`) puts CWD on
sys.path and always works - it is what every other Worker command used. The
Architect prompt said "tax-graph validate 2025", so the Architect caused it;
the invocation rule is now pinned under Worker environment below. Architect
completed the two pending gates (validate green; real preflight
`legacy_mined=394` unchanged), reviewed the diff clean against every boundary
(no promoted artifacts, no call sites in validate/preflight/manifest, S1
fixture still strict-xfail), and fixed two things inline: renamed
`structural_checks.validate_field_maps` -> `check_document_structure` (it
collided with the existing `field_maps.validate_field_maps` and would have
confused the S5 wiring; the collision came from ambiguous Architect phrasing),
and fixed an operator-precedence bug that made three evidence fallbacks
unreachable. Focused tests 10 passed / 1 strict xfail after the rename.
Standing item for John (does not block S5): review
`plans/M16_S3_RESOLVER_REPORT.md` - 8949 table columns, W-2 box templates, and
13614-C wrapperless fields are honest unresolved blocks whose contracts S4/S5
must define. Optional CI quick win, now for feedback speed rather than cost:
the per-push matrix runs three Python versions at ~40-55 min each (3.12 is
always the straggler); trimming per-push to 3.13 with the full matrix nightly,
plus caching the playwright browser download, would cut the loop substantially.

**M16 status:** ACTIVE (`plans/PHASE_M16.md`, canary Straight Line).
- **S1 [DONE] `17d2351`** - Schedule 2 Part I characterization + strict-xfail acceptance
  fixture (`tests/test_schedule_2_m16.py`). It stays xfail until regenerated artifacts land.
- **S2 [DONE] `fc2a6c1`** - Stream A extraction typing: headings become non-fillable
  concepts instead of currency form_lines, `value_type` is inferred from the printed
  control, and PDF-present totals are emitted or explicitly out-of-profile. Also fixed
  the OCR anchor split (`z` -> `1z`) that was swallowing the Schedule 2 line 1z total.
- **S3 [DONE] `0f7ce2c`** - Stream B resolver core, read-only:
  `tax_graph/output/field_identity.py` derives each control's `(line, role)` from
  qualified field-name structure, same-row wrapper inheritance, and caption adjacency -
  never geometry or label mining - and returns `unresolved` rather than guessing. Ships
  with the read-only 9-form corpus comparison report.
- **NEXT: S4** - fail-closed structural validators; then S5 corpus regeneration.

**Step ledger:** M15 S1-S16 and A1-A3 are [DONE] and pushed; M15R R1-R15 are [DONE] and
archived. M15 Gate A is PAUSED and DECOUPLED from remaining-form completion (John,
2026-07-21): it closes on the workbench plus the forms already done, and the M16 pipeline
finishes the rest into the same surface. The A9h..A9z hand campaign is RETIRED/superseded
by M16 (marked in `plans/PHASE_M15.md`); A9a-A9g (9 of 15 forms, `legacy_mined` 1443 ->
394; commits `476e7ee`, `0ec62ae`, `82e07aa`+`1fb34b7`+`1e55e72`, `e0d367f`+`1c03019`,
`492698f`, `29eeeed`, `983303f`) STAND as the regression corpus the resolver must
reproduce. A10, A11, A6 are PAUSED, not cancelled. Gate A open through A13; S17+ blocked.

**Durable context:** John's 2026-07-14 Form 1040 review exposed the label/node-id/
PDF-field-name identity defect that M15R fixed with canonical addresses. His Gate A
feedback and the all-forms scope clarification are pinned as the correction invariants in
`plans/PHASE_M15.md`; the 2026-07-16 round-2 feedback is pinned in that plan's Gate A
round-2 section. Every fillable/checkable control on every exposed form must carry exactly
one population policy and be reviewable - no undefined cells, ever.

**Project state:** M0-M14 are COMPLETE and archived (`plans/archive/`, each with a close
note). THE GRAPH COMPUTES TAX, FILES IT, AND IS STAGED TO SHIP (alpha): computation and
witnesses through M13 (line 16 under OTS + IRS adjudication over the widened Schedule D
domain; filled official PDFs; return-scoped outputs); M14 added the product surface
(installable artifacts, extension harness, intake v1). M15 (Review Workbench + review
campaign) is THE PRE-SHIP GATE. Year rollover (TY2026) stays sequenced after M15 or when
TY2026 docs drop.

- **Public-repo prep (John, 2026-07-23):** the repo is being readied to flip from private
  to public. Two independent audits (Architect + Worker) found NO secrets, keys, tokens,
  or taxpayer PII in the tree, in reachable history, or in dangling commits. Committed
  machine paths were removed from `README.md`, `AGENTS.md`, and `plans/archive/PHASE_M6.md`,
  and this handoff was pruned. Open judgment call left to John: commit-author emails remain
  in history (a rewrite would invalidate every SHA this doc cites - not recommended).
  Never include ignored local artifacts (`_drafts`, `.cache`, `output`, workbench output)
  in any archive or upload.
- **John-only distribution checklist (post-close actions; artifacts staged + verified):**
  1. Configure PyPI trusted publishing for project `tax-graph` (repo `JohnKruse/tax_graph`,
     workflow `.github/workflows/release.yml`, environment `pypi`) at
     https://pypi.org/manage/account/publishing/, then GitHub Actions -> "Release alpha
     artifacts" -> Run workflow with `publish_pypi=true` (the ONLY route that enables the
     publish job).
  2. Download the `.mcpb` artifact from that run, install in Claude Desktop, then submit
     the tested bundle through the Connectors Directory. UX hazards to note in the
     submission and/or file as Anthropic app feedback: extensions install DISABLED with a
     tiny enable link; a config-file dev server with a near-identical name is invisible
     in the Extensions UI (twin-name collision confused testing); per-server logs record
     handshakes but not tools/call.
  3. After the PyPI release is visible: `mcp-publisher login github` then `mcp-publisher
     publish` from the repo to publish `server.json`; verify the
     `io.github.johnkruse/tax-graph` listing at registry.modelcontextprotocol.io.
- **Review queue (M15's raw material):** M10/M11 promotion entries; M12's 11
  field_map_review entries; QDCGT worksheet (high); deduction decision node (TOP); M13's
  Schedule D Tax Worksheet + line-20 decision; `extension_review_form_2441_2025`
  (accepted_local, machine_agreed: false - first review items: the two cross-gate hookup
  edges and the failed Part II math, see archived Step-3 findings A/B); 3 intake_review_*
  entries (routing/triggers/expectations). `human_minutes` stays honestly null until M15.
- **Carried-forward named gaps (M13 Option B; see `plans/archive/PHASE_M13.md` Step 4):**
  (1) PolicyEngine liability witness pending - widen `scenario_inputs_from_facts`, live PE
  over the `m6_seed1315` corpus, refreeze `pe_liability_2025.json`, re-enable the two
  skipped tests; do NOT claim dual-witness on the widened domain until then. (2)
  parameter-diff HoH top-bracket floor (626350 cited vs 375800 fixture) - source review,
  never edit the cited graph parameter without it. (3) The form-2441 extension queue entry
  cannot derive object scope on a parity checkout (no installed extension); the live
  migration and contribution tests are GATED on `graph_ext/2025/form_2441_2025` being
  present, not fixed - it resurfaces when that review lands.
- **Standing rules (cumulative):** ASCII only (pre-push hook `.githooks/pre-push` +
  CI enforce; enable per clone with `git config core.hooksPath .githooks`); hermetic
  tests - no `_drafts` reads, no shared `build/` artifacts (tmp sqlite), and a machine
  with an installed extension IS the normal dev state (use
  `Graph(..., include_extensions=False)` for shipped-content parity); **close-out
  ordering: `frontier build` FIRST, `verify record` SECOND, commit together** (the
  content hash covers frontier.yaml); **commit floor (AMENDED v2 by John,
  2026-07-23, granular tiers): Tier 1 EVERY COMMIT = focused test FILES
  covering the changed modules + any new tests (the Worker DECLARES the
  chosen files in the handoff) + fast gates (ASCII, diff --check, validate,
  preflight); Tier 2 EVERY PUSH = full CI matrix on the pushed commit,
  Architect-watched to green; Tier 3 BIG SHAKEDOWN (full local partitions +
  fresh-checkout sim) ONLY for CI-red investigation, diffs touching promoted
  artifacts / shared surfaces (graph/, field maps, bindings, citations,
  manifest), phase closes/gates, or at John's request. Sequential pytest
  always - concurrent launches orphan children on this box**; **CI on the
  pushed commit must be green at every step commit and phase close** (watch it - do not
  skip for "docs-only" changes, the ASCII gate bites those too); live-execution passes
  for anything an outside tool/user consumes; drafts never committed; base-deps light;
  citations are verbatim-from-acquired-source ONLY - `check_citation_integrity` has
  teeth, use it (the M14 fabricated-citations reopen is the precedent); John-only
  outward actions - no agent publishes, submits, or uploads.
- **Worker environment (2026-07-23):** the recurring `Access is denied` on
  `.venv\Scripts\python.exe` was the venv launcher shim spawning the OUT-OF-WORKSPACE base
  interpreter, which the Codex sandbox denies per session (it is NOT a machine state and no
  restart fixes it). Fixed by mirroring the base interpreter to `.python313/` inside the
  repo (gitignored) and rebuilding `.venv` on it, so `pyvenv.cfg home` is in-workspace.
  Workers call `.venv\Scripts\python.exe` directly - no `uv` needed. **UPDATED 2026-07-25: do
  NOT pass `--basetemp` any more.** The root `conftest.py` pins the temp root to `.test_tmp/`
  for every account, and pytest separates accounts automatically via
  `.test_tmp/pytest-of-<username>/`. The old `.pytest_tmp` is poisoned and unreclaimable; see
  the hard rule in `AGENTS.md`. **CAP RAISED TO 600s (John, 2026-07-26; was ~124s, then 240s)** -
  the Worker now runs its OWN e2e and app-dependent files (the full pair measured 319s). Only
  full partitions and Tier 3 shakedowns stay Architect-side. Anything that still does not fit
  gets an honest `NOT RUN:` line, never a guess.
  **ALWAYS use the module form, never the console scripts** (2026-07-23, M16-S4):
  `.venv\Scripts\python.exe -m tax_graph.cli validate 2025` and
  `.venv\Scripts\python.exe -m workbench.cli preflight --year 2025`. The generated
  `tax-graph.exe` / `review-workbench.exe` launchers resolve the package through the
  editable install's `.pth`, which hardcodes an absolute repo path that does not resolve
  inside the Codex sandbox (`ModuleNotFoundError: No module named 'tax_graph.cli'`). The
  module form puts CWD on sys.path and works everywhere. Architects: write the module
  form into Worker prompts.
- **Recurring op note:** orphaned `serve` processes have first-class tooling -
  `tax-graph serve --sweep-orphans` (dogfooded live on a real orphan). The parent
  watchdog works on Windows as of M14 (OpenProcess probe; the os.kill(pid,0) probe was
  inert). Serve writes stderr breadcrumbs (`tax-graph serve: starting/...`) that Claude
  Desktop logs verbatim - first stop when a client-managed server dies.

## Open for Architect
- **M20-S3a -> S3b decision needed (2026-07-28):** Should the structure step own a
  deterministic corrected-text outline adapter (using page/geometry plus `line_anchors`)
  before S3a regeneration resumes? The bare positional index is not enough: its offsets are
  exact strings but can point at repeated anchor text in another semantic row. S3a therefore
  stops fail-closed; no generated draft is promoted, and no citation/label is hand-edited.
- **RESOLVED 2026-07-26 by the 600s cap:** the manifest-build blocker that made backend
  workbench rounds Architect-run is GONE. Codex can now build the live manifest (~150s) and
  run its own app-dependent and e2e files. The two workflow rulings that existed only because
  of the old cap are RETIRED: (a) "backend workbench rounds are Architect-run", and (b) "e2e
  authorship should be Architect-side, or the Worker should stop declaring e2e files it cannot
  run". Workers own their e2e again, and are expected to run it. No cached-manifest fixture is
  needed.
- **RESOLVED (kept as history) - M17-S1 environment blocker (2026-07-24):** the venv ACL
  grant fixed the flask `PermissionError`, the 600s cap retired the launcher-cap half, and
  the pending work below was completed and pushed long ago. Nothing here is open. Was: the
  split focused run passed 10
  schema/helper tests, then failed during the self-contained API fixture setup with
  `PermissionError: [Errno 13] Permission denied` importing
  `.venv\\Lib\\site-packages\\flask\\testing.py`. The earlier combined declared-file
  run exceeded the 120-second launcher cap after 7 tests and was terminated with no
  assertion failure output. Pending: rerun the new API test and the live
  `tests/test_workbench_write_api_m15.py`, then all Tier-1 gates, inspect/fix any
  failures, and make the single local commit. No commit was made.

### Worker session checkpoint - M17-S1 (2026-07-24)
- Declared step: M17-S1 per-unit review state only; backend only. Canary: Ledger Llama.
- Session-start checkpoint: model GPT-5 Codex, effort level default, and no usage/quota/context
  indicators are exposed.
- Pre-expensive-work checkpoint: M17 design and existing session/schema/server mapping read.
  Focused files declared for the Tier-1 floor: `tests/test_review_schemas_m15.py`,
  `tests/test_workbench_write_api_m15.py`, and new `tests/test_workbench_sessions_m17.py`;
  tests use the existing `m15` marker. Derived GET progress will not be persisted, and
  unknown per-unit review ids will fail closed against the queue manifest.

### Worker session checkpoint - M16-S4 (2026-07-23)
- Declared step: implement the four Stream B structural validators, focused Schedule 2 Part I
  tests, and the read-only promoted-corpus report; no validate/preflight/manifest call sites.
- Focused test files declared for the Tier-1 floor: `tests/test_structural_checks_m16.py`,
  `tests/test_field_identity_m16.py`, and `tests/test_schedule_2_m16.py` (the last remains
  strict-xfail and is not to be edited).
- Session-start checkpoint: model GPT-5 Codex, effort high, usage/quota/context indicators not
  exposed. Required handoff/phase/S3 documents read. Current worktree has only this expected
  handoff edit; implementation has not started.
- Implementation checkpoint: added `tax_graph/output/structural_checks.py` and
  `tests/test_structural_checks_m16.py`; the new focused file is green (3 passed). No promoted
  artifact, graph semantic, binding, citation, manifest, validate, or preflight call-site edit.
- Pending verification: resolver regression, unchanged strict-xfail Schedule 2 file, corpus report,
  ASCII/diff checks, `validate 2025`, and real preflight ratchet.

### Open for Architect - M16-S4 environment blocker (2026-07-23)
- Required command attempted: `.venv\\Scripts\\tax-graph.exe validate 2025`.
- Exact failure: `ModuleNotFoundError: No module named 'tax_graph.cli'` from the generated
  `.venv\\Scripts\\tax-graph.exe` launcher, despite `tax_graph\\cli.py` existing in the clone.
- Completed before the stop: `tests/test_structural_checks_m16.py` 3 passed; resolver file 6
  passed; Schedule 2 file 1 passed / 1 strict xfail; corpus report generated; ASCII and
  `git diff --check` green. No promoted artifacts or S1 fixture changed.
- Pending: required `validate 2025`, real preflight with `legacy_mined=394`, final handoff
  verification, and the single local commit. No workaround launcher was attempted after the
  environment failure, and no commit was made.

## From Architect

- **M20-S23 TASK (RESPECCED 2026-08-02) - BUILD THE `instruction_sections` ARTIFACT AND FIX ITS
  JOIN. Deterministic. NO MODEL CALLS. (Architect, Claude Opus 5.)** Ledger: the RAN/NOT RUN
  rule, D9, D6.
  **READ FIRST: `docs/engineering-plan.md`, section "Extraction as typed frames between pure
  functions".** It records the diagnosis, the architecture, and the M20 exit criteria. This round
  is exit criterion 1 and the first half of criterion 2.
  **WHY THIS FIRST.** `instruction_sections` is the only frame in the architecture that does not
  exist at all, and its join is the worst one we have. Line 21 did not fail loudly - it returned
  **confident, plausible arithmetic built from another form's worksheet**. Until the evidence is
  right, measuring expression quality measures the wrong thing.
  1. **BUILD THE ARTIFACT: per form, per line, verbatim text, with locators.** One deterministic
     pass over each acquired instruction booklet. It is a build artifact that can be opened and
     read, not a query-time join.
  2. **CARRY FORM CONTEXT - this is the bug.** The 1040 booklet ALSO covers Schedules 1, 2 and 3.
     Architect-measured: **`## Line 9` appears twice, `## Line 10` three times**, and Lines 4, 5,
     11, 12, 16 and 19 twice each. Attribution must use the form section a heading sits under,
     never the line number alone. **Never resolve a collision by picking the longest body** -
     that is exactly how the Architect's experiment extractor gave Form 1040 line 9 a Schedule's
     Household Employment Taxes text.
  3. **END A SECTION AT THE NEXT HEADING OF EQUAL OR HIGHER LEVEL**, not at the next `## Line`
     heading. Ending at the next `## Line` swallows intervening `##`/`###` sections that belong
     to neither line.
  4. **RETIRE THE COMPETING IMPLEMENTATIONS.** There are currently three independent
     line-to-instruction joins - the span miner, the S17 `## Line X` join, and
     `experiments/prompt_experiment.py`'s extractor - with three different bugs and one shared
     blind spot. **Everything downstream reads the new artifact.** Update the experiment script
     too so the bench and the pipeline agree.
  5. **PUBLISH COVERAGE.** Per form: lines with a section, lines without, sections that could not
     be attributed to a form, and collisions resolved by form context. **Report wrong-owner spans
     before and after** (the 1040 stood at 45 after S17, from 89).
     **Expect coverage to FALL on some forms and say so** - Schedule A's booklet genuinely does
     not discuss its computed lines, and per John (2026-07-31) augmenting instructions are never
     mandatory. A lower, honest number is the goal.
  6. **Add a test that Form 1040 line 9 does NOT contain "Household Employment Taxes"** and that
     line 21 does not contain Student Loan Interest Deduction Worksheet text. Those are the two
     known collisions; pin them.
  **PROTECTED TEST SET, unchanged hard gate:** `graph/2025/{nodes,edges,rules}/` and
  `graph/2025/field_maps/` byte-identical. No promotion, no hand-authoring, no live graph edit.
  **FORCE-ADD ANY REPORT** (`output/` is gitignored). **CITE THE ACTUAL COMMIT HASH.**
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`, module-form
  `validate 2025`, real preflight with `legacy_mined` explicit (expect **394**),
  `check_citation_integrity` STRICT (expect **36**). Short pytest temp root; no `--basetemp`.
  ONE local commit; no push. **Do not commit with known failing tests.**
  **Stop conditions:** any diff in the protected directories; any draft promoted; resolving a
  duplicate line-number collision by body length or any heuristic other than form context;
  leaving more than one line-to-instruction join in the tree; paraphrasing instruction text
  (it is verbatim-from-source and rides citation integrity); `legacy_mined` above 394; strict
  mismatches above 36.

- **M20-S24 TASK - `derive_cells` AS A PURE FUNCTION, WITH EXPRESSION TREES (Architect, Claude
  Opus 5, 2026-08-02). Runs after S23.** Exit criteria 3 and 5.
  1. **Extract the sub-pipeline to `derive_cells(frame, prompt, api_key) -> frame`** per the
     engineering-plan contract. **It writes nothing** - callers write. That makes S20's failure
     mode (a network blip deleting `edges.yaml`) impossible rather than guarded.
  2. **Row-level `status` and `error`.** One bad row never fails the frame.
  3. **Prompt from CONFIG, not code.**
  4. **Expression TREES, not one enum plus a flat list.** Architect-proved with the bench
     (`509264b`): changing only the schema turns line 15 into `max(line 11b - line 14, 0)` and
     line 22 into `max(line 18 - line 21, 0)`. The flat schema has no slot for a wrapper, so it
     has been silently discarding every floor and cap. Reference implementation:
     `experiments/prompt_experiment.py` (`expression_schema`, `render`). Bound the depth; do not
     use `$ref` recursion.
  5. **Deterministic tree-to-graph conversion**, matching the live convention for 1040 line 15
     (intermediate computed node, `subtract_currency` edges with minuend/subtrahend, then
     `max_currency` edges). Reference: `experiments/to_graph.py`. **Roles come from the operation
     and position, never from the model.** Settle the intermediate node naming - the live set
     uses `_pre_floor`, the experiment uses `_step1`.
  6. **Tests that need no network**, using a fixture frame.

- **M20-S26 TASK - THE FORM FACE IS EVIDENCE (Architect, Claude Opus 5, 2026-08-02). Runs after
  S25.** Exit criterion 4, unchanged: property validators proven on real data. S25 built them
  correctly and they never ran, because one input check rejected every computed line.
  **Architect diagnosis, verified directly against real 2025 data - do not re-derive it:**
  The instruction booklet has 70 sections for Form 1040, covering 56 printed lines - and NOT ONE
  of them is a computed line. Owned lines are `1a..1i, 2a, 2b, 3a, 3b, 4a..4c, 5a..5c, 6, 6a..6d,
  7a, 7b, 10, 12a..12e, 13a, 13b, 16, 19, 25a..25c, 26, 27a..27c, 28..31, 34, 35a..35d, 36..38`.
  The IRS elaborates on INPUT lines in the booklet and states the arithmetic for SUBTOTAL lines on
  the form face itself. `1z, 9, 11a, 11b, 14, 15, 18, 21, 22, 24, 25d, 32, 33` have no instruction
  section and never will. This is correct IRS structure, not an acquisition gap, and it is the
  direct consequence of S23's ownership fix, which was right and must not be regressed.
  The evidence we need is already in hand. Line 22's face reads `Subtract line 21 from line 18.
  If zero or less, enter -0-`; line 15's reads `Subtract line 14 from line 11b. If zero or less,
  enter -0-`. Operand order AND the floor trigger are both there.
  **JOHN'S ARCHITECTURAL BOUNDARY (2026-08-02) - this governs the whole round and outranks any
  detail below it. Three layers, three different standards of accuracy:**
  - **FORM FACE: EXACT.** Labels and line numbers pulled out accurately, per cell, every time.
    This is deterministic geometry work and it is the one place we hold a hard line.
  - **INSTRUCTION PAGES: LOOSE.** Carve the page into sections best-effort. "You may or may not
    get a line instruction; expect about half of them to have nothing useful." **Holes are the
    expected steady state, not a defect.** Never gate the pipeline on instruction coverage.
  - **RECONCILIATION: THE AI'S JOB.** Making sense of the mishmash of labels and partial
    instructions belongs to the operation-extraction subpipeline (`derive_cells`), not to the
    extractor and not to a deterministic validator.
  Consequence: **items 1 and 4 below are the round.** Everything else is secondary.
  1. **Require evidence, not instruction text.** `tax_graph/extract/cells.py:455` raises hard
     `missing_instruction_text` whenever `instruction_text` is empty. Replace it with a check that
     at least ONE cited evidence source is non-empty - `form_face_text` OR `instruction_text`.
     Absent instruction is a normal recorded state for a computed line, not a failure.
  1b. **Demote the instruction-ownership checks from hard failure to drop-the-section.**
     `instruction_wrong_owner` and `instruction_wrong_line` currently kill the row. Under the
     boundary above that is wrong: a loosely-carved page WILL produce doubtful attributions, and
     the correct response is to not attach that text - leaving a hole - never to fail a cell whose
     face text is perfectly good. **Keep the detection exactly as S23 built it** (it is what stops
     Schedule 2's text reaching 1040 line 9, and `wrong_owner_after` must stay 0); change only the
     consequence, and record dropped sections in row metadata so the drop is visible and countable.
     This is not a regression of S23 - S23's job was to stop wrong attribution, and dropping is a
     stricter answer than attaching.
  2. **Keep every S23 ownership check exactly as-is.** When instruction text IS present it must
     still be attributed to this form and line. The fix is narrow: stop requiring presence. Do not
     touch `instruction_wrong_owner` or `instruction_wrong_line`.
  3. **Validate floor/cap against the COMBINED cited evidence.** If the check only reads
     `instruction_text` it will miss `If zero or less, enter -0-` on lines 15 and 22 - the exact
     defect this round exists to catch. Same for operand-order-vs-label and the
     operands-in-cited-text WARNING.
  4. **PRIMARY DELIVERABLE - fix label contamination.** This is the one thing that violates
     John's exact-form-face standard, so it is promoted above everything else in this round.
     Geometry is bleeding neighbouring text into `label`/`form_face_text`. Real values today:
     line 14 is
     `"$15,750 14 Add lines 12e, 13a, and 13b"`; line 15 is `"jointly or 15 Subtract line 14..."`;
     line 22 is `"12a, 12b, 12c, 22 Subtract line 21 from line 18..."`. Line 22's own evidence
     names 12a/12b/12c, which are not its operands - a model can plausibly pull them in, and the
     operands-in-cited-text warning would stay silent because they ARE in the text. Strip the
     leading run that precedes this row's own printed line token. Report before/after.
     **Every one of the 17 computed rows must end with a label that starts at its own printed
     line token and contains no neighbouring row's text.** Print the full 17-row before/after
     table in the handoff - this is the round's headline evidence, alongside `derived`.
     Do NOT gate on instruction coverage, and do NOT add a check that every printed line has an
     instruction section. A hole is a legitimate outcome; the AI reconciles it downstream.
  5. **Then run the real 1040 and report derived / repaired / gapped / errored, plus how many
     expressions gained a floor or cap the flat schema was dropping.** That number is the point of
     the round. Expect 17 attempted; expect a floor on 15 and 22 at minimum.
  6. **Transport errors must not end the run.** All 4 rows that reached the provider died on
     `LlmUnavailable: Connection error`. S21 retry exists; make the runner resumable so a network
     blip costs a retry, not the round. This is the "no heroics each year" requirement.
  **PROTECTED TEST SET, unchanged hard gate:** `graph/2025/{nodes,edges,rules}/` and
  `graph/2025/field_maps/` byte-identical. No promotion, no hand-authoring, no live graph edit,
  nothing into `content_fingerprint`. **`derive_cells` must remain pure - zero disk writes**
  (Architect re-verified this holds at `ff62119`; keep it holding).
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`, module-form
  `validate 2025`, real preflight with `legacy_mined` explicit (expect **394**),
  `check_citation_integrity` STRICT (expect **36**). Short pytest temp root; no `--basetemp`.
  ONE local commit; no push. **Do not commit with known failing tests.** **CITE THE ACTUAL COMMIT
  HASH.**
  **Stop conditions:** any diff in the protected directories; any draft promoted; `derive_cells`
  acquiring a disk write; making the operands-in-cited-text check a hard failure; more than one
  repair attempt per row; hand-authoring; `legacy_mined` above 394; strict mismatches above 36;
  **weakening S23 wrong-owner DETECTION to get rows flowing** (`wrong_owner_after` must stay 0 -
  demoting the consequence per item 1b is required, weakening the detection is a stop);
  **`derived` still 0 at the end of the round without a stated, evidenced reason**; **adding any
  gate, check or hard failure keyed on instruction-section coverage** - that is explicitly against
  John's boundary and it is the mistake the Architect nearly shipped this round.
  **A model or provider failure is NOT a stop condition** - `google/gemini-3.6-flash` is known
  good, and transport errors are retried per S21.
  **Review-surface work resumes after this round, not before.**

- **SUPERSEDED (kept as history; delivered by S25 at `ff62119`, ACCEPTED with the input-validator
  defect carried into S26) - M20-S25 TASK - PROPERTY VALIDATORS AND REPAIR-ONCE (Architect,
  Claude Opus 5, 2026-08-02). Runs after S24.** Exit criterion 4.
  Each validator below is a bug we actually shipped - no speculative checks. Full list and
  rationale in `docs/engineering-plan.md`.
  - expression must not reference its own line (S12: 11 of 11 did)
  - every operand resolves to a printed line on THIS form, or is an explicit cross-form ref
    (line 21 built arithmetic from another form's worksheet)
  - `SUBTRACT`/`DIVIDE` take exactly two operands
  - label says "Subtract A from B" -> tree must be `B - A` (S14: reversed roles hidden by a
    ref-set comparison)
  - cited text says "If zero or less, enter -0-" -> tree must contain `MAX(..., 0)`
  - quote verbatim from a real mined span
  - operands SHOULD appear in the cited text - **WARNING, never a hard failure**: on line 9 the
    model correctly included 4b, 5b, 6b that the hand-authored set omitted
  **On failure, repair ONCE** with the specific complaint fed back; only a second failure becomes
  a named review gap. Report attempted / repaired / gapped, and validator failures by kind.
  **Then re-measure** and report how many expressions gained a floor or cap the flat schema had
  been dropping.
  **ALSO IN THIS ROUND - the three carry-forwards from the BALL:**
  - **Persist the `instruction_sections` frame and its coverage report.** Still computed only;
    no committed artifact exists to open. Force-add it (`output/` is gitignored).
  - **Finish retiring the legacy owner parser**, or state plainly why it must stay.
  - **Run `derive_cells` against the REAL 1040** - S24 was fixture-only and correct to be. Report
    row-level status counts: derived, repaired, gapped, errored.
  **Validators belong INSIDE `derive_cells`, at both edges** (engineering-plan: "Put the
  validation inside the function"). Input checks: every row has a label; instruction text is
  attributed to THIS form and line. Output checks: the property list above. A clean function with
  no validation would still emit line 21's Student Loan arithmetic.
  **PROTECTED TEST SET, unchanged hard gate:** `graph/2025/{nodes,edges,rules}/` and
  `graph/2025/field_maps/` byte-identical. No promotion, no hand-authoring, no live graph edit,
  nothing into `content_fingerprint`. **`derive_cells` must remain pure - zero disk writes.**
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`, module-form
  `validate 2025`, real preflight with `legacy_mined` explicit (expect **394**),
  `check_citation_integrity` STRICT (expect **36**). Short pytest temp root; no `--basetemp`.
  ONE local commit; no push. **Do not commit with known failing tests.** **CITE THE ACTUAL COMMIT
  HASH.**
  **Stop conditions:** any diff in the protected directories; any draft promoted; `derive_cells`
  acquiring a disk write; making the operands-in-cited-text check a hard failure; more than one
  repair attempt per row; hand-authoring; `legacy_mined` above 394; strict mismatches above 36.
  **A model or provider failure is NOT a stop condition** - `google/gemini-3.6-flash` is known
  good, and transport errors are retried per S21.
  **Review-surface work resumes after this round, not before.**

- **SUPERSEDED (kept as history; delivered by S24 at `e6e94e3`) - PART A - THE SCHEMA IS
  DISCARDING THE FLOORS. Architect-proved with the S22 bench, commit
  `509264b`.** The micro extraction schema is `{operation: <one enum>, source_lines: [flat],
  quote}`. **There is no slot for a wrapper, so `max(a - b, 0)` is unrepresentable.** The graph
  itself stores NESTED expressions, so the extraction schema is strictly less expressive than the
  graph it feeds.
  Same model, same evidence, same prompt content - only the schema changed:
  | line | flat schema (today) | expression tree |
  |---|---|---|
  | 1z | `SUM` sources 1a..1h | `line 1a + line 1b + ... + line 1h` |
  | 11a | `SUBTRACT` sources 9, 10 | `line 9 - line 10` |
  | **15** | `SUBTRACT` sources 11b, 14 | **`max(line 11b - line 14, 0)`** |
  | **22** | `SUBTRACT` sources 18, 21 | **`max(line 18 - line 21, 0)`** |
  Both those instructions say "If zero or less, enter -0-". **The model always understood it and
  had nowhere to put it.** This also retires an Architect misreading: S13 recorded line 15 as the
  model missing a floor convention it could not know about. It was the schema.
  1. **Change the micro extraction schema to an expression tree.** Operands are `{"line": "18"}`,
     `{"const": 0}`, or a nested expression. **Bound the depth** (2-3 is enough for real IRS
     lines) rather than using `$ref` recursion, which structured-output support handles
     unevenly. Reference implementation: `experiments/prompt_experiment.py`
     (`expression_schema`, `_expr`, `_operand`, and `render`).
  2. **Render the tree as ordinary math for the human** - `max(line 18 - line 21, 0)` - per the
     S16 rendering standard. `render()` in the bench is a working reference. **The model never
     emits the rendered string; code renders it.**
  3. **Keep identity resolution in CODE.** The tree carries PRINTED LINE NUMBERS only; never ask
     the model for node ids. Unchanged from S13, and it is why the tree is safe.
  **PART B - VALIDATE AND REPAIR BEFORE A HUMAN EVER SEES IT. John: "Do you think the pipeline
  should have a process of batching the expression creation with some error checks before it
  gets to the human review? I feel like this is really brittle." He is right.** Today one model
  call per cell goes straight to a review gap on any failure, and every defect we have found
  reached "review-ready" state or degraded silently.
  4. **Add deterministic validators. Every one below is motivated by a defect we actually hit -
   no speculative checks:**
     - **self-reference** - an expression referencing its own line (S12: 11 of 11 were
       self-referential).
     - **referenced line exists** on this form, including parent/lettered-child resolution
       (S18: `2` -> `2a`, `19` -> `19a`).
     - **arity per operation** - `SUBTRACT`/`DIVIDE` take exactly two args.
     - **operand order against the label text** - "Subtract line 21 from line 18" must produce
       args `[18, 21]`. The label states the rule; parse it and cross-check (S14: line 11a had
       identical ref sets with reversed roles, which the ref comparison hid).
     - **floor/cap presence** - if the cited text contains "If zero or less, enter -0-" the tree
       must contain `MAX(..., 0)`; "but not more than $X" must contain `MIN`. **This is the check
       that catches today's defect.**
     - **operands are mentioned in the cited text** - catches invented operands. NOTE: this must
       be a WARNING, not a hard failure - on line 9 the model correctly included 4b, 5b and 6b
       that the handcrafted set omitted, and it was right.
     - **quote is verbatim** - already enforced; keep it.
  5. **ON FAILURE, REPAIR ONCE - do not go straight to a gap.** Feed the specific complaint back
     ("your expression references line 22, which is the line being computed") and retry once.
     Only a second failure becomes a named review gap. Report attempted / repaired / gapped.
  6. **"BATCHING" MEANS ORCHESTRATION, NOT ONE BIG PROMPT.** Parallelise per-cell calls and
     report them as a group. **Do NOT combine multiple cells into one prompt** - that is the
     whole-document call that burned S7 through S11 and pinned responses at the token cap.
  7. **Re-measure and report:** formula completeness, how many expressions gained a floor or cap
     that the flat schema had dropped, and validator failures by kind. **Report honestly if the
     tree change breaks cells that previously passed.**
  **PROTECTED TEST SET, unchanged hard gate:** `graph/2025/{nodes,edges,rules}/` and
  `graph/2025/field_maps/` byte-identical. No promotion, no hand-authoring, no live graph edit.
  **FORCE-ADD THE REPORT** (`output/` is gitignored). **CITE THE ACTUAL COMMIT HASH.**
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`, module-form
  `validate 2025`, real preflight with `legacy_mined` explicit (expect **394**),
  `check_citation_integrity` STRICT (expect **36**). Short pytest temp root; no `--basetemp`.
  ONE local commit; no push. **Do not commit with known failing tests.**
  **Config note: `extraction.expression_mode` stays `none`.**
  **Stop conditions:** any diff in `graph/2025/{nodes,edges,rules}/` or `graph/2025/field_maps/`;
  any draft promoted; combining multiple cells into one prompt; asking the model for node ids;
  making the "operands mentioned in cited text" check a hard failure; more than one repair
  attempt per cell; hand-authoring; `legacy_mined` above 394; strict mismatches above 36.

- **M20-S22 TASK - FIX THE EVIDENCE PACKET, THEN BUILD THE BENCH THAT WOULD HAVE FOUND IT
  (Architect, Claude Opus 5, 2026-08-01). John's framing: "if you give an AI the right context
  and prompt, you can get the right response. Pretty clearly, we are spending a lot of horsepower
  on non central issues." He is right, and this round is the proof.** Ledger: the RAN/NOT RUN
  rule, D9, D6.
  **THE DIAGNOSIS - Architect-measured 2026-08-01. THE PROMPT IS NOT THE PROBLEM.**
  S21's rerun: `background_controls_attempted: 119`, `succeeded: 15`, `failed: 99`,
  **`background_transport_failures: 0`**. The model answered every single call. All 99 failures
  are one error: `background policy quote has no form-face citation`.
  **Cause, and it is self-contradicting:**
  - `tax_graph/extract/background.py:361` - `if span.relationship != "source": score += 1`.
    **Instruction spans are scored ABOVE form-face spans.**
  - The corpus is **5,021 instruction spans against 222 form-face spans** for the 1040, so the
    top-8 evidence packet is overwhelmingly instruction text.
  - `tax_graph/extract/background.py:118` then **rejects any answer whose quote does not match a
    `relationship == "source"` (form-face) span.**
  **We rank instructions highest, hand the model almost only instructions, then fail it for not
  quoting the form face.** The model is doing exactly what the packet invites.
  **NOTE the partial mitigation at `background.py:366-372` is insufficient:** it tops up
  form-face spans only when `source_selected` is EMPTY. One weak form-face span in the top 8
  suppresses the top-up while still leaving the packet instruction-dominated.
  1. **FIX THE EVIDENCE PACKET SO IT MATCHES THE REQUIREMENT.** Either guarantee form-face spans
     in the packet (reserve slots, and stop scoring instruction spans above them), or relax the
     requirement to accept an instruction quote when the control genuinely has no form-face text.
     **Do not do both blindly - decide, state which, and say why.** Report
     attempted/succeeded/failed after the change; the number to move is `policy_derived`, which
     is currently **0**.
  2. **`policy_derived` IS THE METRIC. `policy_defaulted` IS NOT PROGRESS.** S21 moved 19
     controls and every one was a failover, not a derivation. A drop in `unsupported` achieved by
     failover is relabelling. Keep the columns split and report both.
  3. **BUILD A READ-ONLY PROMPT BENCH. This is the round's durable deliverable.** Today,
     diagnosing the above took the Architect a dozen queries of archaeology, and testing any fix
     requires a multi-minute destructive pipeline run. Build a command that:
     - takes a document and a small list of control or cell ids,
     - runs the real prompt path for each,
     - prints the **exact prompt sent**, the **exact response**, and **why the answer was
       accepted or rejected** (which span matched, which validation failed),
     - **writes NO drafts and touches no promoted artifact.**
     Seconds, not minutes. Had this existed, today's diagnosis would have been one command.
     Keep it small - it is a diagnostic tool, not a framework.
  4. **DO NOT "TUNE THE PROMPTS" IN THIS ROUND.** There is no evidence of prompt-quality failure
     anywhere in this project. Line 1z came back perfect on the first attempt in S13 and formula
     completeness reached 28/28 in S18. **Every failure so far has been ours** - join logic,
     hardcoded operand roles, evidence selection, destructive writes. If the bench later shows a
     genuine prompt weakness, that is its own round with evidence attached.
  5. **RECOVER THE TWO LOST FORMULA CELLS.** S21's rerun came back 26/28, not 28/28. Identify
     which two and why, and report; do not paper over it.
  **PROTECTED TEST SET, unchanged hard gate:** `graph/2025/{nodes,edges,rules}/` and
  `graph/2025/field_maps/` byte-identical. No promotion, no hand-authoring, no live graph edit.
  **FORCE-ADD THE REPORT** (`output/` is gitignored). **CITE THE ACTUAL COMMIT HASH.**
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`, module-form
  `validate 2025`, real preflight with `legacy_mined` explicit (expect **394**),
  `check_citation_integrity` STRICT (expect **36**). Short pytest temp root; no `--basetemp`.
  ONE local commit; no push. **Do not commit with known failing tests.**
  **Config note: `extraction.expression_mode` stays `none`.**
  **Stop conditions:** any diff in `graph/2025/{nodes,edges,rules}/` or `graph/2025/field_maps/`;
  any draft promoted; the bench writing drafts or touching promoted artifacts; reporting
  `defaulted` and `derived` as one number; tuning prompts without bench evidence; hand-authoring;
  `legacy_mined` above 394; strict mismatches above 36.

- **M20-S21 TASK - ATOMIC DRAFT WRITES, RETRY TRANSIENT NETWORK ERRORS, THEN RERUN (Architect,
  Claude Opus 5, 2026-07-31). Small, mechanical, and it protects every round after this one.**
  Ledger: the RAN/NOT RUN rule, D9, D6.
  **WHAT HAPPENED IN S20 - Architect-diagnosed 2026-07-31, and it is NOT what the S20 notes
  say.** S20 reported "provider-blocked" and 185 calls attempted / 0 succeeded. The actual
  recorded reason in `_drafts/form_1040_2025/review_gaps.yaml` is
  **`OpenRouter request failed: Connection error.`** - a TRANSIENT NETWORK FAILURE, not a
  provider outage and not a model refusal. The Architect probed the same model and config
  immediately afterwards and it answered on the first attempt
  (`google/gemini-3.6-flash` -> `{"ok": "yes"}`). The 119 `finish_reason: stop` records in
  `output/logs/` are S19's successful calls; S20's never got a response to log.
  **The damage was not the failure - it was what the failure destroyed:**
  - `_drafts/form_1040_2025/edges.yaml` and `rules.yaml` are **MISSING**. The run deleted them
    before knowing whether the new pass would produce anything.
  - Completeness went **28/28 (100%) -> 0/28 (0%)**; `expression_and_verbatim_citation` 28 -> 0.
  - `policy_mix_before` and `policy_mix_after` are **byte-identical**; `policy_derived: 0`,
    `policy_defaulted: 0`.
  - **4 focused tests now fail** (Architect-run): `test_documents_api_lists_forms`,
    `test_generated_review_keeps_form_and_instruction_slots_separate`,
    `test_generated_review_renders_resolved_external_sources_and_hides_sentinels`,
    `test_generated_review_renders_structured_math_for_humans`.
  **A momentary network hiccup cost three rounds of output. Fix that first; it will recur.**
  1. **RETRY TRANSIENT NETWORK ERRORS WITH BACKOFF.** A connection error is not a finding about
     a tax form. **Only a real model response - or a persistent failure after retries - may
     become a review gap.** Distinguish transport failures (connection reset, DNS, timeout,
     5xx) from semantic failures (unparseable JSON, schema violation, truncation). Retry the
     first class; the second class stays a gap as it is today. Report retries attempted and
     recovered.
  2. **MAKE DRAFT WRITES ATOMIC.** Write the new draft to a temporary location and swap on
     SUCCESS. **A failed run must leave the previous drafts byte-identical.** Today a failed
     pass deletes `edges.yaml`/`rules.yaml` up front, so a bad network is indistinguishable from
     a form that genuinely has no expressions. Add a test that a mid-run failure leaves the
     prior draft intact.
  3. **RERUN AND CONFIRM RECOVERY.** After 1 and 2, rerun `form_1040_2025`, `schedule_1_2025`,
     and `schedule_a_2025` draft-only. **Expected: the 1040 returns to 17/17 formula
     completeness**, and the S20 failover pass gets its first real attempt. Report the policy
     mix before/after with `derived` and `defaulted` split out, per S20 item 4 - a drop in
     `unsupported` achieved entirely by failover is relabelling, not progress.
  4. **THE FOUR FAILING TESTS MUST PASS.** They fail because they read the destroyed draft. If
     any still fails after the rerun, that is a real defect - report it, do not adjust the test
     to match a degraded draft.
  5. **S20's code work is retained** - the failover classification, `policy_origin`,
     `policy_basis`, `policy_defaulted`/`policy_derived` metadata, the three failover classes,
     and the workbench intake-question explanation all landed and are not in question. S20 is
     unaccepted only because its RUN destroyed state; do not revert its implementation.
  **PROTECTED TEST SET, unchanged hard gate:** `graph/2025/{nodes,edges,rules}/` and
  `graph/2025/field_maps/` byte-identical. No promotion, no hand-authoring, no live graph edit.
  **FORCE-ADD THE REPORT** (`output/` is gitignored). **CITE THE ACTUAL COMMIT HASH.**
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`, module-form
  `validate 2025`, real preflight with `legacy_mined` explicit (expect **394**),
  `check_citation_integrity` STRICT (expect **36**). Short pytest temp root; no `--basetemp`.
  ONE local commit; no push.
  **Config note: `extraction.expression_mode` stays `none`.**
  **Stop conditions:** any diff in `graph/2025/{nodes,edges,rules}/` or `graph/2025/field_maps/`;
  any draft promoted; a transient transport error still being written as a review gap; a failed
  run leaving the previous drafts damaged; adjusting a test to match a degraded draft;
  `legacy_mined` above 394; strict mismatches above 36. **Committing with known failing tests is
  NOT acceptable this round** - S20 did so on the reasoning that the failures depended on the
  degraded draft.

- **M20-S20 TASK (IMPLEMENTATION RETAINED; RUN FAILED - see S21) - FILER-PROVIDED AS A FAILOVER, NOT A DEFAULT (Architect, Claude Opus 5,
  2026-07-31). John's ruling.** Ledger: the RAN/NOT RUN rule, D9, D6, and the invariant "every
  control needs exactly one policy".
  **JOHN'S RULING, verbatim:** "filer provided should be a failover rather than a default." And
  earlier: "If I read 'Net proceeds' or 'Interest', my feeling is that this is just something to
  be provided by the filer. If the AI can't find it in the docs provided by the filer, it should
  ask."
  **ARCHITECT MEASUREMENT that supports it - all 119 unsupported 1040 controls classified:**
  | class | count | examples |
  |---|---|---|
  | elections / admin / checkboxes | 76 | "Presidential election campaign", "Combat zone", "Filed pursuant to section 301.9100-2" |
  | checkbox / election | 17 | digital assets Yes/No, "Check if your child's dividends are included" |
  | dates / tax-year fields | 13 | "year Jan. 1-Dec. 31, 2025, or other tax year beginning" |
  | identity / admin | 12 | foreign country, foreign province, names |
  | **LOOKS COMPUTED** | **1** | "Line 32 - total other payments and refundable credits" |
  **There is no hidden arithmetic in the gap.** The single computed-looking control is line 32,
  which is ALREADY in the formula set as "Add lines 27a, 28, 29, 30, and 31" - almost certainly
  the description control rather than the amount control. Confirm and report.
  **Why they have no policy today:** `unsupported` means "no authored graph, filer-fact, or
  decision mapping" - a deliberate ratchet that refuses to guess. Correct when hand-authoring was
  the risk, but it makes "we have not decided" and "the filer provides it" indistinguishable, so
  60% of the form sits in limbo.
  1. **FAILOVER, NOT DEFAULT - ORDER MATTERS AND IT IS THE POINT OF THE ROUND.** A control may
     only fall through to filer-provided AFTER the formula path and the source/import path have
     both had their chance and produced nothing. **Never assign it up front.**
  2. **NEVER FAIL OVER A CONTROL WHOSE LABEL STATES A COMPUTATION.** "Add lines...", "total
     of...", "combine...", "multiply...". Those stay NAMED GAPS. **Silently asking a taxpayer to
     add two numbers the graph should compute is exactly the failure the graph exists to
     prevent**, and it would be invisible in every metric we have.
  3. **SPLIT THE FAILOVER THREE WAYS using concepts that already exist** - not one
     undifferentiated bucket:
     - checkboxes and elections (combat zone, digital assets, presidential campaign) ->
       **filer election / decision**, not a value.
     - names, addresses, dates, foreign country -> **filer identity/admin**.
     - amounts with no derivation ("Net proceeds", "Interest") -> **filer-supplied value, asked
       at intake**. Wire this to machinery that already exists - `list_intake_gaps`,
       `get_intake_relevance`, `intake-inventory.yaml`. John's "if the AI can't find it in the
       docs provided by the filer, it should ask" IS the intake layer; do not invent a new one.
  4. **MARK A FAILOVER POLICY AS `defaulted`, DISTINGUISHABLE FROM A DERIVED ONE.** Separate
     columns. **Otherwise the unsupported count collapses to near zero and we have learned
     nothing** - exactly how the completeness metric read 100% while instructions were
     unattached. A failover is an admission we could not derive it, not a derivation.
  5. **FINISH THE BATCHING. S19's 119-call sequential pass exceeded its time cap** and resolved
     only 17. Same shape as S12, where a sequential 15-form run timed out and the per-document
     parallel run succeeded. Batch or parallelise the background calls; report calls attempted,
     succeeded, failed, and wall time.
  6. **RUN THE OTHER TWO FORMS. S19 ran only `--doc form_1040_2025`.** Schedule 1 has **73
     dispositions (45 unsupported)**, Schedule A has **33 (21 unsupported)**, and both report
     `policy_controls: 0`. Project and generate for all three.
  7. **ATTACH CITATIONS TO PROJECTED POLICIES.** S19 reported policy `83/185 (44.9%)` but policy
     **plus form-face citation** only `17/185 (9.2%)`. Most projected policies are inherited from
     the hand-authored field map with no citation, so by the prime directive they are not
     pipeline output yet. Report both columns per form.
  8. **REPORT the policy mix BEFORE and AFTER, per form**, with `derived` and `defaulted` split
     out. **Report honestly if the derived number barely moves** - a big drop in `unsupported`
     achieved entirely by failover is not progress, it is relabelling.
  **PROTECTED TEST SET, unchanged hard gate:** `graph/2025/{nodes,edges,rules}/` byte-identical.
  **Do not edit `graph/2025/field_maps/` either** - S19 correctly left them alone.
  No promotion, no hand-authoring, no live graph edit, nothing into `content_fingerprint`.
  **FORCE-ADD THE REPORT** (`output/` is gitignored). **CITE THE ACTUAL COMMIT HASH** - S10, S14,
  and S18 all cited hashes that do not exist.
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`, module-form
  `validate 2025`, real preflight with `legacy_mined` explicit (expect **394**),
  `check_citation_integrity` STRICT (expect **36**). Short pytest temp root; no `--basetemp`.
  ONE local commit; no push.
  **Config note: `extraction.expression_mode` stays `none`.**
  **Stop conditions:** any diff in `graph/2025/{nodes,edges,rules}/` or `graph/2025/field_maps/`;
  any draft promoted; failing over a control whose label states a computation; assigning
  filer-provided BEFORE the formula and source paths have run; reporting failover and derived
  policies in one undifferentiated number; hand-authoring; `legacy_mined` above 394; strict
  mismatches above 36. **A model or provider failure is NOT a stop condition.**

- **M20-S17 TASK - ATTACH THE INSTRUCTIONS, THEN TIGHTEN THE UX (Architect, Claude Opus 5,
  2026-07-31). DELIBERATELY SCOPED SMALL. John: "i dont want to overload a revision round."
  The two heavy generation items moved to S18.** Ledger: the exact RAN/NOT RUN evidence rule,
  D4, D6, D9, D11.
  0. **ATTACH THE INSTRUCTIONS TO THEIR OWN LINES. HIGHEST VALUE ITEM; DO IT FIRST; NO MODEL
     CALL REQUIRED.** John found 1040 line 1i showing no instructions and asked how this can
     still be missing after umpteen rounds. **The instructions are fully ingested and always
     have been** - Architect-measured 2026-07-31:
     - `.cache/raw/2025/instructions_form_1040_2025.{pdf,txt,html,ocr.json}` all present.
     - **675,580 characters** of instruction text; **5,021 mined instruction spans** for the
       1040 sitting in `_drafts/form_1040_2025/candidate_spans.yaml`.
     - The document is **explicitly organized by line**: **63 `## Line X` sections** covering
       1b, 1c, 1d, 1e, 1f, 1g, 1h, **1i**, 2a, 2b, 3a, 3b, 4c, 5c, 7a, 7b, 10, 12e, 13a, 13b,
       16, 19, 26, 28, 29, 30, 36, 37, and more.
     - Line 1i's text exists verbatim: `## Line 1i` / `### Nontaxable Combat Pay Election` /
       "If you elect to include your nontaxable combat pay in your earned income when figuring
       the EIC, enter the amount on line 1i. See the instructions for line 27a."
     **THE FAILURE IS THE JOIN, NOT THE INGESTION.** Only **11 of 57** 1040 cells carry
     instruction citations. We matched spans by MENTION instead of using the document's own
     structure - which is why line 1z received line 27b's text in S13 and why S14 counted 146
     wrong-owner spans. **S15's "fix" stripped the wrong spans without attaching the right
     ones**, so we went from wrong instructions to none.
     **Do this deterministically: parse the `## Line X` headings, take that section's body, and
     attach it to that line's canonical address.** No model call, no fuzzy matching, no
     mention-based guessing. Report instruction coverage per form before and after (1040 is
     11/57 today).
  1. **FIX THE COMPLETENESS METRIC - IT HID THIS FOR THREE ROUNDS. Architect's error.** The
     metric is "expression + verbatim citation", which a FORM-FACE citation alone satisfies. So
     S14 reported the 1040 **17/17 complete** while instruction coverage was 11/57, and the
     Architect accepted the round on that number. **Count form-face and instruction citations
     as SEPARATE columns** so an unattached instruction corpus can never again read as complete.
  2. **COMPRESS THE CELL LIST TO ONE LINE PER CELL.** John: "I want the listing of cells to be
     more compressed. It can be a single line each." Line anchor, short label, bucket colour +
     name, review state. Nothing else. The list is navigation.
  3. **THE LIST GETS ONE THIRD OF THE VERTICAL SPACE; THE REVIEW PANE GETS TWO THIRDS.** John's
     explicit ratio. The review pane is where the work happens and it must not require scrolling
     to reach the controls.
  4. **TWO BUTTONS, ONE ROW: `Accept` and `Reject`. RETIRE `Pipeline defect` / `Source
     pathology`.** John, overruling his own M15 design after using it: "if i'm some Joe reviewing
     a doc, do i know what the underlying problem is? I can only tell you that the cell
     instruction/description/entry does not match the source docs and i should tell the pipeline
     why to make corrections, no?" **He is right: the reviewer reports the SYMPTOM; the pipeline
     diagnoses the CAUSE.** Asking a reviewer to classify a defect as pipeline-vs-source is
     asking them to do triage they have no basis for.
     - On `Reject`, the comment box is auto-focused with a clear prompt.
     - John said "strongly encouraged", not required. **Implement it as: submitting an empty
       rejection triggers a confirm step** ("Reject without telling the pipeline why?") rather
       than a hard block. That honours his wording while preserving the rework value - a
       rejection with no comment gives the pipeline nothing to act on. If he still finds it
       heavy after testing, relax it further.
  5. **DROP THE TYPED `Reviewer ID` FROM THE UI.** John: "it isn't as though people will have a
     group of reviewers sitting down and doing this as a team. this just takes up space. I'd
     record the timestamp and maybe something about the computer."
     - Auto-capture instead: timestamp (already recorded) plus machine identity (host / OS user
       / session id). No typing.
     - Keep an OPTIONAL free-text tag for when John wants to mark a batch.
     - `reviewer_id` is currently REQUIRED and validated in `workbench/address_verdicts.py`.
       Change it to auto-populated rather than removing attribution outright - the ledger is a
       record of human judgement and must still say where a verdict came from.
     - **Note the old guard is dead either way:** rejecting `agent`/`codex`/`worker`/`system` was
       always bypassable by any human-looking string (S15 wrote one as `john`). Machine capture
       plus a submission-channel field is a better guard than a blocklist.
  6. **THE MISSING FLOOR.** `line 22` renders `line 18 - line 21` but its instruction says "If
     zero or less, enter -0-". It should be `max(line 18 - line 21, 0)`. Confirm the phrasing
     table covers this class and report how many cells changed.
  **VERIFY IN THE BROWSER and expect John to test it immediately after.** Screenshot the new
  layout at the 1/3-2/3 split with the single-line list.
  **DO NOT write a verdict under a real person's name or into the live ledger.** S16 did this
  correctly with a synthetic reviewer and an isolated store - keep that discipline.
  **What this round does NOT do.** No draft promotion. No hand-authoring. No live graph edit. No
  operation-enum change. No rollover implementation. Verdict-contract changes are additive only
  and **nothing may enter `content_fingerprint`**.
  **PROTECTED TEST SET, unchanged hard gate:** `graph/2025/{nodes,edges,rules}/` byte-identical.
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`, module-form
  `validate 2025`, real preflight with `legacy_mined` explicit (expect **394**),
  `check_citation_integrity` STRICT (expect **36**). Short pytest temp root; no `--basetemp`.
  ONE local commit; no push. Cite the ACTUAL commit hash.
  **Config note: `extraction.expression_mode` stays `none`.**
  **Stop conditions:** any diff in `graph/2025/{nodes,edges,rules}/`; any draft promoted; a
  verdict written under a real person's name or into the live ledger; anything entering
  `content_fingerprint`; hand-authoring; asking the model for internal node ids; `legacy_mined`
  above 394; strict mismatches above 36. **A model or provider failure is NOT a stop condition.**

- **[DONE `e1e8c80`] M20-S18 TASK - INSTRUCTIONS ARE OPTIONAL; FIX LINE RESOLUTION; RUN THE SOURCE EXTRACTION
  (Architect, Claude Opus 5, 2026-07-31). Items 1-2 are small and FULLY DIAGNOSED below - do
  them first, they are mechanical. Item 3 is the heavy one. The background controls moved to
  S19 so this round is not overloaded.** Ledger: the exact RAN/NOT RUN evidence rule, D9.
  1. **INSTRUCTIONS AUGMENT, THEY NEVER GATE - John's ruling, 2026-07-31.** His words: "even
     the form will often not have instructions per se, but just a label that says 'qualified
     income' or some such terse thing. That's ok. If there are augmenting instructions, include
     them, but they are by no means mandatory."
     **The Architect got this metric wrong twice.** S14's version was too lenient - "expression +
     verbatim citation" was satisfied by a FORM-FACE citation alone, so the 1040 read 17/17
     complete while instruction coverage was 11/57. S17's fix over-corrected to
     `expression_and_both_citations`, which permanently caps forms whose instructions do not
     discuss computed lines. **Correct definition:**
     - **PRIMARY metric: expression + form-face citation.** Mandatory.
     - **Instruction citation: reported as its own column, informational, NEVER a gate.**
     - Keep the split columns S17 added - they are right and they are what exposed the problem.
     **PROOF this is not a bug, Architect-measured on Schedule A:** instruction sections exist
     for lines `1, 5, 5a, 5b, 5c, 5e, 6, 8, 8c, 8d, 9, 11, 12, 13`; the computed lines are
     `3, 4, 5d, 7, 8e, 10, 14`; **the intersection is EMPTY.** The IRS explains the INPUT lines
     (what you may deduct) and leaves the arithmetic to the form face. Schedule A's 3/7 is the
     document telling us those lines have nothing more to say. Chasing that number would
     eventually tempt someone to fabricate a citation.
  2. **FIX PARENT / LETTERED-CHILD LINE RESOLUTION. Fully diagnosed; one fix closes several
     failures.** Schedule 1 regressed to 2 cells with neither expression nor citation:
     - `line 10` combines "lines 1 through 7 and 9" -> the outline has **`2a` but no `2`**.
     - `line 26` adds "lines 11 through 23 and 25" -> the outline has **`19a` but no `19`**.
     A single missing anchor kills the whole expression. This is the same class as S14's `8n`
     and `24f` gaps and the Schedule A line 14 namespace mismatch (`11` resolving to
     `section_1_...` instead of `root_line_11b`).
     **Rule:** when a referenced printed line has no exact anchor, resolve to its lettered
     children if the parent is a pure heading, or to the parent if the children are sub-parts.
     Report which cells this closes. **Keep failing closed** - never fabricate a line.
  3. **RUN THE SOURCE EXTRACTION FOR NON-COMPUTED LINES - S16 SCAFFOLDED IT, NEVER RAN IT.**
     40 of the 1040's 57 cells are `review_gap` carrying
     `text: "line 1a = unresolved source"` and
     `reason: "non-computed source extraction has not been generated"`. The schema and the
     surface exist; the second micro question was never executed. Line 1a already holds the
     citation "Total amount from Form(s) W-2, box 1" and must render `= W-2 box 1`; line 1e must
     render `= Form 2441, line 26`. Resolve identity in CODE, fail closed with a named gap.
     **The colour key is meaningless until this lands** - today 40 of 57 render as gap.
  **PROTECTED TEST SET, unchanged hard gate.** No promotion, no hand-authoring, no live graph
  edit, nothing into `content_fingerprint`. Same Tier 3 gates as S17. ONE local commit; no push.

- **M20-S19 TASK - BRING BACK THE BACKGROUND CONTROLS, AND CLOSE THE 60% GAP (Architect,
  Claude Opus 5, 2026-07-31). Its own round on purpose: it roughly quadruples the review
  denominator, and the last time a big item shared a round it got scaffolded instead of built.**
  Ledger: the RAN/NOT RUN rule, D9, and guiding invariant "every control needs exactly one
  policy".
  **John's ask:** "things like are you in a combat zone? dependents, did they live with you for
  half the year? it is all just dead in the 1040. These are important details, even if they are
  just entries by the filer. the AI needs this to create a valid return."
  **ARCHITECT MEASUREMENT, 2026-07-31 - this is John's OLDEST open complaint.**
  `graph/2025/field_maps/form_1040_2025.yaml` carries **199 `field_dispositions`**:
  | population_policy | count |
  |---|---|
  | **unsupported** | **119 (60%)** |
  | user_entered | 42 |
  | decision_required | 24 |
  | computed | 7 |
  | copied | 7 |
  The generated review surface currently shows **57**. The 119 unsupported controls each say
  "has no authored graph, filer-fact, or decision mapping" - **that is the 60%-unaddressed-1040
  complaint, still live.**
  1. **PHASE 1 - PROJECT WHAT IS ALREADY CLASSIFIED. Deterministic, NO model calls, do this
     first.** ~80 controls already carry a policy: 42 `user_entered`, 24 `decision_required`,
     and the 14 `computed`/`copied` the formula path covers. Carry each control's existing
     `label`, `population_policy`, `value_format`, `address_id`, and citation into the generated
     review surface. Render `= entered by filer`, `= decision required`, etc. **Do not call a
     model for a control whose policy is already authored.**
  2. **PHASE 2 - GENERATE FOR THE 119 UNSUPPORTED.** These are the real gap and the reason the
     round exists. Same discipline as every other micro call: the control's label plus its
     instruction text in, structure out, **identity resolved in CODE**, fail closed with a named
     gap rather than inventing semantics. A dependent's "lived with you" box is a boolean that
     drives credit eligibility - the review question is "is this control correctly identified
     and correctly typed?"
  3. **REPORT the policy mix BEFORE and AFTER**, per form, and the new denominator (expect ~199
     for the 1040, not 57). **A control moving from `unsupported` to a reasoned policy is the
     unit of progress for this round.** Report honestly if the number barely moves.
  4. **The completeness metric stays as S18 left it** - expression plus form-face citation is
     the gate; instruction citation is informational and never mandatory (John, 2026-07-31).
     Non-computed controls need a POLICY and a citation, not an expression; extend the metric
     rather than forcing them through the formula denominator.
  **PROTECTED TEST SET, unchanged hard gate:** `graph/2025/{nodes,edges,rules}/` byte-identical.
  No promotion, no hand-authoring, no live graph edit, nothing into `content_fingerprint`.
  **FORCE-ADD THE REPORT** - `output/` is gitignored, and S18's report was left untracked until
  the Architect force-added it. `git add -f output/<report>.yaml`.
  **CITE THE ACTUAL COMMIT HASH in your notes** - S10, S14, and S18 all cited hashes that do not
  exist in the repository.
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`, module-form
  `validate 2025`, real preflight with `legacy_mined` explicit (expect **394**),
  `check_citation_integrity` STRICT (expect **36**). Short pytest temp root; no `--basetemp`.
  ONE local commit; no push.
  **Config note: `extraction.expression_mode` stays `none`.**
  **Stop conditions:** any diff in `graph/2025/{nodes,edges,rules}/`; any draft promoted;
  hand-authoring a policy; calling a model for a control that already has an authored policy;
  fabricating semantics for a control instead of failing closed; `legacy_mined` above 394;
  strict mismatches above 36. **A model or provider failure is NOT a stop condition.**

- **M20-S16 TASK (COMPLETE, accepted at `302c85e`) - MAKE THE REVIEW SURFACE FIT A HUMAN (Architect, Claude Opus 5, 2026-07-31).
  John's feedback from his first real session with the workbench, in one batch. His framing:
  "The only way to get this done is by trial and error." Expect to hand this back to him to
  test.** Ledger: the exact RAN/NOT RUN evidence rule, D4, D6, D9, D11.
  **JOHN'S CORE COMPLAINT, and it is the organizing idea:** "Remember this is a human reviewing,
  not a computer." He was shown `Operation: sum`, a mangled description, and
  `Operands: form_1040_2025_root_line_19 addend`. He wants `19 + 20`. Everything below follows
  from that.
  **DO THE CORRECTNESS FIXES FIRST (items 1-2) - they are small and they are wrong today.**
  1. **FIX THE ROLE BUG - THE GRAPH CANNOT CURRENTLY EXPRESS `18 - 21` VS `21 - 18`.**
     `tax_graph/extract/assembly.py:190` hardcodes `inputs.append({"name": source_id, "role":
     "addend"})` for EVERY operand regardless of operation. At line 127
     `input_item.get("role")` then finds `"addend"` (truthy) so `_default_role()` - which
     handles SUBTRACT correctly - is never reached. Verified in the live draft: both operands of
     `line_22` (rule `..._line_22_subtract`) are stored `role: addend`.
     - Remove the hardcode; derive role from operation and position.
     - **State the ordering convention in the prompt**: for `SUBTRACT` and `DIVIDE`,
       `source_lines` must be in computation order, the value being reduced FIRST. Nothing says
       this today, so correctness depends on the model happening to match our assumption.
     - **Validate arity per operation** - `SUBTRACT`/`DIVIDE` take exactly two; anything else is
       a FINDING, not data. Validate the role set against the operation too.
  2. **STOP SHOWING RAW OUTLINE LABELS TO A HUMAN.** `assembly.py:99` builds
     `f"Compute {output_name} for {outline_node.label}."` and the label carries OCR bleed from
     neighbouring form text. John saw: *"Compute line_22 for 12a, 12b, 12c, 22 Subtract line 21
     from line 18. If zero or less, enter -0- 22."* - he asked what 12a/12b/12c were and why 22
     appears twice. Clean the label (strip the answer-box line number and adjacent-cell bleed)
     or stop surfacing this string entirely in favour of item 3.
  3. **THE RENDERING STANDARD - ONE FORM, READABLE BY A HUMAN AND BY THE AI.** John: "A LLM
     should understand human math." Render DETERMINISTICALLY IN CODE from the structured
     expression. **The model never emits this string** - it emits structure, code renders it, so
     it cannot be gotten wrong and costs zero prompt tokens.
     ```
     line 21  = line 19 + line 20
     line 22  = max(line 18 - line 21, 0)
     line 11a = line 9 - line 10
     line 1a  = W-2 box 1
     line 1e  = Form 2441, line 26
     line 1h  = entered by filer
     line 5   = min(Form 8863 line 25, Form 8863 line 27)
     ```
     Standard math where it is math; plain English where it is provenance. **No `addend`, no
     `Operands:` list, no node ids in the reviewer's face.** ASCII only (`-`, not a minus sign) -
     `tools/check_ascii.py` is a gate. **Use the SAME rendered string in the prompt and in the
     UI**, so John compares exactly what the model was asked about.
  4. **EXTEND REVIEW TO THE NON-COMPUTED LINES. This is the biggest item and John calls it
     critical:** "I need to see that their graph reference/operand is to fetch from another form
     or specific cell or to be provided by the filer... This is critical to making this tax
     graph actually work in practice." The 1040 has 57 lines; only 17 compute. The other 40 are
     imports, cross-form carries, and filer entries - and **none of them are generated or
     reviewable today**, so a mis-wired fetch is invisible.
     Add a second micro question for non-formula lines, same shape and discipline as the formula
     one - label plus instructions in, structure out, identity resolved in code:
     ```
     {"source_kind": "form_line" | "information_return" | "filer_entry",
      "form": "...", "line": "...", "box": "...", "quote": "..."}
     ```
     Render as `= Form 2441, line 26` / `= W-2 box 1` / `= entered by filer`. Resolve to
     canonical addresses in CODE, never ask the model for ids, and fail closed with a named gap
     rather than guessing.
  5. **MOVE THE CONTROLS TO WHERE THE EYE IS.** John: "I hate that the comment section and
     approval is up above... look at the bottom pane of supporting info. you have to scroll to
     see it."
     - **The cell list becomes NAVIGATION ONLY** - line number, label, bucket colour and name,
       review state. **Remove the approve checkbox and the note box from the list entirely.**
     - **The review area holds the decision**: the rendered operation (item 3), the form-face
       text, the instruction-page text, and the accept/reject controls and comment - together,
       **visible without scrolling**.
  6. **REJECTION MUST CARRY A REASON. John asked: "is non approval a comment?"** Yes.
     - Approve is ONE action, no explanation required.
     - **Reject REQUIRES a reason code plus a comment** - reuse John's own labels, `Pipeline
       defect` vs `Source pathology`, which are rework routing, not a generic reject. A rejection
       with no reason gives the pipeline nothing to rework from.
     - **Enforce this in the API, not only the UI.**
     - John floated a slider; the Architect recommends explicit approve/reject actions instead,
       because reject must open the reason and a slider implies a spectrum. If John prefers the
       slider after seeing it, change it.
  7. **COLOUR BY RISK BUCKET.** John: "Put all of the math ones in Red... That way one can speed
     the reviews of the critical ones and find the most likely failure points." Map onto the
     EXISTING tested classification `expression_kind_bucket` (S6-1) - do not invent a second
     taxonomy, and do not recompute bucket membership in JavaScript.
     | bucket | colour |
     |---|---|
     | ARITHMETIC | **red** |
     | COPY | amber |
     | IMPORTED (W-2/1099 box) | blue |
     | CROSS-FORM FETCH | indigo |
     | USER_ENTRY | grey |
     | gap / not reviewable | hatched outline |
     - **RED IS CURRENTLY TAKEN:** `--danger: #a03225` renders "Coverage gap - nobody has mapped
       this yet" and `.official-region.policy-unsupported`. **Move the gap indicator to amber-brown
       and give red to ARITHMETIC**, per John. Note the existing CSS comment at
       `styles.css:112` warning that red must not be confused with a policy state - update it.
     - **Pair every colour with a text label.** Colour alone is not readable for everyone.
     - Note for expectations: on today's formula-only surface 14 of the 1040's 17 cells are
       ARITHMETIC (sum 9, subtract 5, copy 2, require_input 1), so nearly everything is red. The
       key only earns its keep once item 4 lands and the surface holds all 57 lines.
  8. **FIX THE STALE POLICY DISPLAY.** Document cards show `computed: 5 | copied: 1 | coverage
     gap - nobody has mapped this yet: 11` for the 1040, but every generated cell has
     `policy = None` and those counts come from the old live-projection classifier. All 17 cells
     are real and cited. Either compute the mix from the generated set or omit it in
     `generated_draft` mode.
  9. **RE-MEASURE - S15 DID NOT.** Re-run `verify form-completeness`. The report still claims
     Schedule 1 is 0/4 while the workbench shows 4 cells with 4 citations, and still reports 146
     wrong-owner instruction spans from before the S15 fix. Report the current numbers,
     including the wrong-owner count and the new non-computed-line coverage from item 4.
  **VERIFY IN THE BROWSER, and expect John to test it himself afterwards.** Load the page, walk
  a 1040 cell, approve one, reject one with a reason and comment, confirm both land in
  `review_verdicts/2025/address_verdicts.jsonl`, and include a screenshot.
  **DO NOT WRITE A VERDICT AS `john` OR ANY REAL PERSON.** S15 recorded a durable approval under
  John's name for a cell he had never seen, which `docs/review-workbench.md` forbids
  ("No workbench action asserts a human-review claim on the user's behalf"). That was the
  Architect's spec error, not the Worker's. **Use an obviously synthetic reviewer id for
  demonstration, and do not commit demonstration verdicts to the real ledger.**
  **What this round does NOT do.** No draft promotion. No hand-authoring. No live graph edit. No
  operation-enum change. No rollover implementation. The review/verdict contract may change ONLY
  additively for the reject-reason field, and **nothing may enter `content_fingerprint`** -
  comments and reason codes are metadata about the review, not the content approved.
  **PROTECTED TEST SET, unchanged hard gate:** `graph/2025/{nodes,edges,rules}/` byte-identical.
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`, module-form
  `validate 2025`, real preflight with `legacy_mined` explicit (expect **394**),
  `check_citation_integrity` STRICT (expect **36**). Short pytest temp root; no `--basetemp`.
  ONE local commit; no push. Cite the ACTUAL commit hash.
  **Config note: `extraction.expression_mode` stays `none`.** The S9 instruction to set it to
  `generator` is OBSOLETE.
  **Stop conditions:** any diff in `graph/2025/{nodes,edges,rules}/`; any draft promoted; a
  demonstration verdict written under a real person's name or committed to the real ledger; a
  comment or reason code entering `content_fingerprint`; hand-authoring an expression or
  citation; asking the model for internal node ids; `legacy_mined` above 394; strict mismatches
  above 36. **A model or provider failure is NOT a stop condition** - `google/gemini-3.6-flash`
  is known good.

- **M20-S15 TASK (COMPLETE, accepted at `3a8d613`) - FIX THE TWO BLOCKERS, THEN PUT THE GENERATED CELLS IN FRONT OF JOHN
  (Architect, Claude Opus 5, 2026-07-30). John's go. THE REVIEW SURFACE IS THE POINT OF THIS
  ROUND - the two fixes exist to make the reviewed set complete.** Ledger: the exact
  RAN/NOT RUN evidence rule, D4, D6, D9, D11.
  **PRIME DIRECTIVE FRAMING (`AGENTS.md` section 1):** human review is how the last ~2% gets
  directed, and it has NEVER RUN - `review_verdicts/2025/address_verdicts.jsonl` still has zero
  records. Not because review is unimportant, but because the contract kept changing (see
  John, 2026-07-30). It is stable now and there are finally generated cells worth reviewing.
  1. **FIX 1 - THE OUTLINE INDEX IS MISSING LETTERED SUB-LINES. This is all four Schedule 1
     gaps.** Every gap reports `source line is not present in the deterministic outline index`:
     line 9 ("Add lines 8a through 8z") references `8n`; line 26 references `24f`; others
     reference `2` and `19`. The MODEL read those lines correctly and the resolver could not map
     them, so it failed closed with a named gap - correct behavior, wrong index. Index the
     lettered sub-lines and re-measure. **Target: Schedule 1 goes from 0/4 to complete**, or
     produces a DIFFERENT and reasoned gap. Keep failing closed; never fabricate a line.
  2. **FIX 2 - INSTRUCTION SPANS ARE JOINED BY MENTION, NOT OWNERSHIP. 146 wrong-owner spans**
     across the three forms - 89 on the 1040 alone, touching 15 addresses including 1z, 9, 11a,
     14, 15. Line 1z was sent the **line 27b** instructions because they mention 1z. The forms
     still reached 100% because the form face carried the structure, **but these are the
     citations John will READ during review** - a cell can be structurally right and cite the
     wrong paragraph. Fix the join so a line gets ITS OWN instruction entry; report the
     wrong-owner count after (expect a large drop from 146).
  3. **THE REVIEW SURFACE.** Scope it to the ~28 formula cells across `form_1040_2025`,
     `schedule_1_2025`, and `schedule_a_2025`. **Not 2,120 cells** - a set John can finish in
     one sitting is the whole point.
     a. **SHOW THE GENERATED CELLS, AND MARK THEM AS GENERATED.** The workbench currently
        surfaces the hand-authored live graph, which carries ZERO provenance. Reviewing that
        would have John approving scaffolding, which the prime directive forbids. Every cell in
        this surface must show it is pipeline-generated, with resolved model and provider.
     b. **JOHN'S LAYOUT RULING (from the parked S6-2, still binding):** the review panel holds
        **the expression, the two instruction sources, the verdict controls, AND the comment box
        TOGETHER.** Today the controls sit in the LEFT rail (`workbench/static/index.html:45`)
        while content is in the right-hand river - a reviewer reads right and reaches far left
        to approve. Move them together. Amplifying detail stays in a separate panel below.
        Keep the 15/40/45 proportions.
     c. **SHOW THE TWO INSTRUCTION SOURCES SEPARATELY** - form face and instruction page, the
        same two slots as `form_citations` / `instruction_citations`, never concatenated. The
        reviewer must see exactly what the model saw.
     d. **WIRE THE FOUR BUTTONS THAT ALREADY EXIST.** `index.html:48-51` has Confirm /
        Pipeline defect / Source pathology / Save and next, `disabled` since M15 Gate A and
        never functional in either location. `POST /api/verdicts` is already built and tested.
        Wire them. **Keep John's labels** - "Pipeline defect" vs "Source pathology" is his
        rework routing, not a generic reject.
     e. **ADD THE COMMENT FIELD - it does not exist anywhere today**, not in the UI, not in
        `workbench/address_verdicts.py`, not in `schemas/review_address_verdict.schema.json`.
        This is what lets John say "this fails because the instruction says X and this does Y".
  4. **THE REVIEW CONTRACT IS UNFROZEN ONLY FOR THE ADDITIVE COMMENT FIELD.** Everything else
     stays exactly as verified on 2026-07-30. **CRITICAL: the comment MUST NOT enter
     `content_fingerprint`.** The comment is metadata ABOUT the review, not part of the content
     being approved; folding it in would invalidate approvals whenever a note is edited. Add it
     to the schema and the append path as an optional field, and prove with a test that a
     verdict's fingerprint is identical with and without a comment.
  5. **VERIFY IN THE BROWSER, NOT ONLY IN TESTS.** This is UI work and John has to look at it.
     Load the page, click through a cell, record a verdict with a comment, confirm it lands in
     `review_verdicts/2025/address_verdicts.jsonl`, and include a screenshot. **A round that
     passes tests but cannot record one real verdict end to end has failed.**
  6. **What this round does NOT do.** No draft PROMOTION - review-as-promotion is the next
     milestone; here the verdict is recorded, not applied to the live graph. No hand-authoring.
     No live graph edit. No operation-enum change. No rollover implementation. No prompt tuning
     for quality beyond fix 2.
  **PROTECTED TEST SET, unchanged hard gate:** `graph/2025/{nodes,edges,rules}/` byte-identical
  at round end.
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`, module-form
  `validate 2025`, real preflight with `legacy_mined` explicit (expect **394**),
  `check_citation_integrity` STRICT (expect **36**). Short pytest temp root; no `--basetemp`.
  ONE local commit; no push. Cite the ACTUAL commit hash.
  **Config note: `extraction.expression_mode` stays `none`** - it disables the whole-document
  generator; the per-cell micro path is not gated by it. The S9 instruction to set it to
  `generator` is OBSOLETE.
  **Stop conditions:** any diff in `graph/2025/{nodes,edges,rules}/`; any draft promoted; the
  comment entering `content_fingerprint`; hand-authoring any expression or citation; fabricating
  a line to close a gap; `legacy_mined` above 394; strict mismatches above 36. **A model or
  provider failure is NOT a stop condition** - `google/gemini-3.6-flash` is known good.

- **M20-S14 TASK (COMPLETE, accepted at `eb99447`; 1040 17/17, Schedule A 7/7) - RETIRE THE HANDCRAFTED SET AS A SCORE; COMPLETE 3 FORMS FOR REVIEW
  (Architect, Claude Opus 5, 2026-07-30). John's call.** Ledger: the exact RAN/NOT RUN evidence
  rule, and D9.
  **WHY THE YARDSTICK IS BEING RETIRED - the S13 evidence.** Of seven paired cells, most
  "failures" were not the model's:
  - **Line 9: the MODEL IS RIGHT AND THE HANDCRAFTED SET IS WRONG.** The form says "Add lines
    1z, 2b, 3b, 4b, 5b, 6b, 7a, and 8". The model returned all of them; the live graph OMITS 4b,
    5b, and 6b. Scored as a miss; it was the model catching a defect in the test set.
  - **Line 15: a modeling CONVENTION, not an error.** The model returned `SUBTRACT(11b, 14)`,
    which is what the form says. The handcrafted set encodes `MAX(line_15_pre_floor,
    zero_floor)` using synthetic intermediate nodes the model cannot know exist.
  - **Schedule A line 14: same lines, different node ids** - a namespace/granularity mismatch in
    OUR resolution (`section_1_...` vs `root_line_11b`, and 11 vs 11a/11b).
  - **Line 11a: operand refs IDENTICAL**, still scored as differing. **Check whether the ROLES
    came back reversed** - `10 - 9` instead of `9 - 10` is a real correctness bug that the
    ref-set comparison hides. Fix this regardless of the yardstick decision.
  **DEMOTE, DO NOT DELETE (Architect ruling).** Stop scoring against it and stop reporting
  coverage/accuracy against it as THE metric. **Keep the file and keep computing the diff** as a
  "these two disagree, look here first" signal - it is the only independent check we have, it
  costs nothing, and it is exactly the review-prioritization idea. It is a FLAG, not a grade.
  **CONFIG STATE - READ BEFORE CHANGING ANYTHING (verified by the Architect, 2026-07-30).** The
  gitignored live config is already correct for this round. Do NOT "fix" it back to an earlier
  spec's settings:
  - `llm.model: google/gemini-3.6-flash` - concrete pin, known good (74/74 cells in S12).
  - `extraction.expression_mode: none` - **THIS IS CORRECT AND MUST STAY `none`.** It disables
    the WHOLE-DOCUMENT generator, which was the wrong-shaped call that burned S7-S11. The
    per-cell micro path is NOT gated by this setting and runs regardless: S12 produced 74 micro
    calls with `expression_mode: none`. **An earlier spec (S9) told a Worker to set this to
    `generator`. That instruction is OBSOLETE - setting it back reintroduces the defect.**
  - `micro_max_tokens: 4000` - bounded, and a canary. If a per-cell call needs more, the scoping
    is wrong again: STOP AND REPORT rather than raising it.
  - `provider_routing` all null with `allow_fallbacks: true` - deliberate. Do NOT hard-pin a
    provider; that produced S10's 502 and no-route dead ends. Attribution comes from the
    recorded `resolved_provider`, not from constraining the route.
  - `strict_schema: true`, `require_parameters: true` - keep both; loosening either to force a
    route is a stop condition.
  1. **STEP 1 - NEW METRIC: COMPLETENESS AGAINST THE FORM ITSELF.** No ground truth required.
     Per form, report: **formula-bearing cells that have (a) an expression and (b) a verbatim
     cited span, over the total formula-bearing cells on that form.** Also report cells with an
     expression but NO citation, and cells with neither, as separate buckets - the denominator
     is the form, not a partial hand-built slice.
  2. **STEP 2 - COMPLETE THREE FORMS. Target: `form_1040_2025`, `schedule_1_2025`,
     `schedule_a_2025`** (57, 52, and 27 line nodes respectively - real but bounded; John may
     substitute, in which case use his choice). "Complete" means every formula-bearing line on
     those forms has an expression with a verbatim citation, or an explicit, reasoned
     `review_gap` saying why not. **A reasoned gap is an acceptable outcome; a silent miss is
     not.**
  3. **STEP 3 - FIX THE INSTRUCTION-SPAN OWNERSHIP BUG. This is likely the biggest blocker.**
     The instruction text sent for line 1z was actually the **line 27b** instructions ("Check the
     box on line 27b if you are (1) a minister...") plus EIC earned-income prose, joined to 1z
     merely because they MENTION line 1z. **Spans are being matched by MENTION, not by
     OWNERSHIP.** 1z survived because its form face carried the answer; lines whose form face is
     terse are being fed instructions about a different line entirely. Fix the join so a line
     gets ITS OWN instruction entry, and report how many addresses had wrong-owner spans.
  4. **STEP 4 - FIX IDENTITY RESOLUTION FOR LINE REFS.** Schedule A showed the same printed line
     resolving into a different namespace than the live node. Resolve printed line numbers to the
     canonical address for that form consistently, and handle the 11 vs 11a/11b granularity case
     (a bare parent reference where only lettered children exist). Report unresolved line refs as
     findings rather than dropping or fabricating them.
  5. **STEP 5 - REPORT, per form:** completeness numerator/denominator, cells with expression but
     no citation, reasoned review gaps, unresolved line refs, wrong-owner instruction spans
     fixed, plus resolved model, provider, tokens, and cost. Keep the handcrafted DIFF in the
     report as a flag section, clearly labelled as NOT a score.
  6. **What this round does NOT do.** No review UI - pointing the workbench at generated cells is
     the NEXT round, and it is what these three forms are being completed FOR. No draft
     promotion. No hand-authoring. No live graph edit. No operation-enum change. No rollover
     implementation. Review/verdict contract still FROZEN.
  **PROTECTED TEST SET, still a hard gate even though it is demoted:**
  `graph/2025/{nodes,edges,rules}/` byte-identical at round end. It stops being a SCORE; it does
  not become editable.
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`, module-form
  `validate 2025`, real preflight with `legacy_mined` explicit (expect **394**),
  `check_citation_integrity` STRICT (expect **36**). Short pytest temp root; no `--basetemp`.
  ONE local commit; no push. Cite the ACTUAL commit hash.
  **Stop conditions:** any diff in `graph/2025/{nodes,edges,rules}/`; any draft promoted; any
  hand-authored expression or citation; fabricating a node for an unresolved line ref;
  `legacy_mined` above 394; strict mismatches above 36. **A model or provider failure is NOT a
  stop condition** - fall back to a pinned concrete alternative;
  `google/gemini-3.6-flash` is known good.

- **M20-S13 TASK (COMPLETE, accepted at `a3214fc`) - ASK THE QUESTION A HUMAN WOULD ANSWER (Architect, Claude Opus 5,
  2026-07-30). John's design ruling. THE MODEL DOES READING COMPREHENSION; CODE DOES IDENTITY.**
  Ledger: the exact RAN/NOT RUN evidence rule, and D9.
  **JOHN'S TWO OBSERVATIONS, AND THEY ARE THE SAME MISTAKE.** (a) We send WAY too much: 59
  `addressable_operand_candidates` for a line whose instruction literally reads "Add lines 1a
  through 1h". A human is shown a label and the instructions and needs nothing else. (b)
  "Operand" is the wrong word to elicit good judgment - `operand`, `inputs[].name`,
  `operation_plan`, `addressable_operand_candidates` is COMPILER vocabulary; the IRS says
  "add lines 1a through 1h". **Asking for operands forces the model to do IDENTITY RESOLUTION,
  which it is bad at and code is exact at.** That is the source of both the self-reference bug
  and the 159-of-336 unresolved endpoints.
  **THE EVIDENCE THAT THE MODEL IS NOT THE PROBLEM.** For line 1z the model returned EIGHT
  inputs for "Add lines 1a through 1h" - the correct count. Six of the eleven paired cells had
  exactly the right arity. It read the instruction. Then `assembly.py:87-91` resolved every
  name against `node_ids_by_name`, which only ever holds names local to the cell being
  processed, missed on all of them, and fabricated ids under the TARGET's outline id. **The
  collapse to self-reference is deterministic in our code and no model output could avoid it.**
  1. **STEP 1 - REPLACE THE MICRO PROMPT WITH THE HUMAN QUESTION.** Send the cell's label, the
     instruction text for that line (form face AND instruction page), and nothing else. **DELETE
     `addressable_operand_candidates` from the prompt.** Also delete the Form 8949 column-name
     instructions from the generic path - three of the six current instruction lines are
     8949-specific and are noise on a 1040 sum line. Keep 8949's special handling on an
     8949-specific path if it is still needed; report if it is.
     **THE TWO INSTRUCTION SOURCES ARE NAMED SECTIONS, NOT A FLAT LIST (John, 2026-07-30).**
     They play different roles: the FORM FACE is terse and authoritative on STRUCTURE ("Add
     lines 1a through 1h"); the INSTRUCTION PAGE is verbose and authoritative on TREATMENT (what
     counts, exclusions, edge cases). Merged into one anonymous list, neither the model nor the
     reviewer can tell which is which. Shape:
     ```
     Line 1z on Form 1040 (2025).

     On the form:
       "z  Add lines 1a through 1h"

     From the instructions for line 1z:
       [i1] "<paragraph>"
       [i2] "<paragraph>"
     ```
     Named sections at top level; a LIST only WITHIN a section when there are several spans,
     each carrying its span id.
     **These are the SAME TWO SLOTS S6-1 already split** (`form_citations` vs
     `instruction_citations` in `review_content` and the fingerprint). Use the same split end to
     end, so what we send the model and what the review panel shows the human are the same
     shape - the reviewer then sees exactly what the model saw.
     **Volume discipline - this is the round about sending LESS.** Use the spans already mined
     and joined to that address, NOT the whole instruction-booklet section. If a line's
     instruction text is genuinely large, REPORT it rather than silently truncating mid-sentence.
  2. **STEP 2 - ASK FOR LINE NUMBERS, NOT IDS - the form's own vocabulary.** Target output shape:
     `{"operation": <closed enum>, "source_lines": ["1a","1b",...], "quote": "<the instruction
     sentence relied on>"}`. Cross-form references stay natural: `{"form": "schedule_1", "line":
     "26"}`. **Constrain what you can in the schema** - `operation` is already a closed enum;
     keep it. Do NOT reintroduce a 59-item enum of node ids: the point is to stop asking for
     identity at all.
     **`quote` is required, not decorative.** It grounds the answer in cited instruction text and
     it is what the review workbench needs so a human can say "the instruction says X and this
     does Y" - John's original ask from 2026-07-30.
     **RETURN THE SPAN ID ALONGSIDE THE QUOTE.** `quote` alone can drift or paraphrase and is
     then unverifiable prose. The span id lets us check the quote is VERBATIM against a real
     mined span, which is what `check_citation_integrity` already enforces (the M14
     fabricated-citations reopen is the precedent). Keep the existing `citation_span_ids`
     mechanism for this; do not replace it with free text.
  3. **STEP 3 - RESOLVE IDENTITY DETERMINISTICALLY IN CODE.** Map `1a` ->
     `form_1040_2025_root_line_1a` from the outline's own line index, which already exists.
     **Fix `assembly.py` so an unresolved operand is recorded as a FINDING and never fabricates
     a node under the target's namespace.** That fabrication is also the likely source of
     `extra_in_draft=66`; report whether it drops.
  4. **STEP 4 - FIX THE LOGGING HOLES S12 EXPOSED.** The Architect could not show John the 1z
     exchange, which is a failure of the observability built this morning (guiding invariant 8).
     - **Record the TARGET CELL ID on every call record.** Today a micro call logs
       `purpose: tax_graph_micro_formula` and no cell identity, so among 17 calls for the 1040
       the 1z call is unidentifiable. For a per-cell architecture the cell id is the single most
       important field.
     - **Retain request and response bodies for micro calls at normal level**, not DEBUG-only.
       These prompts are ~1,200 tokens and will now be smaller; the whole-document rationale for
       suppressing them is gone.
  5. **STEP 5 - RE-MEASURE AND REPORT.** `form_1040_2025` first, then all 15 draft-only, then
     `verify expression-agreement`. **Report COVERAGE and ACCURACY separately - do not collapse
     them.** Also report prompt-token size before and after (expect a large drop from removing
     the 59 candidates) and whether `extra_in_draft` fell. **Report honestly even if bad.**
     **Paste the full 1z request and response into this file** - John asked to see it and could
     not be shown.
  6. **Model/provider trouble is handled by falling back, never by stopping.** Do not hard-pin a
     provider. `google/gemini-3.6-flash` worked in S12 (74/74). If the configured model fails,
     switch to a pinned concrete alternative and continue. **Coming back without a number is the
     failure mode of this round.**
  7. **What this round does NOT do.** No operation-enum change. No draft promotion. No
     hand-authoring. No live graph edit. No rollover implementation. No review UI; S6-2 stays
     parked. Review/verdict contract still FROZEN. Do not loosen `strict_schema` or
     `require_parameters` to force a route.
  **PROTECTED TEST SET, unchanged hard gate:** `graph/2025/{nodes,edges,rules}/` byte-identical
  at round end; `git diff --stat` on those three directories EMPTY.
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`, module-form
  `validate 2025`, real preflight with `legacy_mined` explicit (expect **394**),
  `check_citation_integrity` STRICT (expect **36**). Short pytest temp root; no `--basetemp`.
  ONE local commit; no push. Cite the ACTUAL commit hash in your notes.
  **Stop conditions:** any diff in `graph/2025/{nodes,edges,rules}/`; any draft promoted;
  collapsing coverage and accuracy; a per-cell call needing more than 4000 response tokens;
  reintroducing node ids as the model's output vocabulary; `legacy_mined` above 394; strict
  mismatches above 36. **A model or provider failure is NOT a stop condition.**

- **M20-S12 TASK (COMPLETE, accepted at `a687c95`) - DERIVE EXPRESSIONS THROUGH THE PER-CELL MICRO PATH, THEN MEASURE
  (Architect, Claude Opus 5, 2026-07-30). John's go.** Ledger: the exact RAN/NOT RUN evidence
  rule, and D9.
  **READ THIS FIRST - IT IS WHY SIX ROUNDS FAILED.** S7-S11 each chased the previous symptom:
  a join failure, then an "empty prompt", then a provider, then truncation. **The actual defect
  was the SHAPE OF THE CALL.** The `expression_mode=generator` branch sends the whole rendered
  document, field grid, links, related sources, and schema summary in ONE prompt and asks for
  every graph kind back at once - which pinned the response at 23,911 / 23,937 completion
  tokens against a 24,000 cap. Raising the cap (which the Architect specced) treated the
  symptom. **The correctly-scoped call already exists**: the outline-first pipeline's
  `tax_graph_micro_formula` carries ONE node and its candidate spans. The generator branch was
  calling the whole-document route redundantly on top of it.
  **THIS IS ALSO EXACTLY WHAT JOHN DESCRIBED ON 2026-07-30:** for a cell, collect that cell's
  instructions from the form and the instruction PDF, then construct the expression against a
  bounding schema. Per cell. That is the simple, valid, reliable shape, and the code already
  had it.
  1. **STEP 1 - ROUTE EXPRESSION DERIVATION THROUGH THE MICRO PATH. Do NOT use the
     whole-document generator for expressions at all.** One call per formula-bearing cell,
     carrying only: that cell's label and address, its citations / candidate spans (form face
     AND instruction page), the closed operation enum, and the addressable operand candidates
     on that form. It returns ONLY the expression - operation plus operand refs. Everything
     else (nodes, citations, structure) continues to come from the deterministic outline path,
     which S11 proved runs clean: exit 0 in 8.4s with zero LLM calls.
  2. **STEP 2 - PER-CELL FAILURE ISOLATION.** A failed cell is recorded and skipped; it must
     NEVER fail the document or the run. Report `cells_attempted`, `cells_succeeded`,
     `cells_failed`, and the failure reasons grouped by kind. This is the property the
     whole-document call could never have: one bad cell cost us the entire form.
  3. **STEP 3 - `max_tokens` IS NOW A CANARY, NOT A DIAL.** Keep `micro_max_tokens` bounded at
     4000. **If a per-cell call needs more than that, the scoping is wrong again - STOP AND
     REPORT rather than raising it.** Do not raise the cap to make a call fit. That mistake is
     what produced this round.
  4. **STEP 4 - `form_1040_2025` FIRST, then all 15.** Report calls, successes, failures,
     tokens, cost, resolved model and resolved provider for the single form; then run the 15
     manifest forms draft-only and `verify expression-agreement`.
     **Report COVERAGE and ACCURACY separately - do not collapse them.** State which model
     produced the number. **Report honestly even if it is bad.**
  5. **MODEL/PROVIDER TROUBLE IS HANDLED BY FALLING BACK, NEVER BY STOPPING.** Do not hard-pin
     a provider. If the configured model fails for any provider-side reason, switch to a pinned
     CONCRETE alternative (a specific Flash version, not a `~...-latest` alias) and continue,
     recording that the fallback fired and why. **Coming back without a number is the failure
     mode of this round.**
  6. **What this round does NOT do.** No prompt tuning for quality beyond what the per-cell
     scope requires. No operation-enum change. No draft promotion. No hand-authoring. No live
     graph edit. No rollover implementation. No review UI; S6-2 stays parked. Review/verdict
     contract still FROZEN. Do not loosen `strict_schema` or `require_parameters` to force a
     route - switch models instead.
  **PROTECTED TEST SET, unchanged hard gate:** `graph/2025/{nodes,edges,rules}/` byte-identical
  at round end; `git diff --stat` on those three directories EMPTY.
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`, module-form
  `validate 2025`, real preflight with `legacy_mined` explicit (expect **394**),
  `check_citation_integrity` STRICT (expect **36**). Short pytest temp root; no `--basetemp`.
  ONE local commit; no push. Cite the ACTUAL commit hash in your notes.
  **Stop conditions - deliberately minimal:** any diff in `graph/2025/{nodes,edges,rules}/`;
  any draft promoted; collapsing coverage and accuracy; loosening `strict_schema` or
  `require_parameters`; a per-cell call needing more than 4000 response tokens (step 3);
  `legacy_mined` above 394; strict mismatches above 36. **A model or provider failure is NOT a
  stop condition - that is what step 5 is for.** Cost is not a constraint at this scale, but
  per-cell calls should be small; if the 1040 run's cost looks wildly out of line with ~$0.65
  for a whole 15-form Flash run, report it before running all 15.

- **M20-S11 TASK (COMPLETE, accepted at `fb8d87f`; produced no number, but diagnosed the real defect) - GET THE NUMBER. TRY GROK, FALL BACK TO FLASH, DO NOT COME BACK EMPTY
  (Architect, Claude Opus 5, 2026-07-30). John's go: `x-ai/grok-4.5`, he reports it is a good
  buy.** Ledger: the exact RAN/NOT RUN evidence rule, and D9.
  **WHY THIS ROUND IS SHAPED DIFFERENTLY.** S9b, S10, and S9 all ended with no measurement
  because each correctly stopped and reported on a provider failure. That discipline was right
  for diagnosis and is now getting in the way. **The deliverable of this round is a NUMBER, and
  there is a built-in fallback so a failing model cannot consume the whole session.**
  **THE PRIOR MEASUREMENT WAS INVALID, WHICH IS WHY FLASH IS A REAL OPTION AND NOT A RETREAT.**
  S8's coverage 8.75% / operation 7/7 / expression 0/7 was measured WHILE THE TRUNCATION BUG WAS
  ACTIVE - three of five Flash calls were cut off at ~4,000 tokens mid-payload. Since then
  `max_tokens` is 24000, expression mode defaults on, `strict_schema` defaults on, and every
  call is logged and attributed. **Flash has never been measured under correct conditions.**
  1. **STEP 1 - TRY `x-ai/grok-4.5`.** Pin the CONCRETE version; **verify the exact id against
     OpenRouter's current model list - do not take it from the Architect or from John's
     shorthand.** Run the one-document check on `form_1040_2025`, draft-only. Report prompt
     tokens, completion tokens, `finish_reason`, latency, cost, and resolved provider from the
     log.
  2. **DO NOT HARD-PIN THE PROVIDER.** That is what produced S10's dead ends - a no-route risk
     and a 502. We now RECORD `resolved_provider` in the log, provenance, and metrics, so
     attribution comes from observability, not from constraint. Leave fallbacks enabled and
     report which provider actually served each call.
  3. **STEP 2 - THE FALLBACK, AND IT IS AUTOMATIC.** If Grok fails the one-document check for
     any provider-side reason, **do NOT stop and report. Switch to a pinned CONCRETE Flash
     version** (not the `~google/gemini-flash-latest` alias - floating aliases are what
     destroyed attribution) and continue. Record clearly that the fallback fired and why.
  4. **STEP 3 - RUN THE 15-FORM BASELINE ON WHICHEVER MODEL WORKED.** Draft-only, then
     `verify expression-agreement`. **Report COVERAGE and ACCURACY separately - do not collapse
     them** - alongside resolved model, resolved provider(s), total tokens, and total cost.
     **Report honestly even if the number is bad.** State plainly which model produced it.
  5. **What this round does NOT do.** No prompt tuning for quality. No operation-enum change. No
     draft promotion. No hand-authoring. No live graph edit. No rollover implementation. No
     review UI; S6-2 stays parked. Review/verdict contract still FROZEN. Do not loosen
     `strict_schema` or `require_parameters` to force a route - switch models instead, per
     step 2.
  **PROTECTED TEST SET, unchanged hard gate:** `graph/2025/{nodes,edges,rules}/` byte-identical
  at round end; `git diff --stat` on those three directories EMPTY.
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`, module-form
  `validate 2025`, real preflight with `legacy_mined` explicit (expect **394**),
  `check_citation_integrity` STRICT (expect **36**). Short pytest temp root; no `--basetemp`.
  ONE local commit; no push. **Cite the ACTUAL commit hash in your notes** - S10's note cited
  `1d9766d` while the commit that landed was `4c40375`.
  **Stop conditions - deliberately few, because the goal is a measurement:** any diff in
  `graph/2025/{nodes,edges,rules}/`; any draft promoted; collapsing coverage and accuracy;
  tuning the prompt for quality; loosening `strict_schema` or `require_parameters`;
  `legacy_mined` above 394; strict mismatches above 36. **A provider failure is NOT a stop
  condition in this round - it is what the fallback is for.** Cost is not a constraint (~$0.65
  per 15-form run; $1.95 total to date).

- **M20-S10 TASK (COMPLETE, accepted at `4c40375`; produced no number - Decart 502) - PIN THE PROVIDER, THEN GET THE BASELINE NUMBER (Architect, Claude Opus 5,
  2026-07-30). John's go, and his words: "I want to get onto the testing." RUN IT THROUGH TO
  THE NUMBER IN ONE SESSION - do not stop at the one-document check if it passes.** Ledger: the
  exact RAN/NOT RUN evidence rule, and D9.
  **WHAT S9b PROVED (accepted at `544c4ae`).** The logging works and settled the diagnosis:
  our request is FINE. One well-formed attempt carried a 5,863-token prompt with strict
  `json_schema`, `max_tokens=24000`, and `require_parameters=true`. OpenRouter resolved
  `z-ai/glm-5.2` exactly and routed to **Baidu**, which returned `finish_reason=error`, null
  content, 3 completion tokens, cost 0.0, after **55 seconds**. **The provider is failing, not
  our code.** Both earlier diagnoses - "GLM cannot produce JSON" and "the prompt never reached
  the model" - are DISPROVEN. The billing page's 1-token entries were OpenRouter's accounting
  for errored calls, not a measure of what we sent.
  1. **STEP 1 - EXPOSE OPENROUTER PROVIDER ROUTING IN CONFIG.** Today
     `_openrouter_extra_body` (`tax_graph/extract/llm_client.py:148-162`) sends exactly one
     field, `provider: {require_parameters: true}`. Add config-driven support for provider
     selection, exclusion, fallback control, and quantization filtering. **Verify the exact
     field names against OpenRouter's CURRENT documentation - do not take them from the
     Architect.** Two diagnoses were wrong today from confident indirect knowledge; this is the
     same shape of claim.
  2. **STEP 2 - PIN TO `decart` WITH `fp4` QUANTIZATION - John's choice, he reports a sale.**
     Disable fallbacks so the route is deterministic and every number is attributable to a
     specific provider AND quantization. **Expected failure mode to anticipate, not to work
     around:** a hard provider pin combined with `require_parameters: true` can yield NO
     eligible route if that endpoint lacks strict `json_schema` support. If that happens,
     report it plainly - do NOT start loosening constraints to make it go away.
  3. **STEP 3 - ONE-DOCUMENT CHECK, then KEEP GOING.** `form_1040_2025`, draft-only. Confirm
     from the log that the call succeeded, and report prompt tokens, completion tokens,
     `finish_reason`, latency, cost, and resolved provider. **If it succeeds, proceed
     immediately to step 4 in the same session.** Only stop if it fails.
  4. **STEP 4 - THE 15-FORM BASELINE AND THE NUMBER.** Re-run the 15 manifest forms draft-only,
     then `verify expression-agreement`. **Report COVERAGE and ACCURACY separately - do not
     collapse them** - alongside resolved model, resolved provider, quantization, total tokens,
     and total cost. This is the deliverable: the first attributable measurement of what the
     pipeline derives on its own. **Report it honestly even if it is bad.**
  5. **What this round does NOT do.** No prompt tuning for quality (that comes after we can see
     a real number). No model swap away from `z-ai/glm-5.2`. No operation-enum change. No draft
     promotion. No hand-authoring. No live graph edit. No rollover implementation. No review UI;
     S6-2 stays parked. Review/verdict contract still FROZEN.
  **PROTECTED TEST SET, unchanged hard gate:** `graph/2025/{nodes,edges,rules}/` byte-identical
  at round end; `git diff --stat` on those three directories EMPTY.
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`, module-form
  `validate 2025`, real preflight with `legacy_mined` explicit (expect **394**),
  `check_citation_integrity` STRICT (expect **36**). Short pytest temp root; no `--basetemp`.
  ONE local commit; no push.
  **Stop conditions:** any diff in `graph/2025/{nodes,edges,rules}/`; any draft promoted;
  collapsing coverage and accuracy; tuning the prompt for quality; swapping the model; loosening
  `strict_schema` or `require_parameters` to force a route; `legacy_mined` above 394; strict
  mismatches above 36. **Cost is NOT a constraint** - $1.95 total for three prior runs, ~$0.65
  per 15-form run. Do not optimize for it, and do not stop to ask about spend at this scale.

- **M20-S9b TASK (COMPLETE, accepted at `544c4ae`) - BUILD THE LOGGING FIRST, THEN LOOK AT WHAT GLM ACTUALLY RECEIVED
  (Architect, Claude Opus 5, 2026-07-30, REWRITTEN on John's call). SUPERSEDES the S9 block
  below - read this first.** Ledger: the exact RAN/NOT RUN evidence rule, and D9.
  **JOHN'S RULING, and he is right: until we can log what GLM received and returned, further
  diagnosis is academic.** My first draft of this round told the Worker NOT to build the
  logging subsystem unless the diagnosis was trivial. That was backwards - **the logging IS the
  diagnostic instrument**, and guessing at causes without it is what produced the wrong S9
  diagnosis in the first place. Build it, then look, then fix what the logs actually show.
  **This round ENDS at a one-document diagnostic run. The 15-form baseline is the NEXT round.**
  Do not expand scope to chase the baseline; John asked to implement and then test.
  **Do NOT pre-commit to a cause.** Candidates for `prompt_tokens == 1` remain unconfirmed:
  the prompt arriving empty from template assembly on the batch path; OpenRouter rejecting and
  billing a stub; or `provider: {require_parameters: true}` (`llm.require_parameters: auto`)
  producing a degenerate route. The logs decide, not us.
  **THE S9 DIAGNOSIS WAS WRONG, AND SO WAS MINE.** S9 stopped with
  `LlmUnavailable: OpenRouter response did not contain JSON` and we both read it as a
  GLM structured-output problem. **It is not.** John's OpenRouter log settles it: all fifteen
  02:29 calls billed **1 prompt token and 1 completion token**, uniform $0.0000058, 0.1-2.2
  tok/s, **no finish reason**. A real extraction prompt is 6,500-9,700 tokens (visible in the
  12:42-12:44 Flash entries). **The prompt never reached the model.** GLM returned one token,
  which naturally was not JSON. **We have still never seen GLM attempt a single expression -
  do not draw any conclusion about the model, and do not swap it out.**
  The 02:27 probe sent 31 tokens and finished `stop`, so the client CAN send content; the
  difference is the pipeline path, not the model.
  1. **STEP 1 - BUILD THE LOGGING. This is the deliverable of the round** (guiding invariant 8
     in `docs/engineering-plan.md`, added 2026-07-30). Current state: **zero** modules import or
     use `logging`; the `logging: {level: INFO}` stub at `config/tax-graph.config.yaml:81` is
     read by nothing; no `logs/` directory exists.
     - **Per call:** run id, document id, purpose (generator / critic / example / nversion),
       requested model AND resolved model, prompt tokens, completion tokens, cost,
       `finish_reason`, latency, outcome.
     - **The request body and the response body.** On failure ALWAYS; otherwise at debug level.
       Cap the length sanely. **This is the highest-value item in the round** - its absence is
       exactly what made today academic. IRS form and instruction text is public; there is no
       sensitivity problem in retaining it.
     - **Run-level:** run id tying calls together, resolved config for the run (model, mode,
       concurrency), start/end, totals.
     - Honor the EXISTING `logging.level` config; do not add a second mechanism.
     - Write under a gitignored path (e.g. `output/logs/`) so a run is inspectable afterwards
       with no vendor dashboard.
     - **Only real constraint: never serialize resolved API keys or client headers.** Keys come
       from keyring/env. Everything else that makes sense, log.
  2. **STEP 2 - ADD THE FAIL-FAST GUARDS** (`tax_graph/extract/llm_client.py`):
     - **Assert `prompt_tokens` is plausible.** A ~1-token prompt must fail loudly and
       immediately with a named error. This would have caught today's failure in one second
       instead of 62.
     - **Treat `finish_reason: length` as a NAMED hard error.** Today it is only consulted when
       content is not text, so truncation surfaces as a confusing JSON parse failure.
  3. **STEP 3 - RAISE `max_tokens`; TRUNCATION IS A REAL SECOND BUG.** Three of five Flash calls
     in John's log finished with reason `length`, cut off at ~3,980-4,026 completion tokens, so
     the effective cap is ~4,000. A full form's nodes + edges + rules + citations does not fit.
     `_balanced_json_object` returns the unbalanced remainder when braces never close, so those
     calls failed outright rather than silently truncating - **but this is a plausible
     contributor to S8's 8.75% coverage.** Raise the cap, or chunk per document, and report
     which and why.
  4. **STEP 4 - RUN ONE DOCUMENT AND READ THE LOG. This is the test, and the round ends here.**
     `form_1040_2025` only, draft-only, pinned `z-ai/glm-5.2`. Then **report what GLM actually
     received and returned**: the outbound prompt size in tokens, whether the body was well
     formed, the response body, and `finish_reason`. If `prompt_tokens` is still ~1, the log now
     says WHY - report the cause with evidence rather than fixing it blind. **Do not proceed to
     the 15-form baseline in this round even if the one document succeeds** - that is the next
     round, and John asked to implement and then test.
  5. **STEP 5 - CLEANUPS. John asked to clear a few things this cycle. Common theme: SILENT
     DEFAULTS AND MISLEADING SIGNALS - the same disease that cost us today.**
     - **`extraction.expression_mode` defaults to `none`**, which silently produced a
       zero-expression 15-document run in S8 with no error. Make it loud or change the default;
       report which and why.
     - **`llm.strict_schema` defaults to `false`**, which makes the JSON schema advisory rather
       than binding on the OpenAI/OpenRouter path. The schema IS sent as
       `response_format: {type: json_schema, ...}`; strict is what gives it teeth.
     - **The example config still uses floating aliases** (`~google/gemini-flash-latest`,
       `~openai/gpt-mini-latest`). Floating aliases are what destroyed attribution - one config
       value was served by Flash 3 preview, 3.5, AND 3.6. The example should teach pinning.
     - **`confidence` is constant 1.0** across every object (min/max/mean all 1.0) and is
       recorded as if it means something. Nothing routes on it today, which is correct; mark it
       explicitly untrustworthy or stop emitting it.
     - **`output/m20_s7_expression_agreement.yaml` contains `measurement: m20_s8`.** The
       filename lies. Rename to a measurement-keyed name and update readers.
     Any cleanup that turns out to be bigger than it looks: leave it, and report why.
  6. **What this round does NOT do.** No 15-form baseline (next round). No model swap. No prompt
     tuning for quality. No coverage work beyond fixing truncation. No operation-enum change. No
     draft promotion. No hand-authoring. No rollover implementation (recorded in
     `docs/review-workbench.md`, for the 2026 boundary). No review UI; S6-2 stays parked.
     Review/verdict contract still FROZEN.
  **PROTECTED TEST SET, unchanged hard gate:** `graph/2025/{nodes,edges,rules}/` byte-identical
  at round end; `git diff --stat` on those three directories EMPTY.
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`, module-form
  `validate 2025`, real preflight with `legacy_mined` explicit (expect **394**),
  `check_citation_integrity` STRICT (expect **36**). **Short pytest temp root** - the Architect
  hit `WinError 206` (path too long) with a deep root today; keep it short. No `--basetemp`.
  ONE local commit; no push.
  **Stop conditions:** any diff in `graph/2025/{nodes,edges,rules}/`; any draft promoted;
  swapping the model away from `z-ai/glm-5.2`; collapsing coverage and accuracy; tuning the
  prompt for quality; `legacy_mined` above 394; strict mismatches above 36. **If step 1 shows
  the empty prompt is caused by OpenRouter routing rather than by our code, STOP and report** -
  that is a provider/config decision for John, not a code fix to improvise.

- **M20-S9 TASK (SUPERSEDED BY S9b ABOVE - its diagnosis was wrong; kept for the instrumentation
  requirements, which landed at `cdcbd65`) - MAKE THE NUMBERS ATTRIBUTABLE, THEN RE-BASELINE ON A PINNED MODEL
  (Architect, Claude Opus 5, 2026-07-30). John's go. Small round, and it is a PREREQUISITE for
  every number that follows.** Ledger: the exact RAN/NOT RUN evidence rule, and D9. Re-read D4,
  D6, D8, D11.
  **PRIME DIRECTIVE FRAMING (`AGENTS.md` section 1):** a pipeline whose output cannot be
  attributed to a specific model is not reliable and cannot be measured year to year. S8 gave us
  our first real numbers (coverage 7/80 = 8.75%; operation accuracy 7/7; expression accuracy
  0/7) but they are NOT attributable - John's OpenRouter billing shows the same config value
  served by a MIX of Flash 3 preview, 3.5, and 3.6, possibly varying within one 15-document run
  across the four concurrent workers. This round buys attribution and a clean baseline.
  **Confirmed spend to date: $1.95 total for three live runs. Cost is NOT a constraint on this
  project** - roughly $0.65 per 15-document run. Iterate freely; do not optimize for cost.
  1. **CAPTURE `usage` AND THE RESOLVED MODEL ID IN `tax_graph/extract/llm_client.py`.** Today
     the file has ZERO references to `usage`, `prompt_tokens`, `completion_tokens`, or cost, and
     it discards the resolved `model` field that OpenRouter returns on every response. The
     downstream plumbing already exists and sits null: `tax_graph/verify/metrics.py` has
     `worker_tokens` and `worker_cost`. Populate them, and record the RESOLVED model per call in
     draft provenance. **Today provenance records the ALIAS** (`extracted_by:
     ~google/gemini-flash-latest`), so no existing draft can be attributed to the model that
     actually produced it. Fix that going forward; do not attempt to backfill history.
  2. **SWITCH THE MODEL TO `z-ai/glm-5.2` - John's call.** He judges it cheaper and comparable.
     Do NOT argue the choice; DO verify it mechanically.
     - **Verify the id resolves with ONE cheap single-document call before any 15-document run.**
       A bad id either errors or gets silently routed somewhere John did not choose. If it does
       not resolve, STOP and report - do not substitute a model.
     - Note the string is a CONCRETE VERSION, not a floating alias: no `~`, no `-latest`. That is
       deliberate and it is what makes attribution possible. **Do not "helpfully" convert it to a
       latest-style alias.**
     - Also set `extraction.expression_mode: generator` in the real config. John's
       `config/tax-graph.config.yaml` is gitignored and LACKS it; the default is `none`, which is
       what made S8's first full run produce zero expressions with no error. **A model swap
       without this line yields a fast, clean, completely empty run.** Consider whether a silent
       `none` default is the right default at all and report a recommendation - do not change it
       in this round.
  3. **RE-BASELINE.** Re-run the 15 manifest form documents on the pinned model, draft-only, then
     re-run `verify expression-agreement`. Report COVERAGE and ACCURACY separately exactly as S8
     did - do not collapse them - and state the resolved model id and total token usage alongside
     the numbers. The S8 Flash numbers do not transfer and must not be reused as a baseline.
  4. **What this round does NOT do.** No prompt tuning for quality. No coverage work (that is the
     next round). No operation-enum change. No draft promotion. No hand-authoring. No rollover
     implementation - those decisions are recorded in `docs/review-workbench.md` and are for the
     2026 boundary. No review UI; S6-2 stays parked. Review/verdict contract still FROZEN.
  **PROTECTED TEST SET, unchanged hard gate:** `graph/2025/{nodes,edges,rules}/` byte-identical
  at round end; `git diff --stat` on those three directories EMPTY.
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`, module-form
  `validate 2025`, real preflight with `legacy_mined` explicit (expect **394**),
  `check_citation_integrity` STRICT (expect **36**). Short pytest temp root; no `--basetemp`.
  ONE local commit; no push.
  **Stop conditions:** `z-ai/glm-5.2` not resolving (stop, do not substitute); any diff in
  `graph/2025/{nodes,edges,rules}/`; any draft promoted; collapsing coverage and accuracy;
  tuning the prompt for quality; converting the pinned model id to a floating alias;
  `legacy_mined` above 394; strict mismatches above 36; or an API/quota/egress failure.
  **Spend is now measurable - report actual token usage and, if the response exposes it, cost,
  rather than "spend is not exposed by the client."**

- **M20-S8 TASK - MAKE THE MEASUREMENT WORK: ID BRIDGE + OPERAND ROLES, THEN RE-MEASURE
  (Architect, Claude Opus 5, 2026-07-30). John's go. S7 produced an UNSCORABLE result; this
  round exists to make the number real, and NOTHING else.** Ledger: the exact RAN/NOT RUN
  evidence rule, and D9 (grep for consumers of the SHAPE, not just the files). Re-read D4, D6,
  D8, D11 before starting.
  **PRIME DIRECTIVE FRAMING (`AGENTS.md` section 1):** we cannot know whether the pipeline
  reaches ~98% until it can be scored against the protected set. This round buys the ability to
  measure. It does NOT try to raise the score.
  **WHAT S7 ACTUALLY FOUND (Architect-read, 2026-07-30).** `expression_agreement=0` is **NOT a
  quality score - it is a failed join.** `operation_disagreement` is ALSO `0`; zero agreements
  AND zero disagreements together mean nothing was ever compared. `missing_in_draft=80`,
  `extra_in_draft=35`. The Worker diagnosed two causes and correctly refused to hand-repair
  either: (a) generated ids do not match the protected canonical ids, so edges never pair -
  note that draft NODE ids already match (`form_1040_2025_root_line_1a` is in both), so this is
  an EDGE-TARGET id convention problem, not a general identity problem; and (b) generated edges
  omitted operand roles, so operand sets cannot be reconstructed even where ids do match.
  1. **STEP 1 - BRIDGE GENERATED IDS TO CANONICAL ADDRESSES.** Identity must go through the
     canonical address path - that is the standing invariant and it is what makes human
     judgement survive regeneration. `graph/2025/addresses/` and `graph/2025/_drafts/addresses/`
     already exist; use them rather than inventing a second mapping. Diagnose FIRST and report
     what the generated edge-target convention actually is before writing the bridge. **A
     hardcoded per-form id lookup table is NOT acceptable** - next year's forms would break it,
     which defeats the point of the pipeline.
  2. **STEP 2 - EMIT OPERAND ROLES ON GENERATED EDGES.** Required for scoring: `addend`,
     `minuend`, `subtrahend`, etc. **Scope discipline: structural changes needed to make the
     output SCORABLE are in scope; prompt tuning to make the output BETTER is NOT.** If you find
     an obvious quality win, write it down as a finding for the next round and leave it. We are
     not tuning against a score we cannot yet see.
  3. **STEP 3 - RE-MEASURE, AND REPORT COVERAGE AND ACCURACY SEPARATELY. Do not collapse them
     into one percentage.** This is the most important instruction in the round. S7's 1040 run
     emitted `edges=4, rules=3` against **80** live expressions. If that holds, a naive
     "agreement %" computed over only the paired cells could read 100% while the pipeline
     derived almost nothing. Report both, per document and in total:
     - **COVERAGE** - of the live expressions in the protected set, how many have ANY generated
       counterpart. (S7 baseline: 0 of 80.)
     - **ACCURACY** - of those that pair, how many match on operation, and how many match on
       operation AND operand set.
     - Keep `missing_in_draft` / `extra_in_draft` as-is.
     Commutative comparison rule is unchanged from S7: order-insensitive for `SUM`, `MULTIPLY`,
     `MIN`, `MAX`, order-sensitive otherwise, reusing the semantics in
     `workbench/address_verdicts.py` `normalize_expression` rather than a second copy.
     Update `output/m20_s7_expression_agreement.yaml` or supersede it with a clearly named S8
     report; state the headline COVERAGE and ACCURACY numbers in this file.
  4. **What this round does NOT do.** No prompt tuning for quality. No model swap (Flash stays -
     John's call, and it has still not had a fair scored trial). No operation-enum change. No
     draft promotion. No hand-authoring or hand-editing of any generated or live artifact. No
     review UI - S6-2 stays parked. No change to the review/verdict contract, still FROZEN.
  **THE PROTECTED TEST SET IS UNCHANGED AS A HARD GATE:** `graph/2025/{nodes,edges,rules}/` must
  be byte-identical at round end; `git diff --stat` on those three directories must be EMPTY.
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:` on every one. ASCII, `git diff --check`,
  module-form `validate 2025`, real preflight with `legacy_mined` reported explicitly (expect
  **394**), `check_citation_integrity` STRICT (expect **36**). Short pytest temp root; no
  `--basetemp`. ONE local commit; no push.
  **Stop conditions:** any diff in `graph/2025/{nodes,edges,rules}/`; any draft promoted; a
  hardcoded per-form id table instead of a canonical-address bridge; collapsing coverage and
  accuracy into a single number; tuning the prompt for quality; `legacy_mined` above 394; strict
  mismatches above 36; or an API/quota/egress failure. **If the bridge turns out to require
  changing how the generator NAMES things rather than how the scorer READS them, stop and report
  before doing it** - that is a pipeline-shape decision for John, not a scoring fix.

- **M20-S7 TASK - GENERATE THE EXPRESSION LAYER AND MEASURE IT AGAINST THE HANDCRAFTED SET
  (Architect, Claude Opus 5, 2026-07-30). John's direction. This round exists to produce ONE
  NUMBER we have never had: how much of the expression layer the pipeline gets right on its
  own.** Ledger: the exact RAN/NOT RUN evidence rule, and D9 (grep for consumers of the SHAPE,
  not just the files). Re-read D4, D6, D8, and D11 before starting.
  **PRIME DIRECTIVE FRAMING (`AGENTS.md` section 1):** the graph is never hand-authored. The
  target loop is: forms change -> re-run the pipeline -> ~98% valid -> human directs the last
  ~2% through comments -> the pipeline reworks. **Every step below serves measuring and then
  raising that 98%.** No step in this round is allowed to raise the number by hand-authoring.
  **THE FINDING THAT MOTIVATES THIS ROUND (Architect-measured, 2026-07-30):** the pipeline
  currently emits **nodes and citations only**. `_drafts/form_1040_2025/metrics.yaml` reports
  `objects_by_kind: {citations: 50, documents: 1, nodes: 56}`, and **no `edges.yaml` or
  `rules.yaml` exists in any of the 16 draft directories.** The live graph's 409 edges and 15
  rule templates carry **zero provenance** and did not come from the pipeline - they are the
  hand-authored A9 scaffolding. **The pipeline has never produced an expression.** The model in
  use is `~google/gemini-flash-latest`; John's ruling is that this is a bounded task (pick one
  operation from a closed enum, name its operands, given a few sentences of instruction text)
  and Flash should be given a fair try before any model change is considered. Do NOT swap models
  in this round.
  **JOHN'S RULING - THE HANDCRAFTED SET IS NOW THE TEST SET, AND IS PROTECTED.** A lot of tokens
  went into it. It is not to be thrown away, promoted over, or edited. It becomes labeled
  comparison data. **The live graph under `graph/2025/{nodes,edges,rules}/` MUST be
  byte-identical at the end of this round** - `git diff --stat` on those three directories must
  be EMPTY, and that is a hard gate, not a guideline.
  1. **STEP 1 - DIAGNOSE THE MISSING EXPRESSION LAYER. Cheap, and it forks the size of step 2.**
     The generator prompt ALREADY asks for them (`prompts/extract_generator.md`: "Emit only
     schema-valid nodes, edges, rules, citations, and decisions", "Rule operation must be one
     of: {operations}", "Every rule must have at least one citation_ref"). So either Flash is
     not returning edges/rules, or it is and something downstream drops them before write.
     **Determine which.** Capture the RAW model response for ONE document (`form_1040_2025`)
     before any parsing, routing, or filtering, and report: raw edge count, raw rule count, and
     what the write path does with them. **CHECKPOINT: record both numbers in this file before
     starting step 2.** If it is a downstream drop, this is a plumbing fix - fix the plumbing and
     do NOT redesign the extraction architecture. If Flash genuinely returns none, step 2 is
     prompt and schema-surfacing work.
  2. **STEP 2 - MAKE THE GENERATOR EMIT THE EXPRESSION LAYER.** Bounded by the EXISTING v0
     operation enum in `schemas/rule.schema.json` - 19 operations: `COPY, SUM, SUBTRACT,
     MULTIPLY, DIVIDE, MIN, MAX, NEGATE, ABS, ROUND, LOOKUP_TABLE, LOOKUP_BRACKET, IF, IF_ELSE,
     AND, OR, NOT, COMPARE, REQUIRE_INPUT`. **Do not extend, rename, or add to this enum in this
     round** - if a form genuinely needs an operation outside it, emit a review gap and report
     it; that is a finding, not a licence to widen the set.
     - Edges MUST carry the operand role (`addend`, `minuend`, `subtrahend`, etc.), because the
       expression is COMPOSED from node + incoming edges + shared rule. Without roles the
       operand set cannot be reconstructed and step 3 cannot score.
     - **The critic must review edges and rules too**, not just nodes. Today drafts carry
       `critic_agrees` on nodes; extend that to the expression layer. An unreviewed expression is
       not a candidate for anything.
     - Prefer instruction-document citations for formulas (the prompt already says this).
     - `confidence` is currently useless telemetry - `min/max/mean = 1.0` across every object.
       Do NOT build any routing or scoring on self-reported confidence. Use critic agreement.
     - **Write to `graph/2025/_drafts/` ONLY. Promote nothing.**
  3. **STEP 3 - DIFF THE GENERATED EXPRESSIONS AGAINST THE HANDCRAFTED SET AND REPORT THE
     NUMBER.** The join is free: draft node ids already match live node ids exactly
     (`form_1040_2025_root_line_1a` is in both). For every live computed node, compare the live
     expression (its rule's operation + the operand set from its incoming edges) against the
     draft's. Report, per document and in total:
     - **`expression_agreement`** - operation AND operand set both match. **This is the headline
       number and the deliverable of the round.**
     - `operation_agreement_operands_differ` - right verb, wrong operands.
     - `operation_disagreement` - wrong verb.
     - `missing_in_draft` / `extra_in_draft` - present in one side only.
     Compare operand sets **order-insensitively for commutative operations** (`SUM`, `MULTIPLY`,
     `MIN`, `MAX`) and order-sensitively otherwise - `workbench/address_verdicts.py`
     `normalize_expression` already encodes exactly this distinction and its
     `_COMMUTATIVE_EXPRESSION_KINDS` set is the reference; reuse the semantics rather than
     inventing a second rule that can drift from it.
     Write the report to a committed artifact under `output/` and state the headline number in
     this file. **Report it honestly even if it is bad** - a low number is the correct input to
     the next decision, and a number massaged upward is worse than no number.
  4. **What this round explicitly does NOT do.** No review UI (S6-2 stays parked). No promotion
     of any draft. No hand-authoring or hand-editing of edges, rules, nodes, citations, or
     labels. No model swap. No change to the operation enum. No change to the review/verdict
     contract - it was verified green on 2026-07-30 and is **FROZEN** until John has actually
     used the page; churn there is what has kept the verdict store empty.
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:` on every one. ASCII, `git diff --check`,
  module-form `validate 2025` (must stay green - the live graph is untouched), real preflight
  with `legacy_mined` reported explicitly (expect **394**, unchanged), and
  `check_citation_integrity` STRICT (expect **36**, unchanged). Short pytest temp root; no
  `--basetemp`. ONE local commit; no push.
  **Stop conditions:** any diff at all in `graph/2025/{nodes,edges,rules}/` (the test set is
  protected); any draft promoted into the live graph; `legacy_mined` rising above 394; strict
  citation mismatches above 36; the operation enum being widened; needing to hand-author an
  expression to make the number look better; an API key, quota, or cost failure - **report the
  spend before running all 16 documents if step 1 suggests the run will be expensive.**

- **M20-S6-2 - PARKED (2026-07-30, John's call).** The review-panel/visual-key round is NOT next.
  Rationale in prime-directive terms: as currently wired the workbench would have John reviewing
  the HAND-AUTHORED graph, which tells us nothing about pipeline validity and spends his scarce
  review attention on scaffolding. Unpark once M20-S7 reports its agreement number, and respec
  it then - review must be pointed at generated cells carrying provenance, with the
  generated-vs-handcrafted disagreements surfaced FIRST, because those are John's 2%. Also note
  the S6-2 text as written is stale: it assumes ARITHMETIC 15 / COPY 39, which was the LOCATED
  count; the projection now measures ARITHMETIC 139 / COPY 49 over 2,120 cells.

- **M20-S6-1 TASK - MAKE THE EXPRESSION THE THING BEING APPROVED (Architect, Claude Opus 5,
  2026-07-29). John's design ruling; the review model's final shape. SPLIT from S6 on John's
  call - this is the BACKEND half, provable by tests; the UI half is S6-2 and this round must
  not touch `workbench/static/`.** Ledger: **D11**, D4, D6, D8, D9, and the RAN/NOT RUN rule.
  **John's ruling:** a cell is a discrete entity with its own instructions and links, because
  the IRS authors forms as a one-step-at-a-time operation. If every cell is right AND the
  operations joining them (sum, copy, etc.) are right, the return is right by composition.
  **Therefore the EXPRESSION is the top-level thing being approved**, with the form
  instruction and the instruction-page text shown as supporting context.
  **Terminology, settled:** `operation` is the graph verb (`SUM`, `COPY`, `SUBTRACT`, `MIN`,
  `MAX`, `MULTIPLY`, `NEGATE`, `IF_ELSE`, `LOOKUP_TABLE`, `LOOKUP_BRACKET`). `expression`
  wraps it and carries the OPERANDS. **Approve the expression, not the operation** - `SUM`
  alone is meaningless without "sum of what". `expression.kind` is the discriminator John
  identified: it spans the computed verbs plus `input` (user entry), `imported` (from a
  1099/W-2), `repeatable_table` (per-row), and `review_gap` (no authored graph).
  **The measured shape of the work, which should drive the UI (Architect-measured, 1,921
  cells):** `imported` 696 (36.2%), `review_gap` 591 (30.8%), `input` 484 (25.2%),
  `repeatable_table` 96 (5.0%), and **all computed kinds together just 54 (2.8%)**. **The
  entire arithmetic of the return is 54 expressions.** Treating all 1,921 as equal review
  units is the wrong shape for the workload.
  1. **Put the expression into `review_content` and therefore into the fingerprint.** Today
     `review_content` is `{label, cited_text}` only (`workbench/derived_reviews.py`), so the
     OPERATION IS NOT PART OF WHAT GETS APPROVED. Worked example: line 1z
     (`2025/document=form_1040/line=1z/control=amount`) is `sum` over operands 1a..1h with
     label `Add lines 1a through 1h`. **Drop operand 1g and the label, the citation, and the
     fingerprint are all unchanged - the cell stays `approved` while computing a different
     number.** That is the exact silent-drift failure this design exists to prevent, and it is
     live today. Fingerprint the operation AND the structured operand refs, normalized, so
     operand order/formatting churn does not cause false invalidation but a changed operand
     set does.
  2. **Split form citations from instruction-page citations - they are merged today.**
     `derived_reviews.py:61` and `:81` concatenate `instruction_citations + citations` into
     one flat `cited_text`, losing which quote came from the form face versus the instruction
     booklet. John wants BOTH, distinguished. Carry two named slots through the projection and
     into `review_content`; the upstream data already keeps them apart.
  3. **Worksheet lines are cells - bring them in.** The QDCGT worksheet currently projects
     **0** units because the projection keys on PDF geometry. `form_1040_2025_qdcgt_line_1` is
     a stable canonical address and is exactly "one step at a time with its own instruction".
     Project graph nodes that have no geometry as cells too, marked unlocated. This also fixes
     the S5-2 regression where the carried authored entry says "no human has read the
     worksheet lines yet" while the units it refers to are unreachable.
  4. **Routing is NOT a cell and needs its own small review set.** Correct cells compose into
     a correct form; they do not tell you WHICH forms apply. Whether this filer files
     Schedule B at all is not a cell - every Schedule B cell can be perfect and the return
     still wrong. That is **90 routing edges + 12 triggers + 2 decisions = 104 objects**,
     small enough to review as its own list. It must not silently be nobody's job, which is
     where S5-2 left it.
  5. **Restore the two non-queue-specific validators S5-2 removed:** `zero_units` and
     `ambiguous_object`. The second seeded a duplicate graph decision and expected preflight
     to reject it - that is graph integrity, not queue plumbing, and it currently has no named
     home. (`promotion_scope_missing` and `field_map_incomplete` were queue-specific and stay
     gone.)
  6. **Emit the data the UI round needs - projection only, NO UI work in this round.**
     S6-2 owns presentation. Here, make the derived coverage emit (a) `review_gap` cells as
     their own named bucket, distinct from `unreviewed`, and (b) a `kind_bucket` on every
     cell resolving `expression.kind` to one of ARITHMETIC / COPY / USER_ENTRY / IMPORTED /
     PER_ROW / NOT_REVIEWABLE per S6-2 item 3's mapping. **Pin the mapping in a test so a new
     `expression.kind` cannot silently fall through to an unlabelled default** - that test is
     the contract S6-2 builds against.
  7. **The fingerprint change is breaking, and it is free exactly once.**
     `review_verdicts/2025/address_verdicts.jsonl` still has ZERO records, so changing the
     fingerprint inputs invalidates nothing today. **Confirm the store is empty before
     starting.** If any real verdict exists by then, STOP and report - it becomes a migration
     of human judgements and needs its own round.
  8. **Do NOT** promote any draft, hand-edit generated citations or labels, change graph
     semantics, alter geometry/field maps, **or touch `workbench/static/`** - the UI is S6-2's
     and this round must not pre-empt it.
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:` on every one. Per D9, grep for
  consumers of the `review_content`/expression SHAPE, not just the files. ASCII,
  `git diff --check`, module-form `validate 2025`, real preflight with `legacy_mined` reported
  explicitly (expect **394**), and `check_citation_integrity` STRICT (expect **36**). Short
  pytest temp root; no `--basetemp`. ONE local commit; no push.
  Stop conditions: any real verdict existing in the store when item 7 is checked; the
  fingerprint being made so strict that formatting churn invalidates approvals (test both
  directions - changed operand set invalidates, reordered/reformatted equivalent does not);
  the 1,921 cell denominator DROPPING (items 3 and 4 should raise it - report the new number
  and what it now covers); `legacy_mined` rising, strict mismatches above 36; or a
  quota/environment failure.

- **M20-S6-2 TASK - CONSOLIDATE THE REVIEW PANEL AND ADD THE CELL-KIND VISUAL KEY (Architect,
  Claude Opus 5, 2026-07-29). Runs AFTER S6-1 lands. UI round - verify in the browser, not
  only in tests.** Ledger: D4, D6, D9, D11, and the RAN/NOT RUN rule. Split from S6 on John's
  call: the backend half is provable by tests, this half needs John to look at it and say it
  reads right, and mixing them would produce one commit where half the work cannot be
  verified the same way.
  **Precondition:** S6-1 is green on main and its `kind_bucket` contract test passes - that
  test is what this round builds against. Do not recompute bucket membership in JavaScript;
  consume what the projection emits.
  1. **John's layout ruling - the review panel holds the decision, the panel below holds the
     evidence.** The review panel must carry **the expression, the instructions, the
     accept/reject controls, and the comment box TOGETHER**. Today the verdict controls sit in
     the LEFT rail (`workbench/static/index.html:45`, `.verdict-bar`) while the cell content
     is in the right-hand river - a reviewer reads on the right and reaches to the far left to
     approve. Move them together. **Amplifying info - sources, metadata, graph evidence -
     stays in a SEPARATE panel below**, roughly what `#river-detail` already is. Keep the
     existing 15/40/45 three-column proportions.
  2. **Show the two instruction sources separately**, using the split S6-1 item 2 produced:
     the form-face text and the instruction-page text are distinct slots with distinct
     labels, never concatenated back together for display.
  3. **VISUAL KEY BY CELL KIND. Read both constraints first; they change the obvious
     implementation.**
     **(a) The critical set is 15, not 54.** John asked for the critical cells flagged
     red/orange with copies coloured differently - and copy is 39 OF the 54. Splitting them as
     he intended gives **ARITHMETIC 15** (`sum` 11, `subtract` 1, `max` 1, `if_else` 1,
     `lookup_table` 1) - the entire computed arithmetic of the return - and **COPY 39**
     separately. That is the right line: a copy is checkable against ONE source ref, a formula
     needs operands and structure checked.
     **(b) RED IS ALREADY TAKEN - do not reuse it.** `--danger` currently means
     `policy-unsupported` on the form overlay (`workbench/static/styles.css:100`), and
     `styles.css:112` carries an explicit standing warning that `--danger` and selection must
     never be mistaken for a policy state. Note the trap: `review_gap` maps to
     `policy-unsupported`, so red today marks the **591 cells that CANNOT be reviewed** -
     roughly the opposite of "critical". **Put the cell-kind key on a SEPARATE VISUAL CHANNEL:
     a labelled badge on the review cell card, NOT the region outline colour**, which stays
     owned by policy state. Two systems, two channels, neither competing.
     **The buckets come from S6-1's `kind_bucket` - never hardcode the counts, they are 2025
     measurements and will move as authoring fills the gaps:**
     - ARITHMETIC (`sum`, `subtract`, `multiply`, `negate`, `min`, `max`, `if_else`,
       `lookup_table`, `lookup_bracket`) - the hottest badge, orange/red-orange
     - COPY (`copy`) - distinct warm colour; `--gold` fits the existing palette
     - USER ENTRY (`input`)
     - IMPORTED (`imported`) - arrives from a 1099/W-2
     - PER-ROW (`repeatable_table`)
     - NOT REVIEWABLE (`review_gap`) - muted, and per item 4 it is a separate bucket rather
       than a colour on a reviewable cell
     **Colour must never be the only signal** - every badge carries a short text label too (it
     is a label flag, so this is free), for colourblind reviewers and for print. Add a legend
     keyed to the same tokens.
  4. **Distinguish "nothing to approve" from "unreviewed".** A `review_gap` cell has no
     authored graph, so approving it is meaningless - **591 cells, 30.8%**, are in this state.
     They need AUTHORING, not review, and must not sit in the reviewer's queue looking like
     work: a third of the list would be unactionable and the tool would read as broken.
     Surface them as their own bucket, using the S6-1 projection.
  5. **Do NOT** change the verdict store, the fingerprint, the projection, or any graph
     artifact. If the UI wants data the projection does not emit, that is an S6-1 follow-up -
     report it rather than recomputing it in the browser.
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:`. **Because this is a UI round, run the
  workbench and verify in the browser** - confirm the consolidated panel, the badges, and the
  legend actually render, and report what you observed. ASCII, `git diff --check`,
  module-form `validate 2025`, and real preflight with `legacy_mined` (expect **394**). Short
  pytest temp root. ONE local commit; no push.
  Stop conditions: any badge reusing `--danger` or otherwise colliding with the policy-state
  channel (item 3b); bucket membership being recomputed in JavaScript instead of consumed
  from the projection; any backend/projection change proving necessary (report it, do not do
  it here); or a quota/environment failure.

- **[DONE `48af95b`, Architect-verified and ACCEPTED 2026-07-29. Two defects found and routed
  to S5-2: the missed FOURTH authored entry (item 6 below - Architect error) and
  string-compared timestamps in `_latest_by_address`.]
  M20-S5-1 TASK - BUILD THE DERIVED VERDICT PATH ALONGSIDE THE QUEUE (Architect, Claude
  Opus 5, 2026-07-29). John's ruling; supersedes the S3a-2 reconciler. SPLIT on John's call
  so that preflight NEVER GOES DARK - this round ADDS the derived path and changes nothing
  about the existing gate; M20-S5-2 retires the queue only once both are green together.**
  Read the ACCEPTED-but-superseded S3a-2 verification and John's ruling in Current state
  first - especially the two verified facts this round rests on: **zero human verdicts exist
  anywhere**, and **100% of generated-id refs churned while 0% of address-keyed refs did**.
  Ledger: **D11** (records must persist - here as append-only history), **D13** (never
  hand-patch generated output; the corollary this round adds is that human data must never
  live in a machine-rewritten file), D4, D6, D8, D9, D10, and the RAN/NOT RUN rule.
  **The problem:** `review_queue/2025/deferred_review.yaml` is a materialized worklist keyed
  on unstable generated ids. Every regeneration invalidates it wholesale, and reconciling it
  is a permanent tax on running the pipeline - which is supposed to be the end state, not a
  thing we tiptoe around. Nothing of human value is stored in it today, so this is the LAST
  CHEAP MOMENT to change the shape. Once real verdicts exist, wiping stops being free.
  1. **Stand up an append-only verdict store, keyed by canonical address.** A verdict records
     the address (`node_id` / control address), a **content fingerprint of what was actually
     reviewed** (label plus cited text), the judgement, who, and when. **Never delete a
     verdict** - superseded ones are the audit trail of what a human saw and approved, which
     is exactly the record tax software most regrets discarding. Current state is a query for
     the newest verdict matching current content.
  2. **Do NOT store verdicts inside the generated node/citation YAML.** Those files are
     rewritten by the pipeline; human data there is clobbered on the next regeneration. This
     is D13's corollary. Keep the store separate and key it on address - because node ids are
     stable, that join is TOTAL and cannot orphan the way the citation-keyed queue did.
  3. **Normalize before fingerprinting** - collapse whitespace, normalize dashes and quotes.
     If the extraction METHOD changes (new model, different quote characters), an unnormalized
     hash shifts on every cell and you get a spurious full wipe with no semantic change. Given
     this project has already been through a 52%->100% text migration, that is not
     hypothetical. Pin it with a test: same semantic text, different whitespace/quoting, same
     fingerprint.
  4. **Make coverage a graph walk, computing three states per cell.** No verdict ->
     `unreviewed`. Verdict with matching fingerprint -> `approved`. Verdict whose fingerprint
     no longer matches -> `approved, content changed, needs recheck`. **That third state IS
     the orphan bucket, derived at read time instead of migrated and stored** - so there is
     nothing to reconcile and nothing to clean out, ever. A -> B -> A content flip revalidates
     the original approval for free.
  5. **Report reingest blast radius BEFORE it lands.** Reingest must stop being scary: with
     content fingerprinting, blast radius is proportional to actual text change, not to the
     act of regenerating. Emit "this reingest invalidates N of M approvals, here they are" so
     it is a decision rather than a surprise.
  6. **[ARCHITECT ERROR - "three" IS WRONG, THERE ARE FOUR. Corrected in S5-2 item 4, which
     names all four by id. `decision_review_1040_deduction_method` was missed here and was
     therefore not carried by S5-1. Verify by id, never by count.]**
     **Carry the three hand-authored entries across by hand.** Nearly all 97 queue entries are
     machine-emitted and regenerable (62 `instruction_join_review` from
     `tax_graph.ingest.instruction_promotion`, 9 `promotion_review` from `tax_graph.promote`,
     the field maps). **Three carry curated Architect prose that is NOT derivable and must be
     preserved:** `authored_review_qdcgt_worksheet_2025` and the two `decision_review` entries
     (`created_by: tax_graph.m13.architect`) - their `summary` and `machine_witnesses` text.
     Everything else is wiped and re-derived.
  7. **Year rollover is the same mechanism plus one rule - build the seam, do not exercise it.**
     Match on address-minus-year plus fingerprint, so an unchanged TY2026 line can inherit its
     TY2025 approval. **A carried approval is its OWN visible state with provenance**
     ("carried from TY2025, approved by X on <date>, text identical"), bulk-acceptable and
     per-cell revocable - never a silent copy. Identical text across a year boundary is weaker
     evidence than within one: "Enter the amount from line 15" can be character-identical
     while line 15's computation changed underneath it. Within a year, identical text can mean
     still-approved; across years it means probably.
  8. **PREFLIGHT GATES ON BOTH, AND THE QUEUE PATH IS UNTOUCHED. This is the point of the
     split.** Add the derived coverage check as a SECOND preflight assertion beside the
     existing queue check; both must pass in the same run. **Do NOT remove, weaken, or rewire
     the existing queue gate, do NOT delete `review_queue/2025/deferred_review.yaml`, and do
     NOT touch `reconcile_generated_review_queue` or `tax-graph review reconcile-queue`** -
     all of that is S5-2's job, after this round proves the derived path in production. The
     failure this ordering exists to prevent is a window where neither gate is trustworthy.
  9. **Report the two paths side by side; do NOT expect them to agree.** The queue currently
     carries 263 orphans and stale draft-era state, so equality is the WRONG gate and forcing
     it would mean corrupting the derived path to match a broken artifact. What must hold is
     that the derived path covers **the same cell denominator the graph reports (1,921
     controls)** with every cell landing in exactly one of the three states, and that any cell
     the queue covers but the derived path does not is a NAMED finding with a reason. Print
     both counts. Divergence is expected and is the data S5-2 needs.
  10. **Do NOT** promote any draft, hand-edit any generated citation or label, change graph
     semantics, or alter geometry/field maps in this round. Promotion is gated on the derived
     reviews actually being worked, and that is a later round.
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:` on every one. Per D9, grep for
  consumers of the queue SHAPE (workbench manifest, preflight, sessions, verdicts), not just
  of the file. ASCII, `git diff --check`, module-form `validate 2025`, real preflight with
  `legacy_mined` reported explicitly (expect **394** - this round promotes nothing), and
  `check_citation_integrity` with the STRICT number (expect **36**). Short pytest temp root;
  no `--basetemp`. ONE local commit; no push.
  Stop conditions: any design that puts a verdict inside a generated file; any fingerprint
  scheme that cannot survive a whitespace/quoting change; the three authored entries not being
  preservable (stop and report rather than dropping them); **any need to modify the existing
  queue gate to make the derived path pass** (that is the signal the split was right - report
  it and stop); `legacy_mined` rising, strict mismatches above 36, or the 1,921 cell
  denominator changing; or a quota/environment failure.

- **M20-S5-2 TASK - RETIRE THE QUEUE, CARRY THE FOURTH AUTHORED ENTRY, AND FIX VERDICT
  ORDERING (Architect, Claude Opus 5, 2026-07-29). Runs ONLY after S5-1 lands and John
  accepts the side-by-side report. Mostly deletion, plus two correctness fixes found in
  Architect review of S5-1 - items 4 and 5 are the BLOCKING ones and item 4 is a data-loss
  path.** Ledger: **D8** (a promoted artifact's SHAPE is a contract - the queue
  file IS such a contract until this round removes it), **D9** (grep for consumers of the
  SHAPE, not the file - the M20-S2d lesson was that a format consumer does not show up in a
  file-reader grep), D4, D6, D11.
  **Precondition, verify before touching anything:** S5-1's dual-gate preflight is green on
  main, and the side-by-side divergence report has been read and accepted. If the derived path
  has ANY unexplained cell, stop - that is what this round's precondition exists to catch.
  1. **Flip preflight to gate on the DERIVED coverage alone**, then remove the queue
     assertion. In that order, in the same commit, so no intermediate state has zero gates.
  2. **Delete the superseded machinery:** `reconcile_generated_review_queue`,
     `tax-graph review reconcile-queue`, the `orphaned` bucket in
     `schemas/deferred_review_queue.schema.json`, and `review_queue/2025/deferred_review.yaml`
     itself.
  3. **Do NOT delete `tests/test_review_queue_reconciliation_m20.py` silently** - state
     explicitly what derived-path test replaces each behaviour it pinned, and delete it only
     once that replacement exists and is green. A deleted test with no named successor is a
     silent coverage loss (D11).
  4. **FOUR authored entries must be carried, not three - ARCHITECT ERROR IN THE S5-1 BLOCK,
     corrected here (2026-07-29).** The S5-1 spec said "three"; there are **four**
     non-derivable entries, and S5-1 carried only three. `review_context/2025/
     authored_reviews.yaml` is MISSING `decision_review_1040_deduction_method`
     (`created_by: tax_graph.architect`, 167 chars of curated prose). **Carry it before
     deleting anything.** Verify by exact id - never by count, which is what let this slip:
     - `authored_review_qdcgt_worksheet_2025` (carried)
     - `authored_review_schedule_d_2025_tax_worksheet` (carried)
     - `routing_review_schedule_d_2025_line_20_decision` (carried)
     - `decision_review_1040_deduction_method` (**MISSING - add it**)
     If any of the four is absent from the carryover file, STOP. Deleting the queue would
     drop prose that is not regenerable from any pipeline. Add a test asserting all four ids
     are present, so the count can never drift again.
  5. **Fix verdict ordering to use truncated epoch seconds - do this FIRST, and pull it
     forward if any real review starts before this round.** `_latest_by_address`
     (`workbench/address_verdicts.py`) string-compares ISO timestamps, so mixed UTC offsets
     pick the WRONG current verdict. Demonstrated: an `approved` at
     `2026-07-29T12:00:00+02:00` (10:00Z) beats a genuinely later `rejected` at
     `2026-07-29T11:00:00+00:00` (11:00Z). That is silent approval drift - precisely the
     failure this whole design exists to prevent - and `reviewed_at` is a caller-supplied
     parameter, so a UI passing local time trips it.
     - **Store `reviewed_at_epoch` as an INTEGER of whole UTC seconds, and make it the sole
       ordering key.** Integers have no offset ambiguity and sort correctly by definition.
     - **Keep a human-readable `reviewed_at`** as UTC ISO-8601, because this ledger is an
       audit record an auditor reads directly and a bare epoch tells them nothing. Validate
       on write AND on load that the two agree; disagreement is a tamper signal, so it must
       raise rather than pick a winner.
     - Tie-break equal epochs by file order (later line wins), and pin it with a test.
     - **`review_verdicts/2025/address_verdicts.jsonl` does not exist yet - there are ZERO
       records - so this is a clean break with no migration.** Do it now; after real verdicts
       exist it becomes a migration.
     - Note `_make_verdict_id` seeds on `address|reviewed_at`; update it consistently.
  6. **While in the file, close the soft validation hole:** `_validate_record` only
     cross-checks `content_fingerprint` against `reviewed_content` when that field is
     present, so a record lacking it can carry any 64-hex string. Require `reviewed_content`
     on every record.
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`,
  module-form `validate 2025`, real preflight with `legacy_mined` (expect **394**), and
  `check_citation_integrity` STRICT (expect **36**). Short pytest temp root. ONE local commit;
  no push.
  Stop conditions: S5-1 not accepted; any moment where preflight asserts nothing; **any of the
  FOUR authored entries named in item 4 not present in the carryover file** (verify by id, not
  by count); any ordering scheme that still compares timestamps as strings; a deleted test with
  no named successor; or a quota/environment failure.

- **M20-S2d TASK - REWIRE THE SPAN MATCHER TO THE LINE-ANCHOR INDEX (Architect, Claude
  Opus 5, 2026-07-28). Small, mechanical, unblocks S3a.** Your own S3a block report
  diagnosed this correctly - it is an Architect scoping error in the S2 task, not a defect
  in your work. Read the ruling directly above this block. Ledger: **D8** (a promoted
  artifact's SHAPE is a contract), **D9** (run the consumers - and note the lesson that a
  format consumer will not show up in a file-reader grep), D4, D6, and the RAN/NOT RUN rule.
  **The problem:** `_span_for_line` (`tax_graph/extract/outline_pipeline.py:698-705`)
  resolves a node's source span with `span.text.startswith(f"- {anchor}:")`. S2 deliberately
  removed that inline wrapper, so the match never fires and the outline comes back empty.
  **The material:** `.fields.json` now carries `line_anchors` - entries with `anchor`,
  `page`, `text_offset`, `text_length`, and rect coordinates, pointing INTO the emitted text.
  1. **Resolve spans through the index, not through a text prefix.** A node with
     `line_anchor` "16" should find its span via the `line_anchors` entry for "16" and that
     entry's offset into the text - positional truth rather than a string convention. Keep
     `_line_anchor_variants` behaviour for anchor spelling (`16` / `16a`); it is the
     PREFIX-matching that goes, not variant handling.
  2. **Fail closed and say so.** A node whose anchor has no index entry, or an index entry
     that resolves to no span, is a named finding - never a silent `None` that empties the
     outline. The current failure mode is precisely a silent empty (ledger D10), and
     `extract` exited **0** while producing nothing, which is the worst combination.
  3. **Pin it with a test that would have caught this.** A line-16 node on
     `schedule_a_2025` must resolve to the span containing
     `Other-from list in instructions. List type and amount:`. Add a negative test too: a
     node whose anchor is absent from the index raises/reports rather than returning empty.
  4. **Do NOT** regenerate artifacts, promote drafts, hand-edit any generated citation or
     label, or touch the rebuilt text, the citation gate, geometry, field maps, or verdicts.
     S3a owns regeneration and runs after this.
  5. **[ANSWERED - the Worker correctly kept this out of S2d and reported it for S3a; S3a
     item 1 now owns it.]** **Leave the stale draft files alone** for now, but report the second defect you found -
     that the draft writer leaves old draft files in place when a batch kind is empty. That
     is a real fail-open and S3a will need it fixed; state whether you consider it in scope
     here or better handled in S3a, and why.
  Declared files plus honest `RAN:`/`NOT RUN:` on every one. Per D9, grep for consumers of
  the span/outline SHAPE, not just of the files. ASCII, `git diff --check`, module-form
  `validate 2025`, and real preflight with `legacy_mined` reported explicitly (expect
  **394**, unchanged - this round promotes nothing). No `--basetemp`. ONE local commit; no
  push.
  Stop conditions: any need to change the rebuilt text, the citation gate, or a promoted
  artifact; the index proving insufficient to anchor spans (report what is missing rather
  than reintroducing prefix matching); or a quota/environment failure.

- **M20-S2e TASK - MAIN IS RED: MAKE THE SPAN RESOLVER FAIL CLOSED AT THE RIGHT GRANULARITY
  (Architect, Claude Opus 5, 2026-07-28). Small and urgent - it unblocks S3b.** Read the
  CI-red ruling directly above; the spec error that caused this is the Architect's, not
  yours. Ledger: **D10** (a zero-node outline is the forbidden outcome), **D14** (a change
  to a function's FAILURE BEHAVIOUR needs the consumers of that behaviour), D4, D6, D9.
  **Reproduce first:** `.venv\Scripts\python.exe -m pytest tests/test_batch_extraction_m10.py -q`
  -> 2 failed in ~2.6s.
  1. **A document with NO line-anchor index is legitimate, not an error.**
     `form_13614_c_2025` has **zero** anchors and 297 widgets. Return `None` for the node
     and record a named finding; do NOT raise and do NOT abort the batch.
  2. **An unresolvable anchor inside a document that HAS an index is a finding, not a
     crash.** Route it through the existing findings/route mechanism so it is visible and
     counted. `SpanResolutionError` should stop being thrown from `_span_for_line` on these
     paths.
  3. **Keep fail-closed where it belongs: the DOCUMENT level.** A document whose outline
     comes back with **zero nodes** is a hard, named failure - that is the D10 outcome and
     it is exactly how S3a died twice. Do not let this fix reopen the silent-empty hole; a
     zero-node outline must never coexist with exit code 0.
  4. **Declare `tests/test_batch_extraction_m10.py`** and any other test that drives
     extraction over documents lacking the index. Per D14, grep for callers of
     `_span_for_line` and `SpanResolutionError`, and for tests that run `extract` over
     fixture documents - the failure-behaviour consumers, not just the result consumers.
  5. **Do not** change the emitted text layer, the citation gate, promoted artifacts, or the
     anchor-variant fix from `414ccda`. This is a narrow behaviour correction.
  Declared files plus honest `RAN:`/`NOT RUN:` on every one. ASCII, `git diff --check`,
  module-form `validate 2025`, real preflight with `legacy_mined` reported explicitly
  (expect **394**). No `--basetemp`. ONE local commit; no push - the Architect pushes this
  one and watches CI, since main is currently red.
  Stop conditions: any need to reintroduce per-anchor fatality, weaken the document-level
  zero-node check, or touch a promoted artifact; or a quota/environment failure.

- **M20-S3b-2 TASK - FIX ANCHOR IDENTITY (Architect, Claude Opus 5, 2026-07-28).**
  Your structure layer WORKS - 100% caption coverage on every document, non-empty outlines
  where all were 0, honest degradation on 13614-C. **The gap is anchor IDENTITY, which is
  what citations key on, and it is 12% wrong.** Read the retraction ruling above; the
  premature acceptance was the Architect's. Ledger: **D13** (verbatim is necessary, not
  sufficient - anchoring is what matters), D10, D14, D4, D6, D9.
  **Measured: 13 disagreements across 112 checkable rows.** The method, which you should
  make permanent: on a line row the token at the RIGHT EDGE is the printed box reference -
  the row's true line - and it is independent of the leading-token rule you mint from.
  1. **Reference vs definition (cheapest, fixes 4).** `'d Add lines 5a through 5c 5d'` mints
     `5a`; the row is `5d`. `_REJECTED_PRECEDERS` (`structure.py:22`) lacks **`line` and
     `lines`**, so a token inside "Add lines 5a through ..." can mint the anchor. Also
     `8a`->`8e`, `14a`->`14c`, `13c`->`38`. **This is the same `5a -> 5d` failure you found
     in your own earlier adapter and correctly removed it for** - it returned in the shipped
     rule. Consider preferring the TRAILING printed box reference when it disagrees with the
     leading token, rather than extending a blacklist indefinitely.
  2. **Two-column merged rows (the real work, about 6 rows).**
     `'4a IRA distributions 4a b Taxable amount 4b'` holds lines 4a AND 4b; also 2a/2b,
     3a/3b, 5a/5b. These must be SPLIT, not assigned one anchor. The 10-form experiment
     measured this class at 34 rows corpus-wide, so it is not confined to the 1040. Widget
     x-positions are the evidence: two input widgets on one visual row means two logical
     rows.
  3. **Headers must mint nothing.** `'Dependents Dependent 1 Dependent 2 Dependent 3
     Dependent 4'` mints `1`. `_HEADER_PHRASES` catches "Part I" and similar but not a
     column-header row like this one.
  4. **Make the cross-check a committed validator.** The printed-box-reference comparison
     must live in the pipeline and FAIL CLOSED on disagreement, not in a scratch script.
     **The citation gate cannot catch this class** - every one of these rows is genuinely in
     the source, so `check_citation_integrity` passes all 13. That is exactly D13, and this
     validator is the mechanical answer to it.
  5. **Report the disagreement count per document, before and after.** Baseline: schedule_a
     2, form_1040 8, schedule_1a 2, form_8949 1, schedule_d 0, schedule_1 0 - 13 of 112
     (12%). Target zero; any residual must be a named finding with its reason, never a
     silent pass. **Hold caption coverage at 100%** while fixing identity.
  6. **Promote NOTHING** - no regeneration, no drafts, no citations. S3a runs after this and
     only once the disagreement count is zero or explicitly accepted.
  Tier 3 (pipeline behaviour). Declared files plus honest `RAN:`/`NOT RUN:` on every one.
  ASCII, `git diff --check`, module-form `validate 2025`. **Real preflight is RED for an
  unrelated reason** (the review queue references stale draft ids; S3a owns it), so report
  it as a known-red gate rather than treating it as your failure. No `--basetemp`. ONE local
  commit; no push.
  Stop conditions: caption coverage regressing below 100%; a rule you cannot justify against
  the three defect classes above; any need to touch the text layer, citation gate, or a
  promoted artifact; or a quota/environment failure.

- **[PARTIAL - implementation landed in `fc337d0`; anchor identity returned as S3b-2]
  M20-S3b TASK - BUILD THE STRUCTURE LAYER (Architect, Claude Opus 5, 2026-07-28).**
  **This is the phase's hard round and it unblocks S3a.** Read `plans/PHASE_M20.md`
  (sequencing correction) and the S3a-attempt ruling above. Ledger: **D10** (a silent empty
  is the forbidden outcome), **D13** (verbatim is necessary, not sufficient - anchoring is
  what matters), **D14** (consumers of a FORMAT, not just a path), D4, D6, D8, D9.
  **The problem in one line:** this pipeline never had a structure layer -
  `render_form.py`'s `- 16:` wrapper WAS the structure, and removing it (correctly) left
  `build_outline_tree` parsing markup that no longer exists. Outline children are **0** on
  every document. Structure must now be built for real.
  **DESIGN DIRECTION - INVERT THE OLD APPROACH.** The old pipeline parsed TEXT to derive
  structure. That is convention-dependent and it just broke. **Build structure from
  GEOMETRY, and use text only for captions.** Geometry is spec-level and producer-robust:
  1,921 AcroForm widgets enumerate cleanly across three distinct producers
  (`Designer 6.5`, `Adobe PDF Library 15.0`, and a 1999 `APJavaScript` form). Text parsing
  is a convention we no longer control.
  **MEASURED FACTS - do not re-survey, build against these:**
  - **Anchors are NOT at row starts.** `schedule_a_2025`: 9 anchors at line start, **18
    mid-line**. `form_1040_2025`: 22 vs **21**. A row like
    `'and 1 Medical and dental expenses (see instructions) 1'` carries left-column spillover
    (`and`), the defining anchor (`1`), the caption, and a trailing printed box reference.
  - **A row can contain several anchors, and the index entry is not always the row's
    defining line.** Index anchor `1a` points at the row `'z Add lines 1a through 1h 1z'` -
    that is line **1z**, and `1a`/`1h` there are REFERENCES inside the caption. Same family
    as the M16-S2 `z -> 1z` defect, and exactly why the Worker's adapter put Schedule A
    `5a` on the `5d` body. **Distinguishing a row's DEFINING anchor from anchors MENTIONED
    in its caption is the core problem of this round.**
  - **Some documents have NO line anchors at all.** `form_13614_c_2025`: **0** line_anchors,
    209 text lines, 297 widgets. Any design keyed solely on line anchors yields nothing
    there. It is the intake questionnaire and it must degrade to geometry.
  - Prior geometry measurement (Architect, same-row/left-of widgets): **85%** on
    schedule_1a, **82%** on the 1040, **51%** on 13614-C, with named failure modes -
    multi-widget rows overshooting, and checkbox matrices whose caption is a column header
    ABOVE rather than left.
  1. **Emit a structure model the pipeline can consume** - whatever `build_outline_tree`
     needs (sections, line nodes with `line_anchor`, page) - derived from widget geometry
     plus word rects, not from synthetic text markup. Keep the emitted text layer untouched;
     S2 owns it and it is complete.
  2. **Resolve a row's DEFINING anchor** and do not be fooled by referenced anchors in the
     caption. State the rule you use and why it is not a heuristic that silently
     mis-assigns. The printed box reference beside the input widget is likely stronger
     evidence than token order in the text - the widget knows where it is.
  3. **Fail closed, loudly.** A row that cannot be assigned a defining anchor, or a widget
     with no caption, is a NAMED finding. **A zero-node outline with exit code 0 is the
     forbidden outcome** (D10) - that is precisely how S3a failed twice.
  4. **Degrade honestly with no anchors.** For `form_13614_c_2025` structure must come from
     geometry alone. Report what fraction of its 297 widgets get a caption, and treat the
     remainder as findings rather than pretending coverage.
  5. **Report association coverage per document** - widgets with a resolved caption over
     total widgets - as the ratcheted number this phase has been building toward. Include
     the three documents above plus at least one from the producer-robustness corpus
     (`tests/fixtures/m20_producer_corpus/`) to check the approach is not `Designer 6.5`
     -specific.
  6. **Prove it end to end:** `build_outline_tree` must return a NON-EMPTY outline for
     `schedule_a_2025`, and Schedule A line 16 must resolve to the row carrying
     `Other-from list in instructions. List type and amount:` - the record D13 got wrong.
  7. **Promote NOTHING.** No regeneration, no draft promotion, no citation or label writes -
     S3a owns all of that and runs after this. `legacy_mined` stays **394**, citations stay
     **36 strict**, cells stay **1,921**.
  Tier 3 (pipeline behaviour). Declared files plus honest `RAN:`/`NOT RUN:` on every one;
  per D14 grep for consumers of the outline's SHAPE, not just its path. ASCII,
  `git diff --check`, module-form `validate 2025`, real preflight with `legacy_mined`
  reported explicitly. No `--basetemp`. ONE local commit; no push.
  **This round is allowed to be big, and it is allowed to come back with a partial result
  plus honest findings.** If association lands well below the measured geometry baselines,
  report the number and the failure modes rather than widening a heuristic to hit a target -
  a silent mis-assignment here becomes a wrong citation on every form.
  Stop conditions: any need to change the emitted text layer, the citation gate, or a
  promoted artifact; a rule you cannot justify against the mis-assignment failures above;
  or a quota/environment failure.

- **M20-S3a-1 TASK - REGENERATE, AND ACCOUNT FOR EVERY DIFF (Architect, Claude Opus 5,
  2026-07-29). Split from the old single S3a on John's call.** This is the round that writes
  to HUNDREDS of promoted citations, so scope is deliberately narrow: regenerate and account.
  **Queue reconciliation is S3a-2 - do not attempt it here.** Read `plans/PHASE_M20.md` and
  the S3b-2 acceptance above. Ledger: **D13** (verbatim is necessary, not sufficient -
  anchoring is what matters), **D12** (never weaken a gate to make it pass), D8, D9, D10,
  D11, D4, D6.
  **Foundation is now sound and verified:** text retention 100%, caption coverage 100%,
  anchor disagreement 1% (was 12%), citation gate strict at 36 pre-existing mismatches.
  The prerequisites from the old task are DONE - the digit-suffix anchor fallback and the
  stale-draft fail-open both landed in `414ccda`.
  1. **Re-run extraction against the corrected text.** Output goes to
     `graph/<year>/_drafts/` - **drafts are NEVER auto-merged**, promotion requires the full
     machine witness set green, and under the deferred-review policy human review is
     recorded as PENDING in the queue, never asserted. Never write `human_confirmed` or any
     equivalent.
  2. **THE DIFF IS THE DELIVERABLE, not the regeneration.** Compare every regenerated
     citation and label against the current one and account for each change. Expected: text
     restored by S2 (punctuation, previously-dropped rows), and labels losing the old
     renderer's damage (`Line 16: Otherfrom list in instructions`, `Part Iii Line 28`).
     **A changed ANCHOR - different line or section - is a FINDING, not an accepted
     change.** That distinction is the whole reason we regenerate rather than patch.
  3. **Verify the known-wrong record explicitly:** `cite_span_schedule_a_2025_0036` must come
     back anchored to Schedule A **line 16** (`Other-from list in instructions. List type and
     amount:`), not line 6. Say so in your evidence with the resulting text.
  4. **Ship the anchor cross-check as a committed fail-closed validator.** On a line row the
     token at the right edge is the printed box reference - the row's true line - and it is
     independent of the rule that mints the anchor. The Architect's scratch version found
     13 mis-anchorings the citation gate could never see, because every quoted row is
     genuinely in the source. **This validator is the mechanical answer to D13** and it must
     exist before hundreds of citations depend on it. Current baseline: 1 of 192 (the
     `schedule_1` footer minting `1` from the form's own name).
  5. **Report the ratchets, before and after:** `legacy_mined` (currently **394** - this
     round should move it DOWN and it must never rise), strict `check_citation_integrity`
     (currently **36**, must not grow), cells (**1,921**, denominator must hold), and the
     count of citations whose text changed versus whose anchor changed.
  6. **Regeneration is an LLM operation and is not trustworthy on a single pass.** State the
     model used. If a document's output disagrees with the current promoted artifact beyond
     the expected text-fix explanations, STOP and report rather than promoting.
  **Real workbench preflight is KNOWN-RED** (stale queue ids; S3a-2 owns it). Report it as a
  known-red gate, not as your failure, and do not try to make it pass.
  Tier 3 (promoted artifacts). Declared files plus honest `RAN:`/`NOT RUN:` on every one;
  per D9 and D14 grep for consumers of both the VALUES and the SHAPE of what you regenerate.
  ASCII, `git diff --check`, module-form `validate 2025`, and `check_citation_integrity`
  reported explicitly with the STRICT number. No `--basetemp`. Use a SHORT pytest temp root.
  ONE local commit; no push.
  Stop conditions: any regenerated citation whose anchor moved without an explanation; any
  temptation to hand-edit a generated artifact (that is D13, and it is what this round
  exists to avoid); `legacy_mined` rising, strict citation mismatches above 36, or the 1,921
  cell denominator changing; or a quota/environment failure.

- **[DONE `d59cbe5`, Architect-verified and ACCEPTED - but SUPERSEDED BY DESIGN in M20-S5.
  The work was correct; the artifact it reconciled is the wrong shape. Kept as history and as
  the evidence for the redesign: 100% of generated-id refs churned, 0% of address-keyed refs
  did, and zero human verdicts existed to preserve.]
  M20-S3a-2 TASK - RECONCILE THE REVIEW QUEUE AND RESTORE PREFLIGHT (Architect, Claude
  Opus 5, 2026-07-29). Runs AFTER S3a-1 lands, against settled ids.** Ledger: **D11**
  (findings/records must persist), D10, D4, D6, D9.
  **The problem:** the queue's pending entries reference draft-derived ids from an old
  extraction run (`cite_span_form_1040_2025_0001`, `form_1040_2025_root_line_a`) that exist
  neither in the graph nor in the current drafts, because the text and spans moved under
  them. **Real workbench preflight has been RED since, and could not gate any round in
  between** - restoring that signal is this round's point.
  **WHAT S3a-1 SETTLED, build on these exact facts:** all 15 form drafts were regenerated
  (model `~google/gemini-flash-latest`); live-to-draft delta is `added=945 removed=698
  changed=72`; **51 citations whose quote or locator moved are already recorded as FINDINGS**
  and must be resolved here, not re-pointed silently; 21 changed labels on `form_1040_2025`
  are damage-shedding and expected. **The `cite_span_schedule_a_2025_0036` case is your
  worked example:** the old id holds line-6 text on a line-16 node, the regenerated draft
  drops it and carries `cite_span_schedule_a_2025_0083` with the correct line-16 text. That
  is a REPLACEMENT, not a rename - the old id must be retired through the orphan path with
  its reason, never aliased onto the new one as though they were the same evidence.
  1. **Migrate against the ids S3a-1 settled**, never against intermediate ones.
  2. **Follow the M19-S2 precedent exactly** (it solved this same problem for manifest unit
     ids): a UNIQUE match moves and records the old id in `aliases`; anything ambiguous or
     missing lands in an orphaned bucket with an explicit reason. **Never silently
     re-point a review** - a deferred human judgement attached to the wrong object is worse
     than an orphaned one, because it looks reviewed.
  3. **Report counts:** migrated, orphaned, and orphaned-by-reason.
  4. **Restore preflight to green** and report it explicitly with `legacy_mined`.
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`,
  module-form `validate 2025`, real preflight, and `check_citation_integrity` with the
  strict number. Short pytest temp root. ONE local commit; no push.
  Stop conditions: any review that cannot be matched uniquely being re-pointed anyway; any
  need to edit a generated artifact by hand; or a quota/environment failure.

- **[SPLIT into S3a-1 and S3a-2 on John's call, 2026-07-29]
  M20-S3a TASK - REGENERATE DERIVED ARTIFACTS FROM THE CORRECTED TEXT (Architect, Claude
  Opus 5, 2026-07-28).** **Do NOT hand-edit a single citation, label, or display name in
  this round.** Everything below is fixed by re-running the generator whose input changed.
  Read ledger **D13 first** (both halves - the Worker defect AND the Architect instruction
  that caused it), plus D4, D6, D8, D9, D10/D11. Phase plan: `plans/PHASE_M20.md`.
  **Why:** S2 rebuilt the stored form text from 52.2% to 100% retention. Everything derived
  from the OLD text is still damaged: `cite_span_*` citations (26 were stale), node labels
  (`Line 16: Otherfrom list in instructions`, `Line 4: through 11 31`, `Part Iii Line 28`),
  display names, and the 394 `legacy_mined` entries. One regeneration fixes the whole class.
  This is where the long-planned M16-S5 regeneration converges.
  0b. **RECONCILE THE REVIEW QUEUE - assigned here by Architect ruling, 2026-07-28.** The
     queue's pending entries reference draft-derived ids from an old extraction run
     (`cite_span_form_1040_2025_0001`, `form_1040_2025_root_line_a`) that no longer exist in
     the graph or the current drafts, because the text and spans moved under them. **Real
     workbench preflight is RED until this is fixed**, so it cannot gate any round in the
     meantime. Reconcile AFTER regenerating, so you migrate against final ids rather than
     ids that are about to change again. **Follow the M19-S2 precedent exactly:** a unique
     match moves and records the old id in `aliases`; anything ambiguous or missing lands in
     an orphaned bucket with an explicit reason. **Never silently re-point a review** - a
     deferred human judgement attached to the wrong object is worse than an orphaned one.
     Report counts: migrated, orphaned, and by reason.
  0. **PREREQUISITE - remove the digit-suffix anchor fallback BEFORE regenerating.**
     `_line_anchor_variants` (`tax_graph/extract/outline.py:152-159`) expands `"16"` to
     `{"16", "6"}`. Exact match wins today so nothing depends on it, but a missing index
     entry would silently resolve line 16 to line 6 - D13 by code. Exposure if exact
     matching ever fails: schedule_a 8, form_1040 8, schedule_d 7, schedule_1a 26 anchors.
     The rule was legacy compensation for the OLD split-label defect, which the corrected
     index has already fixed (`11b` is one anchor). Remove the digit-suffix fallback, or
     make it a reported finding rather than a silent alternate match - never a quiet second
     choice. Prove no anchor regresses (all four documents currently resolve 100%
     exactly), and pin it with a test that a numeric anchor does NOT match a shorter one.
     Do this FIRST: regenerating on top of it would bake a mis-anchoring into hundreds of
     citations.
  1. **Re-run extraction against the corrected text** for the affected documents. **Fix the
     stale-draft fail-open you reported first:** the draft writer leaves the previous
     `nodes.yaml` / `citations.yaml` in place when a regenerated batch kind is empty, so an
     empty regeneration silently presents old content as current. That is a fail-open on the
     exact artifact this round rewrites. Output
     goes to `graph/<year>/_drafts/` as always - **drafts are NEVER auto-merged**, and
     promotion requires the full machine witness set green. Under the deferred-review policy
     the human review may be recorded as pending in the review queue, never asserted as
     done. Do not write `human_confirmed` or any equivalent.
  2. **The DIFF is the verification, and it is the point of this round.** Compare every
     regenerated citation against the current one and account for each changed
     `quoted_text`. A change explained by the text fix (punctuation restored, a previously
     dropped row now present) is expected; a change of ANCHOR - different line, different
     section - is a finding to report, not to accept. This diff is what would have caught
     D13 mechanically.
  3. **Verify the known-wrong record explicitly:** `cite_span_schedule_a_2025_0036` must
     come back anchored to Schedule A **line 16** (the faithful text
     `Other-from list in instructions. List type and amount:` is present in the rebuilt
     `.cache/raw/2025/schedule_a_2025.txt`), not line 6. Say so in your evidence.
  4. **Report the ratchets:** `legacy_mined` before and after (currently **394** - this
     round should move it DOWN and it must never move up), strict
     `check_citation_integrity` before and after (currently **36**, and it must not grow),
     and the cell/address counts (1921 cells - the denominator must hold).
  5. **Regeneration is an LLM operation and is not trustworthy on a single pass.** State the
     model used. If a document's regenerated output disagrees materially with the current
     promoted artifact beyond the expected text-fix explanations, STOP and report rather
     than promoting.
  6. **Scope discipline:** structure and caption-to-cell association are **S3b**, not this
     round. Do not attempt column separation or label joining here.
  Tier 3 (promoted artifacts). Declared files plus honest `RAN:`/`NOT RUN:` on every one;
  per D9 grep the consumers of anything you regenerate. ASCII, `git diff --check`,
  module-form `validate 2025`, real preflight with `legacy_mined` reported explicitly, and
  `check_citation_integrity` reported explicitly with the STRICT number. No `--basetemp`.
  ONE local commit; no push.
  Stop conditions: any regenerated citation whose anchor moved and cannot be explained; any
  temptation to hand-edit a generated artifact (that is the defect this round exists to
  stop); `legacy_mined` rising, citation mismatches rising above 36 strict, or the 1921 cell
  denominator changing; or a quota/environment failure.

- **[CANCELLED - superseded by S3a; hand-patching generated artifacts is the anti-pattern]
  M20-S2c TASK - RE-ANCHOR ONE CITATION (small, surgical round) (Architect, Claude Opus 5,
  2026-07-28).** S2b is otherwise ACCEPTED - **do NOT touch the gate (it is correctly strict
  now), the other 25 re-derivations, the rebuilt text, or the retention ratchet.** Read
  ledger **D13; it was logged from this exact round.**
  1. **Fix `cite_span_schedule_a_2025_0036`.** Its node is
     `schedule_a_2025_root_line_16_amount` (Schedule A **line 16**, Other Itemized
     Deductions). Its `quoted_text` is currently `Other taxes. List type and amount:`, which
     is **line 6** (Taxes You Paid). Re-derive it from line 16 - the faithful string
     `Other-from list in instructions. List type and amount:` is present in the rebuilt
     `.cache/raw/2025/schedule_a_2025.txt`. Verify the result is an exact substring of that
     file. Do NOT change the `citation_id`.
  2. **Sweep for the same class before declaring done.** For every citation whose
     `quoted_text` changed in S2b (`139a1bc`, plus the 22 in
     `graph_ext/2025/form_2441_2025/citations.yaml`), confirm the new text is explainable as
     PUNCTUATION RESTORATION of the old text. Any change that is not - a different span, a
     shorter or longer phrase, different words - must be justified against the referencing
     node's label and the printed line, or re-derived properly. **The gate cannot catch this
     class**, so it is a read-and-compare job, not a test run.
  3. **Report the count** of changed citations that were pure punctuation restoration versus
     any others found, with ids.
  4. Node labels carrying old damage (`Line 16: Otherfrom list in instructions`) are **NOT**
     in scope - S3 owns that sweep. Leave them.
  Declared files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`, module-form
  `validate 2025`, real preflight with `legacy_mined` (expect **394**), and
  `check_citation_integrity` reported explicitly - it must stay at **36 strict**, with zero
  carried by any fallback. No `--basetemp`. ONE local commit; no push.
  Stop conditions: any citation that cannot be re-derived and verified (report the id);
  any need to reintroduce a gate fallback, change a `citation_id`, or touch the rebuilt
  text; or a quota/environment failure.

- **[DONE `139a1bc`, D12 closed; one defect returned as S2c] M20-S2b TASK - RE-DERIVE THE 26 STALE CITATIONS AND REVERT THE GATE LOOSENING
  (Architect, Claude Opus 5, 2026-07-28).** The S2 text rebuild is ACCEPTED - **do NOT redo
  it, do NOT touch `render_form.py`, `text_normalize.py`, or the regenerated `.txt`.** Read
  ledger **D12 first; it was logged from this exact round.** Also **D9** (run the consumers)
  and the exact RAN/NOT RUN rule. The model for this work is **M18-S2b**, which solved the
  identical problem: read that entry in this file before starting.
  **The situation:** your rebuild was CORRECT, and it correctly exposed 26 citations whose
  `quoted_text` still carries the old renderer's damage (`isnt`, `didnt` - apostrophe welds
  the rebuild fixed). Those records are stale; the source is right. With the fallbacks
  disabled the gate reports **62 mismatches**, and **26 pass only because of them**: 22
  `cite_span_form_2441_2025_*`, `cite_span_schedule_1a_2025_0035`, `..._0050`,
  `cite_span_schedule_a_2025_0017`, `..._0036`.
  1. **Re-derive each of the 26 `quoted_text` values from the corrected acquired source and
     VERIFY each against that source**, exactly as M18-S2b did. Use
     `tax_graph/acquire/citation_cleanup.py`; it exists for this. A record that cannot be
     re-derived AND verified is a FINDING to report with its id - never a guess to promote,
     never a record to quietly drop.
  2. **Do NOT change any `citation_id`.** They are referenced from addresses and nodes; a
     re-key orphans those references.
  3. **REVERT the compatibility branches in `_contains_normalized`** -
     `_has_legacy_renderer_signature`, `_legacy_punctuation_match`, and
     `collapse_other_from`. The strict normalized-substring check is the contract. If a
     migration shim is genuinely needed while re-deriving, it must be a ONE-SHOT migration
     path in the cleanup tool with an explicit expiry, never a permanent branch inside the
     verifier.
  4. **Report the gate honestly, both ways:** `check_graph_citations` before and after, and
     state the STRICT number. Target: strict mismatches back to the true **36** pre-existing
     baseline (20 `instructions_form_1040_2025` A9 scaffolding, 15
     `instructions_schedule_d_2025`, 1 `schedule_d_2025`) with **zero** carried by any
     fallback. If you land above 36 strict, STOP and report the ids rather than widening
     anything.
  5. **Pin the new retention floor.** `measure-extraction` now reports
     `headline reproduced: false` because its expectations are the OLD 52.2%/17.0%/52.0%/
     85.7% figures. Update them to the post-rebuild values so the ratchet is live rather
     than inert - a check nobody can see fail is not a check (the M16-S4 precedent).
  Declared files plus honest `RAN:`/`NOT RUN:` on every one; per D9 grep the consumers of
  citation `quoted_text` before declaring. ASCII, `git diff --check`, module-form
  `validate 2025`, real preflight with `legacy_mined` reported explicitly (expect **394**),
  and `check_citation_integrity` reported explicitly with the strict number. No
  `--basetemp`. ONE local commit; no push.
  Stop conditions: any citation that cannot be re-derived and verified (report it, leave it
  untouched); any need to change a `citation_id`, the rebuilt text, geometry, field maps,
  verdicts, or graph semantics; or a quota/environment failure.

- **[DONE `2b08048`, rebuild Architect-verified; gate change returned as S2b] M20-S2 TASK - DETERMINISTIC TEXT REBUILD (Architect, Claude Opus 5, 2026-07-28).**
  Read `plans/PHASE_M20.md` FIRST (canary: **Ground Truth**), then
  `plans/M20_FORM_EXTRACTION_EXPERIMENT.md` sections 1, 6b, and 6c. **This step is the
  CONTENT half only. Do NOT attempt structure, association, or OCR - S3 and S4 own those.**
  Read the ledger: **D4** (hermetic tests), **D6** (module-form CLIs), **D8** (promoted
  artifact values are contracts - grep consumers before renaming), **D9** (run the tests
  that PROJECT changed content, not just the ones you wrote), **D10/D11** (empty expected
  results are findings; findings must be persisted), and the exact RAN/NOT RUN rule.
  **THE RISK, READ IT TWICE.** This step changes `.cache/raw/<year>/*.txt` for all 16 forms,
  and that file is what `check_citation_integrity` validates FORM citations against. The
  existing citations were derived from the LOSSY text, so some may no longer verify.
  **`check_citation_integrity` is the gate that matters this round** - report it explicitly,
  before and after. The current baseline is **36 pre-existing mismatches** (20
  `instructions_form_1040_2025` hand-authored A9 scaffolding, 15 `instructions_schedule_d_2025`,
  1 `schedule_d_2025`); that number must not grow. A citation that stops verifying is a
  FINDING to report with its id, never a citation to quietly edit or drop.
  1. **Emit a COMPLETE verbatim text layer.** No row dropped, no token discarded. Today
     `_rows_from_words` (`render_form.py:96-115`) throws away every token before a detected
     anchor and drops anchorless rows entirely; that is the 52.2% loss.
  2. **Separate the anchor index from the content.** The line-anchor index must POINT INTO
     the text, never consume it. Anchor detection and text emission are two jobs.
  3. **Map non-ASCII, never delete it.** `_ascii_normalize` (`render_form.py:201`) is
     `encode("ascii", errors="ignore")`, which deletes the separator and welds the
     neighbours: `aren't -> arent`, `employee's -> employees`, `Treasury-Internal`. Exactly
     6 distinct non-ASCII characters exist across all 16 forms (309 occurrences): U+2019
     (170), U+2014 (79), U+2022 (28), U+201C/U+201D (14 each), U+2013 (4). **The correct
     mapping already exists in this repo** - `_normalize_punctuation` in
     `citation_check.py:216` handles 5 of the 6 (add the bullet). Promote it to a shared
     module and use ONE table everywhere; `render_ocr.py` has the identical defect.
     Anything unmapped after that is a named finding, not a silent drop.
  4. **Ratchet.** Per-document text retention reported via the S1 `measure-extraction`
     command, before and after. Baseline mean **52.2%**; target ~100%. It only moves up.
     **Also fix the S1 harness tokenizer**, which splits currency on the comma
     (`$1,000` -> `$1` + `000`) and makes its disagreement counts untrustworthy.
  5. **Do NOT change** widget geometry, field maps, addresses, bindings, verdicts, graph
     semantics, or any citation id.
  Declared files plus honest `RAN:`/`NOT RUN:` on every one. **Per D9, grep for consumers of
  the stored text before declaring your list** - `check_citation_integrity`,
  `tax_graph/extract/inputs.py`, and `tax_graph/output/structural_checks.py` all read
  `.cache/raw/<year>/<id>.txt`. ASCII, `git diff --check`, module-form `validate 2025`, real
  preflight with `legacy_mined` reported explicitly (expect **394**), and
  `check_citation_integrity` before/after. No `--basetemp`. ONE local commit; no push.
  Stop conditions: citation mismatches rising above the 36 baseline (STOP and report the
  ids - do not edit citations to make the gate pass); any need to touch geometry, field
  maps, verdicts, or graph semantics; or a quota/environment failure.

- **[DONE `cdb209c`, Architect-verified `f1771e0`] M20-S1 TASK - COMMIT THE EXTRACTION MEASUREMENT HARNESS AND A PRODUCER-ROBUSTNESS
  CORPUS (Architect, Claude Opus 5, 2026-07-28).** Read
  `plans/M20_FORM_EXTRACTION_EXPERIMENT.md` FIRST - it is the finding this step makes
  reproducible. **This step is READ-ONLY: it changes NO promoted artifact, no citation, no
  address, no graph semantic, and no `.cache/raw/<year>/*.txt`.** It is the "read before
  write" step; S2 does the rewrite. Read the ledger: **D4** (hermetic tests, no live
  developer state), **D6** (module-form CLIs only), **D10** (an expected document that
  yields nothing is a FINDING, not silence), **D11** (findings must be persisted, and a
  promoted/derived artifact needs a committed entry point), and the exact RAN/NOT RUN
  evidence rule. D1-D3, D5, D7 are not expected on this non-workbench slice.
  **Why this exists:** the M20 numbers were produced by throwaway scratch scripts and are
  currently evidence, not a harness. Section 7 of the report says so. Until this lands,
  nobody can re-run or trust them.
  1. **Ship the measurement as committed tooling** with a module-form command. Per
     document it reports, against the PDF's own text layer as ground truth
     (PyMuPDF `get_text`):
     - **retention/recall** - word-multiset fraction of ground-truth words preserved;
     - **fabrication** - word-multiset fraction of output words ABSENT from ground truth;
     - the PDF **producer/creator** metadata, the page count, and the widget count.
     Use the exact metric definitions in the M20 report so the numbers are comparable -
     word tokens `[a-z0-9$%]+`, lowercased, multiset intersection/difference. Reproduce the
     report's headline figures (`render_form.py` mean **52.2%**; per-document
     `form_13614_c_2025` **17.0%**, `form_1040_2025` **52.0%**, `schedule_3_2025` **85.7%**)
     and SAY whether you reproduced them. A mismatch is a finding to report, not a number
     to quietly adopt.
  2. **Emit a committed snapshot report** plus a machine-readable artifact the later
     ratchet can consume. This is the first concrete metric of the coverage contract, so
     shape it to be diffable and thresholdable, not just human-readable.
  3. **Do NOT write into `.cache/raw/<year>/`.** The M20 report records the hazard: the OCR
     helper writes `<document_id>.txt` into its output dir, which pointed at the raw store
     would OVERWRITE the form text `check_citation_integrity` validates against. Any
     harness output goes somewhere else entirely.
  4. **Producer-robustness corpus (John approved).** Acquire **2-3 deliberately awkward
     forms** - a state return, a pre-2000 IRS form, and/or a flattened non-fillable PDF -
     and run all three layers against them (text via `get_text`, widgets via AcroForm,
     structure via `find_tables()`). Purpose: our 16 forms are **100% `Designer 6.5`**, so
     robustness across authoring tools is currently UNTESTED and the M20 report says so
     explicitly.
     **HARD CONSTRAINT: these are a test corpus, NOT graph content.** Do not add them to
     `config/manifest.yaml`, do not mint documents, addresses, concepts, citations, or
     geometry, and do not let them touch `graph/<year>/`. Store them under a clearly
     separate path. If that separation is awkward, STOP and say so rather than improvising.
     Report per form which layers survived; a layer that fails is the RESULT, not a
     problem to fix in this step.
  5. **Report, do not fix.** If the harness surfaces further extraction defects, record
     them as named findings. S2 owns the rewrite.
  Declared files plus honest `RAN:`/`NOT RUN:` on every one, ASCII, `git diff --check`,
  module-form `validate 2025` (must be unchanged - this step touches no graph), and real
  preflight with `legacy_mined` reported explicitly (expect **394**, unchanged). No
  `--basetemp`. ONE local commit; no push.
  Stop conditions: any need to modify `.cache/raw/<year>/*.txt`, a promoted artifact, a
  citation, or graph semantics; the robustness corpus not being cleanly separable from
  graph content; a network/acquisition failure on the awkward forms (report it and deliver
  the harness anyway - item 1 does not depend on item 4); or a quota/environment failure.

- **M18-S3b TASK - FIX THE SCHEDULE 1-A SILENT ZERO AND PERSIST THE FINDINGS (Architect,
  Claude Opus 5, 2026-07-28).** M18-S3 is ACCEPTED (`4ab507d`) - **do NOT redo the
  promotion, do NOT re-derive the 82 existing records, do NOT change a citation id.** This
  round is the two gaps its verification returned. Read the ledger: **D10 and D11 are yours
  and were logged from this exact round**; D4, D6, D8, D9 and the exact RAN/NOT RUN evidence
  rule also apply.
  1. **Schedule 1-A: find out why the miner emits nothing, then fix the miner.** The h2
     `Instructions for Schedule 1-A Additional Deductions` is in the stored HTML at `id509`,
     and an h4 `Additional Deductions From Schedule 1-A, Line 38` exists too, but
     `mine_instruction_html_file` produces ZERO sections whose parent chain names Schedule
     1-A (contexts today: Schedule 1 x58, 1040 x54, Schedule 2 x16, Schedule 3 x15).
     `_target_document_id` already has a `schedule_1a_2025` branch, so the join is not the
     problem - the sections never arrive. Diagnose it in the miner's heading tree before
     changing anything, and SAY what the structural cause was. Note Schedule 1 carries 58
     mined sections but only 12 joins; check whether 1-A content is being swallowed into the
     Schedule 1 context rather than dropped, because that changes the fix.
     If sections do materialize, promote them through the SAME verified path S3 used -
     verbatim from the stored HTML, `html#anchor` locator, `source_document_id`,
     `semantic_title` preserved. If after diagnosis the source genuinely has no per-line
     Schedule 1-A material, that is an acceptable outcome - but it must land as a recorded
     finding with the evidence, never as silence.
  2. **Persist the findings (D11).** `join_instruction_sections` already returns
     review-queue-shaped records with a `queue_id`. Write them to the review queue in the
     same round that generates them, including the 57 `unresolved_document_context`
     (worksheet-nested) and 4 `missing_canonical_address` entries. Do not suppress the
     worksheet ones because they are expected - "expected and skipped" is exactly what
     committed state should be able to tell a later reader.
  3. **Add the per-document empty-result check (D10).** For each document the join is
     expected to cover, an outcome of zero promoted sections must be an explicit named
     finding. Give it a negative test that feeds a context yielding nothing and asserts the
     finding is raised - a validator nobody can see fail is inert (the M16-S4 precedent).
  4. **Ship a committed entry point.** `promote_instruction_html` is currently reachable only
     from an ad-hoc `python -c`. Add the module-form command or tool that regenerates the
     artifact, so the promotion is reproducible from committed state the way S2b's cleanup
     tool is.
  5. **Coverage ratchet:** report addresses-with-an-instruction-citation per document before
     and after, and the corpus cell count. Today's verified baseline is **134 cells**
     (1040 59, 8949 22, schedule_1 12, schedule_2 20, schedule_3 17, schedule_d 4) with
     **schedule_1a at 0 of 101 addresses**. It only moves up.
  Tier 3 (promoted artifacts). Declared files plus honest `RAN:`/`NOT RUN:` on every one, and
  per D9 **grep the tests for anything that pins the counts you are about to change** before
  you declare your list. ASCII, `git diff --check`, module-form `validate 2025`, real
  preflight with `legacy_mined` reported explicitly, and `check_citation_integrity` reported
  explicitly - the existing 36 pre-existing mismatches are the baseline and must not grow.
  No `--basetemp`. ONE local commit; no push.
  Stop conditions: any section whose text cannot be quoted verbatim from the stored file; any
  need to change an existing citation id, the 82 promoted records, widget geometry, verdict
  emission, or graph semantics; or a quota/environment failure.

- **M17-S7 TASK - CAPTURE PAGE GEOMETRY AT EXTRACTION (Architect, Claude Opus 5,
  2026-07-27). John's call, and he is right that the current fix is inference rather than
  data.** He asked: "shouldn't we evaluate the PDFs that are brought in to get the aspect
  ratio correctly? I can imagine, for instance, legacy forms that are maybe even tied to
  punch cards or something. this seems like an easy grab, no?" It is - `page.rect` and
  `page.rotation` are already in hand the moment the extractor opens the PDF to read
  widgets.
  **CORRECTION TO THIS TASK'S ORIGINAL FRAMING (Architect, after fixing the display):
  the GEOMETRY WAS NEVER WRONG.** All 297 stored 13614-C rects match the raw PDF exactly,
  with zero page mismatches. The "crazy" display was TWO separate presentation bugs, both
  now fixed: `panes.js` positioned overlays against hardcoded 612x792 constants, and
  `styles.css` forced `.page-canvas { aspect-ratio: 612/792 }`, which letterboxed a
  landscape page inside a portrait box. **So S7 would NOT have caught either defect** - do
  not sell it as the fix for them.
  **Why it is still worth doing.** The page size is currently recovered by inference from
  the rendered PNG, which only helps the ONE consumer that renders a PNG; the fill/print
  path, exports, and any future surface still have no idea how big a page is. And the
  out-of-page-box validator below is the mechanical check that WOULD have caught a genuine
  geometry fault instead of waiting for a human to notice.
  **Measured, and it settles the design: 13614-C mixes portrait AND landscape pages inside
  a single document** - `[(612, 792, 0), (792, 612, 0)]`. Every other form is 612x792.
  So page geometry is a PER-PAGE fact, not per-document; a document-level field would still
  be wrong for 13614-C.
  1. Capture `width`, `height`, and `rotation` PER PAGE at extraction time and persist them
     in the promoted geometry artifact. Decide and state whether that is a `pages` block in
     `graph/2025/node_geometry.json` or a sibling inventory; prefer whichever keeps the
     existing per-widget entries unchanged.
  2. **Capture `rotation` too, not just the aspect ratio.** A rotated page renders correctly
     while its widget rects are in unrotated page space - the PNG-derived workaround
     silently absorbs that, but no other consumer would.
  3. Expose page dimensions through the document cells API and have `panes.js` PREFER them,
     keeping the PNG-derived value as a fallback and the 612x792 constants as a last resort.
     Do not delete the fallbacks - a document with no captured geometry must still render.
  4. Validator: every page referenced by a widget rect has captured dimensions, and no
     widget rect falls outside its page box. That second check would have caught 13614-C
     directly instead of waiting for a human to notice the display was "crazy".
  Tier 3 (promoted artifact). Declared files must include `tests/test_workbench_cells_m17.py`
  and `tests/e2e/test_workbench_v2_m17.py` (assert a landscape 13614-C page places its
  regions on-page), plus `tests/test_workbench_m15.py` (D5). Honest `RAN:`/`NOT RUN:` on
  every declared file, ASCII, `git diff --check`, module-form `validate 2025`, real
  preflight with `legacy_mined` reported explicitly. No `--basetemp`. ONE local commit; no
  push. Stop conditions: any need to change widget rects themselves (they are correct - only
  the page box was missing), verdict emission, or graph semantics; or a quota/environment
  failure.

- **M17-S6 TASK - JOHN'S FOURTH REVIEW: MAKE SELECTION POP, AND STOP LYING ABOUT
  INSTRUCTIONS (Architect, Claude Opus 5, 2026-07-27).** John is mid-review; these are his
  live findings. Frontend/projection only for items 1-3. **Item 4 is a DATA defect - do NOT
  attempt it in this round; it is scoped separately below.** Read the ledger; D1/D2/D3/D7
  apply (e2e + selection work). You run your own e2e - 600s cap.
  1. **SELECTION MUST POP, AND SURVIVE COLORBLINDNESS (John's issue 1).** "the selected
     cell in the PDF is still too subtle. it is kind of a pale yellow. For checkboxes, you
     really have to hunt! Please make it something that sticks out with contrast and is
     also apparent to someone with typical colorblindness. I want this to pop."
     The current fill is `rgba(245,190,40,.18)` - an 18% amber wash. On a 12px checkbox
     that is invisible. **Do not solve this with a different HUE - solve it with LUMINANCE
     and SHAPE**, which is what survives deuteranopia/protanopia and grayscale:
     - Raise the fill substantially (target roughly 45-60% alpha, tune by eye against both
       black form ink and the policy colors).
     - Keep the dark inner ring + white outer halo, and INCREASE the ring weight.
     - **Add a non-color locator that scales independently of the cell's size** - the
       checkbox case is the hard one, because a small target has almost no interior to
       fill. Options: an outward marker/caret anchored to the region, or a halo whose
       radius has a MINIMUM in px so tiny cells still read. Pick one and say which.
     - A brief pulse/flash on selection change is allowed and helps locate without relying
       on color at all. Must not loop forever, and must respect
       `prefers-reduced-motion`.
     Verify at a small checkbox, not just a wide currency cell - e.g. 1040
     `12a/you_as_dependent`. State in your evidence WHICH cell you checked and its size.
  2. **STOP CONTRADICTING YOURSELF ON INSTRUCTIONS (John's issue 3).** He saw
     "What the form instructions say: Not yet ingested" and, three lines below, an
     Authority block quoting `cite_instruction_form_1040_2025_line_1a`: "Enter the total
     amount from Form(s) W-2, box 1..." with `source_document_id: instructions_form_1040_2025`
     and the i1040 URL. **Instruction text EXISTS for some cells and the dossier hides it.**
     Measured: 28 cells carry an instruction citation today (1040 2, 8949 22, schedule_d 4).
     FIX: route citations whose `source_document_id` starts with `instructions_` into the
     "What the form instructions say" slot. Show "not yet ingested" ONLY when the cell has
     no instruction-sourced citation. Authority keeps the statutory/form citations.
  3. **MAKE EMPTY AUTHORITY HONEST (John's issue 4: "Why is the Authority kinda filled in
     for some cells and not at all for others?").** It is a real coverage gap, not a bug:
     **only 258 of 1921 cells (13%) carry ANY citation**, and SIX documents have ZERO -
     form_w2, all three 1099s, form_13614_c, form_2441. The UI currently renders nothing,
     which reads like a glitch. Render an explicit state that says no authority has been
     authored for this cell yet, in the same voice as the instruction placeholder, and
     surface the per-document citation coverage next to the existing policy counts so the
     gap is visible in aggregate rather than one blank cell at a time.
  4. **Two warts from the S5 round while you are in there:** dependents cards render
     "Dependents column First name - First name" (the `official_ref` and `display_name`
     duplicate - collapse the repetition), and the dossier puts "How this is filled" BEFORE
     "Authority" where the spec had authority first. Fix the order.
  Declared files: `tests/e2e/test_workbench_v2_m17.py` (extend for the instruction-slot
  routing and the checkbox selection treatment), `tests/test_workbench_cells_m17.py`,
  `tests/test_workbench_m15.py` (D5). Tier-1 floor, ASCII, `git diff --check`, module-form
  `validate 2025`. No `--basetemp`. ONE local commit; no push.
  Stop conditions: any need to touch promoted artifacts (item 4 below owns that), citations,
  verdict emission, or graph semantics; or a quota/environment failure.

- **M18-S3 TASK - JOIN INSTRUCTION SECTIONS TO ADDRESSES AND PROMOTE (Architect, Claude
  Opus 5, 2026-07-27). RUN M18-S2b FIRST** - S2b cleans the existing citation corpus, and
  S3 writes NEW citations; doing S3 first means auditing a moving target. Design in
  `plans/PHASE_M18.md` (S3 + the HTML-channel revision). **This is the FIRST
  artifact-writing step of M18 and is Architect-reviewed before it counts as done.**
  **What S2 already gives you (measured on the stored 1040 HTML, do not re-survey):**
  143 mined sections, every one carrying `line_tokens`; **16 carry MULTIPLE tokens** -
  `('4a','4b','4c')`, `('5a','5b','5c')` - which is the multi-line-heading expansion case;
  86 of 143 carry a `semantic_title` such as "Total Amount From Form(s) W-2, Box 1";
  blocks expose `block_type`, `text`, `source_start`, `source_end`.
  **SCOPE: the 1040 canary only** (John's decision - prove it on the richest document
  before widening). Do NOT promote for the other six acquired instruction documents.
  1. **Join** each mined section to canonical addresses on the printed line/box token,
     expanding a multi-token heading to EACH address it names. A section that matches no
     address, or matches ambiguously, **fails closed into the review queue** as a named
     finding - never a best guess.
  2. **Promote** matched sections as citation records carrying `quoted_text`, `locator`,
     `url`, `retrieved_date`, and **`source_document_id`** (194 of 297 existing citations
     have none - do not add to that pile).
     **The quoted text must be verbatim from the STORED HTML file** - never a live fetch,
     never reconstructed. `check_citation_integrity` is the gate and it has teeth; the M14
     fabricated-citations reopen is the precedent.
     **Do NOT reintroduce the S2b defect:** no `- <token>:` wrapper, no trailing repeated
     line token. If your promoted text needs cleaning after the fact, the derivation is
     wrong - fix the derivation.
  3. **Locator.** The miner currently exposes character spans but no HTML anchor id. Anchor
     ids are the stable locator that survives repagination. Either capture the section's
     anchor during mining and use it, or use page + span and SAY SO explicitly in your
     handoff entry with the reason. State which you chose.
  4. **Preserve `semantic_title` on the promoted record.** Those 86 titles are the naming
     material M19-S3b needs for line-oriented concepts; losing them here means mining twice.
  5. **Coverage ratchet:** report a named, counted coverage number - 1040 addresses with an
     instruction citation, before and after. It only moves up. Today the whole corpus has
     **28 cells with an instruction citation** (1040 2, 8949 22, schedule_d 4).
  6. Do NOT touch the workbench dossier - S4 owns surfacing, and M17-S6 already routes
     `instructions_*` citations into the instruction slot, so correctly promoted records
     appear there automatically. Verify that they do, and say so.
  Tier 3 (promoted artifacts). Declared files plus honest `RAN:`/`NOT RUN:` on every one,
  ASCII, `git diff --check`, module-form `validate 2025`, real preflight with
  `legacy_mined` reported explicitly, and **`check_citation_integrity` reported explicitly**
  - that is the gate that matters this round. No `--basetemp`. ONE local commit; no push.
  Stop conditions: a section whose text cannot be quoted verbatim from the stored file; a
  join that cannot be made unambiguous (queue it, do not guess); any need to change widget
  geometry, verdict emission, or graph semantics; or a quota/environment failure.

- **M18-S2b TASK - CLEAN THE CITATION RECORDS (Architect, Claude Opus 5, 2026-07-27).**
  This is John's issue 2 from his 2026-07-27 review, the last of his four still open, and
  it is visible on every cell that shows Authority. Read the scoped analysis immediately
  below this block, then this task.
  **The defect, measured:** 217 of 297 citations (73%) carry an extraction wrapper in
  `quoted_text` - a leading `- <token>:` and often the line token repeated at the end.
  John saw `- z: Add lines 1a through 1h 1z`, `- g: Wages from Form 8919, line 6 1g`,
  `- b: Household employee wages not reported on Form(s) W-2 1b`. Separately, **194 of 297
  citations have `source_document_id: null`** - two thirds of the corpus has no provenance.
  **THE HARD CONSTRAINT, READ IT TWICE.** Citations are verbatim-from-acquired-source and
  `check_citation_integrity` has teeth; the M14 fabricated-citations reopen is the
  precedent. **A regex strip is NOT acceptable** - it would silently produce text that no
  longer provably matches the source. RE-DERIVE each `quoted_text` from the acquired source
  document and VERIFY the result appears in that source. A citation whose text cannot be
  re-derived and verified is a FINDING to report, never a guess to promote and never a
  record to quietly drop.
  1. Re-derive `quoted_text` for the affected citations from the acquired source, removing
     the anchor wrapper because it is an EXTRACTION artifact rather than source text. Every
     result must verify against the acquired file.
  2. Populate `source_document_id` where it can be determined with certainty from the
     citation's own evidence. Where it cannot, leave it null and report the count - do not
     infer a plausible document.
  3. **Do NOT change any `citation_id`.** They are referenced from addresses and nodes; a
     re-key would orphan those references.
  4. Run `check_citation_integrity` and report its result explicitly. It is the gate that
     matters here, not the unit tests.
  5. Report a before/after count: citations with the wrapper, with null provenance, and any
     that failed re-derivation.
  Tier 3 (promoted artifacts). Declared files plus honest `RAN:`/`NOT RUN:`, ASCII,
  `git diff --check`, module-form `validate 2025`, real preflight with `legacy_mined`
  reported explicitly. No `--basetemp`. ONE local commit; no push.
  Stop conditions: any citation that cannot be re-derived AND verified against its acquired
  source (report it, leave it untouched); any need to change citation ids, verdict emission,
  or graph semantics; or a quota/environment failure.

- **DATA DEFECT ANALYSIS (now tasked as M18-S2b above) - CITATION QUOTED_TEXT IS POLLUTED (John's issue
  2, 2026-07-27).** He saw quoted text reading `- z: Add lines 1a through 1h 1z`,
  `- g: Wages from Form 8919, line 6 1g`, `- b: Household employee wages not reported on
  Form(s) W-2 1b`. **Measured: 217 of 297 citations (73%) have a leading `- <token>:`
  extraction wrapper, and many also carry the line token repeated at the end.** This is the
  same OCR anchor-split family that M16-S2 fixed for `z` -> `1z`, baked into the promoted
  citation records. Also found: **194 of 297 citations have `source_document_id: null`** -
  a provenance gap on two thirds of the corpus.
  Why this is NOT a quick strip: citations are verbatim-from-acquired-source and
  `check_citation_integrity` has teeth (the M14 fabricated-citations reopen is the
  precedent). The wrapper is an extraction artifact rather than source text, so the fix is
  to RE-DERIVE `quoted_text` from the acquired source and verify each one still matches -
  never a regex strip applied blind. Sequence it with M18-S3, which is already going to
  touch citation authoring, or as an M16-S5 precursor. Tier 3.

- **[DONE `a32e021`, Architect-verified live] M17-S5 TASK - CLOSE JOHN'S RETURNED UI ISSUES
  2, 3, AND 4 (Architect, Claude Opus 5,
  2026-07-27). John is waiting on this to do his next UI review, so it is the priority
  after main is green.** Frontend + projection only: NO promoted-artifact change, NO graph
  change, NO verdict change. Read the ledger; **D1, D2, D3, and D7 all apply directly** -
  this is the round type that produced them (Playwright e2e + scroll/selection work).
  Your cap is 600s, so **you run your own e2e** - do not declare a file you then skip.
  **Background:** John reviewed the live UI on 2026-07-26 and returned four issues. Issue 1
  (the Dependents table showing 1 cell of 41) is FIXED by M19 - the corpus is now 1921/1921
  cells with 0 hidden, and 8949 went from 18 to 202. Issues 2-4 were never scheduled
  because the work pivoted to M19 addressing. Close them now.
  1. **Issue 2 - selection needs a FILL, not just a ring.** John: "I want the
     highlighted/selected cell to have some kind of colored fill. It still isn't as visible
     as I'd like." The current treatment is ring-only (`styles.css` `.official-region.pinned`,
     line 86) because the Architect over-corrected away from a hue collision with
     `.official-region.policy-unsupported` (line 84, `var(--danger)`). Add a translucent
     fill wash (roughly 15-20% alpha) UNDER the existing double ring. Alpha over the policy
     color keeps both readable, so selection still cannot be confused with a policy state.
     Keep a non-color weight cue so it survives grayscale.
  2. **Issue 4 - river cards must LEAD with the line number.** John: "why don't you have the
     number 33 leading this header? or even the section and then the line number? These are
     humans doing this review." `river.js` line ~144 renders `display_name` first and puts
     `official_ref` in a breadcrumb (line 141). Flip it: the card header reads
     `33 - Add lines 25d, 26, and 32`, with the section as a smaller kicker where one
     exists. Same for the selected-cell heading in the dossier (line ~88). Where a cell has
     no printed line token, degrade gracefully - do not print a bare separator.
  3. **Issue 3 (frontend half) - order the dossier for a HUMAN and drop the jargon.**
     John: "it is all in an order that would make sense to you, not a person... Put yourself
     in my shoes!" and, on the current labels, "what is Obtained: not authored? what is 'no
     mapping authored'? this makes no sense to me." Those labels are the Architect's, and
     they describe OUR pipeline state rather than anything about his return. Rebuild
     `renderDetail` order to: **(a)** printed label, large; **(b)** [PLACEHOLDER - M18-S3
     fills this] what the form's instructions say for this line; **(c)** governing authority
     - the citation's quoted text; **(d)** how this gets filled, in plain English
     ("computed by the graph from lines 25d, 26, 32" / "nobody has mapped this yet");
     **(e)** collapsed by default: address id, concept id, AcroForm field, rect, node id,
     artifact provenance. Render (b) as an explicit "not yet ingested" state - do NOT hide
     the slot, John should see where it will land.
  4. **Surface the new M19 data while you are in there:** a cell that is one occurrence of a
     repeatable concept should say so plainly ("Dependent 3 of 4", "W-2 Box 12, copy A,
     row 3") using the `occurrence` axes M19-S4 added. This is new information the dossier
     has never shown.
  **Do NOT rename any enum in a promoted artifact** - relabel in the UI only. That is the
  M17-S4 ruling and it still stands; M16-S5 owns the enum.
  Declare and RUN: `tests/e2e/test_workbench_v2_m17.py` (extend it for the fill and the
  line-number header), the fast cells file, and `tests/test_workbench_m15.py` (D5).
  Tier-1 floor, ASCII, `git diff --check`, module-form `validate 2025`. Run pytest plainly -
  no `--basetemp`. ONE local commit; no push.
  Stop conditions: any need to touch promoted artifacts, verdict emission, or graph
  semantics; or a quota/environment failure.

- **[DONE `94a2fe2`, Architect-verified] M19-S4b TASK - FIX THE DEPENDENTS FILL REGRESSION
  (Architect,
  Claude Opus 5, 2026-07-27).** Do this BEFORE any further M18 work. **Read ledger entry D8
  in `AGENTS.md` first and state it in your checkpoint - this is your defect and you are
  fixing it, not the Architect.**
  **What happened.** M19-S4 was asked to normalize 8949 group naming. It also renamed the
  1040 DEPENDENTS group from the table token `dependents` to the row-template token
  `dependent` across `graph/2025/field_maps/form_1040_2025.yaml`. `tax_graph/output/fill.py`
  line 78 hard-compares `if repeatable.get("group") != "dependents": continue`, so every
  dependent disposition is now skipped: **zero dependent fields are written to the 1040.**
  Dependents do not print. That is filing correctness, not cosmetics.
  Evidence: CI run 30250234820 FAILED on all three interpreters -
  `tests/test_dependents_m15.py` 3 failed / 5 passed
  (`assert 0 == (1 * 4)`, `assert 0 == (4 * 4)`, and the credit-box widget absent).
  Architect bisected it: `8ef228d` 8 passed, `a72d34e` (S3a) 8 passed, `e031fd9` (S4)
  3 failed. Reproduces locally in ~31s.
  1. **Restore `group: dependents`** in the 1040 field maps. `group` names the TABLE
     (`table=dependents`), not the row template (`row_template=dependent`) - so this is
     also the semantically correct value, not merely a revert. Keep the 8949 normalization
     you did (`short_term_transactions` / `long_term_transactions`); that part was right
     and had no consumer coupling.
  2. **Fix the same inconsistency in the workbench projection** so field maps and
     `cell_inventory` agree on the group token. They currently BOTH say `dependent`; both
     must say `dependents`.
  3. **Grep before you conclude:** `grep -rn "dependents\"\|'dependents'" tax_graph/
     workbench/` and confirm every consumer of the group token agrees. Report any OTHER
     value S4 renamed that has a consumer - check the 8949 groups too, since you renamed
     those as well.
  4. **Add a regression test** that fails if a promoted `repeatable.group` value stops
     matching what `fill.py` consumes. A test that pins the CONTRACT, not just the current
     string.
  **Declared test files MUST include `tests/test_dependents_m15.py`** - the file nobody ran.
  Also run the M19 files and the workbench boundary (D5). Tier-1 floor plus ASCII,
  `git diff --check`, module-form `validate 2025`, real preflight with `legacy_mined`
  reported explicitly. Run pytest plainly - no `--basetemp`. ONE local commit; no push -
  the Architect pushes and watches CI to green, since main is currently red.
  Stop conditions: any need to change verdict emission or graph semantics; a consumer whose
  correct token is genuinely ambiguous (report it, do not guess); or a quota/environment
  failure.

- **DESIGN DIRECTION - THE GRAPH AS EXTRACTION CONTRACT FOR SOURCE DOCUMENTS (John,
  2026-07-27). Not a task yet; candidate phase after M18/M19. Captured because it is the
  answer to how real-world input forms enter the system.**
  John, on a real Fidelity consolidated 1099: "Fidelity maps the line numbers to the forms
  very reliably. But they've just gotten rid of the form nature. So... if we have the graph
  and the AI is presented with this, it could extract the info into a form (e.g., JSON)
  that could represent the data... perhaps this is the key for input forms. I've gotten W2s
  from different employers that look quite different and skip various fields."
  **THE INSIGHT: for an information return, the FORM IS JUST ONE RENDERING - the CONCEPT
  SET is the contract.** The graph does not need to recognize a payer's layout. It supplies
  the extraction TARGET, and the AI does layout-agnostic extraction into it.
  **Measured on John's actual Fidelity statement (8 pages, values never copied into the
  repo - it is live taxpayer PII):**
  - **ZERO AcroForm widgets in the entire document.** Our extraction pipeline keys on
    AcroForm field names and their rects; none of that exists in an issued statement.
  - It rolls FOUR IRS form types into one PDF (1099-DIV, 1099-INT, 1099-B, 1099-MISC),
    with **1099-DIV and 1099-INT on the SAME PAGE**, plus issuer-authored sections
    ("Realized Gain", "Summary of", "Supplemental") that are not IRS forms at all.
  - So it breaks four modeling assumptions at once: one PDF = one document; one page =
    one form; widgets exist; a document is a blank form with cells.
  - **But the box labels map 1:1 onto concepts M19 already minted:** `1a Total Ordinary
    Dividends` -> `form_1099_div/dividends/ordinary`, `2b Unrecap. Sec 1250 Gain` ->
    `.../capital_gain_distribution/unrecaptured_section_1250`. 33 distinct 1099-DIV
    concepts, each carrying its box token and semantic name. **The concept layer survives
    contact with a real payer statement; the placement layer does not.**
  **What this implies, when it becomes a phase:**
  1. **FORM DEFINITION vs ISSUED INSTANCE is a real distinction the model lacks.** We model
     blank official forms (cells, concepts, placements). A filer receives instances -
     values, from a specific payer, possibly consolidating several form types. One word for
     both today.
  2. Each `information_return` document should EMIT a canonical extraction schema from its
     concepts (concept id + box token + label + value type + optional). That is the AI's
     target and the validation contract.
  3. **Absence is NORMAL in an instance** - John's W-2 point: different employers skip
     fields that do not apply. This INVERTS the coverage invariant, which says every cell
     on a form DEFINITION must carry a policy. Definition: every cell accounted for.
     Instance: most fields legitimately absent, and absent must be distinguishable from
     zero.
  4. A consolidated statement yields MULTIPLE instances from ONE file - so extraction must
     emit a list of typed instances, not one document.
  5. Per-value provenance (payer, page, locator) so an extracted number is auditable back
     to where it was read, consistent with the witness discipline everywhere else.
  **GAP THIS SURFACED, worth fixing whenever concepts are next touched:** `value_format` is
  EMPTY on the 1099-DIV concepts, so every field falls back to `text` - including currency
  boxes and TINs. An extraction contract needs real typing (currency, tin, date, string) or
  it cannot validate what the AI returns.

- **M18-S0 TASK - DOCUMENT CLASS (Architect, Claude Opus 5, 2026-07-27). DO THIS BEFORE
  S1** - S1's depth rule keys off it. Small, schema + records + validator.
  **John's ruling (2026-07-27):** "add the doc class... i think it will pay off down the
  line since there are all manner of docs that we won't touch in this dev effort." Plus:
  the 1099 family belongs in the graph "so that the AI utilizing it has a solid
  understanding of the fields".
  **Correction to an earlier Architect claim: `document_type` ALREADY EXISTS**, is required
  by `schemas/document.schema.json`, is populated on all 17 documents, and is consumed by
  `tax_graph/intake/classifier.py`, `tax_graph/extension.py`, and `tax_graph/mcp/server.py`.
  Do NOT redefine or repurpose it - you would break those call sites.
  **The problem is that it conflates two axes:** `tax_form` (1040, 6251, 8949) vs
  `schedule` (the 7) is a SHAPE distinction that drives nothing, while `source_document`
  and `instructions` are ROLE. And 13614-C is filed as `source_document` when it is an
  intake questionnaire nobody pulls numbers from.
  1. **Add a NEW field `document_class`** alongside `document_type`, on the ROLE axis.
     Required, enum, one of:
     - `return` - the FILER COMPUTES it; the graph must justify a number it produced.
       1040, all schedules, 6251, 8949, 2441.
     - `information_return` - issued by a THIRD PARTY; the filer READS values from it.
       W-2 and the whole 1099 family. John's "data sink".
     - `instructions` - authority text.
     - `intake` - questionnaires. 13614-C moves HERE, off `source_document`.
     Leave the enum open to extension: there are "all manner of docs we won't touch in
     this dev effort" (1099-MISC/NEC/R/G/K/OID/SA/Q, 1098 family, 5498, W-2G, K-1s), and
     the point of the field is that they slot in without a remodel.
  2. Populate it on all 17 records. Keep `document_type` exactly as-is.
  3. Fail-closed validator: every document has a `document_class`; the value is in the
     enum. Wire it into `validate 2025`.
  4. **Do NOT change behavior off it this round** beyond the validator - no policy
     changes, no review-expectation changes, no call-site rewiring. Recording the fact is
     the deliverable. Note in your handoff entry where it SHOULD eventually drive
     behavior: M18 instruction depth, review expectations (an `information_return` cell is
     reviewed for EXTRACTION correctness, not computation), and population policy
     (`information_return` cells are `imported`, never `computed`).
  5. Report the 5 acquired instruction documents that have NO document record (7 acquired,
     2 modeled) as a finding. Do not author them - M18-S1 owns acquisition.
  Tier 3 (promoted artifacts). Tier-1 floor with `RAN:`/`NOT RUN:` on every declared file,
  ASCII, `git diff --check`, module-form `validate 2025`, real preflight with
  `legacy_mined` reported explicitly. Run pytest plainly - no `--basetemp`. ONE local
  commit; no push. Stop conditions: any need to change `document_type` or its call sites;
  a document whose class is genuinely ambiguous (report it, do not guess); or a
  quota/environment failure.

- **M18-S1 TASK - ACQUIRE THE HTML INSTRUCTION CHANNEL (Architect, Claude Opus 5,
  2026-07-27).** Design in `plans/PHASE_M18.md` - READ the "MAJOR REVISION 2026-07-27 -
  THE HTML CHANNEL" section FIRST; it supersedes the PDF-centric approach in the rest of
  that plan. Read the defect ledger and name applicable entries in your checkpoint.
  **Context:** the IRS publishes every instruction document as structured HTML at
  `https://www.irs.gov/instructions/<slug>` - verified by fetching `i1041si`, `i1040gi`,
  `iw2w3`. Per-line headings carry the SEMANTIC NAME (`Line 1 - Taxable Refunds, Credits,
  or Offsets of State and Local Income Taxes`), which is the exact material M19-S3b needs
  and which does not exist anywhere in our current artifacts. Anchor ids (`id111`) are
  stable citation locators. No OCR, no column-break hyphenation repair, and a consistent
  heading tree (the PDF path had 73 line anchors on the 1040 and ZERO on Schedule B).
  **Scope: the ACQUISITION CHANNEL plus a 1040 canary survey. Do NOT mine the whole
  corpus and do NOT write citations yet.**
  1. **Manifest:** add an `instruction_url` per document in `config/manifest.yaml`. The
     slug is stable across years and the CONTENT is year-specific, so this is a first-class
     field the rollover re-binder re-fetches - not a constant in code.
  2. **Acquisition:** fetch each instruction HTML into `.cache/raw/<year>/` beside the
     existing PDF, recording URL, `retrieved_date`, and a content hash, with the same
     provenance discipline as every other acquired artifact. **Citations must later verify
     against the STORED file, never a live fetch** - that is what gives
     `check_citation_integrity` something to check. Be polite to irs.gov: sequential
     fetches, no parallel hammering.
  3. **ASCII at ingest:** IRS headings use em dashes and typographic quotes. Transliterate
     on the way in or the ASCII gate bites (it is a CI gate, not advice).
  4. **1040 canary survey (READ-ONLY report, `plans/M18_S1_INSTRUCTION_SURVEY.md`):** for
     `i1040gi`, report the heading tree, how many per-line sections resolve to a line
     token WITH a semantic title, the anchor id available per section, and - critically -
     per-line coverage for **Schedule 1, Schedule 1-A, Schedule 2, and Schedule 3**, which
     have no standalone instruction PDF and are the S3b blockers. Verified present:
     `Instructions for Schedule 1...` (id108), `Lines 2a and 2b` (id113),
     `Instructions for Schedule 2...` (id165), `Lines 1a Through 1z` (id167),
     `Instructions for Schedule 1-A Additional Deductions` (id158).
  5. **Report where HTML and PDF disagree** as a FINDING. PDF stays as fallback and
     cross-check; do not silently prefer one.
  6. **Depth by DOCUMENT CLASS (John's ruling, 2026-07-27 - see the plan).** RETURN
     documents (1040, Schedules, 6251, 8949, 2441) are computed by the filer and get full
     per-line depth. SOURCE documents (W-2, 1099-DIV/INT/B) are data sinks the filer pulls
     FROM: understand them enough to IDENTIFY the form and EXTRACT each box, and no more -
     "I don't think we need to go too deeply on this." The exception that defines the
     boundary is issuer method/qualifier fields that change TAX TREATMENT: cost-basis
     method (LIFO vs FIFO on a 1099-B), covered vs noncovered, wash-sale adjustments, and
     Box 12 codes that drive a downstream form. Skip deadlines, Copy A mailing, penalties,
     e-filing thresholds. Skip 13614-C entirely. **For S1 just REPORT whether this split is
     cleanly detectable from the heading tree** - if it is not, say so rather than forcing
     it.
  No citation records, no graph changes, no promoted-artifact changes this round.
  Tests: cover the acquisition/parse helpers with a stored FIXTURE, never a live network
  fetch in a test. Tier-1 floor with honest `RAN:`/`NOT RUN:` lines for EVERY declared
  file, ASCII, `git diff --check`, module-form `validate 2025`.
  **RULE RESTATED after the S4 slip: a declared file gets `RAN:` or `NOT RUN:`. Silence is
  not a third state.** Run pytest plainly - no `--basetemp`. ONE local commit; no push.
  Stop conditions: irs.gov returning non-200 or a changed URL shape for any document
  (record it, do not scrape around it); an instruction page whose structure defeats
  heading-tree parsing (report it); any need to write citations, touch promoted artifacts,
  or change graph semantics; or a quota/environment failure.

- **[DONE `e031fd9`, Architect-verified] M19-S4 TASK - MAKE TABLES RETRIEVABLE
  (Architect, Claude Opus 5, 2026-07-26).**
  Design in `plans/PHASE_M19.md` (S4, rewritten today). **John's framing, which is the
  acceptance bar: "when we run into a table, or a table of subtables, we get clean,
  reliable and repeatable parsing and addressing... if you are asked about dependents,
  numbers, SSNs, whatever, we need to be able to pull it out of the graph
  data/metadata."** He explicitly does NOT want a theoretically perfect scheme - he wants
  practical retrieval. Read the ledger and name applicable entries; D5 applies (any
  `workbench/` change runs `tests/test_workbench_m15.py`). Tests ARE required.
  **What S3a already got right - do not regress it:** 1040 dependents resolve by slot 1-4
  across a TRANSPOSED table (PDF `RowN` = printed column, x-position = which dependent)
  and across the NESTED `Row5/Row6 -> Dependent1..4` checkbox subtable; 8949 gives 11
  contiguous rows per part. "Dependent 3" returns a complete 10-column record.
  **The defect:** form_w2 and the 1099s silently flatten their repeats. W-2 concepts
  repeat 24x (Box 12 `entry/code`, `entry/compensation_amount`) and 12x
  (`state_local/jurisdiction/*`) while carrying `repeatable: null` and
  `occurrence.kind: "singleton"`. 24 cells share one concept with no discriminator.
  `form_w2/employee/ssn` repeats across six copies, also marked singleton.
  1. **Add the fail-closed invariant first, so the bug cannot come back:** a concept
     mapping to >1 widget in a document MUST carry an occurrence discriminator. N>1 with
     `occurrence.kind: singleton` is a PARSE FAILURE. Expect it to go red on W-2 and the
     1099s immediately - that is the point.
  2. Fix W-2 and 1099-DIV/INT/B occurrences. The W-2 is copy (A/B/C/D/1/2) x row, so the
     occurrence key must carry MORE THAN ONE AXIS - this is the table-of-subtables case.
  3. **Stop overclaiming:** `row_policy: "entity_keyed"` is asserted while the real
     discriminator is `repeatable.row_slot`, a printed slot index. Say SLOT at authoring
     time and let runtime bind slot -> entity. Do not advertise an unimplemented contract.
  4. Normalize 8949 group naming - two parallel schemes exist
     (`form_8949_2025_part_i_line_1`, `table_line1_part1`) and the first embeds a line
     token, failing the never-contains test.
  5. Put the occurrence into the quotable ref: `1040/dependents/dependent[3]/ssn`,
     `w2/box12/entry[2]/code`.
  **Acceptance is a RETRIEVAL TEST, not a count.** Ship a test that pulls, by name and
  from graph metadata alone: dependent 3's full record, W-2 Box 12 line C, an 8949 row,
  and a 1099-B state row. Also hold the line: 1921/1921 cells with 0 hidden, and the
  review-unit count must not multiply (granularity stays at the concept).
  Tier 3 (promoted artifacts). Tier-1 floor plus honest `RAN:`/`NOT RUN:` lines, ASCII,
  `git diff --check`, module-form `validate 2025`, and real preflight with `legacy_mined`
  REPORTED EXPLICITLY (S3a asserted it without printing it). Citations must stay
  byte-identical. Run pytest plainly - no `--basetemp`. ONE local commit; no push.
  Stop conditions: any need to touch line-oriented forms, verdict emission, or graph
  semantics; a repeat whose axes cannot be determined structurally (report it, do not
  invent one); or a quota/environment failure.

- **[DONE `a72d34e`, Architect-verified] M19-S3a TASK - CONCEPT MINTING FOR STRUCTURED
  FORMS (Architect, Claude Opus 5, 2026-07-26).** Design in `plans/PHASE_M19.md` (S3a + the Decisions section, which is new
  and answers the three formerly-open questions). Read it, the revised spine invariant, and
  the Worker defect ledger in `AGENTS.md`; name applicable ledger entries in your
  checkpoint. **D5 applies: any `workbench/` change runs `tests/test_workbench_m15.py`.**
  Cap is 600s; you run your own app-dependent files. Tests ARE required this round.
  **SCOPE - STRUCTURED FORMS ONLY. Do NOT touch line-oriented forms** (6251, Schedules
  1/1-A/2/3/A/B/D, or the ~58 bare `amount` controls on the 1040). M19-S1 proved they have
  no semantic material to mint from, and M18 is their prerequisite. In scope: the 1040
  Dependents table, 8949 transaction columns, W-2 boxes and Box 12 rows, 1099-DIV/INT/B
  copies and state/local rows, schedule_1a's repeatable rows, and the
  `section=identity` singletons.
  1. **Mint concept ids** per the decided shape: path style
     (`form_1040/dependents/dependent/ssn`), enforcing BOTH rules with a validator, not by
     convention - the never-contains test (no line numbers, no years, no printed prose)
     and owner/role qualification (a bare `ssn` is never an address; the four dependent
     SSNs collapsing onto one address is the exemplar John raised).
  2. **Author the concept inventory as a promoted artifact** and demote the matching
     address records to PLACEMENTS carrying `concept_id` plus the printed line/box token.
     Keep `logical_key` as the compatibility bridge and populate `aliases` from it -
     `aliases` is currently empty across all 1470 addresses and is the mechanism that
     makes this survivable.
  3. **Occurrence contract for repeatable rows.** Row identity is the ENTITY, never the
     slot index. Define it so the four Dependents rows are occurrences of one concept.
     **Review granularity stays at the CONCEPT** - one review per column, with row widgets
     rendered as instances. Closing this gap must NOT multiply the review queue.
  4. **Fix `workbench/cell_inventory.py:109`** so row-template widgets surface as
     instances instead of being dropped as containers. Acceptance: the 434 previously
     hidden controls become visible and counted (8949 184/202, w2 132/272, 1040 40/199,
     1099-DIV/INT/B 24 each, schedule_1a 6), the 1040 Dependents table is fully
     reviewable, and the per-document cell counts rise by exactly that delta - explained,
     not drifting.
  5. **The 166 unaddressed widgets are OUT OF SCOPE for authoring** but must not regress.
     form_2441 (72, no registry at all) and schedule_b (56) stay reported as coverage
     gaps. Do not invent addresses for them.
  6. Cross-document facts use a `same_fact_as` edge; do not unify concepts across
     documents. Retired concepts stay in the inventory marked with the year they left.
  Tier-1 floor: declared focused files green with honest `RAN:`/`NOT RUN:` lines, ASCII,
  `git diff --check`, module-form `validate 2025`, real preflight. **This round DOES touch
  promoted artifacts, so it is Tier 3** - the Architect runs full local partitions and the
  manifest/workbench partition at verify time; expect the preflight ratchet to be
  discussed rather than assumed unchanged, and report `legacy_mined` explicitly rather
  than asserting it held. Run pytest plainly - no `--basetemp`. ONE local commit; no push.
  Stop conditions: any need to touch line-oriented forms, verdict emission, or graph
  semantics; a concept that cannot satisfy both minting rules (report it, do not force
  it); a citation whose text would change under re-keying (it must not); or a
  quota/environment failure.

- **[DONE `7b3f873`, Architect-verified] M19-S2 TASK - KILL THE POSITIONAL unit_id
  (Architect, Claude Opus 5, 2026-07-26).**
  Design in `plans/PHASE_M19.md` (S2) - read it, plus the revised spine invariant and the
  Worker defect ledger in `AGENTS.md`; name the applicable ledger entries in your
  session-start checkpoint. **D5 applies directly this round: a change under `workbench/`
  MUST run `tests/test_workbench_m15.py` locally** - it carries the import-boundary check
  that went CI-red on M17-S2. Your cap is 600s, so you run your own app-dependent files.
  **THIS ROUND DOES NEED TESTS.** John's "another set of tests is premature" applied to
  S1, where concept ids were an unaccepted proposal. S2 changes real backend behavior that
  review state depends on, so it is tested normally.
  **The bug:** `workbench/manifest.py` `_unit_id` builds
  `{queue_id}_ref_{ref_index:04d}_loc_{location_index:02d}_{object_id}` - the id means
  "the Nth thing in the queue". Insert one control upstream and every saved approval in
  `unit_reviews` silently re-points to a DIFFERENT cell. No rollover needed; it bites on
  the next manifest rebuild.
  1. Replace the derivation with a deterministic function of the unit's IDENTITY, not its
     position: `address_id` plus the review-kind/role qualifier needed to keep the 386
     known same-address/two-review-kind pairs distinct (the M17-S2 ref finding - one ref
     per ADDRESS, not per unit). **Key on `address_id`, NOT `concept_id`** - concepts do
     not exist until S3. Write it so the input can be swapped to `concept_id` later
     without changing the shape.
  2. **Units with no address (166 of 1921 widgets - all 72 of form_2441, 56 of schedule_b,
     and 38 others).** They still need an id and must NOT get a positional one. Derive
     from a stable within-year property (the AcroForm `field_name` is the obvious
     candidate) and MARK the unit as unaddressed so the gap stays visible and countable.
     Do not silently synthesize an address.
  3. **Fail-closed checks:** no two units in a document may share an id, and no id may
     contain a positional index. A collision fails closed rather than emitting a dup.
  4. **Migration - the dangerous part. Never silently re-point an existing review.** Old
     saved sessions key on positional ids. Where an old id can be mapped to its new one
     with certainty, migrate it and record the old key in `aliases`. Where it cannot,
     mark that review ORPHANED and surface it for re-review. A wrong mapping moves a human
     approval onto the wrong cell, which is worse than losing it. Fail closed.
  5. Boundary: `workbench/` must stay free of pipeline imports (stdlib + yaml +
     `workbench.refs` only). `workbench/refs.py` already has a stdlib address reader -
     reuse it rather than importing `tax_graph.addressing`.
  6. Verdicts are OUT OF SCOPE: `review_verdict.schema.json` keys on `object_ref`, not
     `unit_id`, so no emitted verdict changes. Do not touch verdict emission.
  Tests to declare and RUN (600s cap - these are yours): the workbench boundary file
  `tests/test_workbench_m15.py` (D5), plus focused coverage for determinism across two
  manifest builds, uniqueness within a document, the no-positional-index check, the
  unaddressed-unit path, and the migrate/orphan behavior. Honest `RAN:`/`NOT RUN:` lines
  for every declared file.
  Tier-1 floor: declared files green, ASCII, `git diff --check`, module-form
  `validate 2025`, real preflight unchanged at `legacy_mined=394`. The manifest is a
  SHARED SURFACE, so the Architect additionally runs the manifest/workbench partition at
  verify time. Run pytest plainly - do NOT pass `--basetemp`. Sequential pytest only.
  ONE local commit; no push.
  Stop conditions: any need to touch promoted artifacts, graph semantics, or verdict
  emission; a unit whose id cannot be made deterministic AND unique without a positional
  fallback (report it, do not paper over it); an old review that cannot be mapped with
  certainty (orphan it, do not guess); or a quota/environment failure.

- **[DONE `e17345b`, Architect-verified] M19-S1 TASK - CONCEPT INVENTORY AND FLOW-SPINE
  DERIVATION, READ-ONLY (Architect,
  Claude Opus 5, 2026-07-26).** Design in `plans/PHASE_M19.md` - READ IT FIRST, along with
  the revised spine invariant in `AGENTS.md` and the Worker defect ledger (name the
  applicable entries in your session-start checkpoint). **Your command cap is now 600s, so
  you run your OWN app-dependent and e2e files this round** - the old "declare it and let
  the Architect run it" escape hatch is retired.
  **This step changes NO artifact. It produces a module plus a report.**
  1. Derive each document's semantic FLOW - section / group / role - from structure that
     already exists: the AcroForm wrapper hierarchy the M16-S3 resolver reads
     (`tax_graph/output/field_identity.py`), the address `path` breadcrumb, and geometry
     reading order. Structure-first only: never mine labels or guess from geometry, and
     return `unresolved` rather than inventing a flow. That discipline is the M16-S3
     precedent and it holds here.
  2. Propose a CONCEPT ID per widget, applying the two rules from the plan: the
     never-contains test (no line numbers, no years, no printed prose) and
     owner/role qualification (a bare `ssn` is never an address).
  3. Emit a read-only report `plans/M19_S1_CONCEPT_REPORT.md`: proposed concept per
     control; every COLLISION (two widgets sharing a concept - the four dependent SSNs on
     the 1040 are the exemplar, and the 434 hidden row-template widgets are the bulk);
     every UNQUALIFIED concept (a role with no owner); every id failing the
     never-contains test; and per-document counts. Findings are FINDINGS - do not "fix"
     either side.
  4. Cover the 434 hidden widgets explicitly. Report them per document
     (8949 184/202, w2 132/272, 1040 40/199, 1099-DIV/INT/B 24 each, schedule_1a 6) and
     propose the concept each row-template instance would map to. Do NOT change
     `cell_inventory.py` this round - S4 owns that.
  5. Suggested home: a new read-only module (e.g. `tax_graph/output/concepts.py`) that S3
     can consume later. No call sites in validate, preflight, or the manifest.
  **NO NEW TEST SUITE THIS ROUND (John, 2026-07-26: "another set of tests is premature").**
  THE REPORT IS THE DELIVERABLE. Concept ids are a PROPOSAL until John answers the three
  open questions in `plans/PHASE_M19.md`, so tests written against them now would only be
  rewritten. Tests arrive with S3, when the shape is settled and something is actually
  promoted. Do not declare focused test files, and do not pad the round with them.
  Gates for this step, and only these: ASCII, `git diff --check`, and module-form
  `validate 2025`. Real preflight is NOT required - this step adds no call sites in
  validate, preflight, or the manifest, so it cannot move the ratchet. If you do run
  something, report it with an honest `RAN:` line as always. ONE local commit; no push.
  Stop conditions: any need to touch promoted artifacts, the workbench projection, graph
  semantics, or verdict emission; a document whose flow cannot be derived structurally
  (report it as unresolved, do not guess); or a quota/environment failure.

- **[DONE `c370359`, Architect-verified live] M17-S3R2b TASK - FIX D7, THE RIVER SCROLL
  (Architect, Claude Opus 4.8, 2026-07-25).**
  Small, surgical, and it is the fix for John's original issue 1. Read the **Worker defect
  ledger in `AGENTS.md`** first and state in your session-start checkpoint which entries
  apply - that is now a standing rule.
  1. Fix `scrollRiverUnitIntoView` in `workbench/static/river.js`. It uses `card.offsetTop`,
     which is measured from the nearest POSITIONED ancestor; `.river-list` is
     `position: static` with no positioned ancestor, so `offsetParent` is `<body>` and the
     scroll overshoots by a constant ~167px, putting the selected card ~92px ABOVE the
     visible area. Confirmed live on the 1040 at cards 0, 5, and 20 - `inView: false` every
     time. Use `getBoundingClientRect` deltas against the container (the pattern YOU already
     wrote correctly in `scrollOfficialRegionIntoView` in `app.js`), or set
     `position: relative` on `.river-list`. Prefer the rect-delta approach: it is robust to
     future layout changes. Clamp to `[0, scrollHeight - clientHeight]`.
  2. Re-check the same class of bug anywhere else you compute a scroll offset this round.
  3. Verify with `tests/e2e/test_workbench_v2_m17.py::test_form_and_river_selection_crosses_
     pages_and_keeps_selection_visible`, which already asserts the card is within the river
     rect and currently FAILS. **If the ~124s cap blocks that file, you MUST say
     `NOT RUN: <reason>` and NOT report the step complete** - do not declare it verified on a
     Node syntax check. The Architect will run it.
  Tier-1 floor: declared files with honest RAN/NOT RUN lines, ASCII, `git diff --check`,
  module-form `validate 2025`. One local commit; no push. Stop conditions unchanged.
- **[DONE `c421558`+`c370359`, Architect-verified] M17-S3R2 + S4 TASK - NAVIGATION,
  CONTRAST, AND THE CELL DOSSIER (Architect,
  Claude Opus 4.8, 2026-07-25). Source: John's live review of the S3R UI.** Full
  design in `plans/PHASE_M17.md` (steps S3R2, S4b, S4) - READ IT FIRST. Scope is
  the review PROJECTION and the frontend: no verdict-emission change, no graph
  change, and NO promoted-artifact change (field maps, addresses, bindings, and
  citations are read-only this round).
  **Sequence the round in this order - S4b first, or you cannot verify yourself.**
  1. **S4b (do first, enabler).** Split `tests/test_workbench_cells_m17.py`. The
     file imports `create_app`, whose startup preflight + manifest build makes it
     run ~157s - OVER your ~124s launcher cap. Put the pure `cell_inventory`
     projection tests (no `create_app` import) in the fast file and leave the
     app-dependent API tests in a second file. Keep the `m17` marker and the
     existing `_drafts` skip guard on both. Declare BOTH filenames in the handoff.
     You run the fast one; record the app-dependent one as Architect-side.
  2. **S3R2 - navigation (issue 1).** In `workbench/static/`: after any selection,
     scroll the selected river card into view within the RIVER's scroll container
     (`scrollIntoView({block: "center"})`) - do not scroll the page and do not
     steal focus while a note textarea has it. Then fix the cross-page dead end:
     `app.js` `_riverSelectionHandler` currently does `if (!official) return;`, so
     selecting a card for a cell on another page does nothing. Resolve the cell's
     `page` from the model and `renderReview(cell.page, cell.cell_id)` before
     selecting. Same for keyboard next/prev across a page boundary. CAREFUL:
     `renderReview` rebinds both handlers - make sure the `syncingSelection`
     re-entrancy guard cannot be left stuck `true` (a `try/finally`).
  3. **S3R2 - contrast (issue 2).** In `styles.css`, selection currently collides
     with the unsupported policy color (both red - lines 84-86). Make the selected
     ring a treatment that cannot collide with ANY policy hue: a double ring (dark
     inner + light outer halo, so it reads over black form ink and over any fill)
     plus a non-color weight cue so it survives grayscale/color-blindness. Policy
     keeps the fill/border hue; selection owns the ring. Also scroll the selected
     region into view in the center pane when it is off-viewport at the current
     zoom.
  4. **S4 - resolve citations (issue 4).** `cell_inventory._citations` returns bare
     ids. `graph/2025/citations/*.yaml` already carries `quoted_text`, `locator`,
     `url`, `retrieved_date`, `source_document_id` per `citation_id`. Load and
     resolve them (stdlib + yaml ONLY - the workbench must not import the pipeline
     package; that is the M17-S2 boundary lesson that went CI-red). Render quoted
     text + locator + source, id secondary. NEVER synthesize, paraphrase, or
     "fill in" citation text - verbatim from acquired source only.
  5. **S4 - label every datum and name its source (issue 4).** Rebuild
     `river.js` `renderDetail` into labeled groups - Identity / On the form /
     Population policy / Graph / Authority - per the PHASE_M17 S4 item 2 list, each
     field tagged with the artifact it came from. Carry through the three field-map
     fields the UI currently DROPS: `reason`, `downstream_effect`,
     `missing_capability`. Absent data renders as an explicit "not authored" state,
     never a blank line.
  6. **S4 - reframe the policy vocabulary, UI ONLY (issue 3).** Split the flat badge
     into two labeled facets: how the value is obtained (`user_entered`, `imported`,
     `copied`, `computed`, `decision_required`) vs coverage status (`unsupported`,
     `intentionally_blank`). Relabel `unsupported` to say plainly that no mapping has
     been authored yet - it is a coverage gap, NOT a statement that the filer cannot
     enter it. **STOP CONDITION: do not rename the enum values in
     `graph/2025/field_maps/*.yaml` or any promoted artifact.** That is Tier 3 across
     605 cells and M16-S5 owns it.
  7. **S4 - coverage counts.** Per-document counts by policy surfaced in the left
     rail / dashboard.
  Tests: extend `tests/e2e/test_workbench_v2_m17.py` for the navigation and ring
  behavior, and the fast cells file for citation resolution + disposition passthrough
  + per-document policy counts. Tier-1 floor before the single local commit: your
  declared focused files green, ASCII, `git diff --check`, module-form
  `validate 2025` (`.venv\Scripts\python.exe -m tax_graph.cli validate 2025`).
  Preflight and the app-dependent tests are Architect-side (the cap) - record the
  attempt honestly and stop clean rather than guessing. `.pytest_tmp` basetemp;
  sequential pytest only. ONE local commit; no push. Session budget rules apply:
  state your model/effort/indicators on first handoff touch, declare the step,
  checkpoint before every expensive phase.
  Stop conditions: any need to touch promoted artifacts, verdict emission, or graph
  semantics; a citation whose text cannot be resolved from the promoted records (do
  NOT invent it - report it); or a quota/environment failure.
- **M17-S2 TASK - QUOTABLE CELL REF (Architect, Claude Opus 4.8, 2026-07-24;
  autonomous headless round, effort High).** Design in `plans/PHASE_M17.md` (S2).
  BACKEND, PROJECTION ONLY - additive to the review manifest; no authoritative
  writes, no frontend, no verdict change, no graph/promoted-artifact change.
  1. Derive a short, human-quotable REF for each manifest unit
     (`workbench/manifest.py`), deterministically from the unit's canonical
     address (`address_id`). Requirements: ASCII only (notes and citations are
     ASCII-enforced, so no middot - use `/`, `-`, or `:` separators); short and
     readable; STABLE across runs; and UNIQUE within a document. Expose it as a
     `ref` field on each unit (it then rides through the existing entry/manifest
     API and into the session/frontend later). Suggested shape, but you decide and
     state it: a document abbreviation + the line/box token + the role, e.g.
     `sch2/4/amount` or `sch2-4-amt`. When two units would collide, append the
     address's disambiguating qualifier (copy/row) rather than a bare counter, so
     the ref stays meaningful and deterministic.
  2. Enforce uniqueness: a deterministic check (test and/or a preflight predicate)
     that no two visible units in a document share a `ref`; a collision fails
     closed rather than silently emitting a dup.
  3. Tests (declare the files; `m15` marker to match the workbench suite or a new
     `m17` - your call, state it): ref is ASCII, deterministic/stable across two
     builds, unique within each document across the real 2025 manifest, and
     reconstructs from the address (not mined from labels). Reuse the pinned
     raw-cache / `_drafts` skip guards where a test needs live artifacts.
  4. Environment: the venv now grants `CodexSandboxUsers` read+execute, so Flask
     and full imports should work in your sandbox - if a `PermissionError [Errno
     13]` on a venv path recurs, record it under Open for Architect (it means the
     grant did not stick or a sandbox policy blocks it) and continue with whatever
     you can run. ALWAYS use the module form for CLIs
     (`.venv\Scripts\python.exe -m tax_graph.cli ...` /
     `... -m workbench.cli ...`), never the console scripts. `.pytest_tmp`
     basetemp; sequential pytest only; background or split anything near the ~124s
     cap and record honestly if it still cannot finish.
  Tier-1 floor before the single local commit: declared focused files green,
  ASCII, `git diff --check`, module-form `validate 2025`, and real preflight
  unchanged at `legacy_mined=394`. NOTE the manifest is a shared surface, so the
  Architect will additionally run the workbench/manifest partition at verify time -
  you are not required to. One local commit; no push. Uncommitted Architect edits
  to the handoff and `plans/PHASE_M17.md` are expected; leave them, they ride in
  your commit. Stop conditions: any need to change verdict emission, graph
  semantics, or promoted artifacts; a ref scheme that cannot be made deterministic
  AND unique; or a quota/environment failure.
- **M17-S1 TASK - PER-UNIT REVIEW STATE (Architect, Claude Opus 4.8, 2026-07-24;
  autonomous headless round, effort High).** Design + mapping are in
  `plans/PHASE_M17.md` - read it first. This round is BACKEND ONLY: the mutable
  per-cell review-state layer that the redesigned UI needs. No frontend, no
  verdict-emission change, no manifest change.
  1. Extend `schemas/session_state.schema.json` with per-unit review records. A
     `unit_reviews` collection keyed by `unit_id`, each record carrying the review
     status (approved vs open - a boolean or a small enum), a free-text `note`
     (ASCII), and an `updated_at` timestamp. Keep sessions NON-AUTHORITATIVE (they
     are resume state, not verdicts) and keep the existing fields.
  2. Update `workbench/sessions.py`: `default_session` initializes an empty
     `unit_reviews`; add small deterministic helpers to set/clear a unit's approval
     and note; preserve the atomic write and ASCII/sorted-keys serialization.
  3. Expose a DERIVED progress summary (approved count / total units for the
     document) computed on READ from `unit_reviews` against the manifest unit set -
     never stored, to avoid drift. Surface it through the session GET path (or a
     small read helper the API uses); do not add a new authoritative artifact.
  4. Round-trip through `GET/PUT /api/sessions/<queue_id>` in `workbench/server.py`
     (mostly schema + default; the PUT already validates and persists the payload).
     A note or approval for a `unit_id` not in the manifest must fail closed.
  5. Tests (mark them `m15` to match the workbench suite, or a new `m17` marker -
     your call, state it): schema accepts a valid `unit_reviews`; PUT then GET
     round-trips it; approve then reopen a unit; progress count is correct; an
     unknown `unit_id` is rejected; the note persists; nothing touches verdicts,
     the graph, or the preflight ratchet.
  DECLARE your focused test files in the handoff. Tier-1 floor: those files green,
  ASCII, `git diff --check`, module-form `validate 2025`
  (`.venv\Scripts\python.exe -m tax_graph.cli validate 2025`), and real preflight
  unchanged at `legacy_mined=394`. Use `.pytest_tmp` basetemp; sequential pytest
  only; no full partitions (Tier 2 is CI on the Architect's push). One local
  commit; no push. Stop conditions: any need to change verdict emission, the
  manifest, promoted artifacts, or graph semantics; a schema that cannot stay
  backward-compatible with existing saved sessions; or a quota/environment failure.
- **M16-S4 TASK - STREAM B FAIL-CLOSED STRUCTURAL VALIDATORS (Architect, Claude
  Opus 4.8, 2026-07-23; autonomous headless round, effort High).** Scope: the
  validators, focused tests, and a READ-ONLY corpus report. They FLAG this round;
  they are NOT wired as hard gates (see the ruling below).
  1. Implement the four structural validators from `plans/PHASE_M16.md` Stream B,
     consuming the S3 resolver (`tax_graph/output/field_identity.py`):
     a. **Heading integrity** - a heading/section/concept node may not own an
        amount cell.
     b. **Line coverage** - every printed amount line resolves to exactly one node
        OR carries an explicit out-of-profile disposition.
     c. **Total presence** - a form total present on the PDF has a node or is
        explicitly marked out-of-profile; never absent-and-unaccounted.
     d. **Line-identity triangle** - the node's bound line must equal the widget's
        resolver-derived line.
     Each finding is a structured, review-queue-shaped record (document, control,
     validator, observed vs expected, evidence) - never a silent pass and never a
     bare boolean. Suggested home: a new module (e.g.
     `tax_graph/output/structural_checks.py`) exposing a function
     `validate_field_maps` can call LATER; do not call it from there yet.
  2. **RULING - flag, do not enforce, this round.** The S3 report shows large
     honest unresolved blocks (8949 table columns, W-2 box templates, 13614-C
     wrapperless fields). Wiring these validators into `validate 2025` or preflight
     as hard failures now would red the floor on defects that S5 artifact
     regeneration is meant to fix. So: no call sites in `validate`, preflight, or
     the manifest this round; `validate 2025` and preflight must stay green and the
     ratchet must stay at `legacy_mined=394`.
  3. Focused tests with Schedule 2 Part I as the exemplar: the validators MUST flag
     today's real defects - the line-1 heading owning `f1_15`, the missing line-1z
     total node, and the far-right column line-identity mismatches. Prefer inline
     fixtures; any raw-cache read uses the ROOT-anchored skip-if-missing guard.
  4. Read-only corpus report `plans/M16_S4_VALIDATOR_REPORT.md`: run the validators
     over the promoted 2025 artifacts and count findings per document per validator,
     with exemplar rows. This is the S5 work list. Findings are FINDINGS - do not
     "fix" either side, and change no promoted artifact.
  5. Tier-1 floor per the amended standing rule: DECLARE your focused test files in
     this handoff, run them plus fast gates (ASCII, `git diff --check`,
     `validate 2025`, real preflight unchanged at `legacy_mined=394`). Use
     `.pytest_tmp` basetemp; sequential pytest only; no full partitions (Tier 2 is
     CI on the Architect's push). If a command exceeds your launcher cap, record the
     attempt and stop clean - the Architect completes it.
  6. Stop conditions: any need to touch promoted artifacts, graph semantics, or the
     M16-S1 fixture (it stays strict-xfail); a validator that cannot be made
     deterministic; or a quota/environment failure. Stop, record under Open for
     Architect, update the BALL. Exactly one local commit; no push. Session budget
     rules apply.
- **SCHEDULE 2 RULING + PIPELINE PIVOT (2026-07-21; John decided "pause campaign, fix
  pipeline") - the reason M16 exists.** Verified independently against
  `.cache/raw/2025/schedule_2_2025.fields.json` (raw AcroForm rects), MCP `get_node`, and
  citations:
  1. **CONFIRMED extraction/promotion defect, broader than one cell.** `f1_15` (page 1,
     x504-576 y468-480) is LINE 4 Self-employment tax: the PDF groups the row's controls
     under a wrapper named `Line4_ReadOrder`, and its checkboxes `c1_3/c1_4/c1_5` carry
     Form `4361`/`4029` (the SE-tax exemption boxes). Yet the field map binds `f1_15` to
     `schedule_2_2025_part_i_line_1` as `user_entered` currency - and that node is a bare
     heading (citation `cite_span_..._0004`: "- 1: Additions to tax:"). The
     mis-attribution spans the whole Part I far-right column: `f1_13` (really line 3) is
     labeled "Line 1z - line 17 ... 3"; `f1_11` is the line 1z total; the Line 4 exemption
     boxes are all labeled "Line 1". There is NO `line_1z` node though the form has one.
  2. **CONFIRMED clean single-cell shift.** Line 17z binds to `f2_21` (the line 18 total
     cell); its true amount cell is `f2_20`. Same family as the Schedule 1 8z->9 shift.
     NOT applied by hand - it rides along when the resolver reprocesses Schedule 2.
  **DECISION (John):** stop hand-authoring forms one at a time; build the structure-first
  field-identity resolver plus fail-closed structural validators. This is rollover seam 5 /
  guiding invariant 6 pulled forward, not a detour.
- **FORMS-PIPELINE END-STATE PINNED (2026-07-20, at John's direction):** the desired
  end-state is a valid, reliable forms pipeline into the tax graph - yearly IRS document
  updates via the rollover re-binder, user-brought forms via the extension harness - never
  recurring per-form hand transcription. The A9 campaign's hand authoring was a bounded
  one-time recovery whose outputs are the re-binder's ground-truth corpus. Pinned in THREE
  places: guiding invariant 6 and Year-rollover seam 5 in `docs/engineering-plan.md`, and
  A9 contract item 6 in `plans/PHASE_M15.md`. Hand-authoring beyond the retired A9 list is
  a STOP condition, not a precedent.
- **DEFECT-LEDGER RULE (2026-07-25, at John's direction).** John: "I would prefer to force
  Codex to take notice of its errors in the instructions." Recurring Worker defects are now
  pinned in the **Worker defect ledger in `AGENTS.md`** (canonical, Architect-owned, and NOT
  pruned at phase close - unlike this handoff). Every Worker session: read the ledger BEFORE
  declaring a step, and name in your session-start checkpoint which entries apply to what you
  are about to write. Repeating a ledger defect is a process failure to be reported as such,
  not quietly fixed by the Architect. Paired hard rule, also in `AGENTS.md`: for EVERY declared
  focused test file state `RAN: <command> -> <result>` or `NOT RUN: <reason>`; an unverified
  declared file means the step is NOT complete; never declare a file you already know the cap
  prevents you from running - say so up front so the Architect authors or runs it. Node syntax
  checks are not test evidence. WHY THIS EXISTS: across M17-S3 and M17-S3R2 the Worker's app
  code was CORRECT both times and every defect was in an e2e file it could not execute, which
  the Architect then silently fixed - so the Worker never learned. Ledger entries D1-D6 are
  seeded from those rounds.
- **SESSION BUDGET RULES (2026-07-19, at John's direction; every Worker session):**
  (1) Your FIRST handoff touch of a session states your model, effort level, and any
  usage/quota/context indicators your environment exposes - if none are exposed, say
  exactly that. (2) Declare the single step you will attempt before starting it.
  (3) Checkpoint the handoff BEFORE every expensive phase, not only at the end - a quota
  death mid-floor must never lose recorded state. (4) If any command is rejected for quota,
  STOP immediately, record exact completed/pending verification, and do not start new work.
  (5) Do not re-run already-green partitions to "refresh" them.
- **Extension-iteration backlog (M15-adjacent, from the pilot):** one-pass `extend` on
  math-bearing forms yields honest T0 structure without passing worksheet math; the review
  loop needs an iterate/author-in-review story. Named limitation documented in
  `docs/self-serve-extension.md`.
- **M15R hardening notes (opportunistic pickup, not blockers):** (1) duplicate widget
  bindings for one `(document_id, field_name)` are caught only by the SQLite primary key at
  compile time - add the same check to `_validate_artifacts` on the YAML load path; (2)
  node-binding cardinality per role is not validated beyond role compatibility (two `value`
  bindings to one address would pass) - add a per-role cardinality validator.

## Recent rounds (condensed; full narration in git history)
- **M16-S3 (Worker Codex Luna/High headless, Architect-verified, `0f7ce2c`):** first fully
  autonomous headless round. Resolver + focused tests (7 passed, 1 strict xfail) + the
  read-only 9-form report. Worker stopped honestly at real preflight (its launcher cap);
  Architect completed that gate, fixed a CWD-relative raw-cache test guard, and pushed.
- **M16-S2 (Worker, Architect-verified, `fc2a6c1`):** Stream A typing; local not-m15
  partition 370 passed / 6 skipped / 1 xfailed; preflight unchanged at `legacy_mined=394`.
- **M16-CI (Architect, `7087d9a`):** CI had been silently RED on every push since
  2026-07-14. Root causes: the `workbench` extra (flask/werkzeug) and `workbench-dev`
  (playwright) were never synced in CI, the sqlite artifact was never built, and tests
  requiring acquired PDFs / `_drafts` / the 2441 extension were unguarded. Fixed the
  workflow and guarded every fresh-checkout-hostile test on its TRUE dependency. First
  fully green matrix since 2026-07-14.
- **M16-S1 (Worker, Architect-verified, `17d2351`):** the Schedule 2 acceptance fixture.

## Latest verification
- **M16-S3 (2026-07-23):** Tier 1 green - focused `tests/test_field_identity_m16.py` +
  `tests/test_schedule_2_m16.py` 7 passed / 1 strict xfail; ASCII; `git diff --check`;
  `validate 2025`; real preflight 3,243 units, `legacy_mined=394` (ratchet unchanged).
  Tier 2 CI BLOCKED by GitHub billing - see the BALL.
- **M16-CI (2026-07-22):** fresh-checkout sim of the exact CI sequence green with zero
  failures (m15 68 passed / 45 skipped; not-m15 356 passed / 17 skipped); local floor m15
  113 passed / 0 skipped, not-m15 366 passed / 6 skipped / 1 xfailed; CI fully green on
  `7087d9a` (all four jobs) and on `f704968`.
- **M15R close (2026-07-15):** full suite 450 passed / 6 skipped; `pytest -m m15r` 47
  passed; ASCII, `validate 2025`, throwaway SQLite build, real workbench preflight,
  frontier rebuild, and Verification Record regeneration all green. Close commit `baa6fd5`.
- Prior phase closes: `plans/archive/PHASE_M13.md` and earlier - each with a close note.

## Resolved / superseded
- 2026-07-23: the recurring Worker Python `Access is denied` - RESOLVED by the
  in-workspace interpreter rebuild (pinned under Worker environment above).
- 2026-07-23: handoff pruned from 1,198 lines for the public-repo prep; session
  checkpoints, superseded BALL entries, per-round Worker narration, and the retired A9
  rulings were removed. The A9 rulings remain pinned in `plans/PHASE_M15.md`; everything
  else lives in git history.
- 2026-07-16: the open Architect M15R review request - ANSWERED (VERDICT: ACCEPTED; the
  two hardening notes are carried under From Architect).
- M15 S1 "full-suite blocker" - false alarm. M15 S2 over-scoped-queue reopen - fixed,
  re-verified, pushed.
- M14 items (packaging defects, watchdog, fabricated-citations reopen, pilot findings,
  hash-ordering rule): `plans/archive/PHASE_M14.md` header + git history.
- M13 items (S1_21 ruling, SDTW gate-defect adjudication, Option B): `plans/archive/PHASE_M13.md`.
- Pre-M13: `plans/archive/` phase plans and prior handoff snapshots.
