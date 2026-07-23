# M16-S4 structural validator report

Date: 2026-07-23

This is a read-only report from the four M16-S4 Stream B validators over the
promoted 2025 field maps, node files, widget bindings, node bindings, and the
available raw rendered-text companions. No promoted artifact, field map,
binding, citation, graph semantic, manifest, validate call site, or preflight
call site was changed.

The validators consume the M16-S3 resolver. Each finding is a structured record
with `document`, `control`, `validator`, `observed`, `expected`, and `evidence`.
The line-identity counts include unresolved resolver observations because an
unresolved identity is itself a review finding, not a pass. Total lines were
inferred from rendered captions containing `total`, `add lines`, or `these are
your total`; the resolver's resolved amount controls supplied the printed amount
line set. Explicit field-level unsupported dispositions satisfy line coverage,
but do not waive a form-total check without an explicit total disposition.

## Corpus counts

Counts are findings per document and validator. The last column is the sum of
the four validator counts.

| document | heading_integrity | line_coverage | total_presence | line_identity_triangle | total |
| --- | ---: | ---: | ---: | ---: | ---: |
| form_1040_2025 | 0 | 3 | 4 | 134 | 141 |
| form_1099_div_2025 | 0 | 12 | 1 | 96 | 109 |
| form_1099_int_2025 | 0 | 9 | 0 | 84 | 93 |
| form_1099b_2025 | 0 | 10 | 0 | 87 | 97 |
| form_13614_c_2025 | 0 | 0 | 0 | 297 | 297 |
| form_2441_2025 | 0 | 0 | 4 | 28 | 32 |
| form_6251_2025 | 0 | 0 | 0 | 9 | 9 |
| form_8949_2025 | 0 | 0 | 0 | 16 | 16 |
| form_w2_2025 | 0 | 7 | 0 | 153 | 160 |
| schedule_1_2025 | 0 | 0 | 0 | 9 | 9 |
| schedule_1a_2025 | 0 | 0 | 2 | 10 | 12 |
| schedule_2_2025 | 1 | 0 | 1 | 12 | 14 |
| schedule_3_2025 | 0 | 0 | 1 | 3 | 4 |
| schedule_a_2025 | 0 | 1 | 2 | 4 | 7 |
| schedule_b_2025 | 0 | 0 | 1 | 55 | 56 |
| schedule_d_2025 | 0 | 0 | 1 | 8 | 9 |

These are findings for the S5 work list, not a promotion verdict. In
particular, the unresolved counts are expected in the S3 bounded slice for
table columns, box templates, wrapperless controls, and other identities that
still lack a non-guessing structural contract.

## Schedule 2 Part I exemplar

The promoted Schedule 2 artifacts produce the required current defects:

| validator | control | observed | expected |
| --- | --- | --- | --- |
| heading_integrity | `form1[0].Page1[0].f1_15[0]` | amount resolver identity `4`; node `schedule_2_2025_part_i_line_1`, `form_line`, `currency`, label ends with `:` | amount control owned by a fillable non-heading node |
| total_presence | `line=1z` | PDF total cue present; no promoted graph node bound to line `1z` | form total has a graph node or explicit out-of-profile disposition |
| line_identity_triangle | `form1[0].Page1[0].f1_13[0]` | resolver line `3`; widget and mapping line `1z` | resolver-derived line `3` |
| line_identity_triangle | `form1[0].Page1[0].Line4_ReadOrder[0].c1_3[0]` | resolver line `4`; widget line `1` | resolver-derived line `4` |
| line_identity_triangle | `form1[0].Page1[0].f1_15[0]` | resolver line `4`; widget and node line `1` | resolver-derived line `4` |

The line-1z control has an existing unsupported field disposition in the legacy
map, so line coverage does not add a duplicate finding for that control. The
total-presence finding remains because the promoted graph has no line-1z node
and no explicit form-total disposition.

## Representative non-Schedule-2 rows

- `form_1040_2025`, `line_coverage`: the dependent-row controls resolve to
  line `1` but have no node ids; expected exactly one node or explicit
  out-of-profile disposition.
- `form_1040_2025`, `line_identity_triangle`: the resolver and committed
  binding triangle disagree for multiple controls; each control retains its
  own resolver evidence.
- `form_8949_2025`, `line_identity_triangle`: unresolved table/header controls
  remain findings rather than guessed identities.
- `form_13614_c_2025`, `line_identity_triangle`: all 297 descriptive controls
  remain unresolved in the S3 structure-only slice, matching the S3 report's
  wrapperless-field boundary.

## S5 handoff

S5 should regenerate the resolver-backed identities and semantic artifacts, then
rerun this report. The Schedule 2 acceptance target is to remove the heading
finding, add a line-1z node or authored total disposition, and reconcile the
line-3, line-4, and Line4_ReadOrder triangle rows. The report itself intentionally
does not fix either side of any finding.
