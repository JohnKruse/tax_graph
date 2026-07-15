# Phase M15 - Interactive Review Workbench and Human Review Campaign

**Status:** REPLANNED 2026-07-13 (frontend stack + step granularity revised by Architect
for a no-Node machine and weaker-model workers). The human campaign is PAUSED. The
static bundle is not an acceptable review surface and does not satisfy this phase.
As of 2026-07-15, M15R has completed its canonical-address recovery and representative
gates. Preserve A1-A3 and the in-progress A4 work. Resume A4-A7 using canonical
address/control review units; do not reintroduce label, node-id, or PDF-field-name identity
heuristics. M15 remains the human-confirmation campaign.

**Canary:** Fresh Eyes

**Gate:** Pre-ship. M15 is complete only when the interactive workbench is accepted by
John, the deferred-review queue is drained through it, review time and escape rates are
measured, and the resulting verdicts are applied and reverified.

This plan supersedes both the static-first UI direction AND the earlier React/TypeScript/
Vite/npm direction. Git history preserves them; they are not current product guidance.

## 1. Product outcome

The workbench must let a reviewer compare the official IRS artifact to the tax graph's
semantic analog without mentally joining raw JSON, multiple PDFs, and CLI commands. The
primary review gesture is:

1. Look at a line, box, table row, or worksheet step on the official artifact.
2. Look directly across to its aligned semantic analog.
3. Hover either side to highlight the pair.
4. Read, in plain English, where the value comes from and how it is transformed.
5. Inspect citations, graph objects, machine witnesses, and change history only when needed.
6. Record the queue verdict in the same app.

It is a local, interactive desktop-browser application driven by a local Python server.
It is not a long pre-rendered HTML report and does not load every form and instruction
page into one document.

## 2. Why the current surface is rejected

The implemented bundle is useful infrastructure, not a review application: it renders
every acquired PDF (including whole instruction books) into one very long page; its main
interaction is click-rectangle -> raw JSON in a narrow panel; it shows no official/analog
comparison; it explains no input/copy/calculation/lookup/branch/table/frontier semantics
in reviewer language; it matches the queue at document granularity so the reviewer cannot
see exactly what to check; and it has no queue navigation, progress, resume, keyboard
workflow, or integrated verdict entry.

Retained as infrastructure: `workbench/artifacts.py` (artifact loaders), `workbench/
geometry.py` (geometry index), `workbench/render.py` (page rasterization), `workbench/
verdicts.py` (hashed verdict emit), and `tax_graph/review.py` (hardened apply pipeline).
NOT retained: the monolithic bundle output and the raw-JSON-first interaction.

## 3. Pinned reviewer experience

Default desktop layout: a queue rail, two equal review panes, and a bottom detail/verdict
drawer.

```text
+--------------------------------------------------------------------------+
| Queue 8/30 | Form 1040 | Page 1/2 | Back | Next | 06:42 active review    |
+--------------+---------------------------+-------------------------------+
| REVIEW QUEUE | OFFICIAL IRS ARTIFACT     | TAX GRAPH SEMANTIC ANALOG     |
|              |                           |                               |
| Field maps   | [official page image]     | [same-size aligned page]      |
| Promotions   |                           |                               |
| Decisions    | Line 7 -----------hover---| Copied from Schedule 1 line 10|
| Worksheets   | Line 9 -----------hover---| Add lines 1z + 2b + 3b + ...  |
| ...          |                           |                               |
|              | synchronized zoom/scroll  | status, value type, trust     |
+--------------+---------------------------+-------------------------------+
| DETAILS: Formula | Sources | Citation | Witnesses | Diff | Advanced JSON |
+--------------------------------------------------------------------------+
| Confirm | Pipeline defect | Source pathology | Note | Save and next      |
+--------------------------------------------------------------------------+
```

### 3.1 Official artifact pane
- Show only the current form, schedule, worksheet, or cited instruction excerpt.
- Preserve the official page image and field geometry.
- Support synchronized zoom, pan, and page changes with the analog pane.
- Highlight in-scope regions; dim out-of-scope context without hiding it.
- Hover, click, and keyboard focus all select a region.
- Instruction pages load on demand from a citation, never in the initial form view.

