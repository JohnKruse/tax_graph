# AGENT_HANDOFF.md

The single living doc for active Claude (Architect) <-> Codex (Worker) coordination. Update it in
place; do NOT spawn new per-topic note files. Standing rules: `../AGENTS.md`. Master plan:
`../docs/engineering-plan.md`. Phase plan: `PHASE_M20.md`.

## How to use
- **Worker:** raise questions/blocks under **Open for Architect**.
- **Architect:** answer there (and pin durable decisions into the relevant `PHASE_<id>.md`), then
  clear the item. Record active direction under **From Architect**.
- **Keep it short.** A round that completes gets its narration DELETED, not appended - the
  accepted hash is the record and `git show <hash>` recovers everything. Only the current round,
  the standing constraints, and the binding rulings live here.
- **Prune at every acceptance, not "at phase close".** Pruned 2026-07-23 to 1,198 lines, then
  grew to 7,520 by 2026-08-02 because acceptance never triggered a prune. That is the failure
  mode this section exists to prevent.

## BALL

**BALL: WORKER - M20-S41 (RECONCILE THE DOCUMENT LISTS AND DRIVE THE HARNESS FROM THE MANIFEST).**
Task block under **From Architect**. **S40 is ACCEPTED at `e032cfd`.**

**RESEQUENCED 2026-08-03 BY JOHN.** S41 is now the manifest reconcile, S42 is the worksheet
harvester with QDCGT as the canary, and the operand type check moves to S43 with its spec intact.
The reason is in Current round: **the Architect had been using the graph as the corpus list, which
is circular**, so the denominator under every S38-S40 number is wrong in both directions. A wrong
denominator undermines the measurements that would judge the type check, and the harvester needs a
document list it can trust.

## Current round

**M20-S40 ACCEPTED (Architect, Claude Opus 5, 2026-08-03) at `e032cfd`.** The Worker ran its own
provider legs and reported derived 92 / 91; I ran two more and got **92 and 91**, so the numbers
reproduce across four independent runs. **The S39 regression is closed** - `form_1040_2025` is 17/17
and `schedule_1a_2025` is 25/25 and 24/25, where S39 sat at 87 derived on both runs.

| run | attempted | derived | repaired | errored | resolved |
| --- | ---: | ---: | ---: | ---: | ---: |
| S38 (baseline) | 96 | 92 | 1 | 3 | 93 |
| S39 | 96 | 87 | 6 | 3 | 93 |
| S39 | 96 | 87 | 5 | 4 | 92 |
| S40 Worker | 96 | 92 | 3 | 2 | 95 |
| S40 Worker | 96 | 91 | 2 | 3 | 93 |
| S40 Architect | 96 | **92** | 1 | 3 | 93 |
| S40 Architect | 96 | **91** | 2 | 3 | 93 |

**91 on one run of a pair is variance and is NOT a stop.** 87 twice was not; 92/91 four times is.
Do not spend another round chasing the missing one.

**Verified rather than accepted on report.** `form_1040_2025_zero_floor` really is
`node_type: parameter` with `constant_value: 0`, so the widened `missing_floor` accepts the cited
node and still rejects a nonzero parameter. Scoping renders 26 nodes for 1040, 3 for Schedule D, and
1 (`taxpayer_2025_filing_status`) for every other form, which is what stopped a 1040 node from
reaching 6251 and Schedule 1A rows. Protected set byte-identical across `4935053..e032cfd`; focused
suites 67 passed on a short temp root; ASCII OK; `git diff --check`; `validate 2025` exit 0
(18 documents, 441 nodes, 409 edges, 401 citations); preflight `legacy_mined=394` unchanged.
`_projection_warnings` is safe to call where it sits - `_apply_payload` runs
`validate_expression_tree` first, so `expression_to_graph` cannot raise on a tree that reaches it.

**MEASURED CORRECTION TO MY OWN S38 NUMBER. The corpus mints exactly ONE external node, not nine.**
Step 4 closed the reporting hole and both my runs show a single mint: `schedule_a_2025` line 15 ->
`form_4684_2025_root_line_18`. My "9 of 96 rows reference an outside form" counted rows whose *text*
names another form; only one row actually emits a cross-form operand. The rest resolve as
REQUIRE_INPUT or as same-form arithmetic. **The Form 4684 repair is confirmed and the scale of the
problem was smaller than I reported.**

**THE NEW WARNING IS RIGHT AND IT IS 70% NOISE.** `unmapped_operation` fires 12 and 14 times across
my two runs, but 8 and 9 of those are `REQUIRE_INPUT` - the answer the prompt explicitly instructs
the model to give for a line that is not computed. It has no rule mapping because it is not a
computation. **Warning on it trains a reviewer to ignore the warning**, which is the exact failure
the review-loop design calls out: attention is the scarce resource. Excluding it leaves the true
signal at three rows, stable across both runs: `form_1040_2025` line 34 (`IF_ELSE`), and
`form_6251_2025` lines 18 and 39 (`IF_ELSE`, `LOOKUP_TABLE`).

**AND THE WARNING EXPOSED SOMETHING BIGGER THAN EXECUTABILITY. THE EXPRESSION GRAMMAR IS TYPE-FREE.**
The Worker flagged this honestly and I reproduced it. 6251 line 39, run A, status `derived`, zero
failures:

```
if_else(node[taxpayer_2025_filing_status], 0, if_else(line 12, 119550, ...), if_else(line 12, 239100, ...))
```

`IF_ELSE` is documented as comparing a condition AMOUNT against a threshold AMOUNT. This puts a
filing-status enum in the condition slot and `0` in the threshold slot. It is meaningless, and
nothing catches it. In run B the same line came out correctly shaped, so it is nondeterministic
nonsense that validates clean roughly half the time. Run B's line 18 shows the same class from the
other side: `multiply(line 17, lookup_table(status, 0.26, 0.26))` - a filing-status lookup whose two
branches are identical, i.e. the model pattern-matching the bracketed-MFS shape onto a rate that
does not vary by status.

**This outranks the rule mapping.** An unmapped operation fails loudly at projection time. A
type-confused operand is a wrong answer wearing a `derived` badge, and 6251 line 39 is a real tax
computation. **S43 takes it** - it was specced as S41 and John resequenced it behind the two items
below, because a wrong document denominator undermines the measurement that would judge it.

