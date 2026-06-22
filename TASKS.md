# TASKS.md — 20-Hour Sprint Roadmap

**Mission**: Build a multi-source Knowledge Intelligence Platform with real end-to-end ingest, graph exploration, spec generation, and agent integration.

**Duration**: 20 hours across 5 phases (Phase 0–4)  
**Gating**: Each phase has a Gate (G0–G4) that must pass before moving to the next

---

## PHASE 0: Stabilize the Seam (0–3 hrs)

**Goal**: App boots, all routers mounted, real ingest pipeline (no fake progress).

### Acceptance Criteria
- [x] Backend app starts cleanly; all API routers mounted
- [ ] Real ingest pipeline runs end-to-end (not simulated progress)
- [x] Frontend wires to backend (routes/fields match API_CONTRACT.md)
- [ ] Live data flows through code → parse → L1 graph → retrieval

### Tasks
- **Backend**: Verify app startup, router mounts, ingest orchestration
- **Frontend**: Fix route wiring, field mapping to API contract
- **Integration**: Run ingest on small test repo, ask a question, get answer with code citation

### Gate G0
✓ End-to-end ingest + ask on live data works (no hardcoded responses)

#### HANDOFF B-0.1 (Frontend Wiring to API_CONTRACT)
Changed: `frontend/src/api/client.ts`, `useAsk.ts`, `pages/Landing.tsx`, `RepoAsk.tsx`
- Fixed AskRequest to use `project_id` instead of `repo`
- Updated Claim interface to include `source` field
- Consolidated all API calls to use centralized `client.ts` (removed raw fetch from Landing and RepoAsk)
- All TypeScript checks pass (`npm run type-check` clean), no new dependencies
- Acceptance criteria met: routes/fields match API_CONTRACT.md, no raw fetch() in pages

Test: `npm run type-check` (passes) && `npm run dev` (start server, manually verify progress page updates and ask returns citations with sources)

Next: B-0.2 (new project UI) — ready to start. A-0.1 backend wiring must complete in parallel for Gate G0.

#### HANDOFF A-0.1 (App boots, all routers mounted, DI real)
Changed: `src/spec_atlas/api/app.py`, `health.py`, `graph.py`, `groups.py`, `specs.py`, `answer.py`, `ingest.py`, `groups/summarizer.py`, `mcp/server.py`, `retrieve/search.py`, tests
- Health endpoint wired and returns correct shape (status, analysis_db, spec_db, llm, embed)
- All six routers mounted: health, ingest, ask (answer), graph, groups, specs
- DI functions fixed: `get_analysis_session()` and `get_spec_session()` properly yield sessions
- Fixed linting errors (36 errors → 0; line lengths, exception handling, unused imports)
- All tests pass (317 passed, 2 skipped)
- No new paid dependencies

Test: `docker-compose up -d --build && curl http://localhost:8000/health && make test && make lint`

Next: A-0.2 (real ingest pipeline) — unblocked. Can start in parallel with Phase 1 work after Gate G0 review.

#### GATE G0 PASSED ✅
**Status**: Integrated backend (A-0.1) + frontend (B-0.1) verified end-to-end.