### 3.2 Semantic analog pane
Same page dimensions and vertical coordinates as the official page. Not a fake filled PDF;
a readable semantic twin whose cards align with the official lines/boxes. Dense regions may
use collision-free lanes, but a connector must preserve the exact official-to-semantic
pairing. Each visible unit has a concise primary explanation:

| Graph meaning | Primary analog text |
| --- | --- |
| Filer input | `Entered by filer: Wages, salaries, tips` |
| Imported input | `Imported from W-2 box 1` |
| Copy | `Copied from Schedule 1 line 10` |
| Sum | `Add Form 1040 lines 1z + 2b + 3b + ...` |
| Subtract | `Subtract line 15 from line 14` |
| Multiply | `Multiply line 12 by 0.15` with the cited parameter named |
| Lookup | `Look up taxable income in the 2025 tax table` |
| Branch | `If filing status is ..., use ...; otherwise ...` |
| Table row | Show the row template once, the current physical row, and the total rule |
| Frontier | `Not modeled` plus the explicit reason and downstream effect |
| Missing mapping | `Review gap: no official geometry` |

Every operation in the compiled graph needs an explicit formatter. Unknown operations must
FAIL preflight; raw JSON is not a primary-display fallback.

### 3.3 Details and evidence
Clicking a unit pins a drawer with: Formula (fully expanded human-readable transformation
with labeled source lines), Sources (incoming/outgoing edges, source documents, value
origin), Citation (instruction excerpt, locator, hash, on-demand page view), Witnesses
(validation/differential/example/N-version status), Diff (changed values/objects for
promotion or rollover), and Advanced JSON (exact underlying objects, hidden by default).

### 3.4 Queue and verdict workflow
- Group queue entries by review kind and document, with pending/visited/verdict counts.
- `J`/`K` or arrows move between review units; `N`/`P` move between queue entries.
- Reload restores queue entry, page, selection, zoom, notes, and elapsed active time.
- Active time pauses when the tab is hidden or idle and is editable before submission.
- A queue-level confirm is disabled until every required unit has been visited; a defect
  may be submitted before full coverage.
- Verdict choices remain exactly `confirmed`, `pipeline_defect`, `source_pathology`.
  Reason/note requirements follow the verdict schema.
- Verdict submission writes the existing hashed verdict file through the local server. It
  NEVER mutates graph objects, queue entries, trust tiers, or provenance.
- Applying verdicts and reverifying stay separate, explicit pipeline actions. The app may
  display or copy the command; it does not silently apply a verdict.

## 4. Review-unit contract

Document-level matching is too broad. Add a deterministic, schema-validated review manifest
generated from compiled artifacts and the queue: one `review_entry` per queue item and one
or more concrete `review_unit` objects. Each unit includes: stable queue id, unit id, review
kind, required/optional status; exact object ids (node/rule/edge/decision/citation/field/
table/worksheet-row/example as applicable); official location (document id, source PDF hash,
page, normalized rect, locator text when available); analog placement (page, anchor rect,
lane, display order); semantic class (input/imported/copy/calculation/lookup/branch/
repeatable-table/parameter/frontier/review-gap); human-readable summary + structured
expression tree; source/target refs with display labels; citation/witness/confidence/trust/
N-version/promotion-diff references; coverage-state requirements for the final verdict.

The manifest is a projection of authoritative artifacts, never a second tax model. Its
expression tree is generated from rules and role-bearing edges. A manifest hash pins the
review session and verdict to the exact reviewed projection.

Preflight must fail when: a pending entry resolves to zero units; a required object or
geometry reference is ambiguous; a semantic operation lacks a formatter; a promotion review
cannot identify the changed object set; a field-map review omits mapped/excluded/frontier/
unresolved fields; or a citation cannot resolve to an artifact and locator. Where the queue
lacks object scope, add an additive `review_scope` field and a deterministic migration
command; never infer a broad document-wide approval from a document id alone.

## 5. Architecture pins

