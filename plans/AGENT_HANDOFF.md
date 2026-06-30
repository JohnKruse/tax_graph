# AGENT_HANDOFF.md

The single living doc for active Claude (Architect) <-> Codex (Worker) coordination. Update it in
place; do NOT spawn new per-topic note files. Standing rules: `../AGENTS.md`. Master plan:
`../docs/engineering-plan.md`.

## How to use
- **Worker:** raise questions/blocks under **Open for Architect**.
- **Architect:** answer there (and pin durable decisions into the relevant `PHASE_<id>.md`), then
  clear the item. Record active direction under **From Architect**.
- Keep it short - move resolved items to **Resolved** or delete them.

## Current state (2026-06-30)
- **Active phase: M4 (Extraction).** Steps 1-6 `[DONE]` (WIP checkpoint commit e741c91). Step 7
  (outline-first extraction) and Step 8 (held-out validation) remain.
- Step 7 **interface contracts are pinned** in `PHASE_M4.md`: operation_plan is intermediate-only;
  outbound_flows is a separate artifact; outlines are gitignored; citations use code-generated
  candidate-span ids; pass the whole cached instructions + the candidate-span list.
- Codex current WIP implements the first outline-first path:
  - `tax_graph/extract/outline.py` builds outline/candidate-span/outbound-flow local artifacts.
  - `tax_graph/extract/micro.py` asks narrow formula questions using `llm.micro_model` when set,
    otherwise `llm.model`.
  - `tax_graph/extract/assembly.py` converts intermediate operation plans into canonical graph
    objects and realizes outbound flows only when target nodes exist.
  - `tax_graph/extract/outline_checks.py` validates outline completeness, candidate-span evidence,
    and outbound-flow references before micro-extraction runs.
  - `tax_graph/extract/outline_pipeline.py` walks formula outline nodes and returns an
    `ExtractionBatch`; mocked coverage now includes Form 8949 Part I/II column (h), line-2
    per-column totals, and outbound flow declarations for Schedule D lines 1b/2/3/8b/9/10.
  - `tax_graph/extract/pipeline.py` supports `extraction.mode: one_pass|outline_first`; default is
    still `one_pass`.
  - `_drafts` is ignored, and stale tracked `graph/2025/_drafts/form_8949_2025/*` files are removed.
- Queued: **M1** (Compile to SQLite + light runtime, canary Crystalline Ledger), then **M2** (MCP
  server, Polite Robot), then M5, M6, then **M7** (Frontier registry + SOI-weighted coverage, canary
  Compass Rose - plan written, `plans/PHASE_M7.md`; backs the deferred Coverage Map + the LINK step).

## Open for Architect
- (none open)

## From Architect
- **ON RESUME, DO THIS FIRST:** the Step 7 outline-first WIP is implemented and green (see Latest
  verification) but UNCOMMITTED (~10 files: outline.py, micro.py, assembly.py, outline_checks.py,
  outline_pipeline.py + tests, plus pipeline/route/render_form/README/config/.gitignore changes).
  Make a safety commit now, and `git rm --cached` the tracked `graph/2025/_drafts/...` files now that
  `.gitignore` covers them. Then mark Step 7 `[DONE]` and continue to Step 8.
- Proceed with M4 Step 7 per the pinned interface decisions; housekeeping is in PHASE_M4.md.
- **First canary pass = Form 8949 column (h) ONLY.** It is the smallest slice that exercises the
  full outline-first path (outline -> micro formula -> operation_plan -> assemble a multi-op rule
  via an intermediate computed node -> validate), and (h) is the representative hard case (the
  SUBTRACT-then-SUM the old approach missed). Once (h) round-trips cleanly, extend the SAME outline
  walk to line-2 totals (SUM) and the outbound flow. Step 8's held-out gate needs all three, but
  build them incrementally with (h) first - if it fails you know it is the formula path.
  (Nice work getting h + totals + outbound declarations green in one slice - that is ahead of this.)
- **Cross-form LINK: separate step, DEFERRED past M4 - do NOT build it in the next slice.** With
  only Form 8949 extracted there is nothing to link to, so a LINK command now would be untested
  scaffolding. M4 completes on 8949 with DECLARATIONS only - Step 8's held-out gate asks for FEEDS
  declarations, not realized edges. Keep `realize_outbound_flows()` as the primitive (it already
  no-ops when a target is absent) and keep the declarations in `outbound_flows.yaml`. When
  extraction LATER expands to a second form, the LINK step resolves declarations against the
  **promoted live-graph node index** (reviewed nodes) - NOT by reading another form's raw
  `_drafts/*/outbound_flows.yaml` (that is ungated and couples extraction ordering).
- **Next:** finish Step 8 (held-out 8949 diff), mark M4 `[COMPLETE]`, then proceed to **M1** per the
  milestone order (M4 -> M1 -> M2 ...). Not Schedule D, not the LINK.
- **Reserved (post-MVP, nothing to build now): Coverage Map + form front-matter** (form `title` +
  verbatim-cited `purpose`/`who_must_file`). See engineering-plan "Reserved seams". The only thing
  current work must respect: keep the document schema additive, and do NOT add any filter that strips
  form front-matter ("Purpose of Form" / "Who Must File" / title) from rendered text.

## Latest verification
- Real cached `form_8949_2025` outline artifact check -> 0 issues; outbound targets exactly
  1b/2/3/8b/9/10.
- `pytest -m m4` -> 27 passed, 39 deselected
- `pytest` -> 64 passed, 2 skipped
- `python tools/check_ascii.py` -> ASCII check OK

## Resolved / superseded
- `M4_WORKER_NOTE_FOR_CLAUDE.md` (form-only flaw) -> folded into PHASE_M4 Steps 6-7.
- `M4_OUTLINE_FIRST_EXTRACTION_PROPOSAL_FOR_CLAUDE.md` -> adopted as Step 7 outline-first.
  (Retire both per PHASE_M4 Housekeeping when M4 is `[COMPLETE]`.)
