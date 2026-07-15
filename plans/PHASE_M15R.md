# Phase M15R - Canonical Form Addressing Recovery

**Status:** READY FOR JOHN GO. This recovery phase is inserted before the remaining
M15 Gate A work. M15's human campaign and address-dependent A4-A7 work stay paused
until the gates below pass. Existing M15 A1-A3 commits and the in-progress A4
worktree are preserved, not discarded.

**Canary:** Street Address

**Depends on:** M12 field maps and geometry; M14 extension/intake boundaries; M15
A1-A3 complete-field dispositions. M15 remains the pre-ship human-review gate and
consumes the address artifacts produced here.

**Goal:** Establish one authoritative, structured identity for each official form
location and control in the bounded power-law corpus; bind PDF widgets and graph
objects to that identity explicitly; remove semantic joins that reconstruct identity
from prose, node ids, or opaque PDF field names; prove the parsing/contribution
pipeline on diverse forms; and preserve current calculation/runtime compatibility.

## 1. Why this recovery exists

Form 1040 line 1z exposed a foundational identity defect. Its graph edges correctly
target lines 1a through 1h, but the workbench formatter extracts trailing numbers
from source labels before considering the node id. Descriptions mentioning W-2 box
1, W-2 box 2, Schedule 1 line 26, Schedule 1 line 31, and Schedule F line 6 therefore
rendered the formula as `1 + 2 + 1a + 2 + 26 + 31 + 6 + 1h`.

That formatter is not the only problem. Acquisition, outline extraction,
completeness, cross-form linking, frontier generation, PDF mapping, geometry,
workbench semantics, Return Record formatting, and runtime document detection each
infer identity from a different mix of labels, descriptions, line anchors, node ids,
and AcroForm field names. A repository audit found 80 current nodes where the
workbench-derived line disagrees with the line encoded in the node id. Existing tests
can all be green because the schemas have no authoritative semantic address against
which those guesses can be checked.

This phase fixes the missing identity layer. It does not replace the tax graph or
attempt to model every IRS form.

## 2. Product outcome

The first pass over an official form produces a reviewable address tree before graph
rules are extracted or promoted. For every supported location, the tree answers:

1. Which official document is this?
2. Where is it in the document hierarchy?
3. What official line, item, box, or option label identifies it?
4. Is it a logical location, a value-bearing control, or both?
5. What kind of control is it?
6. Which physical PDF widgets and graph objects bind to it?
7. Which cross-form references claim to target it?
8. Is the identity confirmed, pending human review, provisional, or unresolved?

The reviewer can inspect Form 1040 line 1z and see operands 1a through 1h because
the formula references bound addresses. Changing prose, moving a widget, or adding a
number to a label cannot change that formula.

## 3. Bounded scope - power law, not 110-document certification

The repository currently contains 110 document records. That number is the
compatibility blast radius, not the delivery backlog.

### 3.1 Compatibility universe

All current documents must continue to load, validate at their existing support
level, and retain their current node ids and outputs. This phase must not silently
reinterpret or corrupt an out-of-scope document. Compatibility does not confer
canonical-address certification or product support.

Instruction books, publications, and other citation sources keep their source
locators and hashes. They do not need form-control address trees unless they contain
an actual structured worksheet that enters the supported graph.

### 3.2 Power-law candidate corpus

M15R is bounded to the 15 project-gated official surfaces already exposed by the
product, excluding the user-gated Form 2441 extension:

| Group | Documents |
| --- | --- |
| Root and feeders | Form 1040; Schedules 1, 1-A, 2, and 3 |
| High-value schedules | Schedules A, B, and D; Forms 6251 and 8949 |
| Information returns | W-2; 1099-B; 1099-INT; 1099-DIV |
| Intake | Form 13614-C |

This list is a ceiling for the recovery phase, not an invitation to add forms.
Form 2441 remains a user-gated extension/canary. Form 1099-R, Schedules C/E/SE,
Form 1116, and other useful forms remain contribution priorities after the pipeline
is proven; they are not added to M15R merely because they are valuable.

M15R prepares machine-valid registries and bindings for the candidate corpus. M15's
human campaign decides which of those artifacts become human-confirmed. Until then,
their provenance must say pending review. Product coverage and calculation support
remain separate: identifying a Form 6251 control does not claim its tax logic is
modeled.

### 3.3 Representative pipeline canaries

The parser and review flow must be proven on forms chosen for structural diversity:

- Form 1040: dense hierarchy, repeated lettered items, multi-control lines, and
  cross-form references.