### 5.1 Stack (revised - no Node, weaker-model friendly)
- **Backend:** Python, isolated in `workbench/`, using an optional `[workbench]` extra
  (Flask for the local server). Serves a JSON API + static frontend assets. The workbench
  must NOT import `tax_graph` in-process - it consumes only public artifacts and schemas
  (the enforced no-`tax_graph`-import boundary test stays).
- **Frontend:** plain HTML + CSS + vanilla ES-module JavaScript, served as static files by
  the backend. NO build step, NO bundler, NO Node/npm, NO external CDN. Keep it as a few
  small, clearly-named modules (e.g. `api.js`, `panes.js`, `pairing.js`, `drawer.js`,
  `queue.js`, `keyboard.js`) rather than one giant file. A single vendored no-build helper
  is permitted only if a step genuinely needs it and it is committed locally.
- **E2E tests:** Python Playwright (`pytest-playwright`, in a `[workbench-dev]` extra;
  `playwright install chromium` once). Drives the local Flask server. No Node.
- **Base runtime unchanged:** the base `tax_graph` runtime imports none of Flask,
  Playwright, or workbench modules. Base-deps stay light.
- Command surface: `python -m workbench.cli serve|preflight ...` (console alias
  `review-workbench`).

### 5.2 API boundary
Minimum local endpoints: `GET /api/queue` (grouped entries + progress); `GET /api/entries/
{queue_id}` (scoped units + evidence refs); `GET /api/documents/{document_id}/pages/{page}
.png` (lazy render/cache); `GET /api/evidence/{object_type}/{object_id}` (details + raw
object); `GET/PUT /api/sessions/{queue_id}` (non-authoritative resume state + notes);
`POST /api/verdicts` (validate + emit a hashed verdict file). There is NO endpoint that
applies verdicts or edits the live graph.

### 5.3 Server, performance, storage
- Bind only to `127.0.0.1`, choose an available port, use a per-launch session token for
  write requests.
- Render/transfer only the current page plus one-page prefetch per side. Cache page PNGs by
  source PDF hash, page, scale, and renderer version.
- Do NOT generate a single HTML file containing embedded images or every PDF page.
- Targets: initial cached view under 2s locally and under 5 MB transferred; page switch
  after cache under 300 ms; hover pairing under 100 ms.
- Session drafts + the generated manifest live in a gitignored workbench state directory.
  Verdict files keep their existing authoritative location and schema.

## 6. Implementation steps

**Worker rules (read first, especially Luna):** one step = one commit. A step is `[DONE]`
only when its own tests AND `python -m pytest -m m15 -q` pass and it is pushed with green
CI. Do NOT start the next step until the previous is green and pushed. STOP at each JOHN
gate. NEVER write `human_confirmed: true` from any code path except the reviewed
verdict-application pipeline. Full suite green is the commit floor (the Architect re-runs
the full suite and verifies before/at push). ASCII only (the pre-push hook enforces it);
hermetic tests; drafts never committed.

**Environment prep (one-time, not a commit):** add the `[workbench]` (Flask) and
`[workbench-dev]` (pytest-playwright) extras to `pyproject.toml`; `uv sync --extra
workbench --extra workbench-dev`; `uv run playwright install chromium`. This may be its own
tiny first commit (pyproject + a README note) if the worker prefers.

### Group A - Review manifest + semantics (backend, artifact-only Python)

- **S1 - Schemas.** Add `review_manifest`, `review_unit`, `review_expression`,
  `session_state` JSON schemas under `schemas/` + a validation helper. Test: schema-load
  + minimal valid/invalid fixtures pass. `pytest tests/test_review_schemas_m15.py -q`.
- **S2 - Queue `review_scope`.** Add an additive `review_scope` field to the deferred-review
  queue schema + a deterministic migration command that backfills object scope for the
  current pending entries (never a document-wide default). Test: migration is idempotent;
  `validate 2025` green. `pytest tests/test_review_scope_migration_m15.py -q`.
- **S3 - Manifest builder (structure only).** `workbench/manifest.py` projects each pending
  queue entry into >=1 `review_unit` with object ids, official geometry, analog placeholder,
  and semantic class - NO English text yet. Test: every pending 2025 entry -> >=1 unit; hash
  is stable. `pytest tests/test_review_manifest_m15.py -q`.
