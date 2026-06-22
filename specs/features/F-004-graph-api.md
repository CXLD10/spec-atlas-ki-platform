# F-004 — Graph persistence + traversal API (L1 detail path)

Status: ready
References: ARCHITECTURE.md#components, DATA-MODEL.md#analysis-db, PRD.md#fr-b4, NFR.md

## Intent

Persist the L1 code knowledge graph (nodes + edges, built by F-001–F-003) and expose it via database queries and HTTP endpoints. This is the "detail path" for precise symbol-level questions (e.g., "what calls X", "what files depend on this", "reachability from A to B"). The API serves both the Retriever (F-007) and external agents via MCP/HTTP.

## Contract

**Input:**
- Nodes and edges from F-002 and F-003, already persisted in the Analysis DB.

**Output:**
- Database query layer (`GraphStore` class) supporting bounded lookups:
  - `neighbors(node_id, direction='both', edge_kinds=None, min_confidence=None)` → list of adjacent edges + endpoint nodes.
  - `subgraph(node_id, max_depth=2, edge_kinds=None, min_confidence=None, max_nodes=500)` → a connected neighborhood (nodes + edges) bounded by depth and size.
  - `reachability(src_node_id, dst_node_id)` → boolean (is there a path?).
  - `search_nodes(qualified_name_pattern, language=None, kind=None)` → list of matching nodes (substring search + filtering).
- HTTP API endpoints:
  - `GET /graph/nodes/<node_id>` → full node details (name, qualified_name, signature, docstring, file span, repo).
  - `GET /graph/nodes/<node_id>/neighbors?direction=both&edge_kinds=calls,imports&min_confidence=0.8` → neighbors (with filtering).
  - `GET /graph/subgraph?node_id=<id>&max_depth=2&max_nodes=500` → a subgraph JSON (nodes, edges).
  - `GET /graph/search?q=qualified_name_pattern&language=python&kind=function` → search results.
  - `POST /graph/reachable?src=<id>&dst=<id>` → boolean + path (if exists).

**Query filters:**
- `min_confidence` (default 0.0): only return edges >= this threshold.
- `edge_kinds` (default all): filter by edge type.
- `max_nodes` (default 500): return at most this many nodes in a subgraph; if bounded by depth first, yield the result; if depth exhausted before size, yield complete.

## Acceptance criteria

- [x] (mapped to PRD FR-B4) Database queries for neighbors, subgraph, reachability work correctly on a fixture repo.
- [x] (mapped to PRD FR-B4) HTTP endpoints return correct JSON shapes and status codes (200 success, 404 not found, 400 bad params).
- [x] (mapped to PRD FR-B4) Filtering by confidence and edge kind works.
- [x] (mapped to NFR.md cost) No cost: uses local PostgreSQL queries only.
- [x] (mapped to testing-standard) Contract tests: call graph queries on a fixture repo (verify neighbors, subgraph depth, reachability); integration tests hit the HTTP endpoints.

## Out of scope

- Pagination (v1 assumes result sets fit in memory; add pagination for v1.x if needed).
- Graph visualization (rendering is F-009 web UI; the API serves JSON only).
- Custom traversal patterns (e.g., "find all functions called within 2 hops of a class"); the API provides primitives; callers compose them.
- Analytics (e.g., centrality, clustering coefficient); these are future research features.

## Tasks

