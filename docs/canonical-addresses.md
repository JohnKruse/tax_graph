# Canonical Form Addresses

Status: AS BUILT in M15R, 2026-07-15. Canary: Street Address.

Canonical addresses are the authoritative identity for official form locations. Graph
node ids, PDF field names, labels, prose, and geometry remain useful bindings or display
evidence; none is allowed to reconstruct official identity in production.

## Artifact contract

Each promoted document can have four address artifacts plus an optional stable concept
inventory under `graph/<year>/`:

- `addresses/<document_id>.yaml`: typed address hierarchy with a year-specific
  `address_id` and a yearless `logical_key`.
- `bindings/widgets/<document_id>.yaml`: physical AcroForm widget to address bindings.
- `bindings/nodes/<document_id>.yaml`: graph node to address bindings.
- `references/<document_id>.yaml`: cross-form address claims and exact resolution state.
- `concepts/<document_id>.yaml`: the year-free flow-spine concepts for structured forms.

For M19 structured forms, an address is a placement, not durable meaning. Its optional
`concept_id` is path-style and excludes years, printed line/box tokens, and prose. The
`placement` object retains the printed token and official reference for human display;
`aliases` includes the yearless logical key for rollover compatibility. Repeatable rows
carry a slot-authored `occurrence` contract with `row_policy: slot_keyed`; the concrete
field projection records every discriminator axis, such as `copy=A/row_slot=3`. Runtime
may bind a slot to an entity later, but authoring does not claim entity binding. The
`review_granularity: concept` contract keeps one review identity per column rather than
one per printed row slot. Physical widgets remain visible in the workbench as occurrences
and their refs include the slot, for example `1040/dependents/dependent[3]/ssn`.

Repeated concepts are invalid without a discriminator. A W-2 Box 12 field therefore
uses copy plus row slot, while an information-return state table uses copy plus row slot
and a copied singleton uses copy alone. `retrieve_occurrences` and
`retrieve_table_occurrence` read these projections from graph metadata so a complete
table row can be selected without reopening the source PDF.

All candidate-corpus records remain pending review until M15 drains the review queue.
Automation never writes human-confirmed provenance. A missing or ambiguous binding fails
closed; display labels and opaque ids are not fallbacks.

## Author and contributor workflow

`tools/build_address_campaign.py` deterministically rebuilds the bounded project campaign
from committed field inventories and dispositions. It writes drafts first and promotes
only schema-valid pending-review artifacts when `--promote` is explicit. Per-document
coverage reconciles inventory controls to addressed widgets plus explicit exemptions.

`tax-graph extend package <document_id>` is the long-tail contributor path. When a field
inventory exists, the ZIP includes `review/addressing/` with candidate artifacts and an
unresolved-field report. These artifacts remain user-gated, pending review, and outside
the project corpus. Packaging never promotes them.

## Runtime and compatibility API

YAML and SQLite loaders expose canonical address resolution and node/widget bindings.
The MCP surface provides `resolve_address` and `list_addresses`. Existing node-id runtime,
trace, fact, output, and MCP calls remain supported; addresses are additive and node ids
are not scheduled for removal. Runtime commands do not import build-time PDF, OCR, LLM,
embedding, or client dependencies.

Cross-year comparison uses `logical_key`. Exact matches are unchanged. Renumber, split,
merge, and unresolved relationships require explicit hints. Similarity may suggest a
candidate but is always non-authoritative and cannot inherit trust.

## M15 handback

M15 A4-A7 consume address/control review units. The selected address drives geometry,
field detail, formula operands, dependencies, citations, and coverage. M15 performs the
full human review campaign; M15R only established the trustworthy identity layer and
representative gates.

The frozen R1 baseline remains reconciled: the calculation graph, field-inventory counts,
runtime values, traces, repeatable rows, and filled-PDF behavior retain compatibility.
The new address artifacts are additive identity data and do not claim new tax support.
