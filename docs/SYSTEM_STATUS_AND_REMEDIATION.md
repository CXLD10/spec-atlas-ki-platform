# Spec-Atlas — System Status & Remediation Report

An honest, code-verified audit of what is real, what is connected, and what is mocked/stubbed — plus an ordered plan to make it all real. Every item cites a file. Where a doc/spec disagrees with the code, the code wins and the discrepancy is noted.

**Audit basis:** backend `src/spec_atlas/` (9.3k LOC), frontend `frontend/src/`, specs `specs/`, 48 test files. Default config boots **offline** with `fake` providers and **empty DB URLs** (`.env` has `ANALYSIS_DB_URL=`/`SPEC_DB_URL=` blank), which materially shapes what a fresh user sees.

---

## 1. Built & Real (implemented and wired end-to-end)

These work when Postgres (with pgvector) is configured and providers are selected. Backed by tests under `tests/`.

| Capability | Evidence |
|-----------|----------|
| **Repo ingestion pipeline** | `api/ingest.py:133-256` — real `git clone --depth=1`, inventory+hash, language detect, symbol/edge/spec/group/embedding phases; persisted jobs in `ingest_jobs` (`ingest/job_store.py`). |
| **Python symbol extraction** | Real tree-sitter CST (`parse/treesitter.py:12-31`, `parse/python_symbols.py`). |
| **Code graph store & queries** | `graph/store.py` — neighbors, BFS subgraph, reachability, search; served by `api/graph.py`. |
| **Group clustering (L4)** | Directory-based hierarchy with FK-safe ordering (`groups/clustering.py:20-163`). |
| **Group summaries + embeddings** | LLM summary + provenance + fingerprint persisted to DB (`groups/summarizer.py`), embedded via `embed/pipeline.py` with `Vector(384)`. |
| **Spec generation & versioning** | `specify/engine.py`, `specify/batch_generator.py`, `SpecStore` with `valid_from/valid_to` history (`spec/store.py:29-101`). |
| **Spec graph (L3)** | `specify/spec_graph_builder.py` derives `spec_edges` from L1 edges. |
| **Rule-based verifier + reports** | `verify/verifier.py`, idempotent `SpecStore.verify_spec` (`spec/store.py:220-314`), analytics `api/reports.py`. |
| **Retrieval pipeline** | router→pgvector ANN→tree descent→answer (`retrieve/*`, `answer/engine.py`). |
| **Provider abstraction** | LLM `fake/gemini/groq/ollama`, embed `fake/fastembed`, all via interfaces, httpx-only, no vendor SDK (`llm/`, `embed/`). |
| **Health endpoint** | Real DB ping + provider introspection (`api/health.py`). |
| **Document adapters (in isolation)** | PDF/Excel/Markdown parse correctly **when called directly** (`ingest/adapters/`), covered by `tests/ingest/`. |

---

## 2. Connected vs. Backend-only

**Connected front-to-back (real, with graceful mock fallback):**
- **Repo indexing + progress.** `OmniIngest` → `POST /api/ingest` (`lib/hooks.ts:60-78`) → navigate `/index/:jobId` → `IndexProgress` polls `GET /api/ingest/:jobId` via `api/useIndexJob.ts` using the **non-mocking** `ApiClient` (`api/client.ts:201-203`). This is genuinely end-to-end.
- **Ask.** `Ask.tsx` → `client.ask()` → `POST /api/ask` (`lib/api.ts:154-159`). Real when DB+providers are configured; falls back to `MOCK_ANSWER` on any non-2xx (incl. the 503 you get with empty DB URLs).

**Backend-only (real API, but no live UI consumes it / UI uses incompatible shape):**
- `api/graph.py` (nodes/edges/subgraph/search/neighbors/reachable) — real, but the `/graph` page expects a different `{id,label,layer,_x,_y,_z}` shape and falls back to mock (see §3.10).
- `api/specs/*` (CRUD, generate, verify, spec-graph) — real, but no shipped page is wired to it; the new `Specify` page posts an incompatible body (see §3.9). Only legacy `/repo/*` routes touch specs.
- `api/reports/*` — real verification analytics; **no dashboard consumes it**.
- `api/groups` — real query path but broken by a placeholder repo id (see §3.5).

