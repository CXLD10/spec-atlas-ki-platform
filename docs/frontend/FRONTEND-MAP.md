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
  - `/` → Landing page
  - `/projects` → Projects list & management
  - `/graph` → Graphify (3D visualization)
  - `/ask` → Q&A interface
  - `/specify` → Spec creation tool
  - `/dashboard` → Project dashboard
  - `/docs` → Documentation
  - `/index/:jobId` → Index progress tracking
  - `/repo/:repoId/*` — Repo-scoped routes (ask, graphify, specify, explore)

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
- **Method:** Hybrid: Tailwind CSS + CSS custom properties + component-scoped CSS files
- **Tailwind:** Configured with GitHub Dark/Light themes in `frontend/tailwind.config.ts`
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

### Dependencies Summary
- **React:** 18.2.0
- **React Router:** 6.20.0
- **React Query:** 5.25.0
- **Three.js:** 0.184.0 (3D visualization)
- **React Markdown:** 9.0.1
- **Lucide React:** 1.21.0 (icons)
- **Tailwind CSS:** 3.4.0
- **TypeScript:** 5.3.0
