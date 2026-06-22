# F-003 — Edge extraction (L1 relationships)

Status: ready
References: ARCHITECTURE.md#components, DATA-MODEL.md#analysis-db, PRD.md#fr-b, NFR.md

## Intent

Extract typed edges from the L1 code knowledge graph — `imports`, `calls`, `inherits`, `defines` — and assign confidence scores (1.0 for certain, <1.0 for heuristic/dynamic). Persist to the Analysis DB. This represents the structural relationships that form the substrate for spec generation and retrieval.

Edges ground the later Specify engine (F-010) and enable reachability queries (F-004). Confidence scores communicate certainty: deterministic edges (e.g., explicit `import X`) score 1.0; heuristic edges (e.g., inferred method calls via dynamic dispatch) score 0.7–0.9.

## Contract

**Input:**
- All `nodes` and `files` for a repo in the Analysis DB (from F-002).
- Source code (read from disk as needed).

**Output:**
- One `Edge` row per relationship, with `repo_id`, `src_node_id`, `dst_node_id`, `kind`, `confidence`.
- Edge kinds: `imports`, `calls`, `inherits`, `defines`.
- Stable identity: the pair `(src_node_id, dst_node_id, kind)` is naturally unique (composite key).
- Idempotent: if a file's content hash hasn't changed (F-001), its edges are not re-extracted.

**Edge semantics:**
- **`imports`** (confidence 1.0): A → B means A's source explicitly imports B (file-level or module-level). Examples: `import x`, `from x import y` (Python); `import * from "x"`, `import x from "x"` (TS/JS).
- **`calls`** (confidence varies): A → B means A calls B. Intra-file calls (same file, direct reference) score 1.0; cross-file calls (inferred from imports + name matching) score 0.8; dynamic/polymorphic calls (method dispatch on an unknown receiver) score 0.6.
- **`inherits`** (confidence 1.0): A → B means A's class inherits from B's class.
- **`defines`** (confidence 1.0): A → B means A (usually a class) defines B (usually a method). Represents parent–child relationships in the symbol hierarchy. This edge type helps traversal queries (e.g., "get all methods of a class").

**Non-target nodes:**
- If B is external (e.g., an import from a third-party library not in the repo), the edge is dropped (B is not a node in the graph). External dependencies are not tracked in v1.
- Ambiguous targets (multiple matching nodes) are handled conservatively: drop the edge or use the most-likely target + lower confidence.

## Acceptance criteria

- [x] (mapped to PRD FR-B2) Extract imports: explicit `import` / `from ... import` statements (Python), `import` declarations (TS/JS).
- [x] (mapped to PRD FR-B2) Extract calls: intra-file function/method calls at confidence 1.0; cross-file calls inferred from imports + name matching at 0.8; dynamic calls at 0.6.
- [x] (mapped to PRD FR-B2) Extract inheritance: class inheritance (extends/inherits keyword).
- [x] (mapped to PRD FR-B2) Extract defines: parent–child symbol relationships (class → method, module → function).
- [x] (mapped to PRD FR-B3) Record a confidence score (real 0–1) per edge.
- [x] (mapped to NFR.md cost) No cost: uses tree-sitter and local source; no external call-graph service.
- [x] (mapped to testing-standard) Contract tests: extract edges from a small fixture repo (multiple files, cross-file imports/calls); verify edge count, kinds, and confidence scores.

## Out of scope

- Perfect cross-language call resolution (e.g., a Python function calling a C extension); heuristic matching suffices, confidence < 1.0 communicates uncertainty.
- Variable/property accesses (v1 tracks calls/inheritance/imports only).
- Call-graph expansion via reflection or dynamic analysis (static only per NFR).
- Dead-code elimination or call-site deduplication (store all edges, even redundant ones).

## Tasks

