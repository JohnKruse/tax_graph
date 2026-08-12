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

**BALL: CODEX. The granted R1 guard reconciliation is implemented and verified below; ready for
Architect acceptance. Everything else in S101 verifies.**

**ARCHITECT RULING, 2026-08-12: THE WORKER WAS RIGHT TO STOP, AND THE R1 GUARD UPDATE IS APPROVED.**
He refused to edit a guard test without an explicit ruling and modified nothing. **That is the rule
working, not friction** - it is the same instinct that was correct at S90b.
**THE RULING: extend the R1 filter, do NOT re-baseline the count.** Add a class exclusion for
documents whose `status` is `planned`, `unresolved`, or `unsupported`, alongside the existing
`document_type == "worksheet"` clause at `tests/test_address_contract_m15r.py:70`.
**WHY A FILTER AND NOT A NEW NUMBER.** R1 freezes the *address* graph. A `planned` document carries
no nodes, no edges, and no address bindings - **the failing run proves it, because all nine other
counted kinds were byte-identical and only `documents` moved 17 -> 18.** Re-baselining would change
what the number MEANS, from "the frozen address graph" to "whatever is in the graph today."
**AND THIS IS A CLASS, NOT AN INSTANCE** - queue item 6 (out-of-corpus stubs) will add more
acquired-but-unmodelled documents, so one principled clause now prevents a per-document exception
each time.
**ARCHITECT ERROR, RECORDED SO IT IS NOT RETRIED:** the Architect first proposed replacing the
exclusion list with a positive "counts documents that carry address bindings" predicate. **It does
not work** - only **15** documents have entries in `graph/2025/bindings/nodes` while the baseline
freezes **17**, so that predicate cannot reproduce the contract. **Do not attempt it.**
**THE FLOOR, and it is the anti-erosion clause:** the contract must STILL fail when a document that
IS claimed as modelled is added or removed. **Prove it with a test**, in the same shape as
`test_planned_acroform_is_skipped_but_modelled_inventory_drift_fails`. A filter that can be widened
by setting a status flag is worth no more than the AcroForm check would have been. **Then the full
suite returns to 17 red at 951 passed.**

**FULL SUITE ON A QUIET TREE AT `db58775` (Architect, 2026-08-12): 18 failed, 951 passed, 8 skipped,
1 xfailed in 1:01:47. That is the 17-red baseline PLUS EXACTLY ONE, and the one is ours.**
`tests/test_address_contract_m15r.py::test_r1_baseline_matches_unmodified_project_graph` fails
`{'documents': 18} != {'documents': 17}`. **Nine other counted kinds are IDENTICAL** - nodes, edges,
addresses, citations, all unchanged - which is positive evidence that the `planned` Form 1116 stub is
inert exactly as intended: it adds a document and nothing else.
**DO NOT RE-BASELINE IT.** This is the same class S100 hit and the S100 ruling stands: R1 freezes the
pre-worksheet address graph, worksheet documents were FILTERED OUT of the contract rather than
re-baselined, and re-baselining would silently destroy what the contract exists to catch.
**RECOMMENDED FIX, and it makes one concept serve both gates:** the contract filters on
`document_type == "worksheet"` at `tests/test_address_contract_m15r.py:70`. **Extend the filter to
exclude documents whose `status` says they are not yet modelled** - `planned`, `unresolved`,
`unsupported` - which is the SAME predicate the AcroForm check now uses
(`tax_graph/output/field_maps.py`). A document with no address bindings has nothing to contribute to
an address contract. **FLOOR:** the R1 contract passes with 17 documents counted, Form 1116 stays in
the graph as `planned`, and the full suite returns to 17 red.

**AN EARLIER ARCHITECT SUITE RUN REPORTED 31 FAILURES AND WAS INVALID - DISCARD IT.** It was launched
against a tree the Worker was actively editing (source touched at 09:19, 09:23 and 09:33 inside the
window, with concurrent pytest sessions in `.test_tmp_s101_item*`). Three of its failures, including
`test_cli.py::test_cli_validate_succeeds`, pass in isolation. **Do not run the full suite while
another agent is working the tree.**

