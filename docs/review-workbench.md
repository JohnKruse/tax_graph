# Review Workbench

> Product reset, 2026-07-13: the current static bundle is infrastructure only and is not
> an accepted human-review surface. The human campaign is paused. The authoritative
> replacement design and implementation sequence are in `plans/PHASE_M15.md`.

Status: M15 Gate A corrections A1-A4 as-built, 2026-07-14. Canary: "Fresh Eyes". The workbench is a
top-level workspace member with an artifact-only read seam. UI and verdict emission
remain in later M15 steps.

## Legacy scoped queue migration

Older isolated producer fixtures may still carry an additive `review_scope` projection.
Each pending entry has a scope type and explicit object refs with an object type,
object id, source artifact path, and review role. The live workbench no longer reads
or writes a generated queue; current review coverage comes from the physical-cell
projection, graph cells without page geometry, and a separate routing review set.
The address-keyed verdict ledger remains the human-history seam.

## Derived review coverage

The workbench derives one review unit per physical form control and one unlocated unit
per published graph cell without page geometry. It also projects routing edges, intake
triggers, and decisions into a separate routing review set. It does not read a generated
deferred-review queue. Human decisions live in the append-only address-keyed verdict
ledger, where the reviewed content fingerprint binds the label, expression tree, form
citations, and instruction citations, making changed content require review again.

For Form 1040, the generated review projection also covers the complete physical
field-map inventory. Existing authored policies are carried into the draft deterministically;
only unsupported controls are sent through the background-policy micro-extraction, and
the code resolves every field and citation identity. Model results remain draft-only and
unsupported results become named review gaps, so the review denominator stays stable
through regeneration without hand-authoring generated cells.

## Three-column review command

The repeatable input-versus-graph review is generated with:

`python -m tax_graph.cli review-table --year 2025 --document form_1040_2025 --hardest 10 --output C:\\review\\form_1040.html`

After a completed derivation run, build a pending-review candidate outside the
repository and point the same table at it:

`python -m tax_graph.cli regenerate-candidate --year 2025 --run-dir C:\\runs\\ty2025 --output-dir C:\\candidates\\ty2025`

`python -m tax_graph.cli review-table --year 2025 --document form_1040_2025 --candidate-root C:\\candidates\\ty2025 --all-rows --output C:\\review\\form_1040_candidate.html`

Candidate output is machine-generated evidence, not a human approval and not a
published graph. Publishing is a later, review-gated operation that replaces the
generated graph directories as one build artifact; rollback restores the prior
committed tree.

The output path must be outside the repository. The first column is the cleaned printed
instruction used by derivation, with the related instruction source kept separate. The
second column shows the exact stored graph expression, status, and any recorded validator
findings or warnings. The third column is a deterministic pseudocode rendering of that
same expression tree; it never comes from a model. Use `--all-rows` for an exhaustive
table. Selection scores count conditionals, caps, dollar constants, table columns,
cross-document references, and sentence count, and every selected row displays those
signals. The artifact makes no correctness judgment and writes no graph or review state.

## Complete field dispositions

Field-map schema version 2 classifies every terminal AcroForm widget with exactly one
population policy: user-entered, imported, copied, computed, decision-required,
intentionally blank, or unsupported. Each disposition carries a derived reviewer label
and value format. Graph, identity, runtime-fact, and source references are explicit;
repeatable controls also identify their group, printed row slot, column, and role.
Intentionally blank and unsupported controls must name the reason, downstream effect,
and capability needed to close the gap.

`tax-graph review migrate-field-dispositions --year 2025` creates a deterministic
authored-work list. It copies only legacy identity mappings whose user-entered policy is
provable. It does not guess graph operations, frontier consequences, or policies for
unmapped controls. Build-time AcroForm preflight enumerates widgets directly from the
official PDFs; instruction PDFs with no widgets are exempt.

The 2025 sweep covers every exposed AcroForm, including source documents,
intake, and the optional Form 2441 extension boundary. Form 1040 lines 1b-1h
use their full IRS anchors (not bare letters); line 1h keeps separate description
and amount controls, and line 1z continues to sum lines 1a-1h. The maintenance
tool `tools/author_field_dispositions.py` rebuilds inventories from the official
PDFs, preserves authored mappings, and emits actionable unsupported policies for
controls that lack a graph, filer-fact, or decision mapping.

## Step 1 artifact contract

