# Review Workbench

> Product reset, 2026-07-13: the current static bundle is infrastructure only and is not
> an accepted human-review surface. The human campaign is paused. The authoritative
> replacement design and implementation sequence are in `plans/PHASE_M15.md`.

Status: M15 Steps 1-3 as-built, 2026-07-13. Canary: "Fresh Eyes". The workbench is a
top-level workspace member with an artifact-only read seam. UI and verdict emission
remain in later M15 steps.

## Scoped queue migration

M15 queue entries carry an additive `review_scope` projection. Each pending entry has a
scope type and explicit object refs with an object type, object id, source artifact path,
and review role. Expected nodes, changed object ids, field-map records, worksheet line
nodes and rules, decision options and citations, intake records, and explicit review.md
bullets are migrated deterministically. An entry that cannot resolve a targeted object
scope fails closed; the migration never falls back to approving an entire document.

Run the migration with:

`tax-graph review migrate-scope --year 2025`

The command is idempotent. Use `--refresh` only when rebuilding existing scopes after a
scope-derivation code change. It updates only the deferred-review queue; it does not
mutate graph objects, drafts, verdicts, or provenance.

## Step 1 artifact contract

`workbench.artifacts` reads the published artifacts directly and never imports a
pipeline module. The compiled SQLite graph is opened in SQLite read-only URI mode;
graph rows are decoded from their public `object_json` columns. The node geometry
projection and deferred review queue are validated against their committed JSON
Schemas. Draft directories expose YAML/JSON as structured data and Markdown/HTML as
text, while metrics, N-version reports, and mined-example reports are indexed by
workspace-relative artifact path. Source PDFs are represented by path, byte size, and
SHA-256 metadata; rasterization belongs to Step 2 and is not a runtime dependency of
the read seam.

`review-workbench inspect --year 2025` is the Step 1 smoke command. It reports the
artifact counts without writing any file. The committed `m15` boundary test walks all
workbench Python files and rejects imports from `tax_graph` and its pipeline modules.

## Step 3 review manifest

`workbench.manifest.build_manifest` projects each pending queue entry and its additive
`review_scope` into one or more concrete review units. Each unit carries exact object
identifiers, a schema-valid structure-only reference expression, official geometry when
the node or field resolves to a published PDF, and an explicit `null` analog placement
until a later step adds semantic layout. The manifest hash is computed from canonical
artifact hashes and unit data, so repeated builds are byte-stable. Build one with:

`python -m workbench.cli manifest --year 2025 --output-dir .workbench_state/2025`

S3 intentionally does not generate English semantic text or infer missing geometry.

## Step 2 artifact view

`workbench.geometry.GeometryIndex` keeps the AcroForm field layer, resolved node
provenance layer, and unresolved identity/gap layer separate. Point and rectangle
selection is performed in PDF page coordinates, so repeated Form 8949 row slots stay
display geometry and never become runtime node ids. `review-workbench build --year
2025` rasterizes source PDFs with the optional PDF extra and writes a static HTML
bundle with no CDN or API dependency. The bundle carries the public graph rows,
citations, queue, metrics, N-version reports, and mined-example reports in an escaped
JSON payload. A node id absent from the compiled graph is rendered as a visible gap
finding rather than being treated as resolved.

## Step 3 verdict contract

The workbench emits only new files under `review_verdicts/<year>/`; it never edits the
queue, graph, or drafts. Each verdict is schema-validated and carries a canonical
content hash, queue id, reviewer id, ISO timestamp, and measured human minutes.
`confirmed`, `pipeline_defect`, and `source_pathology` are the only terminal labels;
the latter requires marked source provenance. The pipeline-owned command
`tax-graph review apply-verdicts` validates the hash and queue reference before
applying a verdict. Confirmed node/document/decision objects receive
`human_confirmed: true`, `verification_tier: human-confirmed`, and the reviewer
record; unsupported artifact kinds remain represented in the audit sidecar. A
pipeline defect is routed back to `pending_reextract`, while source pathology remains
a marked override and does not masquerade as a clean graph confirmation.

## What it is

A standalone, human-facing visual review tool. A person opens a rendered IRS form
(the actual PDF pages), highlights or clicks a region - a line, a box, a table band -
and the tool shows everything the system believes about that region: the extracted
nodes and rules, the instruction text they came from, the connectors (FEEDS edges in
and out, including cross-form targets), citations with verbatim quotes, trust tier and
which verification layers passed or flagged, open review-queue items, and any mined
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
  artifacts: the source PDFs, the compiled SQLite graph, draft directories, the
  review queue, `metrics.yaml`, and N-version reports.
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

1. Render form pages as images (PyMuPDF at build time, or pdf.js in-browser - open).
2. Overlay two independent geometry layers: AcroForm field boxes (from the PDF) and
   resolved provenance anchors (text spans the pipeline cited).
3. Click or drag-select a region. Hit-test against both layers.
4. A side panel shows, for the hit objects: node ids and labels, rule shape and
   parameters, citations (verbatim quote, clickable back to its own page region),
   inbound/outbound edges rendered as a small local subgraph with cross-form targets
   named, trust tier + per-layer check outcomes (L0-L5), any open review-queue or
   N-version disagreement entries, and mined examples touching the node.
5. Where the reviewer has a pending decision (adjudication, calibration confirm,
   example confirm), the panel offers it inline: pick A / pick B / neither, confirm /
   reject, with a required short reason for anything other than confirm.

## Decisions flow OUT as artifacts, not edits

The workbench never writes the graph, drafts, or queue files directly. It emits small
append-only verdict files (YAML, schema'd) that the existing pipeline commands
consume - the same pattern as `--confirm` on example mining. This keeps the tool
read-only with respect to everything it displays, which is what makes its stance
trustworthy, and keeps promotion mechanics where they already live.

## Rough shape (v1, all soft)

- Local-only, offline, zero API keys. Consistent with the single-binary ethos:
  either a static HTML bundle generated per form-year (like `review.html` but from
  compiled artifacts) or a tiny local server (`review-workbench serve --year 2025`).
  Lean static-first; a server only if adjudication write-back demands it.
- Input contract = published artifact formats only (SQLite schema, draft dir layout,
  queue/report YAML schemas). Any information the workbench needs that artifacts do
  not carry becomes an ADDITIVE field request on the pipeline side - the workbench
  never reverse-engineers pipeline internals.
- Respects the pinned addressing rules: physical row slots (part_i.line_1.row_01...)
  are display geometry only; runtime instances are <node>#<row_key>; static ids stay
  flat. The workbench displays all three vocabularies and never conflates them.
- ASCII source files, provider-agnostic, no external CDNs.

## Candidate v1 workflows (pick two, defer the rest)

1. Draft promotion review: walk the exception queue + calibration sample for one
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

- Not an editor. It never mutates graph YAML, drafts, or queues.
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
