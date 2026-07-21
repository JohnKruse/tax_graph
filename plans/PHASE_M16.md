# Phase M16 - Forms Ingestion Pipeline Correctness (canary Straight Line)

**Status:** PROPOSED (Architect draft 2026-07-21, at John's direction). Awaiting John's
approval of scope + sequencing before any Worker task starts.

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
