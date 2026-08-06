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

**BALL: WORKER - M20-S67 (THE REGISTRY AND THE VALIDATOR MUST AGREE ABOUT ROLES).** Task block
under **From Architect**. **S66 is a NARROW REWORK at `bf135ce`.**

**THE CORPUS IS AT ZERO.** Live: 2441 **0/21**, 1040 **0/17**, 6251 **0/29** - 56 rows repaired, 11
errored, against 20/21, 17/17 and 26/29 before. **59 failures are one kind:**
`payload: operand role is only valid on LOOKUP_TABLE arguments`.

**The cause is the registry disagreeing with the validator about roles.** S66 generates the prompt
from the registry, so the prompt now advertises declared operand roles for every operation - `SUM`
-> `addend`, `SUBTRACT` -> `minuend`/`subtrahend`. The model emits them. `_validate_operand_role`
still permits a non-null role only on `LOOKUP_TABLE`. **That is the exact defect class the registry
was built to end, reintroduced one level up.**

**`doctor` was GREEN while the corpus was at zero, and 104 tests passed.** It checks whether an
operation is PRESENT in each layer, not whether the layers AGREE ABOUT ROLES. **S67 adds that
check** - a guard that would not catch the defect it exists to prevent is not finished.

**WHAT S66 GOT RIGHT AND MUST SURVIVE THE REWORK:** the registry itself; `projection_expected`
derived from category rather than declared per operation, so a real gap cannot be waved through;
`ABS` removed per John's ruling; `ROUND` cited to the 2025 Form 1040 instructions; `DIVIDE`
zero-divisor behaviour specified and tested.

**QUEUE - one line each.**
1. **S67** - restore the role invariant; make `doctor` check role agreement.
2. **S64 candidate regeneration** - first full run; expect ~121 of 478 anchors.
3. **Column and grid recovery** - 2441 lines 3 and 30 and their class.
4. **Deterministic phrase obligations** - the only queued work targeting semantic correctness.
5. **S53 the approval gate.**
6. **Known-red cleanup** - independent, pullable forward.

**FOR JOHN - a design question S66 exposed by accident, worth deciding on purpose.** If the model
named operand roles (`minuend`/`subtrahend` instead of first/second position), `subtract_direction`
- a recurring live failure - becomes structurally impossible. **Named roles are exactly how
`LOOKUP_TABLE` stopped being a positional guess in S46/S47**, and the registry already declares
those roles. It is a deliberate widening of what the model supplies, with a real correctness payoff.
Not this round.

## Current round

**M20-S67 implementation complete locally; provider verification remains.** The prompt registry now
advertises named roles only for `LOOKUP_TABLE`; ordinary roles remain internal positional projection
roles. The validator consumes the same `named_leaf_roles` policy. `doctor` now probes the real
validator and graph projection, compares their role contracts with the rendered prompt contract, and
reports a disagreement instead of checking operation presence only. `schemas/README.md` documents
the wire/projection split.

**Verification.**

- RAN: `.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/test_operation_registry_m20.py tests/test_doctor_m20.py tests/test_derive_cells_m20.py tests/test_m20_s54.py tests/test_extract_m4.py tests/test_prompt_experiment_m20.py tests/test_expression_agreement_m20.py -q` -> **133 passed in 7.72s**.
- RAN: `.venv\Scripts\python.exe -m tax_graph.cli doctor --year 2025` -> **OK**; all operation rows, including roles, are `HOLDS`.
- RAN: `.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> **graph integrity OK**.
- RAN: `.venv\Scripts\python.exe tools/check_ascii.py` -> **ASCII check OK**.
- RAN: `git diff --check` -> **exit 0**.
- RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\08\06\019fd5e8-152b-7dc0-a3f5-7ac25c36afb5\tax_graph_pytest'; .venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/test_extract_m4.py tests/test_nversion_m8.py tests/test_operation_registry_m20.py tests/test_doctor_m20.py tests/test_derive_cells_m20.py -q` -> **122 passed, 1 failed**. The failure is `test_verify_nversion_command_reports_disagreement`, which cannot read three existing `graph/2025/_drafts` directories during `shutil.copytree` (`WinError 5`); no role assertion ran. The file is environment-unverified.
- NOT RUN: live derivation/provider corpus. The provider leg is assigned to the Architect; the prior measured baseline remains 2441 **0/21**, 1040 **0/17**, 6251 **0/29** until that leg is rerun.

**Acceptance state.** Local gates are green, but M20-S67 is not accepted until the live corpus returns
to the handoff target and the eleven errored rows are reported separately. No protected directory was
changed.

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

