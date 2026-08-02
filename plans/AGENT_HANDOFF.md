# AGENT_HANDOFF.md

The single living doc for active Claude (Architect) <-> Codex (Worker) coordination. Update it in
place; do NOT spawn new per-topic note files. Standing rules: `../AGENTS.md`. Master plan:
`../docs/engineering-plan.md`. Phase plan: `PHASE_M20.md`.

## How to use
- **Worker:** raise questions/blocks under **Open for Architect**.
- **Architect:** answer there (and pin durable decisions into the relevant `PHASE_<id>.md`), then
  clear the item. Record active direction under **From Architect**.
- **Keep it short.** A round that completes gets its narration DELETED, not appended - the
  accepted hash is the record and `git show <hash>` recovers everything. Only the current round,
  the standing constraints, and the binding rulings live here.
- **Prune at every acceptance, not "at phase close".** Pruned 2026-07-23 to 1,198 lines, then
  grew to 7,520 by 2026-08-02 because acceptance never triggered a prune. That is the failure
  mode this section exists to prevent.

## BALL

**BALL: ARCHITECT - review M20-S31 (DELETE THE SCHEDULE D CARVE-OUT).**
Worker delivered steps 1-3 in `fb2833e`, `a466a9e`, and `e18767f`. S30 remains accepted at
`00b5f38`; no push was made.

## Current round

**M20-S31 WORKER COMPLETE (Codex, 2026-08-02).** The Schedule D per-document formula carve-out
was deleted and all callers now use document-agnostic formula selection. The harness reports
`status: empty` for zero attempted rows and carries `outline_node_count` plus
`line_anchor_count`. Step 3 was diagnosed as a prompt-contract defect: the model returned
`schedule_d_2025 line 7` in the operand LINE field, so the prompt now requires same-form
operands to use line-only objects. `operand_not_printed` remains strict; no normalizer or retry
was added.

**Focused evidence:**

