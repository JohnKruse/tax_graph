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

**BALL: WORKER - M20-S46 (MAKE CONDITIONALS AND LOOKUPS EXECUTABLE).** Task block under
**From Architect**. **S45 is ACCEPTED at `467685c`** - the verdict bridge exists, dry-run by
default, and the one real ledger record correctly reports STALE rather than applying.

**Why S46 now.** John pushed on it directly: *"shouldn't we have a calc complete operations set with
conditionals... We need to model things that humans do... full stop."* He is right, and the
Architect's earlier framing was misleading. **The graph is NOT deficient** - it already holds two
`IF_ELSE` rules and four `LOOKUP_TABLE` rules, and both run today. The gap is two dictionaries in
`tax_graph/extract/cells.py` that never map the AI's conditionals onto the rules that exist, so
three rows per run derive cleanly and compute nothing. S46 closes it, measuring the required
vocabulary from evidence first rather than adding operations speculatively.

**Known gaps, deliberately NOT S46:** the harvester emits no computed nodes or `CALCULATES` edges,
so it does not harvest arithmetic; and the review vocabulary is two-state, queued as S47.
**Rollover policy and run alerting** are pinned at `docs/engineering-plan.md` -> Year rollover
(TY2026), seam 6. **Notation ruling** is under Current round: borrow the decision-table shape for
lookups, adopt no formalism.

## Current round

**M20-S46 WORKER STATUS (2026-08-04): implementation ready; live corpus UNVERIFIED.** The local
slice closes the projection gap without changing the graph, operation enum, or disk-writing
boundary. The remaining acceptance gate is two live provider corpus passes, which could not run
in this sandbox.

**Step 1 measurement, RAN from the S44 96-row reports plus the harvested QDCGT worksheet:** the
rows emitted 9 operation kinds: `SUM` 42, `SUBTRACT` 27, `COPY` 7, `MAX` 15, `IF_ELSE` 4,
`REQUIRE_INPUT` 8, `MULTIPLY` 12, `MIN` 5, and `LOOKUP_TABLE` 4. The row evidence contained
18 floor/cap cues, 28 conditional cues, 2 band/bracket cues, and 41 aggregation cues. QDCGT
harvest measured 25 lines, 13 constants, 13 citations, 42 edges, and conditional routes on
lines 1 and 25. No new operation enum is demanded.

**Implementation:** `RULE_FOR_OP` maps `LOOKUP_TABLE` to the existing `lookup_selected_value`.
Lookup leaf operands now carry a lowercase `role`, with exactly one `key` and unique named
branches such as `default` and `married_filing_separately`; bare ordered lookup lists fail
closed. `IF_ELSE` maps to the existing `if_less_than_currency` or `if_greater_than_currency`
from deterministic wording in the row evidence. Ambiguous direction is a named warning, never
a guessed rule. The prompt and expression renderer expose the borrowed decision-table shape.

**Canary rows, fixture-only:** 1040 line 34, 6251 lines 18 and 39 all derive through
`derive_cells`, project with real rule ids and roles, and produce no `unmapped_operation` or
unresolved-direction warning. This proves the local boundary; it is not a live model result.

**Tests and gates:**

```
RAN: $env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\08\04\019fcd36-c747-79a1-8005-8d270643f7ad\pytest_s46_focus'; .venv\Scripts\python.exe -m pytest tests\test_derive_cells_m20.py tests\test_m20_s31.py -q -> 65 passed, 1 warning.
RAN: $env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\08\04\019fcd36-c747-79a1-8005-8d270643f7ad\pytest_s46_focus'; .venv\Scripts\python.exe -m pytest tests\test_tax_liability_m11.py -q -> 3 passed, 1 warning.
RAN: $env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\08\04\019fcd36-c747-79a1-8005-8d270643f7ad\pytest_s46_focus'; .venv\Scripts\python.exe -m pytest tests\test_extract_m4.py tests\test_prompt_experiment_m20.py tests\test_worksheet_harvest_m20.py -q -> 38 passed, 1 warning.
RAN: $env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\08\04\019fcd36-c747-79a1-8005-8d270643f7ad\pytest_s46_focus'; .venv\Scripts\python.exe -m pytest tests\test_review_semantics_remaining_m15.py -q -> 8 passed.
RAN: .venv\Scripts\python.exe tools\check_ascii.py -> ASCII check OK.
RAN: git diff --check -> clean.
RAN: .venv\Scripts\python.exe -m tax_graph.cli validate 2025 -> exit 0; 18 documents, 441 nodes, 409 edges, 401 citations; graph integrity OK; six reconcile differences named.
RAN: .venv\Scripts\python.exe -m workbench.cli --root . --year 2025 preflight -> exit 0; review preflight passed; units=2224, derived_cells=2120, legacy_mined=394.
RAN: git diff --stat -- graph/2025/nodes graph/2025/edges graph/2025/rules graph/2025/field_maps -> empty.
```