## THE DENOMINATOR IS WRONG (Architect, 2026-08-03, prompted by John asking how I pick documents)

**I have been passing `graph.items("documents")` to the harness. That is circular** - the graph is
partly the pipeline's output, so a document that was never modelled can never enter a run. The three
lists disagree in every direction: **graph 18, manifest 21, acquired text 23.** `form_2441_2025` is
in the graph and not the manifest (the phantom that errored on every run); four instruction
documents are declared and acquired but invisible to the corpus; `form_2441_2025` and its
instructions are on disk and undeclared. **`instructions_form_6251_2025` is 80,318 characters we
already hold, naming the QDCGT worksheet 20 times - and 6251 lines 13, 20 and 27 are the only
unresolved rows, failing because they reference that worksheet.** The evidence was on disk and my
document list excluded it. Every "full corpus" figure since S33 is over a graph-derived list; the
row counts are real, the phrase overstates them. **S41 fixes this first.**

## WORKSHEETS ARE THE REAL GAP, AND HAND AUTHORING ALREADY LOST DATA (Architect, 2026-08-03)

Verified against the IRS text John supplied: the QDCGT worksheet is **fully and correctly modelled**
- 44 nodes, 25 of 25 lines, and all 13 constants match exactly (0% breakpoints 48,350 / 96,700 /
64,750; 15% breakpoints 533,400 / 300,000 / 600,050 / 566,700; rates 15% and 20%; tax-table cutoff
100,000). Line 25 flows to `form_1040_2025_non_sdtw_tax` and on to 1040 line 16, as the worksheet
itself instructs. **What is missing is document identity, not computation** - no worksheet is a
document, so the pipeline cannot address, cite, review, or derive against content the engine already
computes.

**And the hand-authored version lost real semantics.** There are **zero nodes anywhere in the graph**
for Form 2555 or the Foreign Earned Income Tax Worksheet, although the worksheet's own text
redirects line 1's source and line 25's destination when Form 2555 is filed. The transcriber took
the numbered grid and dropped the footnotes, which are conditional routing. Independent evidence
that the loss is real: **Form 2555 was the most common outside-the-corpus reference in the
derivation runs, five rows** - the model kept reaching for what the transcription lost.

**All 13 QDCGT citations fail `check_graph_citations` today**, and they are 13 of the standing 36
"known red" mismatches. The cause is not rollover drift: the authored quote reorders the IRS
sentence (splitting "single or married filing separately" into two clauses and repeating the
figure), so it was never verbatim. The locator is `"page 35, lines 3443-3447"` - position-based
identity, which will not survive a year change either. **Citation-quote-by-construction is already
the documented rule; these predate it.**

**SMALLER, CARRIED.** (1) Aggregate `validator_failures_by_kind` counts both attempts while
`rows_detail` keeps only the first, so 6251 reports `missing_floor: 3` that no row shows - those are
repair-round failures on lines 13/20/27. For a findings surface, which attempt failed matters.
(2) Step 2 asked the Worker to report whether scoping hides a node a row legitimately needs, and it
did not. I checked: no non-1040 row names the standard deduction or the brackets, so nothing is
lost today - **but 6251 lines 13, 20 and 27 reference the Qualified Dividends and Capital Gain Tax
Worksheet, and scoping now hides the `form_1040_2025_qdcgt_*` nodes from them.** Those three rows
are exactly the three `self_reference` errors, and they are blocked on John's open scoping call (1)
below, not on scoping.

## Standing constraints (every M20 round)

- **PROTECTED SET, hard gate:** `graph/2025/{nodes,edges,rules}/` and `graph/2025/field_maps/`
  must be byte-identical. `git diff --stat` on those directories must be EMPTY. No promotion, no
  hand-authoring, no live graph edit, no verdict write, no operation enum change.
- **`derive_cells` must remain pure - zero disk writes.**
- **PYTEST TEMP ROOT MUST BE SHORT** (e.g. `C:\tgt`). An Architect session was burned reporting 22
  suite failures of which 8+ were `WinError 206` path-length artifacts of a deep temp root. With a
  short root the same files went 11 failed -> 3.
- **KNOWN-RED BASELINE - inherit it, do not get blamed for it, do not fix it in an unrelated
  round.** All three depend on untracked local state, which is why CI is green:
  - `test_review_scope_migration_m15.py::test_live_queue_migration_...` (FileNotFoundError,
    `review_queue/2025/deferred_review.yaml` - tracked dir with no files)
  - `test_schedule_2_m16.py::test_schedule_2_part_i_raw_acroform_identity` (`assert '1a' == 'z'`;
    reads gitignored `.cache/raw/.../schedule_2_2025.fields.json`, regenerated 2026-07-28 while
    the source PDF is unchanged, so a code-only bisect proves nothing)
  - `test_address_campaign_m15r.py::test_form_8949_cross_form_claims_resolve_exactly`
    (`realized 0, expected 6`)
  - `test_schedule_d_extraction_m9.py::test_schedule_d_fixture_drafts_include_schema_valid_band_tables`
    (added 2026-08-03; Architect bisected it against the S35 resolver change and it fails
    identically with that change reverted, so it predates S35)
- **The Worker sandbox has NO outbound network.** Live-provider legs fail 17/17 with
  `LlmUnavailable: ... Connection error`. This has cost three rounds. Either run the provider leg
  outside the sandbox with approved access, or declare the round fixture-only UP FRONT.
- **Model is `openai/gpt-5.6-luna`** in `tax-graph.config.yaml` (`llm.micro_model`). Do not switch
  to `google/gemini-3.6-flash` - measured ~15x the cost at our call volume.
- **Evidence discipline:** honest `RAN:` / `NOT RUN:` lines with exact commands and exact output.
  Never a guess, never a paraphrase of a number.

