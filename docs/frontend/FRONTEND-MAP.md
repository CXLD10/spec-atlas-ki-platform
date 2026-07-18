# Frontend Map

**Frontend Root:** `frontend/src/`

## Key Files & Directories

### Entry Points
- `frontend/src/main.tsx` — React entry point, mounts App component
- `frontend/src/app/App.tsx` — Main app component, router setup, provider stack

### Router
- **File:** `frontend/src/app/App.tsx:1-50`
- **Library:** react-router-dom (v6.20.0)
- **Routes:**
  - `/` → Dashboard (home)
  - `/sources` → Source manager
  - `/kb` → Knowledge Base (specs browser)
  - `/graph` → Knowledge Graph (3D isometric)
  - `/ask` → Ask Atlas (Q&A chat)
  - `/specify` → Spec generator tool
  - `/mcp` → MCP server console
  - `/docs` → Documentation
  - `/index/:jobId` → Index progress tracking

### Layout & Shell
- **TopBar:** `frontend/src/components/layout/TopBar.tsx` (+ TopBar.css) — Header with navigation
- **Sidebar:** `frontend/src/components/layout/Sidebar.tsx` (+ Sidebar.css) — Side navigation panel
- **AmbientGrid:** `frontend/src/components/layout/AmbientGrid.tsx` (+ AmbientGrid.css) — Background grid visual
- **ThemeToggle:** `frontend/src/components/layout/ThemeToggle.tsx` (+ ThemeToggle.css) — Light/dark mode toggle

### Theme Provider
- **File:** `frontend/src/app/theme/ThemeProvider.tsx`
- **Type:** React Context with light/dark toggle
- **Data Attribute:** `data-theme` set on `document.documentElement`
- **Storage:** localStorage key: `theme`
- **Hook:** `useTheme()` for accessing theme state and toggle function
- **Tokens:** `frontend/src/app/theme/tokens.css` — CSS custom properties for colors, fonts, timings

### Pages (Route Components)
- **Directory:** `frontend/src/pages/`
- **Components:**
  - `Landing.tsx` (+ Landing.css) — Homepage with intro
  - `Projects.tsx` (+ Projects.css) — Project list
  - `ProjectDetail.tsx` (+ ProjectDetail.css) — Single project view
  - `RepoAsk.tsx` (+ RepoAsk.css) — Q&A chat interface
  - `RepoExplore.tsx` (+ RepoExplore.css) — Repo exploration
  - `RepoGraphify.tsx` (+ RepoGraphify.css) — 3D graph/visualization
  - `RepoSpec.tsx` (+ RepoSpec.css) — Individual spec view
  - `SpecifyTool.tsx` (+ SpecifyTool.css) — Spec creation/editing
  - `SpecView.tsx` (+ SpecView.css) — Spec detail view
  - `Docs.tsx` (+ Docs.css) — Documentation/guide
  - `IndexProgress.tsx` (+ IndexProgress.css) — Indexing job status

### API Client & Hooks
- **API Client:** `frontend/src/api/client.ts` — Fetch-based HTTP client
- **Hooks (React Query):**
  - `frontend/src/api/useAsk.ts` — Q&A queries
  - `frontend/src/api/useGraph.ts` — Graph data
  - `frontend/src/api/useGroups.ts` — Groups/collections
  - `frontend/src/api/useIndexJob.ts` — Index job status
  - `frontend/src/api/useSources.ts` — Source data
  - `frontend/src/api/useSpec.ts` — Spec queries
  - `frontend/src/api/useSpecGraph.ts` — Spec graph queries

### Styling Approach
- **Method:** CSS custom properties + component-scoped CSS files (Apple-inspired dark mode design)
- **No Tailwind** — styling uses plain CSS + design tokens
- **CSS Variables:** Defined in `frontend/src/app/theme/tokens.css`
  - Colors: `--bg`, `--panel`, `--ink`, `--cyan`, `--l1` (code), `--l3` (specs), `--l4` (groups)
  - Fonts: `--font-display` (Space Grotesk), `--font-mono` (JetBrains Mono)
  - Timing: Motion durations and easing functions