- Form 8949: repeatable rows, columns, continuation pages, and totals.
- Schedule D or its tax worksheet: worksheet steps and cross-document flow.
- W-2 or 1099-B: box-based information return with awkward AcroForm names.
- One held-out form outside the 15-document set, initially Form 2441: contributor
  draft/package flow without project-supported promotion.

Passing these canaries demonstrates pipeline shape; it does not certify every future
IRS layout.

## 4. Canonical address contract

### 4.1 Address object

The committed semantic registry lives under:

```text
graph/<year>/addresses/<document_id>.yaml
```

Candidate registries produced by extraction live only under the existing gitignored
draft boundary. Promotion follows the standard machine-witness and deferred-review
rules; no agent writes a human-confirmed status.

Each address record contains at least:

- `address_id`: deterministic year-scoped identifier.
- `logical_key`: the same semantic path without the tax year, for rollover.
- `year` and existing `document_id`.
- `parent_address_id`: explicit tree parent, null only for the document root.
- `kind`: document, part, section, line, item, box, control, option, table,
  row-template, column, worksheet-step, or a schema-reviewed extension.
- `path`: ordered typed components, each with `kind` and stable ASCII `token`.
- `official_ref`: the printed reference used by IRS prose, such as `1a`, `3b`, or
  `Box 12 code D`, where one exists.
- `printed_label` and scoped `aliases`: display/evidence only, never identity inputs.
- `control_role`: none, amount, text, description, checkbox, radio, choice, date,
  identifier, signature, attachment-indicator, or other schema-reviewed role.
- `status`: `confirmed`, `pending_review`, `provisional`, or `unresolved`.
- source evidence sufficient to reproduce why the location exists.

The canonical string is derived from structured components, not parsed back out of
display prose. Pinned representation:

```text
address_id:  2025/form_1040/line=1/item=a/control=amount
logical_key: form_1040/line=1/item=a/control=amount
```

The serializer owns escaping, normalization, and round-trip behavior. Other modules
may compare or resolve addresses through its API; they may not construct them with
string concatenation. Printed references remain atomic evidence (`1a` stays `1a`);
the typed path expresses the document's reviewed hierarchy.

### 4.2 Unnumbered and ambiguous controls

Numbered/lettered official structure is primary. Prose-only section names become
scoped stable tokens, retaining the printed text as an alias. An unlabeled control
uses the nearest confirmed parent plus a neutral deterministic token such as
`option=1`; it remains `provisional` until a citation or human review establishes
meaning. The parser may suggest `checkbox=withdrawals`, but it may not promote that
semantic name from visual proximity alone.

An address must be unique within its document and role. Resolver results are exact,
missing, or ambiguous; there is no best-match result in a promotion path.

### 4.3 Bindings are separate artifacts

Semantic identity, physical PDF location, and graph identity are related but not the
same thing. Store them separately:

```text
graph/<year>/bindings/widgets/<document_id>.yaml
graph/<year>/bindings/nodes/<document_id>.yaml
graph/<year>/references/<document_id>.yaml
```

- Widget bindings relate opaque AcroForm field names/widgets to `address_id`, with
  widget type/on state, page, rectangle, and physical row slot. Moving or renaming a
  widget changes this binding, not the semantic address.
- Node bindings relate stable existing `node_id` values to `address_id` with a
  binding role such as value, description, decision, total, input, or output.
  Cardinality is explicit; a validator, not an assumption, decides which roles may
  be one-to-many or many-to-one.
- Reference claims relate a source address/citation to an expected target document,
  official reference/path, and optional control role. A target may be unresolved
  before its form is parsed, but it becomes resolved only when exactly one compatible
  target exists.

Field maps and node geometry gain additive `address_id` references and must agree
with these bindings. They remain output/physical projections, not address authority.

### 4.4 Repeatable identity

Preserve the established three namespaces:

1. Static semantic template address, such as the Form 8949 transaction row and its
   proceeds column.
2. Runtime fact row key, represented by the existing `#row_key` convention.
3. Physical printed row slot/widget binding.

No address id contains a taxpayer runtime key or a PDF row-slot number unless that
slot is itself official semantic structure.

### 4.5 Ranked candidate matcher - embeddings assist, validators decide

The resolver has an optional hybrid candidate-retrieval layer for references and
poorly labeled controls. It exists to reduce reviewer search effort, not to establish
identity. The authoritative resolution pipeline is:

```text
parse hard constraints
  -> exact structured lookup
  -> lexical/trigram candidate retrieval
  -> optional short-embedding top-k ranking
  -> deterministic address/role/reference validators
  -> exact connection OR explicit ambiguous/unresolved result
```

Hard constraints include document family, tax-year policy, official line/box/item
tokens, parent path, target kind, and control role. An embedding search may rank only
candidates that survive the applicable hard filters; it may not broaden the pool to a
different form, year, line, or incompatible control type. Exact structured matches
short-circuit the semantic matcher.

Embedding text may include the printed label, scoped aliases, nearby official prose,
section heading, control role, and cited reference sentence. Numbers and structural
tokens are also carried as separate validator inputs; they are never trusted to vector
similarity. For example, line 24 and line 25 are hard negatives even if their embeddings
are nearly identical.

The matcher returns a reviewable candidate record, not an address id alone:

- candidate `address_id` and rank;
- lexical and embedding scores kept separate;
- every hard-filter and validator result;
- source text/hash and target registry hash;
- embedding provider/model, revision, dimensions, normalization, and vector-input hash;
- the reason a candidate was accepted, rejected, or left for review.

A real connection is stored only when exactly one candidate passes all deterministic
structural, document/year, reference-kind, and control-role validators. Embedding score,
score threshold, or winning margin never counts as a validator. If semantic ranking was
needed because the structure itself was incomplete, the result remains provisional or
human-review-required unless independent evidence closes the missing constraint.

The search index is a reproducible derived build/review artifact, not authoritative graph
content. It may be an SQLite FTS/search table plus an optional rebuildable vector sidecar;
neither is a foreign-key source. The canonical registry stores text/evidence, not vectors.
Embedding use is build-time optional, provider-agnostic, and excluded from the light
keyless runtime. With no configured embedding provider, exact and lexical retrieval still
work and the system reports that semantic ranking was unavailable; there is no silent
model default.

Evaluation uses a committed, hermetic fixture set with frozen synthetic vectors plus an
optional live provider benchmark. Metrics are top-k recall, mean accepted rank, reviewer
search reduction, and hard-negative survival. The release invariant is stronger than an
accuracy score: changing, shuffling, or adversarially perturbing embedding ranks cannot
create an invalid resolved connection because the deterministic validators still decide.

## 5. Architecture pins

These are implementation constraints. A Worker who finds one unworkable stops and
records concrete evidence rather than silently designing around it.

1. **Registry first:** a form skeleton/address inventory is generated and reviewed
   before graph extraction or promotion for that form. Graph rules consume addresses;
   they do not define them.
2. **One resolver:** `tax_graph/addressing/` owns schemas, serialization, resolution,
   alias scoping, validation, compilation, and diffs. Downstream modules do not parse
   labels or node ids for semantic identity.
3. **Additive runtime:** existing node ids, edge ids, rules, taxpayer facts, table ids,
   traces, scenarios, and MCP node-id calls remain stable in this phase. Address lookup
   is added alongside them.
4. **Compiled indexes:** SQLite adds `addresses`, `address_aliases`,
   `widget_bindings`, `node_bindings`, and `address_references`. YAML and SQLite
   resolution must agree byte-for-byte on canonical results.
5. **No hidden fallback:** legacy heuristic resolution may exist only behind a named
   migration/diagnostic path. It emits exact/provisional/ambiguous/unresolved results
   and may not promote ambiguous output. Production consumers have no label-parser
   fallback after their migration step closes.
6. **Cross-form claims survive order:** parsing Form A may record a typed target claim
   for Form B before B exists. The linker resolves it later or preserves it as an
   explicit frontier; it never invents a target from a similar label.
7. **Trust stays honest:** machine-produced candidate addresses are pending review.
   Deferred review is allowed, but it is visible in registries, bindings, workbench
   units, and generated records.
8. **Contribution is the scale path:** out-of-core forms use the extension pipeline to
   generate address drafts, bindings, validation reports, and a review package. They do
   not enlarge the project-supported corpus automatically.
9. **Performance is indexed:** registries compile once per build/session. Tests use
   scoped fixtures for fast feedback and an explicit full-corpus integration pass;
   they do not rebuild a 4,000-plus-unit manifest for each assertion.
10. **No new tax math:** this phase can repair identity/bindings and expose existing
    rules accurately. New calculations and expanded tax profiles require their own
    later phase.
11. **Semantic search is non-authoritative:** compact embeddings may rank an already
    constrained candidate pool. They never supply a hard identity field, satisfy a
    validator, auto-confirm an address, or become a required base-runtime dependency.