### Worker environment (2026-07-23)
The recurring `Access is denied` on `.venv\Scripts\python.exe` was the venv launcher shim spawning
the OUT-OF-WORKSPACE base interpreter, which the Codex sandbox denies per session (it is NOT a
machine state and no restart fixes it). Fixed by mirroring the base interpreter to `.python313/`
inside the repo (gitignored) and rebuilding `.venv` on it, so `pyvenv.cfg home` is in-workspace.
Workers call `.venv\Scripts\python.exe` directly - no `uv` needed.
**Do NOT pass `--basetemp`** (2026-07-25). The root `conftest.py` pins the temp root for every
account and pytest separates accounts via `pytest-of-<username>/`. The old `.pytest_tmp` is
poisoned and unreclaimable; see the hard rule in `AGENTS.md`.
**Launcher cap is 600s** (John, 2026-07-26; was ~124s, then 240s). The Worker runs its OWN e2e and
app-dependent files. Only full partitions and Tier 3 shakedowns stay Architect-side. Anything that
still does not fit gets an honest `NOT RUN:`.
**ALWAYS use the module form, never the console scripts** (2026-07-23, M16-S4):
`.venv\Scripts\python.exe -m tax_graph.cli validate 2025` and
`.venv\Scripts\python.exe -m workbench.cli preflight --year 2025`. The generated `tax-graph.exe` /
`review-workbench.exe` launchers resolve the package through the editable install's `.pth`, which
hardcodes an absolute repo path that does not resolve inside the Codex sandbox
(`ModuleNotFoundError: No module named 'tax_graph.cli'`). Architects: write the module form into
Worker prompts.

**Recurring op note:** orphaned `serve` processes have first-class tooling -
`tax-graph serve --sweep-orphans`. The parent watchdog works on Windows as of M14 (OpenProcess
probe). Serve writes stderr breadcrumbs that Claude Desktop logs verbatim - first stop when a
client-managed server dies.

## Binding rulings (John's, still in force - DO NOT DELETE ON PRUNE)

- **THE HANDCRAFTED SET IS THE TEST SET, AND IS PROTECTED.** A lot of tokens went into it. It is
  not to be thrown away, promoted over, or edited. It is labeled comparison data. This is the
  origin of the protected-set gate above.
- **THE SPINE IS THE FLOW OF THE FORM (2026-07-26, the addressing ruling).** Verbatim: *"The spine
  is the flow of the form. We shouldn't be pedantic about the line numbers."* John named the
  disambiguation case himself - *"there might be 6 different SSNs for example. Which one?"* - and
  rejected positional numbering for repeatable rows. This REVISES the pinned invariant "IRS line
  numbers are the spine" in `AGENTS.md`. **Identity comes only via canonical addresses.**
- **THE BAR IS PRACTICAL RETRIEVAL (2026-07-26).** Offered two labeling schemes, John rejected the
  framing: *"I don't know that i care so much about the addressing scheme being perfect in some
  theoretical manner. We need to be able to refer to these things in a practical way... if you are
  asked about dependents... numbers, SSNs, whatever, we need to be able to pull it out of the
  graph data/metadata."*
- **FILER-PROVIDED IS A FAILOVER, NOT A DEFAULT (2026-07-31).** Verbatim: *"filer provided should
  be a failover rather than a default."* And: *"If I read 'Net proceeds' or 'Interest', my feeling
  is that this is just something to be provided by the filer. If the AI can't find it in the docs
  provided by the filer, it should ask."*
- **THE REVIEW QUEUE IS THE WRONG SHAPE (2026-07-29); this supersedes the reconciler.** There are
  ZERO human verdicts anywhere - the queue's `pending`/`deferred`/`accepted_local` are all
  machine-set, so the 198 re-points and 263 orphan records preserved no human judgement. The churn
  was an IDENTITY defect: 100% of 461 citation refs (keyed on generated sequence ids) churned
  while 1,921 field-control refs (keyed on canonical addresses) churned 0%. The graph already has
  stable cell identity; coverage should be a traversal, not a migrated file. **Verdicts must bind
  to CONTENT, not only to address.**
- **REVIEW PANEL LAYOUT (parked S6-2, still binding when UI work resumes).** The expression, the
  two instruction sources, the verdict controls, AND the comment box go TOGETHER; today the
  controls sit in the left rail while content is in the right river. Keep the 15/40/45
  proportions. Show the two instruction sources SEPARATELY (form face, instruction page - never
  concatenated).
- **VERDICT VOCABULARY - SUPERSEDED 2026-08-02. The four-button scheme is RETIRED.** John withdrew
  his own earlier ruling that "Pipeline defect" vs "Source pathology" is the reviewer's
  distinction, and he is right: **that is a DIAGNOSIS, and a reviewer has no way to make it.**
  Verbatim: *"as a human, i have zero insight into the why. I just know that this
  instruction/cell label is wrong."* Asking a reviewer to classify cause yields guesses carrying
  false authority.
  **The scheme is three OBSERVATIONS, not causes: accepted / commented-questioned / rejected.**
  That is already an ordinal confidence scale - the middle tier is "something looks off and I am
  not certain" - so do NOT add a separate numeric confidence field on top of it.
  **Reviewers are instructed NOT to comment when a cell is fine.** John: *"the last thing I would
  want is some guy saying 'good entry', 'this looks ok'."* Accept must be a single cheap action
  with no text box; the comment box appears only for the other two tiers, and **text is REQUIRED
  for those two** - a bare "rejected" is as useless as a cause the reviewer had to invent.
  Silence-as-approval is safe only if the queue records what was PRESENTED as well as what was
  acted on, so "reviewed and fine" stays distinguishable from "never shown".
  Diagnosis moves downstream to where the evidence lives: the checker proposes the cause from the
  witness disagreement, the maintainer confirms. **Reviewer detects; pipeline diagnoses.**
  Current code accepts only `confirmed`/`rejected` (`workbench/static/app.js`), so the middle tier
  is missing. The ledger is already address-keyed and append-only, so adding it is small.

## Open for Architect

- **M20-S36 denominator decision (raised 2026-08-03).** Logical-row assembly removes the measured
  label/span truncation cases, but it also exposes formula cues on `schedule_a_2025` line 15 and
  `schedule_1a_2025` line 36a, so the current formula set is 96 rows rather than the prior 94.
  Should the next provider leg use the fuller 96-row derivation set, or should formula selection
  remain frozen to the prior 94-row denominator for comparability? No provider result is claimed.
