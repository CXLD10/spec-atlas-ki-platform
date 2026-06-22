# F-000 — Foundations

Status: done <!-- exit gate met 2026-06-19 (recovery): app boots, /health ok, both DBs migrate on pgvector, tree-sitter loads, provider fakes pass, CI authored + locally verified. T-000.8 (test-isolation hardening) tracked separately, non-blocking. -->
References: ARCHITECTURE.md, DATA-MODEL.md, INTEGRATIONS.md, NFR.md; skills: testing-standard

## Intent
Stand up the skeleton every later feature builds on: repo scaffold, config, both databases with migrations for all `DATA-MODEL.md` entities, tree-sitter setup, the LLM and embedding provider abstractions (with offline fakes), a health endpoint, and CI.

## Contract
- A Python package `spec_atlas` (FastAPI app) that boots locally with one command.
- Config from env (`ANALYSIS_DB_URL`, `SPEC_DB_URL`, `LLM_PROVIDER`, `EMBED_PROVIDER`, provider keys), documented in `.env.example`.
- Migrations create the Analysis DB (repos, files, nodes, edges, groups, embeddings + pgvector) and Spec DB (specs, spec_edges).
- tree-sitter installed with at least one grammar loadable (Python) — proves the parsing toolchain works.
- `LLMProvider` + `EmbeddingProvider` interfaces, each with a real default and a deterministic **fake** for tests/CI.
- `GET /health` reports app + both DB connections + provider modes.
- CI runs lint + tests offline (fakes), green.

## Acceptance criteria
- [x] `make dev` starts the API; `GET /health` ok with both DBs reachable. _(verified during recovery: `make dev` boots; `/health`→full shape; with both DBs migrated+reachable the DB legs report `ok`. T-000.6 HANDOFF.)_
- [x] `make migrate` applies all migrations to both DBs; tables match `DATA-MODEL.md`; pgvector enabled; `embeddings.vector` dim = 384. _(verified against ephemeral pgvector pg16: both DBs migrated; tables = repos/files/nodes/edges/groups/embeddings + specs/spec_edges; `vector` ext 0.8.2; `vector(384)`.)_
- [x] tree-sitter loads a grammar and parses a sample file into a CST.
- [x] `EmbeddingProvider` default → 384-dim vectors; fake deterministic/offline. _(T-000.3; tests/embed green.)_
- [x] `LLMProvider` default reaches the configured free model (manual/flagged); fake returns canned structured output. _(T-000.4; fake offline; gemini behind `LLM_PROVIDER=gemini`+key, not in CI.)_
- [x] CI green using `LLM_PROVIDER=fake EMBED_PROVIDER=fake` + an ephemeral Postgres; no network/cost; no secrets needed. _(T-000.7 `.github/workflows/ci.yml`; every step verified locally — offline `make test` 34 passed/1 skipped, `make migrate`+`pytest tests/db` green on pgvector. A live GitHub Actions run requires a remote, which does not exist yet — see docs/status.)_
- [x] `.env.example` documents every var; `.env` gitignored. _(T-000.1.)_

## Out of scope
Any parsing/graph/spec/retrieval logic (F-001+).

## Tasks