**UI-only (no backend at all):** `Docs` page, `MCP` page + `Console` playground (see §3.6–3.7).

---

## 3. Mocked / Stubbed / Fake (exhaustive)

For each: **file → what's faked → why → what makes it real.**

### Backend

**3.1 Git history source — fully hardcoded**
`api/sources.py:30-66`. `GET /api/git/history` returns 5 literal commit dicts (`a864233`, …). Comment: *"Mock implementation for demo… In production, this would query the actual git repository."* **Why:** Jira/git sources were spec'd (`INTEGRATIONS.md`) but only the endpoint shell was built. **Real:** run `git log` against the resolved repo working dir (already available from `ingest/resolver.py`), or store commits during ingest and query them.

**3.2 Jira issues source — fully hardcoded**
`api/sources.py:92-142`. Returns literal `ATLAS-123..126`; query filter runs over the mock list. **Why:** placeholder for a Jira export/REST integration. **Real:** ingest a Jira export JSON to a table (or call Jira REST behind a provider interface), index issues as `SourceUnit`s with provenance.

**3.3 Deep Wiki fallback — mock string**
`api/answer.py:219-242`. Only returns content when `LLM_PROVIDER=fake`, and it's a canned `"Based on general knowledge about '…'"` string. Comment: *"In production, integrate with actual Deep Wiki API."* **Why:** fallback path stubbed for demos. **Real:** call a real general-knowledge provider (or the configured LLM with a "no project context" prompt) behind the provider interface, keep the disclaimer, and derive confidence honestly.

**3.4 Answer confidence is rank-derived, not a real score**
`retrieve/search.py:77-79`: `similarity = max(0.0, 1.0 - (i*0.2))` — the "confidence" surfaced to the user is the **rank position**, not the pgvector distance (a real `_distance_to_similarity` helper exists at `search.py:137-149` but is unused). **Why:** shortcut. **Real:** return the actual `<->` distance from the query and map it through `_distance_to_similarity`.

**3.5 Groups API uses a placeholder repo id**
`api/groups.py:99-102`: `repo_id=uuid.UUID("00000000-0000-0000-0000-000000000001")  # Placeholder`. Real repos get random UUIDs, so `GET /api/groups` returns `root=None` for actual data. **Why:** v1 "one repo per DB" assumption never finished. **Real:** accept/resolve `repo` → `repo_id` (look up `repos` by name) and pass it through.

**3.6 MCP `get_graph` handler — empty stub**
`mcp/handlers.py:146-183`: *"For now, return an empty graph structure"* → always `nodes:[], edges:[]`. **Real:** query `GraphStore`/`Group` for the requested layer and serialize.

**3.7 MCP `search_knowledge` / `ask_question` — call non-existent APIs**
`mcp/handlers.py:43-88,185-225` instantiate `VectorSearch(self.analysis_session, …)` and call `search.search(query, limit=…)`, and `TreeDescent(self.analysis_session).retrieve(...)` — but `VectorSearch.search`/`TreeDescent.descend` are **static methods with different signatures** (`retrieve/search.py:20`, `retrieve/descent.py:32`). These handlers will raise at runtime; `ask_question` also hardcodes `confidence: 1.0`. The legacy `MCPToolHandlers` (`handlers.py:229-275`) is entirely stubs ("not yet implemented"). The server's handler-less branches also return `"Search not yet implemented"` (`mcp/server.py:228-274`). **Why:** scaffolding written before the static retrieval APIs settled. **Real:** rewrite `MCPHandlers` to call the same code paths as `AnswerRouter` (`api/answer.py`), reuse `SpecStore`/`GraphStore`, and add a runnable entrypoint.

**3.8 No MCP entrypoint / advertised package doesn't exist**
There is no console script in `pyproject.toml` and `SpecAtlasMCPServer` is only ever constructed in tests (`tests/mcp/`). The UI tells users to run `uvx spec-atlas-mcp` (`frontend/src/pages/MCPServer.tsx:31-41`), which is not published. **Real:** add a `spec-atlas-mcp` entrypoint that builds the server with real `MCPHandlers` over configured sessions, and package it.

