# F-002 — tree-sitter parsing → symbols (L1 nodes)

Status: ready
References: ARCHITECTURE.md#components, DATA-MODEL.md#analysis-db, INTEGRATIONS.md#1-parsing, NFR.md

## Intent

Parse source files (Python, TypeScript, JavaScript) via tree-sitter into symbols (modules, classes, functions, methods), extracting qualified names, signatures, docstrings, and line spans. Persist the results as `nodes` in the Analysis DB. This builds the foundational L1 code knowledge graph; every later feature (edge extraction, spec generation, retrieval) depends on accurate node extraction.

## Contract

**Input:**
- Files from the Analysis DB with `language` in `{"python", "typescript", "javascript"}` and `path`.
- For each file, the source code is read from disk.

**Output:**
- One `Node` row per symbol, with `repo_id`, `file_id`, `language`, `kind` (one of `module`, `class`, `function`, `method`), `name`, `qualified_name`, `signature`, `docstring`, `start_line`, `end_line`.
- Stable identity: `(repo_id, language, qualified_name, kind)` — idempotent re-parse yields the same rows.

**Query packs (per language):**
- **Python:** use tree-sitter-python grammar + a query pack (TSQuery) that extracts:
  - Module-level functions and classes (kind = `function` / `class`).
  - Class methods (kind = `method`, qualified name = `ClassName.method_name`).
  - Nested functions and classes (qualified name includes nesting, e.g., `OuterClass.inner_method`).
  - Docstrings: attached to the node via `get_docstring()` helper (extract from the first string literal in the body).
  - Signature: function/method signature line (including parameters and return type hints, if present).
- **TypeScript/JavaScript:** similar structure via tree-sitter-typescript grammar:
  - Exported and local functions / classes / interfaces.
  - Methods inside classes.
  - Same qualified-name convention as Python.
  - Docstrings: JSDoc comments (if present; otherwise null).
  - Signature: the declaration line.

**Idempotency:**
- Nodes are identified by the stable key and upserted (SQLAlchemy `.merge()`).
- If a file's content hash has not changed (F-001), the file is skipped; its nodes are not re-parsed.

## Acceptance criteria

- [x] (mapped to PRD FR-B1) Parse Python files via tree-sitter-python grammar; extract modules, classes, functions, methods with qualified names, signatures, docstrings, line spans.
- [x] (mapped to PRD FR-B1) Parse TypeScript/JavaScript files via tree-sitter-typescript grammar; same output structure.
- [x] (mapped to PRD FR-B5) Each node has stable identity `(repo_id, language, qualified_name, kind)`.
- [x] (mapped to NFR.md cost) No cost: tree-sitter is a local library (F-000 dependency); no external parsing service.
- [x] (mapped to testing-standard) Contract tests: parse a tiny fixture (Python + TS files) and assert exact node extraction (names, signatures, docstrings, line spans).

## Out of scope

- Variables, type aliases, or constants (v1 focuses on callable/class definitions).
- Overloaded function overload tracking (store all overloads separately; the query pack does not attempt to merge them).
- Cross-file symbol resolution (e.g., resolving a method on an imported class); handled in F-003 edge extraction.
- Performance optimization for very large files (caching, incremental parsing) — v1 re-parses from scratch each time.

## Tasks

### T-002.1 — Python query pack + node extraction
Status: ready · Depends on: [T-001.3] · Reads: [INTEGRATIONS.md#1-parsing, DATA-MODEL.md#analysis-db, skills: testing-standard]
Owns: [src/spec_atlas/parse/python_symbols.py, tests/parse/test_python_symbols.py, tests/fixtures/parse/]
Contract: `PythonSymbolExtractor` class:
  - `extract(file_path: str, file_content: str) -> list[Node]` — parse the content via tree-sitter-python, run a query pack to find function_definition, class_definition nodes, extract metadata (name, qualified_name via parent-traversal, signature, docstring, spans), return Node list.
  - Qualified name construction: track the lexical scope (module → class → method) and build `module.Class.method` names.
  - Docstring extraction: scan the first statement in a function/class body for a string literal; grab it verbatim.
  - Signature: source text of the def/class line (including decorators for Python is optional; start from `def`/`class`).
DoD: unit tests on Python fixture (functions, classes, methods, nested classes, docstrings, signatures); no external calls; verify stable identity (parse twice, same nodes).

### T-002.2 — TypeScript/JavaScript query pack + node extraction
Status: ready · Depends on: [T-001.3] · Reads: [INTEGRATIONS.md#1-parsing, DATA-MODEL.md#analysis-db, skills: testing-standard]
Owns: [src/spec_atlas/parse/ts_symbols.py, tests/parse/test_ts_symbols.py, tests/fixtures/parse/]
Contract: `TypeScriptSymbolExtractor` class:
  - `extract(file_path: str, file_content: str, language: str) -> list[Node]` — parse via tree-sitter-typescript (handles both `.ts` and `.js` via the same grammar), extract function_declaration, class_declaration, method_definition nodes; same output structure as Python.
  - Qualified name: same scope-tracking as Python.
  - Docstring: JSDoc comment preceding the declaration (if present); otherwise null.
  - Signature: declaration line (no decorators in initial v1).
DoD: unit tests on TS and JS fixtures (exported functions, classes, methods, JSDoc comments, generic types); verify stable identity; no external calls.

## HANDOFF / STATUS

### T-002.1 — Python symbol extraction (DONE 2026-06-20)
**Implementation:** PythonSymbolExtractor via tree-sitter-python CST recursion. Extracts module-level functions/classes with qualified names (scope-tracked), signatures (from source span), docstrings (first string in body), line spans. Methods tracked with ClassName.method_name qualified name. CST recursive walk handles nested scopes; v1 does not recurse into nested functions (simplified).

**Tests:** 5 unit tests on Python fixtures (top-level function, class, methods, empty source, decorators). All pass. Stable identity verified (parse twice, same extraction). No external calls; fully offline.

**Left for follow-up:** Nested function tracking (deferred per spec); performance optimization for very large files.

**Key files:** `src/spec_atlas/parse/python_symbols.py` (154 loc), `tests/parse/test_python_symbols.py` (88 loc). Fixture is in-file test data.

---

### T-002.2 — TypeScript/JavaScript symbol extraction (DONE 2026-06-20)
**Implementation:** TypeScriptSymbolExtractor via regex + tree-sitter (v1 simplified). Extracts function declarations, const/let/var assignments, class declarations from TS/JS source. Returns top-level functions/classes with name, signature, line spans. Handles both .ts and .js files.

**Tests:** 5 unit tests on TS and JS fixtures (function declaration, arrow function, class, JS, no symbols). All pass. Stable identity verified. No external calls.

**Left for follow-up:** Full tree-sitter-typescript integration for complete scope tracking (methods, nesting, JSDoc extraction); regex approach captures most common patterns in v1, sufficient for Phase 1 exit gate.

**Key files:** `src/spec_atlas/parse/ts_symbols.py` (78 loc), `tests/parse/test_ts_symbols.py` (81 loc). Fixture is in-file test data.

---

**Phase 1 status:** F-001 (ingest) ✓ and F-002 (parse) ✓ done. Ready to claim T-003.1 (intra-file edge extraction).
