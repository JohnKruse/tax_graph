# PHASE M6 - Differential-testing harness   [COMPLETE]

**Canary:** Twin Witness
**Depends on:** M0/M1 (engine + compiled runtime), M5 (run pipeline stable). Precedes M6b
(repeatable tables) and M8 (verification ladder - M6 supplies its L5 layer).
**Design doc (canonical for strategy):** `docs/oracle-strategy.md` - fencing policy, triage
outcomes, corpus freezing, and what OTS is (imperative C; line-labeled I/O keyed to IRS line
numbers). Read it before starting.
**Goal:** Confidence via cross-implementation agreement. Build the OpenTaxSolver (OTS) adapter,
a seeded scenario generator over a fenced domain profile, a box-level differ with guard boxes,
divergence triage, and a FROZEN corpus of agreed scenario/expected fixtures that the main test
suite replays offline. Exit proof: a deliberate graph bug is caught by the diff, and an
unmodeled-semantics scenario (loss past the $3000 limit) is DETECTED as out-of-domain, not
silently wrong.

## Why
No comprehensive IRS answer key exists; agreement across independent implementations is the
real confidence (testing-strategy category 7). The single-lot capital-gains slice is live end
to end (facts -> 8949 -> Schedule D -> 1040 L7), so every line of it can now be witnessed by an
implementation we did not write. The harness built here is also the L5 layer of the M8
verification ladder and the template for every future promoted form.

## Exit criteria (must pass 100%)
- `pytest -m m6` green - fully OFFLINE/deterministic (parser + differ over committed OTS output
  fixtures; frozen corpus replay; no OTS install, no network).
- Gated oracle job (`pytest -m oracle`, needs a pinned OTS install): a seeded fuzz run of
  >= 100 in-domain single-lot scenarios diffs against OTS with every mapped box agreeing
  (or divergences logged to triage - zero SILENT divergence).
- A deliberately seeded graph bug (swapped SUBTRACT roles on column (h)) is caught by the diff.
- A net-loss-beyond-$3000 scenario is rejected/flagged by the domain fence or guard boxes as
  out-of-domain (proves the harness SEES unmodeled semantics; our line 7 has no loss limit).
- A frozen corpus of >= 20 agreed scenarios is committed under `examples/` and replays offline
  in the base suite; single-lot line 7 = 2000 regression unchanged.
- Base-deps-only `run` untouched; oracle deps live behind a new `[oracles]` extra.
- `uv run python tools/check_ascii.py` OK; full `pytest` green.

## Guardrails (do not drift)
- **No GPL source in this repo.** M6 uses PINNED PREBUILT OTS release binaries, downloaded and
  hash-verified like an acquire artifact (config: version, per-OS URL, sha256, install dir -
  gitignored). Running a subprocess does not touch our license. Vendoring/patching OTS source,
  C builds, and scale CI belong to the separate corpus-factory repo, created ONLY when source
  patches or scale generation demand it (amended 2026-07-05 from "at M6 start" - prebuilt
  releases make it unnecessary now).
- **Deterministic core / gated oracle.** Everything `pytest -m m6` runs is offline: renderers,
  parser, box-map validation, differ, guards, corpus replay - all against committed fixtures.
  Only `@pytest.mark.oracle` invokes a real OTS binary.
- **Neither side is presumed right.** Divergence = a triage entry with the full scenario
  attached; the three outcomes and their required actions are pinned in
  `docs/oracle-strategy.md` (our bug -> fix + regression + drill; OTS bug -> upstream report +
  known-divergence exclusion; IRS-text ambiguity -> documented on the graph object).
- **Whole-dollar exact match** after rounding is the differ default; any per-box tolerance
  wider than that is a FINDING recorded in the box map with a reason, not a knob.
- **Fence the scenario and the comparison, never the oracle** (pinned in oracle-strategy):
  domain profile keeps unmodeled branches inert; only box-mapped lines diff; guard boxes
  assert inertness and REJECT scenarios that trip them before any diffing.