**3.9 Spec provenance uses file UUIDs, not paths**
`specify/engine.py:149` and `groups/summarizer.py:142`: provenance `"file"` is `str(focal_node.file_id)` with comment *"Placeholder: would need file path lookup."* Provenance is mandatory but currently points at a UUID, not a `path`. **Real:** join `Node.file_id → File.path` when building provenance spans.

**3.10 Dead/broken summarize call in ingest**
`api/ingest.py:425` calls `GroupSummarizer.summarize(group, session)` — wrong arity (real signature is `summarize(group, member_nodes, member_edges, related_specs, llm_provider)`, `summarizer.py:21-28`). It always raises and is swallowed by try/except; the real summarization is done later by `GroupWriter`. **Why:** leftover after a refactor. **Real:** delete the dead call (or fix its arguments) to avoid silent failures and confusion.

**3.11 `group.md` written to an ephemeral temp clone**
`groups/group_writer.py:190-213` writes `group.md` under `repo_path`, which for git sources is the `tempfile.mkdtemp` clone (`ingest/resolver.py:91`) — discarded after ingest. The "persistent Markdown" is durable only in `groups.summary_md`. **Real:** write to a configured persistent docs directory (or object store), and serve it via an API.

**3.12 Rate limiting disabled**
`api/ingest.py:73-77`, `api/answer.py:268-272`: `_apply_rate_limit` is a no-op with `# TODO: Fix slowapi compatibility`. **Real:** wire `slowapi` middleware/limiter properly (NFR/security spec F-017).

**3.13 Inventory language stub note**
`ingest/inventory.py:70` comments a language stub; actual detection is done in the pipeline via `LanguageDetector` (`api/ingest.py:164-166`), so this is benign but stale.

### Frontend

**3.14 Central mock dataset**
`frontend/src/lib/mock.ts` — `MOCK_SOURCES` (huggingface/transformers, torvalds/linux, fake PDFs/xlsx/md), `MOCK_CARDS`, `MOCK_ANSWER`, and the **entire L1/L3/L4 `MOCK_SUBGRAPH`** with hand-placed coordinates. Returned whenever the API client throws `MockFallback` (`lib/api.ts:22-56`).

**3.15 Dashboard / Sources / SourceDetail — always mock**
`pages/Dashboard.tsx`, `pages/Sources.tsx`, `pages/SourceDetail.tsx` use `useSources()` → `client.listSources()` → `GET /api/sources`, which **does not exist** in the backend (only `/api/git/history`, `/api/jira/issues`). Result: `MockFallback` → `MOCK_SOURCES`. Dashboard stats are computed from mocks and even fudge domains: `domains: Math.ceil(sources.length*0.3) // Mock` (`Dashboard.tsx:16`). **Real:** add `GET /api/sources` (+ `/api/sources/:id`) aggregating `repos` and ingested documents.

**3.16 Knowledge Base / Knowledge Card — always mock**
`pages/KnowledgeBase.tsx`, `pages/KnowledgeCard.tsx` use `useCards()` → `GET /api/kb` (and `/api/kb/:ref`), which **do not exist** → `MOCK_CARDS`. **Real:** add `/api/kb` listing mapping to `specs`, and `/api/kb/:ref` to a spec/card view (the data exists in the Spec DB).

**3.17 Graph page — always mock, and not THREE.js**
`pages/Graph.tsx` → `client.getSubgraph()` → `GET /api/graph/subgraph`. Backend requires `node_id` (`api/graph.py:192-194`) and returns `NodeDetail` shape (`qualified_name`, `kind`, …), **not** the `{id,label,layer,_x,_y,_z}` the UI needs → `MockFallback` → `MOCK_SUBGRAPH`. The shipped renderer is a **2D canvas** (`components/graph/IsoGraph.tsx`), not the real `three`-based `scene/GraphScene.tsx` (which is only on legacy `/repo/*` routes). **Real:** add a layered subgraph endpoint returning nodes tagged L1/L3/L4 with layout hints (or compute layout client-side), and point `/graph` at `GraphScene`.