### T-000.1 — Repo scaffold & tooling
Status: done · Agent: claude · Claimed: 2026-06-19 · Done: 2026-06-19 · Depends on: [] · Reads: [ARCHITECTURE.md#module-layout, NFR.md, skills: testing-standard]
Owns: [pyproject.toml, src/spec_atlas/__init__.py, src/spec_atlas/config.py, Makefile, .env.example, .gitignore, ruff/format config]
Contract: installable package; `make` targets `dev/test/lint/migrate`; env-validated config. tree-sitter + bindings listed as deps.
DoD: `pip install -e .` works; `make lint`/`make test` run; `.env.example` lists all INTEGRATIONS vars; `.env` gitignored.

### T-000.2 — Database clients + migrations (both DBs)
Status: done · Agent: claude · Claimed: 2026-06-19 · Done: 2026-06-19 · Depends on: [T-000.1] · Reads: [DATA-MODEL.md, INTEGRATIONS.md#2-postgresql]
Owns: [src/spec_atlas/db/analysis.py, src/spec_atlas/db/spec.py, migrations/*, src/spec_atlas/db/__init__.py]
Contract: SQLAlchemy 2.0 models + Alembic migrations for the Analysis DB (repos, files, nodes, edges, groups, embeddings + pgvector) and Spec DB (specs, spec_edges). Two engines/sessions.
DoD: `make migrate` applies to two empty DBs; pgvector enabled; vector dim 384; a test creates+queries one row per table including a `groups` parent/child and a `spec_edges` row.

### T-000.3 — Embedding provider abstraction (+ default + fake)
Status: done · Agent: claude · Claimed: 2026-06-19 · Done: 2026-06-19 · Depends on: [T-000.1] · Reads: [INTEGRATIONS.md#4-embeddings, NFR.md]
Owns: [src/spec_atlas/embed/base.py, embed/fastembed_provider.py, embed/fake.py, tests/embed/*]
Contract: `EmbeddingProvider.embed(texts) -> vectors`; default fastembed bge-small (384); fake deterministic hash→vector.
DoD: default → 384-dim (skipped in CI if model uncached); fake deterministic/offline via `EMBED_PROVIDER=fake`; contract test asserts dim + determinism.

### T-000.4 — LLM provider abstraction (+ default + fake)
Status: done · Agent: claude · Claimed: 2026-06-19 · Done: 2026-06-19 · Depends on: [T-000.1] · Reads: [INTEGRATIONS.md#3-llm-provider, NFR.md]
Owns: [src/spec_atlas/llm/base.py, llm/gemini_provider.py (or groq), llm/fake.py, tests/llm/*]
Contract: `LLMProvider.complete(messages, schema=None) -> str|dict`; structured-output validates against JSON Schema; fake returns canned output by prompt tag; 429/timeout retry+backoff.
DoD: fake via `LLM_PROVIDER=fake` offline; real provider reachable behind a flag (not CI); retry/backoff unit-tested.

### T-000.5 — tree-sitter setup
Status: done · Agent: codex · Claimed: 2026-06-19 · Done: 2026-06-19 · Depends on: [T-000.1] · Reads: [INTEGRATIONS.md#1-parsing]
Owns: [src/spec_atlas/parse/treesitter.py, tests/parse/test_treesitter_smoke.py, sample fixtures]
Contract: load the Python grammar and parse a sample file into a CST; expose a thin wrapper the F-002 parser will build on.
DoD: smoke test parses a fixture and finds expected top-level nodes; grammar load documented.

### T-000.6 — Health endpoint + app wiring
Status: done · Agent: codex · Claimed: 2026-06-19 · Done: 2026-06-19 · Depends on: [T-000.2, T-000.3, T-000.4] · Reads: [ARCHITECTURE.md]
Owns: [src/spec_atlas/api/app.py, api/health.py, tests/api/test_health.py]
Contract: FastAPI app with DI'd providers + DB sessions; `GET /health` → `{status, analysis_db, spec_db, llm, embed}`.
DoD: `make dev` boots; health test passes with fakes + test DB.

### T-000.7 — CI (offline, free)
Status: done · Agent: claude · Claimed: 2026-06-19 · Done: 2026-06-19 · Depends on: [T-000.1] · Reads: [skills: testing-standard, NFR.md]
Owns: [.github/workflows/ci.yml]
Contract: GitHub Actions runs lint + tests with fake providers + an ephemeral Postgres; no external network/cost.
DoD: CI green on a clean clone; no secrets required.

### T-000.8 — Make config/health default tests env-hermetic (defect found in recovery)
Status: ready · Depends on: [T-000.1] · Reads: [skills: testing-standard]
Owns: [tests/unit/test_config.py, tests/api/test_health.py]
Contract: `test_defaults_are_offline_and_zero_cost` and `test_health_reports_degraded_when_databases_are_not_configured` construct `Settings(_env_file=None)` but pydantic still reads `os.environ`, so they FAIL when `ANALYSIS_DB_URL`/`SPEC_DB_URL` are present in the ambient env (e.g. a dev with DB URLs in `.env`, or a single-command CI run with DB env). Harden them (e.g. `monkeypatch.delenv` the DB vars, or pass explicit `analysis_db_url=None`) so `make test` is green regardless of ambient env.
DoD: with `ANALYSIS_DB_URL`/`SPEC_DB_URL` exported, `make test` (full suite) is green; the two tests assert true defaults independent of the environment.
Note: NOT a blocker for the F-000 exit gate — CI (T-000.7) sidesteps it by scoping DB env to the `db-integration` job only. Tracked per the playbook ("found extra work → new ready task"); see ADR-0003.

## HANDOFF / STATUS
_(agents append HANDOFF notes here per the playbook)_

## HANDOFF 2026-06-19 — claude
**Task:** T-000.1 — Repo scaffold & tooling.
**Built:**
- `pyproject.toml` — hatchling package `spec-atlas`, `requires-python = ">=3.12"`, all
  F-000 runtime deps (fastapi/uvicorn, pydantic[-settings], sqlalchemy 2.0, alembic,
  psycopg[binary], pgvector, tree-sitter + python/js/ts grammars, fastembed, httpx,
  tenacity, jsonschema) + `[dev]` (pytest, pytest-cov, ruff); ruff + pytest config
  (markers `db`, `real_provider`).
- `src/spec_atlas/__init__.py`, `src/spec_atlas/config.py` — env-validated
  `Settings` (pydantic-settings) with offline-fake defaults; `get_settings()` cached;
  `.offline` helper.
- `Makefile` — `setup/install/dev/test/test-real/lint/format/migrate/clean` (uv-based
  setup; `test`/`lint` offline with fakes).
- `.env.example` — documents every var (ANALYSIS_DB_URL, SPEC_DB_URL, LLM_PROVIDER,
  EMBED_PROVIDER, LLM_MODEL, EMBED_MODEL, EMBED_DIM, GEMINI/GROQ keys, OLLAMA_HOST).
- `.gitignore` — `.env` ignored, `.env.example` tracked.
- `tests/unit/test_config.py` — defaults/offline, env override, invalid-provider
  rejection, cache.
**Decisions:** ADR-0002 — Python 3.12 via uv standalone interpreter (no sudo); both
providers default to `fake` (offline-first), real providers opt-in via env; DB URLs
optional so the app constructs without a DB.
**Verify:** `pip install -e .` ok; `make lint` clean; `make test` → 4 passed (offline).
**Next can assume:** importable `spec_atlas` package; `spec_atlas.config.get_settings()`;
venv at `.venv` (run `make setup` on a fresh clone); `make` targets exist (`migrate`
wired but needs T-000.2's Alembic env; `dev` needs T-000.6's app).
**Follow-ups:** none. T-000.2/.3/.4/.5 are now unblocked (deps on T-000.1 satisfied).

## HANDOFF 2026-06-19 — claude
**Task:** T-000.2 — Database clients + migrations (both DBs).
**Built:**
- `src/spec_atlas/db/analysis.py` — `AnalysisBase` + models `Repo, File, Node, Edge,
  Group, Embedding` (L1 graph + L4 groups + pgvector embeddings). Stable node identity
  `uq_nodes_identity (repo_id, language, qualified_name, kind)`; check constraints on
  node/edge kinds + edge confidence 0–1; `embeddings` composite PK
  `(owner_kind, owner_ref, model)` with `Vector(384)`; self-referential `groups.parent_id`.
- `src/spec_atlas/db/spec.py` — `SpecBase` + `Spec, SpecEdge` (L2/L3). `uq_specs_version
  (user_id, repo, component_ref, version)`; status check; spec-graph `derived_from`. No
  FKs into the Analysis DB (cross-DB refs by value).
- `src/spec_atlas/db/__init__.py` — `make_engine`, lazy `analysis_engine/spec_engine`
  and `analysis_session/spec_session` (two independent engines; URLs from config; clear
  error if a URL is unset).
- `alembic.ini` + `migrations/{env.py,script.py.mako,versions/0001_initial.py}` —
  **multidb** pattern: one `alembic upgrade head` migrates BOTH DBs (each gets its own
  `alembic_version`). `0001` enables `CREATE EXTENSION vector` on the Analysis DB then
  builds every table from the model metadata (schema cannot drift from models).
- Tests: `tests/unit/test_db_models.py` (offline: table sets, vector dim 384, stable-id
  + version unique constraints, embeddings PK, no cross-DB FK); `tests/db/` roundtrip
  (creates+queries one row per table incl. a groups parent/child pair and a spec_edges
  row), marked `db` and auto-skipped without Postgres.
**Decisions:** multidb Alembic so T-000.1's `make migrate` (`alembic upgrade head`) covers
both DBs unchanged; initial migration uses `metadata.create_all` so DDL always matches the
models. Note: added `alembic.ini` at repo root (alembic CLI looks for it in CWD) — required
companion to `migrations/*`, collides with no other task's owned files.
**Verify:** `make lint` clean; `make test` → 11 passed, 1 skipped (DB roundtrip skips with
no Postgres). `alembic heads` → `0001 (head)`.
**Next can assume:** importable models via `spec_atlas.db`; session factories
`db.analysis_session()/db.spec_session()`. **Gate item:** running `make migrate` + the DB
roundtrip needs a reachable Postgres (local/Docker or two Neon URLs in `.env`).
**Follow-ups:** none.

## HANDOFF 2026-06-19 — claude
**Task:** T-000.3 — Embedding provider abstraction (+ default + fake).
**Built:**
- `src/spec_atlas/embed/base.py` — `EmbeddingProvider` ABC: `dim` property,
  `embed(texts) -> list[list[float]]`, `embed_one(text)`. Vectors must be length `dim`.
- `src/spec_atlas/embed/fake.py` — `FakeEmbeddingProvider` (default dim 384): SHA-256 →
  stable, L2-normalized vector. Deterministic, offline, no deps. Used for `EMBED_PROVIDER=fake`.
- `src/spec_atlas/embed/fastembed_provider.py` — `FastembedEmbeddingProvider`
  (`BAAI/bge-small-en-v1.5`, 384-dim); model lazy-loaded on first `embed` (only network use).
- `src/spec_atlas/embed/__init__.py` — `get_embedding_provider(settings)` factory selecting
  fake vs fastembed; lazy-imports fastembed so the fake path never pulls onnxruntime.
- Tests `tests/embed/`: fake contract (dim 384, determinism, normalization, batch order,
  custom dim, factory); fastembed contract (384-dim + determinism), auto-skips if the model
  can't load offline.
**Decisions:** factory + subpackage `embed/__init__.py` added (necessary companion to the
owned provider files; collides with nothing). Fake L2-normalizes to mimic real embeddings.
**Verify:** `make lint` clean; `make test` → 20 passed, 1 skipped. The fastembed default
loaded locally here and returned 384-dim vectors (model now cached); it skips in offline CI.
**Next can assume:** `from spec_atlas.embed import get_embedding_provider`; `EMBED_PROVIDER`
selects implementation; default dim 384 matches `embeddings.vector(384)`.
**Follow-ups:** none.

## HANDOFF 2026-06-19 — claude
**Task:** T-000.4 — LLM provider abstraction (+ default + fake).
**Built:**
- `src/spec_atlas/llm/base.py` — `LLMProvider` interface, `Message` type, JSON Schema
  validation helper, and shared retry/backoff helper for transient provider failures.
- `src/spec_atlas/llm/fake.py` — deterministic offline fake provider that returns canned
  responses by `[tag:...]` prompt marker and emits schema-shaped structured output.
- `src/spec_atlas/llm/gemini_provider.py` — Gemini REST implementation over `httpx`
  with exponential retry on timeout / transport / 429 / 5xx responses, plus structured
  output validation against caller-provided JSON Schema.
- `src/spec_atlas/llm/__init__.py` — provider exports and `get_llm_provider(settings)`
  factory selecting `fake` or `gemini`.
- `tests/llm/test_fake_llm.py` — fake provider contract tests for canned text, schema
  validation, structured stubs, invalid payload rejection, and factory selection.
- `tests/llm/test_retry.py` — retry helper tests for eventual success, final failure,
  and non-retry on permanent errors.
**Decisions:** the real provider uses Gemini over raw HTTP to satisfy the no-vendor-SDK
constraint from the architecture docs; `fake` remains the offline default and the real
path is only activated when selected in config with a key present.
**Authorship (clarified during recovery):** T-000.4 was authored by **claude** (this
provider code under `src/spec_atlas/llm/`). The original "re-ran during takeover" wording
was ambiguous — to be precise: claude verified at **29 passed, 1 skipped** when this task's
code was complete; the **32 passed** figure was a later re-run by **codex** after it added
T-000.5 (parse) in the same working tree. No agent other than claude wrote the `llm/` code.
**Verify:** `make lint` clean; `make test` → 29 passed, 1 skipped at this task's completion
(grew to 34 passed, 1 skipped once T-000.5/.6 landed). Code committed during Phase-0 recovery
as `feat(F-000): T-000.4 ...`.
**Next can assume:** `from spec_atlas.llm import get_llm_provider`; `LLM_PROVIDER=fake`
is fully offline; `LLM_PROVIDER=gemini` requires `GEMINI_API_KEY` and validates JSON
structured output before returning it.
**Follow-ups:** none inside this task.

## HANDOFF 2026-06-19 — codex
**Task:** T-000.5 — tree-sitter setup.
**Built:**
- `src/spec_atlas/parse/treesitter.py` — thin Python CST wrapper with cached grammar/parser
  loading from `tree-sitter-python`, plus `parse_python`, `parse_python_file`, and
  `top_level_named_nodes` helpers for the later F-002 parser work.
- `tests/parse/test_treesitter_smoke.py` — smoke coverage for grammar loading, direct text
  parsing, and parsing a fixture from disk with expected top-level node types and names.
- `tests/fixtures/parse/sample_module.py` — tiny Python fixture with one function and one
  class for stable CST assertions.
**Decisions:** kept the parse surface intentionally narrow and Python-only per
`INTEGRATIONS.md#1-parsing`; F-002 can layer symbol/query-pack logic on this entrypoint
without widening the public API now.
**Verify:** `make lint` clean; `make test` → 32 passed, 1 skipped (DB roundtrip still skips
offline without Postgres URLs).
**Next can assume:** `spec_atlas.parse.treesitter` loads the local Python grammar with no
network dependency and returns a `tree_sitter.Tree` rooted at `module` for Python files.
**Follow-ups:** none inside this task.

## HANDOFF 2026-06-19 — codex (authored) / claude (verified + closed during recovery)
**Task:** T-000.6 — Health endpoint + app wiring.
**Built:**
- `src/spec_atlas/api/app.py` — `create_app(settings)` factory: stores settings, builds
  `analysis_session`/`spec_session` factories when DB URLs are set (else `None`), wires the
  configured LLM + embedding providers onto `app.state`, registers `GET /health`.
- `src/spec_atlas/api/health.py` — `health()` returns the full
  `{status, analysis_db, spec_db, llm, embed}` shape; DB legs report `ok` /
  `not_configured` / `error`; provider legs report provider name + impl + model/dim.
  Overall `ok` only when both DBs are `ok`, else `degraded` + HTTP 503.
- `tests/api/test_health.py` — 200/`ok` with fake providers + sqlite session factories;
  503/`degraded` + `not_configured` when no DB is wired.
**Status at Codex limit:** code complete but left `in-progress`, uncommitted, on the
T-000.4 branch (no dedicated branch). See ADR-0003.
**Verify (claude, recovery):** committed as `feat(F-000): T-000.6 …`. `make test` → 34
passed, 1 skipped; `make lint` clean. Live boot confirmed: `uvicorn spec_atlas.api.app:app`
serves `GET /health` → full shape; returns 503/`degraded` with DBs unset (by design), with
`llm` and `embed` legs `ok` on the fakes. DoD met (app boots; health test passes with fakes).
**Next can assume:** `from spec_atlas.api.app import create_app`; `/health` is the app's
readiness surface; both-DB-`ok` requires reachable Postgres (gate item, T-000.7/DB pass).
**Follow-ups:** none inside this task.

## HANDOFF 2026-06-19 — claude
**Task:** T-000.7 — CI (offline, free) + Phase-0 exit-gate verification.
**Built:**
- `.github/workflows/ci.yml` — two jobs. **lint-and-test**: `make setup` → `make lint`
  → `make test` with `LLM_PROVIDER=fake EMBED_PROVIDER=fake` and **no** DB URLs (DB
  roundtrip auto-skips; offline suite green). **db-integration**: `pgvector/pgvector:pg16`
  service container, creates the `spec` DB, `make migrate` (both DBs), then `pytest tests/db`
  with DB URLs scoped to that job only. No secrets, no paid services.
**DB-backed acceptance verified (this session, ephemeral Docker pgvector pg16):**
`make migrate` applied `0001` to both DBs; Analysis tables = repos/files/nodes/edges/groups/
embeddings, Spec tables = specs/spec_edges (match `DATA-MODEL.md`); `vector` extension 0.8.2;
`embeddings.vector` = `vector(384)`; `pytest tests/db` → 1 passed. `make dev` boot + `/health`
full-shape confirmed (T-000.6 HANDOFF).
**Decisions:** DB env is scoped to the `db-integration` job rather than set globally,
because `tests/unit/test_config.py` + `tests/api/test_health.py` assert URLs default to
None and read ambient `os.environ` — sliced as **T-000.8** (ready, non-blocking). CI uses
the pgvector image so `CREATE EXTENSION vector` + `vector(384)` work without a build step.
**Verify (local, offline):** `make lint` clean; `make test` → 34 passed, 1 skipped;
`pytest tests/db` (with pgvector) → 1 passed; CI YAML parses; every workflow command was
run locally and is green. A live Actions run needs a git remote (none configured yet).
**Next can assume:** F-000 exit gate met; `master` reflects the BOARD; Phase 1 (F-001→…→F-004)
can be sliced after review. Open items: T-000.8 (test hardening); pick a git remote.
**Follow-ups:** T-000.8 (ready); choose a remote/PR target (tracked in docs/status).
