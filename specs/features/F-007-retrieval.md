# F-007 — Hierarchical retriever + query router

Status: ready
References: ARCHITECTURE.md#components, DATA-MODEL.md#analysis-db, PRD.md#fr-e, NFR.md

## Intent

Enable fast, bounded retrieval: embed a user query, search for relevant groups via ANN (pgvector), descend the group tree to collect specs + source spans, and route the question (big-picture vs. detail) to the right retrieval strategy. The retriever assembles a compact, grounded context for the answerer (F-008).

## Contract

**Input:**
- User query string
- Analysis DB with embeddings (from F-006)
- Group tree (from F-005)
- Specs (from F-011)
- L1 graph (from F-001 to F-004)

**Output:**
- A bounded context object:
  - `strategy`: "vector_search" or "graph_query" (from router)
  - `matched_groups`: list of top-K groups (with similarity scores)
  - `specs`: list of specs in matched groups + descendants
  - `source_spans`: list of {file, start_line, end_line}
  - `tree_path`: hierarchy from root to matched group (for navigation)
- At most N specs, M source spans (e.g., 8 specs, 100 spans max)

**Query routing logic:**
- "What calls X?" → `"graph_query"` (detail; use L1 graph API)
- "Why is X needed?" / "Explain X" → `"vector_search"` (big-picture; use embeddings + descent)
- Keyword heuristic (v1): if query has "call", "depend", "import" → graph; else → vector

**Vector search pipeline:**
1. Embed query (384-dim)
2. ANN search in pgvector (top-K, e.g. K=3)
3. Return matched group IDs + similarity scores

**Tree descent pipeline:**
1. From matched groups, walk downward
2. Collect specs within each group + child groups
3. Collect source spans from specs + nodes
4. Cap at max_specs, max_spans

**Idempotency:**
- Same query → same embedding (model deterministic)
- Same groups + specs → same context (stable retrieval)

## Acceptance criteria

- [x] (mapped to PRD FR-E1) Vector search: embed query, ANN over group embeddings, return top-K groups.
- [x] (mapped to PRD FR-E2) Tree descent: from matched group, walk to descendants, collect specs + spans, bounded by count.
- [x] (mapped to PRD FR-E3) Query router: classify question type, route to "vector_search" or "graph_query" strategy.
- [x] (mapped to PRD FR-E4) Retrieve bounded context: at most N specs, M spans, assembled with hierarchy.
- [x] (mapped to NFR.md cost) ANN search is O(log N) via pgvector; descent is O(k) where k = group size.
- [x] (mapped to testing-standard) Unit tests: vector search on fixture embeddings, tree descent on fixture groups, router classification on fixture questions.

## Out of scope

- Pagination (context fits in memory; retrieve all at once)
- Hybrid search (vector only for v1)
- ML-based routing (keyword heuristic for v1; F-016 upgrades to ML)
- Relevance ranking within result set (return in search order; answerer prioritizes later)

## Tasks

### T-007.1 — Vector search over groups
Status: ready · Depends on: [T-006.1] · Reads: [DATA-MODEL.md#analysis-db, INTEGRATIONS.md#4-embeddings, skills: testing-standard]
Owns: [src/spec_atlas/retrieve/search.py, tests/retrieve/test_search.py]
Contract: `VectorSearch` class:
  - `search(query: str, k: int = 3, session: Session) -> list[(Group, float)]` — embed query, ANN search, return top-K groups with similarity scores.
  - Use `EmbeddingProvider.embed(query)` to embed the query.
  - Use pgvector `<->` operator for ANN search in the Analysis DB.
  - Handle zero results gracefully (return empty list).
DoD: unit test: search for fixture questions on fixture embeddings, verify top results are relevant, verify scores are 0–1.

### T-007.2 — Tree descent (bounded context assembly)
Status: ready · Depends on: [T-007.1] · Reads: [DATA-MODEL.md#analysis-db, skills: testing-standard]
Owns: [src/spec_atlas/retrieve/descent.py, tests/retrieve/test_descent.py]
Contract: `TreeDescent` class:
  - `descend(group_id: uuid, session: Session, max_specs: int = 8, max_spans: int = 100) -> Context` — walk from group downward, collect specs + source spans, cap at max counts.
  - Return a Context object: {matched_group, child_groups, specs, source_spans, tree_path}.
  - Depth-first or breadth-first traversal (prefer DFS; stop early if counts hit max).
  - Include tree path (root → matched → descendants) for navigation.
DoD: unit test: descend from fixture group, verify specs are collected, verify counts respect limits, verify tree_path is correct.

### T-007.3 — Query router (classify question type)
Status: ready · Depends on: [T-007.2] · Reads: [skills: testing-standard]
Owns: [src/spec_atlas/retrieve/router.py, tests/retrieve/test_router.py]
Contract: `QueryRouter` class:
  - `route(query: str) -> "vector_search" | "graph_query"` — classify question, return routing strategy.
  - Heuristic v1: keyword matching (if query contains "call", "depend", "import", "reference" → "graph_query"; else → "vector_search").
  - Later (F-016): upgrade to ML classifier; for now, keep it simple.
DoD: unit test: classify fixture questions (both types), verify routing heuristic works as expected.

## HANDOFF / STATUS

### T-007.1/2/3 HANDOFF (2026-06-19, claude)
**T-007.1 - VectorSearch:** Embed query, ANN search groups via pgvector `<->` operator, return top-K with similarity scores ∈ [0,1].

**T-007.2 - TreeDescent:** Walk group hierarchy downward, collect matched group, child groups, specs, source spans. Respects max_specs/max_spans limits. Returns Context with tree_path for navigation.

**T-007.3 - QueryRouter:** Classify question type via keyword substring matching. Keywords: "call", "depend", "import", "reference", "invoke", "inherit" → graph_query; else → vector_search.

**Tests:** 27 unit tests covering all strategies. 275 tests passing (Phases 1-4: 123+70+27+55), all offline.

**Status:** ✓ All retrieval tasks complete. Commit 443008c. Ready for Phase 5 (verification/drift/eval) or answer integration. Next: F-008 answerer HANDOFF.
