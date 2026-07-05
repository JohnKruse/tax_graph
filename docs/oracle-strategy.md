# Oracle Strategy (scaling differential verification)

> Design note extending M6 (differential harness) and ladder layer L5 of
> `docs/extraction-verification.md`. Written 2026-07-05, following John's questions:
> can we compare against OpenTaxSolver's ruleset directly, does that warrant a second
> repo, and do we need the IRS's own validation service?

## 1. What OpenTaxSolver actually is (so we design against reality)

OpenTaxSolver (OTS, opentaxsolver.sourceforge.net) is C source, one solver program per
form-year (`taxsolve_US_1040_<year>` etc.), GPL-licensed (worker confirms exact version
from the source headers). Three facts matter for us:

1. **Its tax logic is IMPERATIVE C, not a declarative ruleset.** There is no structured
   rules file to diff our graph against. The hope "OTS saves its mechanisms in a
   structured way we could just compare" is, strictly, false.
2. **But its INTERFACE is structured and line-anchored.** Input files are line-labeled
   (`L7  1000 ;` - labels map 1:1 to IRS form line numbers; multiple amounts before a
   semicolon are summed; 8949 transactions import from a CSV with
   Description/DateAcquired/DateSold/Proceeds/Cost/Code/AdjustmentAmount). Output files
   are line-labeled computed values. IRS line numbers are OUR node spine too - so
   scenario translation in both directions is a small deterministic mapping, not a
   research problem.
3. **Its C code is highly REGULAR.** Line arithmetic appears as recognizable per-line
   patterns, and example input files ship with every form. Structured enough to
   mechanically mine, even though it is not a ruleset.

So there are two comparison channels, with very different reliability:

- **Execution-level (load-bearing, scalable):** run OTS as a black-box subprocess,
  translate facts -> OTS input, diff OTS output boxes against our engine's node values.
  This is what M6 already plans; the section below scales it.
- **Parameter-level (load-bearing, cheapest of all; added 2026-07-05):** once thresholds/
  limits/brackets are first-class parameter nodes (engineering-plan "Parameters and
  thresholds (decided)"), diff their VALUES directly against two independent witnesses:
  PolicyEngine-US's declarative parameters YAML (values-by-date, with references - a
  structured oracle for exactly these numbers) and constants mined from OTS's C source
  (simple literals like `S_STD_DEDUC = 15750.0` and bracket arrays - regex-minable even
  though the surrounding LOGIC is not). No execution needed; catches wrong-threshold
  extraction (the standard deduction, bracket boundaries, 0/15/20 percent breakpoints,
  AMT phaseouts, caps like the $3000 capital-loss limit) as a plain value comparison.
  Disagreement between the two witnesses themselves -> flag, human adjudicates against
  the revenue procedure.
- **Structure-level (exploratory bonus, never load-bearing):** statically mine OTS's
  per-line C patterns into a line-dependency graph (which lines feed which) and diff its
  SHAPE against our edges. Cheap way to catch routing errors (taxonomy F4) across a whole
  form at once - but parsing C is brittle and OTS refactors yearly, so it may only ever
  flag, never bless. Time-boxed experiment; drop it without regret if noisy.

## 2. The scalable test: scenario fuzzing + a frozen corpus

The genuinely scalable differential test is EXECUTION at volume:

1. **Domain profile per form** - a small committed spec of what a valid scenario looks
   like (which inputs, ranges, cardinalities: 1-50 lots, gains and losses, zero and
   boundary values). Authored once per form; reviewed like code.
2. **Property-based scenario generator** - deterministic-seeded random scenarios from the
   profile; each renders BOTH ways: our `facts.yaml` and the OTS input file (and the
   PolicyEngine/Tax-Calculator situation JSON for liability-level oracles).
3. **Box-level diff** - run both, compare per mapped line via a per-form
   `box_map.yaml` (our node id <-> OTS `L#` label). The box map is hand-authored but
   tiny, one-time, and itself drill-tested (a deliberately mis-mapped box must surface).
   **Both ends of the map are machine-validated (added 2026-07-05):** the OTS side
   against OTS's own PDF-fill METADATA file (each form-year ships one; it enumerates
   every output variable name - `L1a`, `S1_8d`, `D1bh`, `F8949_1ah`, ... - as
   whitespace-delimited name/coordinate rows, trivially parseable, zero tax logic), and
   our side against the M7 frontier registry. The metadata's page list is also the FENCE
   list: it names exactly which schedules the 1040 solver computes (Sched 1/1-A/2/3, A,
   B, D, 8949 short+long with 11 row slots + a totals row, 6251) - unmodeled entries
   there need guard boxes; forms absent there OTS cannot oracle at all. Its
   `round_to_whole_numbers` directive corroborates the whole-dollar diff default.
   **Pin SourceForge releases only** - the GitHub mirrors are stale (stop ~2020); tax
   logic itself lives solely in the per-form C solvers, confirmed by the metadata's
   omission of any arithmetic.
4. **Triage policy** - on disagreement NEITHER side is presumed right (OTS has bugs
   too). A disagreement is a flag with the full scenario attached; a human adjudicates a
   SAMPLE, and adjudicated cases join the drill/regression catalogs. Adjudication is
   asymmetric in our favor: our engine emits the full trace (rule, edges, quoted
   citation) while OTS emits a number, so the human reads OUR derivation against the
   instruction text. Three outcomes, each with a required action:
   - **Our bug** -> fix the graph; the scenario freezes as a regression fixture and the
     defect class joins the M8 drill catalog.
   - **OTS bug** -> report upstream (from the corpus-factory repo, which owns the OTS
     relationship) with the minimal repro the generator already produced - the scenario
     in OTS's own input format. The case is recorded as a known-divergence exclusion
     (with the report link) so it stops flagging, and re-checked on the next pinned OTS
     release bump.
   - **Genuine IRS-text ambiguity** -> the rarest and most valuable outcome: document it
     on the graph object itself (citation + note, or a decision node if filers genuinely
     choose), so the ambiguity becomes visible roadmap content instead of a silent
     coin-flip.