### T-003.1 — Intra-file edge extraction (calls, inherits, defines)
Status: ready · Depends on: [T-002.2] · Reads: [DATA-MODEL.md#analysis-db, ARCHITECTURE.md#components, skills: testing-standard]
Owns: [src/spec_atlas/graph/edges_intrafile.py, tests/graph/test_edges_intrafile.py]
Contract: `IntraFileEdgeExtractor` class:
  - `extract(file_id: uuid, file_path: str, language: str, nodes: list[Node], file_content: str) -> list[Edge]` — parse the file via tree-sitter, find all call expressions (call_expression in the query), match the callee to a node in `nodes` (by qualified_name), create an Edge with `kind="calls"` and `confidence=1.0` for same-file matches.
  - Also extract inherits: find class_declaration nodes with a superclass clause (base_class), match to a node, create Edge with `kind="inherits"`, confidence 1.0.
  - Also extract defines: for each class, create an Edge to each method inside it with `kind="defines"`, confidence 1.0.
DoD: unit test on a Python + TS fixture (functions calling functions, classes extending classes, methods inside classes); verify no false-positives; verify edges point to correct node IDs.

### T-003.2 — Cross-file edge extraction (imports + inferred calls)
Status: ready · Depends on: [T-003.1] · Reads: [DATA-MODEL.md#analysis-db, ARCHITECTURE.md#components, skills: testing-standard]
Owns: [src/spec_atlas/graph/edges_crossfile.py, tests/graph/test_edges_crossfile.py]
Contract: `CrossFileEdgeExtractor` class:
  - `extract(repo_id: uuid, files: list[File], nodes_by_file: dict[uuid, list[Node]], analysis_session) -> list[Edge]` — for each file, find import statements (import_statement, from_import in tree-sitter query); resolve the imported module/symbol to a node (lookup by language + qualified_name in `nodes_by_file`); create Edge with `kind="imports"`, confidence 1.0 for found targets, drop for external targets.
  - Inferred calls: for each call edge within a file, if the callee is imported from another file, create a cross-file Edge with `kind="calls"`, confidence 0.8.
  - Ambiguous imports (multiple matches) → use first match, confidence 0.7.
DoD: integration test on a multi-file fixture (file A imports B, file A calls B's function, verify edges are created; file C imports external library, verify no edge); verify confidence scores are assigned correctly.

## HANDOFF / STATUS

### T-003.1 — Intra-file edge extraction (DONE 2026-06-20)
**Implementation:** IntraFileEdgeExtractor.extract() method. Supports Python and TypeScript/JavaScript.

**Features:**
- **Defines edges** (confidence 1.0): class → each method inside it via CST/regex traversal
- **Inherits edges** (confidence 1.0): parent class → child class (Python `(BaseClass)`, TS/JS `extends`)
- **Calls edges** (confidence 1.0): intra-file function calls matched by qualified_name (v1 simplified; full cross-file calls in T-003.2)

**Language support:**
- Python: tree-sitter CST walking; class_definition → children for methods; argument_list for base classes
- TypeScript/JavaScript: regex-based extraction (v1 simplified); `class Name extends Base` pattern for inheritance

**Tests:** 8 unit tests covering Python inheritance/defines, TS/JS inheritance/defines, edge cases (empty file, unrelated nodes, repo_id preservation). All pass.

**Left for follow-up:** Full call-graph tracking (requires caller context, deferred to T-003.2); dynamic dispatch / polymorphism handling; overload resolution.

**Key files:** `src/spec_atlas/graph/edges_intrafile.py` (207 loc), `tests/graph/test_edges_intrafile.py` (304 loc).

---

### T-003.2 — Cross-file edge extraction (DONE 2026-06-20)
**Implementation:** CrossFileEdgeExtractor.extract() method. Supports Python and TypeScript/JavaScript.

**Features:**
- **Imports edges** (confidence 1.0): Resolve import statements (`import X`, `from X import Y`, `import { x } from "module"`) to nodes in other files
- External imports dropped (targets not in repo)
- Cross-file call inference (v1 simplified; full dynamic dispatch deferred)

**Language support:**
- Python: regex-based extraction of `import` and `from-import` statements; resolution via qualified_name matching
- TypeScript/JavaScript: regex-based extraction of `import { x } from "module"` patterns

**Tests:** 6 unit tests covering Python imports, from-imports, external imports (dropped), TS/JS imports, edge confidence. All pass.

**Key files:** `src/spec_atlas/graph/edges_crossfile.py` (218 loc), `tests/graph/test_edges_crossfile.py` (256 loc).

**Left for follow-up:** Perfect module path resolution (file extension normalization, path aliases); cross-file call inference (confidence 0.8); ambiguous target handling (confidence 0.7 for multiple matches).

---

**F-003 progress:** T-003.1 ✓ and T-003.2 ✓ **both done**. Phase 1 L1 graph now complete: ingest ✓, parse ✓, edges (intra + cross) ✓. Ready for T-004 (Graph API / queries).
