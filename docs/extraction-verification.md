# Extraction Verification at Scale (the trust ladder)

> Design note behind milestone **M8** in `docs/engineering-plan.md`. Written 2026-07-05.
> Problem owner: John. The question this answers: "If we can't verify the accuracy of
> extractions both reliably and efficiently, this project never pays off."

## 1. The problem

M4 proved extraction works on Form 8949: outline-first, deterministic checks, a critic,
and a human held-out diff against the hand-authored `graph/2025/` reference. But the
held-out diff is the load-bearing accuracy check, and it has two fatal scaling flaws:

1. **It needs a hand-authored reference.** Hand-authoring is exactly what extraction is
   supposed to eliminate. For Schedule D, 1040, Schedule B, and the rest of the personal
   form set there will be no reference to diff against.
2. **The canary is no longer held out.** We iterated the pipeline until `form_8949_2025`
   came back `accepted=73, review=0, issues=0`. That number measures fit to the canary,
   not accuracy on the next form. Treat it as encouraging, not as evidence.

Meanwhile the other checks have a shared blind spot: they verify FORM, not MEANING. A
draft that swaps minuend and subtrahend, points an outbound flow at Schedule D line 2
instead of line 3, or merges lines 1a/1b into one node can be schema-valid, line-complete,
grid-reconciled, and citation-verified - and still wrong. The same-model critic is weak
corroboration (the plan already says so), and nothing today measures whether the check
net would actually catch such errors.

**The payoff condition, stated explicitly:** human review effort per form must be (a)
concentrated on machine-flagged exceptions, (b) cheap per item (verify a number, not
re-derive a form), and (c) trending toward a small audited sample - while a measured
escape rate stays at or near zero. If we cannot hit that, the concern is right and the
pipeline does not pay off. Everything below exists to hit it.

## 2. Failure taxonomy (what we are defending against)

- **F1 Omission** - a true line/column never becomes a node. (Partially covered today by
  true-anchor completeness.)
- **F2 Wrong structure** - lines merged/split wrongly; wrong part/column attribution;
  table rows vs totals confused.
- **F3 Wrong semantics** - right nodes, wrong rule: wrong op, swapped roles
  (minuend/subtrahend), missing addend, wrong rounding. THE dangerous class: plausible,
  well-formed, and invisible to structural checks.
- **F4 Wrong routing** - outbound flow targets the wrong form/line; feeds the wrong
  downstream node. Corrupts other forms' results.
- **F5 Wrong provenance** - citation quotes the wrong passage for a correct rule.
  (Largely prevented by construction: code lifts spans; the model only selects.)
- **F6 Phantom** - a node/rule for something the form does not say (hallucinated
  worksheet line, invented condition).