- **S4 - Simple formatters.** English + structured expression tree for COPY, SUM, SUBTRACT,
  NEGATE. Golden tests for `Add lines 1z + 2b + 3b`, `Subtract line 15 from line 14`,
  `Copied from Schedule 1 line 10`. `pytest tests/test_review_semantics_m15.py -q`.
- **S5 - Remaining formatters.** LOOKUP_TABLE, LOOKUP_BRACKET, MAX, MIN, MULTIPLY (name the
  cited parameter), IF_ELSE (branch English), plus repeatable-table, frontier, and input/
  imported classes. Unknown op -> raises (caught by preflight), never raw JSON. Golden tests.
- **S6 - Preflight + coverage. [DONE]** `python -m workbench.cli preflight --year 2025` fails on
  every Section 4 condition; emits a coverage report by kind/document/object/geometry. Test:
  a seeded bad fixture fails with an actionable message; the real 2025 queue passes.
  `pytest tests/test_review_preflight_m15.py -q && python -m workbench.cli preflight --year 2025`.

### Group B - Local server + read/write API (Python/Flask, no mutation)

- **S7 - Server skeleton + read APIs. [DONE]** Flask app in `workbench/`, `127.0.0.1` + ephemeral
  port + per-launch write token; `GET /api/queue`, `GET /api/entries/{queue_id}`; `python -m
  workbench.cli serve`. Test (Flask test client): grouped queue + scoped units returned.
  `pytest tests/test_workbench_server_m15.py -q`.
- **S8 - Page + evidence APIs. [DONE]** `GET /api/documents/{doc}/pages/{page}.png` (lazy render,
  cache by pdf-hash/page/scale/renderer-version) + `GET /api/evidence/{type}/{id}`. Test:
  only the requested page renders; cache hit on repeat.
- **S9 - Session + verdict APIs. [DONE]** `GET/PUT /api/sessions/{queue_id}` (non-authoritative) +
  `POST /api/verdicts` (validate + emit the existing hashed verdict via `workbench/verdicts
  .py`). Tests: no endpoint mutates graph/queue/tier/provenance; tampered/duplicate verdict
  rejected; missing write token rejected.

### Group C - Paired-view vertical slice (vanilla JS, no build)

- **S10 - Static shell.** `index.html` + ES-module JS served by Flask; loads `/api/queue`
  into the queue rail; empty official/analog panes + drawer region. Playwright test: page
  loads, queue is populated. `pytest tests/e2e/test_shell_m15.py -q`.
- **S11 - Official pane.** Lazy current-page image + geometry rects for the current unit;
  in-scope highlighted, out-of-scope dimmed. Playwright: correct page/region shown.
- **S12 - Analog pane.** Aligned semantic cards (primary English text) at the same page
  height/coordinates, with a connector to the official region. Playwright: pair is visibly
  linked.
- **S13 - Hover/click pairing (the core gesture).** Hovering either side highlights the
  exact pair; clicking pins selection. Playwright on a 1040 unit; assert both directions.
- **S14 - Evidence drawer.** Tabs Formula/Sources/Citation/Witnesses/Diff/Advanced-JSON,
  JSON hidden by default. Playwright: clicking a unit pins the drawer with real content.
- **S15 - Keyboard + synchronized scroll/zoom.** `J`/`K` units, `N`/`P` entries; panes
  scroll/zoom/page in lockstep; focus management. Playwright.
- **S16 - Three representative cases + e2e.** Wire (1) Form 1040 input/copy/calc/lookup/
  branch, (2) Form 8949 repeatable row-template + total, (3) Schedule D worksheet or its
  N-version unit. Verdict controls visibly DISABLED and labeled not-yet-wired. Python
  Playwright e2e "paired view" at 1280x800 and 1920x1080.

### JOHN UX GATE A - accept the review model before breadth work
John reviews the three cases live. The Worker STOPS and records exact feedback in
`plans/AGENT_HANDOFF.md`. Continue only after John confirms the official/analog comparison,
explanations, navigation, and evidence hierarchy match the intended workflow. UX
corrections land in a follow-up commit before the gate is marked passed.

