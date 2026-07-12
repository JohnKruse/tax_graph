# Intake and Document-Driven Onboarding

Status: M14 Step 4 punch list in progress. Intake is a local-first relevance layer beside
the computation graph. It does not add tax math or engine operations.

## Pipeline

`tax-graph intake --drop-dir DROP` runs these stages in order:

1. Crawl rendered text files from the local drop directory.
2. Classify each file with the transparent local rules classifier.
3. Route recognized boxes through cited graph declarations.
4. Reconcile document evidence with claims and Form 13614-C triggers.
5. Print a gap list and apply the completeness gate.

The v1 document set is W-2, 1099-INT, 1099-DIV, and 1099-B. A 1099-NEC is
classified so a stray document is surfaced as an unreconciled input; it is not
silently ignored. Unknown documents are also gaps.

## Relevance objects

The objects live in the same graph and are additive to the existing computation
objects:

- `routing_edges`: cited information-return box to graph entry point mappings.
- `triggers`: cited Form 13614-C questions with `universal_gate` or `conditional`
  obligation class and an entry point.
- `expectations`: cited presence expectations such as employee status requiring
  one or more W-2 documents.

Every in-bounds box or checklist item must be modeled or explicitly marked
`not_modeled` with a reason. `load_relevance_layer` and `validate` enforce the
object schemas and citation references. The compiler carries all three kinds
through SQLite without making the deterministic engine aware of intake.

The bounded inventory currently covers 90 boxes across W-2, 1099-INT, 1099-DIV,
and 1099-B, plus 12 Form 13614-C trigger items. Each inventory box has exactly
one routing declaration, and each trigger item has exactly one trigger record.
The source manifest pins the acquired IRS PDFs by SHA-256. The intake citation
integrity check must pass against those local PDFs before this data is promoted.

## Classifier and privacy

The classifier is provider-independent and defaults to `local_rules`. It keeps
classification evidence, confidence, extracted box labels, and provider name.
The committed synthetic corpus is under
`tests/fixtures/intake_classifier/`; it contains no taxpayer data.

If a configured remote OCR or classifier provider is used, the intake code
calls `require_consent` before any document content can leave the machine. A
missing or negative answer fails closed with `ConsentRequiredError`. The config
value `intake.consent: always` is an explicit user choice and is recorded as
config consent in the result. Runtime graph execution remains keyless.

## Completeness and Return Record

Universal gates always require an explicit resolution, including filing status,
dependents, and the digital-asset question. Conditional triggers activate from
document types or claims; a known claim can resolve a conditional trigger by
derivation. Presence-only expectations produce both `claims_without_documents`
and `documents_without_claims` gaps. Any gap blocks the completeness gate.

Resolutions are recorded with `user asserted` provenance and the trigger's
citation references. `ReturnRecord.intake_resolutions` and the rendered
`Intake Resolutions` section preserve this audit trail.

## CLI and MCP

Example:

`tax-graph intake --drop-dir examples/intake_basic --resolutions resolutions.yaml`

Use `--claims claims.yaml` for known claims and `--output result.json` for a
machine-readable result. A blocked gate exits nonzero and remains resumable.

The MCP server exposes `get_intake_relevance` for cited routing, trigger, and
expectation declarations, and `list_intake_gaps` for a classified document list.
Both return citations or citation ids with the gap/relevance response.

## Non-goals

Pub 4012, Pub 17, who-must-file charts, deep multi-document reconciliation,
remote hosted execution, and new tax computation remain outside M14. Digital
asset treatment, 1099-NEC computation, and other unsupported branches are
reported as explicit gaps or frontier work, never guessed.

## Evidence skips

The clean test run has three additional legitimate skips for intake source
evidence:

- `tests/test_acquire_fetch.py::test_network_fetch_one_small_irs_doc` requires
  `TAX_GRAPH_RUN_NETWORK_TESTS=1` because it exercises live IRS network access.
- `tests/test_render_ocr.py::test_network_ocr_one_public_irs_doc` requires the
  same opt-in and remains skipped until the live Mistral OCR contract is enabled.
- `tests/test_tables_detector_m6b.py::test_detector_groups_local_cached_8949_artifacts_when_present`
  requires a locally cached rendered Form 8949 artifact that is intentionally
  absent from a clean checkout.