`workbench.artifacts` reads the published artifacts directly and never imports a
pipeline module. The compiled SQLite graph is opened in SQLite read-only URI mode;
graph rows are decoded from their public `object_json` columns. The node geometry
projection is validated against its committed JSON Schema. Draft directories expose
YAML/JSON as structured data and Markdown/HTML as
text, while metrics, N-version reports, and mined-example reports are indexed by
workspace-relative artifact path. Source PDFs are represented by path, byte size, and
SHA-256 metadata; rasterization belongs to Step 2 and is not a runtime dependency of
the read seam.

`review-workbench inspect --year 2025` is the Step 1 smoke command. It reports the
artifact counts without writing any file. The committed `m15` boundary test walks all
workbench Python files and rejects imports from `tax_graph` and its pipeline modules.

## Step 3 review manifest

`workbench.manifest.build_manifest` projects the physical form-cell inventory and
geometry-free graph cells into document entries, then adds a separate routing entry.
Each unit carries exact object identifiers, a schema-valid review expression, split form
and instruction citation slots, and either official geometry or explicit `null`
geometry. The manifest hash is computed from canonical artifact hashes and unit data,
so repeated builds are byte-stable. Build one with:

`python -m workbench.cli manifest --year 2025 --output-dir .workbench_state/2025`

S3 intentionally does not generate English semantic text or infer missing geometry.

## Step 4 simple semantics

The manifest now replaces structure-only node references with plain-English summaries and
schema-validated expression trees when a scoped computed node uses COPY, SUM, SUBTRACT, or
NEGATE. Labels are derived from the IRS document and line spine: same-document operands use
compact `line N` labels, while cross-document copies retain names such as `Schedule 1 line 10`.
The workbench never falls back to displaying raw rule JSON as an explanation.

## Step 5 complete semantics

Every operation in the current compiled graph now has an explicit formatter: table and keyed
lookups, bracket lookups, MIN/MAX choices, cited-parameter multiplication, and IF/ELSE branches
join the Step 4 arithmetic set. Repeatable-table members distinguish per-transaction templates
from totals; parameter, frontier, review-gap, input, and imported nodes have purpose-built
expressions. Unknown operations raise `SemanticFormatError` so Step 6 preflight can fail with an
actionable error rather than expose raw JSON or invent an explanation.

## Step 2 artifact view

`workbench.geometry.GeometryIndex` keeps the AcroForm field layer, resolved node
provenance layer, and unresolved identity/gap layer separate. Point and rectangle
selection is performed in PDF page coordinates, so repeated Form 8949 row slots stay
display geometry and never become runtime node ids. `review-workbench build --year
2025` rasterizes source PDFs with the optional PDF extra and writes a static HTML
bundle with no CDN or API dependency. The bundle carries the public graph rows,
citation data, derived review units, metrics, N-version reports, and mined-example reports in an escaped
JSON payload. A node id absent from the compiled graph is rendered as a visible gap
finding rather than being treated as resolved.

## Step 3 verdict contract

The workbench emits only new records under `review_verdicts/<year>/`; it never edits
the derived cell inventory, graph, or drafts. Each address-keyed verdict is
schema-validated and carries the reviewed label, expression, separated form and
instruction citation slots, canonical fingerprint, judgement, an automatically captured
machine/session reviewer id, and UTC timestamp. An optional batch tag groups a review
pass without entering the content fingerprint. Generated cells expose the five
pipeline outcomes `computation`, `filer_entry`, `election`, `information_return`, and
`not_derivable`, with their form citation and instruction citation evidence. A
`not_derivable` result keeps its machine reason visible; it is not relabeled as a
generic review gap.

The three visible generated-cell verdicts are `confirmed`, `questioned` (shown as
`Try Again`), and `rejected`. Try Again sends its comment as evidence and stores only
an in-memory attempt token. Accepting that exact attempt is the only action that
curates its comment into the address ledger. Reject writes a local JSONL defect report
with the rejection comment and retry history; it never posts to GitHub. A project-gated
rejection can only be abandoned. A user-gated rejection can instead continue as
filer-provided, which projects the cell to `REQUIRE_INPUT` without counting it as
derived.

