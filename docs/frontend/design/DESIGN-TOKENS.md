# Design Tokens

**Source:** extracted directly from `02-design/prototype/spec-atlas-hero.html` (grep-verified, not transcribed from memory). If this doc and the prototype ever disagree, re-extract from the prototype — it's the single source of truth.

## Color — Dark mode (primary/default)

```css
--bg: #04070d;
--bg-grid: rgba(46, 200, 255, 0.045);        /* the faint background grid lines */
--panel: rgba(10, 18, 30, 0.72);             /* glass panel fill — pair with backdrop-blur(12-16px) */
--panel-border: rgba(60, 200, 255, 0.18);
--ink: #dff3ff;                               /* primary text */
--ink-dim: #6b8299;                           /* secondary text */
--ink-faint: #3d5163;                         /* placeholders, disabled, tertiary */
--cyan: #2ec8ff;                              /* primary accent — buttons, links, focus */
--cyan-bright: #6fe0ff;                       /* hover/active state of the above */
--cyan-glow: rgba(46, 200, 255, 0.55);         /* box-shadow glow color, used sparingly */
```

## Color — Light mode

```css
--bg: #eef3f7;
--bg-grid: rgba(20, 90, 130, 0.06);
--panel: rgba(255, 255, 255, 0.82);
--panel-border: rgba(20, 110, 150, 0.18);
--ink: #0b2233;
--ink-dim: #5a7286;
--ink-faint: #9fb3c2;
--cyan: #0a93cc;
--cyan-bright: #0875a3;
--cyan-glow: rgba(10, 147, 204, 0.3);
```

## Color — Layer accents (reserved use only — see Design Principles)

| Token | Dark value | Light value | Reserved for |
|---|---|---|---|
| `--l1` | `#2ec8ff` | `#0a93cc` | Code Graph layer — HUD stage 1, citation chips sourced from raw code, graph nodes at depth 0 |
| `--l2` | `#36e0c8` | `#0b9d86` | Specs layer — HUD stage 2; also the "verified" spec status badge |
| `--l3` | `#ffc24d` | `#c8860a` | Spec Graph layer — HUD stage 3; also the "stale" spec status badge; also the citation-chip default color in the Q&A dock |
| `--l4` | `#b794ff` | `#7a52cc` | Group Tree layer — HUD stage 4 |

**Rule (unchanged from earlier design pass, restated for emphasis since it's easy to violate by accident):** these four never appear in general UI chrome (buttons, links, nav, primary borders). They exist only to let a user visually correlate "which knowledge layer is this information from" across the HUD, citation chips, and graph nodes. If you catch yourself reaching for `--l4` to make a random button look nice, stop — that's the violation this rule exists to prevent.

## Typography

```css
--font-display: 'Space Grotesk', system-ui, sans-serif;   /* headings, buttons, nav, brand */
--font-mono: 'JetBrains Mono', ui-monospace, monospace;     /* citations, HUD labels, code, repo-input field */
```

Type scale (from the prototype's actual `clamp()` usage):
| Use | Size |
|---|---|
| Hero H1 | `clamp(38px, 8vw, 86px)`, weight 700, letter-spacing `-0.02em`, line-height `1.02` |
| Lede paragraph | `clamp(15px, 2.2vw, 19px)`, line-height `1.6` |
| Intro title | `clamp(28px, 6vw, 56px)`, weight 700 |
| Eyebrow / nav / HUD labels | `11–12px` mono, letter-spacing `0.08em`–`0.22em`, uppercase |

## Motion — exact timings (grounded in source, do not invent new values)

| Sequence | Duration | Easing | Source line |
|---|---|---|---|
| Intro particle convergence | ~1300ms (particles), full sequence cuts to hero at **1700ms** | per-particle ease: `1 - (1-prog)^4` (fast-then-settle) | confirmed in script: `t < 1300`, final cut at `1700` |
| Intro element snap-in (mark/title/sub) | staggered at 680ms / 780ms / 860ms after start | `cubic-bezier(.2,.85,.25,1.25)` (slight overshoot) | `snapIn` keyframe |
| Intro → hero cut transition | 400ms | `cubic-bezier(.4,0,.2,1)` + `filter: blur(8px)` | `.intro.gone` |
| Theme toggle thumb slide | 350ms | `cubic-bezier(.6,.2,.1,1)` | `.theme-toggle::after` |
| Per-layer build phase (L1→L2→L3→L4) | **1700ms each** (`PHASE_DUR`) | camera eases via `camZ += (camTargetZ - camZ) * 0.05` per frame (exponential approach, not a fixed-duration tween) | `PHASE_DUR = 1700` |
| Q&A answer start delay after build completes | 600ms | — | `setTimeout(runQA, 600)` |
| Typewriter character reveal | 16ms/char (fast), 60ms pause between answer segments, 420ms hold after a citation chip appears | — | `runQA` step function |
| Citation "fly to node" camera nudge hold | 700ms before returning to resting depth | — | `flyToCitation` |
| Scene auto-settle (fade to calm) | triggered 6000ms after the answer finishes typing, then fades at `0.018`/frame (~55 frames ≈ 0.9s at 60fps) | — | `fading = true` trigger + fade decrement |

**Why this level of precision matters:** these numbers were tuned through two rounds of explicit user feedback (original intro was "too slow," ambient motion was "disliked"). Re-deriving new timings from scratch in the React port risks reintroducing exactly the problems that were just fixed. Port these values directly.

## Spacing & layout

No formal spacing scale was defined in the prototype (it uses ad-hoc `px`/`vw` values throughout, appropriate for a single hero page). **For the React app's additional pages** (Explore, Spec detail, etc.), adopt a standard 4px-base scale (`4, 8, 12, 16, 24, 32, 48, 64`) via Tailwind's default spacing — there's no design reason to deviate from Tailwind defaults here, unlike color/type which have a strong specific identity already established.

## Glass panel recipe (reusable)

```css
background: var(--panel);
border: 1px solid var(--panel-border);
border-radius: 12–14px;
backdrop-filter: blur(12–16px);
box-shadow: 0 20-30px 60-80px -20-30px rgba(0,0,0,0.6-0.7);
```
Used for: the launch input, HUD stage cards, the Q&A dock, the replay button. This is the app's one consistent "surface" material — don't introduce a second panel style (e.g., flat opaque cards) elsewhere in the app.
