# Spec-Atlas — Knowledge Intelligence Platform

A tool that maps any codebase (+ supporting docs) into a knowledge graph, generates structured specs from it, and serves them to humans and AI coding agents — turning *what the code is* (structure) into *what the code means* (intent, contracts, the "why"). Now with **multi-source ingestion** (code + PDF + Markdown + Excel) and **conversation memory** (facts persist across sessions). Local-first, zero cost, multi-language.

**Current Sprint**: Phase 0–4 (20 hours)  
- Phase 0 (0–3h): Stabilize backend/frontend seam
- Phase 1 (3–8h): Multi-source ingestion (PDF, Markdown, Excel)
- Phase 2 (8–13h): Graph explorer + on-demand spec generation
- Phase 3 (13–17h): Breadth (≥3 adapters) + conversation memory
- Phase 4 (17–20h): Demo + hardening + deliverables

This repository is **spec-driven**: specs are the source of truth, code is derived from them, and work is sliced so any agent (Claude Code, Codex, Gemini) can pick up an independent task. Start with `docs/PLAYBOOK.md`.

## Reading order
1. **This sprint** (Phase 0–4):
   - `TASKS.md` — 20-hour roadmap (Gates G0–G4)
   - `API_CONTRACT.md` — canonical API spec (routes, fields)
   - `PROMPTS.md` — LLM instruction templates
   - `CLAUDE.md` — agent operating loop
   - `docs/TESTING.md` — Definition of Done
2. **Architecture & Product**:
   - `specs/product/PRD.md` — product requirements (v2.0 with multi-source + memory)
   - `specs/product/SCOPE.md` — Phase 0–4 in-scope vs out-of-scope
   - `specs/architecture/ARCHITECTURE.md` — three-layer graph-RAG design
   - `specs/architecture/DATA-MODEL.md` — database schema (projects, sources, specs, memory)
3. **Design & Reference**:
   - `docs/DECISIONS.md` — ADR index (architecture decisions)
   - `docs/HANDOFFS.md` — developer handoff notes
   - `specs/architecture/INTEGRATIONS.md`, `NFR.md`
   - `specs/FEATURES.md` — feature roadmap
   - `specs/features/F-*.md` — feature specs

## Folder map
```
spec-atlas/
  README.md
  CLAUDE.md · TASKS.md · API_CONTRACT.md · PROMPTS.md   spec-driven foundation
  AGENTS.md · GEMINI.md                                  agent adapters
  docs/
    PLAYBOOK.md                      development constitution
    DECISIONS.md                     ADR index
    HANDOFFS.md                      handoff log
    TESTING.md                       Definition of Done
    decisions/ADR-*.md               architecture decisions
  specs/
    product/      PRD.md (v2.0) · VISION.md · SCOPE.md
    architecture/ ARCHITECTURE.md · DATA-MODEL.md · INTEGRATIONS.md · NFR.md
    FEATURES.md                      feature roadmap
    features/     F-000-foundations.md + others
  tasks/BOARD.md                     task board (phases 0-4)
  .claude/skills/
  src/ · frontend/ · tests/          implementation
```

## Status (Phase 0–4 Sprint)
**June 22, 2026**: Sprint kickoff. Architecture spec-driven (CLAUDE.md, API_CONTRACT.md, TASKS.md, PROMPTS.md). Database schema updated for projects, multi-source sources, memory facts. Phase 0 (stabilize seam) ready to start. All tests passing offline (LLM_PROVIDER=fake).

## Tech Stack Highlights
- **Backend**: Python 3.12 + FastAPI; tree-sitter (multi-language parsing); provider-abstracted LLM (Gemini/Groq free tier or local Ollama).
- **Frontend**: TypeScript + React (Vite); spec browser, graph explorer, source manager, specify tool.
- **Storage**: PostgreSQL (Neon free) + pgvector; Analysis DB (L1 + L4) + Spec DB (L2 + L3 + memory).
- **Agents**: Local MCP server + HTTP API; specs + memory facts accessible to Claude Code, Codex, Gemini.

## Hard Constraints
- **Zero cost**: no paid dependencies; free LLM tiers only.
- **Privacy**: source code stays local; DB stores structure, specs, summaries, embeddings — never raw source.
- **Offline**: all tests pass with `LLM_PROVIDER=fake EMBED_PROVIDER=fake`; no API calls in CI.
- **Static only**: pipeline reads files + calls model; never executes repo code or runs commands.