## 6. Failure policy and migration report

Every migration emits a deterministic report with four buckets:

- `exact`: one authoritative address and compatible role.
- `provisional`: one structural candidate lacking enough evidence for confirmation.
- `ambiguous`: more than one compatible candidate.
- `unresolved`: no compatible candidate.

Only `exact` records may migrate mechanically into a committed binding. Provisional,
ambiguous, and unresolved records enter the review queue with evidence. A rerun over
unchanged inputs is byte-stable. No command turns those buckets into confirmed entries
without the existing human-verdict pipeline.

Candidate rankings are attached to the report as diagnostic/reviewer evidence. They do
not add a fifth resolution state and cannot convert provisional/ambiguous/unresolved to
exact. The report must be reproducible from the registry, matcher configuration, input
hash, and recorded model metadata.

The compatibility universe may retain legacy artifacts with explicit diagnostics.
The 15-document candidate corpus may not pass its address gate with silent ambiguity.

## 7. Implementation steps

**Worker rules:** one step = one commit. Each step includes core logic, focused pytest,
docstrings/docs, `pytest -m m15r`, ASCII, and `git diff --check`. The full suite is the
commit floor and may run in the background with the established long-runtime method.
Do not push until phase close unless John explicitly overrides the repository's
single-push rule. Stop at JOHN gates. Do not touch or discard unrelated dirty-worktree
changes. Never write a human-review claim on John's behalf.

### Group A - Contract, registry, and compilation

- [DONE] **R1 [worker-standard] - Schemas, vocabulary, and baseline witness.** Add schemas
  for address registries, typed paths, bindings, and reference claims; add the `m15r`
  pytest marker; commit small valid/invalid fixtures covering 1040 line 1a amount +
  description, a checkbox under line 3a, an unlabeled option, a 1099 box, a worksheet
  step, and a repeatable-table column. Capture a deterministic baseline containing
  current node/edge/table counts, runtime examples/traces, field-map/widget counts, and
  the known 80-disagreement diagnostic. Tests: schema strictness, ASCII tokens, invalid
  parent/kind/role/status combinations, and no mutation of the current graph.

- [DONE] **R2 [worker-heavy] - Address registry library and compiled indexes.** Implement
  `tax_graph/addressing/` serializer, loader, resolver, validator, alias scoping, and
  YAML-to-SQLite compilation. Add the five additive tables from pin 4 and read APIs that
  work from YAML or compiled graphs. Tests: round trip, uniqueness, acyclic parents,
  component order, year/document consistency, alias ambiguity, dangling bindings,
  incompatible roles, deterministic compile, and YAML/SQLite parity.

- [DONE] **R3 [worker-standard] - Architecture boundary and migration diagnostics.** Add
  a repository check that limits semantic label/node-id parsing to explicit legacy
  migration modules; inventory and classify every current heuristic join. Implement the
  exact/provisional/ambiguous/unresolved migration report and byte-stable rerun. Do not
  switch consumers yet. Tests seed trailing-number labels, renamed nodes, duplicate
  aliases, and missing targets.

- [DONE] **R4 [worker-standard] - Hybrid ranked candidate matcher.** Implement constrained
  candidate retrieval as a separate `tax_graph/addressing/search` layer: exact structured
  lookup first, lexical/trigram baseline second, and an optional pluggable compact-
  embedding ranker over only the surviving pool. Persist review diagnostics/model/input
  metadata, never authoritative vectors or score-based resolutions. Hermetic tests use
  frozen vectors and hostile near-neighbors: line 24 vs 25, identical labels on different
  forms/years, amount vs checkbox, adjacent unlabeled options, and deliberately shuffled
  rankings. Measure recall-at-k and accepted rank against the lexical baseline; prove that
  no score or score margin can bypass a failing deterministic validator. No embedding
  provider is configured by default, and base/runtime dependency tests remain green.

### Group B - Form-first extraction and the 1040 canary

- [DONE] **R5 [worker-heavy] - Deterministic address candidate pipeline.** Extend form
  acquisition/rendering to emit a candidate hierarchy from official text blocks,
  AcroForm widgets, accessibility/layout evidence, and explicit source hashes. The
  deterministic stage finds structure and neutral controls; an optional configured LLM
  or the R4 matcher may propose semantic aliases/candidates but cannot confirm them.
  Candidate output stays in `_drafts`. Tests: reading-order perturbation, widget
  rename/page move, trailing prose numbers, missing labels, multi-control lines, and
  repeated table rows do not change already-evidenced semantic paths.

