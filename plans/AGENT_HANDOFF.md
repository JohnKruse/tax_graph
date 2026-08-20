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

**BALL: CODEX. M20-S156 IS THE ROUND: the second-largest gap class cannot be diagnosed, because
the rejected quote is thrown away and a replay accepts the cell.**

**M20-S155 IS ACCEPTED (`a330b08`, `65333f2`, Architect, 2026-08-20), VERIFIED BY OPENING THE
RESOLVER.** `explain-cell --doc form_1040_2025 --line 31` now reports `found: true` and
`resolved_source_id:
schedule_3_2025_section_1_part_ii_other_payments_and_refundable_credits_line_15` - **a core-to-core
reference that has never resolved now resolves to a real node.** Live unresolved findings on the
three re-extracted documents went **46 -> 21**: `schedule_1a_2025` **20 -> 2**, `form_6251_2025`
12 -> 9, `schedule_1_2025` 14 -> 10. The resolver is fail-closed by construction - aliases that
would identify more than one modelled document are dropped rather than guessed.

**LINE 1e STILL DOES NOT RESOLVE, AND THAT IS NOW CORRECT.** `('form_2441_2025','26')` is absent
because 2441 has no address-backed outline in the main graph, and S151 already put it on the
frontier. **It is a declared frontier case, not a resolver defect.**

**THE RESIDUE SPLITS THREE WAYS, WHICH IS WHY IT WAS WORTH LISTING.** Of the 21 left: genuinely
unmodelled forms (`2555`, `8853`, `8889`, `5471`, `8992`, `4952`, `4797`, `3921`) - correct to leave
unresolved; **a self-reference bug** (`Form 6251` line `3` inside `form_6251_2025`, which should
resolve within its own document); and malformed extraction, where the model put a whole sentence,
an expression, or a column into the `form` field - *"Form 3921, box 4 multiplied by Form 3921, box
5"*, and a sixty-word sentence. **Only the third class is a candidate for a model-side fix.**

