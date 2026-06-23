# Handoff — Phase 2 (document ingestion) in progress

**Written:** 2026-06-23, end of session (connection/session limit reached mid-Phase 2).
**Branch:** `main` (local Phase 0/1/2-WIP work + `origin/uiux-changes` merged in; pushed to `origin/main`).

This note is for whoever continues — human or another Claude session. Read this
before touching anything; it tells you exactly what's real, what's half-built,
and what to do next.

---

## Where things stand

| Phase | Status | Commit |
|---|---|---|
| Phase 0 — real DB happy path, single API client, honest confidence/provenance | **Done, committed** | `9b84aa5` |
| Phase 1 — wire Sources/KB/Graph(THREE.js)/Specify/Reports to real backend | **Done, committed** | `e3d083b` |
| Phase 2 — document ingestion | **Backend done; frontend + durable docs store + dedicated tests NOT done** | `282092a` (WIP) |
| uiux-changes (other dev, branched from `94c38f5`, your last push before Phase 0) | **Merged into main** | merge commit on top of `282092a` |

Full backend suite (`pytest -q`) is green: **433 passed, 1 skipped** (skip is a
network-dependent test, expected offline). Frontend `npm run type-check`,
`npm run test` (no-mock tripwire), and `npm run build` are all green.

### The other dev's branch (`origin/uiux-changes`)
Branched from `94c38f5` (your last push). One commit, cosmetic only: lucide
icons replacing emoji on Dashboard's Capabilities tiles, a logo PNG, light-mode
theme tokens, Topbar tweaks. It only overlapped my changes in one file
(`Dashboard.tsx`) and in a different section of that file (icons block vs. my
stats/error-banner block at the top) — merged cleanly via `git merge
origin/uiux-changes --no-edit`, no conflicts, verified with type-check/build
afterward. **This is already done — nothing left to do here.**

---

## Phase 2: what's actually done (commit `282092a`)

Real, tested, verified live against Postgres + a real uploaded document:

1. **Schema** (`src/spec_atlas/db/analysis.py`, migration
   `migrations/versions/0003_source_units_and_doc_sources.py`):
   - New `source_units` table — the document analogue of `nodes`. Columns:
     `repo_id`, `source_id` (filename), `source_type` (pdf/excel/markdown),
     `text`, `structure` (jsonb, e.g. Excel row), `locator` (full citation
     string), typed `page`/`sheet`/`row`/`section` columns parsed from the
     locator at persist time.
   - `repos.source_format` (`git`|`pdf`|`xlsx`|`md`, default `git`). **Documents
     reuse the `repos` table** (one row per uploaded doc) instead of a
     parallel `documents` table — deliberate, so every place that already
     aggregates by `repos` (the `embeddings.repo_id` FK, `/api/sources`,
     group counts) covers documents for free. See the note in
     `specs/architecture/DATA-MODEL.md` for the full rationale and what it
     replaces (`sources`/`source_locators`, which were spec'd in v2.0 docs
     but never built).
   - `embeddings.owner_kind` CHECK constraint extended to include
     `'source_unit'`.
   - Migration is idempotent (checks `sa.inspect()` before every
     add_column/create_check_constraint) because `0001_initial.py`'s
     `create_all()` always reflects *current* models, not a historical
     snapshot — so on a fresh DB, 0001 alone already creates everything
     0003 adds. Only matters on an older DB that ran 0001/0002 before these
     model fields existed.

2. **`POST /api/documents`** (`src/spec_atlas/api/ingest.py`,
   `src/spec_atlas/ingest/document_pipeline.py`): multipart upload, 25MB cap,
   extension allowlist (`.pdf`/`.xlsx`/`.md`/`.markdown`), routes to the
   matching adapter (`ingest/adapters/{pdf,excel,markdown}.py` —
   **unmodified**, exactly as the task required), persists `SourceUnit` rows,
   embeds them. Reuses the **same** `ingest_jobs` table / `IngestJobStore` /
   `GET /api/ingest/:jobId` polling as repo ingest — `useIndexJob` on the
   frontend needs zero changes to work with document jobs once the frontend
   is wired (see "Not done" below).

3. **Retrieval** (`src/spec_atlas/retrieve/search.py`): `VectorSearch._vector_search`
   now queries **both** group and source_unit embeddings and merges by real
   distance, returning `list[tuple[Group | SourceUnit, float]]`. Callers must
   `isinstance()`-check the owner.

