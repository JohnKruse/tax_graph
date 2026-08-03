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

**BALL: WORKER - M20-S38 (FIX THE RE-DERIVE CALL; THEN LET AN OPERAND NAME A FILER FACT).** Task block under
**From Architect**. **S37 comment plumbing ACCEPTED at `085a234`; the `rederive_cell` entry point
is BROKEN against the real config and must be fixed first.**

## Current round

**M20-S37 PARTIALLY ACCEPTED (Architect, Claude Opus 5, 2026-08-03) at `085a234`.** Steps 1-3
delivered and step 4-5 correctly declared NOT RUN. The Architect ran the provider leg and found
three things, one of which retracts a claim I have repeated all session.

**THE LOOP WORKS - the plumbing is proven. BUT THE DEMONSTRATION WAS BAD, AND THE FAULT IS MINE.**
Form 6251 line 18, same row and model, one call apart:

| run | expression |
| --- | --- |
| no comment | `if_else(compare(line 17, 239100), line 17 * 0.26, (line 17 * 0.28) - 4782, (line 17 * 0.28) - 4782)` |
| curated comment | `if_else(line 17, 239100, line 17 * 0.26, (line 17 * 0.28) - 4782)` |

The comment changed the output, so **the mechanism is real and is ACCEPTED**: ledger, curated vs
contributed, `row.human_comment`, evidence packet, prompt. That is the first time a human
instruction has reached a derivation in this project.
**But the comment I wrote told the model to "use the figures for a single filer: threshold 239100
and subtrahend 4782", and the row has TWO filing-status-dependent values** - the threshold is
$239,100 or $119,550, and the subtrahend is $4,782 or $2,391. **I steered the model into hardcoding
one filing status and dropping the married-filing-separately branch. The expression I reported as a
success is WRONG for anyone filing separately.** On a tax product that is a real defect, and the
demonstration should be read as proof the mechanism works, not as a correct answer.

**ROOT CAUSE, FINALLY, AND IT IS OURS: NO OPERAND CAN NAME A FILER FACT.** The expression grammar
allows exactly four operand shapes - `{line}` on this form, `{form, line}` on another form,
`{const}`, and a nested `{op, args}`. **There is no way to reference a graph node or any
characteristic of the filer.** The graph DOES model filing status: `taxpayer_2025_filing_status`
exists in `graph/2025/nodes/capital-gains.yaml`. The derivation grammar simply cannot reach it.
**So 6251 lines 18 and 39 are not hard - they are INEXPRESSIBLE.** The model's only options were to
hardcode one status, which is wrong for every other filer, or to fail. It has been behaving as well
as the grammar permits, and five rounds of churn on these two rows were our defect throughout.
**This generalizes far past 6251.** Filing-status-dependent constants are everywhere in the code -
standard deduction, brackets, thresholds, phase-outs - so any form with a bracketed
married-filing-separately figure hits the same wall.
**This is my FIFTH diagnosis of these two rows** (model quality, unmodelled worksheet, grammar
expressiveness, label truncation, and now the operand gap). Each was drawn from the evidence in
front of me instead of from the layer below it. The check that settled it took one command:
print the operand shapes the schema actually permits.

**BLOCKER 1 - `rederive_cell` fails against the real config, every time.** It passes
`temperature=_optional_temperature(settings)`, which reads the configured `llm.temperature: 0`.
With `llm.require_parameters: true`, OpenRouter filters to endpoints advertising every requested
parameter, and no `gpt-5.6-luna` endpoint advertises temperature - so **all endpoints are
eliminated and the call 404s** with "No endpoints found that can handle the requested parameters".
Architect isolated it: `temperature=None` derives, `temperature=0.0` 404s, with all else identical.
**The batch path never passes temperature at all**, which is why the corpus runs work. The fix is
to match the batch path. The steering result above was obtained by calling `derive_cells` the way
the batch path does, bypassing the defect.

