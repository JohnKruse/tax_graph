# Phase M16 - Forms Ingestion Pipeline Correctness (canary Straight Line)

**Status:** ACTIVE (approved by John 2026-07-21: M16 is the engine that finishes the
remaining forms; the A9h..A9z hand campaign is retired/superseded, marked in
`plans/PHASE_M15.md`; the Section 3 sequencing question is RESOLVED the same way -
M16 fully replaces the A9h..A9z line items). M16-S1 is [DONE] (commit `17d2351`,
Architect-verified: fixture 1 passed + 1 strict xfail). M16-CI (CI floor
restoration, 2026-07-22) rides under this phase as infrastructure: CI had been
red on every push since 2026-07-14; after a Worker environment stop, John chose
direct Architect implementation. Next Worker step: M16-S2 (Stream A typing).

**Why this phase exists.** The M15 A9 address campaign was hand-authoring, one form at a
time, what a correct ingestion pipeline should generate. On 2026-07-21 the Schedule 2
audit surfaced a defect that is NOT a placement shift and NOT fixable by hand-labeling:
the ingestion pipeline emitted a structurally wrong graph. John's decision: stop
authoring forms one at a time and fix the pipeline at BOTH root-cause layers. This phase
is the forms-pipeline end-state (guiding invariant 6, rollover seam 5) pulled forward.
When it lands, the per-form hand campaign (A9h..A9z) is retired: forms are ingested by
runnable pipeline stages with fail-closed validators, and only genuine review items reach
a human.

**Canary:** Straight Line (a form's printed line identity flows straight through
extraction -> node -> binding -> filled cell with no hand patching).

**Gate:** M16 is complete only when (1) the pipeline regenerates field identities for all
15 in-scope 2025 forms, (2) the 9 committed A9 forms are reproduced by the pipeline as a
regression corpus with no loss of correctness, (3) Schedule 2 Part I passes the acceptance
fixture below, and (4) `validate 2025` + the full floor are green.

## 1. The Schedule 2 exemplar (the acceptance fixture)

Verified 2026-07-21 against `.cache/raw/2025/schedule_2_2025.fields.json` (raw AcroForm
rects), MCP `get_node`, and citations. The defect has two independent layers:

**Layer A - semantic extraction (`tax_graph/extract/`).** `assembly.py:171-172` assigns
every non-computed extracted line `node_type: form_line` and `value_type: currency`,
discarding the section/heading distinction that `outline.py` already detects
(`kind="section"`). So the heading `schedule_2_2025_part_i_line_1` ("- 1: Additions to
tax:", citation `cite_span_schedule_2_2025_0004`) became a currency form_line, and the
form's line 1z total was never emitted as a node at all.

**Layer B - field-identity binding (`tax_graph/output/field_maps.py` + `geometry.py`,
and the addressing layer).** The binding generator associated widgets to nodes/lines by
geometry and label mining, which mis-fired on Schedule 2's redesigned interleaved layout:
`f1_15` (the Line 4 Self-employment tax amount cell - proven by the PDF's own
`Line4_ReadOrder` field grouping and its Form 4361/4029 exemption checkboxes) is bound to
the line 1 heading node; the whole Part I far-right column is mis-attributed (`f1_13` is
line 3, mined as "line 1z/line 17"; `f1_11` is the line 1z total; the Line 4 exemption
boxes are labeled "Line 1"). Nothing failed closed on any of it.

**Acceptance fixture (Schedule 2 Part I).** After M16, the pipeline must independently
yield: `f1_15` -> line 4 (self-employment tax), `f1_13` -> line 3, `f1_11` -> line 1z
total, the `Line4_ReadOrder` checkboxes -> line 4 exemptions; emit a line 1z total node;
type line 1 as a non-fillable heading owning no amount cell; and FLAG (fail closed to the
review queue) any residual contradiction - never silently emit a heading-with-a-cell, a
line with no node, or a total present on the PDF with no node.

## 2. Work streams

### Stream A - Semantic extraction typing (`tax_graph/extract/`)
- Propagate the outline's section/heading distinction through assembly: introduce a
  non-fillable node kind (e.g. `heading`/`section`) so a heading never becomes a
  fillable currency line. `assembly.py:_node_object` is the collapse point.
- Infer `value_type` from the printed control (currency / text / date / identifier /
  checkbox) instead of hardcoding `currency`. The existing per-form differentiation
  (Schedule 1 dates, SSNs) shows the signal exists; make it the rule, not the exception.
- Emit form totals present on the PDF (e.g. line 1z) as nodes, or mark them explicitly
  out-of-profile - never absent-and-unaccounted.
- Re-extraction must not regress the modeled tax logic (edges, formulas, citations).
  The semantic-core diff and OTS/PE witnesses are the guardrails.

### Stream B - Structure-first field-identity resolver + validators (`tax_graph/output/`)
- Replace geometry/label mining with a resolver that derives each control's `(line,
  role)` from the AcroForm qualified field-name structure (`LineNN_ReadOrder`, row/copy
  wrappers) plus printed-caption adjacency (the A9c/A9d adjacency machinery).
- Extend `field_maps.py:validate_field_maps` (which already checks the mapping triangle,
  uniqueness, and coverage) with fail-closed STRUCTURAL validators: a heading/section
  node may not own an amount cell; every printed amount line resolves to exactly one node
  OR an explicit out-of-profile disposition; a form total present on the PDF has a node or
  is explicitly out-of-profile; the node's bound line must equal the widget's derived line
  (line-identity triangle). Contradictions route to the review queue, never silent output.
- This resolver IS the yearly rollover re-binder (engineering-plan rollover seam 5):
  year-independent authored templates matched to each year's widget inventory.

### Stream C - Corpus reconciliation and campaign retirement
- Regenerate field identities for all 15 forms via the pipeline.
- The 9 committed A9 forms (1040, 8949, W-2, 1099-B/DIV/INT, Sch 1, Sch 1-A) are the
  regression corpus: the pipeline output must reproduce their reviewed identities (or
  surface a justified, reviewed diff). A9's authored labels are ground truth, not the
  method.
- Retire A9h..A9z as a hand campaign; fold the remaining review into "run the pipeline,
  review the flagged items" through the M15 workbench.

## 3. Sequencing against M15

M15 Gate A stays PAUSED. M16 is a prerequisite for finishing the forms surface: the A9
hand campaign does not resume; its remaining forms are produced by the M16 pipeline. The
M15 review workbench remains the surface where M16's flagged items are adjudicated, so
M15 and M16 converge rather than compete. John to confirm whether M16 fully replaces the
A9h..A9z line items or runs as an explicit sub-track of M15.

## 4. Proposed first Worker task (M16-S1: characterize + lock the fixture)

Before any code change, the Worker produces a read-only, committed characterization of the
Schedule 2 ingestion defect end to end and turns it into an executable acceptance test
(xfail initially): the raw AcroForm structure for Part I, the current wrong node types and
bindings, and the target identities from Section 1. No extraction or resolver code changes
in S1 - it establishes the failing fixture that Streams A and B must turn green. This
keeps the first step small, verifiable, and grounded in the real form. Later steps
(M16-S2 Stream A typing, M16-S3 Stream B resolver/validators, M16-S4 corpus
reconciliation) are planned just-in-time after S1 lands.

## 5. Invariants carried in

- No hand-transcription of form controls as a recurring practice (guiding invariant 6).
- Fail-closed always: an unresolved identity is a review item, never a silent emission.
- Re-extraction never edits cited graph parameters or modeled tax logic without the
  pinned witnesses; citations stay verbatim-from-acquired-source.
- Local commits only during the run; Architect batch-verifies and pushes at the stop.
- ASCII only; full-suite floor is the commit floor; sequential test partitions.

## M16-S1 characterization record (Worker, 2026-07-22)

This section is the committed defect note and evidence index for the executable
acceptance fixture in `tests/test_schedule_2_m16.py`. The evidence is local and
read-only: `.cache/raw/2025/schedule_2_2025.fields.json`, the official cached PDF,
the promoted Schedule 2 graph and field-map artifacts, and the citation file.

### Raw AcroForm identity

The page-1 AcroForm has a qualified wrapper named `Line4_ReadOrder`. Its children
`c1_3`, `c1_4`, and `c1_5` are the three exemption checkboxes at the printed line-4
row. The official PDF text at that row is `Self-employment tax` followed by the
exemption choices `1 4361`, `2 4029`, and `3`; the far-right amount cell is printed
as line `4`. The raw rectangles put the checkbox controls at x=79.2, 158.4, and
237.6, and the indented `f1_14` text control at x=252.0..324.0, all at y=468..480.
The line-4 far-right amount control is `f1_15` at x=504.0..576.0, y=468..480.

Above that row, the Part-I far-right amount column is `f1_11` at the printed `1z`
row (y=390..402), `f1_12` at line 2 (y=408..420), and `f1_13` at line 3
(y=426..438). This interleaving is why a geometry-only or mined-label-only
binding is unsafe: the qualified wrapper identifies line 4 while the far-right
column is shared by the Part-I rows.

### Current promoted state and citations

The graph node `schedule_2_2025_part_i_line_1` is labeled `Line 1: Additions to
tax:`, has `node_type: form_line` and `value_type: currency`, and cites
`cite_span_schedule_2_2025_0004` (`- 1: Additions to tax:`). It is therefore a
fillable currency node for a heading. There is no graph node for the printed
line-1z total. `schedule_2_2025_part_i_line_3` exists and cites
`cite_span_schedule_2_2025_0019`; the line-4 node is currently named
`schedule_2_2025_part_ii_line_4` and cites `cite_span_schedule_2_2025_0021`.

The current field map binds `f1_15` to the line-1 heading, binds `f1_13` to line
1z, and binds `f1_11` to line 1z as well. The widget bindings label all three
Line4 checkboxes as line 1, and label the indented `f1_14` amount as line 1.
Thus the wrong state is both a semantic extraction defect (heading typed as a
currency line and line-1z omitted) and a field-identity defect (mis-attribution
across the interleaved amount columns). The current map does not fail closed.

### Target and fail-closed contract

The M16-S1 fixture records the Section 1 target identities: `f1_15` -> line 4,
`f1_13` -> line 3, `f1_11` -> the line-1z total, and the `Line4_ReadOrder`
checkboxes -> line-4 exemptions. It also requires a line-1z total node, a
non-fillable line-1 heading that owns no amount cell, and no silent contradictions.
Every printed amount line must resolve to exactly one node or an explicit
out-of-profile disposition, and a bound node line must equal the widget's derived
line. The acceptance test is intentionally a strict xfail against today's
pipeline; later M16 Stream A and Stream B work should turn it green.