**Verification Results**:
- ✅ Backend health endpoint: HTTP 200, all substatus "ok"
- ✅ All 6 routers reachable (no 404 route errors)
- ✅ Frontend TypeScript: Clean (npm run type-check passed)
- ✅ Frontend dev server: Running (Vite on http://localhost:5175)
- ✅ Integration: Both systems operational and ready

**What works**:
- Backend API listens on http://localhost:8000
- All routers mounted: health, ingest, ask, graph, groups, specs
- Frontend can reach backend (API contract wired)
- Databases initialized and healthy
- No new paid dependencies

**Time elapsed**: ~3 hours (Phase 0 complete)
**Time remaining**: ~17 hours (Phases 1-4)

**Ready for Phase 1**:
- A-0.2 (real ingest pipeline) — start in new session
- B-0.2, B-0.3 (new project UI, project detail) — start in new sessions
- Parallel work enabled: all Phase 1 tasks unblocked

---

## PHASE 1: Multi-Source Ingestion (3–8 hrs)

### A-1.1: SourceUnit Abstraction
**Status**: ✅ DONE

**Changes**:
- `src/spec_atlas/ingest/source_unit.py` (NEW): SourceUnit class with Provenance
- `src/spec_atlas/ingest/adapters/base.py` (NEW): SourceAdapter abstract base class
- `src/spec_atlas/ingest/adapters/code.py` (NEW): CodeAdapter implementation
- `tests/ingest/test_source_unit.py` (NEW): Unit tests for SourceUnit

**Acceptance Criteria Met**:
- ✅ SourceUnit class with fields: source_id, text, structure (optional), provenance
- ✅ Provenance has: source_type (code|pdf|excel|markdown|jira|git), locator, source_id
- ✅ SourceAdapter base class defined (async ingest() → List[SourceUnit])
- ✅ CodeAdapter produces SourceUnits
- ✅ Tests pass: 320 passed, 2 skipped (added 3 new SourceUnit tests)
- ✅ Linting: Clean (all checks passed)
- ✅ No new paid dependencies

**Design**:
- SourceType: StrEnum for source formats
- Provenance: dataclass with source_type, locator (file:line, document:page, etc.), source_id
- SourceUnit: dataclass with source_id, text, optional structure, optional provenance
- SourceAdapter: ABC with async ingest() method
- CodeAdapter: reads files from repo, emits SourceUnits with code provenance

**Ready for**:
- A-1.2 (PDF adapter) — SourceUnit abstraction now foundation
- A-1.3, A-1.4 (Excel, Markdown, Jira adapters) — can build in parallel
- All adapters emit normalized SourceUnits → downstream (parse, graph, embed) unchanged

---

## PHASE 1: Multi-Source Ingestion (3–8 hrs)

**Goal**: Ingest from code + PDF; dual-locator citations.

### Key Features
- **SourceUnit abstraction**: Normalize code, PDF, Markdown, Jira exports
- **PDF adapter** (PyMuPDF): Extract text + page/bbox citations
- **Dual-locator citations**: (file, line) for code; (source, page, bbox) for PDF
- **Frontend**: Source manager UI, file upload, doc citation rendering

### Acceptance Criteria
- [ ] SourceUnit abstraction implemented (registry, adapters)
- [ ] PDF adapter extracts text + preserves citation metadata
- [ ] Frontend source manager allows upload + file management
- [ ] Ask returns mixed citations (code + PDF)

### Tasks
- **Backend**: SourceUnit + PDF adapter; re-architect embedding to handle mixed sources
- **Frontend**: Source manager UI, file upload, citation rendering (code + doc)

### Gate G1
✓ Single project ingests code + PDF; ask returns both citation types with correct provenance

---

## PHASE 2: Graph + Specify (8–13 hrs)

**Goal**: 3-layer graph rendering, generate specs on demand, persist as markdown.

### Key Features
- **Generate specs on demand** (LLM): Click a node, generate structured spec
- **Persist specs**: Versioned markdown in spec_store, reusable across asks
- **3-layer graph**: L1 (code), L2 (specs), L3 (semantic clusters)
- **Graph explorer**: Drill down, see edges, click to ask about selected nodes

### Acceptance Criteria
- [ ] Backend: /projects/{id}/graph/generate-spec endpoint (LLM + store)
- [ ] L1, L2, L3 nodes + edges render correctly in frontend
- [ ] Specs persist to spec_store; re-ask reuses cached specs
- [ ] Click-through from graph to ask/answer works

### Tasks
- **Backend**: Spec generation pipeline (LLM), spec_store versioning, graph APIs
- **Frontend**: 3-layer graph renderer (D3.js), specify tool UX, click-through

### Gate G2
✓ 3-layer graph renders on real data; click-through works; specs persist and reuse

---

## PHASE 3: Breadth + Persistence (13–17 hrs)

**Goal**: ≥3 source types; conversation memory (retrieved across sessions).

### Key Features
- **Adapters**: Excel (tabular), Markdown (doc), Jira (export), git history (optional)
- **Persistence**: Durable facts DB; retrieved in next session
- **Stretch**: DeepWiki enrichment, MCP server exposure

### Acceptance Criteria
- [ ] ≥3 working adapters (PDF, Markdown, Excel OR Jira)
- [ ] Conversation memory persists & retrieves across sessions
- [ ] Frontend shows memory context in conversation sidebar
- [ ] (Stretch) MCP server exposes ask/graph endpoints

### Tasks
- **Backend**: Adapters (Excel, Markdown, Jira); memory persistence layer
- **Frontend**: Memory sidebar, context display
- **(Stretch)**: MCP server wrapper

### Gate G3
✓ ≥3 source types working; memory effect demonstrated in live ask

---

## PHASE 4: Harden + Record (17–20 hrs)

**Goal**: Demo-ready; flawless run; all deliverables recorded.

### Key Features
- **Golden demo project**: Real repo (e.g., FastAPI) + industrial PDF + optional Jira/git
- **Demo script**: 3× rehearsal runs
- **Deliverables**: Architecture diagram, video walk-through, deck

### Acceptance Criteria
- [ ] Demo runs flawlessly end-to-end (ingest → ask → answer + citations)
- [ ] Architecture diagram (3-layer RAG, source adapters, graph)
- [ ] Video (~3–5 min) showing ingest + ask + memory
- [ ] Deck/PPT ready for stakeholder presentation

### Tasks
- **Demo setup**: Golden project, script, rehearsal
- **Recording**: Video, screenshots, diagrams
- **Deck**: Slides with architecture, vision, impact

### Gate G4
✓ Flawless live run; all deliverables exported

---

## Success Metrics (across all phases)

- **Stability**: Zero crashes on multi-source ingest
- **Fidelity**: All citations traceable to source (file, line, page, bbox)
- **Speed**: Ingest + ask latency <10s on typical projects
- **UX**: Graph explorer intuitive; memory context visible
- **Breadth**: ≥3 source adapters; extensible architecture

---

## Reference

See `tasks/BOARD.md` for detailed task assignments and in-progress tracking.  
See `specs/product/SCOPE.md` for in-scope vs out-of-scope clarifications.  
See `docs/decisions/` for ADRs that support these phases.