- [DONE] **R6 [worker-heavy] - Form 1040 address tree and review surface.** Generate the
  real 2025 Form 1040 candidate tree, resolve all numbered lines/items and all inventoried
  controls, and build a focused official-page tree review view. It must show parent path,
  official ref, printed label, role, evidence, status, widget bindings, and proposed node
  bindings without showing formulas as identity evidence. Every control is exact,
  provisional, ambiguous, unresolved, or explicitly exempt. Tests include 1a-1h/1z,
  the 1h description + amount pair, filing-status controls, dependent rows/options, and
  rollover/QCD/PSO checkboxes.

### JOHN ADDRESS GATE A - approve the identity model

**PASSED 2026-07-15 (John):** Reviewed the generated Form 1040 address page and
approved continuing. The useful evidence was that specific controls, including
dependent-grid cells, were individually intelligible. This approves the identity
model and R7-R10 cutover; it is not blanket human confirmation of every generated
address, which remains honestly pending review.

John reviews the Form 1040 tree before any downstream semantic migration. The Worker
stops and records exact feedback. The gate passes only when John can select awkward
controls and unambiguously answer what their stable address is, without relying on a
formula, graph node id, PDF field name, or guessed prose meaning. Corrections amend R1-R6.

### Group C - Bindings and consumer cutover

- [DONE] **R7 [worker-heavy] - Form 1040 bindings and line 1z repair.** Promote the reviewed
  1040 registry with honest review provenance; author widget, node, and reference
  bindings; add address ids to dispositions/geometry; and change formula formatting to
  use bound operand addresses. The graph calculation remains node-id based. Tests prove
  line 1z displays exactly 1a-1h, label mutations cannot alter it, every 1040 widget has
  one disposition/address or explicit exemption, and every printable 1040 node is bound
  or has a specific non-form rationale.

- [DONE] **R8 [worker-heavy] - Verification/link/frontier cutover.** Replace semantic joins
  in outline assembly, extraction checks, completeness, LINK, and frontier generation
  with address resolution/reference claims. Preserve structural text extraction as
  evidence, not identity. Seeded defects: swap 1b/1e, route an amount to a checkbox,
  duplicate an option, misroute a cross-document target, and delete a target registry.
  Each fails at the responsible layer. Add those defect classes to the M8 drill catalog.

- [DONE] **R9 [worker-heavy] - Output/runtime/public compatibility cutover.** Compile and
  consume widget/node bindings in field maps, geometry, fill, sidecars, return records,
  used-form detection, oracles, and verification records. Add optional MCP/address APIs
  to resolve/list addresses while retaining all current node-id calls. Tests: current
  examples, taxpayer facts, OTS values, traces, repeatable rows, filled-PDF echo, and MCP
  calls retain parity with the R1 baseline; used-form detection no longer parses a node
  id prefix.

- [DONE] **R10 [worker-heavy] - Workbench address units.** Make review units address/control
  based. The selected address drives official markers, details, citations, rules,
  upstream/downstream bindings, and formula operands. Remove `semantics._line_number` and
  every production display fallback that derives an official ref from a label or node
  id. Tests: selected-only markers; keyboard tree traversal; no label overlap; distinct
  controls on the same line; coverage counts reconcile address = widget disposition =
  review unit; Form 1040 1z remains 1a-1h under hostile label mutations.

### Group D - Power-law corpus and contribution proof

- [ ] **R11 [worker-heavy] - Core return candidate registries.** Run the proven pipeline
  over Schedules 1, 1-A, 2, 3, A, B, and D plus Forms 6251 and 8949. Commit only
  machine-valid artifacts with honest pending-review state; queue every non-exact
  decision. Prove Schedule D worksheet steps, Form 8949 row-template/column addressing,
  and all existing cross-form claims. No new tax logic. Per-document reports reconcile
  widget/address/node/reference coverage.

- [ ] **R12 [worker-heavy] - Information-return and intake registries.** Apply the same
  pipeline to W-2, 1099-B, 1099-INT, 1099-DIV, and 13614-C. Box names/codes and checkbox
  choices are typed controls, not prose-derived node names. Verify the existing intake
  routes and universal gates resolve through addresses while retaining provenance and
  unsupported-box records.

