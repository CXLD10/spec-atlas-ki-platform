# TASKS.md — 20-Hour Sprint Roadmap

**Mission**: Build a multi-source Knowledge Intelligence Platform with real end-to-end ingest, graph exploration, spec generation, and agent integration.

**Duration**: 20 hours across 5 phases (Phase 0–4)  
**Gating**: Each phase has a Gate (G0–G4) that must pass before moving to the next

---

## PHASE 0: Stabilize the Seam (0–3 hrs)

**Goal**: App boots, all routers mounted, real ingest pipeline (no fake progress).

### Acceptance Criteria
- [ ] Backend app starts cleanly; all API routers mounted
- [ ] Real ingest pipeline runs end-to-end (not simulated progress)
- [ ] Frontend wires to backend (routes/fields match API_CONTRACT.md)
- [ ] Live data flows through code → parse → L1 graph → retrieval

### Tasks
- **Backend**: Verify app startup, router mounts, ingest orchestration
- **Frontend**: Fix route wiring, field mapping to API contract
- **Integration**: Run ingest on small test repo, ask a question, get answer with code citation

### Gate G0
✓ End-to-end ingest + ask on live data works (no hardcoded responses)

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