Review comments carry an explicit `origin`: `curated` comments are bounded pipeline
input, while `contributed` comments are retained for lead editing and never reach the
model. Legacy comments without an origin fail closed and are not used as model input.
The latest curated comment for an address wins; the complete ledger remains available
for audit. A changed fingerprint produces a derived `needs_recheck` state. Review-gap
expressions are counted explicitly as `NOT_REVIEWABLE` rather than as unreviewed work.
No workbench action asserts a human-review claim on the user's behalf.

## Human-loop re-derive

The pipeline exposes a single-cell, non-persisting re-derive callback with the shape
`document_id`, `line`, and an optional `draft_comment`. The workbench server exposes it
at `POST /api/rederive` when the application host injects that callback. The request
requires the local write token, returns the derived row plus its validation report, and
writes no draft, graph, verdict, or session state. A draft comment is a try-again input;
it is not stored until a separate explicit Accept action records the verified comment.
The generated-cell panel owns this flow, so there is no detached retry panel that can
be mistaken for a verdict control.
The server keeps this callback injected so the artifact-only workbench does not import
pipeline code.

## Year-to-year rollover review (John's decisions, 2026-07-30)

Settled design for the tax-year boundary. Not yet built; it matters at the 2026 boundary,
and the address + fingerprint machinery it depends on already exists and is verified.

**The shape.** Process the new year's forms through the pipeline, then compare cell by cell
against the previous year's approvals. Carry the approval where the cell is essentially the
same; put changes and additions in front of the reviewer.

**Carry identical cells WITHOUT an AI query.** Where the content fingerprint matches after
normalization, the cells are provably identical - same label, same expression, same operands,
same citations. A model query there can only introduce a false "changed" on content we know
did not change. Deterministic wins where the deterministic answer is exact. `rollover_candidates`
in `workbench/address_verdicts.py` already does this match; the open change is that John wants
identical cells CARRIED, not returned for per-cell reconfirmation. Thousands of clicks to learn
nothing is how a reviewer disengages.

**Use the AI only on the changed set, with a tunable bar.** Where the fingerprint differs,
a model call judges materiality and returns STRUCTURE, not prose:
`{materiality: none|cosmetic|substantive, reason, recommendation}`. John moves the bar by
editing what counts as which - a changed dollar threshold or a changed operand set is
substantive; rewording, renumbered cross-references, and punctuation are cosmetic. This makes
model volume proportional to CHANGES rather than to the ~2,000-cell inventory: tens to low
hundreds of calls at a year boundary.

**Show old vs new, plus the recommendation.** For any changed cell the reviewer sees both
versions and the AI's read. The AI recommends; it never decides.

**Deletions are explicitly OUT OF SCOPE - John's call, 2026-07-30.** A previously approved
cell with no counterpart in the new year is dropped silently. Rationale: you process the new
form, cells are either approved or not, and a handful of stragglers per form is a trivial
review cost. Do not build a removal bucket.

**UX note, deliberately deferred.** Rollover review is a different and much smaller surface
than first-year review - "here are the 60 things that changed, with a diff and a
recommendation" rather than 2,000 cells in address order. It likely deserves its own focused
view rather than being forced into the three-column river, which exists for exhaustive first
pass. Two modes, one contract underneath. Do not design this until John has used the current
page.

## What it is

A standalone, human-facing visual review tool. A person opens a rendered IRS form
(the actual PDF pages), highlights or clicks a region - a line, a box, a table band -
and the tool shows everything the system believes about that region: the extracted
nodes and rules, the instruction text they came from, the connectors (FEEDS edges in
and out, including cross-form targets), citations with verbatim quotes, trust tier and
which verification layers passed or flagged, open findings and verdict states, and any mined
IRS examples that execute through those nodes.

It is the workbench for every moment M8 routes a human to: the exception queue, the
calibration sample, N-version adjudications, mined-example confirmation, and the
promotion gate. The M8 dashboard metric is "human minutes per promoted object"; this
tool is the main lever on that number.

## Why standalone

The existing `review.html` is generated BY the extraction pipeline, from the
pipeline's own intermediate objects. That is useful but structurally sympathetic: it
renders what the extractor believes, in the extractor's own vocabulary, and can only
show what the pipeline chose to emit. A reviewer looking at it is inside the
extractor's frame.

The workbench takes the opposite stance, and this is the core design commitment:

- It is a SEPARATE effort (own module or own repo - open question below) that does
  not import `tax_graph.extract` internals. It consumes only durable on-disk
  artifacts: the source PDFs, the compiled SQLite graph, draft directories, geometry,
  field dispositions, address-keyed verdicts, `metrics.yaml`, and N-version reports.
