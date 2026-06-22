# Prompt 04 — Phase 6d: Polish Pass

**Do not run this prompt until the project owner has personally used the real, wired-up app from Phases 6a–6c for a while.** This phase is deliberately under-specified because it depends on hands-on feedback that doesn't exist yet.

---

## Before running this prompt

The project owner should answer, from real usage (not speculation):

1. Does the Ask page need a persistent graph visualization, or does it work better graph-free with citations opening a code-snippet panel directly? (Open question flagged in `03-ui-ux/USER-FLOWS.md` Flow 3.)
2. Does the typewriter effect on real (non-demo) answers feel right, or should answers render immediately? (Flagged in `04-specs/COMPONENTS.md` and `06-prompts/PROMPT-02-wire-real-backend.md` — a decision should have already been made and implemented in 6b; revisit if it doesn't feel right in practice.)
3. Are there empty/error states that came up in real use that weren't anticipated in `03-ui-ux/USER-FLOWS.md`?
4. Any visual rough edges on mobile beyond what the Landing page's existing media queries handle?
5. Anything in the citation → code-snippet flow that felt clunky (remember `/api/code-snippet` is still a stub returning empty content — does this matter more in practice than expected)?

## Known tasks (regardless of the above answers)

These are real, scoped requirements independent of design-review findings — include them regardless:

### T-FE.11 — Empty & error states
Audit every page for empty states (no groups yet, no specs yet, no answer yet) and error states (failed ingest, failed ask, 429 rate limits, network failure). Every message follows the voice guidance in `02-design/DESIGN-PRINCIPLES.md` — system voice, never apologetic, always says what happened and what to do next.

### T-FE.12 — Mobile pass beyond Landing
The Landing page already has mobile handling (ported from the prototype). Explore and Spec Detail need real mobile layouts — per `03-ui-ux/WIREFRAMES.md`'s layout notes, `GroupTree` should collapse into a drawer/dropdown on mobile rather than a persistent sidebar.

### T-FE.13 — Full accessibility pass
Work through every item in `03-ui-ux/ACCESSIBILITY.md`'s "Summary of concrete build tasks" checklist and confirm each one — by this phase they should mostly already be done (they were embedded into 6a/6b/6c tasks deliberately, not deferred), so this is a verification pass, not new implementation. Flag any that were missed.

### T-FE.14 — Whatever the design review surfaces
Per the project's playbook ("found extra work → new ready task, never expand the current one"), write this task's actual scope only after the review happens. Do not let an agent guess at this task's content before that review exists.

## Exit gate

The product feels finished, not just functional — empty states invite action, errors are calm and clear, mobile works across all pages, and a full accessibility pass confirms nothing from the spec was silently skipped under deadline pressure during 6a–6c.