- **Fake data only.** Scenarios/corpus contain generated values, no real taxpayer data.
- **Deferred within M6 (do not build):** PolicyEngine / Tax-Calculator adapters wait until the
  graph computes tax LIABILITY (they are liability-level oracles; our slice stops at total
  income - nothing for them to witness yet). Parameter-level diffing waits for the first
  `parameter` nodes. OTS static C-mining is a separate time-boxed experiment, not this phase.
- **ASCII-only**; oracle deps never in base.

## Steps

- [DONE] **Step 1 - Pinned OTS runner + output parser.** New extra `[oracles]`;
  `tax_graph/oracles/ots.py`: config-pinned release (version, per-OS download URL, sha256),
  `tax-graph oracle install` fetch/verify/unpack helper (gitignored install dir), and a
  subprocess runner: write an input file, invoke the US_1040 solver, read the `_out.txt`.
  Parser: line-labeled output -> `{label: value}` dict (labels like `L7a`, `D16`, `F8949_2h`).
  Commit a real OTS output file as a fixture. Test (offline): parser over the fixture; runner
  smoke behind `@pytest.mark.oracle`. Docs: install + pinning.
  - Worker note: implemented with stdlib download/unpack/hash verification, so the `[oracles]`
    extra exists but adds no base dependency. Live runner smoke is gated by `OTS_1040_2025_BIN`.

- [DONE] **Step 2 - Scenario model + dual renderers + box map.** A `Scenario` model for the
  capital-gains slice (filing status, single lot: description/dates/proceeds/cost/adjustment -
  multi-lot arrives with M6b). Two deterministic renderers: scenario -> our `facts.yaml`;
  scenario -> OTS input `.txt` (title line, `Status`, lot entry - via the 8949 CSV route if
  cleaner). `oracles/box_map_2025.yaml`: our node_id <-> OTS output label for every modeled
  line (8949 totals, Schedule D lines, 1040 L7) PLUS guard boxes (OTS labels that must be 0 /
  absent, e.g. Schedule 1 income) with expected inert values. Validate the map both ways: every
  our-side node exists in the graph; every OTS-side label appears in a committed OTS label
  inventory (parse OTS's PDF-metadata file once into a fixture - it enumerates all output
  variable names). Test: golden renders; map validation fails on an unknown node id and on an
  OTS label not in the inventory. Docs.
  - Worker note: live rendering now fills the installed OTS `US_1040_template.txt` and points the
    category-specific `f8949_spreadsheet-A/D:` field at a generated Form 8949 CSV. The live v23.06
    labels pinned in the box map are `D8bh` and `L7a` for Schedule D line 8b column (h) and Form
    1040 line 7. The v0 Tax Graph renderer rejects nonzero adjustments because the live graph has
    no adjustment node yet; the domain profile keeps adjustment at zero until M6b/graph growth.

- [DONE] **Step 3 - Differ + guards + deliberate-bug canary.** `oracles/diff.py`: run engine
  result + parsed OTS output through the box map -> report (per-box agree/disagree with values,
  guard violations, scenario attached to every disagreement). Whole-dollar exact match; guard
  violation = scenario REJECTED (distinct from disagreement). Canary tests (offline, canned OTS
  fixtures): (a) agreeing outputs -> clean report; (b) a graph mutated with swapped SUBTRACT
  minuend/subtrahend -> diff catches at the 8949 box, not just L7; (c) a loss-beyond-3000
  canned pair -> detected (OTS caps at -3000, we do not; the divergence/guard must fire).
  Docs.
  - Worker note: differ statuses are `agreed`, `disagreed`, and `rejected`. Guard violations
    short-circuit mapped-box comparison; mapped disagreements include the scenario payload.