- **M20-S67 TASK - THE REGISTRY AND THE VALIDATOR MUST AGREE ABOUT ROLES (Architect, Claude Opus 5,
  2026-08-05).** Ledger: the RAN/NOT RUN rule, D10, and the standing rules in `AGENTS.md`.
  **Narrow rework of S66. Keep everything else it did - the registry, `DIVIDE`, `ROUND`, the removal
  of `ABS`, the categories, and a green `doctor` are all correct.**

  **What S66 got right, verified, and must survive.** One registry; `doctor` green on the vocabulary
  with `projection_expected` **derived from category rather than declared per operation**, so a real
  gap cannot be waved through; `ABS` removed per John's ruling; `ROUND` semantics cited to the 2025
  Form 1040 instructions; `DIVIDE` zero-divisor behaviour specified and tested; 104 focused tests
  green.

  **The defect, measured live.** **0 derived across all three documents** - 2441 0/21, 1040 0/17,
  6251 0/29, with 56 rows repaired and 11 errored. Previously 20/21, 17/17, 26/29. **59 of the
  failures are one kind:** `payload: operand role is only valid on LOOKUP_TABLE arguments`.
  The generated prompt now advertises the registry's declared operand roles for EVERY operation
  (`SUM` -> `addend`, `SUBTRACT` -> `minuend`/`subtrahend`, `MULTIPLY` -> `multiplicand`/
  `multiplier`), the model emits them, and `_validate_operand_role` still permits a non-null role
  only on `LOOKUP_TABLE`. **The registry and the validator disagree about roles - the exact defect
  class the registry was built to end, reintroduced one level up.**

  **Why `doctor` missed it, and fix that too.** `doctor` checks whether each operation is PRESENT in
  each layer. It does not check that the layers AGREE ABOUT OPERAND ROLES. **Add that check** - the
  roles the prompt advertises, the roles the validator accepts, and the roles projection assigns
  must be the same set per operation. A guard that would not have caught the defect it was built to
  prevent is not finished.

  **Step 1 - restore the invariant the minimal way.** The wire permits a nullable role everywhere;
  the deterministic validator permits a non-null role only on `LOOKUP_TABLE`; **projection derives
  roles from position for every other operation.** That was S56's settled split and it worked.
  **Stop the generated prompt advertising operand roles for non-`LOOKUP_TABLE` operations.** The
  registry keeps its role declarations - projection needs them - but they are internal, not part of
  what the model is asked to supply.

  **Step 2 - prove it with the corpus, not with fixtures.** 104 tests passed and `doctor` was green
  while the corpus was at zero. **The round is not accepted until the live numbers return to
  roughly 2441 20/21, 1040 17/17, 6251 26/29.**

  **Step 3 - report the eleven errored rows separately.** 56 rows were repaired, meaning they failed
  once and recovered. **Repair rate is a signal we have been ignoring**: a corpus at 0 derived and
  56 repaired passed every gate we had. Report whether repair rate should itself be a `doctor`
  check.

  **Do not:** change the validator to accept model-supplied roles in this round (see below); remove
  the registry; weaken `doctor`; touch the protected set. **Stop conditions:** any diff in the
  protected directories; live derived not restored; `doctor` green while the corpus is broken.
  Tier 3. Honest `RAN:`/`NOT RUN:` - **the provider leg is the Architect's, and this round is not
  accepted until the corpus recovers.** ASCII, `git diff --check`, module-form `validate 2025`.
  **ONE local commit.**

  **A REAL DESIGN QUESTION THIS EXPOSED, for a later round and worth John's view.** If the model
  DID name operand roles - `minuend` and `subtrahend` rather than first and second position -
  then `subtract_direction`, a recurring live failure kind, becomes structurally impossible. Named
  roles are how `LOOKUP_TABLE` stopped being a positional guess in S46/S47. **The same argument
  applies to every value operation, and the registry now declares those roles already.** That is a
  deliberate widening of what the model supplies, with a real correctness payoff, and it should be
  decided on purpose rather than arrived at by a prompt generator.

## History

Everything before M20-S23, and all per-round Worker narration, lives in git history. This file was
pruned from 7,520 lines on 2026-08-02 at S28 acceptance; `git show 12240ef:plans/AGENT_HANDOFF.md`
is the last unpruned copy. Earlier prune: 2026-07-23, from 1,198 lines, for public-repo prep.
Durable rulings were carried forward into **Binding rulings** above rather than deleted; A9
rulings remain pinned in `plans/PHASE_M15.md`; the defect ledger (D6, D9, D10, D12, D13, D14) is
in `AGENTS.md`.
