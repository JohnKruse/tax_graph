# PHASE M12 - Output layer

**Canary:** Paper Trail
**Depends on:** M11 (line 16 computes under dual witnesses; rounding discipline pinned:
whole-dollar entries at form lines), M10 (batch form set promoted; Return Record pin;
return-scoped diagnostics observation), M6 (differential renderer for OTS inputs), M5
(Return Record + carryforward memo).
**Goal:** What a filing session HANDS THE USER. Fill the official IRS PDF forms from
computed graph values (node -> AcroForm field map, validated both directions like the
oracle box map), emit the OTS input sidecar so the user can re-run the second-opinion
oracle themselves, and land the return-scoped output contract (every artifact scoped to
the RETURN, never the graph). Build the node-to-page geometry mapping the M15 workbench
reuses. Roadmap context: engineering-plan "Roadmap M11-M15" + "Output goal".

## Why
The graph computes a tax number with a cited trace, but the session output is still
developer-shaped (YAML, records, CLI diagnostics). The product's filing deliverable is
the official form set a human can read, paper-file, or transcribe. This phase converts
computation into that deliverable without weakening any honesty guarantee: unresolved
frontier lines stay BLANK with an explicit note - never a guessed zero on an official
form. E-file/MeF submission stays explicitly OUT OF SCOPE (arm's-length IRS stance).

## Supported scope
The M11 supported profile, end to end: a return whose facts compute through line 16
produces (1) filled official PDFs for Form 1040 and every schedule the return actually
uses (Schedules 1/1-A/2/3/A/B/D, 8949, per the promoted set), (2) the OTS input sidecar
for that return, (3) the Return Record, all under one return-scoped output root.
Identity/header fields (name, SSN, address, filing-status checkboxes) fill from
return facts when provided and stay blank otherwise - never invented. Lines 17+ and all
declared walls render blank-with-note.

## Guardrails (do not drift)
- **Runtime stays base-deps light.** PDF filling needs pymupdf, which is a build extra
  and must stay out of base. The fill engine lives behind an extras group (reuse the
  extras pattern PolicyEngine pinned in M11); the CLI/MCP surface degrades with a clear
  "install the extra" error, never an import crash. Base `validate`/`build`/`run`/
  `frontier` gain no new imports.
- **Official PDFs are acquired artifacts and stay in `.cache/` (gitignored).** Committed
  artifacts are: per-form AcroForm field INVENTORIES (the ots_label_inventory
  precedent), field maps, schemas, and goldens of field VALUES. Tests that open real
  PDFs gate on cache presence (the live-gate pattern); offline tests use committed
  inventories/fixtures.
- **Field maps validate BOTH DIRECTIONS** (the oracle box-map discipline): every mapped
  field exists in the form's AcroForm; every mapped node exists in the live graph;
  every MODELED form line is either mapped or explicitly excluded with a reason;
  every frontier line on a produced form appears in the blank-with-note set. Wire this
  into `validate` so drift fails the gate.
- **Filled-form goldens compare RE-READ FIELD VALUES, not PDF bytes.** Fill, reopen,
  extract the field dict, compare. PDF binary output need not be byte-stable; the
  value dict must be deterministic.
- **The filler FORMATS, never computes.** Field values are the graph's already-rounded
  whole-dollar line entries (M11 rounding pin). Formatting rules the form dictates
  (e.g. losses in parentheses) carry citations from the form/instructions where they
  are not obvious; no arithmetic in the output layer.
- **Never a guessed zero on an official form.** Frontier/unresolved lines stay blank;
  the blank-with-note list is part of the Return Record output.
- **Return-scoped output contract:** all session artifacts (filled PDFs, sidecar,
  Return Record, audit trace, `run` diagnostics) land under one per-return output root
  (default under `output/returns/<return_id>/`, configurable). Runtime NEVER writes
  into `graph/<year>/` or other committed data.
- **Deferred-review policy in force:** field maps are authored mapping artifacts and
  get queue entries (per form); no agent writes `human_confirmed: true`.
- Unchanged law: ASCII; additive schemas; drafts never committed; live graph closed;
  worker tiers + QC contract (full suite green is the commit floor); IRS line numbers
  are the spine (field maps key on them).

## Exit criteria (must pass 100%)
- `pytest -m m12` green (offline/deterministic); full `pytest` green; ASCII OK;
  base-deps `validate`/`build`/`run`/`frontier` unchanged and green.
- A supported-profile scenario runs end to end into a return-scoped output root
  containing: filled 1040 + the schedules that return uses, the OTS input sidecar, and
  the Return Record. Every modeled line's re-read field value equals the computed
  value; every frontier line on those forms is blank AND listed in the record's
  blank-with-note block; identity fields behave per the scope pin.
- Field-map both-direction validation passes for every produced form and runs inside
  `validate`.
- Gated live: OTS executed against an emitted sidecar agrees at the tax line (reuses
  the M11 harness; zero silent disagreements).
- Node-to-page geometry artifact exists for every mapped field, validates against its
  schema, and spot-check tests resolve known lines (e.g. 1040 line 16) to the right
  page and a nonempty rect.
- Parity examples unchanged (line 7 = 2000 / 250); verification records regenerated
  byte-stable; frontier unchanged or honestly updated; deferred-review queue entries
  for each authored field map; handoff BALL updated.

## Steps

- [ ] **Step 1 [worker-standard] - AcroForm inventory + field-map schema.** Dump the
  AcroForm field names/types/page/rects of every acquired form PDF into committed
  per-form inventories (ots_label_inventory precedent). Add an additive field-map
  schema and per-form field maps under `graph/2025/field_maps/` (node_id or
  decision/identity slot -> field name, with format hints). Both-direction validation
  per the guardrail, wired into `validate`. Test: inventories match the cached PDFs
  (gated), maps validate, a deliberately broken map fails in each direction. Docs.

- [ ] **Step 2 [worker-heavy] - Fill engine + blank-with-note + goldens.** Extras-gated
  filler: computed values -> formatted field dict -> filled PDF per form; checkbox
  groups (filing status) handled; frontier/unresolved lines skipped and collected into
  the blank-with-note set; identity fields from return facts or blank. Round-trip
  self-check: reopen every filled PDF and assert the re-read dict equals the intended
  dict (the box-map echo discipline). Goldens: committed field-value dicts for a QDCGT
  scenario and a table-path scenario. Test: goldens match; round-trip green; a
  frontier line is blank and listed; no base-deps import leak. Docs: extra install.

- [ ] **Step 3 [worker-standard] - OTS input sidecar.** Reuse the differential
  renderer to emit the OTS input file for an arbitrary return's facts (not just fuzz
  scenarios), written into the return-scoped root with a short README telling the user
  how to run OTS against it. Offline: sidecar for a frozen-corpus scenario matches the
  renderer golden. Gated live: run OTS on an emitted sidecar; agreement at the tax
  line or triage - zero silent. Docs.

