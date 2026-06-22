# PLAYBOOK.md — Spec-Atlas Development Constitution

> The single source of truth for **how** we build. Every agent (Claude Code, Codex, Gemini) reads this before doing anything. Edit this and everything downstream follows.

## 1. Core principles
1. **Spec-first.** No code before a spec defines its contract and acceptance criteria. The spec is the durable artifact; code is derived.
2. **Vertical slices.** Work is small tasks that each deliver one thin, end-to-end-testable capability.
3. **Independent & additive.** Each task ships a new module/file where possible. Avoid editing shared core; if unavoidable, freeze the shared interface in a spec first.
4. **Context budget.** Each task names the exact specs to load. Agents read only those.
5. **Single source of truth.** Product facts in `specs/product/`, design in `specs/architecture/`, decisions in `docs/decisions/`. No duplication.
6. **Zero cost, always.** Every dependency/service must have a sufficient free tier. Non-free choices need an ADR (default: no).
7. **Resumable by anyone.** State lives in files (`STATUS`, `BOARD`, `HANDOFF` notes), not in an agent's head.

## 2. Repository structure
```
spec-atlas/
  CLAUDE.md · AGENTS.md · GEMINI.md   adapters → this playbook
  docs/PLAYBOOK.md · docs/decisions/   process + ADRs
  specs/product/    PRD.md · VISION.md · SCOPE.md
  specs/architecture/ ARCHITECTURE.md · DATA-MODEL.md · INTEGRATIONS.md · NFR.md
  specs/FEATURES.md · specs/features/F-NNN-*.md
  tasks/BOARD.md
  .claude/skills/<name>/SKILL.md
  src/spec_atlas/ · frontend/ · tests/
```
A feature file is self-contained: open `F-NNN`, read it + the architecture sections it references, work without touching anything else.

## 3. Agent adapters
`CLAUDE.md` (Claude Code), `AGENTS.md` (Codex), `GEMINI.md` (Gemini CLI) are thin and near-identical: "read `docs/PLAYBOOK.md`, follow the operating loop, load only the specs the task names." `CLAUDE.md` loads every prompt (global rules); skills in `.claude/skills/` load on demand.

## 4. Spec hierarchy
| Level | Files | Changes |
|---|---|---|
| Product | `PRD.md` (canonical), `VISION.md`, `SCOPE.md` | rarely |
| Architecture | `ARCHITECTURE.md`, `DATA-MODEL.md`, `INTEGRATIONS.md`, `NFR.md` | via ADR |
| Feature | `features/F-NNN-*.md` (spec + task slices) | per feature |
| Task | task entries in the feature file + `BOARD.md` | constantly |
A task may only assume what its feature spec + referenced architecture guarantee; needing more means amending the spec first.

## 5. What makes a good task slice
Small (one focused session), vertical (testable end-to-end), contracted (inputs/outputs/interface written down), independent (deps are explicit task IDs), additive (new files), owned (lists files it creates/modifies so agents don't collide). If it can't be described this way, split it.

## 6. Agent Operating Loop
1. **Pick** a `ready` task from `tasks/BOARD.md` with all deps `done`.
2. **Claim** it: set `in-progress` + agent + date in `BOARD.md` and the feature file.
3. **Load context** — only: the task, its feature file, the referenced architecture sections, any named skills.
4. **Build** in the task's owned files; write tests per `.claude/skills/testing-standard`.
5. **Verify** — tests green, acceptance criteria met.
6. **Record** — architectural/non-obvious choices → an ADR in `docs/decisions/`.
7. **Hand off** — set `done`; append a HANDOFF note (what was built, decisions, what the next task can assume). New work → new `ready` task, never expand the current one.
Stopping early: leave `in-progress` + a HANDOFF note with the exact resume point.

## 7. Templates
### Feature file `F-NNN-<slug>.md`
```
# F-NNN — <name>
Status: draft|ready|in-progress|done
References: ARCHITECTURE.md#<section>, DATA-MODEL.md#<entity>
## Intent
## Contract  (inputs / outputs / interfaces / invariants)
## Acceptance criteria  (checkboxes)
## Out of scope
## Tasks   (T-NNN.M entries — see below)
## HANDOFF / STATUS
```
### Task entry (in the feature file; mirror a row in `BOARD.md`)
```
### T-NNN.M — <title>
Status: ready
Depends on: [T-...]
Reads: [F-NNN, ARCHITECTURE.md#..., skills/...]
Owns (files): [src/..., tests/...]
Contract: <inputs → outputs / interface>
Definition of Done: <checkboxes>
```
### ADR `docs/decisions/ADR-NNNN-<slug>.md`
```
# ADR-NNNN: <title>
Status: accepted
Context / Decision / Alternatives / Consequences (incl. cost)
```
### HANDOFF note (append to feature file)
```
## HANDOFF <date> — <agent>
Task / Built / Decisions / Next can assume / Follow-ups / Stopped at (if incomplete)
```

## 8. Definition of Done (global)
Acceptance criteria checked; `make lint` + `make test` green (offline, fake providers); no new paid dependency without an ADR; `BOARD.md` + feature file updated; HANDOFF written. Untested code isn't done. (Full detail: `.claude/skills/testing-standard`.)

## 9. Skills
Reusable capability docs in `.claude/skills/<name>/SKILL.md` (cross-agent format). Current: `testing-standard`. Add per need, e.g. `adding-an-integration`, `parsing-a-language` (tree-sitter query packs), `writing-specs`.

## 10. Conventions
Features `F-NNN-<kebab>`, tasks `T-NNN.M`, ADRs `ADR-NNNN-<slug>`. One branch per task `task/T-NNN.M-<slug>`; commits reference the task ID. No silent scope creep — discovered work becomes a new task. Stack-specific commands live in `testing-standard`.