**Gate A result (John, 2026-07-14): NOT ACCEPTED.** S17 and later work remains blocked.
The vertical slice proved the artifact/API seam, but not the review model. The repeated
queue-level `Review authored AcroForm...` labels obscure the official IRS text and provide
no field-specific information. The semantic-analog cards overlap, remain unreadable even on
a wide display, and do not earn half of the primary workspace. John prefers the official form
as the primary surface: unobtrusive colored field outlines, click a field, then inspect the
specific semantic detail below. The review also exposed a coverage-integrity problem: every
fillable AcroForm field needs an explicit population policy even if it is merely user-entered
or unsupported. Form 1040 lines 1b-1h are modeled but omitted from the PDF mapping; dependent
identity and eligibility fields are physically inventoried but dependent computation is outside
the current supported profile. Those are different states and must never look like the same
undefined cell. Document-level `independently witnessed` language must not imply whole-form
coverage when the witness corpus fixes dependents at zero and the Verification Record is partial.

### Gate A supplemental correction plan - complete fields + click-to-inspect

This is an in-phase correction sequence, not Group D breadth. One item = one commit with focused
tests, `pytest -m m15`, ASCII, and the full-suite floor. The Worker stops after A7 and reopens the
live Gate A review. Iterate A1-A7 as needed until John explicitly accepts the gate. Do not start
S17 while Gate A is open.

#### Correction invariants

1. **Every fillable/checkable field has exactly one disposition.** All text inputs, checkboxes,
   radio controls, choice controls, and repeatable physical slots on every official form/schedule
   exposed by the workbench are in scope. An official PDF with AcroForm widgets but no inventory
   and field map is a preflight failure. Every inventoried control resolves to one of
   `user_entered`, `imported`, `copied`, `computed`, `decision_required`,
   `intentionally_blank`, or `unsupported`. There is no `undefined`, document-wide default, or
   silent omission.
2. **Mapped is not the same as modeled.** A physical PDF field can be fully identified and
   fillable even when downstream tax logic is unsupported. Conversely, a modeled graph node
   omitted from the PDF map is a pipeline defect, not a frontier.
3. **Unsupported is specific and actionable.** `intentionally_blank` and `unsupported` require
   a reason, downstream consequence, and the capability needed to close the gap. They never
   become guessed zeroes or generic review text.
4. **Repeatable filer facts stay structured.** Dependent identity rows are runtime fact instances,
   not static graph-node copies and not physical-row ids. Printed row slots are output geometry.
   Eligibility/credit boxes require an explicit filer decision or modeled qualification rule;
   the system never infers them from identity data alone.
5. **Witness claims are scope-qualified.** A document can be partial and have an independently
   witnessed subgraph. UI badges state the witnessed output/domain and named exclusions; they do
   not promote a partial form to whole-form confidence.
6. **The official artifact is primary.** No persistent text may cover IRS labels or entry boxes.
   The default view is the official page plus field outlines and a selection-driven evidence
   drawer. A semantic flow view is optional and on demand for worksheets or calculations only.
7. **Every control is reviewable.** Graph-backed, runtime-fact-only, decision-required,
   intentionally blank, and unsupported controls have distinct visual states with a legend and
   non-color-only markers. Clicking any state shows its exact policy. Graph-backed controls show
   rules plus upstream/downstream dependencies; controls without a rule say why and show any
   downstream blocker instead of presenting an empty panel.

#### A1 - Complete field-disposition contract

- Extend `field_map.schema.json` with a schema-versioned, additive `field_dispositions` array.
  Each item pins the exact `field_name`, derived human label, `population_policy`, value format,
  and optional node/identity/runtime-fact/source refs. Repeatable members carry group, row-slot,
  column, and role metadata. Blank/unsupported items require `reason`, `downstream_effect`, and
  `missing_capability`.
- Strengthen `validate_field_maps`: inventory field names and disposition field names must be
  equal sets; no duplicate or unclassified field; current `mappings`, `frontier_fields`, and
  `excluded_nodes` must agree with dispositions; modeled printable nodes cannot be excluded with
  a generic output-profile reason when a matching field exists.
