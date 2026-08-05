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

**BALL: ARCHITECT - M20-S66 provider acceptance pending.** Worker implementation is complete
locally; task block remains under **From Architect**. **S65 is ACCEPTED at `80b71c5`, and it found
something far bigger than it was built to find.**

**ONLY 3 OF 19 OPERATIONS AGREE ACROSS ALL FOUR LAYERS.** `doctor` reports prompt / validator /
projection / engine per operation. `SUBTRACT`, `LOOKUP_TABLE` and `IF_ELSE` hold. **Sixteen
disagree**, in three distinct families:
- **Offered but undocumented (6):** `COPY`, `SUM`, `MULTIPLY`, `MIN`, `MAX`, `NEGATE` are in the
  emission enum and absent from the prompt. **The model has been choosing from an undocumented
  menu**, which is exactly how it reached for `LOOKUP_BRACKET`.
- **Offered and NOT EXECUTABLE (3):** `DIVIDE`, `ABS`, `ROUND` project to a rule and then hit
  `NotImplementedError("operation ... not implemented in v0")` in
  `tax_graph/engine/operations.py`. **An expression using them would pass every validator and fail
  at runtime.**
- **Documented but unprojectable (7):** `IF`, `AND`, `OR`, `NOT`, `COMPARE`, `REQUIRE_INPUT`, and
  `LOOKUP_BRACKET`. **`REQUIRE_INPUT` is the most-emitted operation on our hard rows** - 2441 lines
  3, 19, 21 and 27 - and it projects to nothing, which is the `unmapped_operation` warning we have
  been reading past for rounds.

**This reframes the registry round.** It was queued as "fix `LOOKUP_BRACKET`". It is actually
**the operation contract is 84% incomplete**, and we have been debugging individual rows on top of
it.

**JOHN'S RULING on the three offered-but-unexecutable operations, 2026-08-05:** *"divide and
round yes. ABS nah."* Clarified: *"ABS will never be something asked of a filer."* Implement
`DIVIDE` and `ROUND`; **remove `ABS` permanently** - not until a form demands it, but because no
IRS instruction tells a filer to take an absolute value. Forms say *"if zero or less, enter
-0-"*, which is `MAX(x, 0)`.
**The durable test this establishes:** an operation belongs in the emission vocabulary only if
it corresponds to something a form actually instructs a filer to do.

**QUEUE - one line each.**
1. **S66 the operation registry** - one versioned source of truth generating schema, prompt
   documentation, validator dispatch, projection mapping and runtime registration, with `doctor`
   as its acceptance test.
2. **S64 candidate regeneration** - first full run; expect ~121 of 478 anchors.
3. **Column and grid recovery** - 2441 lines 3 and 30 and their class.
4. **Deterministic phrase obligations** - the only queued work targeting semantic correctness.
5. **S53 the approval gate.**
6. **Known-red cleanup** - independent, pullable forward.

**FOR JOHN, unresolved and not blocking:** "every cell approved before use" and "a human does not
read every new cell" cannot both hold during bootstrap. The pipeline can remove RE-review, not first
review.

## Current round

**M20-S66 WORKER IMPLEMENTATION COMPLETE LOCALLY (2026-08-05).** Canary: **Ground Truth**.
The operation vocabulary is now one versioned registry (`OPERATION_REGISTRY_VERSION = "1"`) with
arity, roles, category, prompt notes, projection mapping, and runtime handler. ABS is removed;
DIVIDE and ROUND are executable. Predicates and REQUIRE_INPUT remain in the vocabulary but doctor
records that no standalone projection is expected for them. The checked-in schemas, extraction
validation, prompts, workbench formatter, review projection, engine dispatch, and doctor all read
or check the same contract. ROUND defaults to nearest whole dollar under the acquired 2025 Form
1040 instructions (`en_US_2025_publink24811vd0e457`); zero DIVIDE returns the unresolved-value
sentinel.

**RAN:**

