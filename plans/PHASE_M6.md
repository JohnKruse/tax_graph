# PHASE M6 - Differential-testing harness   [ ]

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

- [ ] **Step 1 - Pinned OTS runner + output parser.** New extra `[oracles]`;
  `tax_graph/oracles/ots.py`: config-pinned release (version, per-OS download URL, sha256),
  `tax-graph oracle install` fetch/verify/unpack helper (gitignored install dir), and a
  subprocess runner: write an input file, invoke the US_1040 solver, read the `_out.txt`.
  Parser: line-labeled output -> `{label: value}` dict (labels like `L7`, `D16`, `F8949_2h`).
  Commit a real OTS output file as a fixture. Test (offline): parser over the fixture; runner
  smoke behind `@pytest.mark.oracle`. Docs: install + pinning.

- [ ] **Step 2 - Scenario model + dual renderers + box map.** A `Scenario` model for the
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

- [ ] **Step 3 - Differ + guards + deliberate-bug canary.** `oracles/diff.py`: run engine
  result + parsed OTS output through the box map -> report (per-box agree/disagree with values,
  guard violations, scenario attached to every disagreement). Whole-dollar exact match; guard
  violation = scenario REJECTED (distinct from disagreement). Canary tests (offline, canned OTS
  fixtures): (a) agreeing outputs -> clean report; (b) a graph mutated with swapped SUBTRACT
  minuend/subtrahend -> diff catches at the 8949 box, not just L7; (c) a loss-beyond-3000
  canned pair -> detected (OTS caps at -3000, we do not; the divergence/guard must fire).
  Docs.

- [ ] **Step 4 - Domain profile + seeded generator + fuzz command.** Committed
  `oracles/domain_2025.yaml`: what a valid in-domain scenario is (statuses; proceeds/cost/
  adjustment ranges incl. zero and boundary values; net loss capped at $3000 so the unmodeled
  limitation stays inert; everything else absent/inert per the fence). Seeded PRNG generator
  (same seed -> same scenarios). `tax-graph oracle fuzz --n N --seed S`: generate -> render both
  -> run both -> diff -> summary + triage file for disagreements. Test (offline): generator
  determinism + profile-bounds property; out-of-profile scenario refused. Live fuzz >= 100
  scenarios behind `@pytest.mark.oracle`. Docs.

- [ ] **Step 5 - Corpus freeze + offline replay + triage log.** `tax-graph oracle freeze`:
  agreed scenario/expected pairs -> `examples/oracle_corpus/<scenario_id>/` (facts.yaml +
  expected.yaml, same shape the example regression suite already replays) + a `corpus.yaml`
  manifest with provenance (OTS version, seed, generated date, scenario count). Freeze >= 20
  agreed scenarios and commit them. Triage log (`oracles/triage.yaml`) records disagreements
  with the three-outcome disposition from oracle-strategy; a frozen corpus entry may only come
  from an AGREED pair or a human-adjudicated one (disposition recorded). Test (offline): corpus
  replays green through the standard example mechanism; a corrupted expected value fails; a
  disagreed pair cannot freeze without a disposition. Exit-criteria commands run. Docs: README
  oracle workflow.

When all steps are `[DONE]`: mark this phase `[COMPLETE]`, move it to `plans/archive/`, update
`plans/AGENT_HANDOFF.md`, single `git push`, and tell John. Next by milestone order: **M6b**
(repeatable tables, canary Tandem Abacus - plan written just-in-time; its multi-lot execution
immediately widens this harness's domain profile to N lots), then **M8** (verification ladder,
canary Skeptical Notary), with **M7** (Compass Rose) available as the parallel track.
