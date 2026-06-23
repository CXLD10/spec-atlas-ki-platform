# Phase 0 — Make the happy path real out of the box

**Effort:** M · **Depends on:** none · **Audit items:** §3.4, §3.5, §3.9, §3.10, §3.13, §3.24

## Objective
A fresh `docker compose up` boots Postgres+pgvector, migrations run, and the **default read paths return real data instead of 503→mock**. The frontend talks to one client. Confidence and provenance become honest. This is the foundation — every later phase assumes a real DB and one client.

> Why first: with empty DB URLs every read endpoint 503s and the UI *silently* shows mock. Until this is fixed, "wire X to the UI" is meaningless because the UI never sees real data.

---

## Tasks

### 0.1 — Provision Postgres + pgvector, set DB URLs *(Dev B, S)*
- Ensure `docker-compose.yml` has a `db` service on `pgvector/pgvector:pg16`, healthcheck, volume.
- `init-db.sql` runs `CREATE EXTENSION IF NOT EXISTS vector;`.
- `.env.example` ships **non-empty** `ANALYSIS_DB_URL` / `SPEC_DB_URL` pointing at the compose DB; document that blank URLs = offline-degraded mode.
- `alembic upgrade head` applies `0001_initial`, `0002_ingest_jobs_table` cleanly against a fresh DB.
- **Verify:** `GET /health` reports both DBs `up` and providers introspected (`api/health.py`).

### 0.2 — Consolidate to one API client *(Dev A, M)* — §3.24
- Keep **one** typed client matching the backend contract. Recommended: promote `api/client.ts` (`ApiClient`, throws on non-2xx) as the single client; delete `lib/api.ts`'s mock-fallback behavior.
- Fix the path bug: poll `GET /api/ingest/:jobId` (not `…/status`).
- Replace `MockFallback` with real error states (loading / empty / error) in every consuming hook (`lib/hooks.ts`, `api/use*.ts`).
- Move `lib/mock.ts` usage to tests only.
- **Verify:** grep shows no production import of `MockFallback`/`MOCK_*` outside `__tests__`/stories.

### 0.3 — Fix groups repo-id placeholder *(Dev B, S)* — §3.5
- `api/groups.py:100` — replace the hardcoded `00000000-…-0001` UUID with a real resolve: accept `repo` (name) query param → look up `repos` → `repo_id`; pass through to clustering.
- Return `404` (not `root=None`) when the repo doesn't exist.
- **Verify:** `GET /api/groups?repo=<seeded>` returns a populated `root`.

### 0.4 — Real answer confidence *(Dev B, S)* — §3.4
- `retrieve/search.py:77-79` — stop using `1.0 - i*0.2` (rank). Return the actual pgvector `<->` distance from the query and map it through the existing-but-unused `_distance_to_similarity` (`search.py:137-149`).
- Thread the real similarity through `descent` → `answer` so `AskResponse.confidence` is genuine; the `< 0.4` Deep-Wiki branch now triggers honestly.
- **Verify:** two queries (one on-topic, one off-topic) yield clearly different, monotonic-with-relevance confidences.

### 0.5 — Fix provenance + remove dead summarize call *(Dev B, S)* — §3.9, §3.10
- `specify/engine.py:149`, `groups/summarizer.py:142` — provenance `"file"` must be the **path**, not `str(file_id)`. Join `Node.file_id → File.path` when building provenance spans.
- `api/ingest.py:425` — delete (or correctly arg) the dead `GroupSummarizer.summarize(group, session)` call (wrong arity; always swallowed). Real summarization happens in `GroupWriter`.
- `ingest/inventory.py:70` — drop the stale language-stub comment (detection is in pipeline via `LanguageDetector`).
- **Verify:** generated spec provenance shows a real file path; ingest logs have no swallowed summarize exception.

### 0.6 — No-mock tripwire *(Dev A + B, S)* — new
- **Backend smoke test:** boot app against seeded DB; assert every GET in the route table returns 200 with schema-valid, non-empty body.
- **Frontend test:** assert no production module imports `MOCK_*`/`MockFallback`.

---

## Seed / fixtures
Index one small real repo end-to-end against the compose DB so every later phase has L1/L3/L4 + specs + embeddings to render:
```bash
curl -X POST localhost:8000/api/ingest -d '{"repo_url":"https://github.com/<small-real-repo>"}'
# poll GET /api/ingest/{job_id} to 100%
```
Capture the resulting `repo` name; it's the seed handle for frontend checks.

## Backend tests
```bash
pytest -q tests/retrieve/test_search.py     # confidence now distance-derived
pytest -q tests/groups                       # repo-id resolve
pytest -q tests/specify tests/groups         # provenance = path
pytest -q                                    # full suite green
```
New tests:
- `test_confidence_is_distance_derived` — asserts confidence ≠ rank formula; uses `_distance_to_similarity`.
- `test_groups_resolves_repo_name` — 404 on unknown repo; populated root on known.
- `test_provenance_uses_file_path` — provenance `file` matches `File.path`, not a UUID.
- `test_route_table_smoke` — every GET 200 + non-empty on seeded DB.

## Frontend integration checks
1. **Index flow** still works end-to-end (`OmniIngest`→`/index/:jobId`→100%) — already real; confirm no regression after client consolidation.
2. **Ask** returns a real answer with a **real confidence number** that varies by question (no `MOCK_ANSWER`).
3. Network tab shows **one** client, correct paths (`/api/ingest/:jobId`, not `/status`).
4. With DB **down**, pages show an **error state**, never silent mock data.

## Definition of Done
- `docker compose up` + `alembic upgrade head` → `/health` all-green.
- One client; `lib/api.ts` mock-fallback removed; `mock.ts` only in tests.
- Confidence is distance-derived; provenance carries file paths; dead summarize call gone.
- Tripwire tests pass; full backend suite green.

## Commit checkpoint
```
feat(phase0): real DB happy-path, single API client, honest confidence & provenance
```