- `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp_codex'; .\.venv\Scripts\python.exe -m pytest tests/test_operation_registry_m20.py tests/test_doctor_m20.py -q` -> **29 passed, 1 warning**.
- `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp_codex'; .\.venv\Scripts\python.exe -m pytest tests/test_operation_registry_m20.py tests/test_doctor_m20.py tests/test_derive_cells_m20.py tests/test_extract_m4.py tests/test_extract_outline_m4.py tests/test_tax_liability_m11.py tests/test_background_m20.py -q` -> **148 passed, 1 warning**.
- `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp_codex'; .\.venv\Scripts\python.exe -m pytest tests/test_workbench_m15.py -q` -> **4 passed, 1 warning** (mandatory D5 boundary test).
- `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp_codex'; .\.venv\Scripts\python.exe -m pytest tests/test_review_table_m20.py tests/test_expression_agreement_m20.py -q` -> **11 passed, 1 warning**.
- `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp_codex'; .\.venv\Scripts\python.exe -m pytest tests/test_review_table_m20.py tests/test_expression_agreement_m20.py tests/test_generated_review_m20.py tests/test_review_manifest_m15.py tests/test_review_semantics_remaining_m15.py -k "not live_derived_manifest_uses_review_expressions_without_raw_fallback" -q` -> **23 passed, 8 failed, 1 deselected, 2 warnings**. Every failure is a `WinError 5` while reading the protected live `graph/2025/_drafts` directories; no assertion failure was reached.
- `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp_codex'; .\.venv\Scripts\python.exe -m pytest tests/test_capital_gains_slice.py tests/test_tax_table_m11.py tests/test_tax_liability_m11.py tests/test_tables_engine_m6b.py tests/test_frontier_engine_m7.py tests/test_form_1040_spine_m11.py tests/test_dependents_m15.py -q` -> **28 passed, 2 failed** on the same protected draft-directory ACL while preparing live fixtures.
- `.\.venv\Scripts\python.exe -m tax_graph.cli doctor --root C:\Users\devbox\projects\tax_graph` -> **exit 0**; all 18 operation rows HOLD, including expected NO projection for predicates and REQUIRE_INPUT.
- `.\.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> **exit 0**; graph integrity OK.
- `.\.venv\Scripts\python.exe -m compileall -q tax_graph workbench tests/test_operation_registry_m20.py tests/test_doctor_m20.py` -> **exit 0**.
- `.\.venv\Scripts\python.exe tools/check_ascii.py` -> **ASCII check OK**.
- `git diff --check` -> **clean**.

**NOT RUN:** live provider derivation / one-live-row acceptance (Architect leg per task spec).
The protected graph and draft directories were not changed. No provider or prompt-contract wire
test was claimed from fixture evidence.

**NEXT BALL: ARCHITECT - run the provider leg and one live row, then accept or return a concrete
registry-layer defect. Do not push this Worker commit until that acceptance is complete.**

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

**One spec at a time. Queued rounds are one-liners in BALL until they are next.**

- **M20-S66 TASK - ONE VERSIONED OPERATION REGISTRY (Architect, Claude Opus 5, 2026-08-05).**
  Ledger: the RAN/NOT RUN rule, D10, and the standing rules in `AGENTS.md`. **`doctor` going green
  on the vocabulary section is the acceptance test.** One change, no passengers.

  **OPEN ITEMS AND SEAMS THIS ROUND TOUCHES:** none open. **Leaves untouched:** S64 regeneration,
  column and grid recovery, phrase obligations, S53, the known-red cleanup.

  **Why, measured by `doctor` on 2026-08-05.** **Only 3 of 19 operations agree across prompt,
  validator, projection and engine** - `SUBTRACT`, `LOOKUP_TABLE`, `IF_ELSE`. **The two halves of
  the vocabulary were built by opposite logics and nothing ever compared them:** the engine
  implements exactly the ten operations that appear in real graph rules, demand-driven; the emission
  enum was written speculatively with nineteen. One grew from evidence, the other from imagination.

  **JOHN'S RULING, 2026-08-05, on the three that are offered but cannot execute:** *"divide and
  round yes. ABS nah."* Clarified: *"ABS will never be something asked of a filer."*
  - **Implement `DIVIDE` and `ROUND` in the engine.**
  - **Remove `ABS` permanently.** Not "until a form demands it" - **it will never be demanded.** No
    IRS instruction tells a filer to take an absolute value. Forms say *"if zero or less, enter
    -0-"*, which is `MAX(x, 0)`. `ABS` is a programmer's primitive that was written into the enum
    because it looks like arithmetic.
  - **THE TEST THIS ESTABLISHES, and apply it to the whole vocabulary:** an operation belongs in the
    emission vocabulary only if it corresponds to something a form actually instructs a filer to do.
    **Report any other operation that fails this test** - it is the same shape as John's rule that a
    question which cannot be asked about the 1040 is the wrong question.

  **Step 1 - one versioned registry, one source of truth.** Every operation declared once, with its
  arity, operand roles, **category** (see step 2), prompt documentation, validator dispatch,
  projection mapping and engine implementation derived from or checked against that declaration.
  **A new operation must be impossible to add to one layer alone.**

  **Step 2 - classify before projecting, because `doctor`'s flat four-layer table is too coarse.**
  The seven "documented but unprojectable" operations are not one problem:
  - **Value-producing** (`SUM`, `SUBTRACT`, `MULTIPLY`, `DIVIDE`, `MIN`, `MAX`, `NEGATE`, `ROUND`,
    `COPY`, `LOOKUP_TABLE`, `LOOKUP_BRACKET`) - these need a rule to project onto.
  - **Predicates** (`IF`, `AND`, `OR`, `NOT`, `COMPARE`) - these live INSIDE a condition and may
    legitimately have no standalone rule. **Report whether "no projection" is correct for them
    rather than forcing one.**
  - **Dispositions** (`REQUIRE_INPUT`) - "the filer supplies this" is not a computation.
    **Projecting it to a rule is probably wrong; it should mark a required input.** It is the
    most-emitted operation on our hard rows and the source of the `unmapped_operation` warnings.
  **Add the category to `doctor`'s report so a legitimate absence stops reading as a defect.**

  **Step 3 - document the six that were offered in silence.** `COPY`, `SUM`, `MULTIPLY`, `MIN`,
  `MAX`, `NEGATE` are in the enum with no prompt text. **The model has been choosing from an
  undocumented menu**, which is how it reached for `LOOKUP_BRACKET`. Generate the prompt's operation
  documentation from the registry so this cannot recur.

  **Step 4 - state `ROUND`'s semantics explicitly; do not assume them.** Rounding mode and
  precision are part of the executable contract, not an implementation detail. IRS forms round to
  whole dollars. **Report the rule you implement and cite the source for it.** Same discipline for
  `DIVIDE`: state the behaviour on a zero divisor rather than letting Python decide.

  **Step 5 - `doctor` must go green on the vocabulary section**, and its greenness must come from
  the layers actually agreeing, **not from loosening the check**. Weakening `doctor` to pass is the
  guard-inversion failure that cost S54 and S55 two rounds.

  **Do not:** implement `ABS`; add an operation no form has demanded; weaken `doctor`; change
  derivation, the packet, or the addressing layer; touch the protected set. **Stop conditions:** any
  diff in the protected directories; an operation reachable in one layer and absent from another
  after this round; `doctor` passing because a check was relaxed. Tier 3. Honest `RAN:`/`NOT RUN:` -
  **the provider leg is the Architect's, and this round is not accepted until one live row derives.**
  ASCII, `git diff --check`, module-form `validate 2025`. **ONE local commit.**

## History

Everything before M20-S23, and all per-round Worker narration, lives in git history. This file was
pruned from 7,520 lines on 2026-08-02 at S28 acceptance; `git show 12240ef:plans/AGENT_HANDOFF.md`
is the last unpruned copy. Earlier prune: 2026-07-23, from 1,198 lines, for public-repo prep.
Durable rulings were carried forward into **Binding rulings** above rather than deleted; A9
rulings remain pinned in `plans/PHASE_M15.md`; the defect ledger (D6, D9, D10, D12, D13, D14) is
in `AGENTS.md`.
