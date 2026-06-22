# Accessibility

This design leans heavily on canvas animation and color-coded information (layer accents). Both need deliberate accessibility handling — neither is accessible "for free" by default.

## Reduced motion (real gap to close, not yet handled in the prototype)

The prototype's `prefers-reduced-motion` CSS rule only affects CSS-driven animation (the intro's snap-in keyframes, theme toggle, hover states). It does **not** affect the canvas `GraphScene`, which is driven entirely by `requestAnimationFrame` and plain JS timers.

**Required for the React build (not optional, not a "nice to have"):**
- `useGraphBuild.ts` checks `matchMedia('(prefers-reduced-motion: reduce)').matches` on mount.
- If true: render all 4 layers' final state immediately (no phased build, no particle convergence, no camera dolly). The HUD should show all stages as "done" instantly. The Q&A demo can still type out (text typewriter is informational, arguably fine to keep, but consider showing it instantly too — err on showing everything immediately when this flag is set).
- The intro: skip straight to the hero (no particle burst) when this preference is set — show the static brand mark/title/subtitle in place, no animation.
- This is a real implementation task — add it explicitly to T-FE.2's Definition of Done in `04-specs/F-009-web-ui.md`, don't assume it falls out of porting the prototype's existing CSS rule.

## Color contrast

- Dark mode `--ink` (`#dff3ff`) on `--bg` (`#04070d`): passes WCAG AA comfortably for body text (very high contrast).
- Dark mode `--ink-dim` (`#6b8299`) on `--bg`: check against AA for any text smaller than 14px using this color — at the HUD label size (11-12px) this is borderline and should be verified with an actual contrast checker during build, not assumed.
- Light mode equivalents need the same check — `--ink-dim` light value (`#5a7286`) on `--bg` light (`#eef3f7`) likely passes but verify.
- **Citation chips:** `--l3` amber (`#ffc24d` dark / `#c8860a` light) on the chip's translucent background — verify contrast of the chip *text* against its own fill, not just against the page background, since it's a layered translucent element.

## Color is never the only signal

- Spec status badges (draft/verified/stale) use layer-accent colors, but **must also use a text label** ("draft," "verified," "stale"), never color alone — this is already implied by the wireframes but call it out explicitly: a colorblind user or anyone in a noisy visual environment needs the word, not just the dot.
- HUD stage indicators (L1-L4) likewise pair color with the text label ("L1 · Code Graph") — already the case in the prototype, just confirm this carries through the React port and isn't simplified to color-only icons at some point for "cleaner" UI.

## Keyboard navigation & focus

- Every interactive element (repo input, Index button, theme toggle, citation chips, GroupTree nodes, nav links) must have a visible focus state. The prototype currently relies on default browser focus styles in most places — **explicitly define a focus ring using `--cyan` with sufficient offset** in the React build rather than leaving it to browser defaults, which can be inconsistent across browsers and easy to accidentally suppress with a stray `outline: none` somewhere in a reset.
- `GraphScene`'s canvas is **not** keyboard-interactive (clicking nodes directly in the canvas isn't part of the v1 spec — citation chips are the only click-through to the scene, and those are normal DOM elements, already keyboard-focusable/operable by default).
- `GroupTree` must be operable via keyboard (arrow keys or tab+enter to expand/collapse and navigate) — if using a library for the tree component, confirm it has this built in; if hand-rolled, this is a real implementation requirement, not optional polish.

## Screen readers & the canvas scene

The canvas itself is decorative-with-informational-intent (it visualizes pipeline progress, but the same information exists in text form in the HUD labels). **Approach:**
- Give the canvas element `aria-hidden="true"` — it adds no information a screen reader user can't already get from the HUD's text labels and the page's actual content.
- Ensure the HUD stage list is real, semantic markup (a list, with each stage's name and current status as text — "Code Graph: in progress" / "Code Graph: done") rather than purely visual dot-and-label divs with no semantic structure. This is the accessible alternative path required by the original Phase 6 plan's accessibility task (T-FE.13) — this doc makes that requirement concrete instead of leaving it as a vague "do an accessibility pass" line item.
- Index progress: ensure `IndexProgress.tsx` exposes the percentage/stage as text content (not just a canvas-rendered progress visualization) so a screen reader user can follow real ingestion progress.

## Summary of concrete build tasks this implies

These should be folded into the relevant tasks in `05-roadmap/TASK-BOARD.md` rather than treated as a separate vague "accessibility task" at the end:
1. `useGraphBuild.ts` reduced-motion branch (T-FE.2)
2. Explicit focus-ring styling, not browser defaults (T-FE.1, the design-system setup task)
3. `aria-hidden` on the scene canvas + semantic HUD markup (T-FE.3)
4. Keyboard operability of `GroupTree` (T-FE.7)
5. Contrast verification pass on `--ink-dim` and citation chip text, both themes (T-FE.4, before calling Landing "done")
