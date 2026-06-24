# CLAUDE.md — Spec-Atlas (Claude Code)

You are working in **Spec-Atlas**, a spec-driven repository. Follow these rules on every task.

## Before doing anything
1. Read `docs/PLAYBOOK.md` (the development constitution). It defines how work is sliced, claimed, and handed off.
2. Read the task you're working on from `tasks/BOARD.md` and its feature file in `specs/features/`.
3. Load **only** the specs the task names under "Reads". Do not read the whole repo — preserve context.

## How to work (the Agent Operating Loop)
- Pick a `ready` task from `tasks/BOARD.md` with all deps `done`.
- Claim it: set `in-progress` + `claude` + date in `BOARD.md` and the feature file.
- Build **only in the task's "Owns" files**. Add tests per `.claude/skills/testing-standard`.
- Verify: all tests green, acceptance criteria met.
- If you made an architectural/non-obvious choice, add an ADR in `docs/decisions/`.
- Set the task `done`; append a HANDOFF note (template in the playbook) to the feature file.
- Found extra work? Create a new `ready` task — do NOT expand the current one.

## Global rules (always)
- **Zero cost.** No paid dependency without an accepted ADR. Default LLM/embedding = free/local providers; tests/CI use the `fake` providers (offline).
- **Never call a vendor SDK directly** — go through `LLMProvider` / `EmbeddingProvider`.
- **Provenance is mandatory:** no answer or spec field without `{file, start_line, end_line}`.
- **Idempotency:** respect stable keys in `DATA-MODEL.md`; re-ingest must not duplicate.
- Never commit secrets; `.env` is gitignored.
- Stay in scope (`specs/product/SCOPE.md`). Don't invent features.

## Skills
Project skills live in `.claude/skills/`. They load when relevant. `testing-standard` defines what "tested" means and how to run checks — consult it before marking a task done.

## Where things are
- Specs: `specs/` (product, architecture, features) · Roadmap: `specs/FEATURES.md`
- Board: `tasks/BOARD.md` · Decisions: `docs/decisions/` · Process: `docs/PLAYBOOK.md`
