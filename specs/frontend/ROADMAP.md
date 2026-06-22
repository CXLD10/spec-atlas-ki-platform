# Roadmap — Phase 6 (Frontend)

## Where the project stands (2026-06-20)

```
Phase 0 ✅ Foundations
Phase 1 ✅ L1 Code Graph
Phase 2 ✅ L2 Specs + Store
Phase 3 ✅ L3/L4 Group Tree + Spec Graph
Phase 4 ✅ Embeddings + Retrieval + Answerer
Phase 5a ✅ MCP Server (F-013)
Phase 6a (backend half) ✅ HTTP endpoint wiring (F-009.1–3)
F-017 ✅ Deploy + Security — 313 tests passing, dockerized, locally verified
  ⚠️ open item: confirm rate limiting is ACTIVE, not just installed (see 00-README.md)
─────────────────────────────────────────────────────────
Phase 6 (frontend, THIS DECK) 🔨 starting now
Phase 5b (optional, parallel) — F-012 Verifier, F-014 Drift, F-016 Eval — not started,
  does not block frontend, can interleave anytime
```

**The backend is done and live.** This deck exists entirely to plan and execute the frontend against it.

## Phase 6 sub-phases

| Sub-phase | Tasks | Depends on | Can start |
|---|---|---|---|
| **6a** — Static shell + design system | T-FE.1–T-FE.4 | Nothing (just the design tokens/prototype in this deck) | **Immediately** |
| **6b** — Wire to real backend | T-FE.5–T-FE.8 | Backend endpoints (✅ confirmed live) | Immediately, in parallel with 6a if you have two build tracks, or sequentially after 6a |
| **6c** — Real indexing flow | T-009.6 (backend) + T-FE.9–T-FE.10 | A small new backend endpoint that doesn't exist yet (SSE) | After 6b; the backend task (T-009.6) is small (~1-2 hrs) and can be slotted into a single session |
| **6d** — Polish pass | T-FE.11–T-FE.14 | **Your hands-on design review of the real app** | Only after 6a/6b/6c have been live and used for a while |

## Estimated timeline

- 6a: ~1 week (4 tasks, mostly porting validated prototype code into typed components)
- 6b: ~1 week (4 tasks, mostly plumbing — the backend contract is simple and already proven)
- 6c: ~3-4 days (1 small backend task + 2 frontend tasks)
- 6d: depends entirely on what your review surfaces — don't estimate this until you've done the review

**Total to a fully-wired, deployed v1 frontend (6a–6c): ~2.5–3 weeks.** 6d is open-ended by design.

## What "done" looks like at the end of Phase 6c (before polish)

A user can: land on the real deployed site, watch the fast intro, either try the scripted demo or paste a real repo URL, watch it actually index with real progress, land on a real Ask page, ask a real question, get a real cited answer, click a citation, browse the real group tree, view a real spec. All of it on the locked visual design, in both themes, with reduced-motion respected.

That's the MVP frontend. Ship that, live with it, then come back for 6d.
