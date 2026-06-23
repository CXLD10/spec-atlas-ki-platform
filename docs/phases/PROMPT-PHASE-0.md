# EXECUTION PROMPT — Phase 0: Real happy path

You are working in the `CXLD10/spec-atlas-ki-platform` repo. **Goal of this sprint: remove the DB-503→mock cascade, collapse to one frontend API client, and make confidence + provenance honest.** Do not weaken provenance. Keep the offline `fake`/`fastembed` contract — all tests must pass with no network or credentials.

## Rules
- Code wins over docs. If a spec disagrees with code, fix the code path and note it.
- No new mock fallbacks. Replace `MockFallback` with real loading/empty/error states.
- Commit only at the stop point with the exact message below, after all checks pass.

## Do these, in order

**1. DB + pgvector (Dev B).** Ensure `docker-compose.yml` has a `pgvector/pgvector:pg16` `db` service (healthcheck + volume); `init-db.sql` runs `CREATE EXTENSION IF NOT EXISTS vector;`. Ship a non-empty `.env.example` with `ANALYSIS_DB_URL`/`SPEC_DB_URL`. Confirm `alembic upgrade head` applies `0001_initial` + `0002_ingest_jobs_table` on a fresh DB. `GET /health` must report both DBs up.

**2. One API client (Dev A).** Promote `frontend/src/api/client.ts` (`ApiClient`) as the single client. Remove `frontend/src/lib/api.ts`'s mock-fallback path. Fix polling to `GET /api/ingest/:jobId` (not `/status`). Update all consumers (`lib/hooks.ts`, `api/use*.ts`) to use real loading/error/empty states. Restrict `lib/mock.ts` to tests only.

**3. Groups repo-id (Dev B).** In `api/groups.py:100`, replace the hardcoded `00000000-…-0001` UUID. Accept a `repo` (name) query param, resolve via `repos` → `repo_id`, pass it through. Return 404 on unknown repo.

**4. Real confidence (Dev B).** In `retrieve/search.py:77-79`, stop using `1.0 - i*0.2`. Return the real pgvector `<->` distance and map through the existing `_distance_to_similarity` (`search.py:137-149`). Thread real similarity through `descent`→`answer` so `AskResponse.confidence` is genuine and the `<0.4` Deep-Wiki branch triggers honestly.

**5. Provenance + dead code (Dev B).** In `specify/engine.py:149` and `groups/summarizer.py:142`, set provenance `"file"` to the **path** (join `Node.file_id → File.path`), not `str(file_id)`. Delete the dead `GroupSummarizer.summarize(group, session)` call at `api/ingest.py:425` (wrong arity, always swallowed). Remove the stale language-stub comment at `ingest/inventory.py:70`.

**6. Tripwire tests.** Add a backend route-table smoke test (every GET → 200 + non-empty on a seeded DB) and a frontend test asserting no production module imports `MOCK_*`/`MockFallback`.

## Seed
Index one small real repo end-to-end against the compose DB; record the resulting `repo` name as the seed handle.

## Must pass before commit
```bash
pytest -q tests/retrieve/test_search.py
pytest -q tests/groups tests/specify
pytest -q                       # full suite green
cd frontend && npm run build && npm run test
```
Add/extend: `test_confidence_is_distance_derived`, `test_groups_resolves_repo_name`, `test_provenance_uses_file_path`, `test_route_table_smoke`.

## Frontend checks (manual)
1. Index flow works end-to-end, no regression.
2. Ask returns a real answer + real confidence that varies by question (no `MOCK_ANSWER`).
3. Network tab: one client, `/api/ingest/:jobId` path.
4. DB down → error state, never silent mock.

## STOP & COMMIT
```
feat(phase0): real DB happy-path, single API client, honest confidence & provenance
```
Report: what changed per file, test output, and confirmation that no production path hits mock. Do not start Phase 1.