Structural checks (today's layer) catch most F1 and some F2/F6. F3 and F4 are only
reliably catchable by *executing* the graph. That is the design center.

## 3. The verification ladder

Layers ordered cheapest-first. Each layer's job: catch a failure class deterministically
so no human ever has to look for that class by eye. A draft object climbs the ladder;
its height = its trust tier (Section 5).

### L0 - Structural determinism (EXISTS, keep)
Schema validation, closed op vocabulary, rule-has-citation, true-anchor line
completeness, field-grid x/y reconciliation, citation-quote-by-construction.
Catches: F1 (line side), gross F2, F5. Cost: free, offline.

### L1 - Authoritative structural ground truth (extend L0)
Two machine-readable inventories of "what boxes exist" that we do not author:
- **AcroForm field grid** (already acquired per form) - completeness must hold BOTH
  directions: every true anchor has a node AND every entry field maps to some node or an
  explicit not-modeled record. Direction two is new; it catches F1 omissions that the
  text renderer drops.
- **MeF e-file schema line inventory** - the IRS Modernized e-File XML schemas enumerate
  form elements per line. Per the oracle research (see memory/test-oracles): ATS
  scenarios are weak as a MATH oracle, but the MeF *schema* is a strong BOX-MAPPING
  oracle. Worker pins availability/licensing; if the schema package is not cleanly
  obtainable, this sub-check is skipped (the field grid remains) - do not scrape from
  dubious mirrors.
Catches: F1, F2. Cost: free after acquisition, offline.

### L2 - N-version extraction (cross-model corroboration)
Run the micro-extraction pass (M4 Step 7 style: tiny questions, narrow schemas) with
N>=2 models from DIFFERENT vendors via the existing provider-agnostic `LlmClient` seam,
then diff the ASSEMBLED canonical objects (ids are code-assigned and stable, so diffs
are meaningful object-level diffs, not text diffs). Same-vendor critic agreement is weak
because errors correlate within a model family; cross-vendor agreement on a *structured
answer to a narrow question* is strong. Disagreement -> review queue with both answers
shown side by side (a cheap human decision: pick A, B, or neither).
Catches: F3, F2, F6 (uncorrelated halves). Cost: multiplies micro-call cost by N; micro
prompts are small and cheap-model-viable, so this is dollars, not hours. Gated/network.

### L3 - Property tests derived from op semantics (behavioral, free)
For every extracted rule, generate property checks from the op's known algebra and run
them through the ENGINE on random facts: SUM permutation/zero-identity; COPY identity;
SUBTRACT antisymmetry (swapping inputs negates - catches swapped roles); column (h)
metamorphic relations (g=0 implies h=d-e; increasing d by k increases h by k). All
offline, no LLM, generated in code from the rule + op table.
Catches: F3 (the wrong-role/wrong-op core). Cost: free, deterministic, runs in CI.

### L4 - IRS worked examples as numeric ground truth (behavioral, authoritative)
The instructions/pubs contain "Example." blocks with real numbers - per the oracle
research these are THE authoritative numeric cases. Add an example-miner stage: extract
each worked example into a candidate `facts.yaml` + `expected.yaml` fixture, run it
through the engine against the extracted graph, and compare. A human review of a mined
example is MINUTES (read one paragraph, confirm two numbers) versus HOURS to cold-review
a graph draft - this is the key economics move: push human attention from reviewing
*drafts* to confirming *examples*, then FREEZE confirmed examples as committed
regression tests (the `examples/` pattern that already exists). A form whose examples
compute correctly through the extracted graph has its arithmetic verified end to end by
IRS-authored numbers.
Catches: F3, F4 (within-form), F2. Cost: one small extraction call per example + minutes
of human confirmation, once per form-year; then free forever.

### L5 - Differential vs independent implementations (M6, extended)
The M6 harness (OpenTaxSolver box-level; PolicyEngine/Tax-Calculator liability-level)
doubles as EXTRACTION verification: every promoted form with oracle coverage gets
scenario diffs, and cross-form routing (F4) is exactly what box-level diffs catch.
Additionally at LINK time (deferred cross-form step): every outbound-flow declaration
must resolve to a TRUE ANCHOR of the target form's own extraction - a deterministic
reconciliation of F4 once two forms exist.
Catches: F3, F4 (cross-form). Cost: per M6; scenarios reused across the suite.

### L6 - Human review, reshaped (exception + calibration only)
Humans see exactly two queues:
1. **Exceptions** - anything a layer flagged, presented with the evidence that flagged
   it (the two disagreeing model answers; the failing example arithmetic; the missing
   field). Never "please re-derive this form from scratch".
2. **Calibration audit** - a fixed random sample (default 10 percent, min 5 objects) of
   fully-passing objects per form, reviewed cold. Escapes found here are the ESCAPE RATE
   - the single number that tells us whether trusting the ladder is justified - and every
   escape becomes a new seeded-defect drill case (Section 4), so the net only tightens.

## 4. Measuring the net itself: seeded-defect drills

The question "do we trust auto-accept?" must be a measured number, not a vibe. A drill
harness takes a KNOWN-GOOD graph (the hand-authored capital-gains slice - its one
permanent job after extraction replaces hand-authoring), injects one defect per run from
a catalog keyed to the taxonomy, and asserts the ladder catches it and names the layer:

- swap minuend/subtrahend on column (h)            -> expect L3
- change SUM to SUBTRACT on a totals rule          -> expect L3/L4
- drop one addend edge from a totals rule          -> expect L3/L4
- delete a required line node                      -> expect L0/L1
- merge two adjacent lines into one node           -> expect L1
- retarget an outbound flow one line off           -> expect L5 (LINK reconcile)
- corrupt a citation quote                          -> expect L0
- add a phantom node with a plausible id            -> expect L1 (field inventory)
- inflate every confidence to 1.0                  -> expect NO effect (confidence must
  not be load-bearing)

This is mutation testing of the verification net. Fully deterministic, offline, in CI
(`pytest -m m8`). **Gate: the net must catch 100 percent of cataloged drill classes
before extraction expands beyond the capital-gains form set**, and the catalog only
grows (every real-world escape is added). If a drill class cannot be caught by any
layer, that class of object is NOT auto-promotable - it goes to the human exception
queue by policy, honestly.

## 5. Trust tiers and the promotion rule (proposed to John)

- **T0 draft** - failed something; exception queue.
- **T1 structural** - L0+L1 clean.
- **T2 corroborated** - T1 + L2 cross-vendor agreement.
- **T3 behavioral** - T2 + L3 properties pass + at least one L4 example or L5 scenario
  executes through the object's branch correctly.

Proposed promotion rule (replaces "human diffs everything"): **rules and edges require
T3; nodes and citations require T2; decisions always get human eyes** (they encode
judgment by definition). The human promotion step remains (drafts are never auto-merged
- unchanged), but the human reviews the exception queue + the calibration sample and
signs the batch, rather than re-deriving the form. Confidence scores are recorded as
telemetry but are never load-bearing (drill-enforced).

Defaults John can veto: calibration sample 10 percent (min 5); drill bar 100 percent of
catalog; N=2 vendors for L2 (3 for rules that no example/scenario reaches).

## 6. Year-over-year deltas (the long-run efficiency lever)

Forms change little between years. Once year N is verified, year N+1 extraction is
verified as a DIFF: re-extract, structurally diff against year N's promoted graph, and
route only changed objects up the ladder; unchanged objects inherit their tier with a
re-run of the free layers (L0/L1/L3 + frozen L4 examples). M3 change detection already
tells us which source docs changed. Steady-state annual cost per form approaches: run
the free layers + human-review the genuine deltas the IRS actually made.

## 7. Economics: what we track

Per extraction run, write `metrics.yaml` beside `review.md`: objects by kind, tier
distribution, flags by layer, resolved model calls/tokens/cost by call, examples
mined/confirmed, and (filled at promotion) human minutes spent + escapes found. The
draft provenance records the requested and resolved model for objects produced by a
live call; if the provider omits a resolved model or usage value, the field remains
null rather than claiming attribution. A `tax-graph verify
report` rolls these up across forms. The payoff condition in Section 1 becomes a
dashboard line, reviewed at each phase gate: **human minutes per promoted object,
trending down; escape rate, at or near zero.**

Live extraction also writes one JSONL run log under `output/logs/`. It records the
run-level configuration and totals plus each provider request/response envelope,
including finish reason, latency, and outcome. Successful bodies appear at DEBUG
level; failed calls retain capped request and response bodies. The log never stores
API keys or client headers. Self-reported object confidence remains in `metrics.yaml`
only as `untrusted_telemetry`; routing and promotion do not consume it.

## 8. What this does NOT change

Drafts still never auto-merge and never commit. The LLM still never computes a return.
Supported-branch bar (testing-strategy) unchanged - L4 examples and L5 differentials
directly feed its requirements 3 and 4. Provider-agnostic seam unchanged (L2 depends on
it). ASCII-only, offline-deterministic CI, gated network jobs - all unchanged.

## 9. Milestone mapping

This lands as **M8 (canary: Skeptical Notary)** - see `docs/engineering-plan.md` for the
milestone block, gate row, and sequencing. Steps 1 (drills), 2 (L1 both-directions +
MeF), and 3 (L3 properties) are offline and independent of M5/M6; Step 4 (example
miner), Step 5 (N-version), and Step 6 (metrics + delta mode) complete the ladder. M6
supplies L5. PHASE_M8.md is written just-in-time when M8 becomes next.

## 10. User-facing Form Verification Record (decided 2026-07-06, build post-M7)

Everything above records evidence for the MAINTAINERS; users need the same story told
honestly, per form. Decision (John): a **Form Verification Record** - one GENERATED
Markdown page per form plus a roll-up `VERIFICATION.md` - stating what is modeled, which
witnesses back the math, what disagreed and how it was resolved, and a plain-language
verification tier. Rules:

- **Generated from data, never hand-written** (same law as the Coverage Map): rendered
  deterministically from `metrics.yaml`, the corpus manifest, `triage.yaml`, drill
  results, frozen IRS examples, and graph status. No LLM, no API key, committed to the
  repo (it describes public forms, not taxpayer data).
- **The witness list is the honesty mechanism.** OTS's breadth is limited, so each form
  lists ITS witnesses explicitly: differential scenarios (oracle + version + count)
  where an oracle covers it; frozen IRS worked examples; cross-vendor N-version
  agreement; property tests; calibration audits + escape count. A form with no external
  oracle SAYS SO and shows what it has instead - the absence is stated, never papered
  over. Plain-language tiers map from the supported-branch bar (testing-strategy):
  "independently witnessed" > "IRS-example verified" > "structurally verified" >
  "partial".
- **Disagreements build trust.** Triage outcomes appear (our bug fixed + regression;
  OTS bug reported upstream; IRS-text ambiguity documented on the graph object) - a
  record that shows adjudicated conflict is more credible than a clean sheet.
- **Queryable at runtime.** The same data surfaces over MCP (additive tool or document
  metadata) so the filer's agent can answer "how validated is this branch?" in
  conversation - confidence is roadmap content, per the core thesis.
- **Slot:** build after M7 (the frontier registry supplies coverage/status per form and
  enforces box-map growth); render as part of `tax-graph build`. Complements the
  reserved Coverage Map (map = breadth at a glance; record = depth per form).

## 11. Status (2026-07-06): IMPLEMENTED (Sections 1-9)

M8 is complete (`plans/archive/PHASE_M8.md`). The ladder runs: drills catch 100% of the
catalog with layer attribution; routing is deterministic from check outcomes (confidence
is telemetry, drill-proven); `tax-graph verify report` prints the payoff lines. Two
refinements learned from the LIVE runs, now part of the design:

- **L2 compares the SEMANTIC core only.** Free-text fields (label/description) and
  citation-span SELECTION are excluded from the cross-vendor diff: spans are already
  verbatim-verified by construction, and which of several valid supporting spans a model
  picks is provenance quality (F5), not a formula disagreement (F3). Without this the
  review queue drowns in prose-phrasing noise and the economics collapse.
- **Small models are fine BECAUSE the questions are fenced** (John's rule, validated
  live): a mini-class secondary agreed with the flagship primary across the whole 8949
  structure and diverged only on one totals-rule shape - which the queue caught and a
  human adjudicates in seconds against the promoted graph.
