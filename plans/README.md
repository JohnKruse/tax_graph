# plans/ - working state for the Architect / Worker protocol

Filesystem-persisted plan state so a fresh Worker session can resume without the original context.

- **Standing rules, roles, Worker directive, hard rules:** `../AGENTS.md` (canonical).
- **Master plan** + phase gates/canaries: `../docs/engineering-plan.md`.
- **Per-phase subplans:** `PHASE_<id>.md` - generated serially by the Architect. Steps `[ ]` /
  `[DONE]`; a finished phase is `[COMPLETE]` and moved to `archive/`.
- **archive/** - completed subplans.
- **Live Claude <-> Codex coordination:** `AGENT_HANDOFF.md` (one living ledger; no new per-topic
  note files).