- Enumerate AcroForm widgets directly from every official form/schedule PDF exposed by the
  workbench. A PDF with widgets but no committed inventory/map, or an inventory whose widget set
  differs from the PDF, fails preflight. Instruction PDFs with no widgets are explicitly exempt.
- Add a deterministic migration command that copies only provable facts from existing authored
  maps. Current mappings and frontier fields may migrate mechanically; all remaining fields fail
  closed into an authored-work list, never a guessed classification.
- Tests: valid complete fixture; missing/duplicate/unknown field failures; invalid policy/ref
  combinations; unsupported-without-consequence failure; idempotent migration.
- Acceptance: `tax-graph validate 2025` fails until every exposed fillable/checkable official PDF
  has an exact inventory and every control is fully disposed, and passes only when the widget =
  inventory = disposition equality invariant is real.

#### A2 - Universal disposition sweep + Form 1040 1b-1h repair

- Author every disposition for every current official form/schedule exposed by the workbench,
  including identity, filing-status, dependent, income, tax, signature, preparer, checkbox,
  repeatable, and intentionally unused controls. Generate inventories/maps for exposed fillable
  PDFs that currently lack them. Split work internally by document, but A2 is not complete while
  any exposed control remains unclassified.
- Repair the line-anchor normalization that reduced `1b`-`1h` to bare letters. Map the already
  modeled 1b-1h nodes to the exact official fields, preserve line 1h's description + amount pair,
  and prove line 1z still sums 1a-1h.
- Replace every generic exclusion such as `not mapped in the supported output profile` with the
  actual population policy or a specific unsupported boundary.
- Tests: exact golden mappings for 1a-1h/1z; per-document widget/inventory/disposition set equality;
  filled-PDF echo for nonzero 1b-1h; no field label/address collision; a seeded missing text field,
  checkbox, radio control, and entirely missing form inventory each fail preflight.
- Acceptance: clicking any fillable/checkable control on any exposed official form/schedule can
  identify what it is and how it is populated, even when the answer is `unsupported`.

#### A3 - Repeatable dependent facts and honest output behavior

- Add a repeatable `dependents` runtime fact group for filer-entered first name, last name, SSN,
  and relationship. Instance keys remain separate from printed row slots, following the existing
  static/runtime namespace rule.
- Map printed dependent identity cells to row slots without treating them as static tax nodes.
  Map credit/eligibility checkboxes as `decision_required` until a cited qualification branch is
  modeled or the filer explicitly resolves them with provenance.
- Fill 0-4 printed dependent rows deterministically. More rows must produce an explicit attachment
  requirement/unsupported output, never truncation. This step does not claim dependent credits or
  filing-status qualification logic.
- Surface the existing intake universal gate and downstream unsupported consequences in the Return
  Record and workbench field detail.
- Tests: zero, one, and four dependents; five dependents fails closed with attachment guidance;
  identity facts never auto-select a credit box; no `human_confirmed` mutation.

#### A4 - Official-form-first interaction

- Key selection, markers, geometry, and details by canonical `address_id`; the widget
  binding supplies physical placement and never becomes semantic identity.
- Remove the semantic analog from the default two-pane layout and give the official page the main
  review width. Retain queue navigation and synchronized page/zoom controls.
- Delete persistent overlay text and the repeated queue summary from field rectangles. Show only
  low-opacity policy-colored outlines/fills with a compact non-color-only marker; preserve readable
  IRS text. The legend distinguishes graph-backed fields, runtime filer facts, decisions,
  intentionally blank controls, and unsupported controls. Color never implies that a runtime fact
  or unsupported field is a modeled graph computation.
- Hover/focus reveals a short derived field label without obscuring adjacent fields. Click pins one
  exact field and scrolls/focuses its detail drawer. Clicking empty form space clears transient
  hover but not an intentional pinned selection.
- Provide an optional `Semantic flow` action only when the selected unit has a useful worksheet or
  multi-step expression. It is selected-only/on-demand, never a page full of overlapping cards.
- Playwright acceptance at 1280x800 and 1920x1080: official labels remain readable; no overlay text
  intersects an IRS field label; every visible marker is keyboard reachable; no horizontal page
  overflow at reset zoom.

#### A5 - Field-specific detail drawer

