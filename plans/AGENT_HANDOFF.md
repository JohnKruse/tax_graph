# AGENT_HANDOFF.md

The single living doc for active Claude (Architect) <-> Codex (Worker) coordination. Update it in
place; do NOT spawn new per-topic note files. Standing rules: `../AGENTS.md`. Master plan:
`../docs/engineering-plan.md`. Phase plan: `PHASE_M20.md`.

## How to use
- **Worker:** raise questions/blocks under **Open for Architect**.
- **Architect:** answer there (and pin durable decisions into the relevant `PHASE_<id>.md`), then
  clear the item. Record active direction under **From Architect**.
- **THIS FILE IS LIVE STATE ONLY.** The ball, the round in flight, the open questions, and the
  ONE task spec being worked. Durable rulings and standing constraints live in `../AGENTS.md`
  and are never pruned. History lives in git. **Queued future rounds are ONE LINE each** - a
  full spec written rounds ahead goes stale, which is exactly what happened to S57.
- **Keep it short.** A round that completes gets its narration DELETED, not appended - the
  accepted hash is the record and `git show <hash>` recovers everything. Only the current round,
  the standing constraints, and the binding rulings live here.
- **Prune at every acceptance, not "at phase close".** Pruned 2026-07-23 to 1,198 lines, then
  grew to 7,520 by 2026-08-02 because acceptance never triggered a prune. That is the failure
  mode this section exists to prevent.

## BALL

**BALL: WORKER - M20-S64 (REGENERATE A CANDIDATE GRAPH FROM A FULL RUN).** Spec to be written when
picked up. **S67 is ACCEPTED at `bb3daca`; the corpus is recovered.**

**Live: 67 attempted, 60 derived, 2 repaired, 5 errored.** `form_1040_2025` back to **17/17 with
zero repairs**, 2441 **18/21**, 6251 **25/29**. `doctor` gained a **`roles`** column, so the
layer-disagreement that caused S66 is now a check rather than a lesson.

**THE S54 COMPLETENESS VALIDATOR FIRED ON REAL DATA FOR THE FIRST TIME**, and correctly. 2441 line 8
produced all sixteen bands as CUMULATIVE thresholds (`under_15000=0.35, under_17000=0.34, ...`)
rather than the source's explicit ranges, and the validator refused it -
`lookup_table_band_overlap`, `lookup_table_missing_bands`, `lookup_table_bounds_mismatch`. Under
first-match semantics "under 17,000" contains "under 15,000", so the refusal is right. **The row has
still never derived, but it now fails for the correct reason.**

**QUEUE - one line each.**
1. **S64 candidate regeneration** - first full run; expect ~121 of 478 anchors.
2. **Construction grammar (Architect measuring first)** - John, 2026-08-05: a checkbox is boolean and
   the PDF says so (2441 carries 57 Text and **15 CheckBox** widgets); punctuation carries the
   structure, and `BASE (VARIANT if CONDITION)` is a systematic parenthetical construction that maps
   onto the lookup shape that already works.
3. **Construction drift detection** - John: reviews must call out new punctuation and usage as a
   ranked finding with system-filed evidence, against a VERSIONED construction inventory.
4. **Column and grid recovery**; **phrase obligations**; **S53 approval gate**; **known-red cleanup**.

**STANDING FAILURES, unchanged and honest.** 2441 line 25 wrong for the **seventh** consecutive run.
6251 lines 13 and 20 still fail closed on the worksheet references, which regeneration addresses.

## Current round

**M20-S67 ACCEPTED (Architect, Claude Opus 5, 2026-08-05) at `bb3daca`.** The role invariant is
restored and `doctor` now checks role agreement per operation - the S66 defect could not recur
silently.

**Live, three documents: 67 attempted, 60 derived, 2 repaired, 5 errored**, against 0 derived under
S66. `form_1040_2025` 17/17 with zero repairs.

**First firing of the S54 lookup completeness validator on real data**, recorded because the
Architect had noted three times that it never had. 2441 line 8 emitted sixteen cumulative-threshold
bands instead of the printed explicit ranges; the validator caught overlap, missing source bands and
bounds absent from the source, and refused. **A plausible table with the wrong bounds was rejected
rather than accepted.**

**Everything S66 earned survives:** the registry, `projection_expected` derived from category,
`ABS` removed, `ROUND` and `DIVIDE` cited and tested.

## Open for Architect

**Nothing is open for the Architect.** The three items `doctor` flagged STALE at 73 commits on
2026-08-05 are closed: the **S36 denominator decision** (moot - S51 replaced the denominator
with 121 of 478 anchors and a named reason per skip); the **two scoping calls** (worksheets
closed by the S59 nomination chain; the filing-status constant answered by measurement -
`schedule_1a_2025` line 17 and `form_6251_2025` line 18 both emit correct role-keyed lookups);
and **"what is next"** (John chose option (b), structure and association, on 2026-08-05).

**Open for JOHN, not blocking:** during bootstrap, "every cell receives meaningful human
approval before use" and "a human does not read every new cell" cannot both hold. The pipeline
can eliminate RE-review - approve once against stable semantics, fingerprint the clauses, carry
the verdict while nothing changes - but not first review. That decision shapes S53.

## From Architect

**One spec at a time. The next round is specced when it is picked up.**

## History

Everything before M20-S23, and all per-round Worker narration, lives in git history. This file was
pruned from 7,520 lines on 2026-08-02 at S28 acceptance; `git show 12240ef:plans/AGENT_HANDOFF.md`
is the last unpruned copy. Earlier prune: 2026-07-23, from 1,198 lines, for public-repo prep.
Durable rulings were carried forward into **Binding rulings** above rather than deleted; A9
rulings remain pinned in `plans/PHASE_M15.md`; the defect ledger (D6, D9, D10, D12, D13, D14) is
in `AGENTS.md`.
