# M16-S3 structure-first resolver comparison

Date: 2026-07-23

This is a read-only characterization report. The resolver read the committed raw
AcroForm field inventories under `.cache/raw/2025/*.fields.json` and their rendered
text companions, then compared each derived `(line, role)` identity with the
address selected by the committed widget-binding registries. No graph, field-map,
binding, citation, or other promoted artifact was regenerated or edited.

## Corpus scope

The handoff and M16 plan call this the 9-form A9 corpus. The named A9 commit list
contains eight document IDs: Form 1040, Form 8949, W-2, Forms 1099-B/DIV/INT,
Schedule 1, and Schedule 1-A. The ninth row below is Form 13614-C, the already
committed information-return address registry in the same 15-form surface. It is
included to make the requested nine-form comparison explicit; it is not presented
as a new A9 campaign artifact.

## Results

Counts are per physical AcroForm widget. Agreement means the derived line and role
both equal the authored registry projection. Disagreement means both sides are
present but differ. Unresolved means the resolver did not have enough structural
or adjacent-caption evidence, or the authored side had no matching binding.

| document | controls | agreement | disagreement | unresolved |
| --- | ---: | ---: | ---: | ---: |
| form_1040_2025 | 199 | 42 | 33 | 124 |
| form_8949_2025 | 202 | 0 | 184 | 18 |
| form_w2_2025 | 272 | 39 | 107 | 126 |
| form_1099b_2025 | 163 | 28 | 68 | 67 |
| form_1099_div_2025 | 140 | 21 | 34 | 85 |
| form_1099_int_2025 | 127 | 17 | 29 | 81 |
| schedule_1_2025 | 73 | 34 | 5 | 34 |
| schedule_1a_2025 | 54 | 29 | 20 | 5 |
| form_13614_c_2025 | 297 | 0 | 0 | 297 |

The result is intentionally not a promotion claim. The disagreements are findings
for the Architect and later validator/reconciliation work; neither side was
altered by this step.

## Exemplar rows and findings

- Schedule 2 is not part of this A9 comparison because its current authored map is
  the M16 acceptance defect. Focused tests independently establish `f1_15 -> 4,
  amount`, `f1_13 -> 3, amount`, `f1_11 -> 1z, amount`, and the
  `Line4_ReadOrder` checkboxes -> `4, checkbox` from raw structure and rendered
  text.
- Form 1040 unresolved examples include the unwrapped page-header fields
  `f1_01`, `f1_02`, and `f1_03`; these have no line wrapper or raw line anchor.
- Form 8949 is mostly a deliberate finding in this bounded resolver slice: its
  table column identity needs the later table/column reconciliation contract.
  Header fields and repeated checkbox rows remain unresolved rather than guessed.
- W-2 exposes the same boundary: `BoxA_ReadOrder` is structurally visible, while
  unwrapped `Col_Left` fields and `Void_ReadOrder` need explicit box-template
  semantics to establish a canonical line/box identity.
- Schedule 1 and Schedule 1-A show raw anchor limitations on indented sublines;
  examples include `f1_03` and `f1_05` where a one-letter or nearby numeric anchor
  is not enough to prove the authored subline without a table/row contract.
- Form 13614-C uses descriptive field names rather than IRS line wrappers. All 297
  controls are therefore unresolved in this structure-first slice, which is an
  honest review finding rather than a guessed mapping.

## Reproduction

The report was produced by calling `resolve_fields` for each inventory, loading
the committed widget bindings through `load_address_artifacts(2025, root)`, and
passing the resulting expected identities to `compare_identities`. The focused
executable coverage is in `tests/test_field_identity_m16.py`; the raw-cache test
has the standard skip-if-missing guard for fresh checkouts.
