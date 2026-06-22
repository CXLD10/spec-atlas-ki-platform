# Master Prompt — Build the Spec-Atlas Frontend (Phases 6a–6c)

**Use this when you want one agent session to run the whole build end to end, pacing itself through the phases, rather than running each prompt file separately.** If you prefer tighter control per phase, use `PROMPT-01` through `PROMPT-03` individually instead — this file is a convenience wrapper, not different content.

**Do NOT run Phase 6d from this prompt.** That phase is explicitly gated behind hands-on design review — see `PROMPT-04-polish-pass.md` for why.

---

## Context

You're building the Spec-Atlas frontend against a **confirmed-live backend**: F-017 (Deploy + Security) is complete, 313 tests passing, `docker-compose up -d` boots the full stack locally. The visual design is **already validated** — `02-design/prototype/spec-atlas-hero.html` is a working prototype that went through two rounds of real user feedback (an intro that was too slow got fixed to a fast particle-convergence burst; ambient pulsing nodes that auto-played behind the homepage got removed entirely in favor of a calm-by-default scene that only animates on explicit user action). Your job is not to design anything new for the Landing page — it's to port a proven design into real, typed, accessible, backend-wired components, then extend the same design language to the Ask/Explore/Spec pages that didn't exist in the prototype.

**One open item inherited from the backend:** the F-017 handoff describes rate limiting as installed but not confirmed active (no test proves a 429 past the stated limits). This doesn't block your frontend work, but don't write marketing copy or demo scripts implying the API is bulletproof against abuse until that's verified on the backend side.

## Read order (do this before writing any code)

1. `00-README.md` — orientation
2. `02-design/prototype/spec-atlas-hero.html` — open in a browser, this is ground truth for Landing
3. `01-architecture/ARCHITECTURE.md`, `API-CONTRACT.md`, `STATE-MANAGEMENT.md`
4. `02-design/DESIGN-TOKENS.md`, `DESIGN-PRINCIPLES.md`
5. `03-ui-ux/INFORMATION-ARCHITECTURE.md`, `USER-FLOWS.md`, `WIREFRAMES.md`, `INTERACTION-SPEC.md`, `ACCESSIBILITY.md`
6. `04-specs/F-009-web-ui.md`, `COMPONENTS.md`
7. `05-roadmap/TASK-BOARD.md` — merge this into the project's real `tasks/BOARD.md` before starting, so task claims are tracked the same way every other phase of this project has been

## Execution order

### Phase 6a — Static shell + design system (T-FE.1–T-FE.4)
No backend dependency. Port the prototype into real components. **The one new thing not in the prototype itself:** the canvas build animation must respect `prefers-reduced-motion` — the prototype's existing reduced-motion CSS rule doesn't cover the canvas, so you're adding a real check (`useGraphBuild.ts` short-circuits to instant final-state rendering) that the prototype doesn't have. Full detail: `06-prompts/PROMPT-01-scaffold-and-scene.md`.

**Exit gate:** the React app, standalone, reproduces the prototype exactly — including the fast intro, the calm-by-default homepage, the non-pulsing nodes, and the auto-settle after a demo completes. Verify all three of those specifically; they're the exact things that were fixed once already and are easy to accidentally regress during a refactor-into-components pass.

### Phase 6b — Wire to real backend (T-FE.5–T-FE.8)
Confirm the backend is running (`docker-compose up -d`, `curl localhost:8000/health` → 200) and that your dev server's origin is in its CORS allowlist before starting. Build the API client + hooks, then wire Ask, Explore, and Spec Detail to real data. Full detail: `06-prompts/PROMPT-02-wire-real-backend.md`.

**Exit gate:** real questions get real cited answers; real groups and specs are browsable.

### Phase 6c — Real indexing flow (T-009.6 + T-FE.9–T-FE.10)
One small backend task first (an SSE progress endpoint that doesn't exist yet — don't skip it, don't fake it from the frontend), then make `GraphScene`'s live mode real. Full detail: `06-prompts/PROMPT-03-real-indexing-sse.md`.

**Exit gate:** the signature build animation is the real progress UI for real indexing, not a decoupled visual next to a separate real progress bar.

## After 6c: stop, report, wait

When 6c's exit gate is met:
1. Update `tasks/BOARD.md` — all T-FE.1–T-FE.10 and T-009.6 marked `done`
2. Append HANDOFF notes to `specs/features/F-009-web-ui.md` per the project's usual convention (what was built, decisions made — especially the typewriter-effect decision and the Ask-page-graph-or-not decision, both explicitly flagged as judgment calls in the per-phase prompts — and what the next phase can assume)
3. Tag: `git tag -a v0.6.0 -m "Frontend MVP: Landing, Ask, Explore, Spec Detail — all live-wired"`
4. **Stop.** Report what's built, and explicitly hand the "what should 6d focus on" question back to the project owner rather than guessing at it. Phase 6d's prompt (`PROMPT-04-polish-pass.md`) exists specifically to be run only after that conversation happens.

## Throughout: don't violate these even under time pressure

- No ambient/idle motion anywhere, ever — see `DESIGN-PRINCIPLES.md`'s motion-restraint section. This has already been explicitly fixed once; don't let it creep back in through a "small enhancement" during any task.
- `--l1`–`--l4` colors stay reserved for layer-identification only — never general UI chrome.
- Citations always render as the same `CitationChip` component, everywhere, no exceptions.
- Every new interactive element gets real keyboard support and a visible focus state — this is not a deferred "accessibility pass" item, it's a per-task requirement throughout 6a/6b/6c (the dedicated 6d accessibility task is a verification pass, not where the actual implementation work happens).
