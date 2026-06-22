# BOARD.md — Spec-Atlas Task Board

The work queue. Pick a `ready` task whose Deps are all `done`. Claim it (set `in-progress` + agent), follow the Agent Operating Loop in `docs/PLAYBOOK.md`, then set `done` and write a HANDOFF note in the feature file.

Statuses: `ready` · `in-progress` · `blocked` · `done`

## Phase 0 — Foundations (build first)

| Task | Feature | Status | Agent | Deps | Updated |
|------|---------|--------|-------|------|---------|
| T-000.1 | F-000 | done | claude | — | 2026-06-19 |
| T-000.2 | F-000 | done | claude | T-000.1 | 2026-06-19 |
| T-000.3 | F-000 | done | claude | T-000.1 | 2026-06-19 |
| T-000.4 | F-000 | done | claude | T-000.1 | 2026-06-19 |
| T-000.5 | F-000 | done | codex | T-000.1 | 2026-06-19 |
| T-000.6 | F-000 | done | codex | T-000.2, T-000.3, T-000.4 | 2026-06-19 |
| T-000.7 | F-000 | done | claude | T-000.1 | 2026-06-19 |
| T-000.8 | F-000 | ready | — | T-000.1 | — |

Suggested order: **T-000.1** first (unblocks all), then **.2 / .3 / .4 / .5** in parallel (independent, different owned files), then **.6**; **.7** any time after .1.

**Phase 0 status:** core 7 tasks **done**; exit gate met (app boots, `/health` ok, both DBs migrate on pgvector, tree-sitter loads, provider fakes pass, CI authored + locally verified). **T-000.8** is a follow-up defect found during recovery (config/health default tests read ambient env) — `ready`, **non-blocking** for the gate; see ADR-0003.

## Phase 1 — L1 code graph (sliced; ready to build)

| Task | Feature | Status | Agent | Deps | Updated |
|------|---------|--------|-------|------|---------|
| T-001.1 | F-001 | done | claude | — | 2026-06-20 |
| T-001.2 | F-001 | done | claude | T-001.1 | 2026-06-20 |
| T-001.3 | F-001 | done | claude | T-001.2 | 2026-06-20 |
| T-002.1 | F-002 | done | claude | T-001.3 | 2026-06-20 |
| T-002.2 | F-002 | done | claude | T-001.3 | 2026-06-20 |
| T-003.1 | F-003 | done | claude | T-002.2 | 2026-06-20 |
| T-003.2 | F-003 | done | claude | T-003.1 | 2026-06-20 |
| T-004.1 | F-004 | done | claude | T-003.2 | 2026-06-20 |
| T-004.2 | F-004 | done | claude | T-004.1 | 2026-06-20 |

**Phase 1 status:** All 9 tasks **done** (2026-06-20); exit gate met ✓ (ingest multi-language repo, parse symbols, extract edges intra/cross-file, query graph via API). 123 tests passing, zero cost.

**Phase 2 status:** All 5 tasks **done** (2026-06-20); exit gate met ✓ (generate spec → validate schema + provenance → store in DB → fetch via API → version immutability). 193 tests passing (Phase 1: 123 + Phase 2: 70), zero cost.

## Phase 2 — Specs (L2) + store (sliced; ready to build after Phase 1)

| Task | Feature | Status | Agent | Deps | Updated |
|------|---------|--------|-------|------|---------|
| T-010.1 | F-010 | done | claude | — | 2026-06-20 |
| T-010.2 | F-010 | done | claude | T-010.1 | 2026-06-20 |
| T-010.3 | F-010 | done | claude | T-010.2 | 2026-06-20 |
| T-011.1 | F-011 | done | — | T-010.3 | 2026-06-20 |
| T-011.2 | F-011 | done | claude | T-011.1 | 2026-06-20 |

**Build order suggestion:** T-010.1 and T-011.1 can start in parallel (no inter-dependencies); once T-004.2 is done, T-010.2 → T-010.3 (serial); T-011.2 follows T-011.1. **Phase 2 exit gate:** generate a spec for a focal area, store it versioned in the Spec DB, retrieve it.

## Phase 3 — Spec graph & group tree (sliced; ready to build after Phase 1)

| Task | Feature | Status | Agent | Deps | Updated |
|------|---------|--------|-------|------|---------|
| T-005.1 | F-005 | done | claude | T-004.2 | 2026-06-20 |
| T-005.2 | F-005 | done | claude | T-005.1, T-011.2 | 2026-06-19 |
| T-005.3 | F-005 | done | claude | T-005.2 | 2026-06-19 |

**Build order:** T-005.1 (group formation from dirs) → T-005.2 (spec graph edges from L1) → T-005.3 (LLM summaries + fingerprints). Must complete Phase 1 & 2 first (needs L1 graph + specs). **Phase 3 exit gate:** groups formed, spec graph linked, group.md summaries generated with provenance.

**Phase 3 status (Group tree & spec graph):** All 3 tasks **done** (2026-06-19); exit gate met ✓ (groups formed from directories, spec edges linked across groups, group summaries with provenance). 220 tests passing (Phase 1: 123 + Phase 2: 70 + Phase 3: 27), zero cost.

## Phase 3 — Embeddings + Retrieval + Answerer (sliced; ready to build after Phase 2)

