# Tax Graph schemas

JSON Schema (draft 2020-12) definitions for the graph's authored YAML objects. The build step validates every YAML file against these before compiling the graph to SQLite, so a typo or a misparsed YAML scalar fails at **build time**, never at runtime.

M15R adds additive canonical-address registries, widget/node bindings, and typed cross-form reference claims. Address strings are serialized from typed path components; consumers must not reconstruct official locations from display labels, node ids, or PDF field names.

## Files

| Schema | Purpose |
|---|---|
| `document.schema.json` | A form / schedule / source doc / instructions / publication / worksheet (carries the tax year, role-axis document class, and version metadata for change detection). |
| `node.schema.json` | An addressable point: form line, box, worksheet field, taxpayer fact, computed value, or concept. |
| `table.schema.json` | A repeatable table subunit: row-template columns plus totals rows, with runtime row instances supplied in taxpayer facts. |
| `address_registry.schema.json` | Canonical semantic form locations and their evidence. |
| `address_binding.schema.json` | Physical widget and stable graph-node bindings to canonical addresses. |
| `address_reference.schema.json` | Typed cross-form target claims with explicit resolution state. |
| `edge.schema.json` | A typed directed relationship between nodes; references a rule by id. |
| `rule.schema.json` | A reusable declarative transformation from the primitive instruction set. |
| `citation.schema.json` | **(addition beyond req. doc Section 11)** A span-level, *quotable* pointer to source text - the artifact that powers both extraction-time verification and runtime grounded questions. |
| `decision.schema.json` | **(addition)** A first-class human-judgment point. Enforces an escape hatch (`other`/`unsupported`/`escalate`) at the schema level, so a filer is never forced into a wrong choice. |
| `taxpayer_facts.schema.json` | Normalized inputs (not canonical graph); each fact records provenance for the audit trace. |
| `carryforward.schema.json` | **(addition)** The structured, machine-ingestible block of a Return Record (see `../docs/return-record.md`): cross-year carryforwards + consistency elections that year N emits and year N+1 ingests. |
| `review_manifest.schema.json` | Deterministic review-workbench projection grouped by deferred-review queue entry. |
| `review_unit.schema.json` | One scoped review target with official geometry, semantic analog placement, evidence references, and coverage state. |
| `review_expression.schema.json` | Recursive semantic expression tree used to explain graph operations in reviewer language. |
| `session_state.schema.json` | Non-authoritative queue-entry resume state: selection, page, zoom, notes, timing, and visited units. |

## Conventions

- All ids are `snake_case`, conventionally suffixed with the tax year (`schedule_d_2025_line_16`).
- Repeatable table ids and member node ids are static/template-level only. Runtime row instances
  use `row_key` and appear in traces as `<template_node>#<row_key>`; `#` remains illegal in static
  ids.
- Taxpayer fact table rows are keyed by table `column_id`, never by node id. Computed table columns
  are not valid taxpayer inputs.
- `additionalProperties: false` everywhere - unknown fields are authoring errors and fail validation on purpose.
- Cross-object references (`citation_refs`, `edge.source/target`, `edge.rule_id`) are **id strings**, validated for existence by build-time graph-integrity checks (req. doc Section 10.3), not by JSON Schema `$ref`.

## Note on the rule vocabulary

`tax_graph/operation_registry.py` is the versioned source for the operation enum and its
arity, operand roles, prompt description, projection rule, and runtime handler. Positional
roles are internal projection names; only named lookup roles are supplied by the extraction
model on the wire. Ordinary operands carry a nullable role field for schema uniformity, but
the deterministic validator rejects a non-null role on them. The JSON schema and prompt
schemas consume that contract; tests fail if the checked-in schema enum drifts from the
registry. Bias is toward composing existing primitives over adding bespoke rules.
