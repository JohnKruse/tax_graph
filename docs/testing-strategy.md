# Tax Graph - Testing Strategy (hard guardrails)

Testing is the credibility of this project. Because **no comprehensive IRS answer key
exists**, confidence comes from *deterministic execution + cross-implementation agreement*,
seeded with the few authoritative IRS numeric cases. Implementers (Codex/Sonnet/Gemini)
must follow this document - it is not optional.

## The supported-branch bar (non-negotiable)
A graph branch may NOT be marked `status: supported` until ALL of these hold:
1. Schema-valid and passes graph-integrity (`tax-graph validate`).
2. Every rule on the branch cites an IRS source (governance Section 13).
3. >=1 passing **example test** (facts.yaml + expected.yaml), IRS-derived where possible.
4. Where an independent oracle exists, a passing **differential test**.
Until then a branch is `partial`/`planned`. **Incomplete is fine; wrong is not.**

## Per-change discipline (every step, every PR)
From the working protocol: **every implementation step must (a) implement, (b) create or
update the pytest, (c) update docstrings/docs.** Reuse/extend existing tests rather than
proliferating near-duplicates. A step is not done until its tests pass 100%.

## Test categories (requirements doc Section 10)
1. **Primitive-op unit tests** - COPY copies exactly; SUM treats blank as 0; SUBTRACT
   respects minuend/subtrahend; ROUND modes (nearest/up/down + increment). Property-based
   tests welcome (e.g. SUM order-independence).
2. **Graph-integrity** - every edge source/target/rule resolves; citations exist; no
   illegal cycles; tax-year consistency. (Already implemented in the validator.)
3. **Form-level** - calculations within a form (8949 totals, Schedule D summaries).
4. **Cross-form flow** - 8949 -> Schedule D -> 1040; 1116 -> Schedule 3 -> 1040.
5. **Example regression (IRS Example Suite)** - facts/expected fixtures; seed exists at
   `examples/capital_gains_basic/`. Every supported branch needs >=1.
6. **Trace/snapshot** - assert the audit-trace structure for key scenarios (rules applied,
   citations, derivation order) so refactors can't silently change provenance.
7. **Differential** - Tax Graph vs OpenTaxSolver (box-level) and PolicyEngine /
   Tax-Calculator (liability). Agreement across independent implementations is the real
   confidence - a single engine agreeing with itself proves nothing.

## Determinism & isolation
- Categories 1-7 above are **deterministic and offline** - no network, no LLM, no clock
  dependence. Mock acquisition and the LLM.
- **Extraction tests are separate and gated** (need an API key/network) - a marked, optional
  CI job. The LLM is never on the path of a deterministic test.

## The extraction guardrail (critical)
LLM-extracted graph objects are **drafts, never trusted**. Tests must assert that extractor
output: validates against the schemas, uses only the closed op vocabulary, carries a quoted
source span + confidence, and is gated behind human review before merge. A suite that
"passes" because the model agreed with itself is worthless - that is what Differential and
the IRS examples are for.

**Verification at scale (M8, `docs/extraction-verification.md`):** structural checks verify
FORM, not MEANING - a schema-valid draft can still swap SUBTRACT roles or mis-target a flow.
Accuracy checks that need a hand-authored reference do not scale past the canary form.
Two additional hard rules once M8 lands:
1. **The check net is itself under test.** Seeded-defect drills (mutation testing over the
   known-good slice) must catch 100% of the cataloged defect classes, offline, in CI; every
   real-world escape becomes a new drill case. A defect class no layer can catch means that
   object class is not auto-promotable - route it to human review by policy.
2. **Confidence scores are telemetry, never load-bearing.** No promotion decision may depend
   on a self-reported confidence value (drill-enforced: inflating all confidences to 1.0
   must change nothing).

## Layout & gates
- `tests/` mirrors components. **Tag tests by phase** with pytest markers
  (`@pytest.mark.m0`, `m3`, ...) so each phase's exit-criteria command is `pytest -m <phase>`.
- **CI on every push:** `tax-graph validate` + `pytest` (the deterministic suite).
  Extraction/oracle jobs are separate and may be manual/scheduled.
- Coverage is a signal, not a target - prioritize meaningful form/cross-form/differential
  coverage over line percentage.