- **Global Styles:** `frontend/src/styles/global.css`
  - Baseline resets, focus states, button/input resets
  - Glass panel recipe (`.glass-panel` with blur backdrop)
  - Monospace text recipe (`.mono`)
  - Theme-specific overrides for light/dark modes
- **Component Styles:** Each page has a paired `.css` file with scoped styles

### Other Components
- **Explore Components:** `frontend/src/components/explore/` — Search & exploration UI
- **HUD Components:** `frontend/src/components/hud/` — Heads-up display elements
- **QA Components:** `frontend/src/components/qa/` — Q&A specific UI
- **Scene Components:** `frontend/src/components/scene/` — 3D scene & visualization
- **Sources Components:** `frontend/src/components/sources/` — Source/reference display

### Data Fetching
- **Library:** TanStack React Query (v5.25.0)
- **Config:** `frontend/src/app/App.tsx:17-24`
- **Defaults:** 5-minute staleTime, 10-minute garbage collection

### Build & Dev
- **Build Tool:** Vite (v5.0.0)
- **Config:** `frontend/vite.config.ts`
- **Dev Server:** Port 5173 (auto-opens in browser)
- **Chunking:** Three.js and React Router split into separate chunks
- **TypeScript:** Strict mode, v5.3.0

---

## Document & KB Endpoints (Verify or Implement — P1)

**Backend status:** Repo ingest via `/api/ingest` is live. PDF/Markdown adapters exist in backend. Specs endpoints serve code specs.

**Frontend needs (mark `// BACKEND-DEP:` in client if missing):**

| Endpoint | Purpose | Status |
|---|---|---|
| `POST /api/documents` (multipart) | Upload PDF/XLSX/MD | **NEEDED** — adapters exist, needs HTTP route |
| `GET /api/documents` | List uploaded documents | **NEEDED** |
| `GET /api/documents/:id` | Get one document metadata | **NEEDED** |
| `GET /api/documents/:id/status` | Document ingestion progress | **NEEDED** (may reuse /api/ingest/:jobId/status) |
| `GET /api/sources` | List both repos + documents (unified) | **DONE** — `api/sources.py` |
| `GET /api/sources/:id` | Get source (repo or document) | **DONE** — `api/sources.py` |
| `GET /api/kb` | List knowledge cards/specs (all) | **DONE** — `api/kb.py` |
| `GET /api/kb/:ref` | One knowledge card/spec + markdown | **DONE** — `api/kb.py` |
| `GET /api/source-snippet?doc=:id&page=:n` | Citation preview (file:line or p.N) | **NEEDED** |

**Live endpoints:**
- `POST /api/ingest` {repo_url} → JobStatus
- `GET /api/ingest/{job_id}` → JobStatus (poll progress)
- `GET /api/sources` → sources list
- `DELETE /api/sources/{id}` → remove source
- `GET /api/graph/nodes` + `GET /api/graph/edges` → graph data
- `GET /api/groups` → group tree
- `GET /api/specs/{component_ref}` → Spec
- `POST /api/specs/generate/{component_ref}` → generate spec
- `GET /api/kb` + `GET /api/kb/{ref}` → knowledge cards
- `POST /api/ask` {question, repo} → answer + claims
- `POST /api/ask/stream` → SSE streaming answer
- `POST /api/mcp/call` {tool, args} → MCP tool result
- `GET /health` → status

**Frontend strategy:**
- Ingest: use `/api/ingest` for repos; create `/api/documents` POST for files (POST endpoint will wire the adapters).
- Sources: create a `/api/sources` endpoint that unions repo + document lists, or list documents + query repo separately.
- KB: map `/api/kb/:ref` to `/api/specs/:ref` + ensure markdown field is populated.
- Progress: reuse `/api/ingest/:jobId/status` for document uploads if document post returns same JobStatus.
- Mock fallback: if VITE_API_URL is empty or endpoints fail, return MOCK_SOURCES, MOCK_CARDS, etc.

### Dependencies Summary
- **React:** 18.2.0
- **React Router:** 6.20.0
- **React Query:** 5.25.0
- **Three.js:** 0.184.0 (3D visualization)
- **React Markdown:** 9.0.1
- **Lucide React:** 1.21.0 (icons)
- **Tailwind CSS:** 3.4.0
- **TypeScript:** 5.3.0