- Treat the selected canonical address as the unit identity. Node ids and field names are
  bindings shown only as advanced provenance.
- Replace queue-summary-first content with the selected field's derived IRS label, locator,
  population policy, value origin, format, graph/runtime fact ref, and exact write behavior.
- For computed/copied/imported fields, show the plain-English operation and labeled sources. For
  user-entered fields, show the expected fact and validation. For decision-required fields, show
  options, citation, and escape hatch. For unsupported fields, lead with the missing capability
  and downstream consequence.
- Graph-backed controls list their direct upstream dependencies and downstream consumers. Controls
  without a computation rule explicitly say `No computation rule - <policy>` and still show the
  runtime fact, decision, blanking rule, or unsupported blocker that governs them.
- Keep Formula, Sources, Citation, Witnesses, Diff, and Advanced JSON as progressive evidence, but
  hide tabs that have no relevant content rather than filling them with generic prose.
- Tests: representative 1a user input, 1b repaired mapping, 1z calculation, dependent identity,
  dependent eligibility decision, and an unsupported field all show distinct truthful details.

#### A6 - Coverage and witness-scope honesty

- Reconcile address, widget-disposition, and review-unit counts before displaying coverage.
- Add field coverage counts by population policy to preflight, queue API, and entry header. The sum
  must equal the inventory count. Show modeled, fillable-only, decision-required, intentionally
  blank, and unsupported counts separately.
- Replace broad form-level trust display with scoped language from published artifacts: Verification
  Record status, witnessed outputs/domain, scenario count, fixed assumptions, explicit gaps, and
  pending human review. For the current OTS corpus, disclose that dependents are fixed at zero.
- A field never inherits `independently witnessed` merely because another subgraph in its document
  has that tier.
- Tests: partial Form 1040 cannot render as whole-form witnessed; 1b-1h inherit only their actual
  graph evidence; dependent fields show no OTS coverage; coverage counts reconcile exactly.

#### A7 - Gate A replay + regression pack

- Traverse canonical address units and assert each selected marker resolves to exactly one
  widget disposition and truthful detail unit.
- Rebuild the three Gate A cases around the corrected interaction: Form 1040 field-disposition
  sweep, Form 8949 repeatable table/total selection, and Schedule D worksheet selected-only flow.
- Add a traversal test for every exposed official form/schedule. It clicks every text field,
  checkbox, radio control, choice control, and repeatable slot and asserts a nonempty derived label,
  exactly one population policy, and either graph rules/dependencies or an explicit truthful
  no-rule explanation. Add screenshot assertions/visual goldens for the dense Form 1040
  filing-status/dependents area and lines 1a-1h at both target viewports.
- Run: focused A1-A7 tests; `python -m pytest tests/e2e -q`; `python -m pytest -m m15 -q`;
  full `pytest`; ASCII; real preflight; `tax-graph validate 2025`; filled-form echo checks.
- Launch the local workbench with no verdict writes enabled, stop, and hand the visible surface to
  John. Record exact feedback in `AGENT_HANDOFF.md`. Gate A remains open until John explicitly says
  it passes; further corrections amend A1-A7 before S17 begins.

### Group D - Breadth (navigation, coverage, density)

- **S17 - Queue navigation + exact resume.** Grouped nav, filtering, progress, visited
  state; reload restores queue entry/page/selection/zoom/notes/active-time exactly.
- **S18 - In-context citations + collision lanes.** Lazy instruction-citation viewing
  without leaving the current review context; collision-free lanes + connectors for dense
  official forms.
- **S19 - Visual states + delta.** Explicit states for pending/selected/visited/confirmed/
  defect/frontier/review-gap (never color-only) + keyboard help; changed-only highlighting
  with unchanged context for promotion/delta entries. No raw JSON in the primary UI.

### Group E - Per-kind adapters (one small commit each)

- **S20 - Field-map adapter.** Every mapped/excluded/frontier/unresolved field is a unit.
- **S21 - Promotion adapter.** Changed objects by default; full graph context on demand.
- **S22 - Decision adapter.** Options, rationale, citations, selected branch, escape hatch.
- **S23 - Worksheet + repeatable-table adapter.** Template, physical-row example,
  aggregation, output line.