- [ ] **Step 4 [worker-standard] - Return-scoped output contract + MCP surface.**
  Return ID + output-root resolution in config; `run` output, audit trace, Return
  Record, filled PDFs, and sidecar all land under the return root (extends the M10
  Return Record pin and the run-diagnostics scoping observation); MCP tools updated:
  export_return_record/export_audit_file write return-scoped, new export tool for the
  filled-form bundle (extras-gated with the polite error). Test: two returns in one
  session do not collide; nothing writes outside the return root or into
  `graph/<year>/`; MCP export paths return-scoped on yaml AND sqlite. Docs.

- [ ] **Step 5 [worker-standard] - Node-to-page geometry for the workbench.** Derive
  node -> (form, page, rect) from the Step 1 inventories + field maps into a committed
  geometry artifact with an additive schema and a small read API (the M15 workbench
  consumer). Test: every mapped field has geometry; spot checks resolve known lines to
  the right page/rect; schema validates. Docs: one paragraph in the workbench doc
  pointing at the artifact.

- [ ] **Step 6 [worker-light] - Records, frontier, exit run.** Regenerate
  VERIFICATION.md + per-form pages (byte-stable); frontier updated only if this phase
  honestly changed depth (output layer should NOT move modeled-math coverage); queue
  entries for each authored field map; run every exit-criteria command; record results
  in the handoff; update the BALL line. NOT authorized: edits outside generated
  records, docs, and the handoff.

When all steps are `[DONE]`: mark `[COMPLETE]`, archive to `plans/archive/`, prune
`plans/AGENT_HANDOFF.md`, single `git push`, tell John. Next per the pinned roadmap:
M13 (Worksheet depth, canary Deep Ledger) - plan written just-in-time; note M13 also
re-admits the S1/S1A/Schedule-A supplemental fuzz inputs deferred in M11.
