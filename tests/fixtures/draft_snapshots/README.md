# Draft snapshots (test fixtures)

Frozen, minimal snapshots of extraction-draft files that tests depend on. The live
draft directory `graph/<year>/_drafts/` is gitignored by hard rule (drafts are never
committed, never auto-merged), which means a clean CI checkout does not have it -
tests must NEVER read `graph/<year>/_drafts/` directly; they copy from here instead.

Scope is deliberately minimal - only the files the code under test consumes:

- `form_8949_2025/`, `schedule_d_2025/`: `outbound_flows.yaml` (frontier build + LINK)
  and `metrics.yaml` (verification record).
- `form_6251_2025/`: `outbound_flows.yaml` (rejected-flow disposition tests).
- `schedule_1_2025/`: the promotable kinds present in its draft (`documents.yaml`,
  `nodes.yaml`, `citations.yaml`) for the promote test.

These are fixtures for exercising mechanics, not promotion sources: nothing here may
be promoted into the live graph, and the deferred-review provenance rules are
unaffected. If a pipeline change regenerates drafts with different shapes, refresh
the snapshot files here in the same commit that changes the consuming code.
