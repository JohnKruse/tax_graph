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

A refusal is surfaced when it becomes a visible cell in the generated review
surface. Form-line cells are identified by the generated review HTML object
marker for the candidate's canonical document and line. Worksheet refusals are
identified by their generated worksheet card. A frontier entry at status
`declared` is surfaced by that declaration itself.

The source artifacts remain the candidate inputs, respectively:

| Candidate | Candidate artifact |
| --- | --- |
| derivation row | `*_derive_cells_report.yaml` |
| formula review gap | the document draft's `review_gaps.yaml` |
| not derivable outcome | the document draft's `micro_extraction.yaml` |
| worksheet refusal | `worksheet-discovery*.yaml` |
| frontier refusal | `graph/<year>/frontier.yaml` |

The generated review surface is the per-document `review.html` beside the
draft. A form-line cell must have the generated object marker for
`nodes/<document>_root_line_<line>`. A worksheet card must carry the generated
worksheet document marker. The gate does not treat the candidate artifact,
`review_queue/`, or preflight output as a review surface.

The gate fails only when a core candidate is unsurfaced. Non-core candidates
remain in the report and may be unsurfaced without blocking the core.