**S101's OFFLINE SLICE LANDED (`40b4db3`) AND THE ACQUISITION LEG IS DONE (Architect, 2026-08-12).**
The `ownership` field is on all 26 non-region entries and absent from all 19 regions; regions resolve
through their parent booklet. The tier guard is REAL - `test_tier_guard_names_both_directions`
asserts both directions against a synthetic fixture, and `validate 2025` now prints a tier reconcile
section. **Form 1116, its instructions, and Publication 514 are acquired**, hashes pinned from the
real downloads, all three loading through `load_document_input`. **`acquire --check` reports 26
documents unchanged and `changed: -` empty**, so the protected set did not move. **6251 line 8 no
longer fails with `operand_document_not_found`** - it now emits `COPY(form_1116_2025, line 17)`,
which is the right answer, and stops at `operand_inventory_unavailable` because 1116's own lines are
deliberately unmodelled. **The 42 `acquire --check` citation reds are PRE-EXISTING** - they are
against renders the same run certifies as unchanged, and the one form-sourced case,
`cite_schedule_d_line20_gate`, is a hand-authored quote that stitches across a printed branch it
skips. Not this round's.

**THE REWORK'S THREE ITEMS ARE ALL DELIVERED AND VERIFIED ON REAL DATA (Architect, 2026-08-12).**
**Item 1:** the refusal gate reads `structural_skip_reason` and the same run now reports **59
refusals, 59 reported, 0 unreported, 0 core unreported, OK** - the 17 became REPORTED, not hidden,
which is what the floor demanded. **Item 2:** `tiers.T1` is 9 and `tiers.T2` is 5, matching sections
9.2 and 9.3; the PLUS set moved to an explicit `core_plus_documents` list, `core_documents` stays 22,
and `load_core_plus_document_ids` REJECTS an id named by both a tier and the core-plus list - which
is what stops T1 being re-inflated a fourth time. **Item 3:** Form 1116 is a live document with
`status: planned` and a stub message, no field map was minted, and `validate 2025` exits 0.
**The guard rail held:** `test_planned_acroform_is_skipped_but_modelled_inventory_drift_fails` proves
a status flag cannot silence the check for a document that IS claimed as modelled.

**S100 ACCEPTED (`c7a338b`, Architect, 2026-08-11). Verified by running the corpus and the suite,
not by reading the report.**
- **19 worksheets are harvested, promoted, loadable, and DERIVED.** All 19 region documents load
  through `load_document_input` with correct parents; `graph/2025/` holds worksheet documents only
  and **no form or schedule file was touched**; `test_current_2025_graph_validates` passes.
- **DERIVATION, live over all 19: 214 lines, 201 RULED - 94%.** Schedule D Tax Worksheet **47 of
  47**, Capital Loss Carryover 13 of 13, Worksheet A 17 of 17, Standard Deduction 7 of 7. Simplified
  Method emits `DIVIDE(2,3)`, `MULTIPLY(4,12)`, `MIN(5,7)`, `SUBTRACT(2,10)`. **This is a booklet's
  HTML tables becoming executable rules with no hand authoring anywhere in the chain** - the prime
  directive, demonstrated rather than asserted.
- **Self-serve holds:** harvest mints the manifest region entry, `promote-worksheet` promotes, and
  **no Python edit is needed to add a worksheet.**
- **The region ruling held:** the face comes from promoted nodes and citations, never a re-slice of
  the parent text, and no synthetic artifact was written into `.cache/raw`.
- **A refused worksheet now reaches a human.** `pilot/review_panel.py` reads
  `worksheet-discovery*.yaml`, separates promoted from refused, and classifies advisory findings.
- **FULL SUITE: 17 failed, 941 passed, 8 skipped, 1 xfailed - the SAME 17 test ids as the accepted
  baseline, four more passing than S99.** All five contracts the round moved are reconciled.

**THE REWORK'S ONE JUDGEMENT CALL WAS MADE WELL.** R1's address contract was NOT re-baselined;
worksheet-owned objects are filtered out of it, because R1 freezes the pre-worksheet address graph
and promoted worksheets carry no address bindings. **Re-baselining would have silently destroyed
what that contract exists to catch.** The dead QDCGT id was also still hardcoded as the harvester's
default target - the Architect missed that; the Worker found and fixed it.

