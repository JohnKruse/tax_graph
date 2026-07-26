# Phase M19 - Stable cell identity (the flow of the form is the spine)

**Status:** DRAFTED by the Architect 2026-07-26 at John's direction. John's ruling:
"The spine is the flow of the form. We shouldn't be pedantic about the line numbers."
Supersedes the pinned invariant "IRS line numbers are the spine" (`AGENTS.md`) - see
Invariant change below.

Origin: John's 2026-07-26 review of the M17 workbench. He has been uneasy about cell
addressing "from the beginning" and asked for identity that survives a cell being added
or removed next year, explicitly rejecting positional numbering, and named the
disambiguation problem himself: "there might be 6 different SSNs for example. Which one?"

## Why this phase exists

Three identity layers are in use today. All three are unstable, and one breaks WITHOUT
any year rollover at all.

**1. Review units are keyed by ORDINAL POSITION.** `workbench/manifest.py` `_unit_id`:

```
f"{queue_id}_ref_{ref_index:04d}_loc_{location_index:02d}_{object_id}"
```

`unit_id` means "the Nth thing in the queue". Insert one control anywhere upstream and
every downstream id shifts, so every saved approval in `unit_reviews` silently re-points
to a DIFFERENT cell. This does not need a rollover to bite - it bites on the next
manifest rebuild. Any review campaign run on today's scheme is corrupt the moment the
corpus changes.

**2. Addresses are keyed on LINE NUMBERS.**
`2025/document=form_1040/line=33/control=amount`. The IRS renumbers - the 2017->2018
redesign moved essentially everything. On a renumber every approved cell is orphaned.

**3. Repeatable-table columns are keyed on PRINTED PROSE**, in one case including the
year itself: `column=lived_with_you_more_than_half_2025`. That address is guaranteed to
change next year for a concept that has not changed at all. Measured: 1 of 1470
addresses carries a year literal, so it is an isolated bug rather than systemic - but it
is the flaw in miniature.

`aliases` - the schema field built for exactly this - is EMPTY across all 1470 addresses.
The stability mechanism was scaffolded and never populated.

### John's SSN case, measured

The 1040 has 8 SSN-bearing widgets. The singleton path already does the right thing:

```
2025/document=form_1040/section=identity/control=taxpayer_ssn
2025/document=form_1040/section=identity/control=spouse_ssn
```

Role-qualified, unambiguous. The repeatable path does not - all FOUR dependent SSNs
collapse onto ONE address:

```
2025/document=form_1040/table=dependents/row_template=dependent/column=ssn
```

"Which one?" is literally unanswerable from the address. **The design John is asking for
already exists for singletons; the table path is the gap.**

### The visible symptom: 434 controls that do not exist to a reviewer

`workbench/cell_inventory.py:109` drops any geometry entry whose address `kind` is not
`control`/`option`. Repeatable-table widgets carry `kind: column` row-template addresses,
so they are classified as containers and silently vanish:

| document | widgets | hidden |
| --- | --- | --- |
| form_8949 | 202 | **184** |
| form_w2 | 272 | **132** |
| form_1040 | 199 | **40** |
| 1099-DIV / INT / B | 430 | 24 each |
| schedule_1a | 54 | 6 |
| **total** | **1849** | **434 (23%)** |

The entire 1040 Dependents table is in that 40 - including
`lived_with_you_more_than_half_2025`, which drives the child tax credit, credit for other
dependents, and head-of-household status. Form 8949 is 91% invisible.

This is the worst failure mode of John's coverage invariant: not "a control with no
policy", which the UI at least SHOWS, but a control that never appears at all. The
"159 cells" figure on the 1040 has been misreporting its own denominator.

## The model: meaning, placement, occurrence

**Layer 1 - CONCEPT. Stable, permanent, year-free, line-free, prose-free.**
Identity is the control's position in the FLOW of the form - section, group, role - never
the printed line number. A concept id is minted once and never renumbered:

```
form_1040/identity/taxpayer/ssn
form_1040/identity/spouse/ssn
form_1040/dependents/dependent/ssn
form_1040/payments/withholding/w2
```

This is what a review verdict attaches to, what citations hang off, what survives forever.

