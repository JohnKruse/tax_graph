# PHASE M8 - Extraction verification at scale (the trust ladder)   [ ]

**Canary:** Skeptical Notary
**Depends on:** M4 (extraction pipeline), M6 (differential harness - supplies ladder layer L5),
M6b (promoted 8949 table subunits - the first real promotion to calibrate against).
**Design doc (canonical, read first):** `docs/extraction-verification.md` - the failure
taxonomy (F1-F6), the ladder (L0-L6), trust tiers, drills, and economics. This plan only
sequences it. Milestone block: engineering-plan "M8".
**Goal:** Make extraction accuracy verifiable WITHOUT hand-authored references and WITHOUT
humans re-deriving forms. Build the seeded-defect drill harness (mutation-tests the check net
itself), both-direction structural completeness, engine-executed property tests, the IRS
worked-example miner, cross-vendor N-version corroboration, and trust-tier routing with
metrics. **This phase's drill gate is the prerequisite for extracting beyond the capital-gains
form set** (pinned sequencing rule).

## Why
The held-out human diff that closed M4 needed a hand-authored reference - the exact bottleneck
extraction exists to remove. Structural checks verify FORM, not MEANING: a schema-valid draft
can still swap SUBTRACT roles or mistarget a flow. M6 proved the fix pattern live (offline
gates green while the OTS integration was broken; the independent witness caught it). M8
generalizes that pattern into a layered net, then measures the net itself.

## Adopted defaults (proposed 2026-07-05, unvetoed - John may still override)
Calibration sample 10% (min 5 objects) per form; N=2 vendor FAMILIES for L2 corroboration
(model families, not gateways - two models through OpenRouter are fine if their families
differ); 100% drill-catalog catch rate before bulk extraction.

## Exit criteria (must pass 100%)
- `pytest -m m8` green - offline/deterministic (drills, property tests, completeness checks,
  tier routing, report; LLM and oracle mocked or gated).
- **Drill gate:** every cataloged defect class injected into a copy of the known-good live
  graph is caught, and the report names the catching layer; the confidence-inflation drill
  changes NOTHING (confidence is telemetry, never load-bearing); the inline-magic-number drill
  is flagged by the validator.
- Property tests auto-generated from op semantics run green over the promoted live graph
  (including per-instance table rules).
- Both-direction completeness holds for the promoted 8949: every AcroForm entry field maps to
  a node or an explicit not-modeled record.
- A mined IRS worked example executes through the engine and freezes into `examples/` after
  human confirmation (mining behind the network gate; the frozen fixture replays offline).
- N-version micro-extraction diff runs for `form_8949_2025` with two vendor-family models
  (gated); agreement/disagreement lands in the draft provenance and review queue.
- `tax-graph verify report` prints per-form tier distribution, flags by layer, human-minutes
  ledger, and escape count. Routing assigns tiers; auto-accept no longer reads confidence.
- ASCII check OK; full `pytest` green; base-deps runtime untouched.

## Guardrails (do not drift)
- **The net is under test, not just the drafts.** Every drill asserts WHICH layer catches the
  defect. A defect class no layer catches = that object class is NOT auto-promotable; route it
  to human review by policy and say so in the report - never quietly shrink the catalog.
- **The catalog only grows.** Real-world escapes (calibration audit, differential triage)
  become new drill cases. Seed it from the taxonomy in the design doc Section 4, including:
  swapped minuend/subtrahend, SUM->SUBTRACT, dropped addend edge, deleted required node,
  merged adjacent lines, retargeted outbound-flow line, corrupted citation quote, phantom
  plausible node, table totals-column dropped, confidence inflation (must be a no-op), inline
  IRS magic number in `rule.parameters` (validator flag per engineering-plan "Parameters").
- **Confidence is telemetry.** No routing/promotion decision may read a self-reported
  confidence value. Tier assignment is deterministic from check outcomes.
- **Human review = exceptions + calibration sample only.** The review queue shows the evidence
  that flagged each item (the two disagreeing model answers; the failing arithmetic; the
  unmapped field) - never "re-derive this form". Decisions (the object kind) always get eyes.
- **Provider-agnostic.** L2's second model comes through the existing `LlmClient` seam
  (config `llm.nversion_model` or similar); no privileged vendor; vendor-FAMILY diversity is
  what counts. Deterministic tests mock both clients.
- **Offline core / gated network+oracle** (established pattern). Frozen mined examples replay
  offline forever. **Drafts law unchanged:** nothing here auto-merges drafts; tiers INFORM the
  human gate, they do not replace it.
- **MeF schema inventory is OPTIONAL** (worker pins availability from official sources only;
  skip cleanly if unobtainable - the AcroForm grid remains the load-bearing inventory).
- **ASCII-only; runtime stays light; schemas additive-only.**

## Steps

