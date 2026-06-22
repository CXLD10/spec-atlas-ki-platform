# Interaction Spec

Exact behaviors, ported from the validated prototype. Timings live in `DESIGN-TOKENS.md`; this doc describes the *behavior*, not just the numbers.

## Intro sequence

1. ~130 particles spawn at random positions just outside the viewport edge, each assigned one of 5 target points (matching the brand mark's node layout).
2. Each particle animates toward its target with a fast-then-settle ease (`1 - (1-progress)^4`), leaving a short motion-blur trail (drawn via a translucent fill-rect clear each frame, not a full clear — this is what produces the streak look).
3. As particles converge, the brand mark SVG, title, and subtitle snap in with a slight overshoot (scale 0.82 → 1.05 → 1.0), staggered ~100ms apart.
4. The whole intro overlay cuts to the hero via a fast opacity+blur transition — not a slow fade.
5. **No skip button.** At ~1.7s total, it's short enough that skip controls would add more UI than they save in time. (If this is ever revisited, e.g. for a "skip on repeat visits" cookie-based behavior, that's a 6d-or-later consideration, not v1.)

## The build sequence (L1 → L4)

1. Triggered only by explicit user action: clicking "Index repo" (real flow) or "Watch a live index" (scripted demo) — **never automatically**.
2. Each layer (L1 Code Graph → L2 Specs → L3 Spec Graph → L4 Group Tree) gets a fixed window to build in (1700ms in the demo; in the real-data mode, this becomes event-driven rather than fixed-duration — see Phase 6c notes in `04-specs/F-009-web-ui.md`).
3. Within a layer's window: nodes pop in with a quick grow-and-settle (no continuous pulsing once formed), edges draw in with a short fade, and edges that cross from one layer to the layer above carry a traveling signal-pulse dot (this visualizes "specs are derived FROM the graph below them," not random decoration).
4. The simulated camera (`camZ`) eases toward whichever layer is currently building, via exponential approach (`camZ += (target - camZ) * 0.05` per frame) — this produces the "dollying through depth" feel without needing a real 3D engine.
5. A subtle mouse-driven parallax applies throughout (nodes shift slightly opposite mouse position) — this is allowed ambient motion because it's responsive to user input, not self-running; it does not violate the motion-restraint principle.
6. Once L4 completes, the HUD shows all 4 stages as "done," the scene becomes interactive, and after a short pause the Q&A demo begins.

## Citation chip → camera fly-to

1. Each citation chip (`◆ file:line`) is clickable.
2. On click: the camera's target depth (`camTargetZ`) jumps to a value associated with the cited layer, holds briefly (~700ms), then eases back to a resting mid-depth.
3. This is a **deliberately small, quick gesture** — not a dramatic multi-second cinematic zoom. It's meant to give a light sense of "the evidence lives over here in the graph," not to be the visual centerpiece of the Ask page (the answer text and citations are the centerpiece there; the graph fly-to is a supporting flourish, if a graph is even present on that page — see the open question in `USER-FLOWS.md` Flow 3).

## Scene auto-settle

1. After the Q&A demo's answer finishes typing, the scene holds as-is for 6 seconds (enough time to actually read the answer).
2. It then fades out smoothly (~0.9s) back to a fully calm, blank state — nodes and edges are cleared, the HUD hides.
3. A "Replay" button (which appeared once the build completed) remains available to re-trigger the whole sequence on demand.
4. **This auto-settle exists specifically so the homepage never has graph content sitting indefinitely behind other page content** — it's a direct response to the earlier "I don't like the pulsating nodes behind it" feedback, generalized: even non-pulsing static content shouldn't sit there forever uninvited.

## Theme toggle

Instant CSS variable swap; the only animated part is the toggle thumb's slide (350ms). No page-wide transition/fade when switching themes — that would feel sluggish for what should be an instant preference change.

## Reduced motion

`prefers-reduced-motion: reduce` must collapse all animation/transition durations to near-zero (already implemented as a global override in the prototype's CSS — port this rule as-is, it's a single block):
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.1ms !important; }
}
```
**Caveat for the React port:** the canvas-based `GraphScene` animation is driven by JS (`requestAnimationFrame`), not CSS, so this media query alone won't affect it. `useGraphBuild.ts` must check `window.matchMedia('(prefers-reduced-motion: reduce)')` and, if true, skip the animated build entirely — render the final state of each layer immediately rather than animating the convergence. This is a real gap in the prototype (which is CSS/HTML-only for the intro but canvas-driven for the build) — **flag this explicitly as a task**, don't let it silently ship unhandled. See `ACCESSIBILITY.md`.
