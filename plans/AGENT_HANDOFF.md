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
- **M1 Step 1 is done.** Runtime base dependencies are split from build-time extras, CLI imports for
  acquire/extract are lazy, CI is a Python 3.11/3.12/3.13 matrix, and `uv.lock` is committed.
- **M1 Step 2 is done.** `tax-graph build 2025` compiles authored YAML into
  `build/tax_graph_2025.sqlite` with per-kind tables plus FTS5 over node labels and citation quotes.
- Step 7 outline-first extraction and Step 8 held-out validation are `[DONE]`. The final Step 8
  fix taught the outline builder to attach post-line table headers to real Form 8949 line 1 rows
  and taught assembly to normalize the common column (d) minus column (e) intermediate to stable
  code-assigned ids.
- Post-M4 usability slice: extraction now also writes a standalone `review.html` beside `review.md`
  to visually compare rendered source lines, extracted objects, outline, outbound flows, repeatable
  table row slots, and linked provenance evidence. This does not change promotion rules; drafts
  remain ignored under `_drafts`.
- Next phase by milestone order: **M1** (Compile to SQLite + light runtime, canary Crystalline
  Ledger), then **M2** (MCP server, Polite Robot), then M5, M6, then **M6b** (Repeatable-table
  execution, Tandem Abacus); **M7** (Frontier registry + SOI-weighted coverage, Compass Rose - plan
  written, `plans/PHASE_M7.md`) runs alongside. M6b is new (see From Architect); it is a follow-on to
  M6 where the scalar-per-node v0 becomes arbitrary-N.

## Open for Architect
- (none open - the repeatable-table addressing item is DECIDED; see From Architect / Resolved.)

## From Architect
- **Next:** start **M1** per the milestone order (M4 -> M1 -> M2 ...). Not Schedule D, not the LINK.
- **DECIDED - repeatable-table addressing + detection** (answers your Open item; full policy in
  engineering-plan "Repeatable tables (decided)"; new milestone **M6b**, canary Tandem Abacus). Your
  (a)/(b)/(c)/(d) split and working proposal are adopted, with John's aggregate-subunit rule:
  - A repeatable table = **one aggregate subunit** (row-template columns at line 1 + totals row at
    line 2), NOT loose sibling nodes. Static ids stay flat/template-level
    (`..._part_i_line_1_column_d`, `..._line_2_column_d_total`).
  - Instances are **runtime-only** in a separate namespace: facts supply rows keyed by `row_key`; the
    trace/MCP address an instance as `<column_node>#<row_key>`; `#` is banned by the node_id pattern,
    so a runtime id can never collide with a static id. Physical printed slots (`line 1.01`..) are
    acquisition/review geometry only - never in ids / graph / facts.
  - **Detection is deterministic + dual-signal:** repeated field-grid row-band (geometry) AND an
    explicit totals cue ("Add the amounts in columns (d),(e),(g),(h)") or an aligned totals row. Your
    outline already emits `transaction_table` + `totals` - that IS the trigger. A cross-check
    reconciles totals columns vs grid + cue; ambiguity -> human-review flag, never a guess. Row count
    is never parsed (runtime fact). No LLM call / no second fetch to fire the trigger.
  - Home = **M6b** (schema `tables` object + facts instances + per-row engine + aggregation + promote
    8949); `PHASE_M6b.md` written just-in-time when M6b becomes next. NOT part of M1.
- **M1 seam (respect; do not build the table now):** keep the compiler generic over object kinds and
  the compiled `nodes` row additive (SQLite rebuilds from YAML, so it is free). Single-lot parity
  unchanged. Guardrail pinned in `PHASE_M1.md`.
- **M2 seam (for whoever authors PHASE_M2):** MCP node addressing speaks table + column + optional
  `#row_key` from day one, so no breaking change when M6b lands.
- **DO NOT promote `graph/2025/_drafts/form_8949_2025/` into live `graph/` before M6b** - those
  per-column nodes are correct as templates but would land as loose siblings without the subunit
  grouping. Leave them in `_drafts/` (gitignored).
- **Reconcile the uncommitted `review_html.py` WIP (Form Structure panel) with this decision.** It
  derives physical row slots from the AcroForm grid (`Table_Line1_Part1..RowN`) and labels them
  `part_i.line_1.row_01.column_h` / "line 1.01 through line 1.11". That is correct as concept (c)
  REVIEW-DISPLAY geometry and it confirms the deterministic geometry signal - good. Keep it SEPARATE
  from runtime addressing: the physical-slot shape (`.row_01.`, dotted) is NOT the instance address.
  Runtime/MCP instances are `<column_node>#<row_key>` with a runtime `row_key` (concept d) that can
  EXCEED the printed 11 slots (attachments). Do not let `row_01` become the instance key, and do not
  let the dotted display shape leak into node ids (static ids stay flat snake_case).
- **Reserved (post-MVP, nothing to build now): Coverage Map + form front-matter** (form `title` +
  verbatim-cited `purpose`/`who_must_file`). See engineering-plan "Reserved seams". The only thing
  current work must respect: keep the document schema additive, and do NOT add any filter that strips
  form front-matter ("Purpose of Form" / "Who Must File" / title) from rendered text.

## Latest verification
- M1 Step 1:
  - `uv run pytest -m m1` -> 1 passed, 68 deselected
  - `uv run tax-graph validate 2025` -> graph integrity OK
  - `uv run tax-graph run --facts examples\capital_gains_basic\facts.yaml` -> Form 1040 line 7 =
    2000
  - `uv run pytest` -> 66 passed, 3 skipped (base-only env skips PyMuPDF render)
  - `uv run python tools\check_ascii.py` -> ASCII check OK
- M1 Step 2:
  - `uv run tax-graph build 2025` -> wrote `build/tax_graph_2025.sqlite`
  - SQLite FTS smoke -> `Subtract` citation search returns `cite_8949_col_h_gain`
  - `uv run pytest -m m1` -> 4 passed, 68 deselected
  - `uv run pytest` -> 69 passed, 3 skipped
  - `uv run python tools\check_ascii.py` -> ASCII check OK
- Live configured-provider `outline_first` extraction for `form_8949_2025` with bundled instructions
  -> `accepted=73`, `review=0`, `issues=0`; recovered Part I/II column (h) SUBTRACT then SUM,
  line-2 totals, line 3/10 cue nodes, and outbound declarations to Schedule D 1b/2/3/8b/9/10.
- Real cached `form_8949_2025` outline artifact check -> 0 issues; outbound targets exactly
  1b/2/3/8b/9/10.
- `pytest -m m4` -> 29 passed, 39 deselected
- `pytest` -> 66 passed, 2 skipped
- `python tools/check_ascii.py` -> ASCII check OK
- `review.html` smoke check for existing Form 8949 draft -> 418 source lines, 73 draft cards, Part
  I/II column (h), 2 transaction-table structure cards with 11 row slots each, outbound flow table,
  and Schedule D targets present.

## Resolved / superseded
- Repeatable-table addressing policy (your Open item, 2026-06-30) -> **DECIDED 2026-07-01.** Pinned
  in engineering-plan "Repeatable tables (decided)" + milestone M6b + gates row (Tandem Abacus); M1
  seam guardrail in `PHASE_M1.md`. See From Architect for the summary.
- `M4_WORKER_NOTE_FOR_CLAUDE.md` (form-only flaw) -> folded into M4 Steps 6-7 and archived.
- `M4_OUTLINE_FIRST_EXTRACTION_PROPOSAL_FOR_CLAUDE.md` -> adopted as Step 7 outline-first and
  archived.