- **FOR JOHN - the two scoping calls that block the last 5 rows (raised 2026-08-03).** Both are the
  same shape as the Form 2441 question below, and answering all three together would clear every
  open scoping item in one pass.
  **(1) ANSWERED IN PRINCIPLE 2026-08-03 - John: yes, and via a harvester, not by hand.** The
  worksheets are in scope; the mechanism is S42. Two sub-calls remain his: the manifest schema change
  that lets a document declare a region of another acquired document (S42 step 4 reports it,
  implements nothing), and **his standing requirement that adding or removing a document, an
  instruction set, or a worksheet must never require an agent.** Original framing below.
  **(1) Are the tax worksheets in the base profile?** 6251 lines 13, 20 and 27 reference the
  Qualified Dividends and Capital Gain Tax Worksheet and the Schedule D Tax Worksheet. Both live in
  the IRS *instructions* rather than as standalone forms, and neither is a document in our graph,
  so those rows reference addresses that do not exist. Either model them as documents, or declare
  them out of scope and make the reference fail closed with a named reason instead of a confusing
  self-reference. The 1040 and Schedule D reference the same worksheets, so this recurs.
  **(2) Should the expression grammar carry a filing-status-dependent constant? PARTLY ANSWERED BY
  MEASUREMENT, 2026-08-03 - it is now a correctness question, not a cost one.** 6251 lines 18 and 39
  need a threshold ($239,100 / $119,550) and a subtrahend ($4,782 / $2,391) that both vary by filing
  status. Once S39 showed the model `taxpayer_2025_filing_status`, it reached for it unprompted and
  produced a rule that DOES cover married filing separately - but via a positional
  `LOOKUP_TABLE(node, 239100, 119550)` that maps to no rule and no roles, so the engine returns
  MISSING. The graph already contains the shape it needs (`lookup_capital_loss_limit`: one `key`
  edge plus one role-per-status edge), and the positional expression schema cannot express it. **So
  the question is no longer whether to carry the constant, but whether the grammar grows a
  role-keyed selection - and whether the four 6251 parameter nodes are hand-authored or pipeline-
  minted.** S40 step 3 asks for the mapping report that makes this decidable; the hand-author
  versus pipeline call remains John's under the prime directive.
- **FOR JOHN - what is next, once the scoping calls are made? (raised 2026-08-03.)** The corpus
  resolves 92 of 94 rows with 3 repairs, and the only remaining failures are model-quality issues
  on `form_6251_2025`. Chasing those means tuning a nondeterministic model for 2 rows, which is a
  poor trade. Three candidates, and it is a product call:
  **(a) The standalone reviewer.** Package the workbench so colleagues can review a form without a
  dev setup. Needs the three-tier verdict vocabulary (accepted / commented-questioned / rejected)
  and one proven round trip: a comment that survives a pipeline regeneration and shows up as input
  on the next run. That round trip has never actually happened, and it is the prime directive's
  core loop.
  **(b) Structure and association, S3b.** The geometric label path and the AcroForm-tree skeleton,
  which is what would make the 13614-C class of form reviewable at all. Today it derives nothing
  because it has no computed lines, but 297 of its cells are unaddressable by line number.
  **(c) The checker.** Adjudicate disagreements between the AcroForm tree, the geometry and OCR,
  and route them to a findings queue. John's view: set it up, then decide the payload from real
  disagreement instances rather than designing it in advance.
  Architect's recommendation is **(a)**, because it closes the human loop that everything else
  feeds, and because the reviewer surface is what turns (b) and (c) into something a person can
  act on.
- **FOR JOHN - is Form 2441 in the base profile? (raised 2026-08-02, blocks nothing else.)** The
  graph counts 18 documents but only 17 exist: `graph/2025/field_maps/form_2441_2025.yaml` carries
  a `document_id` for a form that was never acquired, its `mappings` are empty, its nodes are
  marked `optional_extension: true` with no base-profile printable placement, and the 1040 and
  Schedule 3 reference it in addresses and citations. Two coherent answers, and it is a product
  call rather than a technical one:
  **(a) Yes, 2441 is in scope** - acquire the PDF like any other form, give it a document record,
  and it joins the corpus and the derivation runs.
  **(b) No, it is an optional extension** - then the field map should stop contributing a document
  id to the count, so `validate 2025` reports the 17 documents that actually exist and no future
  corpus run trips over a phantom.
  Nothing is broken either way: the harness reports it as a load failure with a reason rather than
  skipping it silently, which is the S31 D10 behaviour doing its job.

## From Architect