**3.18 Specify page — animated mock + demo stubs**
`pages/Specify.tsx`: the five "trace" stages are pure `setTimeout` animation (`:52-59`); `client.generateSpec(repo, entity)` posts `{repo, entity_name}` as a body to `POST /api/specs`, but the backend expects **query params** `repo`+`component_ref` and a `content` body (`api/specs.py:98-104`) → 422 → `MockFallback` → `MOCK_CARDS[0]`. Save = `alert('… demo stub')` (`:81`); Verify flips local state only (`:84-89`). **Real:** call `POST /api/specs/generate/{component_ref}?repo=…` (which already does generate-on-demand), render its real provenance, and wire Save/Verify to the spec endpoints.

**3.19 MCP page + Console — fully static/mock**
`pages/MCPServer.tsx`: tool list and config are hardcoded; health is "OK" even on `MockFallback` (`:53-54`). `components/mcp/Console.tsx:66-133`: the "Playground" returns **hardcoded `mockResponses`** after an 800ms `setTimeout` — it never calls the backend or MCP server. **Real:** expose an HTTP bridge to the MCP tools (or call the equivalent REST endpoints) and render real responses.

**3.20 Docs page — 100% static content**
`pages/Docs.tsx` embeds all documentation as in-file string constants (`docContent`, `:62-455`). Search box is non-functional. **Real (optional):** source docs from `docs/` or a CMS; wire search.

**3.21 Fake answer streaming**
`pages/Ask.tsx:76,95`: "streaming" waits `answer.length * 20ms` then reveals text — there is no SSE despite `docs/frontend/prompts/PROMPT-03-real-indexing-sse.md`. **Real:** add an SSE/streaming `/api/ask` variant and consume it.

**3.22 Document upload — mock job → dead end**
`OmniIngest` document path → `client.uploadDocument()` → `POST /api/documents` (**no such endpoint**) → `MockFallback` → mock `job_id` `mock-document-…` → `/index/:jobId` → `useIndexJob` calls `GET /api/ingest/mock-document-…` → 404 error. **Real:** implement document ingestion (see §4 Phase 2) and `POST /api/documents`.

**3.23 Mock progress simulator**
`lib/hooks.ts:106-150`: `useIngestStatus` simulates climbing progress for any `mock-` job id. (Note: the *real* progress page uses `api/useIndexJob.ts`, not this hook.)