**Live corpus evidence:**

```
RAN: .venv\Scripts\python.exe experiments\derive_cells_s25.py --root . --year 2025 --output-dir <external s46_run1> -> exit 124; command timed out after 600213 ms. This is NOT a passing corpus run.
RAN: .venv\Scripts\python.exe experiments\derive_cells_s25.py --root . --year 2025 --document form_6251_2025 --output-dir <same external s46_run1> -> exit 0; rows_attempted=29, derived=0, errored=29; every row reported `LlmUnavailable: OpenRouter request failed: Connection error`.
NOT RUN: second live corpus pass -> provider unavailable. An escalated provider attempt was rejected because explicit user authorization is required before transmitting local pipeline evidence to the external provider.
```

**Open for Architect / John:** authorize the external live-provider corpus run, or direct a
fixture-only S46 acceptance. Until then, S46 is not complete and no corpus number is claimed.

### Prior accepted round

**M20-S45 ACCEPTED (Architect, Claude Opus 5, 2026-08-04) at `467685c`. The bridge exists, and the
safety property it was built for fired on the first real record.**

`tax_graph.review.apply_address_verdicts` plus `review apply-address-verdicts`, **dry-run by
default** - `--apply` is required to write. It reuses the existing `_apply_graph_review` rather than
adding a second applier, which was the explicit instruction: a second parallel path is how this gap
was created in the first place.

**THE ONE REAL VERDICT IS STALE, AND THAT IS THE ROUND WORKING.** I ran the live dry-run myself:

```
address verdicts: 1 | would apply: 0 | stale: 1 | unresolved: 0 | ambiguous: 0
  2025/document=form_1040/line=1z/control=amount: stale
    reviewed fingerprint: 151f0df2...  current fingerprint: e270b15d...
```

The single human verdict in the ledger was recorded against content that has since changed, so it
correctly does not apply. **This is exactly the property the M15 path lacked** - it would have
blessed changed content because it keyed on a churning id and never compared content at all.
`git status -- graph/2025/` is empty after the run.

**Address resolution verified.** `2025/document=form_1040/line=1z/control=amount` resolves to
`form_1040_2025_root_line_z`, whose label reads "Line 1z: Add lines 1a through 1h". The node id
dropping the `1` is a pre-existing mined-label oddity, not an S45 defect, and the resolution is
correct.

**Gates:** 29 passed on a short temp root, ASCII OK, `git diff --check` clean, protected set
byte-identical across `86f6c01..467685c`.

**VOCABULARY GAP REPORTED, NOT INVENTED (correct - this was Step 3).** The ledger schema accepts
arbitrary judgement strings; the review surface emits only `confirmed` and `rejected`; there is no
`problem` state anywhere. The bridge applies `confirmed` only and reports the rest as unsupported
without writing. **John's model is accepted / rejected / problem**, so the vocabulary needs one
small round before non-confirming flags can land. Queued below, deliberately not folded into S46.

## Architect decision - notation

John, 2026-08-04: *"do what makes sense. We are not boiling the ocean here. I just don't want to
reinvent and perfect the wheel either."*

**BORROW THE DECISION-TABLE SHAPE FOR LOOKUPS. DO NOT ADOPT A FORMALISM.** Prior art exists and two
pieces are on point: **DMN** decision tables (named input/output columns plus a hit policy, designed
for exactly "if income is in this band, the rate is that"), and **Catala** (a language for encoding
tax law with the legal text attached, philosophically closest to our citation discipline). We also
already touch **PolicyEngine-US** as a parameter witness (`tax_graph/oracles/pe_liability.py`,
`verify parameter-diff`), currently `policyengine_enabled: false`.

