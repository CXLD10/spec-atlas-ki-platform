# Component Contracts

One entry per component named in `01-architecture/ARCHITECTURE.md`'s directory layout. Each has: purpose, props, and the one or two things most likely to go wrong if built carelessly.

---

### `GraphScene`
**Purpose:** renders the layered L1→L4 canvas build animation; the app's signature element.
**Props:** `mode: 'timer' | 'live'`, `jobId?: string` (required when `mode='live'`), `onPhaseComplete?: (phase: number) => void`
**Watch for:** must check `prefers-reduced-motion` on mount and short-circuit to final-state rendering (see `ACCESSIBILITY.md`) — this is the single most important thing to get right and the easiest to forget since the prototype doesn't do it.

### `useGraphBuild`
**Purpose:** hook that drives `GraphScene`'s internal phase/camera state from either a timer (demo) or real backend events (`live` mode).
**Returns:** `{ phase, camTargetZ, nodes, edges, interactive }` — internal to the scene component, not really consumed elsewhere.
**Watch for:** in `live` mode, must gracefully handle the SSE endpoint not existing yet (Phase 6c) by falling back to polling `/api/ingest/{job_id}/status` and synthesizing reasonable phase transitions from the percentage — don't let `IndexProgress.tsx` hard-fail just because 6c hasn't landed.

### `PipelineHUD`
**Purpose:** the L1–L4 stage list (left side on Landing/IndexProgress).
**Props:** `activeStage: number, stages: Array<{id, label, sublabel}>`
**Watch for:** must be semantic markup (a real list with text status), not div-soup — this is the accessible alternative to the canvas per `ACCESSIBILITY.md`.

### `AnswerDock`
**Purpose:** question + typewriter/real answer + citation chips + confidence bar.
**Props:** `question: string, answer?: Answer (from useAsk), isLoading: boolean`
**Watch for:** the typewriter effect is cosmetic for the demo; for **real** answers (Phase 6b), consider rendering immediately rather than typing out a potentially-long real answer character by character — re-evaluate whether the typewriter effect actually serves a real (not scripted-demo) answer, or whether it just makes the user wait longer for information they asked for. This is worth a quick decision before T-FE.6, not a default carry-over from the demo.

### `CitationChip`
**Purpose:** the `◆ file:line` clickable chip.
**Props:** `file: string, startLine: number, endLine?: number, layer?: number (0-3, for the fly-to-node visual only — optional, omit if no scene is present on the page)`
**Watch for:** must remain keyboard-focusable and operable (it's a real button/link, not a styled `<span>` with an onClick) — see `ACCESSIBILITY.md`.

### `GroupTree`
**Purpose:** collapsible nav of the L4 group hierarchy.
**Props:** `groups: GroupNode[], activeId?: string, onSelect: (id: string) => void`
**Watch for:** keyboard operability (arrow/tab/enter) is a hard requirement, not polish — see `ACCESSIBILITY.md`. If using a headless tree library, verify this is built in before committing to it; if hand-rolling, budget real time for it in T-FE.7, don't treat it as a 6d cleanup item.

### `GroupDetail`
**Purpose:** renders a group's `summary_md` + lists member specs with status badges.
**Props:** `group: GroupDetail (from useGroups)`
**Watch for:** status badges (draft/verified/stale) need both color AND text label — never color-only (see `ACCESSIBILITY.md`).

### `SpecDetail`
**Purpose:** the full structured spec viewer.
**Props:** `spec: Spec (from useSpec)`
**Watch for:** every provenance-bearing field renders as a `CitationChip`, consistently — don't let some fields show plain `file:line` text and others show the chip component; the whole point of the chip pattern is that citations always look the same everywhere in the app.

### `TopBar`
**Purpose:** persistent brand + nav + theme toggle.
**Props:** `variant: 'marketing' | 'workspace'` (marketing shows Docs/MCP/GitHub links; workspace shows Ask/Explore secondary nav)
**Watch for:** must render identically across pages within the same variant — no per-page tweaks to height/spacing/brand treatment.

### `ThemeToggle`
**Purpose:** light/dark switch.
**Props:** none (reads/writes `ThemeProvider` context)
**Watch for:** persist to `localStorage`, read on initial mount before first paint if possible (avoids a flash of the wrong theme on load — consider an inline blocking script in `index.html` that sets the initial `data-theme` attribute before React even hydrates, a common pattern for this exact flash-of-wrong-theme problem).

### `AmbientGrid`
**Purpose:** the fixed, faint background grid (the `body::before` pattern from the prototype, extracted into its own component/CSS for reuse across pages — but note this is NOT the node-scene canvas, just the static grid texture).
**Props:** none
**Watch for:** nothing tricky — this is intentionally the simplest, most static element in the whole app, by design (per the motion-restraint principle, most of the app should look like this: quiet).
