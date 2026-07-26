# M19-S1 Concept inventory and flow-spine derivation

Status: READ-ONLY survey of the promoted 2025 geometry and address projections.
Generated 2026-07-26 by the Worker. This report proposes identities; it does not
promote concepts, rewrite addresses, alter field maps, or change review state.

## Executive result

The current corpus exposes useful section-scoped and table-scoped flow structure, but
it does not yet provide a complete stable flow spine. Removing `line` and `box`
placement tokens from current paths exposes generic collisions such as `amount` and
`value`. Repeated table rows and document copies also collide, as expected, until the
M19 occurrence contract exists. These are findings, not accepted ids.

| measure | count |
| --- | ---: |
| physical geometry widgets | 1921 |
| documents | 16 |
| widgets with a mapped address | 1755 |
| widgets without a mapped address | 166 |
| address-derived concept groups after removing line/box tokens | 547 |
| repeatable-table collision groups | 47 |
| non-repeatable identity collision groups | 80 |

These counts describe the diagnostic projection only; none is an accepted promoted
identity. The per-document survey below gives the same split by document.

### Interpretation

- A candidate is a path-derived proposal that is unique in this snapshot and contains
  no detected year or placement token. It is not yet a promoted concept.
- A repeatable collision is multiple physical widgets for one concept. Examples are
  dependent rows, 8949 transaction rows, W-2 rows, and 1099 copies. The concept should
  remain one review unit and physical rows should be occurrences.
- An identity collision is distinct controls sharing one proposal after placement tokens
  are removed. It needs a semantic group or owner/role before stable ids are minted.
- An unresolved widget has no address-derived concept and remains visible in the source
  inventory rather than being silently dropped.

## Derivation method

For each geometry entry in `graph/2025/node_geometry.json`, the survey joins `address_id`
to `graph/2025/addresses/*.yaml` when available. The proposal keeps the document token
and path components of kinds `section`, `table`, `row_template`, `column`, `control`,
and `option`. It removes `document`, `line`, and `box` components because those are
placement or container coordinates in the current registry. A trailing `_YYYY` is
removed from a token for the proposal; the original token remains evidence.

The projection is a diagnostic baseline, not a minting algorithm. Raw AcroForm field
names, page numbers, row slots, geometry order, printed labels, and line/box numbers
are evidence only. They must never be used to make a collision appear unique.

## Document survey

The `groups` column is the count of distinct projected proposals for widgets that have
an address record. A repeatable collision is a group with multiple widgets under a
`row_template` path. An identity collision is any other multi-widget group.

| document | widgets | mapped | unresolved | groups | repeatable collisions | identity collisions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| form_1040_2025 | 199 | 199 | 0 | 104 | 10 | 6 |
| form_1099_div_2025 | 140 | 140 | 0 | 16 | 3 | 12 |
| form_1099_int_2025 | 127 | 127 | 0 | 17 | 3 | 13 |
| form_1099b_2025 | 163 | 163 | 0 | 27 | 3 | 23 |
| form_13614_c_2025 | 297 | 297 | 0 | 297 | 0 | 0 |
| form_2441_2025 | 72 | 0 | 72 | 0 | 0 | 0 |
| form_6251_2025 | 62 | 53 | 9 | 1 | 0 | 1 |
| form_8949_2025 | 202 | 200 | 2 | 38 | 16 | 3 |
| form_w2_2025 | 272 | 266 | 6 | 18 | 9 | 10 |
| schedule_1_2025 | 73 | 73 | 0 | 12 | 0 | 3 |
| schedule_1a_2025 | 54 | 54 | 0 | 6 | 3 | 1 |
| schedule_2_2025 | 63 | 59 | 4 | 2 | 0 | 2 |
| schedule_3_2025 | 37 | 33 | 4 | 1 | 0 | 1 |
| schedule_a_2025 | 33 | 28 | 5 | 2 | 0 | 1 |
| schedule_b_2025 | 72 | 16 | 56 | 2 | 0 | 2 |
| schedule_d_2025 | 55 | 47 | 8 | 2 | 0 | 2 |

The mapped/unresolved split is exact for the current files. `form_2441_2025` has no
address registry. The other unresolved widgets have no address id or refer to an
address absent from the registry:

| document | unresolved widgets | cause |
| --- | ---: | --- |
| form_2441_2025 | 72 | no address registry |
| schedule_b_2025 | 56 | no address record |
| form_6251_2025 | 9 | no address record |
| schedule_d_2025 | 8 | no address record |
| form_w2_2025 | 6 | no address record |
| schedule_a_2025 | 5 | no address record |
| schedule_2_2025 | 4 | no address record or id |
| schedule_3_2025 | 4 | no address record or id |
| form_8949_2025 | 2 | no address id |

## Collision findings

### Form 1040

- `form_1040/amount` is 58 line amount controls. This is an identity collision: line
  number was carrying all semantic identity and cannot remain in the concept id.
- Each Dependents column is a repeatable collision of four physical row widgets:
  `first_name`, `last_name`, `ssn`, `relationship`, `lived_with_you_more_than_half_2025`,
  `in_the_us`, `child_tax_credit`, `credit_for_other_dependents`, `full_time_student`,
  and `permanently_totally_disabled`.
- The Dependents proposal is already owner-qualified at `dependents/dependent/<role>`
  except for the year-bearing role. The year suffix must be removed before promotion.
- `lived_with_you_more_than_half_2025` is a direct never-contains failure: the year is
  placement/prose data, not identity.

### Forms 1099-DIV, 1099-INT, and 1099-B

- Each form has a repeated `value` collision across its numbered boxes. Box number is
  the only current discriminator and is placement data.
- Header, recipient, and state/local fields repeat across physical copies. Copy identity
  must be an occurrence, not a positional suffix in the concept id.