- It derives page geometry ITSELF, from the PDF: AcroForm field rects and text-span
  search resolve the pipeline's line/field anchors to pixel regions. The pipeline's
  provenance says "this rule came from source line N / field X"; the workbench
  independently finds where line N and field X actually sit on the page. A dangling
  or unresolvable anchor is itself a finding, displayed as such.
- It starts from the FORM, not from the draft objects. The reviewer's frame is "here
  is the official document; what does the system claim about this spot?" - including
  the honest answer "nothing" (uncovered regions are visible as gaps, which doubles
  as a poor-man's coverage view and complements M7's frontier registry).

## Core interaction (the one primitive)

Highlight-to-inspect. Everything else is a workflow wrapped around it.

The primary navigator is document-first. Each official document shows its pages and
required-unit count, then expands to a deterministic `Things to check` checklist. The
plain-English groups cover identity/filer inputs, mappings/imports, calculations,
decisions, tables/worksheets, citations/witnesses, changes/diffs, and unsupported/gaps;
empty groups are omitted. Queue ids and review kinds remain internal API provenance. A
check group can span several documents, but every projected graph cell appears exactly
once and counts reconcile to the manifest cell inventory; unlocated cells remain
visible as unlocated rather than receiving invented geometry.

Every review unit carries required `display_name`, `official_locator`, and
`review_prompt` fields. Names resolve from authored canonical-address/control metadata;
raw AcroForm names and serialized ids are never display-name fallbacks. Preflight rejects
blank or raw field names. Population-policy prompts distinguish filer input, import, copy,
calculation, decision, intentional blank, and unsupported behavior.

1. Render form pages as images (PyMuPDF at build time, or pdf.js in-browser - open).
2. Overlay low-opacity policy outlines. Persistent labels never cover IRS text.
3. Hover or focus a control to show its derived label outside the page. Click to pin one
   exact field and open its evidence. Empty page space clears hover, not the pin.
4. A side panel shows, for the hit objects: node ids and labels, rule shape and
   parameters, citations (verbatim quote, clickable back to its own page region),
   inbound/outbound edges rendered as a small local subgraph with cross-form targets
   named, trust tier + per-layer check outcomes (L0-L5), any open finding or
   N-version disagreement entries, and mined examples touching the node.
5. Where the reviewer has a pending decision (adjudication, calibration confirm,
   example confirm), the panel offers it inline: pick A / pick B / neither, confirm /
   reject, with a required short reason for anything other than confirm.

The official form owns the main review width. Semantic flow is hidden by default and,
when requested, shows only the selected field. A no-geometry worksheet may expose its
scoped flow on demand. It never recreates a page-height layer of overlapping cards.

## Decisions flow OUT as artifacts, not edits

