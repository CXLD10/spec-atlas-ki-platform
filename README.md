# Spec-Atlas

A tool that maps any codebase into a knowledge graph, generates structured specs from it, and serves them to humans and AI coding agents — turning *what the code is* (structure) into *what the code means* (intent, contracts, the "why"). Local-first, zero cost, multi-language.

This repository is **spec-driven**: specs are the source of truth, code is derived from them, and work is sliced so any agent (Claude Code, Codex, Gemini) can pick up an independent task. Start with `docs/PLAYBOOK.md`.

## Reading order
1. `docs/PLAYBOOK.md` — how we build (process, slicing, agent operating loop). **Read first.**
2. `specs/product/PRD.md` — the canonical product doc (v1.1).
3. `specs/architecture/ARCHITECTURE.md` — the four-layer system design.
4. `specs/architecture/` — `DATA-MODEL.md`, `INTEGRATIONS.md`, `NFR.md`.
5. `specs/FEATURES.md` — the phased roadmap.
6. `specs/features/F-000-foundations.md` + `tasks/BOARD.md` — the first buildable work.

## Folder map
```
spec-atlas/
  README.md
  CLAUDE.md · AGENTS.md · GEMINI.md      agent adapters (all point to the playbook)
  docs/
    PLAYBOOK.md                          development constitution
    decisions/ADR-0001-v1-key-decisions.md
  specs/
    product/      PRD.md · VISION.md · SCOPE.md
    architecture/ ARCHITECTURE.md · DATA-MODEL.md · INTEGRATIONS.md · NFR.md
    FEATURES.md
    features/     F-000-foundations.md
  tasks/BOARD.md
  .claude/skills/testing-standard/SKILL.md
```

## Status
Planning complete through the foundation. PRD at v1.1; architecture locked on the four-layer model. Phase 0 is sliced into ready tasks; Phases 1+ get sliced into tasks one phase at a time.

## Hard constraints
Zero cost (free tiers + local compute). Source code stays local. The pipeline only reads files and calls a model — it never executes repository code.
