# Return Record (decision log + carryforward memo)

> Status: implemented-v0. The runtime, persistent counterpart to the build-time
> [decision nodes](../schemas/decision.schema.json). Extends the requirements-doc
> "Tax Trace" (Section 5.3) / `export_audit_file` (Section 8.2) from *computation provenance* into a
> durable, re-ingestible record of **what was decided, why, and what carries forward**.

## Why this exists

Tax is an annual-cadence activity: by next year you've forgotten *what* you did and,
more importantly, *why*. A Return Record is the institutional memory for a filing. It serves
four jobs:

1. **Carryforwards** - capital-loss carryover, unused FTC by category/year, basis, etc.
   reference a *prior* year and feed a *future* one. The Return Record is the vehicle for
   that cross-tax-year linkage (the gap found in the rule survey). Year N's carryforward
   block becomes year N+1's **input facts**, with provenance "from 2025 Return Record."
2. **Consistency** - some elections must be the same year to year (e.g. FTC paid-vs-accrued,
   accounting methods). Next year's agent reads last year's choice and holds the line.
3. **Audit defense** - every judgment call is recorded with its rationale and the *quoted*
   IRS citation that supports it. If the return is ever questioned, the "why" is on file.
4. **Roadmap-for-AI continuity** - next year's agent ingests last year's record to prime
   itself. It's a first-class *input* to the next run - and, unlike the user's scanned tax
   docs, it's perfectly clean because the system authored it (no OCR, no variability).

## The dual-format principle

A Return Record is **one human-readable Markdown memo** that **embeds (or is paired with) a
structured, schema-validated block** for machine ingestion.

- **Prose, for the human:** the decisions and the *why*, in plain language.
- **Structured data, for the machine:** the carryforward values and elections.

**Never make next year's agent re-extract a dollar figure from prose** - that reintroduces
exactly the variability we avoid everywhere else. The human reads the narrative; the next
pipeline reads the structured payload deterministically.

## Contents

1. **Metadata** - tax year, filing status, generated date, Tax Graph version, client/model used.
2. **Facts ledger** - each input fact, its value, and provenance (source document,
   `extracted_by`, confidence) - mirrors `taxpayer_facts`.
3. **Decision log** - for each decision node resolved: the question, options presented,
   **chosen option, rationale (the *why*), governing citation (quoted), decided-by
   (filer/agent), timestamp.**
4. **Unsupported / deferred** - cases explicitly marked unsupported and how they were
   handled, so next year knows the gap was intentional.
5. **Computed outputs + trace summary** - the Section 5.3 Tax Trace for the final values.
6. **Carryforwards (structured)** - the cross-year payload: each carryover with its amount,
   category, originating year, and derivation. This block is schema-validated and is what
   next year ingests.
7. **Consistency elections (structured)** - year-to-year choices that must stay consistent.

## Cross-year flow

```
2025 Return Record --(carryforwards + elections block)--> 2026 input facts
        ^                                                          |
        +---------------- audit / "why" for the human <-----------+
```

Year N's structured block is read as year N's-plus-one facts (provenance recorded); the prose
is for the human to review and remember.

## Privacy

A Return Record contains a person's actual decisions and dollar figures - about as sensitive
as data gets. It is **local-first**: it lives with the user's tax documents on their machine,
is never uploaded, and is the user's to keep. Test/example records use only fake data (Section 10.5).

## Implemented

M5 implements a paired output from `tax-graph run`: `return_record_<year>.md` for the memo and
`return_record_<year>.carryforward.yaml` validated by
[`carryforward.schema.json`](../schemas/carryforward.schema.json). Use `--record-dir` to redirect
the files, `--no-record` to skip emission, and `--prior-record` to ingest a previous structured
block. The MCP server also exposes `export_return_record`.

For capital losses, the cited Capital Loss Carryover Worksheet emits separate positive
`capital_loss_short_term` and `capital_loss_long_term` amounts. Prior-record ingestion maps those
positive worksheet amounts to the negative Schedule D line 6 and 14 form-entry convention. The
block retains `capital_loss_raw` as a secondary continuity field; it is not used to prime a later
return.

## Open items

- How the agent *surfaces* last year's decisions when a consistency election recurs.
- Redaction/fixture tooling so records can be shared for testing with fake data only.
# Filing field maps

M12 maps graph nodes and identity slots to official IRS AcroForm widgets under
`graph/<year>/field_maps/`. Committed inventories record each official widget's
type, page, and rectangle. `tax-graph validate` checks that mapped fields exist,
mapped nodes exist, exclusions are explicit, and frontier fields have blank notes.

All session artifacts default to `output/returns/<return_id>/`: Return Record,
carryforward YAML, audit trace, run diagnostics, official forms, and OTS sidecar.
`return_id` is a path-safe caller value or a stable id from the facts document;
separate returns never share an artifact directory. The legacy `--record-dir`
option remains an explicit direct-directory override.