**Layer 2 - PLACEMENT. Year-specific, derived, DISPOSABLE.**
For tax year Y, concept C is printed on document D at printed line/box token T, control
role R, page P, rect X, AcroForm field F. Regenerated wholesale by the rollover re-binder.
Nobody reviews a placement; it is machine-derived and machine-verified. The printed line
number lives HERE, as data, never as identity.

**Layer 3 - OCCURRENCE. Runtime, never authored.**
A dependents row is an ENTITY (a specific person in the return record), not a row slot.
Row order is an artifact of data entry - the same child is row 2 this year and row 1 next
year - so a slot index can neither carry a verdict nor mean anything.

### The rule this reduces to

**An address key must never contain anything the IRS can change without changing the
meaning.** No line numbers, no years, no printed prose. Apply it as a test when minting
any id.

### The disambiguation rule (John's SSN case)

**Every concept must be qualified by its OWNER or ROLE in the flow.** A bare `ssn` is
never an address. `identity/taxpayer/ssn`, `identity/spouse/ssn`, and
`dependents/dependent/ssn` are distinct concepts, and the third is completed per
occurrence.

### What happens next year

- **Cell added:** new concept minted. Nothing else moves.
- **Cell removed:** concept retired with the year it left. History intact, no cascade.
- **Moved or renumbered:** placement changes, concept does not. **Review work persists.**
- **Reworded:** printed label is data on the placement. The `_2025` bug becomes
  impossible by construction.
- **Genuinely split or merged:** a real semantic change that SHOULD force re-review,
  recorded with an explicit `supersedes` link rather than a silent re-key.

### Review granularity - do not inflate the queue

A reviewer must NOT be asked to review "dependent 1 first name", "dependent 2 first
name", "dependent 3 first name", "dependent 4 first name". The review unit is the
CONCEPT (one per column). The row instances are then a COVERAGE CHECK: every physical
widget must map to exactly one concept, and the workbench renders the row widgets as
instances of the reviewed concept - visible and accounted for, not four separate
unreviewed cells. This is what closes the 434-control gap without quadrupling the
campaign.

## Invariant change (requires John's sign-off - he gave it 2026-07-26)

`AGENTS.md` currently pins: "**IRS line numbers are the spine:** nodes are keyed on them;
they drive extraction chunking and completeness checks."

Revised: **the FLOW of the form is the spine.** Line numbers remain load-bearing for
extraction chunking, completeness checks, and human-facing display - they are how humans
quote a form and they belong in the UI and in the quotable ref - but they are PLACEMENT
data, never identity. Display wants `33`; identity must not have it.

## Steps

- **S1 - Concept inventory and flow-spine derivation (READ-ONLY).** Derive each document's
  semantic flow (section / group / role) from the structure already available: the
  AcroForm wrapper hierarchy the M16-S3 resolver reads, the address `path` breadcrumb, and
  the geometry reading order. Propose a concept id per widget. Emit a read-only report:
  proposed concept per control, every collision (two widgets, one concept - the 4 SSNs are
  the exemplar), every unqualified concept (a role with no owner), and every id that fails
  the never-contains test. NO artifact changes. This report is the S3 work list.
- **S2 - Stable review identity (backend, high value, independently shippable).** Replace
  positional `unit_id` with a DETERMINISTIC derivation from the unit's identity rather
  than its queue position. **Input is `address_id` (+ the review-kind qualifier), NOT
  `concept_id`** - concepts do not exist until S3, and S3b is blocked on M18, so keying on
  them now would block the one step that needs no prerequisites. The derivation is written
  so its input can be swapped to `concept_id` in S3 without changing the shape. Add a
  fail-closed check that no two units share an id and that no id is positional. This step
  alone stops review work from drifting on a manifest rebuild and can land before
  everything else.
- **S3a - Concept minting for STRUCTURED forms (no M18 dependency).** Forms whose flow
  already exists in the address path - the 1040 Dependents table, 8949 transaction
  columns, W-2 boxes, 1099 copies, and the `section=identity` singletons. Author the
  concept inventory as a promoted artifact; demote the matching address records to
  placements carrying `concept_id` + printed line/box token. Keep `logical_key` as the
  compatibility bridge and populate `aliases` from it.