- **S24 - N-version adapter.** Candidate agreement/disagreement + selected result.
- **S25 - Intake/extension/examples/contract views.** Purpose-built structured views, no
  forced page geometry when there is no official counterpart. Any unsupported kind FAILS
  preflight rather than falling back to raw JSON.
  Group E acceptance: every current pending entry opens in a purpose-built view; full queue
  traversal has no dead links, empty views, or document-only approvals.

### Group F - Verdict wiring, timing, integrity, rehearsal

- **S26 - Sessions + active timing + verdict emission end to end.** Persist notes/coverage/
  timer/selection; pause timing on hidden/idle, editable before submit; enforce coverage +
  reason in UI AND backend; emit via `POST /api/verdicts`; show verdict path/hash + the
  explicit apply/reverify command. Acceptance: a full entry is reviewable and verdicted with
  no CLI; reload cannot lose a submitted verdict or silently submit a draft; a confirm
  cannot be submitted with unvisited required units.
- **S27 - Integrity cleanup.** Remove or hard-disable every remaining soft path that can
  write `human_confirmed` outside the reviewed verdict-application pipeline, including
  `mine-examples --confirm`. Boundary + no-mutation tests remain green.
- **S28 - Rehearsal instrumentation + docs.** Metrics export (active minutes, navigation
  errors, review gaps, defect-submission flow, notes) from REAL session/verdict data; a
  10-entry rehearsal harness spanning field-map/promotion/decision/worksheet-or-table/
  N-version/product-contract; graduate `docs/review-workbench.md` from stub to as-built with
  reviewer help.

### JOHN UX GATE B - approve campaign readiness
John reviews rehearsal results and personally completes at least one simple entry and one
complex worksheet/table entry. Continue only when John says the workflow is fit for the full
campaign. Record the decision + any residual low-severity issues in the handoff.

### Group G - Campaign + close

- **S29 - [JOHN] Full human review campaign.** Every pending entry gets exactly one explicit
  verdict; pipeline defects fixed/re-extracted/reverified/re-reviewed; source pathologies
  use only marked manual-override paths with human provenance; verdicts applied atomically +
  full reverify; campaign metrics exported by queue kind and complexity. NOT
  worker-completable - the worker only assists/instruments.
- **S30 - Close M15 (worker-light).** Run the exit criteria; regenerate records byte-stable
  (frontier first); write the ship-readiness ledger; update engineering + review-workbench
  docs with final commands + metrics; mark `[COMPLETE]`, archive, prune the handoff, single
  push, confirm CI green, report.

## 7. Exit criteria

All must pass 100 percent (real commands on this repo/machine):

```powershell
python tools\check_ascii.py
python -m pytest -m m15 -q
python -m pytest -q
python -m workbench.cli preflight --year 2025
python -m pytest tests\e2e -q
python -m tax_graph.cli validate 2025
python -m tax_graph.cli frontier build
python -m tax_graph.cli verify record
python -m tax_graph.cli review apply-verdicts --year 2025
```
(Build to a throwaway root when a build is needed - the shared `build/tax_graph_2025.sqlite`
is held open whenever a dev MCP server is connected; see the hermetic rule in the handoff.)

Plus these product conditions:
- John has passed BOTH UX gates.
- The full queue was reviewed in the interactive official/analog workflow.
- No current queue kind relies on raw JSON as its primary view.
- No pending item remains and no `human_confirmed` claim was written by an agent.
- Real active review minutes and escape rates were measured and reported.
- The base runtime stays light; provider agnosticism unchanged; ship-readiness ledger
  reconciles the carried-forward gaps (PolicyEngine witness; parameter-diff HoH floor).

## 8. Out of scope
- Editing graph rules or citations directly in the review app.
- Automatically applying verdicts from the browser.
- Remote multi-user hosting, accounts, or cloud sync.
- Replacing official IRS artifacts with a custom form renderer.
- Using the review projection as an execution engine or tax-calculation source.
- Mobile review. The target is a desktop monitor wide enough for paired panes.
- A Node/npm/React/Vite toolchain (deliberately excluded; see 5.1).
