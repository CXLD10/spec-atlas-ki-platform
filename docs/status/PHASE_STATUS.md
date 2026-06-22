# PHASE_STATUS.md — Spec-Atlas audit (2026-06-19)

**Active phase:** Phase 0 — Foundations · **Active feature:** **F-000** (`specs/features/F-000-foundations.md`).
**Active task:** T-000.6 (Health endpoint, `in-progress`), with T-000.4/.5 work also sitting uncommitted alongside it.

> **The "F-006 / embedding pipeline" hypothesis is WRONG.** No Phase 1+ feature has been
> sliced or started. Work has not left Phase 0. The only Phase-4 artifact in the repo is
> the *embedding provider abstraction* (T-000.3, part of F-000) — not the F-006 embedding
> *pipeline*, which depends on F-005/F-007 and does not exist.

## Summary
F-000 stands up the skeleton (scaffold, two-DB migrations, tree-sitter, LLM/embedding
providers + fakes, health endpoint, CI). Six of seven tasks have working, test-backed code;
only CI (T-000.7) is untouched. **But the audit's central finding is a process/tracking
discrepancy, not a code gap:** the git history is merged only through **T-000.3**. All of
T-000.4 (`llm/`), T-000.5 (`parse/`), and T-000.6 (`api/`) — plus the BOARD/feature-file
status edits marking them done/in-progress — exist **only as uncommitted working-tree
changes** on branch `task/T-000.4-llm-provider`. `git log master..HEAD` is empty: zero
commits beyond master. So three tasks are marked `done`/`in-progress` on the BOARD with no
commit, no merge, and (for .5/.6) no dedicated branch. The code itself is sound and the
suite is green offline.

## Task status (per `specs/features/F-000-foundations.md` DoD)

| Task / Criterion | Status | Evidence (file:line) | Notes |
|---|---|---|---|
| **T-000.1** Scaffold & tooling | ✅ Done (committed `506bbd0`/`1601b78`) | `pyproject.toml`, `src/spec_atlas/config.py`, `Makefile`, `.env.example` | Merged to master. HANDOFF F-000:77. |
| **T-000.2** DB clients + migrations | ✅ Done (committed `e5fca50`/`400db75`) | `src/spec_atlas/db/{analysis,spec}.py`, `migrations/versions/0001_initial.py` | Merged. DB roundtrip test auto-skips offline (no Postgres). HANDOFF F-000:104. |
| **T-000.3** Embedding provider | ✅ Done (committed `66a3fde`/`90259ce`) | `src/spec_atlas/embed/{base,fake,fastembed_provider}.py`, `tests/embed/*` (9 tests) | Merged. fake=384-dim deterministic. HANDOFF F-000:137. |
| **T-000.4** LLM provider | ⚠️ Code done, **UNCOMMITTED** | `src/spec_atlas/llm/{base,fake,gemini_provider,__init__}.py`; `tests/llm/*` (9 tests pass) | Marked `done`/`claude` on BOARD but not in any commit. DoD met in code: fake offline `llm/fake.py:53`, gemini behind flag `llm/__init__.py:43`, retry/backoff unit-tested `tests/llm/test_retry.py`. No vendor SDK (raw httpx, `gemini_provider.py:12`). |
| **T-000.5** tree-sitter setup | ⚠️ Code done, **UNCOMMITTED** | `src/spec_atlas/parse/treesitter.py`, `tests/parse/test_treesitter_smoke.py` (3 tests pass) | Marked `done`/`codex`. No `task/T-000.5-*` branch — built on the T-000.4 branch. DoD met: smoke test parses fixture, finds top-level nodes. |
| **T-000.6** Health endpoint + app wiring | ⚠️ Code present (`in-progress`), **UNCOMMITTED** | `src/spec_atlas/api/{app,health}.py`, `tests/api/test_health.py` (2 tests pass) | Marked `in-progress`/`codex`. Functionally near-complete: `/health` returns `{status,analysis_db,spec_db,llm,embed}` (`health.py:84`). `make dev` boot not verified (needs running server); DB legs verified only via sqlite in test. |
| **T-000.7** CI (offline, free) | ❌ Not started | (no `.github/workflows/`) | `ready` on BOARD. Blocks feature-level CI acceptance criterion. |

## Feature-level acceptance criteria (`F-000` "Acceptance criteria")

| Criterion | Status | Evidence / gap |
|---|---|---|
| `make dev` → `/health` ok w/ both DBs | 🟡 Partial | App + endpoint exist (`api/app.py`); needs reachable Postgres + running server to fully verify. Health works with fakes + sqlite in test. |
| `make migrate` applies to both DBs; pgvector; dim 384 | 🟡 Partial | Migration `0001_initial.py` exists (multidb, `Vector(384)`); **unverifiable offline** — no Postgres. Flagged below as gate item. |
| tree-sitter loads grammar → CST | ✅ Done | `tests/parse/test_treesitter_smoke.py` passes; feature file checkbox now `[x]` (uncommitted edit). |
| EmbeddingProvider default 384-dim; fake deterministic | ✅ Done | `tests/embed/*` pass; fastembed default cached, fake offline. |
| LLMProvider default reaches free model (flagged); fake canned structured | ✅ Done (provider side) | fake `llm/fake.py`; gemini gated behind `LLM_PROVIDER=gemini` + key. Real call not exercised (correct — not in CI). |
| CI green w/ fakes + ephemeral Postgres; no secrets | ❌ Not done | T-000.7 not started; no workflow file. |
| `.env.example` documents every var; `.env` gitignored | ✅ Done | T-000.1; `.env.example` + `.gitignore` committed. |

## Test & constraint verification (offline, `LLM_PROVIDER=fake EMBED_PROVIDER=fake`)

| Check | Result |
|---|---|
| `pytest` (full suite) | **34 passed, 1 skipped** (DB roundtrip skips w/o Postgres — expected per NFR) |
| Per area | unit 11 · embed 9 · llm 9 · parse 3 · api 2 · db 1 (skipped) |
| `ruff check` / `ruff format --check` | clean (29 files) |
| Offline / $0 (NFR.md cost) | ✅ no network, no creds needed for green |
| No vendor SDK (ARCHITECTURE cross-cut) | ✅ grep finds no `openai/genai/anthropic/groq` imports; Gemini via raw `httpx` |
| Repo code never executed (NFR security) | ✅ tree-sitter static parse only |

## Codex activity (attributed via BOARD "Agent" + HANDOFF + branch/commit, NOT git author)

| Task | Agent (BOARD/HANDOFF) | Branch | Commit | Landed? |
|---|---|---|---|---|
| T-000.1 | claude | `task/T-000.1-scaffold` | `506bbd0` | ✅ merged `1601b78` |
| T-000.2 | claude | `task/T-000.2-db-migrations` | `e5fca50` | ✅ merged `400db75` |
| T-000.3 | claude | `task/T-000.3-embed-provider` | `66a3fde` | ✅ merged `90259ce` |
| T-000.4 | claude (HANDOFF notes a "takeover") | `task/T-000.4-llm-provider` | — | ❌ uncommitted |
| T-000.5 | **codex** | *(none — on T-000.4 branch)* | — | ❌ uncommitted |
| T-000.6 | **codex** | *(none — on T-000.4 branch)* | — | ❌ uncommitted |

Note: environment lists the PR base as `main`, but the repo's default branch is **`master`**;
there is **no git remote**. The T-000.4 HANDOFF (F-000:159) is attributed to claude yet mentions
re-running verification "during takeover" — the only HANDOFF whose authorship wording is ambiguous.