The workbench never writes the graph, drafts, or derived cell inventory directly. It
emits small append-only, address-keyed verdict files (JSONL, schema'd) that later
promotion workflows can consume - the same pattern as `--confirm` on example mining. This keeps the tool
read-only with respect to everything it displays, which is what makes its stance
trustworthy, and keeps promotion mechanics where they already live.

## Rough shape (v1, all soft)

- Local-only and static-review capable with zero API keys. Consistent with the single-binary ethos:
  either a static HTML bundle generated per form-year (like `review.html` but from
  compiled artifacts) or a tiny local server (`review-workbench serve --year 2025`).
  The normal `serve` entry point is the application host: it injects the pipeline's
  non-persisting single-cell re-derive callback. The artifact-only `workbench.server`
  seam remains usable without that callback and returns 501 for retry requests.
- Input contract = published artifact formats only (SQLite schema, draft dir layout,
  geometry, field disposition, and verdict schemas). Any information the workbench needs that artifacts do
  not carry becomes an ADDITIVE field request on the pipeline side - the workbench
  never reverse-engineers pipeline internals.
- Respects the pinned addressing rules: physical row slots (part_i.line_1.row_01...)
  are display geometry only; runtime instances are <node>#<row_key>; static ids stay
  flat. The workbench displays all three vocabularies and never conflates them.
- ASCII source files, provider-agnostic, no external CDNs.

Try Again is a fresh attempt, not a verdict and not a session save. It sends only the
correction typed for that attempt, then displays the returned expression and validator
failures. If the cell is later rejected, the local defect report and the next workbench
read retain the retry comments and result summaries. Curated ledger comments are used
when no new correction is supplied; contributed comments remain visible history and
are never sent to the model.

## Candidate v1 workflows (pick two, defer the rest)

1. Draft promotion review: walk machine findings + calibration samples for one
   form, spatially, on the form itself.
2. N-version adjudication: side-by-side semantic-core diff anchored to the disputed
   region of the page (the pending Part I/II line-2 totals disagreement is the live
   test case). Two intake severities, per the pinned escalation ladder (AGENT_HANDOFF,
   2026-07-08): BLOCKING items where all families disagreed (no majority - the human
   IS the resolution, all answers shown), and NON-BLOCKING attention flags for 2-1
   majority resolutions (pipeline already proceeded on the majority; the human verdict
   confirms or overrides, and the verdicts double as a complete tiebreaker
   escape-rate measurement).
3. Mined-example confirmation: show the instruction "Example." paragraph in place,
   the facts/expected extracted from it, and the engine result.
4. (Later) Coverage walk: page heatmap of modeled vs frontier vs unclaimed regions.

## Open questions (for when this gets a real plan)

- Home: separate repo vs a workspace member in this repo with an enforced no-import
  boundary. Separate repo is the stronger objectivity statement; workspace member is
  cheaper to keep in sync with artifact schemas.
- Rendering: prebaked page images (simple, heavy) vs pdf.js (live text layer, more
  moving parts).
- Whether the workbench reads the compiled SQLite directly or speaks to the MCP
  server as a client. MCP-client mode is a nice dogfood of the public interface and
  keeps the read seam honest, but adds a process dependency.
- Verdict-file schema and which pipeline commands grow a `--verdicts` intake.
- How much of the current `review.html` survives: probably remains as the pipeline's
  cheap self-report, while the workbench becomes where human GATES happen.

## What this is NOT

- Not an editor. It never mutates graph YAML, drafts, or generated review state.
- Not part of extraction or CI. Pipelines must stay fully runnable without it.
- Not a taxpayer-facing UI. The audience is the maintainer/reviewer (John).
- Not a coverage authority - M7's frontier registry stays canonical; the heatmap is
  a view of it, not a rival.
# Official-form geometry seam

M12 commits `graph/<year>/node_geometry.json`, a schema-validated projection
from field maps and AcroForm inventories. The M15 workbench should use
`tax_graph.output.resolve_node_geometry` to place node review links on the
official form page; repeatable table templates intentionally return every
physical printed row slot.

## Preflight and coverage

Before starting a review server, run:

```text
python -m workbench.cli preflight --year 2025
```

Preflight fails closed when object identity, geometry identity, semantic formatting,
or citation evidence is incomplete or ambiguous. A successful run reports derived
cell coverage by review kind, source document, object type, geometry state, and
explicit expression kind bucket.

During the A9 address-authoring ratchet, legacy geometry-mined labels carry explicit
`legacy_mined` provenance and appear as provisional. Preflight reports their count per
document. Authored address labels are checked immediately for raw AcroForm tokens; the
final A9 gate removes the legacy path and requires a zero count.

Start the local API after preflight succeeds:

```text
python -m workbench.cli serve --year 2025
```

The server binds only to `127.0.0.1`, chooses an available port unless `--port`
is supplied, and prints a per-launch token reserved for write requests. Derived
entry and scoped-entry reads are available at `/api/queue` and
`/api/entries/<queue_id>`.

Official pages are rendered lazily through
`/api/documents/<document_id>/pages/<page>.png`. The cache key pins the source
PDF hash, one-based page, requested scale, and renderer version. Evidence lookup
at `/api/evidence/<object_type>/<object_id>` returns the exact compiled or draft
object plus its geometry, derived-unit references, and citation references.

Resume state is non-authoritative JSON under `.workbench_state/` and is exposed
through `GET/PUT /api/sessions/<queue_id>`. PUT and verdict emission require the
per-launch token in `X-Workbench-Token`. `POST /api/verdicts` validates the human
decision and emits the existing append-only, content-hashed verdict format; it
never applies a verdict or edits graph, derived cells, tier, or provenance artifacts.
When a verdict includes a comment, its optional `origin` is copied to the address
ledger; omitted origin defaults to `contributed` for fail-closed behavior.