- **S3b - Concept minting for LINE-ORIENTED forms (BLOCKED on M18).** 6251, Schedules
  1/1-A/2/3/A/B/D, and the ~58 bare `amount` controls on the 1040. **S1 proved these have
  no semantic identity to mint from**: strip the line token and Form 6251's 49 amount
  controls collapse to ONE group, and the graph nodes are line-keyed too
  (`form_6251_2025_part_i_line_1a`) with scraped prose labels, some corrupt ("Line 14:
  1a"). The instructions are the only machine-readable source that names these lines, so
  M18 is a PREREQUISITE, not a follow-on.
- **S4 - Repeatable-table occurrence contract: MAKE TABLES RETRIEVABLE.** Reframed
  2026-07-26 by John: "when we run into a table, or a table of subtables, we get clean,
  reliable and repeatable parsing and addressing... if you are asked about dependents,
  numbers, SSNs, whatever, we need to be able to pull it out of the graph data/metadata."
  The goal is PRACTICAL RETRIEVAL, not a theoretically perfect scheme.
  S3a fixed visibility (`cell_inventory.py:109`; 1921/1921 cells, 0 hidden) but occurrence
  coverage is UNEVEN, which is the real defect:
  - **WORKS:** 1040 dependents (slots 1-4 across a transposed table AND the nested
    `Row5/Row6 -> Dependent1..4` checkbox subtable) and 8949 (11 contiguous rows per part).
    "Dependent 3" returns a complete 10-column record with correct widgets.
  - **BROKEN:** form_w2 and the 1099s. W-2 concepts repeat **24x** (Box 12 `entry/code`,
    `entry/compensation_amount`) and **12x** (`state_local/jurisdiction/*`), yet every one
    carries `repeatable: null` and `occurrence.kind: "singleton"`. 24 cells share one
    concept with NO discriminator, so "Box 12 line C" or "state row 2" cannot be
    addressed. `form_w2/employee/ssn` repeats across the six copies and is also marked a
    singleton. This is the same class of silent flattening as the original 434 - visible,
    but not retrievable.
  Required:
  1. **THE INVARIANT (fail-closed):** a concept mapping to more than one widget in a
     document MUST carry occurrence data with a discriminator. A concept appearing N>1
     times with `occurrence.kind: singleton` is a PARSE FAILURE, not a valid state.
     Validate it; do not let it pass silently.
  2. **Multi-dimensional occurrences.** The W-2 is copy (A/B/C/D/1/2) x row - John's
     "table of subtables". The occurrence key must express more than one axis.
  3. **Honest naming.** Today `row_policy: "entity_keyed"` is claimed while the actual
     discriminator is `repeatable.row_slot`, a printed slot index. At authoring time a
     slot is all that exists (there is no return record yet), so SAY slot, and let runtime
     bind slot -> entity. Do not advertise a contract that is not implemented.
  4. **Normalize group naming.** 8949 currently carries two parallel schemes
     (`form_8949_2025_part_i_line_1` and `table_line1_part1`), and the first embeds a line
     token, failing the never-contains test.
  5. **Put the occurrence in the quotable ref** so a human or an agent can name one:
     `1040/dependents/dependent[3]/ssn`, `w2/box12/entry[2]/code`.
  Acceptance is a RETRIEVAL TEST, not a count: pull dependent 3's full record, W-2 Box 12
  line C, an 8949 row, and a 1099-B state row - each by name, from the graph metadata
  alone. Plus: the 434 stay visible, and the review-unit count does not multiply
  (granularity stays at the concept).
- **S5 - Migration of promoted artifacts + workbench projection.** Field maps, bindings,
  citations, and the manifest move onto concept ids. Refs stay human-quotable and
  line-based for DISPLAY (`1040/33/amount`) while resolving to a concept underneath.
- **S6 - Rollover simulation (THE ACCEPTANCE GATE).** Synthesize a renumbered/moved
  variant of a real form - shift line numbers, insert a control, remove a control, reword
  a label - and prove that concepts, review verdicts, and citations survive, that the
  added control appears as new, and that the removed one retires without cascading. Prove
  stability with a test; do not assert it in prose.

## Sequencing

**CORRECTED 2026-07-26 after the S1 survey.** The Architect originally ruled "M19 before
M18" outright. S1 proved that holds only for STRUCTURED forms. Line-oriented forms have
no semantic material to mint a concept from, and the instructions are the only
machine-readable source that names their lines - so M18 is a prerequisite for S3b.

- **Before M16-S5:** S5 regenerates field maps, bindings, and addresses across 605 cells.
  Regenerating onto an unstable identity scheme means doing it twice.
- **S3a before M18:** structured-form concepts are derivable today and deliver the
  434-control fix; no reason to wait.
- **M18 before S3b:** instruction text is what NAMES a line-oriented concept. Mining it
  once, against ids that are about to stabilize, is the whole point.

Recommended order: **M19-S1 [DONE] -> M19-S2 -> M19-S3a -> M18 -> M19-S3b -> M19-S4/S5
-> M16-S5**, with M19-S6 as the gate before M16-S5 starts. S2 has NO prerequisites and
none of the open questions below block it.

## Gates and boundaries

- Tier 3 throughout S3-S5 (promoted artifacts and shared surfaces): full local partitions
  plus fresh-checkout sim, not just the focused floor.
- S1 is read-only - a report only, no artifact edits, and **no new test suite** (John,
  2026-07-26: "another set of tests is premature"). Concept ids are a PROPOSAL until the
  open questions below are answered; tests written against them now would only be
  rewritten. Testing starts at S3, where something is actually promoted. S1's gates are
  ASCII, `git diff --check`, and `validate 2025` - nothing more.
- The preflight ratchet (`legacy_mined=394`) must not regress; S4/S5 are expected to move
  the reviewable-cell COUNT up by ~434, which is the point, and the manifest unit count
  must be explained by that delta rather than drifting silently.
- Citations stay verbatim-from-acquired-source. Re-keying a citation to a concept must
  never alter its text.
- No verdict already emitted may be silently re-pointed. A concept change that invalidates
  a verdict must retire it explicitly via `supersedes`.

## Decisions (John, 2026-07-26: "pick the defaults, note them as reversible")

John delegated all three to the Architect's recommendation rather than blocking S3a. These
are DECIDED for S3a and reversible before S5 promotion - flag it if implementation shows
one to be wrong.

1. **Concept id shape: PATH STYLE.** `form_1040/dependents/dependent/ssn`. Reads well,
   sorts usefully, and stays human-quotable. The never-contains test is enforced by a
   validator rather than by opacity. Rejected: an opaque key (`c_0a41f2`) - unbreakable by
   a rename, but unquotable, and this project's whole review model depends on a human
   being able to say which cell they mean.
2. **Cross-document concepts: PER-DOCUMENT, with an explicit `same_fact_as` edge.** A W-2
   box 1 wage and 1040 line 1a stay distinct concepts joined by an edge. True
   cross-document unification is a larger modeling change, and the flow spine is
   per-form by construction. The edge preserves the option without paying for it now.
3. **Retirement: concept STAYS in the inventory, marked retired with the year it left.**
   Keeps rollover diffs readable in one place and keeps a retired id from being minted
   again. Revisit only if the inventory becomes unwieldy.

## Open questions for John

1. **Concept id shape.** Path style (`form_1040/dependents/dependent/ssn`) reads well and
   sorts usefully; an opaque stable key (`c_0a41f2`) cannot be broken by a rename but is
   unquotable. Architect recommends the path style, with the never-contains test enforced
   by a validator.
2. **Cross-document concepts.** The same fact appears on multiple forms (a W-2 box 1
   wage flows to 1040 line 1a). Should concepts be per-document, or should one concept
   carry placements on several documents? Architect recommends per-document concepts for
   now with an explicit `same_fact_as` edge, deferring true cross-document unification -
   it is a larger modeling change and the flow spine is per-form by construction.
3. **Retirement policy.** When TY2026 drops a control, does the TY2025 concept stay live
   in the inventory marked retired, or move to an archive file? Affects how rollover diffs
   read.