**Ruling:** take the decision-table STRUCTURE for the lookup problem and nothing else. Our lookups
break because arguments are a bare ordered list - `(status, 239100, 119550)` - with no way to say
which value belongs to which status; a decision table names them structurally, which is a solved
problem we should not re-solve. **Do not adopt DMN, FEEL, or Catala wholesale.** The property that
makes this project checkable is a narrow emission vocabulary a deterministic validator can verify;
a general-purpose expression language widens exactly what we need kept narrow. Revisit only if a
real form defeats the borrowed shape.

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

- **M20-S46 TASK - MAKE CONDITIONALS AND LOOKUPS EXECUTABLE (Architect, Claude Opus 5, 2026-08-04).**
  Ledger: the RAN/NOT RUN rule. **This is the round that closes the gap John pushed on: the graph
  models these operations and the pipeline cannot reach them.**

  **Why, stated precisely so nobody repeats the Architect's earlier overstatement.** The GRAPH is not
  deficient. `graph/2025/rules/core.yaml` already holds 15 rules including **two `IF_ELSE` rules**
  (`if_less_than_currency`, `if_greater_than_currency`) and **four `LOOKUP_TABLE` rules**
  (`lookup_capital_loss_limit`, `lookup_selected_value`, `lookup_selected_value_required`,
  `lookup_tax_table_amount`). Both run today: 1040 line 16 flows through
  `if_greater_than_currency`, and the Schedule D capital loss limit is a live filing-status lookup.
  **The gap is `RULE_FOR_OP` and `ROLE_FOR_OP` in `tax_graph/extract/cells.py`**, which list ten
  arithmetic operations and omit the conditionals and lookups, so an AI-written conditional emits
  `no reusable rule for operation IF_ELSE` and produces no rule at all. Measured cost: three rows
  per corpus run - 1040 line 34, 6251 lines 18 and 39 - derive cleanly and compute nothing.

  **Step 1 - measure the required vocabulary before adding anything.** Do not add operations
  speculatively. Across the 96 corpus rows plus the harvested QDCGT worksheet, report what the
  forms' own text actually demands and what the model actually emits: floors, conditions,
  band/bracket tables, ranges, aggregation over repeated rows. **Report the counts and name any
  operation the evidence demands that the enum lacks.** If the evidence shows the current enum is
  already sufficient, say so - that is a valid and useful outcome.

  **Step 2 - map the conditionals.** Add `IF_ELSE` (and the rest of the conditional family, if step
  1 shows the evidence demands them) to `RULE_FOR_OP` and `ROLE_FOR_OP`. **The open design question
  is comparison direction:** there are two `IF_ELSE` rules and the AI's four positional arguments do
  not say which comparison is meant. Two candidate answers - the model names the direction, or it is
  resolved in code from the row's own evidence text ("is more than", "is less than", "or less").
  **Recommend one with reasoning and implement it; do not implement both.** Given this phase's
  history, resolving deterministically from evidence is the safer default and should be preferred
  unless step 1 shows the wording is unreliable.

  **Step 3 - the lookup shape, borrowed not invented (John's ruling, see Architect decision).** Take
  the DMN decision-table STRUCTURE: named inputs and outputs rather than a bare ordered list. Our
  lookups are unmappable because `(status, 239100, 119550)` cannot say which value belongs to which
  status, while the engine selects by matching a role name to the status value. **Extend the
  expression format minimally so a lookup can name its branches**, then map `LOOKUP_TABLE` to
  `lookup_selected_value` with a `key` role plus one role per named branch, matching the shape
  `lookup_capital_loss_limit` already uses in `graph/2025/edges/capital-gains.yaml`. **Do not adopt
  DMN, FEEL, or Catala wholesale** - structure only. A prompt change needs a RENDER test (S32) and
  the `prompts/` render test must still pass.

  **Step 4 - prove executability, not just validation.** For 1040 line 34 and 6251 lines 18 and 39,
  show `expression_to_graph` now emits real rules with real roles and **zero** `no reusable rule`
  findings, and that the projected nodes and edges match the shape the engine consumes. **A clean
  validator result is not the deliverable here; a rule the engine can run is.** Report the
  `unmapped_operation` warning count before and after - it was 9 and 7 in the S44 runs.

  **Step 5 - rerun the corpus twice and report both.** Numbers to hold: **derived 92, resolved 93**.
  Print the 6251 line 18 and 39 expressions from each run and state whether each is now executable.

  **Do not:** author or edit anything in `graph/2025/` - the rules you need already exist, and if
  step 1 proves a genuinely new rule is required, REPORT it and stop rather than authoring it;
  adopt a general-purpose expression language; widen the operation enum without step 1 evidence;
  weaken any validator; promote anything. **Stop conditions:** any diff in the protected
  directories; `derive_cells` acquiring a disk write; the corpus dropping below derived 91 on both
  runs. Tier 3. ASCII, `git diff --check`, module-form `validate 2025`, preflight `legacy_mined`
  394. **ONE local commit.**

- **M20-S47 (QUEUED, SMALL) - EXPAND THE REVIEW VOCABULARY TO ACCEPTED / REJECTED / PROBLEM.** S45
  found that the ledger schema accepts arbitrary judgement strings, the review surface emits only
  `confirmed` and `rejected`, and no `problem` state exists anywhere. **John's model is three-state**
  and the bridge currently applies `confirmed` only. Define the three states end to end - review
  surface, ledger schema, and what each writes onto a node - then extend the bridge. Report what a
  `rejected` or `problem` node should mean to the ENGINE (refuse to compute? compute with a warning?
  report unresolved?) and let John rule before wiring engine behaviour.

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

- **M20-S45 (`467685c`, Architect-verified):** `apply_address_verdicts` plus
  `review apply-address-verdicts`, dry-run by default, reusing the existing `_apply_graph_review`
  rather than adding a second applier. Architect ran the live dry-run: the one real ledger record
  reports STALE with both fingerprints printed and writes nothing, which is the property the M15
  path lacked. Vocabulary gap reported not invented -> S47.
- **M20-S44 (`e0a3f35`, Architect-verified):** `operand_type_mismatch` hard-fails a nonnumeric graph
  node in a numeric slot while still allowing a status node as a `LOOKUP_TABLE` key; incomplete node
  metadata is recorded as `operand_type_undetermined_nodes` and allowed through; `REQUIRE_INPUT` no
  longer emits an unmapped-operation warning. Architect ran both corpus legs: derived 92/92,
  resolved 93, `unmapped_operation` down 12-14 -> 9/7, and 6251 line 39 correctly shaped in both.
- **M20-S43 (`ba7a1f8`, Architect-verified):** worksheet start resolves by normalized printed title,
  exact after NFKC/case/punctuation folding with one allowance for the IRS `-Line N` suffix; zero or
  multiple matches fail closed with every candidate named; the publink is demoted to an observation
  and no longer appears in the stored locator. Architect rewrote all 1,480 publink ids in the real
  source and got identical output (25/13/13 with 0 mismatches/2), and confirmed a renamed title
  blocks even with the declared publink still present - the title is the key, not a fallback.
- **M20-S42 (`b6e9be7`, Architect-verified):** `tax_graph/ingest/worksheet_harvest.py` plus the
  `harvest-worksheet` CLI - pure over acquired instruction HTML, writes only under `_drafts`, no
  schema change. QDCGT canary met the prediction exactly: 25 contiguous lines, 13 constants, 13
  citations with zero mismatches under the project's own checker, and **both Form 2555 conditional
  routes that the hand-authored graph drops.** Declared scope limit: no computed nodes and no
  `CALCULATES` edges, so it does not harvest the arithmetic. Architect finding -> S43.
- **M20-S41 (`40530b1`, Architect-verified):** `tax_graph.acquire.reconcile_document_lists` names
  every graph/manifest/raw difference, degrades the raw leg to `skipped`, and reports non-fatally
  through `validate`; the derivation harness now defaults to the manifest's declared order. Architect
  ran the provider leg: 21 documents, 9 complete, 12 empty, zero errored, 96 rows unchanged, the
  2441 phantom gone. All six instruction documents derive zero rows -> the case for S42.
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

- **M20-S45 Worker implementation (2026-08-04, Worker-verified; awaiting Architect verification):** added
  `tax_graph.review.apply_address_verdicts` and `review apply-address-verdicts`, dry-run by default.
  Exact canonical address plus one node binding plus one unchanged content fingerprint is required;
  the existing `_apply_graph_review` writes the three node fields on an explicit temporary apply.
  Stale, missing, ambiguous, and unsupported records are reported with no write. The real ledger
  entry is stale: reviewed `151f0df27ea00babb02732005d1aed7d2753bb1a0cb0117ab9464c1d75d30ca4`;
  current `e270b15dd0e41720e0a5b7143e9ce8ace5526b008f3cbef8fc91a25c28ac26d1`. No live graph write.
  RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\08\04\019fcd22-0dbe-7481-9da9-77388ec5d84c\pytest_m20_s45_focus';
  .venv\Scripts\python.exe -m pytest tests\test_review_address_bridge_m20.py tests\test_review_workbench_verdicts_m15.py
  tests\test_workbench_m15.py tests\test_review_verdicts_m20.py -q` -> 33 passed.
  RAN: `.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK; `git diff --check` -> clean;
  module-form `validate 2025` -> exit 0, graph integrity OK, reconcile differences named.
  RAN: protected-set `git diff --stat -- graph/2025/nodes graph/2025/edges graph/2025/rules graph/2025/field_maps`
  -> empty. RAN: module-form live dry-run -> 1 stale, 0 unresolved, 0 ambiguous, 0 writes, with both
  fingerprints printed. RAN: temporary graph copy using the real ledger record -> `would_apply`, exact
  address/node resolution, node `form_1040_2025_root_line_z`, all three field changes printed, and
  applied/stale/unresolved/ambiguous lists empty because the run was dry.
- **M20-S44 (2026-08-04, Architect live):** two corpus runs, attempted=96 both, derived 92 and 92,
  repaired 1 and 1, errored 3, resolved 93 both; `unmapped_operation` 9 and 7 (was 12 and 14);
  `operand_type_mismatch` fired once on live data. Type check verified directly: status node in the
  `IF_ELSE` condition slot hard-fails, the same node as a `LOOKUP_TABLE` key passes,
  `REQUIRE_INPUT` warns zero times. 72 passed on a short temp root; ASCII OK; `git diff --check`;
  protected set byte-identical across `0310ba1..e0a3f35`.
- **M20-S43 (2026-08-04, Architect):** independent year-turn simulation - all 1,480
  `en_US_2025_publink*` ids in the acquired HTML rewritten to a 2026 scheme, headings untouched;
  harvest output identical (25 lines, 13 constants, 13 citations with 0 mismatches, 2 conditions)
  with the new anchor recorded as an observation. Negative case verified directly: heading text
  renamed with the declared publink left intact blocks with `missing_start_title`. 73 passed on a
  short temp root; ASCII OK; `git diff --check`; `validate 2025` exit 0 with all six reconcile
  differences named; protected set byte-identical across `c04db97..ba7a1f8`.
- **M20-S42 (2026-08-04, Architect):** harvester run directly against
  `.cache/raw/2025/instructions_form_1040_2025.html` - `ok=True`, zero findings, 25 line nodes, 13
  parameter nodes, 13 citations, 42 edges, 2 conditions (Form 2555, lines 1 and 25). Citations
  re-checked with `check_citation_integrity`: **checked=13, mismatches=0**. 77 passed on a short
  temp root; ASCII OK; `git diff --check`; protected set byte-identical across `25d2895..b6e9be7`.
- **M20-S41 (2026-08-04, Architect live):** manifest-driven corpus, 21 documents, 9 complete /
  12 empty / 0 errored; attempted=96, derived=90, repaired=3, errored=3, resolved=93 (third sample
  in the 90-92 band; no derivation code changed). 78 passed on a short temp root; ASCII OK;
  `validate 2025` exit 0 with the reconcile report printing all six named differences; protected set
  byte-identical across `8dc3511..40530b1`.
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