**3.24 Two divergent API clients**
`lib/api.ts` (mock-fallback) and `api/client.ts` (`ApiClient`, throws) coexist with overlapping methods and **inconsistent paths** (e.g. `lib/api.ts:131` polls `/api/ingest/:jobId/status` which doesn't exist; `api/client.ts:202` polls the correct `/api/ingest/:jobId`). This is a latent source of "works here, mock there" bugs. **Real:** consolidate to one typed client matching the backend contract.

---

## 4. Road to Real — phased remediation

Effort: **S** ≈ <1 day, **M** ≈ 1–3 days, **L** ≈ 1–2 weeks. Ordered so each phase unblocks the next.

### Phase 0 — Make the happy path real out of the box (foundation)
1. **Provision Postgres+pgvector and set DB URLs** (`.env`, `docker-compose.yml`, `init-db.sql`). *(S)* — without this every read endpoint 503s and the UI silently shows mock. *Dep: none.*
2. **Consolidate frontend to one API client** matching the backend contract; remove `lib/api.ts`/`api/client.ts` divergence and the `/status` path bug. *(M)* §3.24. *Dep: 1.*
3. **Fix groups repo-id placeholder** — resolve `repo`→`repo_id`. *(S)* §3.5.
4. **Real answer confidence** via `_distance_to_similarity` on actual pgvector distance. *(S)* §3.4.
5. **Remove dead `summarize` call**; **fix provenance to use `File.path`** (`engine.py`, `summarizer.py`). *(S)* §3.9–3.10.

### Phase 1 — Connect the existing real backend to the UI
6. **`GET /api/sources` + `/api/sources/:id`** aggregating repos + documents; point Dashboard/Sources at it. *(M)* §3.15. *Dep: 0.1, 0.2.*
7. **`GET /api/kb` + `/api/kb/:ref`** mapping `specs` → cards; wire KnowledgeBase/Card. *(M)* §3.16. *Dep: 0.1.*
8. **Layered subgraph endpoint** (nodes tagged L1/L3/L4 + edges) and switch `/graph` to the THREE.js `GraphScene`. *(L)* §3.17. *Dep: 0.1, 0.3.*
9. **Wire Specify** to `POST /api/specs/generate/{ref}` with real trace + Save/Verify. *(M)* §3.18. *Dep: 0.2.*
10. **Verification dashboard** consuming `/api/reports/*`. *(S–M)* §2.

### Phase 2 — Real document ingestion (close the biggest "multi-source" gap)
11. **`POST /api/documents`** (multipart) + a document ingest path that runs the PDF/Excel/Markdown adapters, embeds `SourceUnit`s, and persists them with provenance into the graph. *(L)* §3.22, PRODUCT feature 7. *Dep: 0.1.*
12. **Persist `SourceUnit`s** (new table) and include them in retrieval/answers so PDF page / Excel cell citations actually surface. *(L)* *Dep: 11.*
13. **Persistent docs store** for `group.md`/cards instead of the temp clone. *(M)* §3.11. *Dep: 0.1.*

### Phase 3 — Real external sources
14. **Real git history** from the resolved repo (or stored at ingest). *(S–M)* §3.1.
15. **Real Jira** via export-JSON import or REST behind a provider interface; index as sources. *(M)* §3.2. *Dep: 11–12.*
16. **Real Deep Wiki fallback** (real provider call + honest confidence + disclaimer). *(M)* §3.3.

### Phase 4 — Agents & real-time
17. **Rewrite `MCPHandlers`** to reuse `AnswerRouter`/`SpecStore`/`GraphStore`; implement `get_graph`; remove stub branches. *(M)* §3.6–3.7. *Dep: 0.x.*
18. **MCP entrypoint + package** (`spec-atlas-mcp`); make the `/mcp` Console call it for real. *(M)* §3.8, §3.19. *Dep: 17.*
19. **SSE streaming `/api/ask`** + real streaming UI. *(M)* §3.21.

### Phase 5 — Robustness & spec parity
20. **Drift detection (F-014)** — `DriftDetector` comparing `source_fingerprint` on re-ingest, marking specs `stale` + `staleness_detected_at`, with retrieval filtering. *(L)* PRODUCT feature 8.
21. **Eval harness (F-016)** — implement the retrieval/answer eval over `tests/eval/fixtures`. *(M)*.
22. **TS/JS via tree-sitter** to replace regex extraction (`parse/ts_symbols.py`, `graph/edges_crossfile.py`). *(M)*.
23. **Enable rate limiting** (`slowapi`). *(S)* §3.12.

### Definition of Done — a fully-real system
- A fresh `docker compose up` provisions Postgres+pgvector; no endpoint silently falls back to mock, and `frontend/src/lib/mock.ts` is used only in tests.
- Indexing a real repo populates L1/L3/L4; the `/graph` page renders that data in THREE.js with raycast selection and an inspector.
- Uploading a PDF/Excel/Markdown produces searchable knowledge whose answer citations resolve to real page/cell/section locators.
- `Dashboard`, `Sources`, `KnowledgeBase`, `Specify`, and the verification dashboard render **only** backend data; Specify Save/Verify mutate the Spec DB.
- Answer confidence reflects true vector distance; Deep Wiki, Jira, and git-history return real data.
- The MCP server runs from a published entrypoint with DB-backed handlers; all four tools return real results and are covered by tests.
- Drift detection marks stale specs on re-ingest; the eval harness runs in CI; rate limiting is active; TS/JS parsing uses tree-sitter.
- CI stays green and fully offline using `fake`/`fastembed` fakes — the zero-cost contract holds.