**THE TARGET, AND THE BASELINE IT IS MEASURED FROM (John, 2026-08-20: "get to at least 90% before I
review manually").** Read as the review-gap share, which is the number the Architect graded on:

    derived cells: 2120
    derived states: approved=0, needs_recheck=2, review_gap=591, unreviewed=1527

**591 / 2120 = 27.9% review gap. The target is <= 10%.**

**WHERE THE GAPS COME FROM, MEASURED ACROSS EVERY DRAFT.** 151 formula-cell review gaps produce
those 591 units (a gap backs about four physical units). By cause:

     83  source line is not present in the deterministic outline index
     24  micro extraction failed: quote does not match the supplied form or instruction
     20  micro extraction failed: information_return box must ...
      5  micro extraction failed: LlmUnavailable: structured-output request
      3  evidence packet is incomplete; provider call suppressed

**Of the 83, SEVENTY-FOUR name another form** and nine are bare same-document lines. **That single
cause is 55% of all gaps**, and clearing it should move roughly 320 units.

**M20-S154 IS ACCEPTED (`17ecc2d`, Architect, 2026-08-20), VERIFIED IN BOTH DIRECTIONS ON REAL DATA
BY THE ARCHITECT, NOT TAKEN FROM THE REPORT.** **290 candidates, 280 core, 27 core unsurfaced, 2
non-core** - roughly 10%, spread over twelve documents at one to seven each. **That is the shape of
a real defect distribution**, unlike the two numbers before it.

- **SURFACED:** `schedule_1_2025` line `1` returns `True`, and its marker
  `data-object="obj-nodes-schedule-1-2025-section-1-part-i-additional-income-line-1"` is in the file.
- **UNSURFACED:** `form_1040_2025` line `31`, `formula_review_gap`, *"source line is not present in
  the deterministic outline index"*. I checked its neighbours: markers exist for `-line-30`,
  `-line-32`, `-line-33`, `-line-34`, `-line-35a`, `-line-36`, and **none for 31.** The line fails
  to derive AND has no cell a reviewer can land on. **That is exactly the invisible refusal this
  gate exists to catch, and it is real.**

**WHY THE PREVIOUS MATCHER LOOKED SANE AND WAS NOT.** Form 1040 emits
`obj-nodes-form-1040-2025-root-line-30`; Schedule 1 emits section-scoped slugs. The guessed pattern
fit one document's format and not the other's. **The matcher now derives its pattern from
`review_html.object_dom_id` - the code that writes the markers** - which is what the spec demanded
and why it works.

**ONE OVERREACH, RECORDED RATHER THAN ACCEPTED SILENTLY.** The round cut candidates 310 -> 290 by
excluding every candidate whose OWNER document has `kind: instructions`. The reasoning - instructions
are evidence, not reviewable cells - is right for form-line candidates. **But the 20 dropped are 16
`frontier_refusal` at `unmodeled` and 4 `worksheet_refusal`, none of them form-line candidates.** A
refused worksheet is real regardless of which document's instructions spawned it. **The filter keys
on the owner's kind where it should key on the candidate's kind.** Queued.

**M20-S153 (`bdb1779`) IS ACCEPTED ON ITEM 1 ONLY (Architect, 2026-08-20).** The gate is out of
`pilot/` and into `tax_graph/core_refusal_gate.py`, and `doctor.py` no longer imports from `pilot`.
That is right.

**THE 213 UNSURFACED CORE REFUSALS ARE MOSTLY FALSE, AND I NEARLY REPORTED THEM AS REAL.** I checked
the by-document split first and it looked convincing - nine of the top ten documents HAVE a
`review.html`, so the refusals appeared to be genuinely invisible. **Then I opened one candidate
end to end and the claim collapsed.** Schedule 1 line `1`, `formula_review_gap`, reason *"micro
extraction failed: MicroExtractionError: quote does not match the supplied form or instruction"*.
The gate looks for:

    nodes/schedule_1_2025_root_line_1

and that string occurs **zero times** in a 1.97 MB `review.html`. `nodes/` occurs zero times.
`root_line` occurs zero times. **The real markers are slugified and section-scoped:**

    data-object="obj-nodes-schedule-1-2025-section-1-part-i-additional-income-line-1"

**Schedule 1 has 59 such line-level markers, and line `1` is among them - the cell IS on the review
surface.** So the matcher fails every form-line candidate on a format mismatch: **191 of the 213
are `formula_review_gap` (109) and `not_derivable_outcome` (82)**, both matched this way. Only
`frontier_refusal` (18) and `worksheet_refusal` (4) use other logic and may stand.

**THE SAME HOLE TWICE, FROM OPPOSITE ENDS.** S152's gate could never fail; S153's can never pass for
the commonest candidate kind. **My floor asked only for a test that CAN FAIL, and a constructed
fixture satisfied that while the real corpus went 100% red for form lines.** The floor below fixes
my omission, not just the Worker's code.

**M20-S152 (`4440009`) IS ACCEPTED ON ITEM 1 ONLY (Architect, 2026-08-20).** The duplicate core
definition is gone: **zero manifest entries carry a `core` flag**, the schema and loader support was
removed with it, and `load_core_document_ids` is the single source at 22 documents. 20 core-set
tests pass. That half is right.

**THE GATE IS VACUOUS, AND ITS OWN RESULT SAYS SO: 310 CANDIDATES, 0 UNSURFACED.** A gate that
passes everything on its first run has usually measured nothing, and this one has. The whole
surfacing test is one line of `pilot/core_refusal_gate.py`:

    surfaced=bool(reason_text and artifact.is_file())

**`artifact` is the file the candidate was just parsed out of.** Every candidate is discovered by
reading that file - `_derive_cells_report.yaml`, `review_gaps.yaml`, `frontier.yaml` - so
`artifact.is_file()` is necessarily true for anything the gate can see. **The condition therefore
reduces to "does the refusal have a non-empty reason string."**

**THAT IS NOT THE RULING.** John, 2026-08-11: *"core means ZERO UNREPORTED refusals. Non-core may
refuse, but the refusal must surface FOR REVIEW."* Surfacing is about a human finding it. The gate
as built asks whether the string exists in the file the gate itself just read, which no refusal it
can enumerate could ever fail. **The docs even state the circularity plainly:** *"A refusal is
surfaced when its reason is present in the concrete artifact that owns the candidate."*

**ALSO: PRODUCTION CODE NOW IMPORTS FROM `pilot/`.** `tax_graph/doctor.py` carries
`from pilot.core_refusal_gate import ...`. `pilot/` is exploratory work held off to the side and
lifted in later; it is not a home for a shipped gate.

**ARCHITECT ERROR, FOUND 2026-08-20 WHILE SPECCING THE GATE.** `config/document_tiers.yaml` ALREADY
held a machine-readable core set - `core_documents`, 22 entries, plus `core_plus_documents` and a
`tiers` map (`T1`, `T2`, `T4`, `review-cycle`) - and it is ALREADY wired to refusal accounting via
`load_core_document_ids`, whose own docstring reads *"Load the explicit core set used by refusal
accounting."* It is consumed today by `tax_graph/ingest/core_source_ranges.py`. **I specced S151
from the handoff ruling without checking `config/` for an existing list, so S151 built a SECOND
core definition in the manifest.** `read-the-open-list` names this exact failure.

**AND THE PRE-EXISTING LIST IS THE MORE FAITHFUL ONE.** The manifest marking is a strict subset -
17 against 22, nothing marked that the tier file lacks. The five it misses are `form_1116_2025`,
`instructions_form_1116_2025`, `instructions_form_6251_2025`, `instructions_schedule_a_2025`,
`instructions_schedule_b_2025`. **John's own 2026-08-11 ruling calls 1116 core in the same
paragraph I specced from:** *"That is a missing CORE document, not an out-of-corpus form; do not
stub it."* I read the tier sentence and not the next one.

**M20-S151 IS ACCEPTED (`bec3510`, Architect, 2026-08-20).** **17 documents carry `core: true` and
the set matches John's 2026-08-11 ruling exactly** - I recomputed it independently, symmetric
difference empty. `ownership` untouched, schema and loader updated. Focused sets 28 passed; e2e
Architect-side **11 failed, 6 passed, 1 xpassed**, the documented eleven.

**THE 2441 ENTRIES ARE DERIVED, NOT WRITTEN, AND ONE OF THEM CLOSES THIS MORNING'S LOOP.** Eight
entries, all from `frontier build` after two labels were added to `data/soi/form_id_map.yaml`. One
is `ref_cite_instruction_form_1040_2025_en_us_2025_publink1000106125_to_form_2441_2025` - **that is
the citation carried by 1040 line `1e`**, the reference that has been unresolvable all day. Status
`modeled`, `weight: null` (SOI carries no count for 2441).

**RUNNING THE BUILD SURFACED SOMETHING LARGER THAN THIS ROUND: THE REGISTRY WENT 89 -> 241 ENTRIES,
161 ADDED AND 9 REMOVED, AND ONLY 8 OF THE ADDITIONS CONCERN 2441.** The cause is structural, and
checked rather than assumed: `frontier build` derives from graph citations AND from
`graph/<year>/_drafts/<doc>/outbound_flows.yaml`, and **`graph/*/_drafts` is gitignored while
`frontier.yaml` is committed.** A committed artifact is derived from uncommitted inputs, so the
registry had been stale for days and two machines with different drafts produce different
registries from one commit. **The Architect's 06:45 regeneration of the 1040 draft is the likely
source of most of the 153 non-2441 additions - likely, not established.** This is not S151's doing;
S151 is simply the first round in a while to run the build.

**THE VERDICT STORE IS SAFE.** The two removed `rejected` entries took their status from
`graph/2025/flow-dispositions.yaml`, which is committed and re-read on every build, so human
judgement does not live in the derived file. **What vanished are the entries, because the flows
that carried them are no longer produced from the drafts.** Whether that is correct is queued as a
question.

**M20-S150 IS ACCEPTED (`7a57c13`, Architect, 2026-08-20), AND I USED THE TOOL TO VERIFY THE TOOL.**
`explain-cell --doc form_1040_2025 --line 1e` prints form face, instruction span, model record,
finding, and resolver in one call. Its resolver block is the thing that would have prevented two bad
diagnoses yesterday:

    "planned_operand": {"form": "Form 2441", "line": "26", "role": null},
    "computed_key_text": "('form_2441_2025', '26')",
    "found": false,
    "searched": "outline index"

**THE NORMALISER IS FIXED AND NORMALISED ONCE.** `re.sub(r"[^a-z0-9]+", "_", form).strip("_")`, and
the normalised value is now USED rather than computed and discarded. The assembly-level test feeds
the RECORDED operand through and asserts it resolves to `form_2441_2025_root_line_26`, so the
reference works once the form is in the index. **The new `review_gap` reads
`unresolved_source_line: form="Form 2441" line="26" -> key ...`, so quoting that string is now
quoting evidence.** 108 passed, 1 failed (line 1e); e2e Architect-side **11 failed, 6 passed, 1
xpassed**, the documented eleven.

**THE NEXT BLOCKER, OBSERVED AND NOT INFERRED.** `outline_pipeline.py:133` builds the index as
`_outline_line_index(document.document_id, outline.children)` - **from the single document being
extracted.** During a 1040 run it holds only 1040 lines, so `('form_2441_2025', '26')` cannot be
found there however well the key is normalised. **This also kills my earlier "Form 2441 has no
canonical addresses" story for a second reason: even with addresses, THIS index would not hold
them.**

**WHAT IS NOT ESTABLISHED, AND MUST NOT BE ASSUMED.** There is a `_resolve_declared_source` path at
`outline_pipeline.py:755` and a green test asserting Form 8949 cross-form claims resolve exactly, so
cross-document resolution exists SOMEWHERE. **Whether line 1e is meant to be caught by a later
stage - `link`, or declared-source resolution - is an open question, not a finding.** Queued as a
question.

**M20-S149 IS ACCEPTED (`a0c5d11`, Architect, 2026-08-20), VERIFIED BY OPENING THE CELLS AND BY
READING THE TEST DIFF.** The three renders are now:

    1a: line 1a = W-2 box 1        <- passes
    1e: line 1e = unresolved source <- FAILS, correctly
    28: line 28 = not derivable     <- passes

**LINE 1a IS CORRECT END TO END FOR THE FIRST TIME.** The model supplies `form: 'Form(s) W-2'`,
`box: '1'`; the renderer normalises it; the assertion passes **on pipeline output, with no regex and
no lowered expectation.** That chain took S147 (ask for the provenance), S148 (delete the fake), the
regeneration, and S149 (render it) - and every step of it was verified against the artifact rather
than the round's own report.

**THE NORMALISER IS GENERIC, WHICH WAS THE POINT.** `_source_label` strips a leading `Form(s)`
rather than matching the one spelling we happened to see, and capitalises only a leading lowercase
letter instead of `.title()`, so punctuation survives. Spot-checked: `Form(s) 1099-R` ->
`1099-R box 7`, `schedule_8812` -> `Schedule 8812, line 5`. `test_m20_s115.py` gained a test; none
was weakened.

**THE GUARD IS STILL RED AND THAT IS NOW A FEATURE.** It fails on line `1e` alone, with the verdict
recorded in the test beside the assertion. **A red that names one real defect is worth more than a
green that hid three stale strings.** Focused sets **26 passed, 1 failed**; e2e Architect-side
**11 failed, 6 passed, 1 xpassed** - the documented `*_m15.py` eleven, unchanged.

**THE 1040 DRAFT WAS REGENERATED 2026-08-20 06:45-06:53 ON JOHN'S INSTRUCTION.** `tax_graph.cli
extract --doc form_1040_2025 --year 2025`, **7m55s, 120 model calls, $0.40**; 161 auto-accepted, 8
to human review, 129 deterministic issues. The draft is gitignored regenerable output and is not
committed.

**M20-S147'S PIPELINE FIX IS NOW PROVEN, ON THE PATH THAT ACTUALLY MATTERS.** Line 1a's outcome
record came back from the model as `form: 'Form(s) W-2'`, `line: '1a'`, `box: '1'`, quoting *"Enter
the total amount from Form(s) W-2, box 1."* **The fields the model left empty for three days are
populated by the prompt change, with no regex anywhere near them.** Rejecting the prose-scraping
shortcut in S148 is what made this a real test.

**M20-S148 (`48c8108`, `f45a842`) IS ACCEPTED ON ITEMS 1 AND 3 (Architect, 2026-08-20).** The
quote-regex is gone from `_filer_entry_source`, which now reads structured fields only; **no test
file was touched by the implementation commit at all.** Line 1a renders `line 1a = entered by
filer` again and its guard is red, which is the honest colour with the draft unregenerated. Focused
sets **35 passed, 1 failed** (that guard). e2e Architect-side: **11 failed, 6 passed, 1 xpassed** -
the documented `*_m15.py` eleven, unchanged.

**ITEM 2'S EVIDENCE DOES NOT TEST WHAT IT CLAIMS, AND THE FIX IS UNTESTED RATHER THAN DISPROVEN.**
The round ran `experiments/derive_cells_s25.py` and reported that line 1a came back `REQUIRE_INPUT`
with empty `form`/`box`. **But that harness imports from `tax_graph.extract.cells` and takes only
`_micro_max_tokens` and `build_derivation_denominator` from the micro side** - it never runs the
union-plan path. **S147's prompt and schema change lives in `micro.py` and `outline_pipeline.py`,
which produce `micro_extraction.outcomes`, and that is the record the workbench actually reads.**
The run exercised a different prompt. Queued.

**THE LINE 1a GUARD IS STALE IN THREE PLACES, NOT ONE.** I loaded the pre-S147 module against the
same draft: `line 1e` rendered `unresolved source` and `28` rendered its question string **before
S147 and after, identically.** So `test_generated_review_renders_resolved_external_sources_and_hides
_sentinels` also expects `line 1e = Form 2441, line 26` and `line 28 = unresolved source`, and
neither has been true for some time. **Only the `1a` assertion was ever reached, which hid the other
two.** Fixing line 1a will not turn this test green. Queued.

**THE WORKER'S 600-SECOND LAUNCHER CAP BLOCKED THE LIVE EVIDENCE IN ALL THREE ROUNDS.** S146, S147
and S148 each hit `exit 124` on a 1040 re-derive. **Live `derive_cells` on `form_1040_2025` is
Architect-side from now on** - it runs 8 to 10 minutes and cannot fit. I ran them; the numbers above
are mine.

**M20-S147 (`bff7652`) IS NOT ACCEPTED AS IT STANDS (Architect, 2026-08-20). THE GUARD WENT GREEN
FOR THE WRONG REASON.** The live outcome record for line `1a` is still, unchanged:

    kind: filer_entry
    form: ''
    line: ''
    box: ''

and the review surface nonetheless renders `line 1a = W-2 box 1`. **The only thing that can produce
that string from an empty record is the new fallback in `_filer_entry_source`,** which regex-scrapes
`\bForm(?:\(s\))?\s+(?P<form>[A-Za-z0-9-]+),\s*box\s+(?P<box>[0-9]+[A-Za-z]?)\b` out of the
model's prose `quote`. I confirmed it by loading the draft and the projection together.

**THAT IS PROVENANCE INVENTED AT THE PRESENTATION LAYER, AND THIS FILE ALREADY CONDEMNS IT.** *"Do
not derive ownership from line references in prose - it scores well and is wrong in every
instance."* Worse than the red it closes: a green guard that no longer means the pipeline produced
anything. **The Worker disclosed this plainly in its own summary rather than hiding it**, which is
why the rest of the round survives.

**THE PIPELINE HALF IS CORRECT AND STAYS.** `micro.py` now admits `line` on a `filer_entry` plan,
`_validate_filer_entry_source` enforces the shape (`form` required if any field is set, `box` must
be a printed box number), and the prompt now tells the model to copy a named form, line and box
instead of dropping them. The new tests exercise the STRUCTURED path only - they pass
`{"form": "W-2", "line": "1a", "box": "1"}` explicitly - **so none of them locks in the regex and
removing it breaks none of them.**

**AND THE PROMPT CONTRACT WAS THE REAL GAP ALL ALONG.** `prompts/derive_cells.md` says
*"Information returns are the exception: W-2, any 1099 variant, and K-1 are records supplied by the
filer, so use REQUIRE_INPUT for a value copied from one of those records."* It tells the model to
call a W-2 value an input and **never asks it which W-2 box.** `filer_entry` was right; the contract
simply never requested the provenance.

**M20-S146 IS ACCEPTED (`f22f6ad`, Architect, 2026-08-19), AND I RAN THE TWO FLOOR ITEMS THE WORKER
COULD NOT.** The Worker's launcher caps at 600s; the live re-derive and the e2e set both exceed it.
Architect-side results:

| arm | derived | repaired | errored | truncated | cost |
| --- | --- | --- | --- | --- | --- |
| `high`, cap 4000 | 50 | 1 | 7 | `7a`, `12e`, `16`, `27a` | $0.0997 |
| null, cap 4000 | 50 | 3 | 5 | none | $0.0956 |
| **`high`, cap 8000 + retry** | **50** | **2** | **6** | **NONE** | **$0.1188** |

**The truncation class is gone**, which was the round's target state. e2e: **11 failed, 6 passed, 1
xpassed** - the documented `*_m15.py` eleven, unchanged. Protected set: no `graph/` or `_drafts`
path appears in the commit at all.

**THE BUDGET IS MEASURED, NOT GUESSED**, which is what ITEM 1 asked: completion tokens over 55 rows
ran min 98, median 224, P90 899, P95 2041, P99 3337, max 3520, with five rows pinned at exactly
4000. 8000 is twice the boundary; the retry doubles again. **The retry is unit-tested on both
branches** - recovery and exhaustion - with the exact budgets asserted, and a second truncation
still raises so a row errors explicitly rather than vanishing. `test_m20_s94.py` GAINED assertions;
no green guard was weakened.

**THE SIX REMAINING ERRORS ARE NOW ALL GENUINE, AND THEY ARE SIX DIFFERENT DEFECTS** - which is
exactly why a bucket named by its error message is a hypothesis, not a class:
`12e` `LOOKUP_TABLE arguments must be named leaf operands with a role`; `25c` and `27a`
`operand_document_not_found` naming `form_w2g_2025` and an earned-income-credit worksheet; `31`
`operand_not_printed: line 15 is not a printed line on schedule_3_2025`; `35a` `quote_not_verbatim`;
`38` `subtract_direction: instruction says subtract line 34 from line 38`. **Only `27a`, `31`, `35a`
and `38` persist across all three arms.**

**M20-S143 (`6dffa97`) AND M20-S144 (`3dd28d9`) ARE ACCEPTED (Architect, 2026-08-19), VERIFIED BY
RECOMPUTATION, BY OPENING THE CELLS, AND BY READING THE TEST DIFF.** S143 cleared Schedule 1 to
**60/60/0** and S144 fixed what S143 broke. My independent counts reproduce Codex's table exactly -
`form_1040` 62/54/8, `schedule_1` 60/60/0, `schedule_2` 38/36/2, `schedule_3` 29/27/2, total
**189/177/12**, unchanged by S144 - and I ran the focused sets myself: **22 passed, 1 failed**, the
failure being the documented line 1a `entered by filer` red.

**THE ROUND'S POINT IS VISIBLE IN THE ARTIFACT, NOT THE COUNT.** Schedule 2 `17z` now leads with
`section_0136__line_17z`, `projection=run_in_line`, *"**Line 17z.** Use line 17z to report any taxes
not reported elsewhere on your return or other schedules"*, with the Negative Form 8978 worksheet
retained at `[1]`. `8j` is unchanged. **The totals did not move and the defect is still gone** - the
metric is dominated by a different defect, one line below in Queued.

**THE FOREIGN-OWNER GUARD WAS NECESSARY, NOT SCOPE CREEP - I CHECKED THE SPAN MYSELF.**
`section_0144` carries `owner_document_id: schedule_3_2025`, owns `6a`-`6z`, and holds a run-in
*"**Line 6a.** The general business credit consists of..."*. Under effective width alone it scores
1 on Form 1040 line `6a` and outranks the 1040's own `section_0025` (`owner_lines` `['6a','6b']`, no
run-in), which is *"### Lines 6a and 6b / #### Social Security Benefits"*. **Schedule 3's credit
text would have become the 1040's social security instruction.** Codex found this by opening the
artifact and quoted it in the round; that is the hard rule working.

**THE TEST DIFF IS CLEAN THIS TIME.** `17z` is back in the green S142 run-in loop and the
`section_0138`-is-primary assertion is deleted. The guard was restored, not edited.

**FULL SUITE RED BASELINE IS 22, AND THE SUITE SITS AT 28.** The difference is the six broken S115
workbench cases - a defect awaiting a round, not an accepted red. Eleven `tests/e2e/*_m15.py`, plus
`test_address_campaign_m15r::test_form_8949_cross_form_claims_resolve_exactly`,
`test_field_identity_m16::test_schedule_2_raw_cache_reproduces_target_fields`,
`test_m20_s71::test_real_candidate_node_labels_use_clean_text`,
`test_review_preflight_m15::test_real_2025_preflight_passes_with_all_coverage_dimensions`,
`test_review_scope_migration_m15::test_live_queue_migration_gives_every_pending_entry_a_primary_target`,
`test_schedule_2_m16::test_schedule_2_part_i_raw_acroform_identity`,
`test_schedule_d_extraction_m9::test_schedule_d_fixture_drafts_include_schema_valid_band_tables`,
`test_extract_outline_m4::test_instruction_section_body_survives_deeper_heading`,
`test_citation_cleanup_m18::test_real_citation_corpus_has_source_verified_cleanups`, and both
`test_generated_review_m20` line 1a is red for the reason in
Queued below (W-2 box 1 versus `entered by filer`); do not silence it.**

**STILL OWED, UNCHANGED:** the S115 review contract needs a LIVE check, not a test read - six cases
die at `workbench/server.py:640` on `object_ref` and cannot be bisected because they skip without
`_drafts` and error at setup with it. **That is the surface John reviews and it has been unverified
since 2026-08-16.**

**THE CITATION RANGE BACKLOG IS APPLIED (John approved 2026-08-19).** `citation_range_patch --write`
put **78** ranges into `graph/2025/citations/instruction-form-1040-html.yaml` (71) and
`intake.yaml` (7). **Unverifiable citations 114 -> 36; checked 515 -> 593, zero mismatches, and the
bad-provenance findings stay at exactly 2** - none of the added ranges introduced one. The
protected set (`nodes`, `edges`, `rules`, `field_maps`) has an empty diff and the edit is additive:
242 insertions, 0 deletions.

**I TOLD JOHN 114 -> 14 AND THE HONEST NUMBER IS 114 -> 36. TWO CORRECTIONS I OWE.** The proposal
was **100, not 99** - the S136 follow-up (`b3050d5`) added one. And **22 of the 100 could not be
written**: they live in `graph_ext/2025/form_2441_2025/citations.yaml`, which carries a stamped
`content_hash` the loader enforces and which is **gitignored**. Writing there broke `load_graph`
closed on the first attempt; I reverted it and **proved the revert byte-identical by recomputing
the extension hash against the stamp**. The applier now defers overlay-held citations by design
rather than raising. **14 of the remaining 36 are HTML-only and no range can fix them; the other 22
are the 2441 overlay and they land in the round that retires it** - `AGENTS.md` already condemns
that overlay as a surviving special case.

**Durable findings from S128-S142 are now pinned in `PHASE_M20.md` section 4.2** - the OCR-damage
acquisition finding, the mentioning-versus-governing result, Schedule 1-A's real ceiling, and the
do-not-drop-`quoted_text` constraint. They are no longer repeated here.

## Current round

**M20-S156: A FAILURE THAT DISCARDS ITS OWN EVIDENCE CANNOT BE FIXED.**

**THE CLASS.** 24 review gaps read *"micro extraction failed: MicroExtractionError: quote does not
match the supplied form or instruction evidence"* - the second-largest cause, spread thinly across
13 documents (1 to 4 each), so it is cross-cutting rather than one document's problem.

**IT CANNOT BE DIAGNOSED FROM THE ARTIFACT, AND I TRIED.** `explain-cell --doc form_1040_2025
--line 3a` returns the form face, the instruction span and the record - and **the record does not
contain the quote that was rejected.** Only that it failed. There is nothing to compare against the
evidence.

**AND A REPLAY ACCEPTS THE SAME CELL.** `verify prompt-bench --doc form_1040_2025 --id
form_1040_2025_root_line_3a` returns:

    "quote": "Enter your total qualified dividends on line 3a.",
    decision: accepted
    why: all deterministic validations passed

That quote IS verbatim in `section_0016`. **So the recorded failure does not reproduce**, which
means these are very likely near-misses rather than fabrications - but **I am NOT asserting that,
because the rejected string was never kept.** Establishing it is ITEM 2.

ITEM 1. **Persist the rejected quote on the failure**, with the validation reason and, where
computable, the closest matching span text and the offset where the match broke. **A validation that
throws away the string it rejected is the defect; the 24 gaps are the symptom.**

ITEM 2. **Then classify the 24 with the string in hand.** Near-miss (whitespace, unicode, casing,
truncation, an ellipsis) versus genuine fabrication versus wrong span supplied. **Report counts per
class with three quoted examples**, and do not generalise from one.

ITEM 3. **Only then propose the fix**, and say plainly whether it is normalisation on our side or a
prompt change. **Do not loosen the verbatim check to make the number fall** - a citation that is not
verbatim is worthless in a graph whose value is its citations.

**LIVE CALLS ARE PERMITTED** for a targeted re-extract to capture real rejected quotes: at most
THREE documents, outside the repository root, about $0.40 each. `form_1040_2025`, `schedule_1_2025`
and `form_1116_2025` carry 3, 4 and 3 of them.

**WHAT MUST NOT HAPPEN.**
- **Do not weaken the verbatim quote check.**
- **Do not weaken, delete, or invert an assertion that is green on `main`.**
- Do not regenerate the live drafts under `graph/2025/_drafts`.

**THE FLOOR.**
- **A rejected quote persisted and shown** for a real failing cell.
- **The 24 classified**, with counts and three quoted examples.
- **A named fix with its side stated** - ours or the model's - not applied blind.
- **Focused sets green** against their known reds. **e2e is Architect-side.**
- **`check_ascii` OK, `check_diagnosis_evidence` OK**, `git diff --check` clean, protected set
  byte-identical.

### M20-S156 result

**ITEM 1 COMPLETE.** The outline-first micro validator now attaches the rejected provider
payload to `MicroExtractionError`. The outline pipeline copies it into both `micro_extraction.yaml`
failure records and `review_gaps.yaml`, including `rejected_quote`, `validation_reason`, the full
`rejected_payload`, and `closest_matching_span` with normalized quote/span offsets. The strict
verbatim predicate was not changed.

External live evidence from `C:\tmp\m20_s156_live` shows the persisted record for a real failure:

    target_cell_id: form_1040_2025_root_line_3a
    rejected_quote: Enter your total qualified dividends on line 3a. Generally, these dividends are shown in box 1b of Form(s) 1099-DIV.
    validation_reason: quote does not match the supplied form or instruction evidence
    closest_matching_span.span_id: span_form_1040_2025_0079
    closest_matching_span.span_text: if required. 3a Qualified dividends 3a b Ordinary dividends 3b
    closest_matching_span.longest_common_substring.quote_offset: 18
    closest_matching_span.longest_common_substring.span_offset: 17

The three targeted live runs persisted 2 quote failures for `form_1040_2025`, 5 for
`schedule_1_2025`, and 2 for `form_1116_2025` in their external drafts. The older 24-cell set was
classified from provider response bodies in `output/logs`, keyed by each failing target cell;
nine of those cells were independently recaptured in the three permitted live runs.

**ITEM 2 COMPLETE.** Classification of the 24 recovered rejected strings:

    near-miss: 3
    genuine fabrication: 5
    wrong span supplied or span-boundary failure: 16
    total: 24

Near-miss means the answer tracks one source passage but the supplied text has a visible
acquisition/rendering defect: `If you were self-employed or a partner, you may be able to take
this deduction.` was supplied with `deduc-` and `tion` split across the source span; the other
two are the analogous `dis-` split on Schedule 1 line 24h and the clipped `interest` on Form
1099-INT line 9. Genuine fabrication includes the current 1040 line 3a replay answer, which
stitches non-contiguous instruction sentences: `Enter your total qualified dividends on line 3a.
Generally, these dividends are shown in box 1b of Form(s) 1099-DIV.` It also includes the two
"evidence not available" refusals and the random one-character Schedule A answer. The remaining
16 are source-derived text that is absent from one supplied span, crosses adjacent spans, or is
present in the packet while the validator's result does not reproduce; examples include the
Form 1116 line 26 quote crossing spans 0134 and 0135 and the Form 1099-DIV box descriptions split
across spans 0175-0189.

The handoff's earlier claim that prompt-bench ACCEPTS the same 1040 line is not reproducible in
the current tree. The command below returned `decision: rejected` for a different response whose
quote stitches the line 3a sentence to the later box 1b sentence. That is evidence of response
instability, not permission to weaken the quote check.

**ITEM 3 COMPLETE.** The recommended fix is on our side: repair evidence-span construction and
source-text normalization before validation so one citable passage remains one span, adjacent
source fragments are joined only when their source offsets prove continuity, and line-end
hyphenation is corrected in the canonical acquired text. Do not make the validator accept
dehyphenation, punctuation repair, non-contiguous joins, or fuzzy similarity. The five genuine
fabrications remain model/prompt work after this pipeline fix; the strict check should continue to
reject them.

**EVIDENCE AND TEST STATUS.**

RAN: `.venv\Scripts\python.exe -m pytest tests\test_extract_outline_m4.py::test_rejected_micro_quote_is_carried_into_review_gap_evidence -q` -> 1 passed.

RAN: `.venv\Scripts\python.exe -m pytest tests\test_llm_attribution_m20.py -q` -> 8 passed.

RAN: `.venv\Scripts\python.exe -m pytest tests\test_m20_s113.py -q` -> 9 passed, 2 failed; known baseline failures `test_filer_entry_preserves_a_named_information_return_source` and `test_declines_are_outcomes_and_never_review_gaps` call `_record_union_non_computation` without the pre-existing required `form_aliases` argument.

RAN: `.venv\Scripts\python.exe -m pytest tests\test_extract_outline_m4.py -q` -> 21 passed, 1 failed; known baseline failure `test_instruction_section_body_survives_deeper_heading` expects heading/title spans that the current matcher returns as body only.

RAN: `.venv\Scripts\python.exe -m tax_graph.cli extract --year 2025 --doc form_1040_2025 --output-dir C:\tmp\m20_s156_live\form_1040_2025` -> auto_accepted 172, human_review 10, deterministic_issues 129; external output only.

RAN: `.venv\Scripts\python.exe -m tax_graph.cli extract --year 2025 --doc schedule_1_2025 --output-dir C:\tmp\m20_s156_live\schedule_1_2025` -> auto_accepted 182, human_review 7, deterministic_issues 38; external output only.

RAN: `.venv\Scripts\python.exe -m tax_graph.cli extract --year 2025 --doc form_1116_2025 --output-dir C:\tmp\m20_s156_live\form_1116_2025` -> auto_accepted 111, human_review 6, deterministic_issues 70; external output only.

RAN: `.venv\Scripts\python.exe -m tax_graph.cli verify prompt-bench --doc form_1040_2025 --id form_1040_2025_root_line_3a` -> decision rejected; `MicroExtractionError: quote does not match the supplied form or instruction evidence`.

RAN: `.venv\Scripts\python.exe -m tax_graph.cli explain-cell --root C:\tmp\m20_s156_live\form_1040_2025 --doc form_1040_2025 --line 3a` -> persisted `rejected_quote`, `rejected_payload`, validation reason, closest span, and offsets shown.

NOT RUN: e2e; it exceeds the launcher cap and is Architect-side.

## Open for Architect


## Queued (ONE LINE each - do not spec ahead)

- **THE INSTRUCTIONS FILTER IN THE CORE GATE KEYS ON THE WRONG THING (Architect, 2026-08-20).**
  `_is_reviewable_candidate` drops every candidate whose owner document is `kind: instructions`.
  Measured: that removes **16 `frontier_refusal` at `unmodeled` and 4 `worksheet_refusal`**, zero of
  them form-line candidates. **Only a form-line candidate is unreviewable on an instructions
  document**; a refused worksheet still needs to reach a human - see the existing refused-worksheet
  item. Key the exclusion on the candidate kind.

- **1040 LINE 31 HAS NO REVIEW CELL AT ALL (Architect, found via the gate 2026-08-20).** Markers
  exist for lines 30 and 32 through 36; there is none for 31. It is also one of the four persistent
  derivation errors (`operand_not_printed: line 15 is not a printed line on schedule_3_2025`).
  **A line that neither derives nor appears is invisible twice over.** Open it with `explain-cell`.

- **`frontier.yaml` IS COMMITTED OUTPUT DERIVED FROM GITIGNORED INPUT (Architect, 2026-08-20).**
  `frontier build` reads `graph/<year>/_drafts/<doc>/outbound_flows.yaml`; `graph/*/_drafts` is
  gitignored. **Rebuilding on 2026-08-20 moved it 89 -> 241 entries.** Either the registry should
  not be committed, or its inputs must be. **Pick one; the current arrangement makes the file's
  contents a function of whose machine ran last.**

- **TWO `rejected` OUTBOUND FLOWS DISAPPEARED IN THE REBUILD (Architect, open QUESTION 2026-08-20).**
  `flow_form_6251_2025_outbound_schedule_d_column_h_to_schedule_d_2025_line_2` and `_line_3`, both
  `status: rejected`, are absent from the rebuilt registry, along with six `modeled` Form 8949
  flows. Their disposition still exists in `flow-dispositions.yaml`. **Establish whether the source
  flows were legitimately removed or are missing, before concluding anything.**

- **IS `modeled` THE RIGHT STATUS FOR FORM 2441? (Architect, open QUESTION 2026-08-20.)** The build
  calls a target `modeled` when it appears in `graph.items("documents")`. 2441 does, yet it has no
  canonical addresses under `graph/2025/addresses/` and its objects live in the `graph_ext` overlay.
  **The status vocabulary may not distinguish "in the core graph" from "in an extension"** - which
  is exactly the distinction the core marking now makes elsewhere.

- **THE CORE GATE ITSELF: ZERO UNREPORTED REFUSALS (John's 2026-08-11 ruling; queued 2026-08-20).**
  The marking is only worth having if it is enforced - *"core means ZERO UNREPORTED refusals.
  Non-core may refuse, but the refusal must surface for review."* **Needs a definition of "refusal"
  and the stage that enforces it**; that is a round of its own, after S151.

- **THE FRONTIER'S REACH IS CAPPED BY A 12-LABEL HAND-MAINTAINED MAP (Architect, 2026-08-20).**
  `data/soi/form_id_map.yaml` is what `frontier build` can see, so any form absent from it is
  invisible to the registry no matter how often the corpus cites it. **That is a hand-authored
  bottleneck in a derived pipeline.** Ask whether the label set should itself be derived from the
  manifest.

- **REVISIT `README.md` AND THE SUPPORTING MD FILES (John, 2026-08-20).** Three jobs: **(1)** state
  the project accurately as of wrap-up; **(2)** real operating instructions for users; **(3)**
  documentation for ingesting new forms and contributions. **Today the README says nothing about
  extensions at all** - the model exists only in `docs/self-serve-extension.md`. **(3) needs
  thinking through and John has explicitly deferred execution.**

- **NON-CORE MODULARITY: HOW A CONTRIBUTOR'S FORM IS FOUND AND ADOPTED (John, 2026-08-20, execution
  deferred).** His sketch: a contributor publishes their own repo, a user opts in. **Much of the
  mechanism exists** - `tax-graph extend` writes discrete per-form graphs under
  `graph_ext/<year>/<doc_id>/`, checks collisions against the shipped graph AND other extensions,
  and `extend package` emits a deterministic ZIP. **The unsolved half is discovery and trust, not
  collision.** After core finality.

- **WHERE IS A CROSS-DOCUMENT OPERAND SUPPOSED TO RESOLVE? (Architect, open QUESTION 2026-08-20 -
  not a diagnosis.)** The micro-extraction index is single-document by construction
  (`outline_pipeline.py:133`), yet `_resolve_declared_source` exists at line 755 and
  `test_address_campaign_m15r::test_form_8949_cross_form_claims_resolve_exactly` is green. **Find
  out which stage owns cross-form resolution BEFORE proposing that line 1e be fixed anywhere.**
  Start with `explain-cell`; it now costs one command.

- **[SUPERSEDED BY M20-S150 - AND BY A DIAGNOSIS I GOT WRONG TWICE.]** I queued line `1e` as an
  outline-join failure, read off the `review_gap` string without opening
  `micro_extraction.findings`. Then I blamed the missing `graph/2025/addresses/form_2441*`. **Both
  were inferences.** The proven cause is in the round below.

- **S147'S PROMPT FIX IS UNTESTED: EXERCISE THE MICRO PATH, NOT `derive_cells_s25` (Architect,
  2026-08-20).** The change is in `micro.py` / `outline_pipeline.py`, which write
  `micro_extraction.outcomes`; the only live run so far went through `tax_graph.extract.cells`.
  Run the outline-first micro extraction over `form_1040_2025` to scratch and see whether the model
  now fills `form`/`line`/`box` for line 1a. **Architect-side: it exceeds the Worker's cap.**

- **`prompts/derive_cells.md` NEVER ASKS WHICH BOX EITHER (Architect, 2026-08-20).** It says
  *"Information returns are the exception: W-2, any 1099 variant, and K-1 ... use REQUIRE_INPUT for
  a value copied from one of those records"* and stops. The cells path has the same gap S147 fixed
  on the micro path. **Same defect, second prompt.**

- **THE LINE 1a GUARD NEEDS ALL THREE EXPECTATIONS RE-DERIVED, NOT JUST THE FIRST (Architect,
  2026-08-20).** `1e` and `28` are stale too and were never reached. **Do not correct the strings
  by observation - find out what each SHOULD render and why, then fix the pipeline or the string
  with the reason recorded.**

- **THE FOUR PERSISTENT 1040 DERIVATION ERRORS (Architect, measured 2026-08-20).** These are the
  ERROR STRINGS the run reported, pasted verbatim. **They name the stage that raised. None of them
  is a diagnosis and this item does not claim one:**

      line  12e: validation gap after one repair: payload: ValueError: LOOKUP_TABLE arguments must be named leaf operands with a role
      line  25c: validation gap after one repair: operand_document_not_found: cross-form operand names unknown document form_w2g_2025
      line  27a: validation gap after one repair: operand_document_not_found: cross-form operand names unknown document earned_income_credit_worksh
      line   31: validation gap after one repair: operand_not_printed: line 15 is not a printed line on schedule_3_2025
      line  35a: validation gap after one repair: quote_not_verbatim: ValueError: quote is not verbatim from the cell evidence
      line   38: validation gap after one repair: subtract_direction: instruction says subtract line 34 from line 38

  `27a`, `31`, `35a` and `38` survive every arm. **Run `explain-cell` on three of them before
  naming a class; they are almost certainly not one class.**

- **THE TRUNCATION COUNTERS ARE NOT IN THE DERIVE REPORT (Architect, 2026-08-19).** S146 added
  `truncation_retries` / `truncation_recovered` / `truncation_exhausted` to the validation report
  and unit-tests them, but the run report YAML carries no such key even as a zero, so **"no
  truncations" and "not plumbed" look identical from the artifact.** Small; surface them.

- **THE TWO LABEL-ONLY CITATIONS ARE STILL IN THE GRAPH AND STILL COUNTED AS VERIFIED (Architect,
  2026-08-19).** S145 stopped projecting them; it did not remove them.
  `cite_instruction_schedule_2_2025_en_us_2025_publink100079593` (`quoted_text: Line 17a.`, nine
  characters) and `cite_instruction_schedule_3_2025_en_us_2025_publink10001946` (`Line 6a.`) remain
  in `instruction-form-1040-html.yaml` with ranges the 2026-08-19 backlog added, and four addresses
  still list them in `citation_refs`. **Decide whether a byte-verified label should count toward
  the checked-citation metric at all.**

- **A CELL CAN CARRY A NEIGHBOUR'S STUB CITATION, AND IT IS WHAT THE 177/12 METRIC ACTUALLY
  MEASURES NOW (Architect, opened 2026-08-19).** Schedule 2 line `17z` has a second physical cell,
  `form1_0_page2_0_f2_21_0`, whose only instruction citation is
  `cite_instruction_schedule_2_2025_en_us_2025_publink100079593` and whose entire quoted text is
  *"Line 17a."*; both of line `17a`'s cells carry the same stub. **Cause not yet known** - it
  arrives through the inventory fallback in `build_generated_document_cells`, which keeps
  `base_cell["instruction_citations"]` when the span index has nothing for the anchor. Open three
  before speccing.

- **[SUPERSEDED 2026-08-19 - THE FRAME WAS NEVER THE PROBLEM; SEE M20-S140.]** I queued this as
  "the pilot frame is not wired in". Wrong: the draft's own `instruction_sections.yaml` already
  holds the `Line 1i` section, text and all. **The gap is the section-to-citation join, 39 of 54
  lines**, and it is the current round.

- **DOES 1040 LINE 1a DERIVE FROM W-2 BOX 1, OR IS `filer_entry` CORRECT? (Architect, 2026-08-19.)**
  The line reads *"Total amount from Form(s) W-2, box 1"*, `form_w2_2025` IS in the manifest, and
  the 2026-08-17 draft carries a node and a `1a -> 1z` addend edge but **no rule at all**. Under
  John's 2026-08-16 taxonomy that is **`derivation_failed`, a defect - not
  `source_form_not_modelled`.** Surfaced by an S115 workbench guard that expected
  `line 1a = W-2 box 1`; **the guard is being relaxed in M20-S138 and this question must not go with
  it.** Needs a re-derive, so it needs John's egress.

**JOHN'S PRIORITY, 2026-08-10: get the CORE documents processing reliably.** Ordered for that.
**Every item below is a PIPELINE change - none of them is a per-cell human correction.**

**THE ACQUISITION FINDING AND THE SCOREBOARD IT PRODUCED LIVE IN BALL.** What remains queued off it:

- **CONSTRAIN `governs` TO A LINE TOKEN OR EMPTY IN THE STRUCTURED-OUTPUT SCHEMA (Architect,
  measured 2026-08-18).** 93 distinct non-line values are in the live 1040 frame; the join key
  accepts free text today. **Prompt/schema change - no blast radius, runs wide, needs a live call.**
- **[APPROVED BY JOHN 2026-08-18 - THE NEXT ROUND AFTER M20-S133] ATTRIBUTION AS ITS OWN STAGE OVER
  BOUNDED SPANS.** Ask, of a span whose boundaries are ALREADY fixed and byte-verified, *"which of
  this form's lines does this span govern, or none?"* **Permitted by the binding ruling pinned in
  AGENTS.md**: the model is labelling a boundary it did not choose, so it cannot drag a neighbour's
  text in. **Its honest prize is 19 Schedule 1-A cells, not 37** - see BALL.
  **FOUR CONSTRAINTS, ALL FROM OPENING THE 37, AND THE FIRST IS THE ROUND:**
  1. **IT MUST NOT BE A LINE-REFERENCE MINER.** Measured: in this chapter, prose that GOVERNS a
     line never names it, and prose that NAMES a line does not govern it. A miner reaches none of
     the 19 and gets every mention wrong. **If the round produces a regex over body prose, it has
     failed regardless of its score.**
  2. **THE MODEL NEEDS THE FORM'S LINE INVENTORY AND THAT DOES NOT BREAK CELL-NAIVETY.** It cannot
     answer *"which lines does this govern"* without knowing which lines exist. **A closed menu
     attached to a fixed span is a lookup; a demand to go find one cell's instruction is not.**
     The inventory is the printed anchors we already hold - no model call to build it.
  3. **EMPTY IS A FIRST-CLASS ANSWER AND MOST SPANS MUST TAKE IT.** 18 of 37 cells have no prose at
     all, and 50 of the 69 sections govern no line. **A run where few spans answer "none" is
     evidence of fabrication, not coverage** - report the "none" rate as a headline, not a footnote.
  4. **SCORE IT AGAINST WHAT THE PROSE ACTUALLY SAYS, NOT AGAINST 48.** The reference answer is the
     19, and the 18 arithmetic cells are a CEILING - reaching them would mean the model invented an
     instruction. **Do not write a floor that counts them as misses.**
  **NEEDS JOHN'S EGRESS - it is a live model call**, and it changes the prompt, so it has no blast
  radius and runs wide.
- **[DONE 2026-08-18 - see BALL] SCHEDULE 1-A'S 37 UNREACHED CELLS ARE OPENED.** 19 have governing
  prose, 18 are the instruction ceiling, and mentioning a line is anti-correlated with governing it.
- **DOES THE IRS PUBLISH THE LOOKUP TABLES AS THEIR OWN PAGES?** The 2025 Tax Table and the EIC
  tables are the only content the HTML does not carry, and they are the last thing holding the OCR
  path open. **The tax table itself is already modelled** - `tax_graph/compile/tax_table.py` builds
  2,062 bands from the authored brackets and the engine matches OTS - so what a clean copy buys is
  verification against something other than our own inputs, not a new capability.
- **NO MCP TOOL RESOLVES A RANGE TO TEXT (Architect, 2026-08-18).** `get_document` returns a
  document object and `get_citation` the stored record. Attaching augmenting context BY REFERENCE
  needs the accessor M20-S133 builds, exposed as a tool.
- **`sibling_worksheet_owner` MASKS WORKSHEET-TO-WORKSHEET MISATTRIBUTION (Architect, measured
  2026-08-17).** Correct today only because all four Schedule D worksheets have 0 cells in the
  reconciliation population. **The moment worksheet cells enter it, a row attributed to the WRONG
  sibling scores as correct.** Key it on whether the owner is the cell's own document.
- **[SPECCED, DEFERRED - full spec at `5e9230c`] M20-S125: MAKE THE COVERAGE METRIC HONEST.**
  `model_reachable` counts a foreign worksheet's row number as reach.
- **`_write_recording` CLOBBERS THE FIXTURE INSTEAD OF MERGING (Architect, read 2026-08-17).** It
  writes only the booklet just run, so pointing `--output` at
  `instruction_segmenter_live_recordings.json` **destroys the paid Schedule B and D recordings**
  every floor since S121 rests on. Merge by `source_document_id`; until then write to a new path.

**DIRECTION PINNED 2026-08-13 IN `../docs/source-extents.md`. DO NOT REDESIGN IT HERE.** A citation
should record WHERE its text is, not carry a copy of it, and a source chunk that is not a numbered
row should say what it is and what it governs. **ORDER MATTERS AND M20-S133 IS THE FIRST STEP:
dropping `quoted_text` before the ranges are checkable would freeze an unverified range where
nothing can ever see it.** The stored copy is the only reason the defect was detectable at all.
**The queue has NOT been reshaped around the doc yet - that is John's call.** What the doc settles
is that items 2, 3, 6 and the recurring extent defects are one root cause and should stop being
specced as separate cue-matching repairs.

**ITEM 1 IS DELIVERED.** Prior-year documents were M20-S102, accepted at `ee6eb55`. The graph now
has the concept, the gate is correct on the real rows, and `status: unresolved` prior-year stubs
carry their own year. **The four documents item 1 also named remain open** and belong to items 4
and 6: `schedule_se_2025` and `form_6252_2025` are real IRS forms absent from the manifest;
`form_w2_2025` and `form_1099_g_2025` are information returns, which
`../docs/source-extents.md` records as NOT covered by the extents work.

1. **[SPECCED AS M20-S102, 2026-08-12 - see Current round]
   PRIOR-YEAR DOCUMENTS ARE A CATEGORY THE GRAPH HAS NO CONCEPT OF** (Architect, measured
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

**NO DUPLICATE FULL SUITES, AND THE ARCHITECT STOPS RUNNING ONE PER ROUND (Architect, 2026-08-19).**
I started three full suites today and **every one was invalidated by the Worker committing under
it** - the tree moves the moment John launches the next round, and pytest collects at start, so the
run measures a mix. **Two of them also ran concurrently with the Worker's own suite, contending for
CPU and workbench ports.** Net yield of ~3.5 hours of CPU: nothing that the focused sets and
recomputation did not already show.
- **The Architect's job is recomputation, not a second suite.** Re-derive the round's claims from
  the artifacts, diff failure SETS when a suite exists, and verify the blast radius.
- **When a full suite IS wanted, it runs in the gap between rounds and John is told to hold the next
  launch until it lands.** Otherwise it is not a quiet window, it is a race.
- **The one full-suite result that ever caught something the focused sets missed was S133's item 5**
  - a check that had stopped checking. **That is the case that justifies the occasional run**, at a
  phase boundary, not every round.


**ONLY ONE FULL SUITE RUNS AT A TIME, AND IT BELONGS TO WHOEVER'S ROUND FLOOR DEMANDS IT
(Architect, 2026-08-19, after wasting ~40 minutes of CPU and nearly corrupting a Worker run).**
I had a suite going from 11:52 while Codex started its own at 12:23. **Two full suites on one
working tree contend for CPU and both write review state and bind workbench ports, so each can make
the other fail spuriously** - and mine was void regardless, because Codex was editing source files
underneath it. **I killed mine and left the Worker's running.**
- **The Worker's run is the authoritative one when a round is in flight.** It covers the new code;
  an Architect run started before the round does not.
- **The Architect's quiet-window run is for the interval between rounds** - after a round lands and
  before the next is launched. **John starts Codex, so that window is real and schedulable.**
- **Before starting a suite, check for a python process already running one.**

**A GUARD I SPECCED IN M20-S139 WENT STALE IN ONE ROUND, WHICH IS THE FASTEST YET.** I had the round
assert `len(missing) == 39`. S140 fixed the join and the number is now **5**, so my own guard is the
new red. **Codex was right to refuse to rewrite it and to escalate instead.**
**THE RULING: replace it with a non-increasing assertion** - the gap is reported, and it does not
GROW - plus the designed `xfail`, which is the part that carries information. **A measured number
belongs in the round report, never frozen into a guard.** This is the third time a snapshot
assertion has cost a round (S138's three, S139's one), and the previous two were inherited; **this
one I wrote myself, one round after writing the rule against it.**


**THE FULL SUITE CANNOT BE RUN IN A GIT WORKTREE, AND MY ATTEMPT TO PIN IT THERE PRODUCED A VOID
RESULT (Architect, measured 2026-08-19).** I moved the run into a worktree pinned to `cb93fea` so
Codex could not change files underneath it. **It came back `31 failed, 989 passed, 11 skipped,
34 errors` in 46:47 - and every one of those numbers is meaningless as a baseline.** The 34 errors
are collection failures in exactly the files that need untracked live state - all of `tests/e2e/*`,
`test_workbench_cells_api_m17`, `test_workbench_page_evidence_m15`, `test_review_preflight_m15`,
`test_verify_record_m9`, `test_self_serve_extension_m14`. **A naive set-diff makes it look like 28
tests "cleared" and 10 went "new"; nothing cleared - those tests never ran.** The 46-minute runtime
against the ~70-minute anchor is the tell.
- **Junctioning `.cache` and copying `graph/2025/_drafts` is NOT enough.** The suite also reads live
  `output/`, `review_queue/`, `workbench_output/` and `review_context/` CONTENT, none of it tracked
  and none of it enumerated anywhere.
- **So the full suite is only meaningful in the working tree, which means it is only meaningful
  while the Worker is IDLE.** John starts Codex, so the quiet window is real and schedulable: run
  it after a round lands and before the next is launched.
- **THIS IS THE SAME FINDING AS THE S115 WORKBENCH DEBT, ARRIVING AGAIN.** A test suite that cannot
  be reproduced from a clean checkout is not a gate, it is a local ritual. **Enumerating what
  untracked state the suite requires is worth a round of its own** - and it is the precondition for
  ever running this in CI.


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

## From Architect

**ACTIVE DIRECTION: M20-S133 UNDER CURRENT ROUND.** Heading extraction is finished; the citation
range is the next thing that is wrong in the artifact the agent actually reads.

**A PRECEDENT THAT BINDS M20-S133 DIRECTLY, AND IT IS WHY THE SPEC FORBIDS TOUCHING `quoted_text`.**
The S106 rework was REJECTED for truncating real quotes to fit wrong ranges. S107 was allowed to
change `quoted_text` only in the opposite direction - replacing hand-authored paraphrase with what
the document actually says, with the source pinned and the changed set asserted to be exactly the
named 30. **When a quote and a range disagree, the range is the thing under suspicion; editing the
quote to make a check pass is how the defect gets buried.**

**A NOTE TO MYSELF THAT KEEPS EARNING ITS PLACE.** Repeated specs have set a floor the data could
not meet - `7ba64be`, S106, S112, S130 - and twice this week I specced a floor item that was ALREADY
SATISFIED. **Before writing the next floor, check that the corpus can satisfy it and that the
machinery does not already exist.** S131 is the worst case: I hand-rolled a formula, compared THAT
against OTS, never ran the engine, and specced a round to rebuild a tax table the repo already had.

## History

Everything before M20-S23, and all per-round Worker narration, lives in git history. This file was
pruned from 7,520 lines on 2026-08-02 at S28 acceptance; `git show 12240ef:plans/AGENT_HANDOFF.md`
is the last unpruned copy. Earlier prune: 2026-07-23, from 1,198 lines, for public-repo prep.
Durable rulings were carried forward into **Binding rulings** above rather than deleted; A9
rulings remain pinned in `plans/PHASE_M15.md`; the defect ledger (D6, D9, D10, D12, D13, D14) is
in `AGENTS.md`.