**THE 13 DERIVATION FAILURES ARE 4 FAMILIES AND ONLY ONE IS NEW:** `operand_not_printed` 5 (the
known promoted-node inventory gap - `1z`, `2a`, `7a` on the 1040), `operand_document_not_found` 5,
`self_reference` 2, `operand_inventory_unavailable` 1. **Prior-year documents are the new one and
are queued as item 1.**

**CARRIED FORWARD, UNANSWERED BY THE REWORK: the `REFERENCES` edges.** The harvester mints them,
promotion excludes them, and **nothing in `tax_graph/` reads that relationship**. Inert either way,
which is why it did not block acceptance - but the harvester still writes a relationship to disk
that no consumer exists for. **Promote them or stop minting them.** Queued as item 14.

**THE ARCHITECT'S READING OF WHAT IS NEXT.** The worksheet line is finished, so the queue's top is
now genuinely open. **Item 4 (mark the core set, acquire Form 1116) is John's own standing priority
and is what makes "are the core documents reliable" a measurable question at all** - today there is
no marking, and the tier list and manifest have already drifted. **Item 1 (prior-year documents)
is the newest and blocks carryforward worksheets.** Item 6 (out-of-corpus stubs) would clear
`form_w2_2025` and `form_1099_g_2025` from the derivation failures above. **Ordering is John's.**


## Current round

**M20-S101 REWORK SPECCED BY ARCHITECT (2026-08-12). THE GATE MUST FAIL FOR TRUE REASONS, THE TIER
FILE MUST SAY WHAT ITS SOURCE SAYS, AND AN ACQUIRED-BUT-UNMODELLED FORM MUST BE SAYABLE.**
**REAL-PROJECT ROUND** - full-suite floor applies. The S101 spec is in `git show c479d70`; the
offline slice is `40b4db3`. **All three items are deterministic and need no network.**

**1. THE REFUSAL GATE FAILS ON DAY ONE BECAUSE THE REPORT DOES NOT READ THE FIELD THE REASON IS
STORED IN.** Measured 2026-08-12 against `C:\tmp\m20_full\run`: **59 refusals, 42 reported, 17
unreported, 14 of them core**, so `ok` is False. **All 17 unreported rows DO record their reason** -
`structural_skip_reason`, with values `structure_duplicate_anchor` 8, `structure_non_cell_anchor` 7,
`structure_header_anchor` 2. **`_reasons()` at `pilot/maintenance_report.py:141` scans only `error`,
`review_gap`, `validation_failures`, `validation_warnings`, and `findings`**, so every structurally
skipped row prints `(no reason recorded)` and counts as a hidden refusal.
**This is the round's headline deliverable failing for a reason that is not true.** The spec said in
so many words that a gate failing on day one teaches nobody anything, and this one fails while the
pipeline is doing exactly what it should - recording why it skipped.
**FIX:** read `structural_skip_reason` in the refusal accounting. **FLOOR:** the same run reports
**core unreported 0** and `ok` True, with all 17 still listed as refusals carrying their reason -
**do not make them disappear, make them reported.** Add a test with a skipped row whose only reason
field is `structural_skip_reason`, and assert it reads as reported.

**2. THE TIER FILE CALLS 15 DOCUMENTS TIER 1 WHERE ITS SOURCE TABLE LISTS 9.** `config/document_tiers.yaml`
`tiers.T1` holds 15 ids; `docs/tax_graph_requirements.md` section 9.2 lists **9**. The six extras are
John's PLUS set - `schedule_a_2025`, `schedule_1a_2025`, `form_6251_2025` - together with
`instructions_schedule_a_2025`, `instructions_schedule_b_2025`, and `instructions_form_6251_2025`.
**`core_documents` (22) encodes John's ruling correctly and is not the problem.** The problem is that
`tax_graph/acquire/corpus.py` documents the file as the machine-readable projection of the
requirements tier tables, and for T1 it is not one. **T2 IS faithful** - 5 ids, matching 9.3 exactly.
**So the manifest and the tier file now agree while the tier file and the document it claims to
project do not: the drift moved up a layer rather than dying, which is the third recurrence this
round existed to prevent.**
**FIX, and the shape is John's call to keep cheap:** keep the tiers as the requirements doc states
them and express the PLUS set as what it is - a core-membership decision that is not a tier. **FLOOR:**
`tiers.T1` has 9 ids and `tiers.T2` has 5, matching sections 9.2 and 9.3 id-for-id; `core_documents`
still has 22; the bidirectional manifest guard still passes; **and a test fails if any tier's id list
stops matching the requirements tables.** That last clause is the whole point - without it this
recurs a fourth time.
**ALSO UNMET FROM THE ORIGINAL FLOOR, and it is a reporting gap not a mechanism gap:** the guard was
never run against the four documents that were drifting on 2026-08-11 to show it catching them
before the fix. The synthetic test does prove both directions. **Demonstrate it once on the real
four and record the output.**

