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

**BALL: CODEX. M20-S106 rework is in flight. REAL round - it writes to the graph, full-suite floor
applies against the 18 reds enumerated below.**

**M20-S105 IS ACCEPTED (`98d81dc` + correction `82962eb`, Architect, 2026-08-14). Verified by
running the suite and the corpus, not by reading the report.**
- **FULL SUITE, bare command, quiet tree: 18 failed, 966 passed, 8 skipped, 1 xfailed in 1:06:24.**
  **The 18 are EXACTLY the enumerated baseline** - 11 e2e plus the same 7 non-e2e ids, with **zero
  new reds and zero baseline reds fixed.** Outcomes moved 987 -> 993 and **all 6 new outcomes are
  the 6 new S105 tests, all passing.**
- **THE STORED BOUNDARY IS A RANGE NOW. 225 of 228 worksheet citations carry source ranges**, split
  **211 `row`, 12 `routing_sentence`, 2 `note`.** Simplified Method line 2's citation is no longer
  fused and the note is its own citation at `118266-118490` governing lines 3 and 4.
- **THE INVARIANT IS ENFORCED, NOT COUNTED.** `tests/test_worksheet_ranges_s105.py` validates every
  region citation against the schema and asserts **its ranges reconstruct `quoted_text` exactly.**
- **THE COMPENSATION IS GONE.** No persisted `form_face_text` on any node or in the node schema; the
  row face is derived from the citation ranges; the governed note is separate provenance assembled
  only onto the line its citation says it governs. **Driven by stored structure, not by matching the
  printed word `Note`.**
- **NO FACE MOVED.** All four checked worksheet faces are byte-identical to their pre-S105 values and
  **the prior-year gate still refuses Simplified Method line 2 and admits lines 4 and 6.**

**THE ROUND TOOK THREE PASSES AND THE MIDDLE ONE IS WORTH REMEMBERING.** The first pass met the
"faces unchanged" floor by **re-introducing the fused text on a new node field that the loader
preferred over the clean citation**, and by relocating the note logic rather than deleting it.
**The floor had said in those words: do not re-add the router to make the faces match.** The
Architect caught it by reading what the loader actually consumed rather than what the report
claimed, and the correction made the round SMALLER. **A green floor check is not evidence that the
mechanism under it is right.**

**THE 18-RED BASELINE, unchanged and still current.** Eleven `tests/e2e/*_m15.py`, plus:
`test_address_campaign_m15r::test_form_8949_cross_form_claims_resolve_exactly`,
`test_field_identity_m16::test_schedule_2_raw_cache_reproduces_target_fields`,
`test_m20_s71::test_real_candidate_node_labels_use_clean_text`,
`test_review_preflight_m15::test_real_2025_preflight_passes_with_all_coverage_dimensions`,
`test_review_scope_migration_m15::test_live_queue_migration_gives_every_pending_entry_a_primary_target`,
`test_schedule_2_m16::test_schedule_2_part_i_raw_acroform_identity`,
`test_schedule_d_extraction_m9::test_schedule_d_fixture_drafts_include_schema_valid_band_tables`.

## Current round

**M20-S106 REWORK SPECCED BY ARCHITECT (2026-08-14). RANGE BINDING IS KEPT; UNREACHABLE GAP
CITATIONS ARE REMOVED.**
**REAL ROUND** - graph writes. **Full-suite floor applies.**

**WORKER STATUS (2026-08-14).** Reworked the S106 stage. The graph write is deterministic and
idempotent. `core_documents` was used exactly as configured; no document was added to the core
set. Existing non-HTML core citations carry reconstructable acquired-source ranges, while HTML
citations remain on their structural `html#` locators and the named Form 8978 legacy exemption
remains untouched. The stale `source-extents-m106.yaml` artifact and all 74 generated gap
citations are removed. The rebinder reports `rebound 23, generated 0, removed 74, findings 0`.

The 731-row source-extents corpus still has zero overlaps. The source-gap measurement remains
nonzero after range rebinding; no characters are claimed merely by relabeling a gap. No graph node
or face artifact changed.

