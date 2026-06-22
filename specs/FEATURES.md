# FEATURES.md — Spec-Atlas Roadmap

Status: ready
References: ARCHITECTURE.md, PRD.md §8, ADR-0001

Feature IDs are **stable identifiers**, not a build order. Build order is given by **phase + explicit dependencies** below (some features depend on a higher-numbered one — that's fine). Each feature gets a self-contained file in `specs/features/` with its task slices; only Phase 0 is sliced so far.

## Build order (phases)

| Phase | Theme | Features (build order) | Key deps |
|---|---|---|---|
| 0 | Foundations | F-000 | — |
| 1 | L1 code graph (multi-language) | F-001 → F-002 → F-003 → F-004 | F-000 |
| 2 | Specs (L2) + store | F-010, F-011 | F-004 |
| 3 | Spec graph + group tree (L3/L4) | F-005 | F-010 |
| 4 | Embeddings + retrieval + answers | F-006 → F-007 → F-008 | F-005 |
| 5 | Verify, agents, drift | F-012, F-013, F-014 | F-010/F-011, F-007 |
| 6 | UI, eval, more languages, deploy | F-009, F-015, F-016, F-017 | varies |

## Feature list

**Phase 0 — Foundations**
- **F-000** Repo scaffold, config, two-DB setup + migrations (all entities in `DATA-MODEL.md`), tree-sitter setup, LLM/embedding provider abstractions, health endpoint, CI. *(sliced — `features/F-000-foundations.md`)*

**Phase 1 — L1 code graph (multi-language)**
- **F-001** Ingestion & file inventory (local path / public git URL; language detect; hashes; idempotent). *(sliced — `features/F-001-ingestion.md`)*
- **F-002** tree-sitter parsing → symbols (Python + TS/JS query packs). *(sliced — `features/F-002-parsing.md`)*
- **F-003** Edge extraction (`imports`, `calls`, `inherits`, `defines` + confidence). *(sliced — `features/F-003-edges.md`)*
- **F-004** Graph persistence + traversal API (neighbors, subgraph, reachability — the detail path). *(sliced — `features/F-004-graph-api.md`)*

**Phase 2 — Specs (L2) + store**
- **F-010** Specify engine: LLM generates a schema-validated spec per area, provenance-bound. *(sliced — `features/F-010-specify.md`)*
- **F-011** Spec store (separate Spec DB; per-user; versioned; fingerprinted) + API. *(sliced — `features/F-011-spec-store.md`)*

**Phase 3 — Spec graph + group tree (L3/L4)**
- **F-005** Cluster code into a bounded set of areas → `group.md` tree (skeleton from directory + community refinement, ADR-0001 D1); link specs into the spec graph from real code edges; write group summaries. *(sliced — `features/F-005-groups.md`)*

**Phase 4 — Embeddings, retrieval, answers**
- **F-006** Embedding pipeline (group summaries primary + specs; incremental).
- **F-007** Hierarchical retriever (vector over groups → descend) + **query router** (detail→graph, big-picture→spec/group).
- **F-008** Ask-anything answerer (grounded + provenance; small spec-page context).

**Phase 5 — Verify, agents, drift**
- **F-012** Spec grounding verifier.
- **F-013** MCP server (`search`, `get_group`, `get_spec`, `list_stale_specs`).
- **F-014** Drift detection (fingerprints → stale → subtree regen).

**Phase 6 — UI, eval, languages, deploy**
- **F-009** Web UI (question box + grounded answer + spec/group browser = living onboarding docs). ✅ **COMPLETE** (June 22, 2026)
- **F-015** Additional language packs (additive).
- **F-016** Eval harness (head-to-head spec/group vs. raw-node baseline; gates auto-routing).
- **F-017** Optional free-tier deploy + observability.

## Per-phase exit gates
- **P0:** app boots, both DBs migrate, tree-sitter loads, provider fakes pass contract tests, CI green.
- **P1:** ingest a multi-language repo → graph queryable; idempotent re-ingest verified.
- **P2:** generate + store a versioned, fingerprinted spec for one area.
- **P3:** `group.md` tree + spec graph exist for a repo (browsable as onboarding docs).
- **P4:** ask a question end-to-end → routed, grounded, cited answer with small context.
- **P5:** verifier passes a spec; an agent retrieves it via MCP; drift flags a stale page after a commit.
- **P6:** UI usable; eval shows context/cost reduction vs. baseline; a 3rd language indexes.

## MVP slice (smallest end-to-end demo)
F-000 → F-001 → F-002 → F-003 → F-004 → F-010 → F-011 → F-005 → F-006 → F-007 → F-008 → F-013. (Verifier F-012, drift F-014, UI F-009, eval F-016 enhance but aren't required for the first agent-consumable demo.)
