# Frontend Architecture

## Tech stack (locked)

| Layer | Choice | Why |
|---|---|---|
| Framework | React 18 + TypeScript | Matches the backend team's existing comfort level; broad ecosystem for the canvas-integration work below |
| Build tool | Vite | Fast dev server, simple config, no need for Next.js's SSR — this is a client-rendered app talking to a separate API |
| Routing | `react-router` v6 | Standard, sufficient for the route list in `03-ui-ux/INFORMATION-ARCHITECTURE.md` |
| Server state | React Query (`@tanstack/react-query`) | Caching, refetch, loading/error states for all backend calls — avoids hand-rolled fetch+useState everywhere |
| Styling | Tailwind CSS, configured to read the design tokens as CSS custom properties (NOT Tailwind's default palette) | Fast iteration without fighting a CSS-in-JS bundle; tokens still live in one place (`02-design/DESIGN-TOKENS.md`) |
| Animation/graphics | Native Canvas 2D (no library) | The prototype already proves this works at the needed fidelity (signal pulses, depth projection, parallax) without the bundle weight of three.js/PixiJS for what's fundamentally 2D-with-fake-depth |
| Local/session state | React `useState`/`useReducer` only — no Redux | The app's state needs (theme, active scene phase, current repo) don't justify a global store library |

**Deployment target:** Vercel (free tier), per the cost/hosting plan already locked in the project's Phase 6 master plan. Backend lives separately (Render/Fly), already dockerized per F-017.

## Directory layout

```
frontend/
  src/
    app/
      App.tsx                  routing shell, theme provider mount
      theme/
        tokens.css             CSS variables — see 02-design/DESIGN-TOKENS.md, copy exactly
        ThemeProvider.tsx       toggle state, persists to localStorage (safe here — this is
                                 the real app, not a sandboxed artifact)
    components/
      scene/
        GraphScene.tsx          canvas-based layered build animation (ported from the
                                 prototype's <script> — it's vanilla canvas, framework-agnostic,
                                 wrap in a React component with a ref + effect for the RAF loop)
        useGraphBuild.ts        hook: drives phase/camera state from either
                                 (a) a timer [marketing demo on Landing] or
                                 (b) real SSE progress events [real index, IndexProgress page]
        layerConfig.ts          the LAYERS array — L1–L4 colors, counts, z-depth (exact
                                 values in 02-design/DESIGN-TOKENS.md)
        sceneEvents.ts           tiny event bus: CitationChip.onClick emits 'fly-to-node',
                                 GraphScene subscribes and nudges camera — decouples the
                                 two components instead of prop-drilling camera state
      hud/
        PipelineHUD.tsx         left-side L1→L4 stage indicator
      qa/
        AnswerDock.tsx          question, typewriter answer, citation chips, confidence bar
        CitationChip.tsx        clickable chip — emits scene event on click
      explore/
        GroupTree.tsx           collapsible nav (L4 groups → sub-groups)
        GroupDetail.tsx         rendered group.md + member specs list
        SpecDetail.tsx          structured spec viewer; every field's provenance is a CitationChip
      layout/
        TopBar.tsx, ThemeToggle.tsx, AmbientGrid.tsx (the fixed grid+vignette background)
    pages/
      Landing.tsx               hero + intro + timer-driven demo (mirrors the prototype exactly)
      IndexProgress.tsx         real index job — GraphScene in SSE-driven mode
      RepoAsk.tsx, RepoExplore.tsx, RepoSpec.tsx
    api/
      client.ts                 typed fetch wrapper for the backend's confirmed-live endpoints
                                 (full list in API-CONTRACT.md)
      useAsk.ts, useGroups.ts, useSpec.ts, useIndexJob.ts   (React Query hooks)
    styles/
      global.css
```

## Data flow

```
User action (ask a question / click a citation / browse a group)
  → React Query hook (api/use*.ts) calls api/client.ts
  → client.ts hits the real backend endpoint (see API-CONTRACT.md)
  → response renders into AnswerDock / GroupTree / SpecDetail
  → CitationChip clicks emit a 'fly-to-node' event on sceneEvents.ts
  → GraphScene (mounted on the same page, or globally) reacts by nudging camera depth
```

**Key architectural decision carried from the earlier execution spec:** `GraphScene` is the *same component* in two modes:
- **Landing page (marketing):** timer-driven, scripted demo data — exactly what the prototype does today
- **`/index/:jobId` (real indexing):** SSE-driven, real backend progress events

This means the "wow" animation isn't a marketing trick bolted onto a separate real progress bar — it IS the real progress UI. Build the timer-driven mode first (it already exists, ported from the prototype), then add the SSE-driven mode in Phase 6c once the backend emits progress events (see `06-prompts/PROMPT-03-real-indexing-sse.md`).

## What NOT to introduce

- No Redux/Zustand/Jotai — not justified by this app's actual state complexity
- No CSS-in-JS (styled-components, emotion) — Tailwind + CSS variables already covers the design token system cleanly
- No charting/graph library (d3, vis-network, react-flow) for the hero scene — canvas 2D is sufficient and is what the validated prototype uses; introducing a library here would mean re-deriving the exact visual behavior already proven to work