**3. AN ACQUIRED-BUT-UNMODELLED FORM CANNOT BE STATED, SO MERELY DOWNLOADING A PDF TURNS THE BUILD
RED.** `validate 2025` exits 1 on `exposed AcroForm form_1116_2025 -> missing committed field map and
inventory`. **This is NOT caused by the manifest entries.** `validate_exposed_pdf_fields`
(`tax_graph/output/field_maps.py:150`) globs `.cache/raw/<year>/*.pdf` and **never consults the
manifest or the graph**; it went red on 2026-08-11 at 23:37 when the PDF was downloaded and the
manifest entries were then reverted. **Every future acquired-but-unmodelled form hits this, and
queue item 6 (out-of-corpus stubs) is the same family from the other direction.**
**JOHN'S RULING, 2026-08-12: take the status-aware fix, not the mechanical one.** The mechanical fix
- commit the box inventory with an empty `mappings` list - would work and is honest, but it encodes
"not modelled yet" as an ABSENCE. **The schema already has the vocabulary John proposed long ago:**
`schemas/document.schema.json` requires `status` with enum `supported|partial|planned|unsupported|
unresolved`, and carries `stub_message` and `not_modeled_fields`. **All 36 live documents are
`partial`, so `planned` would be its first real use** - check nothing downstream assumes otherwise
before relying on it (`tax_graph/verify/record.py:116` passes status through as an opaque string,
which is the encouraging case).
**THE DISTINCTION TO PIN SO A LATER ROUND DOES NOT COLLAPSE IT:** `unresolved` means a formula NAMES
a document we do not have - that is the existing `_stub_document` shape at
`tax_graph/extract/candidate.py:1094`, whose `stub_message` says the document must be ingested.
**`planned` means we HAVE it - acquired, rendered, hashed - and have not modelled its lines.** Form
1116 is `planned`. **Use the existing stub shape as the reference, not a new one.**
**FIX:** give `form_1116_2025` a live graph document with `status: planned` and a `stub_message`
naming what must happen, and make the AcroForm check skip documents not claimed as modelled.
**FLOOR:** `validate 2025` exits 0; the check still FAILS for a modelled document whose inventory
drifts from its widgets - **prove that with a test, because a gate that can be silenced by a status
flag is worse than no gate**; and `form_1116_2025` remains free of nodes, edges, and rules.

**OUT OF SCOPE, unchanged from S101.** Deriving or modelling Form 1116's own lines. Prior-year
documents (item 1). Out-of-corpus stubs (item 6). Publication 514's content. **And item 16, the
API-key diagnostics, which John queued on 2026-08-12 - do not fold it in here.**


**S101 WORKER STATUS (2026-08-12; three commits: `da90dbe`, `29d0362`, `1feafef`).** The three
rework items are implemented. The refusal report now reads `structural_skip_reason`; the real
`C:\tmp\m20_full\run` report is **59 refusals, 59 reported, 0 unreported, 0 core unreported,
result OK**. The requirements projection now has T1=9 and T2=5 in source-table order; John's six
additional core documents are in `core_plus_documents`, not mislabelled as a priority tier. The
live reconcile is 26 inventory / 26 manifest with no directional differences. A four-document
replay names both directions: tier-only `form_1116_2025`, `instructions_form_1116_2025`; manifest-
only `form_6251_2025`, `schedule_a_2025`. Form 1116 is a promoted document-only `planned` artifact
with a stub message and no nodes, edges, or rules. Status-aware AcroForm validation skips planned,
unsupported, and unresolved documents while still failing a partial modelled document with widget
inventory drift. `python -m tax_graph.cli validate 2025` exits 0 and reports graph integrity OK.

RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp_s101_item3';
.venv\Scripts\python.exe -m pytest tests\test_m20_s101.py -q` -> **11 passed, 1 warning**.
RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp_s101_item2';
.venv\Scripts\python.exe -m pytest tests\test_m20_s101.py tests\test_acquire_manifest.py -q`
-> **17 passed, 1 warning**.
RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp_s101_item3';
.venv\Scripts\python.exe -m pytest tests\test_m20_s101.py tests\test_field_maps_m12.py
tests\test_field_dispositions_m15.py tests\test_graph_validator.py -q -k "not validator_rejects
and not validator_catches and not validator_flags and not validator_allows"` -> **38 passed, 11
deselected, 1 warning**.
RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp_s101_item3';
.venv\Scripts\python.exe -m pytest tests\test_cli.py -q` -> **7 passed, 1 warning**.
RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp_s101_item3';
.venv\Scripts\python.exe -m pytest tests\test_graph_validator.py -q -k
"current_2025_graph_validates or current_documents_have_role_axis_classes"` -> **2 passed, 12
deselected, 1 warning**.
RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp_s101_item3';
.venv\Scripts\python.exe -m pytest tests\test_graph_validator.py -q` -> **3 passed, 11 failed,
2 warnings**. All 11 failures are the known `WinError 5` while copying protected
`graph/2025/_drafts`; no assertion failure remains in that file.
RAN: `.venv\Scripts\python.exe pilot\maintenance_report.py C:\tmp\m20_full\run --root . |
Select-String -Pattern 'refusals:|reported:|unreported:|core unreported:|result:'` -> **59 / 59,
0 / 0, result OK**.
RAN: `.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> **exit 0**, graph integrity OK.
RAN: `.venv\Scripts\python.exe tools\check_ascii.py` -> **ASCII check OK**.
RAN: `git diff --check` -> **clean**.
NOT RUN: full suite, per the S101 instruction that the Worker must not rerun it; the accepted
baseline remains the Architect's 17-red environment/artifact baseline. No provider leg was needed.

**S101 R1 CONTRACT RECONCILIATION WORKER STATUS (2026-08-12).** Implemented the granted R1
filter for `planned`, `unresolved`, and `unsupported` documents without changing the frozen
baseline. Added an anti-erosion guard proving a `partial` modelled document changes the R1 count.

RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp_r1_contract';
.venv\Scripts\python.exe -m pytest tests\test_address_contract_m15r.py -q` -> **9 passed, 1
warning**.
RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp_s101_item3';
.venv\Scripts\python.exe -m pytest tests\test_address_contract_m15r.py tests\test_m20_s101.py
-q` -> **20 passed, 1 warning**.
RAN: `.venv\Scripts\python.exe tools\check_ascii.py` -> **ASCII check OK**.
RAN: `git diff --check` -> **clean**.
NOT RUN: full suite; the S101 Worker instruction keeps that verification with the Architect because
it exceeds the Worker command cap. NOT RUN: provider leg; this reconciliation is provider-free.


## Open for Architect

**CODEX DONE; BALL IS ARCHITECT'S FOR ACCEPTANCE.** The granted R1 reconciliation is provider-free,
the focused address-contract and S101 tests are green, and the historical baseline remains 17
documents. The only remaining verification is the Architect's full-suite comparison against the
17-red baseline; the Worker must not rerun it under the S101 command-cap instruction.


## Queued (ONE LINE each - do not spec ahead)

**JOHN'S PRIORITY, 2026-08-10: get the CORE documents processing reliably.** Ordered for that.
**Every item below is a PIPELINE change - none of them is a per-cell human correction.**

1. **PRIOR-YEAR DOCUMENTS ARE A CATEGORY THE GRAPH HAS NO CONCEPT OF** (Architect, measured
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
