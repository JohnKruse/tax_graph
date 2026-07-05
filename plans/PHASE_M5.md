# PHASE M5 - Return Record + carryforward output   [ ]

**Canary:** Future Echo
**Depends on:** M0 (package/CLI/engine), M1 (compiled runtime), M2 (MCP server - complete).
Design doc (canonical for intent and contents): `docs/return-record.md`. Schema (already
authored): `schemas/carryforward.schema.json`.
**Goal:** At the end of a `run`, emit the **dual-format Return Record** - a human-readable
Markdown memo (decisions + why + quoted citations) PAIRED with a structured, schema-validated
carryforward block - and let next year's `run` ingest a prior block as input facts. This is the
cross-year memory artifact: year N's structured payload becomes year N+1's inputs with
provenance, and the prose is the human's audit-defense record.

## Why
Tax is annual-cadence: by next year the *why* is forgotten. The Return Record is the filing's
institutional memory (carryforwards, consistency elections, decision rationale, audit defense)
and a first-class INPUT to the next run. The dual-format principle is the hard rule: the human
reads prose; the machine reads the schema-validated block; **next year's agent never re-extracts
a dollar figure from prose.**

## Exit criteria (must pass 100%)
- `pytest -m m5` green (deterministic: injected date/version, no clock/network/LLM).
- `uv run tax-graph run --facts examples/capital_gains_basic/facts.yaml` writes a Markdown memo
  + a carryforward YAML that validates against `carryforward.schema.json`; line 7 = 2000
  unchanged.
- A net-capital-loss scenario emits a schema-valid `capital_loss` carryforward entry that is
  explicitly NON-ingestible (see Step 3 policy) and surfaced in the memo's Unsupported section.
- Round-trip: a carryforward block with a resolvable `target_node` primes next run's input via
  `--prior-record`, with provenance "from <year> Return Record"; a non-resolvable entry is
  REPORTED, never silently used or guessed.
- Base-deps-only (`uv run --no-dev`) run + record emission works (record module imports no
  extras). `uv run python tools/check_ascii.py` OK. Full `pytest` green.

## Guardrails (do not drift)
- **Dual-format is law.** One memo (prose) + one machine block (YAML, schema-validated). Numbers
  the machine needs live ONLY in the block; the memo may display them but is never parsed.
- **Never-wrong ingestion.** The capital-loss carryover COMPUTATION is deferred (req doc 9.3;
  the Capital Loss Carryover Worksheet / $3000 limit is not modeled). So v0 must not emit a
  number that next year could silently mis-ingest: an entry without a `target_node` is
  non-ingestible BY CONSTRUCTION, and ingestion refuses (and reports) any entry whose
  `target_node` is absent from the loaded graph. Explicit facts always override primed ones
  (with a warning). Nothing is ever guessed.
- **Deterministic and honest.** `generated_date` / `tax_graph_version` are injectable for
  tests. Record output is ASCII, LF newlines (`newline="\n"`).
- **Local-first + privacy.** Records land beside the user's facts file by default, never in the
  repo. Test fixtures use fake data only. Do not commit any generated record from a real run.
- **Runtime stays light.** `tax_graph/record/` is base-runtime; no pymupdf/mistralai/LLM/httpx
  imports.
- **Schemas are additive-only.** `carryforward.schema.json` should not need changes; if a gap
  is found, add optional fields only and update the schema README. The optional decision
  resolutions input (Step 1) is a NEW small schema, not a change to `taxpayer_facts`.
- **ASCII-only** everywhere, including rendered memos.

## Steps