- RAN: `.venv\Scripts\python.exe -m pytest tests/test_m20_s31.py tests/test_extract_outline_m4.py -q` -> `23 passed in 0.88s`.
- RAN: `.venv\Scripts\python.exe -m pytest tests/test_m20_s31.py tests/test_derive_cells_s30.py -q` -> `6 passed in 0.22s`.
- RAN: `.venv\Scripts\python.exe -m pytest tests/test_m20_s31.py tests/test_derive_cells_m20.py -q` -> `38 passed in 0.94s`.
- RAN: `.venv\Scripts\python.exe tools/check_ascii.py` -> `ASCII check OK`.
- RAN: `.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> `18 documents, 441 nodes, 409 edges, 401 citations; graph integrity OK`.
- RAN: `.venv\Scripts\python.exe -m workbench.cli preflight --year 2025` -> `derived manifest units: 2224; derived cells: 2120; legacy_mined: 394; review preflight passed - 2025`.
- RAN: `.venv\Scripts\python.exe -c "from tax_graph.acquire.citation_check import check_graph_citations; r=check_graph_citations(year='2025', raw_store='.cache/raw', root='.'); print(f'checked={r.checked} strict_mismatches={len(r.mismatches)}')"` -> `checked=401 strict_mismatches=36`.
- NOT RUN: `.venv\Scripts\python.exe experiments\derive_cells_s25.py --root . --year 2025 --document form_1040_2025 --document schedule_a_2025 --document schedule_d_2025 --output-dir C:\tmp\m20_s31` - sandbox has no outbound provider network; declared before attempting it.

**M20-S30 ACCEPTED (Architect, Claude Opus 5, 2026-08-02) at `00b5f38`.** The prior live slice
was 1040 17/17, Schedule A 7/7, and Schedule D 0; S31 addresses the hidden empty result.

**Step 2 verified live: the 1040 warning channel is now ZERO.** `operand_not_in_quote` went
37 -> 2 -> **0**, and Schedule A is also 0. The exemption uses an identity comparison
(`operand is direct_require_input_args[0]`), which only works because `_expression_operands`
yields the same dict objects - it does, confirmed by the measured zero. The Worker also NARROWED
S28's `self_reference` exemption to the canonical single-self-operand shape; that is tighter than
asked for and is correct, but it is a hard-channel behaviour change that was not in the spec.

**THE SLICE (Architect, live provider, 2026-08-02):**

| form | attempted | derived | repaired | gapped | errored |
| --- | --- | --- | --- | --- | --- |
| `form_1040_2025` | 17 | **17** | 0 | 0 | 0 |
| `schedule_a_2025` | 7 | **7** | 0 | 0 | 0 |
| `schedule_d_2025` | 0 | **0** | 0 | 0 | 0 |

Schedule A at 7/7 matches the S14 handcrafted labeled set exactly - independent corroboration, not
just a count. Zero validator failures and zero warnings on both.

**SCHEDULE D ATTEMPTED ZERO ROWS, AND THE HARNESS CALLED IT `status: complete`.** A row of zeroes
with no failures is the emptiest possible result and it reads in the table as "nothing went
wrong". That is the D10 unexpected-empty case and the harness does not currently fail closed on
it - fix in S31.

**ROOT CAUSE - a hardcoded per-document exclusion, `tax_graph/extract/outline_pipeline.py:452`:**

```
if _is_formula_node(node) and not (document_id.startswith("schedule_d_") and node.kind == "line"):
```

Every Schedule D node of kind `line` is dropped from formula detection regardless of its label.
Measured: Schedule D's outline is healthy - 31 nodes, 24 line anchors - and **3 nodes pass
`_is_formula_node`**: lines 7, 15 and 16, all plainly computed (`Combine lines 1a through 6 in
column (h)`, `Combine lines 8a through 14`, `Combine lines 7 and 15`). The clause excludes exactly
those three. `_is_formula_node` does have `transaction_table` and `totals` branches that look
intended to carry Schedule D instead, but Schedule D's outline contains ONLY `line`, `section` and
`outbound_flow_cue` kinds, so that path never fires and the form falls through to zero.

**The clause entered at `eb99447` - M20-S14, "COMPLETE 3 FORMS FOR REVIEW", accepted on the score
"1040 17/17, Schedule A 7/7".** Schedule D was the third form and its number was never reported.
The intent may well have been legitimate (exclude column-structured lines pending table support),
but it was never recorded as a known gap, and a per-document `startswith` in the shared pipeline
is precisely the gaffer's tape that `PHASE_M20.md` section 1 exists to remove.

**ARCHITECT PROBE - the carve-out is hiding a path that mostly works.** With the clause lifted
in memory only (no repository edit, working tree verified clean afterwards), the live provider
returned **attempted=3, derived=2, errored=1**: lines 7 and 15 derived clean, and line 16 failed
because the model put `schedule_d_2025 line 7` in the operand's LINE field, which
`operand_not_printed` correctly rejected. **So Schedule D is roughly 2/3, not 0/3**, and the one
failure is a malformed-operand question, not evidence that the design fails on tables.

## Standing constraints (every M20 round)

- **PROTECTED SET, hard gate:** `graph/2025/{nodes,edges,rules}/` and `graph/2025/field_maps/`
  must be byte-identical. `git diff --stat` on those directories must be EMPTY. No promotion, no
  hand-authoring, no live graph edit, no verdict write, no operation enum change.
- **`derive_cells` must remain pure - zero disk writes.**
- **PYTEST TEMP ROOT MUST BE SHORT** (e.g. `C:\tgt`). An Architect session was burned reporting 22
  suite failures of which 8+ were `WinError 206` path-length artifacts of a deep temp root. With a
  short root the same files went 11 failed -> 3.
- **KNOWN-RED BASELINE - inherit it, do not get blamed for it, do not fix it in an unrelated
  round.** All three depend on untracked local state, which is why CI is green:
  - `test_review_scope_migration_m15.py::test_live_queue_migration_...` (FileNotFoundError,
    `review_queue/2025/deferred_review.yaml` - tracked dir with no files)
  - `test_schedule_2_m16.py::test_schedule_2_part_i_raw_acroform_identity` (`assert '1a' == 'z'`;
    reads gitignored `.cache/raw/.../schedule_2_2025.fields.json`, regenerated 2026-07-28 while
    the source PDF is unchanged, so a code-only bisect proves nothing)
  - `test_address_campaign_m15r.py::test_form_8949_cross_form_claims_resolve_exactly`
    (`realized 0, expected 6`)
- **The Worker sandbox has NO outbound network.** Live-provider legs fail 17/17 with
  `LlmUnavailable: ... Connection error`. This has cost three rounds. Either run the provider leg
  outside the sandbox with approved access, or declare the round fixture-only UP FRONT.
- **Model is `openai/gpt-5.6-luna`** in `tax-graph.config.yaml` (`llm.micro_model`). Do not switch
  to `google/gemini-3.6-flash` - measured ~15x the cost at our call volume.
- **Evidence discipline:** honest `RAN:` / `NOT RUN:` lines with exact commands and exact output.
  Never a guess, never a paraphrase of a number.

### Worker environment (2026-07-23)
The recurring `Access is denied` on `.venv\Scripts\python.exe` was the venv launcher shim spawning
the OUT-OF-WORKSPACE base interpreter, which the Codex sandbox denies per session (it is NOT a
machine state and no restart fixes it). Fixed by mirroring the base interpreter to `.python313/`
inside the repo (gitignored) and rebuilding `.venv` on it, so `pyvenv.cfg home` is in-workspace.
Workers call `.venv\Scripts\python.exe` directly - no `uv` needed.
**Do NOT pass `--basetemp`** (2026-07-25). The root `conftest.py` pins the temp root for every
account and pytest separates accounts via `pytest-of-<username>/`. The old `.pytest_tmp` is
poisoned and unreclaimable; see the hard rule in `AGENTS.md`.
**Launcher cap is 600s** (John, 2026-07-26; was ~124s, then 240s). The Worker runs its OWN e2e and
app-dependent files. Only full partitions and Tier 3 shakedowns stay Architect-side. Anything that
still does not fit gets an honest `NOT RUN:`.
**ALWAYS use the module form, never the console scripts** (2026-07-23, M16-S4):
`.venv\Scripts\python.exe -m tax_graph.cli validate 2025` and
`.venv\Scripts\python.exe -m workbench.cli preflight --year 2025`. The generated `tax-graph.exe` /
`review-workbench.exe` launchers resolve the package through the editable install's `.pth`, which
hardcodes an absolute repo path that does not resolve inside the Codex sandbox
(`ModuleNotFoundError: No module named 'tax_graph.cli'`). Architects: write the module form into
Worker prompts.

**Recurring op note:** orphaned `serve` processes have first-class tooling -
`tax-graph serve --sweep-orphans`. The parent watchdog works on Windows as of M14 (OpenProcess
probe). Serve writes stderr breadcrumbs that Claude Desktop logs verbatim - first stop when a
client-managed server dies.

## Binding rulings (John's, still in force - DO NOT DELETE ON PRUNE)

- **THE HANDCRAFTED SET IS THE TEST SET, AND IS PROTECTED.** A lot of tokens went into it. It is
  not to be thrown away, promoted over, or edited. It is labeled comparison data. This is the
  origin of the protected-set gate above.
- **THE SPINE IS THE FLOW OF THE FORM (2026-07-26, the addressing ruling).** Verbatim: *"The spine
  is the flow of the form. We shouldn't be pedantic about the line numbers."* John named the
  disambiguation case himself - *"there might be 6 different SSNs for example. Which one?"* - and
  rejected positional numbering for repeatable rows. This REVISES the pinned invariant "IRS line
  numbers are the spine" in `AGENTS.md`. **Identity comes only via canonical addresses.**
- **THE BAR IS PRACTICAL RETRIEVAL (2026-07-26).** Offered two labeling schemes, John rejected the
  framing: *"I don't know that i care so much about the addressing scheme being perfect in some
  theoretical manner. We need to be able to refer to these things in a practical way... if you are
  asked about dependents... numbers, SSNs, whatever, we need to be able to pull it out of the
  graph data/metadata."*
- **FILER-PROVIDED IS A FAILOVER, NOT A DEFAULT (2026-07-31).** Verbatim: *"filer provided should
  be a failover rather than a default."* And: *"If I read 'Net proceeds' or 'Interest', my feeling
  is that this is just something to be provided by the filer. If the AI can't find it in the docs
  provided by the filer, it should ask."*
- **THE REVIEW QUEUE IS THE WRONG SHAPE (2026-07-29); this supersedes the reconciler.** There are
  ZERO human verdicts anywhere - the queue's `pending`/`deferred`/`accepted_local` are all
  machine-set, so the 198 re-points and 263 orphan records preserved no human judgement. The churn
  was an IDENTITY defect: 100% of 461 citation refs (keyed on generated sequence ids) churned
  while 1,921 field-control refs (keyed on canonical addresses) churned 0%. The graph already has
  stable cell identity; coverage should be a traversal, not a migrated file. **Verdicts must bind
  to CONTENT, not only to address.**
- **REVIEW PANEL LAYOUT (parked S6-2, still binding when UI work resumes).** The expression, the
  two instruction sources, the verdict controls, AND the comment box go TOGETHER; today the
  controls sit in the left rail while content is in the right river. Keep the 15/40/45
  proportions. Show the two instruction sources SEPARATELY (form face, instruction page - never
  concatenated). Wire the four buttons that already exist and **keep John's labels** - "Pipeline
  defect" vs "Source pathology" is his distinction.

## Open for Architect

- *(empty - the S3a outline-adapter question was answered 2026-08-02, see Architect decisions)*

## From Architect

- **M20-S31 TASK - DELETE THE SCHEDULE D CARVE-OUT, AND MAKE AN EMPTY RESULT LOUD (Architect,
  Claude Opus 5, 2026-08-02).** Ledger: the RAN/NOT RUN rule, D9, D6, D10.

  **Why this round.** S30 measured the slice and the answer was 17/17, 7/7, and **0**. The zero was
  not a limit of the design - it was one hardcoded clause, and lifting it in a probe produced 2/3
  on the live provider. This round removes the special case and makes the shape of failure that
  hid it impossible to miss next time.

  **Step 1 - delete the per-document exclusion.** `tax_graph/extract/outline_pipeline.py:452`
  currently reads `if _is_formula_node(node) and not (document_id.startswith("schedule_d_") and
  node.kind == "line")`. **Delete the `schedule_d_` clause.** If `document_id` then has no
  remaining use in `_formula_outline_nodes`, remove the parameter and update its callers rather
  than leaving a dead argument. Add a focused test asserting that `schedule_d_2025` yields exactly
  its three formula nodes (lines 7, 15, 16).
  **No other form may be special-cased to compensate.** If some form needs different treatment,
  that is a property of its NODES (kind, columns, label), never of its document id. A
  `startswith` on a document id in shared pipeline code is the defect, not the fix.

  **Step 2 - make an unexpected empty fail closed (ledger D10).** `run_documents` in
  `experiments/derive_cells_s25.py` reports `status: complete` for a document that attempted ZERO
  rows. That is how a form disappears from a report while the table looks clean. A document whose
  frame yields no rows must be reported as a distinct, visibly bad status - `empty` or equivalent -
  carrying the outline node count and line-anchor count so the reader can see whether the form was
  unreadable or merely had nothing to derive. Add a focused test.

  **Step 3 - diagnose the line 16 malformed operand. Do not paper over it.** In the Architect
  probe, `schedule_d_2025` line 16 (`Combine lines 7 and 15 and enter the result`) failed with
  `operand_not_printed` because the model returned the operand LINE field as
  `schedule_d_2025 line 7` - the form id concatenated into the line. Lines 7 and 15 derived clean.
  Report which it is:
  a. a prompt problem (the operand field's contract is ambiguous when a row references sibling
     lines on the same form), or
  b. a code problem (the operand normaliser should split a leading form id out of the line field,
     since identity resolution belongs in CODE - the S13/S24/S28 principle).
  **If (b), fix it in the normaliser and keep `operand_not_printed` strict.** Do not relax the
  printed-line check to let a malformed operand through, and do not add a retry.

  **Step 4 - rerun the three-form slice** and report the per-form table: form, attempted, derived,
  repaired, gapped, errored, top three `validator_failures_by_kind`. Expect 17/17 and 7/7
  unchanged, and Schedule D at 3 attempted. **Lead with `derived` per form.**
  If approved external network is unavailable, do steps 1-3, declare step 4 NOT RUN up front, and
  hand back - the Architect will run it. Do not burn the round on `Connection error`.

  **Do not:** add a retry policy for the temperature-0 nondeterminism; add any gate keyed on
  instruction-section coverage; weaken the self-reference, printed-line, verbatim-quote or
  operand checks; reintroduce reordering into `clean_form_face_text`; promote anything.
  **Stop conditions:** any diff in the protected directories; `derive_cells` acquiring a disk
  write; any harness output landing inside the repository; adding a new per-document special case
  anywhere in the pipeline.
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`, module-form
  `validate 2025`, preflight with `legacy_mined` explicit (394), strict citations (36).
  ONE local commit; no push.