- [DONE] **Step 1 - Drill harness + defect catalog + layer attribution.**
  `tax_graph/drills/` (dev tooling, not base runtime): a `drill_catalog.yaml` seeded from the
  guardrail list above (id, taxonomy class F1-F6, mutation spec, expected catching layer(s));
  a mutator that applies one defect to an in-memory copy of the live graph or a draft batch;
  a runner that executes the relevant layers (validator, extraction checks, property tests
  [Step 3 - stub until then], example replay, box-map diff where applicable) and reports
  catch/miss + layer per drill. Wire `tax-graph drill run [--catalog]`. The validator gains
  the inline-magic-number flag (numeric literal in `rule.parameters` that is not structural).
  Tests: every seeded drill caught with correct attribution; an uncatchable synthetic drill
  reports honestly as MISS (and the gate fails). Docs.

- [DONE] **Step 2 - Both-direction structural completeness.** Extend extraction checks +
  validator: direction one exists (true anchors -> nodes); add direction two - every AcroForm
  entry field in `.fields.json` maps to a promoted/draft node or an explicit `not_modeled`
  record (id + reason) carried with the form. Optional MeF line-inventory cross-check behind
  a fixture (worker pins availability; official source only; clean skip otherwise). Tests:
  the promoted 8949 passes; deleting a node from a copy produces an unmapped-field flag (and
  Step 1's deleted-node drill now attributes here). Docs.

- [DONE] **Step 3 - Property tests from op semantics.** `tax_graph/verify/properties.py`:
  generate engine-executed property checks per rule from the op table - SUBTRACT antisymmetry
  (swapping inputs negates), SUM permutation + zero-identity, COPY identity, MULTIPLY/DIVIDE
  inverse where both present, and metamorphic column (h) relations (g=0 -> h=d-e; d+k -> h+k)
  - over seeded random facts, including table rules per-instance. Runs offline in `-m m8`
  against the live graph and against draft batches at extraction time. Tests: live graph
  green; the swapped-SUBTRACT drill is caught HERE (attribution proof). Docs.

- [DONE] **Step 4 - IRS worked-example miner (the answer key).** Segment instruction/pub text
  into "Example." blocks (deterministic segmentation; the blocks are already in the rendered
  pages). Micro-extract each block (existing outline-first micro pattern, narrow schema) into
  candidate `facts.yaml` + `expected.yaml` keyed to graph nodes; EXECUTE through the engine;
  report per-example agree/disagree/unmappable. Human confirms agreed candidates (a
  minutes-per-example review: one paragraph, two numbers); confirmed fixtures FREEZE into
  `examples/irs_examples/<doc>/<example_id>/` with provenance (source doc, page locator,
  quoted span) and replay offline in the base suite. Mining behind `@pytest.mark.network`;
  deterministic tests mock the client over a committed fixture block. Wire
  `tax-graph verify mine-examples --doc ID`. Docs.

- [DONE] **Step 5 - N-version cross-vendor micro-extraction.** Config gains a second
  vendor-family model for verification passes (same `LlmClient` seam). Re-run the
  micro-extraction questions for a document with model B; diff the ASSEMBLED canonical
  objects (code-assigned ids make this an object diff, not text): agree -> record
  corroboration in provenance; disagree -> review-queue entry showing BOTH answers
  side-by-side (a pick-A/B/neither human decision). Gated live run for `form_8949_2025`;
  deterministic tests with two mocked clients (agreeing and disagreeing cases). Docs.
  - Architect note (2026-07-06): Codex authored `tax_graph/verify/nversion.py` + tests but its
    session ended at the usage limit before committing or writing the handoff note. Architect
    verification: `pytest -m m8` -> 24 passed (4 new N-version tests); full `pytest` -> 161
    passed, 5 skipped; ASCII OK; tests confirm vendor-family tracking, agreement
    corroboration in provenance, and disagreement producing a side-by-side review entry.
    Committed by the Architect, authored by Codex. The gated LIVE N-version run for
    form_8949_2025 has not been executed yet - fold it into Step 6's exit-criteria pass.

- [ ] **Step 6 - Trust tiers + metrics + verify report (routing change).** Tier assignment in
  routing: T1 = L0/L1 clean; T2 = T1 + N-version agreement; T3 = T2 + properties pass + an
  example/differential executes through the object's branch. **Remove confidence from the
  auto-accept path** (it stays in provenance as telemetry); review queue = exceptions +
  deterministic 10%-min-5 calibration sample; decisions always queued. Per-run `metrics.yaml`
  beside `review.md` (objects by kind, tier distribution, flags by layer, model calls,
  examples mined/confirmed, human-minutes field filled at promotion, escapes). Wire
  `tax-graph verify report` (roll-up across forms + the payoff line: human minutes per
  promoted object, escape rate). Year-over-year delta seam: a `tax-graph verify diff-drafts`
  that structurally diffs a re-extraction against the promoted graph (the year N+1 workflow,
  exercised now against 8949 itself). Tests: tier logic; confidence-inflation no-op at the
  ROUTING level; calibration sample determinism (seeded); report golden. Exit-criteria
  commands run. Docs: README verify workflow + design-doc status update.

When all steps are `[DONE]`: mark this phase `[COMPLETE]`, move it to `plans/archive/`, update
`plans/AGENT_HANDOFF.md`, single `git push`, and tell John. With the drill gate green, bulk
extraction beyond the capital-gains set is UNLOCKED (Schedule D and 1040 extraction, the
cross-form LINK step, and M7's frontier registry become the working set). M7 (Compass Rose)
remains available in parallel throughout.