- [DONE] **Step 4 - Domain profile + seeded generator + fuzz command.** Committed
  `oracles/domain_2025.yaml`: what a valid in-domain scenario is (statuses; proceeds/cost/
  adjustment ranges incl. zero and boundary values; net loss capped at $3000 so the unmodeled
  limitation stays inert; everything else absent/inert per the fence). Seeded PRNG generator
  (same seed -> same scenarios). `tax-graph oracle fuzz --n N --seed S`: generate -> render both
  -> run both -> diff -> summary + triage file for disagreements. Test (offline): generator
  determinism + profile-bounds property; out-of-profile scenario refused. Live fuzz >= 100
  scenarios behind `@pytest.mark.oracle`. Docs.
  - Architect note (2026-07-05): Codex drafted this step but its session hit the usage limit
    before it could run tests (sandbox escalation blocked). The Architect ran verification on
    its behalf: `pytest -m m6` -> 17 passed, 2 skipped (gated live-oracle tests); full `pytest`
    -> 113 passed, 5 skipped; ASCII check OK; `oracles/domain_2025.yaml` confirmed to cap net
    loss at -3000 with boundary values. Committed by the Architect, authored by Codex.

- [DONE] **Step 5 - Corpus freeze + offline replay + triage log.** `tax-graph oracle freeze`:
  agreed scenario/expected pairs -> `examples/oracle_corpus/<scenario_id>/` (facts.yaml +
  expected.yaml, same shape the example regression suite already replays) + a `corpus.yaml`
  manifest with provenance (OTS version, seed, generated date, scenario count). Freeze >= 20
  agreed scenarios and commit them. Triage log (`oracles/triage.yaml`) records disagreements
  with the three-outcome disposition from oracle-strategy; a frozen corpus entry may only come
  from an AGREED pair or a human-adjudicated one (disposition recorded). Test (offline): corpus
  replays green through the standard example mechanism; a corrupted expected value fails; a
  disagreed pair cannot freeze without a disposition. Exit-criteria commands run. Docs: README
  oracle workflow.
  - Worker note: `tax-graph oracle freeze` writes deterministic replay fixtures and
    `tax-graph oracle replay-corpus` replays them offline. After the live-gate fix,
    `freeze_generated_corpus` requires a live OTS executable and freezes expected values only from
    agreed diff reports. The committed seed corpus has 20 in-domain scenarios under
    `examples/oracle_corpus/` with provenance `live_ots_diff_report`.

## Architect live-gate review (2026-07-05): resolved before phase close

All five steps are implemented and the OFFLINE gates are green, but the Architect installed the
pinned OTS (2025 v23.06, sha256-verified) and ran the live gate: **both live tests FAIL**, and
the failures are real defects the offline goldens could not see. This is the live gate doing
its job. Required fixes before `[COMPLETE]`:

1. **F1 - OTS input renderer emits invalid grammar** (`scenario.py` OTS render + the smoke
   test input). Verified against the real solver and the shipped examples:
   - `Status` takes NO colon (`Status Single` - `Status:` is a fatal ERROR1).
   - The title line must start `Title:  US Federal 1040 Tax Form - 2025` (a foreign title also
     makes the exe shell out to a `bin/` helper from the wrong cwd - the "'bin' is not
     recognized" noise).
   - The header QUESTION SEQUENCE is required after Status: `You_65+Over?`, `You_Blind?`,
     `Spouse_65+Over?`, `Spouse_Blind?`, `Dependents`, `CkHomeInUS`, `VirtCurr?`,
     `CkSepLivedApart` (parser expects them in order; missing -> ERROR1).
   - The spreadsheet label in 2025 v23.06 is CATEGORY-SPECIFIC WITH a colon:
     `f8949_spreadsheet-A/D:  <csv>` (also `-B/E:`, `-C/F:`, ...) - NOT `f8949spreadsheet:`.
     The CSV path resolves relative to the solver's cwd; the runner sets cwd = the input
     file's dir, so write the CSV beside the input and reference the bare filename.
   - **Fix direction: fill the INSTALLED package's `tax_form_files/US_1040/US_1040_template.txt`
     rather than composing lines from scratch** - template-filling guarantees the grammar and
     survives yearly template drift. Add a live grammar test (valid render -> OTS exit 0, no
     ERROR1 in output).
2. **F2 - Corpus freeze bypasses the oracle.** `freeze_generated_corpus` computes `expected`
   from OUR OWN ENGINE and stamps every entry `status: agreed` with
   `oracle_version: ots_2025_23.06` - but OTS never ran. That is self-agreement with false
   provenance, exactly what testing-strategy forbids. Fix: freezing must CONSUME a live diff
   report (only boxes that actually agreed with OTS freeze as `agreed`); REGENERATE the
   committed corpus against live OTS after F1; the current corpus must not survive phase close
   with its current provenance.
3. **F3 - Smoke test input** has the same grammar bugs as F1 (fix together).

Infrastructure now in place (Architect, 2026-07-05): OTS 2025 v23.06 installed and verified at
`.cache/oracles/opentaxsolver/2025_23.06/` (executable `...\bin\taxsolve_US_1040_2025.exe`);
pin is in John's local config. **Commit the pin (URL + sha256) into
`config/tax-graph.config.example.yaml` and README** so the gated CI/job can reproduce it:
url `https://sourceforge.net/projects/opentaxsolver/files/OTS_2025/v23.06_mswin/OpenTaxSolver2025_23.06_mswin.zip/download`,
sha256 `7d570384801b04a70eea4e704f80f2c5f37472ecd3406e9a3d695d132b963bc7`. Set
`OTS_1040_2025_BIN` to the executable path to run `pytest -m oracle`.

When all steps are `[DONE]`: mark this phase `[COMPLETE]`, move it to `plans/archive/`, update
`plans/AGENT_HANDOFF.md`, single `git push`, and tell John. Next by milestone order: **M6b**
(repeatable tables, canary Tandem Abacus - plan written just-in-time; its multi-lot execution
immediately widens this harness's domain profile to N lots), then **M8** (verification ladder,
canary Skeptical Notary), with **M7** (Compass Rose) available as the parallel track.

## Worker closeout (2026-07-05)

Resolved F1-F3 from the live-gate review:
- OTS input rendering fills the installed `US_1040_template.txt`, emits the required header
  question sequence, uses `Status` without a colon, and writes `f8949_spreadsheet-A/D:` with a
  bare CSV filename beside the input.
- `tax-graph oracle freeze` now requires a live OTS executable, runs generated scenarios through
  OTS, and freezes only values carried by agreed diff reports.
- The box map and label inventory now match live OTS v23.06 labels (`D8bh`, `L7a`), and the
  committed corpus manifest records `source: live_ots_diff_report`.

Exit verification:
- `.\.venv\Scripts\python.exe -m pytest -m m6` -> 23 passed, 2 skipped, 99 deselected
- `.\.venv\Scripts\python.exe -m pytest -m oracle` with `OTS_1040_2025_BIN` set -> 2 passed,
  122 deselected
- `.\.venv\Scripts\python.exe -m tax_graph.cli oracle freeze --year 2025 --n 20 --seed 20250705
  --generated-date 2026-07-05 --oracle-version ots_2025_23.06 --source yaml` -> wrote 20 live
  OTS-agreed scenarios
- `.\.venv\Scripts\python.exe -m tax_graph.cli oracle replay-corpus --year 2025 --source yaml`
  -> 20 scenarios, OK
- `.\.venv\Scripts\python.exe -m pytest` -> 119 passed, 5 skipped
- `.\.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK
- `uv --directory C:\Users\devbox\projects\tax_graph run --no-dev python -m tax_graph.cli run
  --facts examples\capital_gains_basic\facts.yaml --source yaml --no-record` -> Form 1040 line 7
  = 2000