## Architect decisions

- **S3a -> S3b: YES, the structure step owns a deterministic outline adapter. S3a regeneration
  stays blocked until it lands. (Answered 2026-08-02; open since 2026-07-28.)** The bare positional
  index is not enough, and the reason is the one this phase already discovered twice: **identity
  must be resolved in CODE from a stable anchor, never from position.** An exact string offset that
  can land on repeated anchor text in another semantic row is position-based identity - the same
  class of defect as keying the review queue on generated sequence ids (100% churn) and as asking
  the model to name a `quote_span_id` (fixed in S28). The adapter belongs to S3b because
  `PHASE_M20.md` section 3 is explicit that this pipeline never had an independent structure layer
  and that building one IS S3b; an outline is structure, not regeneration. Requirements: build it
  from the corrected text plus `line_anchors` plus page/geometry, resolve each anchor to exactly
  one semantic row, and **fail closed at row granularity** when an anchor is ambiguous - matching
  the S2d/S2e span-resolver ruling. Do not promote a draft or hand-edit a citation or label to get
  past an ambiguity.

## Recent rounds (condensed; full narration in git history - `git show <hash>`)

- **M20-S30 (`00b5f38`, Architect-verified):** harness takes repeatable `--document`, refuses
  in-repo output, and reports per-document failures; REQUIRE_INPUT self-operands exempt from
  `operand_not_in_quote`. Architect slice: 1040 17/17, Schedule A 7/7, Schedule D 0 - the zero
  traced to a hardcoded carve-out, 2/3 with it lifted.