**BLOCKER 2, AND A RETRACTION I OWE - `llm.temperature: 0` HAS NEVER BEEN IN EFFECT.** The batch
derivation path does not pass it, so it has never been sent. **Every "nondeterministic at
`temperature: 0`" statement in this file and in my reports is wrong** - the runs were
nondeterministic at the provider's DEFAULT temperature. I repeated that claim across S28 through
S36 without ever checking that the setting reached the request. The observed variance is real; the
explanation attached to it was not. Decide explicitly whether to send temperature (which requires
relaxing `require_parameters` or dropping the setting) or to delete the key so the config stops
implying something untrue.

**BLOCKER 3 - `IF_ELSE` has an enforced arity and NO DEFINED SEMANTICS. This is the actual cause
of 6251 lines 18 and 39, and it is my fourth diagnosis of those rows.** `cells.py` enforces
`IF_ELSE: 4` arguments. `ROLE_FOR_OP` names argument roles for SUM, SUBTRACT, DIVIDE, MULTIPLY,
MAX, MIN, COPY and NEGATE - **`IF_ELSE` is absent, so `_role_for` returns the generic "operand" for
every slot.** Nothing anywhere says what the four arguments mean. The two runs above are two
mutually incompatible readings that BOTH pass validation: one puts a `COMPARE` in slot 1 and pads
slot 4 with a duplicate of the else-branch; the other puts the comparison operands in slots 1 and 2.
**Downstream execution would compute different numbers from these, and no check can tell them
apart.** Same gap applies to `IF`, `COMPARE`, `AND`, `OR`, `NOT`, `LOOKUP_TABLE` and
`LOOKUP_BRACKET`. This is not an expressiveness gap - the grammar can express the row fine. It is
an undefined grammar, and any expression using a conditional operator is currently unreliable
regardless of model quality.

**CONFIG CHANGE (John, 2026-08-03): provider routing is now OpenAI ONLY.** Azure is roughly 10x the
price for the same model. `llm.provider_routing.only` was `[openai, azure]` and is now `[openai]`.
Verified live afterwards - both derivations above ran on the new routing. **Do not re-add Azure as
a fallback without asking**: a silent failover would cost 10x per call with no signal. If OpenAI's
endpoint is unavailable the call now fails loudly, which is the intended trade.

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
  **(1) Are the tax worksheets in the base profile?** 6251 lines 13, 20 and 27 reference the
  Qualified Dividends and Capital Gain Tax Worksheet and the Schedule D Tax Worksheet. Both live in
  the IRS *instructions* rather than as standalone forms, and neither is a document in our graph,
  so those rows reference addresses that do not exist. Either model them as documents, or declare
  them out of scope and make the reference fail closed with a named reason instead of a confusing
  self-reference. The 1040 and Schedule D reference the same worksheets, so this recurs.
  **(2) Should the expression grammar carry a filing-status-dependent constant?** 6251 lines 18 and
  39 need a threshold ($239,100 / $119,550) and a subtrahend ($4,782 / $2,391) that both vary by
  filing status. They resolve today via repair, so this is a cost question rather than a
  correctness one - but the same shape appears wherever the IRS prints a bracketed
  married-filing-separately figure, which is common.
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