- State/local rows collide by column. The semantic owner is present (`state/local` and
  `jurisdiction`) but the row occurrence is not.
- Form 1099-B has the same pattern for transaction and state rows, plus repeated checkbox
  copies. Printed box numbers and source-copy order must not become concept identity.

### Form W-2

- `form_w2/value` is a non-repeatable collision across the numbered boxes. The box token
  is doing all the work and must be replaced by semantic flow roles.
- `state_local/jurisdiction/*` repeats across twelve physical row widgets and is a
  repeatable occurrence family.
- `entry/amount` and `entry/code` repeat across the four Box 12 rows. These are valid
  concept candidates only after the row occurrence contract is defined.

### Form 8949

- The Part I transaction columns `a` through `h` each repeat across eleven physical
  printed rows. These are occurrence collisions, not eleven concepts.
- The Part II transaction columns have the same shape.
- The table token `part_i_line_1` contains a line token and therefore fails the
  never-contains test even though the table/row/column structure is otherwise useful.
  The table needs a semantic name independent of the printed line anchor.

### Line-only schedules

- Schedule 1 collapses 60 amount controls to `schedule_1/amount`, and has smaller
  `date` and `description` collisions. Schedule 1-A collapses 46 amount controls.
- Schedule 2 collapses 48 amounts and 11 checkboxes. Schedule 3 collapses 33 amounts.
- Schedule A collapses 27 amounts. Schedules B and D collapse 14 and 44 amounts.
- Form 6251 collapses 53 amounts. These are not safe concepts. The missing semantic
  group/role must be derived from wrapper flow and authored structure before S3.

### Missing address projections

Form 2441 has 72 geometry widgets and no address registry. Its raw wrappers show a
repeatable Care Provider table and a Qualifying Person table, but S1 does not mint ids
from raw field names or row numbers. It is an explicit S3 acquisition/authoring work
item. The remaining 94 unresolved widgets in the other documents are likewise retained
as coverage gaps, not inferred from printed labels.

## Proposed concept inventory by flow shape

This table is the compact per-control inventory: each row represents the full set of
physical controls with the same proposed concept. The counts are the number of geometry
widgets in that set; the canonical control-level evidence is the joined geometry and
address source named above.

| flow shape | proposed concept pattern | widgets | result |
| --- | --- | ---: | --- |
| section singleton | `document/section/control` or `document/section/option` | 515 | candidate when unique |
| dependent row template | `form_1040/dependents/dependent/<column>` | 40 | repeatable collision; one concept per column |
| 8949 row template | `form_8949/<table>/transaction/<column>` | 184 | repeatable collision; table token also needs semantic rename |
| W-2 Box 12 rows | `form_w2/entry/<column>` | 24 | repeatable collision |
| W-2 state/local rows | `form_w2/state_local/jurisdiction/<column>` | 12 | repeatable collision |
| 1099 state/local rows | `form_1099_*/state/jurisdiction/<column>` | 24 per form family | repeatable collision |
| line-only controls | `schedule_*/amount`, `form_6251/amount`, or generic role | 447 | identity collision |
| box-only controls | `form_1099_*/value` or `form_w2/value` | 358 | identity collision |
| year-bearing table role | `form_1040/.../lived_with_you_more_than_half_2025` | 4 | never-contains failure |
| no address | `UNRESOLVED/no_address` | 166 | coverage gap; no id proposed |

The inventory deliberately preserves collisions. A row count greater than one is not
resolved by appending a counter, page, field name, or row slot. The next phase must add
semantic flow and occurrence data so the same table remains stable when IRS line/box
numbers or physical row order change.

## Never-contains and owner-qualification findings

The S1 checks are:

- `year_literal`: a year appears in a source path token or proposed id.
- `placement_token`: a line or box token survives in a proposed id, including a table
  token such as `part_i_line_1`.
- `unqualified_role`: the terminal role is generic and has no section/table owner in
  the current path. Bare `ssn` is never acceptable; it needs taxpayer, spouse,
  dependent, provider, or another owner/role.
- `collision`: multiple controls share the same proposal. This is either an expected
  repeatable occurrence or an unsafe identity collision, as classified above.
- `unresolved`: no address-derived proposal exists.

The measured high-value examples are:

| finding | evidence |
| --- | --- |
| year literal | `lived_with_you_more_than_half_2025` on four Dependents rows |
| placement token | `form_8949/part_i_line_1/transaction/<column>` |
| bare/generic role | line-only `amount`, box-only `value`, generic checkbox roles |
| owner-qualified success | `form_1040/identity/taxpayer_ssn`, `spouse_ssn`, and `dependents/dependent/ssn` |
| repeatable occurrence | four Dependents rows, eleven 8949 rows, W-2 rows, 1099 copies |

## S3 work list

1. Add semantic group and owner metadata for all line-only and box-only controls. Their
   current generic collisions are not safe stable identities.
2. Replace `lived_with_you_more_than_half_2025` with a year-free semantic role before
   any concept is promoted.
3. Define the occurrence contract for Dependents, 8949, W-2, and 1099 repeated rows
   and copies. Keep review at concept granularity; do not quadruple the queue.
4. Acquire or author an address projection for Form 2441 and close unresolved address
   records in the other documents.
5. Decide whether cross-document concepts remain per-document with `same_fact_as`, as
   recommended in `PHASE_M19.md`; do not infer identity from matching printed labels.

## Source and verification commands

- Source: `graph/2025/node_geometry.json`
- Source: `graph/2025/addresses/*.yaml`
- No promoted artifact, field map, graph object, verdict, or session was written.
- No new pytest file is declared for S1; testing starts at M19-S3 per the phase plan.
- S1 gates to run after this report: ASCII, `git diff --check`, and module-form
  `validate 2025`.
