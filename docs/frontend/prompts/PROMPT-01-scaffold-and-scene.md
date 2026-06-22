# PROMPT-01 — Phase 6a: Scaffold + Scene

**Phase:** 6a — Static shell + design system  
**Tasks:** T-FE.1–4  
**Duration estimate:** ~1 week  
**Dependencies:** Nothing (just design tokens, prototype, and this project's tech stack)

## Context

The backend is complete (F-017) and live. You're building a React + TypeScript + Vite frontend that will call its confirmed-live endpoints.

The visual design is **already validated** — `docs/frontend/design/prototype/spec-atlas-hero.html` is a working prototype that went through two rounds of real user feedback. Your job is NOT to redesign anything — it's to port the proven prototype into real, typed, accessible React components.

**One constraint you must respect:** canvas animation must check `prefers-reduced-motion` and skip to final state rendering if the user has enabled it. The prototype's CSS respects this for the intro, but the canvas doesn't — this is your one new thing the prototype doesn't have.

## Read order (before writing code)

1. `docs/frontend/design/prototype/spec-atlas-hero.html` — open in browser, study the intro, hero, scene behavior
2. `docs/frontend/design/DESIGN-TOKENS.md` — exact colors, typography, motion timings (use these numbers directly, don't re-derive)
3. `docs/frontend/architecture/ARCHITECTURE.md` — directory layout, tech stack decisions
4. `docs/frontend/ui-ux/WIREFRAMES.md` — Landing page layout (other pages don't need this pass yet)
5. `docs/frontend/ui-ux/ACCESSIBILITY.md` — reduced-motion requirement, keyboard basics
6. `docs/frontend/ui-ux/COMPONENTS.md` — GraphScene, useGraphBuild, PipelineHUD, AnswerDock, CitationChip specs

## Execution order (Task breakdown)

### T-FE.1 — Scaffold (frontend app + build config)
Owns: `frontend/` root, `vite.config.ts`, `tailwind.config.ts`, `src/styles/global.css`, `src/app/theme/tokens.css`

- Create React + TypeScript + Vite app
- Configure Tailwind to read design tokens as CSS custom properties (not Tailwind's default palette)
- `tokens.css` should define all `--` variables from `DESIGN-TOKENS.md` (exact values, exact names)
- `global.css` sets up baseline styles
- Theme toggle provider (light/dark mode, persists to localStorage)
- App routing shell (React Router v6)
- Health check: app boots, `/health` endpoint reachable, no TypeScript errors

### T-FE.2 — GraphScene + useGraphBuild hook
Owns: `src/components/scene/GraphScene.tsx`, `src/components/scene/useGraphBuild.ts`, `src/components/scene/layerConfig.ts`

**What this does:**  
Renders the layered L1→L4 build animation using native Canvas 2D. This is the app's signature element — it drives the visual experience on Landing and IndexProgress pages.

**Key implementation details:**
- `GraphScene.tsx` wraps vanilla canvas code (from prototype script) in a React component with a ref + useEffect for RAF loop
- `useGraphBuild.ts` hook drives phase/camera state (currently only timer-driven for demo mode; real SSE mode added in Phase 6c)
- `layerConfig.ts` exports LAYERS array with L1–L4 node counts, colors, z-depth
- **CRITICAL:** Check `prefers-reduced-motion` on mount. If true, skip animation and render final state immediately.
- Motion timings from `DESIGN-TOKENS.md` (exact values, not approximates): 1700ms per phase, exponential camera easing
- No external libraries (three.js, PixiJS, etc.) — canvas 2D is the proven approach from prototype

**Acceptance:**  
- Canvas animation renders with exact prototype behavior
- Intro works, hero appears, phases progress L1→L2→L3→L4
- `prefers-reduced-motion` checked: if true, final state renders instantly (no animation)
- No console errors, TypeScript compiles

### T-FE.3 — HUD + AnswerDock + CitationChip
Owns: `src/components/hud/PipelineHUD.tsx`, `src/components/qa/AnswerDock.tsx`, `src/components/qa/CitationChip.tsx`, `src/components/scene/sceneEvents.ts`

**What this does:**  
Three core UI components + a tiny event bus for decoupled communication.

**PipelineHUD:**  
- Renders L1–L4 stage indicator (left side, vertically centered)
- Semantic HTML (real `<ol>` list with stage labels), not div-soup — this is the accessible alternative to canvas
- Styling: monospace labels, layer colors, active state highlighting

**AnswerDock:**  
- Container for question input, answer text, citation chips, confidence bar
- Question shown prominently, answer (when available) displayed below
- Confidence bar uses `--l1` color, fills from left
- No typewriter effect in the static 6a pass — add later if needed (decision point in T-FE.6)

**CitationChip:**  
- `◆ file:line` clickable chip
- Real `<button>` or `<a>` semantics (keyboard-operable, visible focus state)
- Props: `file`, `startLine`, `endLine`, optional `layer` (0-3, for future fly-to-node styling)
- Emits a `fly-to-node` event on click (via `sceneEvents.ts` tiny event bus)

**sceneEvents.ts:**  
- Minimal pub/sub: `on('fly-to-node', callback)`, `emit('fly-to-node', nodeId)`
- Decouples CitationChip clicks from GraphScene camera changes

**Acceptance:**  
- All three components render without errors
- PipelineHUD shows L1–L4 with correct colors, semantic HTML
- CitationChip is keyboard-focusable, shows focus state, emits event on click
- AnswerDock layout matches wireframe, holds question + answer + chips + confidence bar

### T-FE.4 — Landing page + contrast verification
Owns: `src/pages/Landing.tsx`, `src/components/layout/*` (TopBar, ThemeToggle, AmbientGrid)

**What this does:**  
Assembles Landing page layout: top bar + HUD + canvas scene + hero text + repo input + AnswerDock (after demo completes).

**Landing.tsx:**  
- Mounts GraphScene in timer-driven demo mode
- Shows SPEC·ATLAS hero text + lede (exact text from prototype)
- Renders repo input field (styled per design tokens)
- After build completes (1700ms × 4 phases + 600ms delay): show AnswerDock with scripted demo answer
- "Replay" button appears after demo, lets user restart
- CORS-aware: input is disabled / shows "backend unavailable" if `/health` check fails on mount

**TopBar.tsx:**  
- Persistent header (same height/treatment on all pages)
- Brand mark + optional nav links (Docs, GitHub, MCP)
- Theme toggle (right side)
- Must not shift between pages

**ThemeToggle.tsx:**  
- Dual-state icon toggle (sun/moon)
- Slide animation (350ms per `DESIGN-TOKENS.md`)
- Persists to localStorage as `theme: 'light' | 'dark'`

**AmbientGrid.tsx:**  
- Fixed background: faint grid lines + vignette
- Renders on all pages (Landing, Ask, Explore, Spec)
- CSS only (no canvas)

**Acceptance:**  
- Landing page reproduces prototype exactly:
  - Fast intro convergence (~1300ms to particles settling)
  - Hero snap-in (mark, title, sub at 680/780/860ms)
  - Scene builds through L1→L4
  - Q&A dock appears after build
  - Typewriter effect types demo answer (scripted, not real backend call yet)
  - Confidence bar fills
  - "↻ Replay" button appears, restarts demo
- Contrast check: all text readable in both light + dark themes
- No ambient idle motion (prototype had pulsing nodes that were removed)
- Theme toggle persists across page reload

## Exit gate

The React app, standalone, reproduces the prototype exactly. Verify these three things specifically:
1. **Fast intro:** particle convergence is snappy, finishes at ~1700ms, not slow
2. **Calm by default:** canvas scene is blank/calm until a user action, not auto-animating
3. **No ambient motion:** there is no subtle pulsing or floating anywhere when scene is idle

These are the exact things that were fixed once already in user feedback. They're easy to regress during component refactor — check them explicitly.

## Notes

- Use the exact timings from `DESIGN-TOKENS.md` — they were tuned through feedback
- CSS variables (`--l1`, `--cyan`, etc.) should render correctly in both light/dark mode
- No external animation libraries (Framer Motion, etc.) — the prototype uses vanilla CSS + canvas RAF loop
- All interactive elements (CitationChip, theme toggle, etc.) must have visible keyboard focus states
- `prefers-reduced-motion` check is non-negotiable — test with `prefers-reduced-motion: reduce` in dev tools