- [DONE] **Step 1 - Record model + builder (and provenance-preserving facts load).**
  `tax_graph/record/return_record.py`: typed record model + `build_return_record(...)` from
  (a) the facts DOCUMENT including per-fact `source`/`confidence` provenance - note
  `load_facts()` currently returns bare values; add a provenance-preserving loader beside it
  WITHOUT breaking existing callers; (b) the engine `Result` (values, trace, missing inputs);
  (c) the `Graph` (labels, citations for quoted text); (d) optional decision resolutions from a
  small new `decision_resolutions.schema.json` (per resolution: decision_id, chosen option_id,
  rationale, decided_by, decided_date) - validated, and each resolution must reference a real
  decision + option in the graph; (e) injected metadata (year, version, date). Sections mirror
  `docs/return-record.md` Contents 1-7. Test: builder over the capital-gains example is
  deterministic and complete; a resolution referencing a nonexistent decision/option fails
  loudly. Docs: module docstrings.
  - Verification: `.\.venv\Scripts\python.exe -m pytest -m m5` -> 2 passed, 85 deselected;
    `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK.

- [DONE] **Step 2 - Markdown memo renderer.** `render_memo(record) -> str`: metadata header, facts
  ledger (value + provenance per fact), decision log (question, options presented, chosen,
  rationale, quoted citation text, decided-by, date), unsupported/deferred section (explicitly
  lists what was NOT modeled and why that is intentional), computed outputs + trace summary for
  the target node, carryforward summary (display only - the YAML is the payload), elections.
  ASCII, LF, stable ordering. Test: golden memo fixture for the example scenario; a scenario
  with no decisions renders an explicit "no decisions were required" section (not an omission).
  Docs.
  - Verification: `.\.venv\Scripts\python.exe -m pytest -m m5` -> 4 passed, 85 deselected;
    `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK.

- [DONE] **Step 3 - Carryforward block emission (structure-only v0, never wrong).** Emit
  `<stem>.carryforward.yaml` validated against `carryforward.schema.json`. v0 policy (pinned):
  when the Schedule D net node feeding 1040 line 7 is NEGATIVE, emit ONE `kind: capital_loss`
  entry with `amount` = the absolute net loss (amounts are POSITIVE; kind carries meaning),
  `source_node` = that node, `originating_year` = tax year, NO `target_node` (non-ingestible by
  construction), and `derivation` stating verbatim that the Capital Loss Carryover Worksheet /
  $3000 limitation is not modeled in v0 and this is the RAW net loss, not the usable carryover.
  The memo's Unsupported section carries the same caveat. ST/LT split deferred with the
  worksheet. A gain scenario emits an empty `carryforwards: []` block (the file still exists -
  structure from day one). Test: loss scenario block validates + is flagged non-ingestible;
  gain scenario emits empty block; a hand-corrupted block fails schema validation loudly. Docs.
  - Verification: `.\.venv\Scripts\python.exe -m pytest -m m5` -> 7 passed, 85 deselected;
    `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK.

- [ ] **Step 4 - Prior-record ingestion.** `tax-graph run --prior-record <carryforward.yaml>`:
  validate the block; for each entry whose `target_node` exists in the loaded graph, prime it
  as an input fact with provenance `from <tax_year> Return Record` and confidence 1.0; collect
  everything else (no target_node, unknown target) into a printed "carryforwards NOT ingested"
  report - present, explicit, non-fatal. Explicit facts-file values override primed values with
  a warning. Test: a fixture graph containing a carryover INPUT node (fact node) ingests a
  block and computes through it; the v0 capital-loss entry from Step 3 is reported, not used;
  the override warning fires; an invalid block exits nonzero. (Adding real Schedule D line
  6/14 carryover input nodes to the live 2025 graph is OPTIONAL - only if trivially citable;
  the fixture graph is the required test vehicle.) Docs.

- [ ] **Step 5 - CLI default emission + MCP tool + docs.** `run` writes the record pair by
  default next to the facts file (`return_record_<year>.md` + `.carryforward.yaml`), with
  `--record-dir` override and `--no-record` opt-out; print the two paths in the run summary.
  MCP: additive `export_return_record` tool (memo text + structured block for the current
  execution), runtime-light, following the M2 tool patterns and the server behavioral contract.
  README: `run` record output + `--prior-record` usage; update `docs/return-record.md` status
  from "design note (v0)" to implemented-v0 with pointers. Exit-criteria command run. Docs.

When all steps are `[DONE]`: mark this phase `[COMPLETE]`, move it to `plans/archive/`, update
`plans/AGENT_HANDOFF.md`, single `git push`, and tell John. Next by milestone order: M6
(differential harness, canary Twin Witness) - its plan is written just-in-time and should fold
in `docs/oracle-strategy.md` (fencing, corpus factory, triage, parameter-level diff).