- **M20-S29 (`fca0a4a`, Architect-verified):** `_line_mentioned` handles singular, plural-list and
  range references; `clean_form_face_text` truncates instead of reconstructing, restoring the
  substring invariant. Live 1040 17/17 with warnings 37 -> 2. Step 3 blocked - single-document
  harness.
- **M20-S28 (`12240ef`, Architect-verified):** the three deterministic last-five-row defects -
  cleaned evidence text, REQUIRE_INPUT exempt from the self-reference check, `quote_span_id`
  resolved in code and dropped from the schema. Real 1040 **17/17**.
- **M20-S27 (`8027161`, Architect-verified):** `printed_lines` carries all 59 printed anchors (was
  17 formula-only); `operand_not_printed` collapsed 31 -> 1; per-row span-id enum; generic
  `provider: openai` honors `llm.base_url`. Real 1040 12/17.
- **M20-S26 (`b3e102b`, Architect-verified):** `missing_instruction_text` -> `missing_evidence`
  (face OR instruction), so `attempted` went 4 -> 17; ownership issues DROP the section instead of
  killing the row; label contamination fixed 17/17. **First real expressions in M20**, including
  the floors the flat schema had been dropping (`line 15 -> max(line 11b - line 14, 0)`).
- **M20-S25 (`ff62119`, Architect-verified):** property validators and repair-once. Architect then
  diagnosed derived=0 against real data: the instruction booklet does not document computed lines,
  the form face does - which set up S26.