- **M20-S41 TASK - RECONCILE THE DOCUMENT LISTS AND DRIVE THE HARNESS FROM THE MANIFEST (Architect,
  Claude Opus 5, 2026-08-03; John approved the sequencing).** Ledger: the RAN/NOT RUN rule, D10.
  **Deterministic, no provider leg. This is the prerequisite for S42 - a harvester needs a document
  list it can trust.**

  **Why. The Architect has been using the GRAPH as the corpus list, and that is circular.** Every
  "full corpus" run since S33, mine included, passed `graph.items("documents")` to the harness. The
  graph is partly the pipeline's OUTPUT, so a document that was never modelled can never enter the
  run. Measured today, the three lists disagree in every direction:

  | list | source | count |
  | --- | --- | ---: |
  | graph documents | `graph.items("documents")` | 18 |
  | acquisition manifest | `load_manifest()` | 21 |
  | acquired text | `.cache/raw/2025/*.txt` | 23 |

  - **In the graph, not in the manifest:** `form_2441_2025` - the phantom, which returned a load
    error on every corpus run.
  - **In the manifest, not in the graph:** `instructions_form_6251_2025`,
    `instructions_form_8949_2025`, `instructions_schedule_a_2025`, `instructions_schedule_b_2025`.
  - **Acquired but not declared:** `form_2441_2025`, `instructions_form_2441_2025`.

  `instructions_form_6251_2025` is 80,318 characters we already hold, naming the Qualified Dividends
  and Capital Gain Tax Worksheet 20 times - and 6251 lines 13, 20 and 27 are the only unresolved
  rows in the corpus, failing because they reference that worksheet. **The evidence was on disk and
  the document list excluded it.**

  **Step 1 - a reconcile check.** Add a deterministic function (suggested home:
  `tax_graph/acquire/reconcile.py`, beside `manifest.py` and `citation_check.py`) that reports each
  of the three set differences by name, never as a count alone. **The raw store is gitignored, so CI
  cannot depend on it:** the manifest-vs-graph legs must run without `.cache/`, and the raw leg must
  degrade to `skipped` with a stated reason rather than failing. Report exactly the six ids above as
  the current baseline.

  **Step 2 - surface it.** Wire it into `workbench.cli preflight` and/or `tax_graph.cli validate`
  (pick one, say which and why). A phantom or an orphan must appear as a NAMED finding. **Do not
  make it a hard failure in this round** - the six discrepancies are real and pre-existing, and
  failing the gate on them would block every other round. Report them; John rules on 2441.

  **Step 3 - drive the harness from the manifest.** `experiments/derive_cells_s25.py` defaults to
  `form_1040_2025` and takes repeatable `--document`. Add a manifest-driven default so a corpus run
  covers what we DECLARED, not what we already modelled. Keep `--document` working. A document in
  the manifest that cannot be loaded must be reported per-document with a reason, which is the
  existing D10 behaviour and it already works.

  **Step 4 - rerun the corpus ONCE with the new list and report the new denominator.** Expect more
  documents attempted and probably more empty ones; the four instruction documents may well derive
  zero rows, exactly as `instructions_form_1040_2025` does today. **That is a finding, not a
  failure** - it tells us instruction documents produce no derivation rows, which is precisely why
  S42 exists. Report attempted/derived/repaired/errored against the OLD 96-row denominator as well,
  so the S38-S40 numbers stay comparable.

  **Do not:** author or edit anything in `graph/2025/`; add or remove manifest entries (John rules
  on 2441 and on the undeclared acquisitions); make the reconcile a hard gate; touch the derivation
  validators. **Stop conditions:** any diff in the protected directories; `derive_cells` acquiring a
  disk write; any harness output landing inside the repository. Tier 3. ASCII, `git diff --check`,
  module-form `validate 2025`, preflight with `legacy_mined` explicit (394), strict citations (36).
  **ONE local commit.**

