# AGENTS.md — Spec-Atlas

Spec-driven repository. This file is the entry point for Codex CLI and other AGENTS.md-aware agents. (Claude Code reads `CLAUDE.md`; Gemini CLI reads `GEMINI.md`; all three say the same thing.)

## Read first, every task
1. `docs/PLAYBOOK.md` — the development constitution (work slicing, claiming, handoff).
2. The task in `tasks/BOARD.md` + its feature file in `specs/features/`.
3. **Only** the specs the task lists under "Reads" — preserve context; don't read the whole repo.

## Operating loop
1. Pick a `ready` task whose deps are `done`.
2. Claim it: set `in-progress` + `codex` + date in `BOARD.md` and the feature file.
3. Build only in the task's "Owns" files; add tests per `.claude/skills/testing-standard/SKILL.md`.
4. Verify (tests green + acceptance criteria met).
5. Record any architectural choice as an ADR in `docs/decisions/`.
6. Mark `done`; append a HANDOFF note to the feature file.
7. New work discovered → create a new `ready` task; never expand the current one.

## Hard rules
- **Zero cost:** no paid dependency without an accepted ADR. Tests/CI use `fake` providers (`LLM_PROVIDER=fake`, `EMBED_PROVIDER=fake`) — offline, no network.
- Reach models only via `LLMProvider` / `EmbeddingProvider` — never a vendor SDK directly.
- Provenance mandatory for every answer/spec field (`{file, start_line, end_line}`).
- Honor stable keys / idempotency from `specs/architecture/DATA-MODEL.md`.
- No secrets in git; `.env` gitignored. Stay within `specs/product/SCOPE.md`.

## Conventions
- Branch per task `task/T-NNN.M-<slug>`; commit messages reference the task id.
- Lint/format/test commands and the definition of "done" are in `.claude/skills/testing-standard/SKILL.md`.

## Map
Specs `specs/` · Roadmap `specs/FEATURES.md` · Board `tasks/BOARD.md` · Decisions `docs/decisions/` · Process `docs/PLAYBOOK.md`.

> Note: skills use the cross-agent `SKILL.md` format in `.claude/skills/`. If your agent doesn't auto-load them, read the relevant `SKILL.md` manually when a task references it.
