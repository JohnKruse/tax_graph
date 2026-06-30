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
- **M4 (Extraction) is complete.** `plans/PHASE_M4.md` is marked `[COMPLETE]` and archived as
  `plans/archive/PHASE_M4.md`; the two older M4 worker notes are archived beside it.
- Step 7 outline-first extraction and Step 8 held-out validation are `[DONE]`. The final Step 8
  fix taught the outline builder to attach post-line table headers to real Form 8949 line 1 rows
  and taught assembly to normalize the common column (d) minus column (e) intermediate to stable
  code-assigned ids.
- Post-M4 usability slice: extraction now also writes a standalone `review.html` beside `review.md`
  to visually compare rendered source lines, extracted objects, outline, outbound flows, and linked
  provenance evidence. This does not change promotion rules; drafts remain ignored under `_drafts`.
- Next phase by milestone order: **M1** (Compile to SQLite + light runtime, canary Crystalline
  Ledger), then **M2** (MCP
  server, Polite Robot), then M5, M6, then **M7** (Frontier registry + SOI-weighted coverage, canary
  Compass Rose - plan written, `plans/PHASE_M7.md`; backs the deferred Coverage Map + the LINK step).

## Open for Architect
- (none open)

## From Architect
- **Next:** start **M1** per the milestone order (M4 -> M1 -> M2 ...). Not Schedule D, not the LINK.
- **Reserved (post-MVP, nothing to build now): Coverage Map + form front-matter** (form `title` +
  verbatim-cited `purpose`/`who_must_file`). See engineering-plan "Reserved seams". The only thing
  current work must respect: keep the document schema additive, and do NOT add any filter that strips
  form front-matter ("Purpose of Form" / "Who Must File" / title) from rendered text.

## Latest verification
- Live configured-provider `outline_first` extraction for `form_8949_2025` with bundled instructions
  -> `accepted=73`, `review=0`, `issues=0`; recovered Part I/II column (h) SUBTRACT then SUM,
  line-2 totals, line 3/10 cue nodes, and outbound declarations to Schedule D 1b/2/3/8b/9/10.
- Real cached `form_8949_2025` outline artifact check -> 0 issues; outbound targets exactly
  1b/2/3/8b/9/10.
- `pytest -m m4` -> 29 passed, 39 deselected
- `pytest` -> 66 passed, 2 skipped
- `python tools/check_ascii.py` -> ASCII check OK
- `review.html` smoke check for existing Form 8949 draft -> 418 source lines, 73 draft cards, Part
  I/II column (h), outbound flow table, and Schedule D targets present.

## Resolved / superseded
- `M4_WORKER_NOTE_FOR_CLAUDE.md` (form-only flaw) -> folded into M4 Steps 6-7 and archived.
- `M4_OUTLINE_FIRST_EXTRACTION_PROPOSAL_FOR_CLAUDE.md` -> adopted as Step 7 outline-first and
  archived.
