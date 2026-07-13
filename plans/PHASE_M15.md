# Phase M15 - Interactive Review Workbench and Human Review Campaign

**Status:** REPLANNED 2026-07-13. The human campaign is PAUSED. The static bundle is
not an acceptable review surface and does not satisfy this phase.

**Canary:** Fresh Eyes

**Gate:** Pre-ship. M15 is complete only when the interactive workbench is accepted by
John, the deferred-review queue is drained through it, review time and escape rates are
measured, and the resulting verdicts are applied and reverified.

This plan supersedes the static-first UI direction previously recorded for M15. Git
history preserves that direction; it must not be used as current product guidance.

## 1. Product outcome

The workbench must let a reviewer compare the official IRS artifact to the tax graph's
semantic analog without mentally joining raw JSON, multiple PDFs, and CLI commands.
The primary review gesture is:

1. Look at a line, box, table row, or worksheet step on the official artifact.
2. Look directly across to its aligned semantic analog.
3. Hover either side to highlight the pair.
4. Read, in plain English, where the value comes from and how it is transformed.
5. Inspect citations, graph objects, machine witnesses, and change history only when
   needed.
6. Record the queue verdict in the same app.

The workbench is a local, interactive desktop-browser application. It is not a long
pre-rendered HTML report and it does not load every form and instruction page into one
document.

## 2. Why the current surface is rejected

The implemented bundle is useful infrastructure, not a review application:

- It renders every acquired PDF, including entire instruction books, into one very long
  page.
- Its main interaction is click rectangle -> raw JSON in a narrow side panel.
- It does not show an official-form/semantic-analog comparison.
- It does not explain input, copy, calculation, lookup, branch, table, or frontier
  semantics in reviewer language.
- It matches queue entries at document granularity, so the reviewer cannot see exactly
  what must be checked.
- It has no queue navigation, progress, resume state, keyboard workflow, or integrated
  verdict entry.
- It exposes data already present in the bundle but does not turn rules, edges,
  citations, decisions, examples, or witnesses into a usable review flow.

`workbench/artifacts.py`, `workbench/geometry.py`, `workbench/render.py`, and
`workbench/verdicts.py` are retained where useful. The current monolithic output and
raw-JSON-first interaction are not retained as the product design.

## 3. Pinned reviewer experience

The default desktop layout is a queue rail plus two equal review panes and a bottom
detail/verdict drawer:

