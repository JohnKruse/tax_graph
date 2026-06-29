# M4 Proposal for Claude: Outline-First Extraction

Date: 2026-06-29
Author: Codex worker note for Claude/Architect review

## Summary

The current M4 extractor can run live, is provider-agnostic, writes only to `_drafts`,
and has a conservative human-review gate. However, held-out Form 8949 trials suggest
that whole-document extraction is too broad a task for reliable, cheap model use.

The model generally understands the tax structure, but it often fails one or more
mechanical requirements while producing the whole draft graph at once: exact citation
quotes, provenance for every object, stable id style, formula decomposition, and
section-specific line completeness.

Recommendation: redesign Step 7 around **outline-first extraction**. First build a
document tree that preserves the flow of the IRS form. Then walk that tree with small,
targeted extraction tasks and assemble final draft graph objects deterministically.

## Why the Current One-Pass Approach Struggles

The current generator sees the form text plus bundled instructions and emits nodes,
edges, rules, citations, decisions, and provenance in one response. That forces the
model to do all of this simultaneously:

- identify sections, lines, boxes, tables, columns, formulas, and cross-form flows;
- locate relevant instruction snippets;
- produce exact source quotes;
- create graph-shaped objects;
- choose stable ids;
- represent formulas using the closed operation vocabulary;
- emit all provenance;
- avoid overproducing unrelated objects;
- satisfy JSON/schema constraints.

Live trials showed model variance:

- `z-ai/glm-5.2` was not reliable for the JSON-schema response contract.
- `qwen/qwen3.7-plus` recovered some key structures but was slow/flaky.
- `openai/gpt-5.2-chat` via OpenRouter produced the cleanest `SUBTRACT` structure.
- `~google/gemini-flash-latest` needed `reasoning_effort` and `reasoning_exclude`
  controls to avoid truncated JSON. Minimal reasoning recovered `SUBTRACT`; high
  reasoning improved headline issue counts but lost the key `SUBTRACT` formula.

This points to task shape, not just model choice. Smaller prompts and narrower output
schemas should make cheap/fast models more viable.

## Proposed Architecture

### 1. Build a Form Outline Tree

Before graph extraction, create a structured outline for each form. Simple forms may be
a flat vector of line nodes. Complex forms should preserve sections, subsections,
tables, checkbox groups, worksheets, and flow cues.

Example sketch for Form 8949:

```yaml
document_id: form_8949_2025
children:
  - outline_id: part_i
    kind: section
    label: Short-Term
    boxes: [A, B, C, G, H, I]
    children:
      - outline_id: part_i_line_1
        kind: transaction_table
        columns: [a, b, c, d, e, f, g, h]
      - outline_id: part_i_line_2
        kind: totals
        columns: [d, e, g, h]
      - outline_id: part_i_line_3
        kind: outbound_flow
  - outline_id: part_ii
    kind: section
    label: Long-Term
    boxes: [D, E, F, J, K, L]
    children:
      - outline_id: part_ii_line_1
        kind: transaction_table
        columns: [a, b, c, d, e, f, g, h]
      - outline_id: part_ii_line_2
        kind: totals
        columns: [d, e, g, h]
      - outline_id: part_ii_line_10
        kind: outbound_flow
```

This can be mostly deterministic from rendered form text, headers, field-grid geometry,
and line anchors. Use an LLM only when the renderer cannot confidently classify a block.

### 2. Attach Evidence to Each Outline Node

Each outline node should carry a compact evidence bundle:

- nearby rendered form text;
- nearby headers/section labels;
- field-grid rows and x/y clusters;
- relevant instruction snippets;
- extracted URLs/links when useful;
- known sibling/parent context.

For Form 8949 line 2, the evidence bundle should include the column header text
containing "Subtract column (e) from column (d)" and the instruction text explaining
column (h) and Schedule D routing.

### 3. Walk the Tree With Micro-Extractions

Instead of asking for the whole graph, ask small questions over one outline node at a
time. Examples:

- classify this outline node as input, total, formula, decision, table, or flow;
- extract only graph nodes for this line/table/box group;
- extract only the formula for column (h);
- extract only outbound Schedule D flows for this section;
- extract only exact citations for the proposed formula/flow.

Use tiny purpose-specific schemas rather than the full draft graph schema for every
question.

Example formula schema:

```json
{
  "output": "column_h",
  "inputs": ["column_d", "column_e", "column_g"],
  "operation_plan": [
    {"operation": "SUBTRACT", "minuend": "column_d", "subtrahend": "column_e"},
    {"operation": "SUM", "addends": ["previous_result", "column_g"]}
  ],
  "citation_quote": "..."
}
```

### 4. Assemble Graph Objects Deterministically

The model should answer semantic questions. Code should:

- create stable ids;
- map outline ids to graph node ids;
- create graph objects from micro-results;
- enforce schema shape;
- merge duplicate patterns across Part I/Part II;
- attach provenance;
- keep drafts under `_drafts`.

This lowers the chance that a model invents bad ids, mixes provenance into graph
objects, or emits partial graph objects with missing metadata.

### 5. Validate at Multiple Levels

Keep the existing draft review gate, but add earlier checks:

- outline completeness: every true section/line/table has an outline node;
- evidence completeness: every extraction task has exact source spans;
- micro-result validation: exact quote appears in the evidence bundle;
- assembly validation: final graph objects validate against canonical schemas;
- held-out validation: compare assembled drafts against hand-authored references.

## Suggested Plan Changes

Claude should consider replacing the current Step 7 with a new staged Step 7, or adding
a new Step 8 before declaring M4 complete.

Proposed Step 7:

1. Define outline-tree schema and evidence-bundle schema.
2. Implement deterministic outline builder for rendered form text plus field grid.
3. Add LLM-assisted outline repair/classification behind the same provider-agnostic
   `LlmClient`.
4. Implement tree-walk micro-extraction for:
   - line/column nodes;
   - formulas;
   - outbound flows;
   - citations.
5. Implement deterministic graph assembly from micro-results.
6. Re-run held-out Form 8949 validation.

Exit criteria:

- `pytest -m m4` remains green.
- Outline for `form_8949_2025` captures Part I, Part II, boxes, line 1 tables, line 2
  totals, and Schedule D flow cues.
- Micro-extraction recovers column (h) as `d - e + g` using closed operations.
- Outbound FEEDS declarations include Schedule D lines 1b, 2, 3, 8b, 9, and 10.
- Exact citation quotes pass deterministic verification.
- Drafts remain review-gated and never auto-merge.

## Open Questions for Claude

- Should the outline tree be a committed intermediate artifact under
  `graph/<year>/_drafts/<document_id>/outline.yaml`, or only an internal build artifact?
- Should outline building be mostly deterministic with optional LLM repair, or always
  model-assisted?
- Should micro-extraction use the same provider/model as whole-document extraction, or
  allow a cheaper configured `llm.micro_model`?
- Should exact citation extraction be model-generated, deterministic span-selected, or a
  hybrid where the model chooses among candidate spans?
- Should Form 8949 become the canary for outline-first extraction before expanding to
  Schedule D and Form 1040?

## Worker Recommendation

Use outline-first extraction for the held-out gate. The current whole-document pipeline
is useful as a baseline and fallback, but it asks too much of one model call. Preserving
the form's own tree and walking it with small, auditable extraction tasks should improve
accuracy, reduce model cost, and make failures easier to debug.
