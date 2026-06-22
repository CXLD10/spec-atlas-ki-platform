# User Flows

## Flow 1 — First-time visitor

```
Land on /
  → fast intro plays (~1.7s, auto, not skippable — it's short enough not to need a skip button)
  → hero appears, calm, no ambient motion
  → user reads headline + lede, sees the repo-URL input
  → EITHER:
      (a) types a real repo URL → clicks "Index repo" → Flow 2
      (b) clicks "Watch a live index" → the SAME build animation plays with scripted
          demo data (no real backend call) → ends in the scripted Q&A → user has now
          SEEN the product's value without indexing anything real
  → "Replay index" button appears once the demo/build finishes, for re-watching
```

**Design intent:** option (b) exists because not everyone has a repo URL ready at hand on first visit — it's a zero-commitment way to understand what the product does before investing in a real index.

## Flow 2 — Indexing a real repo

```
User submits a URL on / or /index
  → POST /api/ingest (rate-limited 5/hr — if the limit is hit, show the system-voice
     error: "Too many index requests right now. Try again in a few minutes." — not a
     raw 429 status dump)
  → redirect to /index/:jobId
  → GraphScene plays in REAL-DATA mode (Phase 6c) — same visual language as the demo,
     driven by actual backend stage events, not a timer
  → on completion → redirect to /repo/:repoId/ask, pre-seeded with a suggested
     question (e.g., "What does this repository do?") so the user isn't staring at
     an empty input
```

**Before Phase 6c lands (interim, Phase 6a/6b state):** `/index/:jobId` polls `GET /api/ingest/{job_id}/status` instead of using SSE, and shows a simpler progress indicator (the HUD stage list, advanced via polled percentage thresholds rather than real per-stage events) rather than the full real-time scene. This is an acceptable interim state — don't block Phase 6a/6b shipping on Phase 6c's SSE work.

## Flow 3 — Asking a question

```
On /repo/:repoId/ask
  → user types a question, submits
  → useAsk() fires POST /api/ask (rate-limited 20/min)
  → loading state: AnswerDock shows a pulse indicator (reuse the existing .pulse dot
     pattern from the prototype's qa-head), not a generic spinner
  → answer renders: text + interleaved CitationChips, confidence bar fills
  → user clicks a citation chip
      → sceneEvents emits 'fly-to-node'
      → IF a GraphScene is mounted on this page (see open design question below),
        camera nudges toward that layer
      → a code-snippet panel/modal opens showing the cited file:line — calls
        GET /api/code-snippet (currently a stub; show "source preview unavailable"
        gracefully if empty, per API-CONTRACT.md)
```

**Open design question for your review pass (Phase 6d):** the prototype's hero has `GraphScene` and `AnswerDock` on the same page, so "fly to node" has somewhere to fly. On `/repo/:repoId/ask` as a dedicated full page, is a persistent background graph visualization (smaller, corner-docked?) worth keeping, or does the Ask page work better as a focused, graph-free reading experience with citations just opening a code-snippet panel directly? **Recommendation:** ship Ask without a persistent graph in 6b (simpler, faster to build, avoids the "graph-free Ask page might be better" question blocking progress), and revisit in 6d once you've used the real thing — this is exactly the kind of call your hands-on design review should make, not something to guess at now.

## Flow 4 — Exploring the knowledge tree

```
On /repo/:repoId/explore
  → GroupTree shows the root-level groups (from GET /api/groups)
  → user clicks a group → GroupDetail fetches GET /api/groups/{id}, renders
     summary_md + lists member specs
  → user clicks a member spec → navigates to .../explore/specs/:ref → SpecDetail
     renders the full structured spec, every field's provenance as a CitationChip
  → clicking a citation chip here behaves the same as Flow 3 (opens code-snippet panel)
```

## Flow 5 — Theme switching

```
Any page → click ThemeToggle in top bar → CSS variables swap (0.35s thumb-slide,
per DESIGN-TOKENS.md) → choice persists to localStorage → respected on next visit
```

No flow complexity here — it's a straightforward, instant, persisted toggle. Don't add a "system preference" auto-detect option in v1 unless explicitly requested; it adds a third state (light/dark/auto) to test and explain for marginal value at this stage.