5. **Freeze the corpus** - agreed scenario+expected pairs are frozen into committed
   fixtures (`facts.yaml` + `expected.yaml`, the existing `examples/` pattern). Frozen
   fixtures are pure data: the main repo's CI replays them offline with NO oracle
   installed, preserving the deterministic-offline invariant. Re-generation against live
   oracles is a periodic gated job, not a per-push cost.

Thousands of machine-checked scenarios per form, zero humans except disagreement
triage - this is the scalability answer.

### Fencing (pinned 2026-07-05, answering John)

OTS solvers are monolithic - the 1040 program always computes the whole return and
cannot be limited to one schedule. We therefore fence the SCENARIO and the COMPARISON,
never the oracle:

1. **Scenario fence** - the domain profile generates only facts that keep unmodeled
   branches structurally inert (no dividends, no self-employment, standard deduction
   applies, ...). OTS computes everything; everything outside our slice computes to zero
   or a known default.
2. **Comparison fence** - only box-mapped lines are diffed; unmapped OTS output lines
   are ignored by design.
3. **Guard boxes** - the box map also asserts that fenced-off paths stayed inert (e.g.
   "Schedule 1 additional income == 0 in this corpus"). A scenario that trips a guard is
   REJECTED before diffing - no triage time on garbage diffs.
4. **Frontier-derived fence (once M7 lands)** - every modeled node must have a box-map
   entry; everything at or beyond the frontier registry is a guard or ignored. The box
   map is validated against the registry, not hand-trusted.

Neither side is fed filled schedules: both consume the same primitive source facts (the
8949 lot list) and independently derive every intermediate line - which is what makes
mid-graph diffs (8949 totals, Schedule D lines) meaningful, not just the 1040 bottom
line. The differ carries an explicit per-box rounding policy (whole-dollar exact match
by default; anything looser is a finding, not a knob).

## 3. The second repo: an oracle corpus FACTORY, not (initially) a fork

A separate GitHub project is the right call, but its product is DATA, not a fork:

- **`tax-oracle-corpus` (name TBD by John):** vendors/pins exact OTS releases (and
  PolicyEngine / Tax-Calculator versions), builds OTS in its own CI, hosts scale
  generation, and PUBLISHES the frozen corpus. The main repo consumes released corpus
  fixtures as plain files.
- **Timing (amended 2026-07-05):** OTS ships prebuilt per-OS release binaries, so M6
  needs NO C toolchain and NO vendored source - it pins a release (version + sha256) and
  downloads it like an acquire artifact, keeping the main repo GPL-clean. The factory
  repo is created only when source patches, C builds, or scale CI actually demand it -
  not automatically at M6 start.
- **Why separate:** (a) LICENSE isolation - running OTS as a subprocess does not touch
  our license, but keeping GPL C source, patches, and build tooling in their own repo
  keeps the main project clean; (b) the C toolchain and oracle installs stay out of the
  main repo's base CI; (c) the corpus is independently useful and independently
  versioned (oracle-version bumps churn the corpus, not the tax graph).
- **Fork only when a patch is actually needed** (e.g. machine-readable JSON output or a
  headless fix). OTS is already CLI-driven, so a thin wrapper likely suffices; if we do
  patch, the fork lives inside/beside the corpus repo and patches are offered upstream.
  Harvesting the oracles' OWN shipped tests (OTS example files; PolicyEngine's YAML unit
  tests) as scenario seeds is cheap corpus bootstrap - license terms for redistributing
  derived fixtures get checked per oracle (worker task).

## 4. The IRS's validation service: stay at arm's length (John's instinct is right)

The IRS offering is MeF ATS (Assurance Testing System) - a certification gate for
authorized e-file providers. Per the June 2026 oracle research: it validates SCHEMA and
BUSINESS-RULE ACCEPTANCE of a transmission, not arithmetic, and enrolling means becoming
an e-file provider (EFIN application, compliance obligations). We are not filing
software; we produce a roadmap + audit trail. Decision:

- **Do NOT enroll or transmit anything to the IRS.** The degree of separation is
  deliberate: independent implementations prove themselves (PolicyEngine is validated
  against NBER TAXSIM; OTS against its user base and published examples), and we measure
  agreement with THEM.
- **Do use the IRS's PUBLIC artifacts as data:** ATS scenario PDFs (public downloads)
  are IRS-authored scenario INPUTS - feed them to the generator pipeline as seeds; the
  MeF schema line inventory (if cleanly obtainable) serves as the box-mapping ground
  truth already noted in ladder layer L1. Both are downloads, not a service
  relationship.

## 5. How this slots into the plan

All of this is the SCALE half of **M6** (Twin Witness) plus the L5 layer of the M8
ladder; no new milestone. M6's step list (in `PHASE_M6.md`, written just-in-time) should
cover: adapters + box maps -> domain profile + generator -> fuzz/diff/triage -> corpus
freeze + offline replay -> (time-boxed, optional) OTS static line-graph mining. The
corpus-factory repo is created when M6 starts; until then nothing blocks on it.

Decisions proposed to John: (1) create the separate corpus-factory repo at M6 start;
(2) no IRS enrollment, public artifacts only; (3) OTS static mining is a time-boxed
experiment, never load-bearing. Defaults adopted unless vetoed.