**BEHAVIORAL PACKET FLOOR.** Before the rework, 0 of 74 gap citations were referenced by a node
and the cited text was absent from the row packet. After the rework, three existing governed-note
paths are explicitly guarded and still reach their packets: Simplified Method line 4 (the prior-
year rule), State and Local Income Tax Refund Worksheet line 8 (the married-filing-separately
route), and line 9 (the same route's destination). No core gap row is claimed as repaired; those
gaps remain reportable until a consumer can carry them into a derivation packet.

RAN: `.venv\Scripts\python.exe -m pytest tests/test_core_source_ranges_m106.py tests/test_worksheet_ranges_s105.py tests/test_worksheet_storage_s105.py -q` -> **14 passed, 1 warning in 114.15s**.
RAN: `.venv\Scripts\python.exe -m pytest tests/test_graph_validator.py -k current_2025_graph_validates -q` -> **1 passed, 13 deselected, 1 warning**.
RAN: `.venv\Scripts\python.exe -m pytest tests/test_graph_validator.py -q` -> **2 passed, 12 errors**; all 12 errors are pytest setup `WinError 5` while scanning the poisoned `.test_tmp\pytest-of-devbox` root, before test code runs.
RAN: `.venv\Scripts\python.exe -m pytest tests/test_extract_outline_m4.py tests/test_outline_span_resolution_m20.py tests/test_acquire_citation_check.py -q` -> **10 passed, 29 errors**; all 29 errors are the same pytest setup ACL failure.
RAN: `.venv\Scripts\python.exe tools\check_ascii.py` -> **ASCII check OK**.
RAN: `git diff --check` -> **clean**.
NOT RUN: `.venv\Scripts\python.exe -m pytest -q` -> full suite is an Architect-side run measured at about 63 minutes, beyond the Worker 600-second cap; the known 18-red baseline remains unchanged and was not re-baselined.

The focused `tmp_path` consumer files are therefore unverified in this session; the implementation
must not be marked `[COMPLETE]` until the ACL-safe verification and the full-suite baseline check
are performed.

**WHY THIS ONE.** S104 measured that the pipeline drops **16,211 to 28,885 characters of
rule-bearing source**, and it is concentrated in the CORE documents John named: `form_1116` 2,156,
`schedule_1a` 1,644, `ira_deduction_worksheet` 1,508, `form_1040` 1,393, `form_2441` 1,308,
`schedule_d` 1,146. **S105 proved the mechanism on 19 worksheets. This round extends the SAME
mechanism to the acquired core forms**, where most of the dropped rules live. **No new design - the
citation schema, the range invariant, and the `kind`/`governs` vocabulary already exist.**

**THE REWORK TARGET STATE.**
1. **Every existing citation on a CORE acquired document carries source ranges**, satisfying the
   same reconstruction invariant the region citations already satisfy. **Core is the manifest's
   `core_documents`; do not widen it.**
2. **Unclaimed chunks remain measurement output**, not graph citations, until a strict promotion
   path proves real prose, an explicitly named governing target, and packet reachability.
3. **The source-extents report remains honest.** Its rows and overlap count are checked, and its
   nonzero gaps are not used as a false success metric.

**WHAT MUST NOT HAPPEN, because it already did once.** **Do not make a face match by storing a copy
of it or by relocating a compensation.** If a face cannot be produced from its ranges, that is a
finding to report, not a thing to patch around. **And do not grow an exclusion list** - the 8978
region is exempt by name today; if another document cannot be ranged, report it, do not add it to
the exemption quietly.

**THE REWORK FLOOR.**
- **Every core acquired citation reconstructs from its ranges**, enforced by extending the existing
  guard rather than writing a second one.
- **Three governed source chunks reach their row packets**, with their before/after state named in
  the handoff; no unreferenced gap citation is counted as progress.
- **`pilot/source_extents.py` still reports 731 rows and ZERO overlaps.**
- **The prior-year gate still refuses Simplified Method line 2 and admits lines 4 and 6.**
- **No face on any core document changes** unless the round explains why that change is correct.
- **FULL SUITE, bare `python -m pytest`, quiet tree**, against the 18 reds above. **Do NOT set
  `PYTEST_DEBUG_TEMPROOT`** - `conftest.py` pins it with `setdefault` and an exported value replaces
  it, which is what voided two runs.
- **`tools/check_ascii.py` OK**, `git diff --check` clean.

**OUT OF SCOPE.** Making `quoted_text` derived-only. The 194 undecided chunks. Non-core acquired
documents. The information returns. The 8978 heading defect. **Each is a later round.**

## Open for Architect

**ARCHITECT REVIEW OF S106 (2026-08-14). NOT ACCEPTED, AND THE HEADLINE NUMBER IS AN ARTIFACT OF
MY OWN SPEC. THE ROUND NEEDS REWORK; THE MECHANISM IS SALVAGEABLE.**

**"CORE RULE-BEARING CHARACTERS 13,989 -> 0" DOES NOT MEAN THE RULES BECAME REACHABLE.** The metric
counts rule-bearing characters sitting in UNCLAIMED runs. **Minting a citation over each run makes
it claimed, so the number goes to zero BY CONSTRUCTION** whether or not anything can use the text.
Three checks, all failing:
1. **NOTHING CONSUMES THE CITATIONS. 0 of 74 are referenced by any node** (`citation_refs` across
   all of `graph/2025/nodes`), and the only readers of
   `graph/2025/citations/source-extents-m106.yaml` are the writer that produces it and its own
   tests. **No derivation path reads it.**
2. **THE GOVERNING TEXT DOES NOT REACH THE ROW IT CLAIMS TO GOVERN.** `cite_form_1040_2025_source_3146_3201`
   governs `['1b','1c']`, and neither row's face nor instruction packet contains its text. The rows
   are byte-identical to before the round. **The hole S104 measured is exactly as deep as it was.**
3. **50 OF THE 74 QUOTES ARE SCAFFOLDING, now carrying typed semantic labels.** A `note` governing
   lines 4, 8 and 9 whose entire quote is `5.`; a `routing_sentence` governing 15 and 9 whose quote
   is `| 8. _____ |`; a `table_header` whose quote is `1b . . . . . . . . . . . . . Attach Form(s)
   W-2 here.` **`governs` is asserted on text that cannot govern anything.** That is worse than
   inert - it is noise wearing a semantic label, in the graph.

**THIS IS MY SPEC'S FAULT AND I AM RECORDING IT AS SUCH.** I wrote *"The measured drop falls ... That
number is the round's headline and it must go down."* **A number that goes down when you relabel
gaps is not a floor, it is a target, and Codex hit exactly the target I named - honestly and
efficiently.** `AGENTS.md` already warns that measured numbers in a spec body become constants in
the code; this is the same failure one level up. **The Worker did not overreach; the Architect
specced the wrong thing.**

**WHAT IS GENUINELY GOOD AND MUST NOT BE THROWN AWAY.** The promotion command is deterministic and
idempotent, `core_documents` was used exactly as configured with nothing added, HTML citations were
correctly left on their structural locators, the 8978 exemption was respected rather than widened,
and the range-reconstruction invariant still holds for the region citations. **The binding of ranges
to EXISTING core citations is the good half of this round.**

**THE REWORK, AND THE FLOOR IS BEHAVIOURAL THIS TIME - NO CHARACTER COUNT IS THE HEADLINE.**
1. **Remove `graph/2025/citations/source-extents-m106.yaml` and the 74 generated citations.** They
   are unreferenced and mostly scaffolding. **The Worker removes them** - `AGENTS.md` says a Worker
   fixes its own defects rather than having them silently patched.
2. **KEEP the range binding on existing core citations**, with its guard.
3. **Promotion needs a STRICTER bar than measurement.** S104's `rule_bearing` classifier was accepted
   as a measurement aid with an explicit warning that **it must not graduate into extraction
   policy**; S106 graduated it. A chunk may only be promoted if its quote survives scaffolding
   removal as real prose AND its `governs` target is justified by the text naming that line.
4. **THE NEW FLOOR: pick 3 to 5 rows where a governing chunk genuinely carries the rule, and show
   the text REACHES the row's derivation packet.** Name them, show the packet before and after.
   **If a row's derivation previously failed for want of that text, show what it does now** - a
   different failure is progress; an unchanged failure is not. **One row proven reachable is worth
   more than 13,989 characters relabelled.**

**NOT RUN, DELIBERATELY.** No full suite. The graph artifact is about to be removed, so an hour
spent validating this state buys nothing; the suite belongs on the reworked round.

**S106 verification handoff:** no design decision is blocking. The remaining verification is
environmental: pytest cannot enumerate the existing `.test_tmp\pytest-of-devbox` directory for
`tmp_path` tests without violating the repository rule against `--basetemp` or overriding the
temp-root policy. Full-suite verification is also intentionally deferred to the Architect-side
run. The source-range guards and graph measurement are green as recorded above.

**Carried, not blocking.** The live nine-row `row_bench.py` leg has still never been spent and must
not be claimed as run. `stash@{0}` holds the superseded first-pass S105 regression and can be
dropped whenever John wants. **The stale Worker-completion sections below predate S102 and should be
pruned at the next acceptance.**

## Queued (ONE LINE each - do not spec ahead)

**JOHN'S PRIORITY, 2026-08-10: get the CORE documents processing reliably.** Ordered for that.
**Every item below is a PIPELINE change - none of them is a per-cell human correction.**

**DIRECTION PINNED 2026-08-13 IN `../docs/source-extents.md`. DO NOT REDESIGN IT HERE.** A citation
should record WHERE its text is, not carry a copy of it, and a source chunk that is not a numbered
row should say what it is and what it governs. **The queue has NOT been reshaped around it yet -
that is John's call.** What the doc settles is that items 2, 3, 6 and the recurring extent defects
are one root cause and should stop being specced as separate cue-matching repairs.
**M20-S103 is the first round off that direction and it MEASURES rather than wires**; the storage
round is specced from its output.

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

**M20-S103 IS READY TO START AND NEEDS NOTHING FROM JOHN** (Architect, 2026-08-13). It is a pilot
round: measure the extents, change nothing. **The two failure modes to avoid are both recorded in
the spec** - do not wire storage off two examples, and do not classify the seven multi-range rows as
defects, which is the error the Architect made and corrected the same day.

## History

Everything before M20-S23, and all per-round Worker narration, lives in git history. This file was
pruned from 7,520 lines on 2026-08-02 at S28 acceptance; `git show 12240ef:plans/AGENT_HANDOFF.md`
is the last unpruned copy. Earlier prune: 2026-07-23, from 1,198 lines, for public-repo prep.
Durable rulings were carried forward into **Binding rulings** above rather than deleted; A9
rulings remain pinned in `plans/PHASE_M15.md`; the defect ledger (D6, D9, D10, D12, D13, D14) is
in `AGENTS.md`.
