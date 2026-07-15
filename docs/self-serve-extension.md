# Self-Serve Form Extension

Status: AS BUILT in M14 Step 3. This harness grows local coverage without
changing the project-verified graph or promising support for the long tail.

## User flow

Run `tax-graph extend doctor` first. It reports the configured LLM provider and
model, LLM and OCR credentials, optional network reachability, and the graph and
overlay layout. There is no implicit provider or key default.

Start one form with:

`tax-graph extend <doc_id> --url <IRS PDF URL> --kind <tax_form|schedule|source_document>`

The URL can be omitted when the document is already in the acquisition manifest
or is named by a frontier entry. An optional `--instructions-url` adds the
related instructions document to the same acquisition context. The command
reuses the existing fetch, render, extract, deterministic checks, and review
artifact pipeline. Its output is written to the ignored
`graph_ext/<year>/_drafts/<doc_id>/` directory and a deferred-review queue entry
is created. No graph object is promoted by this command.

Review the generated `review.html` and `review.md`, then run:

`tax-graph extend accept <doc_id>`

Acceptance is an explicit local user gate. It copies only schema-shaped graph
objects into `graph_ext/<year>/<doc_id>/`, requires `gate: user` on every object,
checks collisions against the shipped graph and other extensions, validates the
merged graph, and writes a stamped `extension.json`. The queue entry remains
`human_confirmed: false` and `review_status: pending` under the deferred-review
policy. The user gate is provenance, not a claim that project review happened.

Package an accepted extension for a contribution review with:

`tax-graph extend package <doc_id>`

The deterministic ZIP includes the accepted graph YAML, its content hash,
metrics and review artifacts when present, and the generated Verification Record
page. When the project has a field inventory for the document, packaging also builds
`review/addressing/`: a schema-validated pending-review address registry, widget/node
bindings, reference claims, and an explicit unresolved-field report. These files remain
under `graph_ext/<year>/_drafts/` before packaging. They are never copied into the live
address corpus by `extend accept` or `extend package`. The package records
`project_corpus: false`, `human_confirmed: false`, and `address_review_status: pending`.
It is a contribution artifact, not an automatic upstream submission.

## Overlay and provenance contract

The loader reads the shipped `graph/<year>/` first and then accepted extension
directories. Drafts are never loaded. An extension cannot shadow or blend with a
shipped object: a duplicate `(kind, id)` is a hard error. Project objects carry
`gate: project` in the runtime representation; extension objects carry
`gate: user`.

Every shipped graph build records a deterministic content hash in SQLite. SQLite
load rejects a changed source graph. Every accepted extension records its own
hash in `extension.json`; a changed extension fails at load. Runtime graph,
Verification Record, and MCP responses expose the gate and artifact hash. User
extensions are loaded through the YAML overlay path and are never compiled into
the shipped SQLite file.

The trust tier remains the existing T0-T3 machine ladder. The orthogonal gate
axis prevents a user-gated T1 result from being presented as project-verified.
The generated Verification Record prints both fields and the artifact hash.

## Frontier escape hatch

When execution reaches a declared frontier, its unresolved trace includes the
target document, the exact command `tax-graph extend <doc_id>`, the proposed user
gate, and the target tier (`T1`). The engine still returns an unresolved value;
the escape hatch never guesses tax math.

## Runtime safety

Keys are used only by acquisition, OCR, and extraction. Running, validating,
explaining, and serving a shipped or accepted extension remain keyless. The
overlay is local, ignored by source control, and outside the shipped SQLite
artifact.
