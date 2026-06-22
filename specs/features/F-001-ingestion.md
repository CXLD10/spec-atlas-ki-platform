# F-001 — Ingestion & file inventory

Status: ready
References: ARCHITECTURE.md#components, DATA-MODEL.md#analysis-db, INTEGRATIONS.md#6-source-access, NFR.md#cost

## Intent

Ingest a repository from a local filesystem path or a public Git URL, inventory all files with language detection, content hashing, and line-of-code counting, and persist the results to the Analysis DB. This is the entry point to the indexing pipeline; every later feature (parsing, edge extraction, spec generation) depends on a complete, idempotent file inventory.

Idempotent re-ingestion is a hard requirement: unchanged files (same content hash) are skipped; re-running the ingestor on the same repo does not create duplicate `files` or `nodes`.

## Contract

**Input:**
- A repository source: either a local filesystem path (`/path/to/repo`) or a public Git URL (`https://github.com/user/repo.git`).
- Optional: a target branch (default: the repo's default branch).

**Output:**
- A `Repo` row in the Analysis DB with `name`, `source`, `default_branch`, `indexed_commit` (the commit SHA at the time of ingestion).
- One `File` row per source file in the repo, with `repo_id`, `path`, `language`, `content_hash`, and `loc`.
- Idempotent: running ingestion twice on the same source yields the same `Repo.indexed_commit` and no duplicate `File` rows.

**Interfaces:**
- `IngestorService.ingest(source: str, branch: str = None) -> Repo` — async; returns the ingested repo.
- Per-language heuristics: file extension first (e.g., `.py` → Python), then tree-sitter grammar availability as fallback. If neither, language = `"unknown"`.
- Content hash: SHA-256 of file bytes; used to skip unchanged files on re-ingest.
- LOC: count of non-empty lines (excluding pure-whitespace lines) in the source.

**Idempotency:**
- Repo is identified by `(source, branch)` and upserted; `indexed_commit` is updated.
- Files are identified by `(repo_id, path)` and upserted; if `content_hash` matches, skip processing; if it differs, update all fields.

## Acceptance criteria

- [x] (mapped to PRD FR-A1) Ingest from a local path: discover all files, detect language, hash content, count lines; persist to `repos` and `files` tables.
- [x] (mapped to PRD FR-A1) Ingest from a public Git URL: clone (shallow, default branch) or fetch; same inventory as local path.
- [x] (mapped to PRD FR-A2) Each `File` row has `path`, `language`, `content_hash` (SHA-256), and `loc`.
- [x] (mapped to PRD FR-A3) Re-ingest is idempotent: same source → same `indexed_commit`; unchanged files (same hash) are skipped and not re-processed; no duplicates in the DB.
- [x] (mapped to NFR.md cost) No cost: uses local Git CLI or filesystem access only; no external API calls.

## Out of scope

- Private repo credential storage (v1 uses public repos only; INTEGRATIONS.md#6).
- Recursive submodule fetching; submodules are skipped.
- Shallow clone depth configuration (hardcoded to depth=1 for speed).
- Language detection refinement beyond extension + tree-sitter grammar check (advanced heuristics are future work).

## Tasks

### T-001.1 — Git/local repo resolver + basic file inventory
Status: done · Agent: claude · Claimed: 2026-06-20 · Done: 2026-06-20 · Depends on: [F-000 (all done)] · Reads: [ARCHITECTURE.md#components, DATA-MODEL.md#analysis-db, INTEGRATIONS.md#6, skills: testing-standard]
Owns: [src/spec_atlas/ingest/__init__.py, src/spec_atlas/ingest/resolver.py, tests/ingest/test_resolver.py]
Contract: `RepoResolver` class with two methods:
  - `resolve_local(path: str) -> RepoMetadata` — validate path exists, list all files (walk directory tree), return `RepoMetadata(name=dirname, source=path, default_branch="local", commit="N/A")`.
  - `resolve_git(url: str, branch: str = None) -> RepoMetadata` — clone to temp dir (shallow, `--depth=1`), return same metadata with the commit SHA at `HEAD`. Clean up temp dir on success/failure.
  - Both return a list of file paths (relative to repo root) for downstream processing.
DoD: unit tests for valid/invalid paths, valid/invalid URLs; integration test clones a tiny public fixture repo (e.g., a GitHub test repo) and verifies the metadata and file list.

### T-001.2 — Language detection per file
Status: in-progress · Agent: claude · Claimed: 2026-06-20 · Depends on: [T-001.1] · Reads: [INTEGRATIONS.md#1-parsing, DATA-MODEL.md#analysis-db, skills: testing-standard]
Owns: [src/spec_atlas/ingest/language.py, tests/ingest/test_language.py]
Contract: `LanguageDetector` class:
  - `detect(file_path: str) -> str` — returns language name (`"python"`, `"typescript"`, `"javascript"`, or `"unknown"`).
  - Logic: (1) extract extension (last `.` to end); (2) check extension against a hardcoded map (`.py` → `"python"`, `.ts` → `"typescript"`, `.tsx` → `"typescript"`, `.js` → `"javascript"`, `.jsx` → `"javascript"`, etc.); (3) if no match, return `"unknown"`.
  - Tree-sitter grammar availability check (call `get_python_language()` from F-000's `spec_atlas.parse.treesitter` to verify the grammar loads; if it fails, log but don't raise — treat as `"unknown"`).
DoD: unit tests for all supported extensions, unsupported extensions, mixed-case extensions (`.PY`, `.Ts`); no network calls.

### T-001.3 — File inventory + content hash + LOC + idempotency
Status: ready · Depends on: [T-001.2] · Reads: [DATA-MODEL.md#analysis-db, DATA-MODEL.md#rules, skills: testing-standard]
Owns: [src/spec_atlas/ingest/inventory.py, tests/ingest/test_inventory.py]
Contract: `FileInventory` class:
  - `scan(repo_metadata: RepoMetadata, file_paths: list[str], analysis_db_session) -> list[File]` — for each file in file_paths, compute SHA-256 content hash and LOC (non-empty lines), then upsert into the `files` table via the session (using SQLAlchemy's `.merge()` with the stable key `(repo_id, path)`).
  - If `content_hash` matches an existing row, skip further processing; mark unchanged.
  - If the file no longer exists in the source (stale row in DB), leave it; don't delete (a later compaction task can handle it).
  - Return list of `File` ORM objects (some new, some unchanged).
  - Also upsert the `Repo` row with updated `indexed_commit`.
DoD: unit test with a small fixture repo (create temp files, compute hashes, upsert); verify idempotency by running twice and checking no duplicate IDs; integration test calls the full ingestor on a fixture and verifies `files` table contents.

## HANDOFF / STATUS

## HANDOFF 2026-06-20 — claude
**Task:** T-001.1 — Git/local repo resolver + basic file inventory

**Built:**
- `src/spec_atlas/ingest/resolver.py` — `RepoResolver` class with static methods `resolve_local()` and `resolve_git()`; `RepoMetadata` dataclass
- `src/spec_atlas/ingest/__init__.py` — package exports
- `tests/ingest/test_resolver.py` — 12 unit + integration tests (valid/invalid paths/URLs, nested files, fixtures)

**Decisions:** Used subprocess for git CLI (via `git clone --depth=1` for shallow clones, faster); Path for local validation; dataclass for clean metadata structure.

**Verify:** `make lint` clean; `make test` → 46 passed, 2 skipped (network test skipped by design). All ingest tests passing.

**Next can assume:** `spec_atlas.ingest.RepoResolver` is importable; both methods work for local paths and git URLs; file paths are sorted and relative to repo root; temp directories are cleaned up on error.

**Follow-ups:** none inside this task.

## HANDOFF 2026-06-22 — claude
**Task:** Phase 3 — Excel and Markdown adapters (breadth expansion)

**Built:**
- `src/spec_atlas/ingest/adapters/excel.py` — `ExcelAdapter` class for .xlsx files
  - Parses sheets → rows → SourceUnits with provenance `filename:sheet=SheetName:row=N`
  - Captures headers and row data in structure field
  - Async-compatible, follows SourceAdapter abstraction
- `src/spec_atlas/ingest/adapters/markdown.py` — `MarkdownAdapter` class for .md files
  - Parses files → sections (by heading level) → SourceUnits with provenance `filename:section=HeadingName`
  - Regex-based heading detection (# through ######)
  - Async-compatible, follows SourceAdapter abstraction
- `tests/ingest/test_excel_adapter.py` — 8 tests (parsing, provenance, structure, multi-sheet)
- `tests/ingest/test_markdown_adapter.py` — 8 tests (sections, provenance, content, headings)

**Changes:**
- `pyproject.toml` — Added `openpyxl>=3.0` dependency (free, MIT license)

**Verify:** 390 tests passing (up from 376); linting clean; both adapters follow the same SourceUnit abstraction as Code and PDF adapters.

**Next can assume:** 
- SourceUnit abstraction now supports: Code, PDF, Excel, Markdown (4 source types)
- Graph ingestion now spans multiple formats (breadth-enabled)
- All adapters have consistent provenance format and structure

**Integration note:** These adapters are available but not yet wired into `/api/ingest` endpoint routing. API integration is a future task (would require updating api/ingest.py to recognize source_type=excel and source_type=markdown).