```text
+--------------------------------------------------------------------------+
| Queue 8/30 | Form 1040 | Page 1/2 | Back | Next | 06:42 active review    |
+--------------+---------------------------+-------------------------------+
| REVIEW QUEUE | OFFICIAL IRS ARTIFACT     | TAX GRAPH SEMANTIC ANALOG     |
|              |                           |                               |
| Field maps   | [official page image]     | [same-size aligned page]      |
| Promotions   |                           |                               |
| Decisions    | Line 7 ------------hover--| Copied from Schedule 1 line 10|
| Worksheets   | Line 9 ------------hover--| Add lines 1z + 2b + 3b + ...  |
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
- Highlight in-scope regions. Dim out-of-scope context without hiding it.
- Hover, click, and keyboard focus must all select a region.
- Instruction pages load on demand from a citation, never as part of the initial form
  view.

### 3.2 Semantic analog pane

The analog uses the same page dimensions and vertical coordinates as the official page.
It is not a fake filled PDF. It is a readable semantic twin whose cards align with the
official lines and boxes. Dense regions may use collision-free lanes, but a connector
must preserve the exact official-to-semantic pairing.

Each visible unit has a concise primary explanation:

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

Every operation in the compiled graph needs an explicit formatter. Unknown operations
must fail review-manifest preflight; raw JSON is not a primary-display fallback.

### 3.3 Details and evidence

Clicking a unit pins a drawer with these tabs:

- Formula: fully expanded human-readable transformation with labeled source lines.
- Sources: incoming and outgoing edges, source documents, and value origin.
- Citation: instruction excerpt, locator, hash, and an on-demand page view.
- Witnesses: validation, differential, example, and N-version status.
- Diff: changed values and objects for promotion or rollover review.
- Advanced JSON: exact underlying objects, hidden by default.

### 3.4 Queue and verdict workflow

- Group queue entries by review kind and document, with pending/visited/verdict counts.
- `J`/`K` or arrow keys move between review units; `N`/`P` move between queue entries.
- Reload restores queue entry, page, selection, zoom, notes, and elapsed active time.
- Active time pauses when the tab is hidden or idle and is editable before submission.
- A queue-level confirm is disabled until every required unit has been visited. A reviewer
  can submit a defect before full coverage.
- Verdict choices remain exactly `confirmed`, `pipeline_defect`, and
  `source_pathology`. Reason and note requirements follow the verdict schema.
- Verdict submission writes the existing hashed verdict file through the local server.
  It never mutates graph objects, queue entries, trust tiers, or provenance.
- Applying verdicts and reverifying remain separate, explicit pipeline actions. The app
  may display or copy the command, but it does not silently apply a verdict.

## 4. Review-unit contract

Document-level matching is too broad. Add a deterministic, schema-validated
`review-manifest.json` generated from compiled artifacts and the queue. It contains one
`review_entry` per queue item and one or more concrete `review_unit` objects.

Each review unit includes:

- Stable queue ID, unit ID, review kind, and required/optional status.
- Exact object IDs: node, rule, edge, decision, citation, field, table, worksheet row, or
  example as applicable.
- Official location: document ID, source PDF hash, page, normalized rectangle, and
  locator text when available.
- Analog placement: page, anchor rectangle, lane, and display order.
- Semantic class: input, imported, copy, calculation, lookup, branch, repeatable table,
  parameter, frontier, or review gap.
- Human-readable summary and structured expression tree.
- Source and target references with display labels.
- Citation, witness, confidence, trust, N-version, and promotion-diff references.
- Coverage state requirements for the final verdict.

The manifest is a projection of authoritative artifacts, never a second tax model. Its
expression tree is generated from rules and role-bearing edges. A manifest hash pins the
review session and verdict to the exact reviewed projection.

Queue preflight must fail when:

- A pending entry resolves to zero units.
- A required object or geometry reference is ambiguous.
- A semantic operation lacks a formatter.
- A promotion review cannot identify the changed object set.
- A field-map review omits mapped, excluded, frontier, or unresolved fields.
- A citation cannot resolve to an artifact and locator.

Where the current queue lacks object scope, add an additive `review_scope` field and a
deterministic migration command. Never infer a broad document-wide approval from a
document ID alone.

## 5. Architecture pins

### 5.1 Local application

- Command: `review-workbench serve --year 2025 [--queue-id ID] [--no-open]`.
- Bind only to `127.0.0.1`, choose an available port, and use a per-launch session token
  for write requests.
- Backend: Python, isolated in `workbench/`, using optional workbench dependencies only.
- Frontend: React + TypeScript built by Vite into local bundled assets. No CDN and no
  network requirement at review time.
- The base `tax_graph` runtime must not import workbench, rendering, server, or frontend
  dependencies.
- The workbench must not import `tax_graph` in-process. It consumes only public artifacts
  and schemas.

### 5.2 API boundary

Minimum local endpoints:

- `GET /api/queue` - grouped entries and progress.
- `GET /api/entries/{queue_id}` - scoped review units and evidence references.
- `GET /api/documents/{document_id}/pages/{page}.png` - lazy page rendering/cache.
- `GET /api/evidence/{object_type}/{object_id}` - details and raw object.
- `GET/PUT /api/sessions/{queue_id}` - non-authoritative resume state and notes.
- `POST /api/verdicts` - validate and emit a hashed verdict file.

There is no endpoint that applies verdicts or edits the live graph.

### 5.3 Performance and storage

- Render and transfer only the current page plus one-page prefetch on each side.
- Cache page PNGs by source PDF hash, page, scale, and renderer version.
- Do not generate a single HTML file containing embedded images or every PDF page.
- Initial cached view target: under 2 seconds locally and under 5 MB transferred.
- Page switch target after cache: under 300 ms.
- Hover pairing target: under 100 ms.
- Session drafts live in a gitignored workbench state directory. Verdict files retain
  their existing authoritative location and schema.

### 5.4 Test strategy

- Python unit tests for manifest projection, expression formatting, preflight, page
  service, session state, and verdict API.
- Contract fixtures for every rule operation and every queue kind.
- TypeScript component tests for paired selection, keyboard navigation, queue state,
  coverage gating, and verdict validation.
- Playwright end-to-end tests at 1280x800 and 1920x1080 for the representative cases.
- Screenshot assertions for aligned panes and collision handling.
- Boundary tests proving no `tax_graph` import and no graph/queue mutation.
- Existing M15 verdict tamper, duplicate, stale, rollback, and reverify tests remain.

## 6. Implementation steps

Each step is one commit. Core logic, tests, docstrings/docs, and 100 percent passing
step tests are required before `[DONE]`. Do not begin the human campaign before both
John gates pass.

### Step 1 - Build the scoped review manifest and semantic formatter

**Deliverables**

- Add schemas for review manifests, units, structured expressions, and session state.
- Build the manifest from current artifact loaders, queue entries, compiled SQLite,
  geometry, citations, decisions, witnesses, and promotion diffs.
- Add explicit human-readable formatters for every current rule operation: COPY, SUM,
  SUBTRACT, LOOKUP_TABLE, LOOKUP_BRACKET, NEGATE, MAX, MIN, MULTIPLY, and IF_ELSE.
- Add queue `review_scope` migration/backfill for all current pending entries.
- Add `review-workbench preflight --year 2025` with actionable failures.
- Produce a coverage report by queue kind, document, object type, and geometry status.

**Acceptance**

- Every pending 2025 queue entry resolves to at least one concrete unit.
- Every required unit is represented or explicitly marked as a review gap.
- No primary semantic summary contains raw IDs where a document/line label exists.
- Golden tests render representative examples such as `Add line 12 + line 15b`, copy,
  lookup, branch, repeatable table, and frontier text.

**Tests**

```powershell
python -m pytest tests/test_review_manifest.py tests/test_review_semantics.py -q
python -m workbench.cli preflight --year 2025
python tools/check_ascii.py
```

### Step 2 - Deliver the paired-view vertical slice

**Deliverables**

- Add the local server and React/TypeScript shell.
- Implement queue rail, official pane, aligned analog pane, synchronized zoom/scroll,
  hover pairing, click pinning, keyboard movement, and the evidence drawer.
- Implement three end-to-end representative cases:
  1. Form 1040 with input, copy, calculation, lookup, and branch units.
  2. Form 8949 with repeatable row-template and total behavior.
  3. Schedule D or its named worksheet with a worksheet/N-version unit.
- Keep the verdict controls visibly disabled in this slice; label them as not yet wired.

**Acceptance**

- A reviewer can identify the source and transformation of each representative unit
  without opening Advanced JSON or a second application.
- Hovering either pane highlights the exact pair and selecting it opens useful evidence.
- Only the current page and adjacent prefetch are requested.
- The app is usable at both required desktop sizes with no obscured review content.

**Tests**

```powershell
python -m pytest tests/test_workbench_server.py -q
npm --prefix workbench/ui test
npm --prefix workbench/ui run test:e2e -- --grep "paired view"
python tools/check_ascii.py
```

### JOHN UX GATE A - Accept the review model before breadth work

John reviews the three cases live. The Worker stops here and records exact feedback in
`plans/AGENT_HANDOFF.md`. Continue only after John confirms that the official/analog
comparison, explanations, navigation, and evidence hierarchy match the intended review
workflow. UX corrections belong in Step 2's follow-up commit before the gate is marked
passed.

### Step 3 - Complete navigation, coverage, and page-scale behavior

**Deliverables**

- Add grouped queue navigation, filtering, progress, visited state, and exact resume.
- Add lazy instruction citation viewing without leaving the current review context.
- Add collision handling and connector lanes for dense official forms.
- Add changed-only highlighting with unchanged context for promotion/delta entries.
- Add explicit visual states for pending, selected, visited, confirmed, defect, frontier,
  and review gap. Color must never be the only cue.
- Add keyboard help and focus management.

**Acceptance**

- A reviewer can traverse an entire queue entry without mouse precision work.
- Reload resumes the exact queue unit, page, selection, zoom, notes, and active time.
- No route loads all forms or all instruction pages.
- The primary UI contains no raw JSON dump.

### Step 4 - Add adapters for every queue kind

**Deliverables**

- Field maps: every mapped, excluded, frontier, and unresolved field is a review unit.
- Promotions: changed objects by default, full graph context on demand.
- Decisions: options, rationale, citations, selected branch, and escape hatch.
- Worksheets and repeatable tables: template, physical-row example, aggregation, and
  output line.
- N-version: candidate agreement/disagreement and selected result.
- Intake, extension, examples, and contract decisions: purpose-built structured views,
  not forced page geometry when no official counterpart exists.
- Unsupported/frontier coverage: downstream impact and explicit wall.

**Acceptance**

- Every current pending queue entry opens in a purpose-built view.
- Any unsupported queue kind fails preflight instead of falling back to raw JSON.
- Full queue traversal has no dead links, empty views, or document-only approvals.

### Step 5 - Wire sessions, active timing, and verdict emission

**Deliverables**

- Persist draft notes, coverage, active timer, and selection through the session API.
- Pause timing on hidden/idle state and allow explicit correction before submission.
- Enforce coverage and reason requirements in both UI and backend.
- Emit the existing hashed verdict format through `POST /api/verdicts`.
- Show the resulting verdict path, hash, and explicit apply/reverify command.
- Preserve duplicate, tamper, stale-artifact, rollback, and batch-atomicity behavior.

**Acceptance**

- A complete queue entry can be reviewed and receive a valid verdict without using the
  CLI.
- Reloading cannot lose a submitted verdict or silently submit a draft.
- The server cannot mutate graph objects, queue state, trust tiers, or provenance.
- A confirm cannot be submitted with unvisited required units.

### Step 6 - Integrity cleanup and campaign rehearsal

**Deliverables**

- Remove or hard-disable any remaining soft path that can write `human_confirmed`
  outside the reviewed verdict-application pipeline, including the noted
  `mine-examples --confirm` seam.
- Rehearse at least ten entries spanning field map, promotion, decision, worksheet or
  table, N-version, and product-contract views.
- Record active minutes, navigation errors, review gaps, defect submission flow, and
  reviewer notes.
- Fix all P0/P1 usability and integrity findings before Gate B.
- Update `docs/review-workbench.md` from as-built behavior and include reviewer help.

**Acceptance**

- Ten-entry rehearsal completes with no CLI needed for viewing or verdict creation.
- Zero queue entries resolve at document granularity only.
- Zero unauthorized paths can assert human confirmation.
- Measured active time and escape metrics are emitted from real session/verdict data.

### JOHN UX GATE B - Approve campaign readiness

John reviews rehearsal results and personally completes at least one simple entry and
one complex worksheet/table entry. Continue only when John says the workflow is fit for
the full campaign. Record the decision and any residual low-severity issues in the
handoff.

### Step 7 - Run the full human review campaign

**Deliverables**

- John reviews every pending queue entry through the accepted workbench.
- Every entry receives exactly one explicit verdict.
- Pipeline defects are fixed, re-extracted or re-authored, reverified, and re-reviewed.
- Source pathologies use only marked manual override paths with human provenance.
- Apply verdicts with the existing atomic pipeline and run full reverify.
- Export campaign metrics by queue kind and complexity.

**Acceptance**

- Pending review queue count is zero.
- No stale or duplicate verdict remains.
- Confirmed entries have honest reviewer/time/verdict provenance.
- Pipeline-defect and source-pathology paths satisfy their existing policy gates.

### Step 8 - Close M15 and the pre-ship gate

**Deliverables**

- Run the complete exit criteria below.
- Update engineering and review-workbench docs with final commands and metrics.
- Mark this plan `[COMPLETE]`, archive it, push once, and report.

## 7. Exit criteria

All commands must pass at 100 percent:

```powershell
python tools/check_ascii.py
python -m pytest -m m15 -q
python -m pytest -q
python -m workbench.cli preflight --year 2025
npm --prefix workbench/ui test
npm --prefix workbench/ui run test:e2e
review-workbench status --year 2025 --strict
tax-graph verify --year 2025 --profile full --strict
tax-graph compile --year 2025 --strict
```

The phase is not complete unless all of these product conditions are also true:

- John has passed both UX gates.
- The full queue was reviewed in the interactive official/analog comparison workflow.
- No current queue kind relies on raw JSON as its primary view.
- No pending item remains and no human-confirmed claim was written by an agent.
- Real active review minutes and escape rates were measured and reported.
- The base runtime remains light and provider agnosticism is unchanged.

## 8. Out of scope

- Editing graph rules or citations directly in the review app.
- Automatically applying verdicts from the browser.
- Remote multi-user hosting, accounts, or cloud synchronization.
- Replacing official IRS artifacts with a custom form renderer.
- Using the review projection as an execution engine or tax-calculation source.
- Mobile review. The primary target is a desktop monitor with enough width for paired
  panes.
