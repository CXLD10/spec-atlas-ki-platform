# ADR-0003: Phase-0 recovery — late commit of T-000.4/.5/.6 from one branch

Status: accepted
Date: 2026-06-19
Context: Phase 0 (F-000). Tasks T-000.1/.2/.3 were each developed on their own
`task/T-NNN.M-*` branch and merged to `master` per the Agent Operating Loop
(`docs/PLAYBOOK.md`). Work then deviated from that loop and a recovery was required.

> Filename note: the recovery prompt named this `ADR-0002-phase0-recovery.md`, but
> `ADR-0002` is already taken (`ADR-0002-toolchain-and-offline-defaults.md`). To avoid a
> duplicate ADR number this decision is recorded as **ADR-0003**.

## What happened (the process deviation)

- Branch `task/T-000.4-llm-provider` was created off `master` (at T-000.3) for T-000.4.
- **Three tasks' work accumulated on that single branch, uncommitted:**
  - T-000.4 — `src/spec_atlas/llm/` (+ `tests/llm/`), authored by **claude**.
  - T-000.5 — `src/spec_atlas/parse/` (+ `tests/parse/`, fixtures), authored by **codex**,
    with **no dedicated `task/T-000.5-*` branch**.
  - T-000.6 — `src/spec_atlas/api/` (+ `tests/api/`), authored by **codex**,
    with **no dedicated `task/T-000.6-*` branch**; left `in-progress` when codex hit its limit.
- The `tasks/BOARD.md` and `specs/features/F-000-foundations.md` edits marking these
  done/in-progress were also uncommitted. `git log master..HEAD` was empty — git did not
  back the BOARD's claims.
- A fresh audit (`docs/status/`) caught this; this ADR records the resolution.

This violates two playbook norms: **one task = one branch**, and **commit/merge per task**.

## Decision

1. **Commit the recovered work in place**, on `task/T-000.4-llm-provider`, as three
   logically separated commits — one per task, each referencing its task id
   (`feat(F-000): T-000.4 …`, `… T-000.5 …`, `… T-000.6 …`). Re-creating the two missing
   branches retroactively would rewrite shared history for no real benefit; honest commit
   messages + this ADR preserve attribution instead.
2. **Attribution lives in BOARD + HANDOFF + commit messages**, not git author (Codex commits
   under the maintainer's git identity). The T-000.4 HANDOFF "takeover" wording was corrected
   to state plainly: claude wrote `llm/`; codex wrote `parse/` and `api/` and re-ran the suite.
3. **Keep `master` as the base.** There is **no git remote**; merges are local-only and
   **no push is attempted**. A remote/PR target is deferred (tracked in `docs/status/`).

## Consequences

- Git history now reflects the BOARD. Future tasks return to one-branch-per-task.
- T-000.6 was finished and verified during recovery (see its HANDOFF) before being marked done.
- No code behavior changed by this ADR; it is a process/record decision only. $0 cost holds.