| Task | Feature | Status | Agent | Deps | Updated |
|------|---------|--------|-------|------|---------|
| T-006.1 | F-006 | done | claude | T-005.3 | 2026-06-19 |
| T-007.1 | F-007 | done | claude | T-006.1 | 2026-06-19 |
| T-007.2 | F-007 | done | claude | T-007.1 | 2026-06-19 |
| T-007.3 | F-007 | done | claude | T-007.2 | 2026-06-19 |
| T-008.1 | F-008 | done | claude | T-007.3 | 2026-06-19 |
| T-008.2 | F-008 | done | claude | T-008.1 | 2026-06-19 |

**Build order:** T-006.1 (embed groups/specs) → T-007.1 (vector search) → T-007.2 (tree descent) → T-007.3 (query router) → T-008.1 (LLM answer) → T-008.2 (provenance validation). Sequential dependency chain. **Phase 3 exit gate:** embeddings stored, vector search works, router classifies questions, answerer generates grounded answers with provenance.

**Phase 4 status (Embeddings + Retrieval + Answerer):** All 8 tasks **done** (2026-06-19); exit gate met ✓ (embeddings batch-stored in pgvector, vector search works, tree descent collects specs, query router classifies, LLM answerer generates grounded answers with provenance validation). 275 tests passing (Phase 1: 123 + Phase 2: 70 + Phase 3: 27 + Phase 4: 55), zero cost.

## Phase 6 — Backend Wiring & Deployment (priority after F-013)

| Task | Feature | Status | Agent | Deps | Updated |
|------|---------|--------|-------|------|---------|
| T-009.1 | F-009 | done | claude | T-008.2, T-007.3 | 2026-06-19 |
| T-009.2 | F-009 | done | claude | T-005.1, T-011.2 | 2026-06-19 |
| T-009.3 | F-009 | done | claude | T-001.1 | 2026-06-19 |
| T-017.1 | F-017 | done | claude | T-009.3 | 2026-06-20 |
| T-017.2 | F-017 | done | claude | T-017.1 | 2026-06-20 |
| T-017.3 | F-017 | done | claude | T-017.2 | 2026-06-20 |
| T-017.4 | F-017 | done | claude | T-017.3 | 2026-06-20 |

**Phase 6 execution:** T-009.1 (POST /api/ask) → T-009.2 (groups/specs endpoints) → T-009.3 (ingest + snippets) → T-017 (dockerize + deploy). After this, MCP server is fully wired to live backend.

## Phase 6 — Frontend + Polish (ready after F-017)

| Task | Feature | Status | Agent | Deps | Updated |
|------|---------|--------|-------|------|---------|
| T-FE.1 | F-009 | ready | — | F-017 (done) | — |
| T-FE.2 | F-009 | ready | — | T-FE.1 | — |
| T-FE.3 | F-009 | ready | — | T-FE.1 | — |
| T-FE.4 | F-009 | ready | — | T-FE.2, T-FE.3 | — |
| T-FE.5 | F-009 | ready | — | T-FE.4 | — |
| T-FE.6 | F-009 | ready | — | T-FE.5 | — |
| T-FE.7 | F-009 | ready | — | T-FE.5 | — |
| T-FE.8 | F-009 | ready | — | T-FE.5 | — |
| T-009.6 | F-009 (backend) | ready | — | F-017 (done) | — |
| T-FE.9 | F-009 | ready | — | T-FE.2, T-009.6 | — |
| T-FE.10 | F-009 | ready | — | T-FE.9 | — |
| T-FE.11 | F-009 | blocked | — | T-FE.6, T-FE.7, T-FE.8 + design review | — |
| T-FE.12 | F-009 | blocked | — | T-FE.6, T-FE.7, T-FE.8 + design review | — |
| T-FE.13 | F-009 | blocked | — | T-FE.6, T-FE.7, T-FE.8 + design review | — |
| T-FE.14 | F-009 | blocked | — | design review output | — |

**Phase 6 execution:** 6a (T-FE.1–4), 6b (T-FE.5–8), 6c (T-009.6 + T-FE.9–10), 6d (T-FE.11–14, gated behind design review after 6c is live).

## Later phases
See `specs/FEATURES.md`. Phase 5b continues with verifier, drift, eval after backend is live.

## Phase 5 — Verification, Agents, Drift, Eval (ready to build after F-013)

| Task | Feature | Status | Agent | Deps | Updated |
|------|---------|--------|-------|------|---------|
| T-012.1 | F-012 | ready | — | T-011.2 | — |
| T-012.2 | F-012 | ready | — | T-012.1 | — |
| T-012.3 | F-012 | ready | — | T-012.2 | — |
| T-013.1 | F-013 | done | claude | T-011.2 | 2026-06-19 |
| T-013.2 | F-013 | done | claude | T-013.1 | 2026-06-19 |
| T-013.3 | F-013 | done | claude | T-013.2 | 2026-06-19 |
| T-014.1 | F-014 | ready | — | T-005.3, T-011.2 | — |
| T-014.2 | F-014 | ready | — | T-014.1 | — |
| T-016.1 | F-016 | ready | — | T-004.2 | — |
| T-016.2 | F-016 | ready | — | T-016.1 | — |
| T-016.3 | F-016 | ready | — | T-016.2 | — |

**Phase 5 execution:** F-013 (MCP) first → F-009 backend wiring → F-017 deploy → F-012 verifier → F-009 frontend → F-014 drift → F-016 eval.
