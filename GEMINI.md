# GEMINI.md — Spec-Atlas (Gemini CLI)

Spec-driven repository. Same rules as the other agents (`CLAUDE.md`, `AGENTS.md`).

## Read first, every task
1. `docs/PLAYBOOK.md` — development constitution.
2. The task in `tasks/BOARD.md` + its feature file in `specs/features/`.
3. **Only** the specs listed under the task's "Reads" — keep context tight.

## Operating loop
Pick a `ready` task (deps `done`) → claim it (`in-progress` + `gemini` + date) → build only in its "Owns" files with tests → verify → record ADRs for architectural choices → mark `done` + append a HANDOFF note → create new tasks for new work (never expand the current one).

## Hard rules
- **Zero cost:** no paid dependency without an accepted ADR. Tests/CI use `fake` providers (offline).
- Reach models only via `LLMProvider` / `EmbeddingProvider`.
- Provenance mandatory for every answer/spec field.
- Honor stable keys / idempotency in `specs/architecture/DATA-MODEL.md`.
- No secrets in git; stay within `specs/product/SCOPE.md`.

## Skills & conventions
Skills are in `.claude/skills/` (`SKILL.md` files). When a task references one (e.g. `testing-standard`), read it. Lint/format/test commands and the global Definition of Done live in `.claude/skills/testing-standard/SKILL.md`.

## Map
Specs `specs/` · Roadmap `specs/FEATURES.md` · Board `tasks/BOARD.md` · Decisions `docs/decisions/` · Process `docs/PLAYBOOK.md`.
