# Tax Graph schemas

JSON Schema (draft 2020-12) definitions for the graph's authored YAML objects. The build step validates every YAML file against these before compiling the graph to SQLite, so a typo or a misparsed YAML scalar fails at **build time**, never at runtime.

## Files

| Schema | Purpose |
|---|---|
| `document.schema.json` | A form / schedule / source doc / instructions / publication / worksheet (carries the tax year and version metadata for change detection). |
| `node.schema.json` | An addressable point: form line, box, worksheet field, taxpayer fact, computed value, or concept. |
| `table.schema.json` | A repeatable table subunit: row-template columns plus totals rows, with runtime row instances supplied in taxpayer facts. |
| `edge.schema.json` | A typed directed relationship between nodes; references a rule by id. |
| `rule.schema.json` | A reusable declarative transformation from the primitive instruction set. |
| `citation.schema.json` | **(addition beyond req. doc Section 11)** A span-level, *quotable* pointer to source text - the artifact that powers both extraction-time verification and runtime grounded questions. |
| `decision.schema.json` | **(addition)** A first-class human-judgment point. Enforces an escape hatch (`other`/`unsupported`/`escalate`) at the schema level, so a filer is never forced into a wrong choice. |
| `taxpayer_facts.schema.json` | Normalized inputs (not canonical graph); each fact records provenance for the audit trace. |
| `carryforward.schema.json` | **(addition)** The structured, machine-ingestible block of a Return Record (see `../docs/return-record.md`): cross-year carryforwards + consistency elections that year N emits and year N+1 ingests. |

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

`rule.schema.json`'s `operation` enum is the **v0** starting set from req. doc Section 6.6. It is being validated and (sparingly) expanded by a survey of real IRS instruction language - see the rule-survey notes. Bias is toward *composing* existing primitives over adding new ones.
