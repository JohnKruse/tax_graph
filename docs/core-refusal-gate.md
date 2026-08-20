# Core refusal gate

The core set is loaded only from `config/document_tiers.yaml` through
`load_core_document_ids`. The acquisition manifest does not carry a second
core marker.

## Refusal definition

The gate considers exactly these observable candidates:

1. A derivation row with status `errored`, `error`, `gapped`, or `skipped`.
2. A formula cell with status `review_gap` in `review_gaps.yaml`.
3. An extracted outcome with kind `not_derivable`.
4. A worksheet discovery refusal: a worksheet status other than `ready`, or a
   non-advisory discovery finding.
5. A frontier entry with status `unmodeled` or `declared`.

These are refusals because the pipeline did not produce a shippable answer for
the candidate. Other statuses and advisory worksheet findings are not refusals.

## Surfaced definition

A refusal is surfaced when its reason is present in the concrete artifact that
owns the candidate. The artifacts are, respectively:

| Candidate | Surfacing artifact |
| --- | --- |
| derivation row | `*_derive_cells_report.yaml` |
| formula review gap | the document draft's `review_gaps.yaml` |
| not derivable outcome | the document draft's `micro_extraction.yaml` |
| worksheet refusal | `worksheet-discovery*.yaml` |
| frontier refusal | `graph/<year>/frontier.yaml` |

The gate fails only when a core candidate is unsurfaced. Non-core candidates
remain in the report and may be unsurfaced without blocking the core.