4. **Answer citations** (`src/spec_atlas/api/answer.py`): new
   `_build_context_from_source_unit()` — when the top retrieval match is a
   `SourceUnit`, build a leaf `Context` directly (no group-tree descent;
   documents aren't part of the L4 tree) with the real locator in
   `source_spans`, which flows into the LLM prompt and the answer's
   `claims[].source`. Also fixed the "empty_db" guard, which only checked
   `Group`/`Node` counts — a document-only ingest (no code graph) was
   incorrectly reported as an empty database.

5. **`/api/sources`**: documents now report `type: "document"` and the real
   `format` (`pdf`/`xlsx`/`md`) instead of being mislabeled as a git repo.

### Bugs found and fixed while testing this live (not in the original task list, but blocking)
- **`/api/ask` never worked with the project's own zero-cost default `fake`
  provider.** `AnswerEngine.answer_async()` unconditionally `await`ed
  `llm_provider.complete()`, but the ABC (`llm/base.py`) declares `complete()`
  sync, and `FakeLLMProvider`/`GeminiLLMProvider` implement it that way — only
  `GroqProvider`/`OllamaProvider` are async. Calling `await` on a sync
  provider's dict return raised `TypeError: object dict can't be used in
  'await' expression` on every single call. Likely never caught before
  because nothing had literally curl-tested `POST /api/ask` end-to-end until
  this session.
- **The inverse bug existed in `SpecifyEngine.generate()` and
  `GroupSummarizer.summarize()`**: both called `.complete()` synchronously
  with no await — fine for fake/Gemini, but silently broken against
  `GroqProvider`/`OllamaProvider` (an unawaited coroutine object would get
  passed to `json.loads()`/string parsing instead of the real response).
  Since `.env` in this repo has `LLM_PROVIDER=groq` configured as the real
  provider, this means spec generation was likely silently broken against
  the actually-configured provider this whole time.
  - Fixed all four call sites (`answer/engine.py` x2, `specify/engine.py`,
    `groups/summarizer.py`) with `inspect.isawaitable()` checks instead of
    assuming either sync or async.
  - **If you touch any of these four files, keep this pattern** — don't
    revert to a bare `await` or bare sync call.

---

## Phase 2: what's NOT done yet

Pick these up next, in this order (matches the original task's numbering):

### 2.3 — Persistent docs store for `group.md` (not started)
`src/spec_atlas/groups/group_writer.py` still writes `group.md` into the
**ephemeral temp clone dir** (`ingest/resolver.py`'s `tempfile.mkdtemp()`,
which is never cleaned up on success but isn't a durable location either —
not served by any API, not guaranteed to survive a container restart).
Needs:
- A configured persistent docs directory (new `Settings` field, e.g.
  `docs_dir`, defaulting to something like `./data/docs`).
- `GroupWriter.write_groups_for_repo`'s `_write_group_markdown` to write
  there instead of `repo_path`, keyed by **repo name** (already resolved
  inside `write_groups_for_repo` via the `repo_name` lookup added in Phase 0)
  rather than the throwaway clone path.
- Some way to serve it (a new `GET` endpoint, or confirm an existing static
  file mount covers it).
- A test asserting the file exists post-ingest and is fetchable, per the
  original task's `test_group_md_persisted_to_durable_store`.

### Frontend: OmniIngest document upload (not started)
`frontend/src/components/ingest/OmniIngest.tsx` already calls
`client.uploadDocument(file)` → `POST /api/documents` (this client method was
added in Phase 0, pointing at the right URL) — **but `/api/documents` didn't
exist on the backend until this session**, so it's never been exercised
end-to-end from the UI. To close this out:
- Manually verify: upload a PDF/MD/XLSX via the Dashboard's `OmniIngest` →
  confirm it navigates to `/index/:jobId` → confirm progress climbs to 100%
  (no more `mock-document-` dead end — that was already removed in Phase 0,
  but never had a real backend to land on until now).
- Confirm the uploaded doc shows up in **Sources** (`/api/sources` already
  reports `type: document` correctly — verified) and **KnowledgeBase**
  (documents have no specs, so they won't appear in `/api/kb` — that's
  expected; KB is specs-only, not source-units. If product wants document
  *content* browsable in KB too, that's a new decision, not a bug.)
- Confirm **Ask** with a question only answerable from the uploaded doc
  returns a citation that resolves to a real page/cell/section. The backend
  side of this is done and verified live (see commit message); only the
  frontend rendering of that citation needs a look (check
  `components/ask/ChatMessage.tsx` renders `claims[].source` reasonably for
  a document-style locator like `doc.pdf:p.3`, not just `file:line`).

### Tests/fixtures (not started)
The original task asked for `tests/fixtures/docs/` with 2-3 real sample
documents (multi-page PDF, Excel workbook, Markdown doc) and:
- `test_upload_pdf_creates_source_units`
- `test_upload_excel_cell_locators`
- `test_markdown_section_locators`
- `test_answer_cites_document_source`
- `test_group_md_persisted_to_durable_store` (blocked on 2.3 above)

None of these exist yet as committed test files — what exists instead is
live, manual curl verification (see this session's transcript) that the
whole chain works, which is not the same as a regression test. **Write these
before considering Phase 2 done.** The adapters themselves
(`tests/ingest/test_{pdf,excel,markdown}_adapter.py`) already have good
coverage and are unchanged — reuse their patterns for fixture files.

A good template: look at `tests/api/test_route_table_smoke.py` and
`tests/groups/test_group_writer_integration.py` (both from Phase 0/1) for
the `migrated`/`pytest.mark.db` pattern this repo uses for real-Postgres
tests — every Phase 2 test above should follow the same pattern (skips
offline, runs against real Postgres when available).

### Known related-but-out-of-scope finding (not fixed, just flagged)
`src/spec_atlas/answer/provenance.py`'s `AnswerProvenanceExtractor` is a
fully-built, fully-tested (`tests/answer/test_multiformat_citations.py`)
claim-grounding validator — checks whether an LLM's cited claim source
actually matches a real context span, with confidence scoring (1.0 grounded,
0.7 ungrounded). **It is never called from `AnswerRouter.answer()`** — the
live `/api/ask` flow trusts the LLM's claims directly with no grounding
validation. Wiring this in would be a genuine answer-quality improvement
(applies to code citations too, not just documents) but is a separate,
bounded piece of work — didn't fold it into this session's document-ingestion
scope. Worth a dedicated task.

---

## Operational notes for whoever continues

### Local Postgres
Docker compose brings up `pgvector/pgvector:pg16` as service `postgres`
(not `db`, despite what the master plan doc says — functionally identical,
just a naming mismatch, not fixed since renaming risked an unrelated
regression for zero functional gain). `docker compose up -d postgres`,
then `alembic upgrade head`.

### IMPORTANT: don't run live manual tests against the same DB you run pytest against without resetting
I hit this repeatedly this session: spinning up `uvicorn` against the dev
Postgres and curl-testing leaves real rows that collide with hardcoded
fixture data in some tests (e.g. a group literally named `"auth"` in
`tests/db/test_schema_roundtrip.py`), causing spurious `IntegrityError`/
duplicate-key failures that look like real bugs but are just leftover data.
Reset before trusting a red test run:
```bash
python3 -c "
from spec_atlas import db
from spec_atlas.config import get_settings
from sqlalchemy import text
s = get_settings()
for url in [s.analysis_db_url, s.spec_db_url]:
    eng = db.make_engine(url)
    with eng.connect() as conn:
        conn.execute(text('DROP SCHEMA public CASCADE'))
        conn.execute(text('CREATE SCHEMA public'))
        conn.commit()
"
alembic upgrade head
```

### `.env` has a real Groq key in it
Already gitignored, not committed. `LLM_PROVIDER=groq` is the real configured
provider — the async/sync provider bug above means spec generation against
Groq should be re-verified live now that it's fixed (wasn't re-tested with
real Groq this session, only with `LLM_PROVIDER=fake` to stay zero-cost
during iteration).

### `python-multipart` is now a real dependency
Added to `pyproject.toml` for `POST /api/documents` multipart parsing. The
project's `.venv` doesn't have a `pip` module — use `uv pip install <pkg>
--python .venv/bin/python` to add packages, not `pip install` directly (that
resolves to a stray user-level pip and silently doesn't land in the venv).

### Browser/visual testing is not available in this sandbox
No `sudo`, so Playwright's Chromium system deps (`libnspr4.so` etc.) can't be
installed even after downloading the browser binary itself. All frontend
verification this session was type-check + build + live API-contract curl
checks, not actual rendered screenshots. If the next environment has a real
browser available, a visual pass on `/graph` (THREE.js scene) and the new
`/reports` page would be worthwhile — they were never visually confirmed,
only confirmed to type-check, build, and receive correctly-shaped data.

### Task tracker
Tasks #22-25 marked complete in this session's task list; #26-29 (durable
docs store, frontend wiring, tests/fixtures, final Phase 2 commit) are still
open. If continuing in a fresh Claude session, there's no task-list
continuity across sessions — just pick up from "Phase 2: what's NOT done
yet" above.

---

## Next immediate step

Phase 2 is **not** done — don't mark it complete or move to Phase 3 without
finishing 2.3 (durable docs), the frontend OmniIngest verification, and the
dedicated test suite above. The commit message on `282092a` says `wip(phase2)`
deliberately, not `feat(phase2)`, to make this unambiguous in `git log`.