- [ ] **R13 [worker-standard] - Held-out contributor flow.** Use Form 2441 as an
  out-of-core held-out form through `extend` candidate generation, validation, review
  package, and local user-gated acceptance. It must not enter the project-confirmed
  corpus or block M15R close. Document the contributor contract: exact machine witnesses,
  explicit unresolved list, no drafts committed, no corpus expansion without project
  review, and no human-confirmed claim from automation.

### JOHN ADDRESS GATE B - accept campaign readiness and bounded scope

John reviews the representative set: Form 1040, Form 8949, Schedule D worksheet, one
information return, and the held-out Form 2441 contribution package. The gate checks
that the pipeline generalizes across structure types and that unsupported/niche forms
remain contributor work. It does not ask John to certify all 15 forms in this phase.
M15 performs the full power-law corpus review.

### Group E - Rollover seam and close

- [ ] **R14 [worker-standard] - Cross-year identity/delta fixtures.** Implement address
  diffs through yearless `logical_key` with explicit unchanged, added, removed,
  renumbered, split, merged, and unresolved results. Fuzzy matching may suggest a
  candidate but cannot inherit trust. Synthetic TY2025/TY2026 fixtures prove each case;
  no real TY2026 form work is pulled into this phase.

- [ ] **R15 [worker-light] - Records, docs, exit run, and handback to M15.** Run all exit
  criteria; regenerate affected records after frontier rebuild in the standing order;
  document the as-built author/contributor workflow and compatibility API; reconcile the
  R1 baseline; update M15 A4-A7 to consume addresses and remove superseded heuristic
  requirements; record both John gates; mark this plan complete/archive it; then resume
  M15 Gate A work. One phase-level push after every step commit is verified.

## 8. Exit criteria

All commands and product conditions pass 100 percent:

```powershell
python tools\check_ascii.py
python -m pytest -m m15r -q
python -m pytest -q
python -m tax_graph.cli validate 2025
python -m tax_graph.cli build 2025 --output <throwaway-sqlite>
python -m workbench.cli preflight --year 2025
python -m tax_graph.cli frontier build
python -m tax_graph.cli verify record
```

Plus:

- Both JOHN address gates pass.
- Form 1040 line 1z displays 1a-1h from bindings under hostile label mutations.
- The 15-document candidate corpus has deterministic registries/bindings, exact
  coverage reports, and no silent ambiguity. Pending human review remains visible.
- The other repository documents retain baseline compatibility without being claimed
  as address-certified or product-supported.
- No production semantic join reconstructs an official reference from display prose,
  a node id, or an opaque field name.
- YAML and compiled SQLite address resolution agree.
- Existing runtime values, traces, facts, node-id APIs, repeatable-row behavior, and
  filled-PDF echo retain parity.
- The held-out contributor form produces a complete draft/review package without
  entering the project-gated corpus.
- The matcher beats or documents parity with the lexical baseline on committed top-k
  fixtures; all hostile hard negatives are rejected by deterministic validators; shuffled
  or adversarial embedding ranks cannot create or change a resolved connection.
- Exact resolution and the full keyless runtime remain functional with embeddings disabled
  and no embedding provider installed or configured.
- No agent-authored human-confirmed provenance exists.
- The base runtime remains light and provider agnosticism is unchanged.

## 9. Explicit deferrals

- Human confirmation of every candidate-corpus address happens in M15's review
  campaign. M15R prepares trustworthy units and obtains representative gate approval.
- New tax calculations, additional form coverage, and expanding the supported taxpayer
  profile are not part of address recovery.
- Form 1116, 1099-R, Schedules C/E/SE, and other high-value forms enter through the
  contributor pipeline after the canaries prove it; priority can be driven by SOI weight
  and graph centrality.
- Production embedding-model choice, vector dimensions, and whether live embeddings earn
  their cost remain evidence-driven configuration decisions. M15R implements the pluggable
  ranked-matcher contract and hermetic evaluation; it does not pin a vendor/model or make
  semantic search mandatory. Computer vision and LLM suggestions obey the same
  non-authoritative boundary.
- Making addresses the primary taxpayer-fact or MCP execution input is optional future
  API work. Node-id backward compatibility is not scheduled for removal.
- Real TY2026 migration waits for official forms. This phase implements only the seam
  and synthetic delta witnesses.

## 10. Non-goals

- Canonicalizing all 110 document records.
- Hand-authoring every niche IRS form.
- Renaming existing graph nodes or rewriting the calculation engine.
- Treating PDF field names, page coordinates, or printed prose as stable semantic ids.
- Auto-confirming candidate addresses or auto-merging contributor drafts.
- Turning M15R into another tax-math expansion phase.
