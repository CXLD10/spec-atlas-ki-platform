# Frontend Development Guide — Spec-Atlas

This directory contains all documentation for building the Spec-Atlas frontend (Phase 6, F-009).

**Status:** Frontend development ready. Backend is live (F-017 complete, 313 tests passing, docker-compose verified).

## Quick start

1. **Read in this order:**
   - `MASTER-PROMPT-run-all-phases.md` — overview of all phases and execution strategy
   - `prompts/PROMPT-04-polish-pass.md` — understanding the polish phase constraints
   - This file (README.md) — navigation guide

2. **Understand the design:**
   - `design/prototype/spec-atlas-hero.html` — open in browser, this is the Landing page reference
   - `design/DESIGN-TOKENS.md` — color, typography, motion timings (exact values extracted from prototype)
   - `design/DESIGN-PRINCIPLES.md` — motion constraints, layer color usage rules

3. **Learn the architecture:**
   - `architecture/ARCHITECTURE.md` — tech stack, directory layout, data flow
   - `architecture/API-CONTRACT.md` — confirmed live backend endpoints
   - `architecture/STATE-MANAGEMENT.md` — React Query for server state, useState for UI state

4. **Plan the UI:**
   - `ui-ux/INFORMATION-ARCHITECTURE.md` — page structure and navigation
   - `ui-ux/USER-FLOWS.md` — user journey through each feature
   - `ui-ux/WIREFRAMES.md` — ASCII layouts for Landing, Ask, Explore, Spec Detail
   - `ui-ux/COMPONENTS.md` — detailed component contracts
   - `ui-ux/INTERACTION-SPEC.md` — interaction patterns and state transitions
   - `ui-ux/ACCESSIBILITY.md` — keyboard support, reduced-motion, ARIA

5. **Reference during build:**
   - `prompts/PROMPT-01-scaffold-and-scene.md` — detailed Phase 6a instructions
   - `prompts/PROMPT-02-wire-real-backend.md` — detailed Phase 6b instructions
   - `prompts/PROMPT-03-real-indexing-sse.md` — detailed Phase 6c instructions

## Directory structure

```
docs/frontend/
  README.md (this file)
  
  architecture/
    ARCHITECTURE.md          — Tech stack, directory layout, data flow
    API-CONTRACT.md          — Backend endpoint list (confirmed live)
    STATE-MANAGEMENT.md      — React Query + useState patterns
  
  design/
    DESIGN-TOKENS.md         — Colors, typography, motion timings (extracted from prototype)
    DESIGN-PRINCIPLES.md     — Layer colors reserved, motion constraints
    prototype/
      spec-atlas-hero.html   — Working prototype (ground truth for Landing page)
  
  ui-ux/
    INFORMATION-ARCHITECTURE.md  — Pages and navigation
    USER-FLOWS.md               — User journeys per feature
    WIREFRAMES.md               — ASCII layout sketches
    COMPONENTS.md               — Component contracts and prop specs
    INTERACTION-SPEC.md         — Interaction patterns
    ACCESSIBILITY.md            — Keyboard, reduced-motion, ARIA rules
  
  prompts/
    MASTER-PROMPT-run-all-phases.md  — Full build overview and execution strategy
    PROMPT-01-scaffold-and-scene.md  — Phase 6a (static shell + design system)
    PROMPT-02-wire-real-backend.md   — Phase 6b (wire to real backend)
    PROMPT-03-real-indexing-sse.md   — Phase 6c (real indexing flow)
    PROMPT-04-polish-pass.md         — Phase 6d (polish, gated behind design review)
```

## Execution phases

### Phase 6a — Static shell + design system
**Tasks:** T-FE.1–4 (scaffold, scene, HUD/dock, landing page)
**Dependencies:** None (just design tokens and prototype)
**Can start:** Immediately

Goals:
- React app boots with Vite + Tailwind + TypeScript
- GraphScene component renders the canvas build animation
- PipelineHUD, AnswerDock, CitationChip components built and styled
- Landing page reproduces prototype exactly
- Theme toggle (light/dark) works and persists
- prefers-reduced-motion respected for both CSS and canvas animations

### Phase 6b — Wire to real backend
**Tasks:** T-FE.5–8 (API client, hooks, Ask/Explore/Spec pages)
**Dependencies:** Phase 6a complete, backend live (✅ confirmed)
**Can start:** Immediately (in parallel with 6a if desired)

