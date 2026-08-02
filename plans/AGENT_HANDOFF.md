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

**BALL: WORKER - M20-S32 (REPLACE THE PROMPT TEMPLATE SYNTAX; DO NOT ESCAPE THE BRACES).**
Task block under **From Architect**.
**S31 steps 1-2 are ACCEPTED; step 3 is REJECTED - it zeroes the whole pipeline.**

## Current round

**M20-S31 PARTIALLY ACCEPTED (Architect, Claude Opus 5, 2026-08-02).** Steps 1 and 2 are good and
independently verified. **Step 3 is a regression that takes every form to zero and must be fixed
before anything else.** The Worker declared step 4 NOT RUN, as instructed; the Architect ran it,
which is how this was caught.

**ACCEPTED - step 1, the carve-out is gone (`fb2833e`).** The `schedule_d_` clause is deleted, the
now-unused `document_id` parameter was removed from `_formula_outline_nodes` rather than left as a
dead argument, and all four call sites were updated (`cells.py`, `outline_pipeline.py` x2,
`prompt_bench.py`). No compensating special case was added anywhere.

**ACCEPTED - step 2, an empty document is now loud (`a466a9e`).** Zero attempted rows reports
`status: empty` with a reason, plus `outline_node_count` and `line_anchor_count` so a reader can
tell an unreadable form from one with nothing to derive. This is the D10 fix and it is well done.

**REJECTED - step 3 breaks the prompt (`e18767f`).** The Architect's live slice:

| form | status | reason |
| --- | --- | --- |
| `form_1040_2025` | reported | `ValueError: cell prompt has unsupported placeholder: "line"` |
| `schedule_a_2025` | reported | same |
| `schedule_d_2025` | reported | same |

**17/17 and 7/7 both became 0.** `_render_cell_prompt` renders the prompt with
`template.format(**values)` (`cells.py:1133`), so the literal JSON added to
`prompts/derive_cells.md` - `{"line": "7"}` and `{"form": "form_XXXX_2025", "line": "7"}` - parses
as placeholders named `"line"` and `"form"`, quotes included, which are not in `values`. Every
document fails before a single model call.

**THE REAL DEFECT IS THE TEST, and this is the durable lesson.** `tests/test_m20_s31.py:104-105`
asserts the new sentences are PRESENT in the file:

```
assert 'For a sibling line on this same form, use only {"line": "7"}' in text
```

It never renders the prompt. A substring check passes on precisely the text that breaks rendering.
**Rendering needs no network**, so this was fully catchable in the Worker's sandbox - the round
reported 38 passed with the shipped prompt unloadable. Any change to a prompt file must be covered
by a test that RENDERS it.

**FIX DECIDED - NOT the escape.** The Architect verified in memory that escaping the braces
(`{{"` and `"}}`) does restore rendering. **We are not doing that.** John's call, 2026-08-02:
escaping is the `sed` fix - it works today and becomes the thing nobody can maintain, because an
LLM pipeline will keep needing JSON examples and JSON is made of braces. S32 replaces the
placeholder syntax with `<<name>>` so braces stop being syntax at all. Scope measured and small:
3 prompt files, 3 render sites, every placeholder a bare name.

**STILL OPEN - is the prompt even the right fix?** The Worker chose diagnosis (a), prompt contract,
and added no normaliser. That is defensible, but it makes correct operand encoding depend on model
compliance, and this model is measurably nondeterministic at `temperature: 0`. Once the prompt
renders again, the line 16 result is the evidence. If it still intermittently emits
`schedule_d_2025 line 7` in the LINE field, escalate to diagnosis (b) and normalise in code, per
the S13/S24/S28 principle that identity resolution belongs in code.

**Process note, not a blocker:** the round asked for ONE local commit and produced four. The split
is clean and per-step, which made this review easier, so no complaint - but say so up front next
time rather than silently deviating.

**Gates re-verified by the Architect:** 99 passed on a short temp root; ASCII OK; `validate 2025`
graph integrity OK; protected set byte-identical across `8414211..bf9f7cf`.

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

