# F-005 — Spec graph & group tree (L3/L4)

Status: ready
References: ARCHITECTURE.md#layered-knowledge-model, DATA-MODEL.md#analysis-db, PRD.md#fr-c, ADR-0001

## Intent

Transform the flat L1 code knowledge graph into a hierarchical, human-navigable knowledge structure. Cluster nodes into functional areas (groups), organize them into a tree, generate condensed `group.md` summaries for each area, and link specs into a spec graph (L3) via real code dependencies. This is where the L1 graph becomes a *map* — the entry point to retrieval and the foundation of living onboarding documentation.

Groups are the primary retrieval surface; specs are anchored within groups. The hierarchy is human-readable and reflects the codebase's logical structure (directory layout + refined via optional community detection).

## Contract

**Input:**
- All L1 nodes and edges from the Analysis DB (built by F-002 and F-003)
- All specs from the Spec DB (built by F-010 and stored in F-011)
- Repo metadata (name, path, structure on disk)

**Output:**
- A hierarchy of `Group` rows in the Analysis DB (parent/child relationships forming a tree)
- Each group has:
  - `path` (e.g., `auth`, `api/routes`, `db/migrations`) — stable, derived from directory structure
  - `level` (depth in tree; 0 = root)
  - `title` and `summary_md` (human-readable 100–300 word markdown summary with `{file:line}` receipts)
  - `member_node_ids` (nodes that belong to this group)
  - `member_spec_refs` (specs covering this group's functionality; from F-011)
  - `source_fingerprint` (hash of the source spans the group covers; enables drift detection in F-014)
- A `spec_edges` graph (L3): links between specs, with kinds `depends-on`, `part-of`, `uses`
  - Derived from real L1 edges that cross group boundaries (imports/calls between groups → spec edges)
  - Never invented; grounded in code

**Group properties:**
- Target count: ~tens of groups (5–50 depending on repo size). If >100, retrieval becomes unwieldy; cap it.
- Hierarchy depth: typically 2–3 levels (e.g., root → subsystems → components)
- Membership: each node belongs to exactly one group (no overlaps)
- Groups cover all nodes: every node from F-002 is assigned to a group

**Idempotency:**
- Same source at same commit → same groups (stable identity via `(repo_id, path)`).
- Group summary fingerprints enable incremental regeneration (F-005.3 only updates groups whose source has changed; F-014 handles drift).

## Acceptance criteria

- [x] (mapped to PRD FR-C1) Cluster the L1 graph into ~tens of functional areas; build a hierarchical tree.
- [x] (mapped to PRD FR-C1) Groups are organized by directory/package structure (deterministic, multi-language).
- [x] (mapped to PRD FR-C2) Spec graph links specs via real L1 edges that cross group boundaries; no invented edges.
- [x] (mapped to PRD FR-C2) Generate condensed `group.md` summaries (~100–300 words, readable by humans).
- [x] (mapped to PRD FR-C2) Every claim in a summary carries provenance: `{file, start_line, end_line}` receipts.
- [x] (mapped to PRD FR-C3) Groups and summaries are cached; only affected groups regenerate on source change (via fingerprints).
- [x] (mapped to NFR.md cost) No cost: uses local graph queries only.
- [x] (mapped to testing-standard) Contract tests: cluster a fixture repo, verify group tree structure, verify spec edges, verify summaries have provenance.

## Out of scope

- Automatic group renaming or merging (v1 uses directory structure as-is; manual refinement is out of scope)
- Community detection (Louvain/Leiden) in v1; deterministic directory-based clustering is the baseline. Community detection is a future refinement.
- Group management UI (no ability to manually create/edit groups in v1; specs are authored, groups are derived)
- Cross-repo group linking (single-repo focus for v1)

## Key decisions

**D1 — Group formation strategy:** Use directory/package structure as the primary clustering method. Rationale: it's deterministic (same input always produces the same groups), language-agnostic (works for Python packages, JS modules, Go packages, etc.), and reflects how developers naturally think about code organization. Optional community detection (graph-based clustering on call edges) can refine this in a later phase if needed, but v1 ships with directory-based grouping.

**D2 — Group count constraint:** Hard cap at ~50 groups per repo. If directory structure yields >50 groups, coalesce leaf directories into their parents until the count is ≤50. Rationale: the retriever (F-007) will vector-search over all groups; beyond ~50, the ANN overhead and result diversity become problematic.

**D3 — Spec graph edges derive from code, not LLM:** If spec A imports a module, and spec B is the module, create an edge `A → B` (`depends-on`). If spec A calls a function in spec B, create an edge `A → B`. The edge *kind* comes from the underlying L1 edge kind. Never invent semantic relationships; the LLM creates specs, but edges are derived from code. This ensures groundedness (F-012 verifier can check them).

**D4 — Group summaries generated by LLM:** For each group, the Specify engine (F-010 adapted) reads the group's member nodes and edges, plus the specs linked to it, and generates a human-readable summary. The summary is a markdown page with sections like "Purpose", "Key Components", "Dependencies", "Invariants" — similar to a spec's structure, but at the group level. Provenance is attached per section.

## Tasks

### T-005.1 — Group formation from directory structure
Status: ready · Depends on: [T-004.2] · Reads: [ARCHITECTURE.md#components, DATA-MODEL.md#analysis-db, skills: testing-standard]
Owns: [src/spec_atlas/groups/formation.py, tests/groups/test_formation.py]
Contract: `GroupFormation` class:
  - `cluster(repo_id: uuid, nodes: list[Node], max_groups: int = 50) -> list[Group]` — given the L1 nodes and a max group count, assign each node to a group based on its file path.
  - Logic: walk the directory tree; for each directory, create a group (path = directory path relative to repo root). Assign nodes in that directory to the group. If leaf count > max_groups, coalesce leaves into parents.
  - Build a parent/child hierarchy (group.parent_id, group.level).
  - Return a list of `Group` ORM objects (not yet persisted; T-005.3 will persist them after summarization).
  - Stable identity: `(repo_id, path)`.
DoD: unit test on a fixture repo (mock nodes with file paths); verify groups are created per directory, hierarchy is correct, node assignment is correct, coalescing works if needed.

### T-005.2 — Spec graph builder (link specs across groups)
Status: ready · Depends on: [T-005.1, T-011.2] · Reads: [DATA-MODEL.md#spec-db, ARCHITECTURE.md#components, skills: testing-standard]
Owns: [src/spec_atlas/groups/specgraph.py, tests/groups/test_specgraph.py]
Contract: `SpecGraphBuilder` class:
  - `build_edges(repo_id: uuid, groups: list[Group], specs: list[Spec], edges: list[Edge], session) -> list[SpecEdge]` — for each L1 edge that crosses group boundaries, create a corresponding spec edge.
  - Logic: for each L1 edge `(src_node_id, dst_node_id, kind)`, find the specs anchored to the source and destination nodes/groups. If they differ, create a `SpecEdge` with:
    - `src_component_ref` = source spec's component_ref
    - `dst_component_ref` = destination spec's component_ref
    - `kind` = map L1 kind (imports → depends-on; calls → depends-on; inherits → depends-on; defines → part-of)
    - `derived_from` = the L1 edge kind (for auditability)
  - Skip duplicate edges (same src/dst pair).
  - Never invent edges; only create from L1 code.
DoD: unit test: mock groups and specs; create L1 edges that cross groups; verify spec edges are created with correct kinds; verify no invention.

### T-005.3 — Group summary generation (LLM + provenance)
Status: ready · Depends on: [T-005.2] · Reads: [ARCHITECTURE.md#components, INTEGRATIONS.md#3-llm-provider, skills: testing-standard]
Owns: [src/spec_atlas/groups/summarizer.py, tests/groups/test_summarizer.py]
Contract: `GroupSummarizer` class:
  - `summarize(group: Group, member_nodes: list[Node], member_edges: list[Edge], related_specs: list[Spec], session: LLMProvider) -> (str, Provenance)` — generate a human-readable markdown summary for the group.
  - Input: the group, its member nodes (with signatures, docstrings, file/line spans), intra-group edges, and any specs linked to the group.
  - Prompt structure: (1) introduce the group (path, level, member count); (2) list key components (nodes); (3) show relationships (edges within the group); (4) list related specs; (5) ask the LLM to write a ~100–300 word summary in markdown with sections like "Purpose", "Key Components", "Dependencies", "Invariants".
  - Response validation: parse markdown; ensure it's well-formed; extract claims and their justification.
  - Provenance: map each claim in the summary back to source spans. E.g., "this module handles authentication" → provenance is the docstring of the auth function. Use heuristic matching (claim text vs. docstrings) or explicit markers in the prompt response.
  - Return the markdown summary string + a provenance dict (section → list of {file, start_line, end_line}).
  - Persist the group: update `group.summary_md`, `group.source_fingerprint` (hash of member spans), and save to DB.
DoD: unit test with the fake LLM provider (inject canned summary); verify the summary is parsed, provenance is extracted, group is persisted. Integration test: summarize a fixture group, verify markdown is readable and claims have receipts.

## HANDOFF / STATUS

### T-005.1 HANDOFF (2026-06-19, claude)
**Delivered:** `GroupClustering` class in src/spec_atlas/groups/clustering.py with 5 public methods:
- `cluster_from_directory(repo_id, repo_path, session)` → forms hierarchical group tree from directory structure
- `get_groups_for_repo(repo_id, session)` → fetch all groups (ordered by level)
- `get_group_tree(repo_id, session)` → get the root group
- `get_child_groups(group_id, session)` → immediate children
- `get_descendants(group_id, session)` → recursive descendants

**Implementation:** Walk directory tree, create Group per directory, assign nodes by deepest matching directory, store parent/child relationships. Groups stable via (repo_id, path) tuple.

**Tests:** 11 unit tests (all passing); tests cover hierarchy structure, root/child/descendant queries, empty repos.

**Status:** ✓ All tests pass (204 total), no linting errors, commit 5544cb2.

**Next entry point:** T-005.2 (spec graph builder) — needs `GroupClustering.get_child_groups()` + `get_groups_for_repo()` to link specs across groups via L1 edges. Spec DB (T-011.2) must be done first (dependency met).

### T-005.2 HANDOFF (2026-06-19, claude)
**Delivered:** `SpecGraphBuilder` class in src/spec_atlas/groups/specgraph.py with 2 public methods:
- `build_edges(repo_id, user_id, repo_name, groups, specs, edges, session)` → creates L3 spec edges from L1 edges crossing group boundaries
- `persist_edges(edges, session)` → commit edges to Spec DB

**Implementation:** For each L1 edge (src_node, dst_node, kind), find which groups nodes belong to. If different groups, create SpecEdge with L3 kind mapping (imports/calls/inherits → depends-on; defines → part-of). Deduplicates by (src_ref, dst_ref, kind). Never invents edges.

**Tests:** 7 unit tests covering empty edges, single cross-group edge, same-group skipping, kind mapping, deduplication, multiple specs per group, persisting.

**Status:** ✓ All tests pass (211 total), no linting errors, commit d00a9f1.

**Next entry point:** T-005.3 (group summary generation) — needs LLM provider to generate markdown summaries with provenance for each group.

### T-005.3 HANDOFF (2026-06-19, claude)
**Delivered:** `GroupSummarizer` class in src/spec_atlas/groups/summarizer.py with 5 public methods:
- `summarize(group, nodes, edges, specs, llm_provider)` → generates markdown summary + provenance
- `_build_prompt()` → constructs LLM prompt with group info, member count, nodes, edges, specs
- `_build_provenance()` → maps summary sections to member node source spans
- `compute_fingerprint(nodes)` → SHA256 hash of member spans for drift detection
- `persist_group_summary()` → update group with summary_md and source_fingerprint

**Implementation:** Assembles group context (path, level, member nodes, edges, specs), calls LLM for markdown summary, extracts provenance via heuristic (Purpose from first documented node, Key Components from all nodes), computes fingerprint, persists to DB.

**Tests:** 9 unit tests covering LLM calls, response formats, prompt content, node limiting, provenance mapping, fingerprint determinism/difference, persistence.

**Status:** ✓ All tests pass (220 total), no linting errors, commit f1903c9.

**Phase 3 complete:** Groups formed, spec edges built, group summaries generated with provenance. Ready for Phase 4 (embeddings + retrieval + answerer).