- **M20-S38 TASK - FIX THE RE-DERIVE CALL, THEN DEFINE `IF_ELSE` (Architect, Claude Opus 5,
  2026-08-03).** Ledger: the RAN/NOT RUN rule, D9, D6. **Step 1 is a one-line fix. Step 2 is the
  real work. No UI this round.**

  **Step 1 - make `rederive_cell` match the batch path.** It passes
  `temperature=_optional_temperature(settings)`; the batch path passes no temperature at all. With
  `llm.require_parameters: true` this eliminates every endpoint and 404s on every call. **Stop
  passing temperature.** Architect isolated it directly: identical calls, `temperature=None`
  derives and `temperature=0.0` 404s. Add a test that the re-derive path sends the same parameter
  set as the batch path, so the two cannot drift again.

  **Step 2 - decide what `llm.temperature: 0` means and make the config honest.** It is in
  `tax-graph.config.yaml` and has never reached a request. Either send it - which needs
  `require_parameters` relaxed or a routing change, and should then be VERIFIED live rather than
  assumed - or delete the key. **Do not leave a setting that implies a determinism guarantee we do
  not have.** Whichever you choose, say so in the config with a dated comment.

  **Step 3 - let an operand reference a filer fact. THIS IS THE ROUND'S REAL WORK.**
  The grammar permits four operand shapes - `{line}`, `{form, line}`, `{const}`, `{op, args}` - and
  none of them can name a characteristic of the filer. The graph already models one:
  `taxpayer_2025_filing_status` in `graph/2025/nodes/capital-gains.yaml`. **Add an operand shape
  that references an existing graph node, e.g. `{"node": "taxpayer_2025_filing_status"}`, and
  validate it against the real node set so a fabricated id fails closed** - the same discipline as
  `operand_not_printed`. Do NOT invent a parallel vocabulary of filer attributes; bind to what the
  graph already declares.
  With that, 6251 line 18 becomes expressible: the threshold and the subtrahend each select on
  filing status. **Report the expression the model produces for line 18 with the new operand
  available, and state whether it covers married filing separately** - the Architect's earlier
  steering demo did NOT, and reporting a single-status rule as correct would repeat that mistake.
  **Check whether anything downstream can consume the new operand** (`experiments/to_graph.py`, the
  rule vocabulary, the engine). If nothing can execute it yet, say so plainly and record it as a
  known gap rather than implying the expression is usable.

  **Step 4 - define the semantics of every conditional operation, starting with `IF_ELSE`.**
  `cells.py` enforces `IF_ELSE: 4` arguments and `ROLE_FOR_OP` does not mention it, so all four
  slots are the generic "operand" and their meaning is undefined. Two Architect runs of the same
  row produced two incompatible readings that both validated:
  `if_else(compare(a,b), then, else, else)` and `if_else(a, b, then, else)`.
  **Add `IF_ELSE` to `ROLE_FOR_OP` with named roles, state them in `prompts/derive_cells.md`, and
  add a validator that rejects an expression whose argument shapes do not match the declared
  roles.** Do the same for `IF`, `COMPARE`, `AND`, `OR` and `NOT`. `LOOKUP_TABLE` and
  `LOOKUP_BRACKET` may need more than roles - if so, report what they need and do NOT guess.
  **Choose the reading that the downstream engine already assumes if one exists** - check
  `to_graph.py` and the rule vocabulary before inventing one. If nothing downstream consumes
  `IF_ELSE` yet, say so plainly, pick the condition-first reading, and record it as a decision
  rather than a discovery.
  **A prompt change needs a RENDER test** (S32) and the existing test over every file in
  `prompts/` must still pass.

  **Step 5 - rerun the corpus and report.** Expect the 96-row result to be unchanged or better;
  the target is `form_6251_2025` lines 18 and 39 no longer needing a repair, because the model will
  finally be told what the four slots mean. Report attempted / derived / repaired / errored per
  document and say plainly whether 18 and 39 moved.
  Then rerun the Architect's steering check: derive 6251 line 18 with no comment and with a curated
  comment, and report both expressions. **With roles defined, the two runs should now agree on
  shape** - if they still disagree, the roles are not being enforced.
  If approved external network is unavailable, do steps 1-3, declare step 4 NOT RUN up front, and
  hand back.

  **Do not:** re-add Azure to `llm.provider_routing.only` (John, 2026-08-03 - roughly 10x the price;
  a silent failover would cost 10x with no signal); weaken a validator so a comment can override
  it; let a `contributed` comment reach the model; write from `derive_cells` or the re-derive path;
  build UI; promote anything.
  **Stop conditions:** any diff in the protected directories; `derive_cells` acquiring a disk
  write; any harness output landing inside the repository; the no-comment corpus result regressing.
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`, module-form
  `validate 2025`, preflight with `legacy_mined` explicit (394), strict citations (36).
  **ONE local commit** - and run `git status` first; do not commit paths you did not touch.

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