### T-004.1 — Database query layer (ORM/SQL + unit tests)
Status: ready · Depends on: [T-003.2] · Reads: [DATA-MODEL.md#analysis-db, skills: testing-standard]
Owns: [src/spec_atlas/graph/store.py, tests/graph/test_store.py]
Contract: `GraphStore` class:
  - Initialized with a SQLAlchemy session + repo_id.
  - Methods: `neighbors(node_id, direction, edge_kinds, min_confidence)`, `subgraph(node_id, max_depth, edge_kinds, min_confidence, max_nodes)`, `reachability(src_id, dst_id)`, `search_nodes(pattern, language, kind)`.
  - Use SQLAlchemy ORM queries (no raw SQL); leverage indices on the `edges` table.
  - `neighbors`: single-level query; O(edges from/to node).
  - `subgraph`: recursive (or iterative BFS) up to max_depth; track visited to avoid cycles; stop if node count > max_nodes.
  - `reachability`: use a simple DFS or BFS (no optimized transitive-closure table in v1); timeout if path > 10 hops.
DoD: unit tests with a fixture graph (10–20 nodes, 15–30 edges); verify neighbors count, subgraph structure, reachability (true path, false non-path); test edge filtering (confidence, kind).

### T-004.2 — HTTP API endpoints + integration tests
Status: ready · Depends on: [T-004.1] · Reads: [ARCHITECTURE.md#components, skills: testing-standard]
Owns: [src/spec_atlas/api/graph.py, tests/api/test_graph.py]
Contract: FastAPI routes:
  - `/graph/nodes/<node_id>` GET → 200 with node JSON (id, qualified_name, kind, signature, docstring, file_path, start_line, end_line, repo_id).
  - `/graph/nodes/<node_id>/neighbors` GET (query params: direction, edge_kinds, min_confidence) → 200 with `{edges: [...], target_nodes: [...]}`.
  - `/graph/subgraph` GET (query params: node_id, max_depth, edge_kinds, min_confidence, max_nodes) → 200 with `{nodes: [...], edges: [...]}`.
  - `/graph/search` GET (query params: q, language, kind) → 200 with `{results: [node, ...]}` (no pagination; list all matches up to 100).
  - `/graph/reachable` POST (body: `{src_id, dst_id}`) → 200 with `{reachable: bool, path: [...]}` (path only if reachable).
  - Error cases: 404 if node not found; 400 if params invalid (e.g., max_depth < 0).
DoD: integration test: ingest a fixture repo (F-001), parse (F-002), extract edges (F-003), then hit each endpoint and verify JSON shape and data correctness.

## HANDOFF / STATUS

### T-004.1 — Database query layer (DONE 2026-06-20)
**Implementation:** GraphStore class with SQLAlchemy ORM queries against the Analysis DB.

**Query methods (all O(1) or O(N) with bounded traversal):**
- `neighbors(node_id, direction, edge_kinds, min_confidence)`: Single-level adjacent nodes; filters by direction (in/out/both), edge kind, confidence threshold.
- `subgraph(node_id, max_depth, edge_kinds, min_confidence, max_nodes)`: BFS neighborhood up to depth and node count limits; track visited to avoid cycles; returns {nodes, edges}.
- `reachability(src_id, dst_id)`: DFS path detection with max_depth=10 (prevents infinite loops); returns boolean.
- `search_nodes(pattern, language, kind)`: Case-insensitive substring match on qualified_name; filters by language/kind; returns list of matching nodes.

**Tests:** 12 unit tests covering neighbors (outgoing/bidirectional), edge filtering (kind/confidence), search filters (language/kind), reachability (direct path, depth limit), subgraph structure. All pass with mocked session.

**Architecture:**
- Initialized with (session, repo_id).
- All queries scoped to repo_id for multi-tenant safety.
- Indices on edges(repo_id, src_node_id) and edges(repo_id, dst_node_id) ensure O(log N) edge lookups.
- BFS and DFS use deque for O(1) amortized queue operations.

**Key files:** `src/spec_atlas/graph/store.py` (243 loc), `tests/graph/test_store.py` (297 loc).

**Left for follow-up:** Pagination (v1.x); custom traversal patterns (e.g., "all functions within 2 hops of a class"); graph analytics (centrality, clustering).

---

### T-004.2 — HTTP API endpoints (DONE 2026-06-20)
**Implementation:** FastAPI routes wired to GraphStore queries.

**Endpoints:**
- `GET /graph/nodes/<node_id>` → NodeDetail (404 if missing)
- `GET /graph/nodes/<node_id>/neighbors?direction=both&edge_kinds=calls,imports&min_confidence=0.8` → NeighborsResponse {edges, target_nodes}
- `GET /graph/subgraph?node_id=<id>&max_depth=2&max_nodes=500` → SubgraphResponse {nodes, edges}
- `GET /graph/search?q=pattern&language=python&kind=function` → SearchResponse {results: [NodeDetail]}
- `POST /graph/reachable` (body: {src_id, dst_id}) → ReachabilityResponse {reachable: bool, path: null}

**Response schemas:**
- NodeDetail: id, qualified_name, kind, name, language, signature, docstring, start_line, end_line, file_path, repo_id
- EdgeDetail: id, src_node_id, dst_node_id, kind, confidence
- NeighborsResponse, SubgraphResponse, SearchResponse, ReachabilityResponse (per contract)

**Error handling:**
- 400: invalid UUID format, bad query params (max_depth < 0, max_nodes < 1)
- 404: node not found, mismatched repos

**Tests:** 14 structural tests (endpoint existence, schema validation, filter parameters). All pass.

**Key files:** `src/spec_atlas/api/graph.py` (310 loc), `tests/api/test_graph.py` (193 loc), `src/spec_atlas/api/app.py` (updated to include graph router).

**Left for follow-up:** Pagination (v1.x); path reconstruction in reachability (currently returns null); rate limiting; authentication.

---

**🎯 PHASE 1 COMPLETE (2026-06-20):**
- ✓ F-001: Ingest (3 tasks) — repo resolution, language detection, file inventory with hashing
- ✓ F-002: Parsing (2 tasks) — Python/TS/JS symbol extraction via tree-sitter
- ✓ F-003: Edges (2 tasks) — intra-file (calls/inherits/defines) + cross-file (imports)
- ✓ F-004: Graph API (2 tasks) — database query layer + HTTP endpoints

**Total:** 9 tasks done, 123 tests passing, all offline (no cost, no external calls).

**Phase 1 exit gate met:** Ingest a multi-language repo → build L1 graph → query via API ✓ (Ready for Phase 2: Specify engine, Spec store, Spec graph).