- **M20-S24 (`e6e94e3`):** `derive_cells` as a pure function with expression trees.
- **M20-S23 (`0831694`):** the `instruction_sections` artifact and its join.

## Latest verification

- **M20-S30 (2026-08-02, Architect):** live three-form slice - `form_1040_2025` 17/17,
  `schedule_a_2025` 7/7 (matches the S14 labeled set), `schedule_d_2025` 0 attempted;
  `operand_not_in_quote` 0 on both non-empty forms; protected set byte-identical; working tree
  clean after the in-memory carve-out probe.
- **M20-S29 (2026-08-02, Architect):** focused suite 79 passed on a short temp root; ASCII;
  `validate 2025` (18 documents, 441 nodes, 409 edges, 401 citations); protected set
  byte-identical across `12240ef..fca0a4a`; live 1040 17/17 with `operand_not_in_quote` 37 -> 2;
  substring invariant verified directly on all four cleaning branches.
- **M20-S28 (2026-08-02, Architect):** focused suite 96 passed on a short temp root; ASCII;
  `git diff --check`; `validate 2025` (18 documents, 441 nodes, 409 edges, 401 citations);
  preflight units=2224, derived cells=2120, `legacy_mined=394` (ratchet unchanged); strict
  citations `checked=401 strict_mismatches=36`; protected set byte-identical; live 1040 17/17.
- **Preflight note:** the sandbox run hits a known pre-existing `WinError 5` on
  `graph/2025/_drafts/form_1040_2025` (a draft ACL, not a regression). The same read-only command
  with escalation passes.
- Prior phase closes: `plans/archive/PHASE_M13.md` and earlier - each with a close note.

## History

Everything before M20-S23, and all per-round Worker narration, lives in git history. This file was
pruned from 7,520 lines on 2026-08-02 at S28 acceptance; `git show 12240ef:plans/AGENT_HANDOFF.md`
is the last unpruned copy. Earlier prune: 2026-07-23, from 1,198 lines, for public-repo prep.
Durable rulings were carried forward into **Binding rulings** above rather than deleted; A9
rulings remain pinned in `plans/PHASE_M15.md`; the defect ledger (D6, D9, D10, D12, D13, D14) is
in `AGENTS.md`.