- **M20-S32 TASK - REPLACE THE PROMPT TEMPLATE SYNTAX SO BRACES STOP MATTERING (Architect, Claude
  Opus 5, 2026-08-02). RESPECCED - do NOT escape the braces.** Ledger: the RAN/NOT RUN rule, D9,
  D6, D10.

  **Why this and not the two-character fix.** Escaping the JSON example to `{{"line": "7"}}`
  works, and it leaves the same trap armed for the next person who shows the model an example.
  We are building an LLM pipeline; prompts will keep needing JSON examples, and JSON is made of
  braces. John's call, 2026-08-02: this is the `sed` situation - the patch that works today is the
  thing that becomes unmaintainable. Remove the collision instead of escaping around it.

  **The scope is small and fully measured. Three prompt files, three render sites, no format
  specs, no nested attribute access, no indexing - every placeholder is a bare name:**
  - `prompts/derive_cells.md` - `form`, `line`, `label`, `form_face_text`, `instruction_text`,
    `instruction_locator`
  - `prompts/extract_generator.md` and `prompts/extract_critic.md` - `document_id`,
    `document_kind`, `tax_year`, `source_text`, `source_url`, `fields`, `links`, `operations`,
    `schemas`, `related_sources`, and `draft_objects` on the critic only
  - render sites: `tax_graph/extract/cells.py:1133`, `tax_graph/extract/prompts.py:213`,
    `tax_graph/extract/prompts.py:242`. (`prompts.py:105` formats a literal log string, NOT a
    prompt template - leave it alone.)

  **Step 1 - adopt `<<name>>` as the placeholder delimiter.** Not `{name}`, which collides with
  JSON. **Not Python's `string.Template` `$name` either** - the prompts contain no literal `$`
  today, but these are TAX prompts and dollar amounts are a matter of time; that trades one
  hazard for a likelier one. `<<` and `>>` appear in neither JSON nor tax prose.
  Add one shared renderer - `render_prompt(template: str, values: Mapping[str, str]) -> str` in
  `tax_graph/extract/prompts.py` - and route all three sites through it. It must **fail closed in
  both directions**: a placeholder with no supplied value raises, and any `<<...>>` token still
  present after substitution raises. Keep the existing error type and an equivalent message so
  callers and tests do not silently change behaviour. Substitution is literal text replacement -
  a value that happens to contain `<<` or braces must never be re-scanned.

  **Step 2 - convert the three prompt files** from `{name}` to `<<name>>`, and **restore the JSON
  example in `derive_cells.md` to plain, unescaped `{"line": "7"}` and
  `{"form": "form_XXXX_2025", "line": "7"}`.** After this change braces are ordinary characters
  and the example reads exactly as the model should emit it. Keep the guidance wording from
  `e18767f`; only the mechanism changes.

  **Step 3 - test that prompts RENDER, not that they contain words.** The S31 defect was a
  substring assertion (`tests/test_m20_s31.py:104-105`) that passed while the shipped prompt was
  unloadable. Replace it. Add a test that **iterates every file in `prompts/`**, renders it
  through `render_prompt` with a representative value for each of its placeholders, and asserts
  success - so a new prompt file is covered the day it lands. Add two negative tests: a missing
  value raises, and a leftover `<<token>>` raises. **This needs no network and must pass in the
  Worker sandbox.** Then, if you want to assert the guidance survived, assert it on the RENDERED
  output.

  **Step 4 - rerun the three-form slice** and report the per-form table: form, status, attempted,
  derived, repaired, gapped, errored, top three `validator_failures_by_kind`. **Lead with
  `derived` per form.** Expected: `form_1040_2025` 17, `schedule_a_2025` 7, `schedule_d_2025` 3
  attempted. **Report what line 16 actually does** - that is the point of the guidance. If it
  derives, say so. If it still emits `schedule_d_2025 line 7` in the LINE field, say that plainly;
  that is the signal to move to a code-side normaliser in S33, and it is a useful result rather
  than a failure of this round.
  If approved external network is unavailable, do steps 1-3, declare step 4 NOT RUN up front, and
  hand back - the Architect will run it. Do not burn the round on `Connection error`.

  **Do not:** escape braces as the fix; leave any prompt on `{name}` syntax; relax
  `operand_not_printed` or any other check to make line 16 pass; add a retry policy; add a
  normaliser this round (that waits on step 4's evidence); reintroduce any per-document special
  case; promote anything.
  **Stop conditions:** any diff in the protected directories; `derive_cells` acquiring a disk
  write; any harness output landing inside the repository; a prompt file that renders only
  because a test was weakened.
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`, module-form
  `validate 2025`, preflight with `legacy_mined` explicit (394), strict citations (36).
  **ONE local commit** - or say up front why it is more; no push.

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
