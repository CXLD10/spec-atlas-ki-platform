# NEXT_STEPS.md — Spec-Atlas (2026-06-19)

Ordered actions to resume Phase 0 without re-deriving context. Active feature is **F-000**
(Phase 0); F-006 is NOT active. The blocker is *tracking hygiene*, not missing code — the
suite is green offline (34 passed, 1 skipped).

1. **Reconcile git with the BOARD (do this first).** On `task/T-000.4-llm-provider`, the
   code for **T-000.4** (`src/spec_atlas/llm/`, `tests/llm/`), **T-000.5** (`src/spec_atlas/parse/`,
   `tests/parse/`, `tests/fixtures/parse/`), and **T-000.6** (`src/spec_atlas/api/`, `tests/api/`)
   plus the `tasks/BOARD.md` + `specs/features/F-000-foundations.md` edits are all uncommitted.
   Decide the unit of commit. Cleanest path matching `docs/PLAYBOOK.md`: commit T-000.4 on this
   branch (`feat(F-000): T-000.4 ...`) and merge to master; then create `task/T-000.5-treesitter`
   and `task/T-000.6-health` and land each separately. Goal: `git log` must reflect what the
   BOARD claims.

2. **Verify and close T-000.6 (Health endpoint).** After committing, run `make dev`, hit
   `GET /health`, confirm the `{status, analysis_db, spec_db, llm, embed}` shape and that the
   provider legs report the fakes. Flip T-000.6 `in-progress → done` on the BOARD + append its
   HANDOFF. (Code already passes `tests/api/test_health.py`.)

3. **Do the one DB-backed verification pass.** Start a local Postgres+pgvector (Docker, $0 per
   `INTEGRATIONS.md#2`), set `ANALYSIS_DB_URL`/`SPEC_DB_URL`, run `make migrate`, then
   `pytest tests/db` (the currently-skipped roundtrip). Confirm tables vs. `DATA-MODEL.md` and
   `embeddings.vector` dim = 384. This closes the two unverified F-000 acceptance criteria.

4. **Build T-000.7 — CI (the last open P0 task).** Add `.github/workflows/ci.yml`: install via
   uv, run `ruff check`/`format --check`, run `pytest` with `LLM_PROVIDER=fake EMBED_PROVIDER=fake`
   against an ephemeral Postgres service container; no secrets. Owned file per `F-000` T-000.7.
   This satisfies the "CI green" criterion and the **P0 exit gate** (`FEATURES.md` line 55).

5. **Advance the feature & run the P0 review.** Once T-000.6 + T-000.7 are `done`, set
   `F-000` `Status: ready → done` (or per playbook convention) and confirm every F-000
   acceptance checkbox. The P0 exit gate (`FEATURES.md`) is the explicit precondition for
   slicing Phase 1.

6. **Slice Phase 1 into `tasks/BOARD.md`.** Only after the P0 review. Build order from
   `FEATURES.md` line 13: **F-001** (ingestion & file inventory) first, then F-002 → F-003 →
   F-004. Write each as a self-contained `specs/features/F-001-*.md` with task slices, Owns,
   and DoD, following the F-000 file as the template. BOARD line 25 marks F-001 as next.

7. **(Process) Pick a git remote / PR target.** There is no remote and the env's stated base
   (`main`) does not match the repo default (`master`). Resolve before relying on PR review.