- **M20-S42 TASK (QUEUED, DO NOT START UNTIL S41 IS ACCEPTED) - HARVEST A WORKSHEET, WITH QDCGT AS
  THE CANARY (Architect, Claude Opus 5, 2026-08-03; John's design call).**

  **Why, and why an end anchor was REJECTED.** The Architect proposed declaring a worksheet as a
  region between a start and an end anchor. **John rejected it and he is right: an end anchor is
  position-based identity wearing a different hat**, the exact defect this phase has now ruled
  against three times (S28 `quote_span_id`, the review-queue churn, the S3a/S3b resolver ruling).
  Worse, it would formalise the error already in the graph. Measured: the hand-authored QDCGT model
  has all 25 lines and all 13 constants correct, and **zero nodes anywhere in the graph for Form
  2555 or the Foreign Earned Income Tax Worksheet** - even though the worksheet's own text redirects
  line 1's source and line 25's destination when Form 2555 is filed. Whoever transcribed it took the
  numbered grid and dropped the footnotes, which are conditional routing, not annotation. And Form
  2555 was the most common outside-the-corpus reference in the derivation runs, five rows: **the
  model kept reaching for what the transcription lost.**

  **Step 1 - a pure harvest stage.** Same shape as `derive_cells`, which is the pattern that works:
  a pure function with **zero disk writes**, taking acquired instruction text plus a target, and
  returning a worksheet document, its `worksheet_field` nodes, edges, and citations. Every emitted
  object carries a **verbatim quote checked in code** - that check is what exposed the 13 paraphrased
  QDCGT citations, and it is what stops a harvester from inventing the way a human did. Output goes
  to drafts and through the workbench. **Nothing is promoted in this round.**

  **Step 2 - extent is DISCOVERED, not declared.** No end anchor. A worksheet is self-describing, so
  validate completeness deterministically: numbered lines 1..N contiguous with no holes; the
  terminal line states its own destination (QDCGT line 25: *"Also include this amount on the entry
  space on Form 1040 or 1040-SR, line 16"*); every footnote marker in the harvested region resolves
  to a footnote. Fail closed and report when any of those does not hold. The start anchor survives
  only as the NAME - the addressing handle - never as a slice boundary.

  **Step 3 - the canary, with a falsifiable prediction.** Run it on
  `instructions_form_1040_2025` targeting the Qualified Dividends and Capital Gain Tax Worksheet and
  diff against the existing hand-authored graph:

  | expected | why it is a real test |
  | --- | --- |
  | 25 lines, contiguous | matches the existing 44-node model |
  | 13 constants | already verified correct against IRS text; a mismatch means the harvester is wrong |
  | 13 citations, VERBATIM | the current ones are paraphrase and fail `check_graph_citations` today |
  | Form 2555 conditionals on lines 1 and 25 | **NEW** - the human missed them |

  **Report the diff honestly in both directions.** If the harvester misses the footnotes too, say so
  - that is a prompt finding worth having, not a failure to hide. **Do not tune the prompt against
  the hand-authored graph until the first honest attempt is reported**, or the canary measures
  nothing.

  **Step 4 - report what the manifest would need, implement no schema change.** A worksheet has no
  standalone PDF URL, and `schemas/manifest.schema.json` requires `url` matching
  `^https://www\.irs\.gov/pub/irs-(pdf|prior)/[fip][a-z0-9-]+\.pdf$`. The `kind` enum ALREADY
  contains `worksheet` in both `manifest.schema.json` and `document.schema.json`, and `node.schema.json`
  already has `worksheet_field`. **The vocabulary exists end to end; only the source field cannot
  express a region of another document.** Report the minimal change (a `source_document_id` plus a
  start anchor, with `url` required only when `source_document_id` is absent) and stop. **John rules
  on the schema change** - it is the self-serve surface, and his stated requirement is that adding or
  removing a document, an instruction set, or a worksheet must not require an agent.

  **Do not:** author or edit anything in `graph/2025/`; promote a draft; change any schema; let the
  harvester write outside drafts; tune against the known answer before reporting the first attempt.
  **Stop conditions:** any diff in the protected directories; any harvest function acquiring a disk
  write outside the draft path; a citation emitted that is not verbatim in the acquired text.

- **M20-S43 TASK (QUEUED BEHIND S41/S42; SPEC IS COMPLETE AND STILL STANDS) - TYPE THE OPERANDS,
  AND MAKE THE WARNING WORTH READING (Architect, Claude Opus 5, 2026-08-03).** Ledger: the RAN/NOT RUN rule, D9, D6. **Small, and both parts are already measured
  in Current round - do not re-diagnose.**

  **Step 1 - `REQUIRE_INPUT` must not raise `unmapped_operation`.** It is the answer the prompt
  instructs the model to give for a line that is not computed, so it has no rule by design. It is 8
  and 9 of the 12 and 14 warnings in my two runs. Exclude it at the source in
  `_projection_warnings` (not by filtering downstream), and add a test that asserts a REQUIRE_INPUT
  row warns zero times while an `IF_ELSE` row still warns once. Expected result: the warning drops
  to the three real rows - 1040 line 34, 6251 lines 18 and 39.

  **Step 2 - the expression grammar is type-free, and that is now the top correctness hole.**
  Measured, status `derived`, zero failures:
  `if_else(node[taxpayer_2025_filing_status], 0, if_else(line 12, 119550, ...), if_else(line 12, 239100, ...))`.
  `IF_ELSE` compares a condition AMOUNT to a threshold AMOUNT; a filing-status enum cannot sit in
  either slot. **Add a deterministic operand-type check, in code, using inventory metadata you
  already have.** A `{"node": ...}` operand resolves to a `node_type` and, for parameters, a
  `constant_value`; a node that is a non-numeric `fact` must be rejected in any slot that the
  positional semantics define as an amount - `IF_ELSE` condition and threshold, `COMPARE` left and
  right, and the arithmetic operations. **This is a HARD failure, not a warning** - unlike the
  `zero_floor` and Form 4684 cases, the model is not offering a better answer here, it is offering a
  meaningless one. Name the kind `operand_type_mismatch` and give the message the slot name and the
  node's type, so a repair prompt can act on it.
  **Report what you cannot decide deterministically rather than guessing.** If the inventory does
  not record enough about a node to classify it (no `value_type`, no `constant_value`), say which
  nodes those are and leave them passing rather than inventing a rule.

  **Step 3 - the same run also produced `multiply(line 17, lookup_table(status, 0.26, 0.26))`,**
  a status lookup whose branches are identical. Step 2 does not catch it: the slot is an amount and
  the lookup returns one. **Report only** - is a degenerate lookup worth a warning, or is it noise
  that will dilute Step 1's cleanup? Recommend one and say why. Implement nothing for this.

  **Step 4 - rerun the corpus TWICE and report both, per S40's precedent.** Numbers to hold:
  **derived 92/91, repaired 1-2, errored 3, resolved 93.** Report `validator_warnings_by_kind` for
  both runs so the Step 1 drop is visible, and print the 6251 line 39 expression from each run -
  that is the row where the type error appeared once and not the other time, so one clean run proves
  nothing. **State plainly whether either run still produces a status enum in a numeric slot.**

  **Do not:** author or edit anything in `graph/2025/`; add rule or role mappings (still not
  authorized - the S40 mapping report stands and John has not ruled); turn `unmapped_operation` into
  a hard failure; weaken `missing_floor` or the external-reference discriminator; re-add Azure to
  `llm.provider_routing.only`; let a `contributed` comment reach the model; build UI; promote
  anything.
  **Stop conditions:** any diff in the protected directories; `derive_cells` acquiring a disk write;
  any harness output landing inside the repository; derived below 91 on both runs. Tier 3. Declared
  files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`, module-form `validate 2025`,
  preflight with `legacy_mined` explicit (394), strict citations (36).
  **ONE local commit** - and run `git status` first; do not commit paths you did not touch.

## Worker status

- **M20-S41 implementation complete locally; awaiting Architect acceptance.** Added the
  read-only `tax_graph.acquire.reconcile_document_lists` report with named graph/manifest/raw
  differences and an explicit skipped raw leg. Wired the report into module-form `validate`
  because document inventory is an acquisition/source concern, not a review projection. The
  derivation harness now defaults to the manifest's declared document order while retaining
  repeated `--document` selection. No manifest, graph, field map, or draft artifact was edited.
- **RAN:** `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\_pytest_temp'; .\.venv\Scripts\python.exe -m pytest tests/test_m20_s41.py -q` -> 5 passed.
- **RAN:** `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\_pytest_temp'; .\.venv\Scripts\python.exe -m pytest tests/test_acquire_manifest.py tests/test_m20_s31.py tests/test_cli.py tests/test_runtime_light_m1.py tests/test_derive_cells_m20.py -q` -> 74 passed.
- **RAN:** `.\.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> exit 0; graph integrity OK; named baseline differences are `form_2441_2025`, four undeclared instruction ids, and `form_2441_2025` plus `instructions_form_2441_2025` in raw-only.
- **RAN:** `.\.venv\Scripts\python.exe -m workbench.cli --root . --year 2025 preflight` with read-only escalation -> exit 0; `derived manifest entries=18`, `derived cells=2120`, `legacy_mined=394`.
- **RAN:** `.\.venv\Scripts\python.exe tools\check_ascii.py` -> `ASCII check OK`.
- **RAN:** `git diff --check` -> exit 0; protected `graph/2025/{nodes,edges,rules,field_maps}` diff -> empty.
- **RAN:** `.\.venv\Scripts\python.exe experiments\derive_cells_s25.py --root . --year 2025 --output-dir <external> --no-provider` -> all 21 manifest documents prepared in manifest order.
- **NOT RUN:** live provider corpus leg; the Worker sandbox has no outbound network, so no attempted/derived/repaired/errored denominator is claimed for S41.
- **Open questions:** none for S41; John still rules on the queued S42 manifest schema change and Form 2441 scope.

## Architect decisions

- **THE REVIEW LOOP, as designed with John 2026-08-03. This is the shape S37-S39 build toward.**
  - **The FORM is the unit of approval, not the cell.** John: *"I view the form as a unit."* No
    per-cell sign-off across ~1,921 controls; findings route attention to the handful that need it.
  - **Try again, not reject, is the main action.** The reviewer edits a comment, re-derives that one
    cell live, and iterates. Reject is the escape hatch for a cell that will not converge.
    Feasibility measured before committing to it: **6.0s for one row cold, ~2.7s for the model call
    alone**; a warm server does not repeat the setup.
  - **This is only safe because `derive_cells` is pure.** The zero-disk-write gate defended every
    round since S24 is what lets a request handler call it with a modified evidence packet.
  - **The stored comment is one that has been VERIFIED to work.** Because the reviewer tunes wording
    until the cell comes out right, the ledger accumulates known-good instructions rather than
    hopeful ones. This is strictly better than a comment written blind and batched.
  - **Two classes of comment.** `contributed` is raw input from another reviewer - John's example:
    *"this is broke"* - retained and shown but NEVER sent to the model. `curated` is the lead's
    edited instruction; only curated comments feed derivation. Turning the first into the second is
    the irreplaceable human act.
  - **Latest curated comment per address wins**, with full history retained for audit and display.
    Keeps the prompt bounded as comments accumulate over years.
  - **A comment must never override a validator.** It steers interpretation; it cannot talk the
    model past `quote_not_verbatim`, `operand_not_printed` or `self_reference`.
  - **Show nondeterminism rather than hide it.** Try-again with an unchanged comment can return a
    different answer - measured repeatedly at `temperature: 0`. The UI must distinguish "you changed
    the comment" from "same comment, fresh attempt", or reviewers tune toward superstition.
  - **Convergence needs a measure and an escape hatch.** Track rounds-to-approval per cell and flag
    anything reopened more than twice; at that point it needs a human decision, not another pass.
  - **The reviewer's scarce resource is attention.** John: apathy is a bigger risk than
    over-control. Findings-first ranking is therefore not polish - it is what makes a contributor's
    fifteen minutes productive. Measure findings raised vs findings upheld, and minutes per upheld
    finding; that is the ratchet the phase plan asks for and we have never been able to compute.
  - **Audited 2026-08-03: NONE of this is surfaced today.** The workbench API is six calls - list
    documents, load cells, load/save session, save progress, submit verdict. There is no findings
    endpoint, no per-cell problem badge, and no ranking. Derivation quality IS generated every run
    (per-row failures, warnings, repair events) and is written to a temp report and discarded. S38
    carries it into the surface.


- **S3a -> S3b: YES, the structure step owns a deterministic outline adapter. S3a regeneration
  stays blocked until it lands. (Answered 2026-08-02; open since 2026-07-28.)** The bare positional
  index is not enough, and the reason is the one this phase already discovered twice: **identity
  must be resolved in CODE from a stable anchor, never from position.** An exact string offset that
  can land on repeated anchor text in another semantic row is position-based identity - the same
  class of defect as keying the review queue on generated sequence ids (100% churn) and as asking
  the model to name a `quote_span_id` (fixed in S28). The adapter belongs to S3b because
  `PHASE_M20.md` section 3 is explicit that this pipeline never had an independent structure layer
  and that building one IS S3b; an outline is structure, not regeneration. Requirements: build it
  from the corrected text plus `line_anchors` plus page/geometry, resolve each anchor to exactly
  one semantic row, and **fail closed at row granularity** when an anchor is ambiguous - matching
  the S2d/S2e span-resolver ruling. Do not promote a draft or hand-edit a citation or label to get
  past an ambiguity.

## Recent rounds (condensed; full narration in git history - `git show <hash>`)

- **M20-S40 (`e032cfd`, Architect-verified):** `missing_floor` accepts a zero-valued `parameter`
  node, the prompt inventory is scoped per document (26 for 1040, 3 for Schedule D, 1 elsewhere),
  unmapped projection operations became warnings, and the harness reports expressions and external
  mints. Closed the S39 regression: derived 92/91 across four runs. Delivered the operation-mapping
  report with no protected-set change. Its warning surfaced the type-free grammar hole -> S41.
- **M20-S39 (`ef39dfe`, Architect-verified, REWORK):** the node inventory reached the prompt, the
  unseen-form hard fail became a minted unresolved required input, and the four 6251 parameter nodes
  were reported rather than invented. Corpus fell to derived=87 on two runs; A/B isolated it to
  `form_1040_2025_zero_floor` being rejected by a `missing_floor` check that only accepts a literal
  zero. Placement was tested and ruled out. Reworked as S40.
- **M20-S38 (`514443e`, Architect-verified):** `{"node": ...}` operand plus positional conditional
  semantics; best first-attempt corpus to that point (derived=92, repaired=1, resolved 93/96), and
  6251 lines 18 and 39 derived with no repair. Its new `operand_document_not_found` hard fail
  rejected the correct Form 4684 answer on Schedule A line 15 - fixed in S39 step 2.
- **M20-S33 (`771d169`, Architect-verified):** first full-corpus live run. 93 of 94 rows resolve
  (derived=79, repaired=14, gapped=0, errored=1); all eight empty documents correctly empty; 1040
  identical across two runs. Diagnosed the repairs to `operand_not_printed` on IRS ranges with
  holes, against an inventory the prompt never shows the model.
- **M20-S32 (`70e8b6d`, Architect-verified):** prompt placeholders moved from `{name}` to
  `<<name>>` with a shared fail-closed `render_prompt`, so JSON examples need no escaping; the
  substring prompt assertion was replaced by a render test over every file in `prompts/`.
  Architect slice: 1040 17/17, Schedule A 7/7, **Schedule D 3/3**.
- **M20-S31 (`fb2833e`, `a466a9e`; step 3 `e18767f` rejected):** Schedule D carve-out deleted and
  `document_id` dropped from `_formula_outline_nodes`; a zero-row document now reports
  `status: empty` with outline and anchor counts. Step 3's prompt edit broke rendering for every
  form and was superseded by S32.
- **M20-S30 (`00b5f38`, Architect-verified):** harness takes repeatable `--document`, refuses
  in-repo output, and reports per-document failures; REQUIRE_INPUT self-operands exempt from
  `operand_not_in_quote`. Architect slice: 1040 17/17, Schedule A 7/7, Schedule D 0 - the zero
  traced to a hardcoded carve-out, 2/3 with it lifted.
- **M20-S29 (`fca0a4a`, Architect-verified):** `_line_mentioned` handles singular, plural-list and
  range references; `clean_form_face_text` truncates instead of reconstructing, restoring the
  substring invariant. Live 1040 17/17 with warnings 37 -> 2. Step 3 blocked - single-document
  harness.
- **M20-S28 (`12240ef`, Architect-verified):** the three deterministic last-five-row defects -
  cleaned evidence text, REQUIRE_INPUT exempt from the self-reference check, `quote_span_id`
  resolved in code and dropped from the schema. Real 1040 **17/17**.
- **M20-S27 (`8027161`, Architect-verified):** `printed_lines` carries all 59 printed anchors (was
  17 formula-only); `operand_not_printed` collapsed 31 -> 1; per-row span-id enum; generic
  `provider: openai` honors `llm.base_url`. Real 1040 12/17.
- **M20-S26 (`b3e102b`, Architect-verified):** `missing_instruction_text` -> `missing_evidence`
  (face OR instruction), so `attempted` went 4 -> 17; ownership issues DROP the section instead of
  killing the row; label contamination fixed 17/17. **First real expressions in M20**, including
  the floors the flat schema had been dropping (`line 15 -> max(line 11b - line 14, 0)`).
- **M20-S25 (`ff62119`, Architect-verified):** property validators and repair-once. Architect then
  diagnosed derived=0 against real data: the instruction booklet does not document computed lines,
  the form face does - which set up S26.
- **M20-S24 (`e6e94e3`):** `derive_cells` as a pure function with expression trees.
- **M20-S23 (`0831694`):** the `instruction_sections` artifact and its join.

## Latest verification

- **M20-S40 (2026-08-03, Architect live):** two full corpus runs (output under `C:\tmp`, outside the
  repo), attempted=96 both, derived 92 and 91, repaired 1 and 2, errored 3 both, resolved 93 both;
  `form_1040_2025` 17/17 in both. Focused suites 67 passed on a short temp root; ASCII OK;
  `git diff --check`; `validate 2025` (18 documents, 441 nodes, 409 edges, 401 citations); preflight
  `units=2224 derived_cells=2120 legacy_mined=394`; protected set byte-identical across
  `4935053..e032cfd`. `unmapped_operation` 12 and 14, of which 8 and 9 are REQUIRE_INPUT; the true
  signal is three rows in both runs. Exactly one external mint in both runs
  (`schedule_a_2025` line 15 -> `form_4684_2025_root_line_18`).
- **M20-S39 (2026-08-03, Architect live):** two full corpus runs, attempted=96 both, derived=87 both,
  repaired 6 / 5, errored 3 / 4, resolved 93 / 92. Focused suites 60 passed on a short temp root;
  ASCII OK; `git diff --check`; `validate 2025` (18 documents, 441 nodes, 409 edges, 401 citations);
  protected set byte-identical across `514443e..ef39dfe`. Inventory verified at 37 parameter/fact
  nodes. Schedule A line 15 recovers `copy(form_4684_2025:18)` and mints
  `form_4684_2025_root_line_18`; both fabrication shapes still rejected. Floor A/B on five rows
  across three forms: 1 of 24 clean with `zero_floor` in the inventory, 12 of 12 clean without.
  Placement A/B on two rows: 0 of 8 clean either way.
- **M20-S33 (2026-08-02, Worker live, Architect-verified):** full corpus, 18 ids, 17 loadable.
  attempted=94, derived=79, repaired=14, gapped=0, errored=1. Two identical 1040 runs both 17/17
  with no validator failures. ASCII, `git diff --check`, `validate 2025` (441 nodes, 409 edges,
  401 citations), preflight `legacy_mined=394`, strict citations 36, protected set empty diff.
- **M20-S32 (2026-08-02, Architect):** live three-form slice all green - `form_1040_2025` 17/17,
  `schedule_a_2025` 7/7, `schedule_d_2025` 3/3, zero validator failures and zero warnings on all
  three; 102 passed on a short temp root; protected set byte-identical.
- **M20-S30 (2026-08-02, Architect):** live three-form slice - `form_1040_2025` 17/17,
  `schedule_a_2025` 7/7 (matches the S14 labeled set), `schedule_d_2025` 0 attempted;
  `operand_not_in_quote` 0 on both non-empty forms; protected set byte-identical; working tree
  clean after the in-memory carve-out probe.
- **M20-S29 (2026-08-02, Architect):** focused suite 79 passed on a short temp root; ASCII;
  `validate 2025` (18 documents, 441 nodes, 409 edges, 401 citations); protected set
  byte-identical across `12240ef..fca0a4a`; live 1040 17/17 with `operand_not_in_quote` 37 -> 2;
  substring invariant verified directly on all four cleaning branches.
- **M20-S28 (2026-08-02, Architect):** focused suite 96 passed on a short temp root; ASCII;
  `git diff --check`; `validate 2025` (18 documents, 441 nodes, 409 edges, 401 citations);
  preflight units=2224, derived cells=2120, `legacy_mined=394` (ratchet unchanged); strict
  citations `checked=401 strict_mismatches=36`; protected set byte-identical; live 1040 17/17.
- **Preflight note:** the sandbox run hits a known pre-existing `WinError 5` on
  `graph/2025/_drafts/form_1040_2025` (a draft ACL, not a regression). The same read-only command
  with escalation passes.
- Prior phase closes: `plans/archive/PHASE_M13.md` and earlier - each with a close note.

## History

Everything before M20-S23, and all per-round Worker narration, lives in git history. This file was
pruned from 7,520 lines on 2026-08-02 at S28 acceptance; `git show 12240ef:plans/AGENT_HANDOFF.md`
is the last unpruned copy. Earlier prune: 2026-07-23, from 1,198 lines, for public-repo prep.
Durable rulings were carried forward into **Binding rulings** above rather than deleted; A9
rulings remain pinned in `plans/PHASE_M15.md`; the defect ledger (D6, D9, D10, D12, D13, D14) is
in `AGENTS.md`.