Goals:
- API client wraps backend endpoints with proper error handling
- useAsk, useGroups, useSpec, useIndexJob hooks built with React Query
- RepoAsk page displays real questions and answers with working citations
- RepoExplore shows real group tree with real summaries
- RepoSpec shows full spec detail with all citations
- All pages keyboard-accessible (GroupTree tree navigation, etc.)

### Phase 6c — Real indexing flow
**Tasks:** T-009.6 (backend: SSE endpoint), T-FE.9–10 (live graph mode, IndexProgress)
**Dependencies:** Phase 6b complete
**Can start:** After phase 6b (T-009.6 is small, ~1-2 hrs of backend work)

Goals:
- Backend emits SSE events during indexing (T-009.6)
- useGraphBuild hook operates in "live" mode, consuming real events
- IndexProgress page shows real indexing progress with signature animation
- Fallback to polling if SSE not ready (Phase 6a/6b can ship with status polling)

### Phase 6d — Polish pass
**Tasks:** T-FE.11–14 (empty/error states, mobile, accessibility verification, design review output)
**Dependencies:** Phase 6c live + hands-on design review
**Status:** Blocked until review happens

Goals:
- Guided by review feedback (don't pre-guess scope)
- Empty states, error messages per voice guidance
- Mobile responsive beyond Landing page
- Full accessibility verification (keyboard focus states, ARIA, etc.)

## Blocked by: design review

Phase 6d is explicitly gated behind your hands-on review of the live app (6a–6c deployed and in-use). Per `PROMPT-04-polish-pass.md`, once you've used it, review surfaces specific tasks — don't try to pre-define 6d scope now.

## Key constraints (hard requirements, not stretch goals)

1. **Reduced-motion everywhere:** Both CSS intro and canvas animation must respect `prefers-reduced-motion`. Not a deferred 6d task.

2. **Citations always consistent:** CitationChip component used everywhere (AnswerDock, GroupDetail, SpecDetail) — never plain text or different component for the same data.

3. **Layer colors reserved:** --l1, --l2, --l3, --l4 never in general UI chrome (buttons, borders). Only for layer identification (HUD, citation chips, graph nodes).

4. **Keyboard accessible:** Every interactive element navigable + operable via keyboard. Full implementation in each task, not a 6d cleanup pass.

5. **Design tokens exact:** Use the numbers in `DESIGN-TOKENS.md` directly (they were tuned through user feedback and re-derived values risk reintroducing fixed bugs).

## Backend status

✅ Live and confirmed working:
- `POST /api/ask` — question → answer with claims (20/min rate limit)
- `GET /api/groups`, `/api/groups/{id}` — group tree + summaries
- `GET /api/specs/{ref}` — full spec detail with status
- `POST /api/ingest`, `GET /api/ingest/{job_id}/status` — repo indexing + polling
- `GET /health` — system status check
- CORS locked to frontend origin (configurable)

🟡 Not yet live (Phase 6c blocker):
- `GET /api/ingest/{job_id}/events` (Server-Sent Events) — this is T-009.6, a small backend task

## Deployment

- Frontend: Vercel (free tier, auto-deploys from git)
- Backend: Render or Fly.io (free tier, docker-compose verified locally)
- Database: Neon Postgres with pgvector (free tier)

See `/docs/DEPLOY.md` for full deployment instructions (inherited from F-017).

## Testing standards

Follow `.claude/skills/testing-standard` for what "tested" means. Each task should include:
- Unit tests for hooks + components
- Integration tests for pages with real/mock API
- Visual regression tests if applicable (compare to prototype)

All tests must pass before marking a task done.

## Handoff protocol

When each phase completes:
1. Update `tasks/BOARD.md` — set tasks to `done`
2. Append HANDOFF notes to `specs/features/F-009-web-ui.md` with:
   - What was built
   - Key architectural decisions (especially "judgement call" items flagged in prompts)
   - What the next phase can assume
3. Tag the commit (e.g., `git tag -a v0.6.0 -m "Frontend MVP: Landing, Ask, Explore, Spec Detail"` after 6c)

## Questions?

Refer back to the referenced docs in each section. The architecture, design, and prompts contain the ground truth — this README is navigation only.
