# Intake and Document-Driven Onboarding (stub)

Status: DIRECTION PINNED 2026-07-07. This is a target statement, not a build plan.
Flesh out post-M10. Companion doc: `docs/self-serve-extension.md`. Nothing here
changes M9 or M10 scope.

## Thesis

Intake inverts the fixed tax-software interview. Traditional software walks every
user through the same choreography because it cannot know what is missing until it
asks everything. The graph can know: documents assert facts, facts activate
branches, `list_required_inputs` computes the exact frontier of unknowns, and the
AI asks about only those - conversationally, in the user's order, with the IRS
citation in hand for every question.

Primary entry channel: the user drops their tax documents in a directory and the
AI crawls it. Most of a typical return is assembled from information returns
(W-2, 1099-B/DIV/INT/R/NEC/G, 1098, K-1); those are keyed, structured documents
that classify reliably and deterministically imply forms and lines.

## The funnel

1. CLASSIFY. Crawl the drop directory, OCR/parse each document, identify its
   type and extract its box values. This is AI squish.
2. ROUTE. Map each document type + box to the form lines it feeds, via routing
   edges in the graph (see below). Activated lines pull in their forms; forms
   outside the modeled set land on frontier declarations and surface the
   self-serve extend path. This is mechanical and cited.
3. GAP-FILL. Sweep the trigger checklist for branches with no paper trail
   (dependents, cash income, estimated payments, life events). Ask only what
   evidence did not already resolve. This is AI squish over mechanical,
   cited trigger data.

## Relevance layer, not a second graph

Intake artifacts live in the SAME graph as additive node/edge kinds - a
relevance layer beside the existing computation layer. No second engine.

- ROUTING EDGES: information-return box -> form line ("1099-DIV box 2a feeds
  Schedule D line 13"). Citable from the recipient instructions printed on the
  information return itself ("Report this amount on..."). Information returns
  are already document nodes (form_1099b exists today).
- TRIGGER NODES: mined from Form 13614-C checklist items, each pointing at a
  graph entry point (form line or frontier declaration), each cited.
- EXPECTATION EDGES: claim -> expected evidence ("employee status expects one
  or more W-2s"). Drive bidirectional reconciliation (below).

The AI never routes, triggers, or reconciles from memory. It queries the
relevance layer over MCP and gets citations back - same discipline as the
existing MCP contract (no rule without its citation; report unsupported
rather than guess).

## Trigger resolution model (required vs conditional)

Pinned reframe: REQUIRED means must-be-resolved-before-filing, not
must-be-asked-early. Per the 13614-C's own quality-review doctrine, every
trigger must reach a resolved state - yes, no, or unsure (escalate; never
guess). Resolution sources, in preference order: document evidence,
derivation from known facts, asking the user. Asking is the fallback, not
the spine.

Obligation classes (metadata the 13614-C mining must produce per trigger):

1. UNIVERSAL GATES - always explicitly confirmed with the human, never
   silently inferred: filing status, dependents, the digital-asset question
   (the 1040 itself makes it mandatory for every filer - required-ness is
   citable). Small set.
2. CONDITIONAL TRIGGERS - the bulk of the checklist; dormant until a fact or
   document activates them.
3. EXPECTATION EDGES - reconciliation constraints, both directions:
   - claims-without-docs: user asserts employee status, no W-2 present ->
     ask; do not proceed silently.
   - docs-without-claims: a 1099-NEC is in the folder but the user said no
     self-employment income -> surface it; never silently ignore a
     classified document.

Careless-user protection is a COMPLETENESS GATE at the end of intake: no
unresolved triggers, no unreconciled expectations, or the return does not
proceed. Same shape as every other gate in the project.

Every resolution is logged in the Return Record with provenance ("resolved by
W-2 x3", "user asserted no", "unsure - escalated"), giving an audit trail of
what was asked and what the user attested. A half-finished intake is just a
Return Record with open frontier items - resumable by design, no new state
machinery.

## Mining targets (all public IRS PDFs, standard pipeline)

- Form 13614-C (Intake/Interview & Quality Review Sheet): the IRS's own
  intake instrument -> trigger nodes + obligation classes. Preserve its
  every-question-reaches-a-state doctrine.
- Pub 4012 (VITA/TCE Volunteer Resource Guide): decision charts (filing
  status, dependency tests, credit eligibility) -> trigger/decision wiring.
- Recipient instructions on each information return: routing edges with
  verbatim "report this amount on..." citations.
- Pub 17: plain-language definitional depth for citations on eligibility
  facts (e.g. qualifying child tests).
- Form 1040 instructions Charts A/B/C (who must file) and the Interactive
  Tax Assistant topic list: decision-tree maps, mineable.

All go through the same acquire -> extract -> verify net as forms, with
citations and completeness checks:

- Every 13614-C item becomes a trigger or an explicit not_modeled record.
- Every box on a modeled information return becomes a routing edge or a
  declared out-of-scope record.
- Both-direction completeness, M8 style.

## Privacy

The crawl is local. The only egress is OCR/LLM calls to the user's configured
providers - that is the informed-consent moment, stated before the first byte
leaves. Provider-agnostic per repo policy.

## Non-goals

- Not a build plan; no schema/CLI/engine changes until the flesh-out pass.
- Not a replacement for the escape hatch: "unsure" always escalates to a
  human-visible decision, never a guess.
- Not scope growth for M9/M10.

## Open questions (for the flesh-out pass)

- Trigger/routing/expectation schema: new kinds vs generalized edges; how
  obligation class and expectation cardinality (one-or-more W-2s) are
  expressed.
- How expectation edges are cited (13614-C itself? who-must-file charts?).
- Document classifier design and its verification story (N-version over
  classification? a labeled fixture corpus?).
- Whether trigger sweep ordering hints (early vs deferrable) are worth
  modeling or left entirely to AI squish.
- Multi-document reconciliation depth (count matching, withholding totals)
  - v1 is presence/absence only.
