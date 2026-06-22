# PROMPT-02 — Phase 6b: Wire to Real Backend

**Phase:** 6b — Wire to real backend  
**Tasks:** T-FE.5–8  
**Duration estimate:** ~1 week  
**Dependencies:** T-FE.4 (Landing page done), backend endpoints confirmed live (✅ confirmed in F-017)

## Context

Phase 6a built the visual shell. Phase 6b wires it to real data.

**Key reminder:** The backend is confirmed live. Every endpoint listed in `docs/frontend/architecture/API-CONTRACT.md` exists, is tested, and returns real data. CORS is configured. You're not blocked — this is a straightforward plumbing phase.

## Read order (before writing code)

1. `docs/frontend/architecture/API-CONTRACT.md` — full endpoint list, shapes, rate limits
2. `docs/frontend/architecture/STATE-MANAGEMENT.md` — React Query patterns
3. `docs/frontend/ui-ux/USER-FLOWS.md` — user journeys through Ask, Explore, Spec Detail
4. `docs/frontend/ui-ux/WIREFRAMES.md` — layout details for all pages except Landing
5. `docs/frontend/ui-ux/COMPONENTS.md` — detailed component prop specs (especially `GroupTree`, `SpecDetail`)
6. `docs/frontend/ui-ux/ACCESSIBILITY.md` — keyboard support required in this phase, not 6d

## Execution order (Task breakdown)

### T-FE.5 — API client + React Query hooks
Owns: `src/api/client.ts`, `src/api/useAsk.ts`, `src/api/useGroups.ts`, `src/api/useSpec.ts`, `src/api/useIndexJob.ts`

**What this does:**  
Typed fetch wrapper + React Query hooks. Everything the frontend needs to talk to the backend.

**client.ts:**  
- Fetch wrapper with base URL from `VITE_API_URL` env var (defaults to `http://localhost:8000` in dev)
- Typed methods: `ask(question, repo)`, `getGroups()`, `getGroup(id)`, `getSpec(ref)`, `postIngest(repoUrl)`, `getIngestStatus(jobId)`, `health()`
- Error handling: parse backend error messages, throw typed errors
- CORS check: if you see CORS errors in-browser (but curl works), verify your dev origin is in backend's `allowed_origins`

**useAsk hook:**  
```ts
export function useAsk(question: string, repo: string) {
  return useQuery({
    queryKey: ['ask', repo, question],
    queryFn: () => client.ask({ question, repo }),
    enabled: !!question,
  });
}
```
- Cache prevents re-fetching if user navigates back
- Rate limit: 20/min per IP (backend enforces 429; show friendly "rate limited, try again in X seconds")

**useGroups hook:**  
- `useQuery(['groups'], () => client.getGroups())` for root tree
- `useQuery(['group', id], () => client.getGroup(id))` for detail view

**useSpec hook:**  
- `useQuery(['spec', ref], () => client.getSpec(ref))` for full spec detail

**useIndexJob hook:**  
- `useQuery(['ingest', jobId], ...)` with `refetchInterval: 1000` (poll every second)
- Disables polling when status is `done` or `error`

**Acceptance:**  
- All hooks typed, no `any` types
- Queries memoize results (no duplicate requests for same input)
- Error states handled (show error message, not crash)
- Rate limit 429 response shows retry-after message
- TypeScript compiles, no console errors

### T-FE.6 — RepoAsk page (ask question, see real answer)
Owns: `src/pages/RepoAsk.tsx`

**What this does:**  
User asks a real question about a real indexed repo, gets a real cited answer.

**Layout:**  
- Top bar (TopBar component, workspace variant)
- Question input field (text, submit button)
- Answer dock (mounted once answer arrives)
  - Question repeated
  - Answer text with inline CitationChip components
  - Confidence bar
- If no question yet: show placeholder "Ask a question about this repository..."
- If loading: show spinner or skeleton
- If error: show error message (friendly, no stack trace)

**Flow:**  
1. User types question, hits enter
2. `useAsk(question, repo)` fires (React Query handles caching)
3. While loading: show spinner in AnswerDock
4. When data arrives: render answer with CitationChip components interspersed
5. If CORS fails: show "Backend unavailable" (dev-friendly debug hint)
6. If rate limit (429): show "Too many requests, try again in X seconds"

**Key decision point — typewriter effect:**  
The prototype types out demo answers character by character (16ms/char). For **real** answers from the backend, consider whether this serves the user experience:
- Pro: maintains the prototype's visual identity
- Con: makes the user wait for information they asked for
  
**Make a judgment call here.** Decide: does the typewriter effect add value for real answers, or does immediate rendering (with optional fade-in animation) feel snappier? Document your decision in the HANDOFF notes (it's a non-obvious choice).

**Acceptance:**  
- Real questions return real answers from the backend
- Answer renders with CitationChip components inline (chips are clickable, not plain text)
- Confidence bar visible and accurate
- Error states (no backend, rate limit, etc.) show friendly messages
- Loading state (spinner or skeleton) while answer loads
- Keyboard accessible: question input focusable + operable, submit button works via enter + click

### T-FE.7 — RepoExplore page + GroupTree (browse knowledge tree)
Owns: `src/components/explore/GroupTree.tsx`, `src/components/explore/GroupDetail.tsx`, `src/pages/RepoExplore.tsx`

**What this does:**  
User browses the L4 group tree, drills into groups to see group summaries + member specs.

**Layout:**  
- Left sidebar: GroupTree (collapsible hierarchy)
- Right panel: GroupDetail (selected group's summary + member specs)
- Top bar (workspace variant, shows Ask/Explore secondary nav)

**GroupTree.tsx:**  
- Recursive component: root groups → children → children
- Collapsible/expandable (▾/▸ chevron)
- Single-select (click = select, render as active)
- **Keyboard operability (hard requirement, not 6d):**
  - Arrow up/down: navigate between siblings
  - Arrow right: expand; arrow left: collapse
  - Enter/Space: select
  - See `ACCESSIBILITY.md` for full spec
- No external tree library required (if you use one, verify keyboard support is built-in)

**GroupDetail.tsx:**  
- Renders group.md content via `react-markdown` (add to `package.json`)
- Lists member specs with status badges:
  - Draft: neutral color + text "draft"
  - Verified: `--l2` teal + "verified"
  - Stale: `--l3` amber + "stale"
- Status badges must include both color AND text (not color-only per `ACCESSIBILITY.md`)
- Clicking a spec navigates to `/repo/:repoId/explore/specs/:ref`

**RepoExplore.tsx:**  
- `useGroups()` hook gets root tree on mount
- Click a group in tree → calls `useGroup(id)` for detail
- Shows loading state while detail loads
- Handles errors (no group found, network error, etc.)

**Acceptance:**  
- Group tree renders with correct hierarchy
- Tree is keyboard-navigable (arrow keys + enter)
- Clicking a group loads and displays its detail
- Status badges show both color + text
- Member specs list is present and linked
- No console errors, TypeScript compiles
- GroupTree tested with real backend data (use `/api/groups` output, not mock data)

### T-FE.8 — RepoSpec page (view full spec detail)
Owns: `src/components/explore/SpecDetail.tsx`, `src/pages/RepoSpec.tsx`

**What this does:**  
User views a full structured spec: purpose, inputs, outputs, dependencies, invariants, side effects, failure modes — each field with working citations.

**Layout:**  
- Top bar (workspace variant)
- Breadcrumb: Group → Spec ref (clickable, links back to group)
- Status badge (draft/verified/stale)
- All structured fields (see `WIREFRAMES.md` Spec Detail section)
- Every field with provenance → CitationChip component

**SpecDetail.tsx:**  
- Takes `spec` object from `useSpec(ref)`
- Renders each field:
  - PURPOSE: text + citation chip
  - INPUTS: bullet list, each with citation
  - OUTPUTS: bullet list, each with citation
  - DEPENDENCIES: other specs (links), with citation
  - INVARIANTS: text + citation
  - SIDE EFFECTS: text + citation
  - FAILURE MODES: text + citation
- Status badge (top-right): reuses `--l2` (verified) / `--l3` (stale) / neutral (draft)

**RepoSpec.tsx:**  
- Route: `/repo/:repoId/explore/specs/:ref`
- Calls `useSpec(ref)` to load spec
- Shows loading state, error state
- Renders SpecDetail when loaded

**Acceptance:**  
- Full spec renders with all fields
- Every field with provenance shows CitationChip (not plain text)
- CitationChips are keyboard-operable and have visible focus state
- Status badge is accurate (color + text)
- Breadcrumb navigation works (back to group detail)
- No console errors, TypeScript compiles

## Exit gate

Real workflow end-to-end:
1. User lands on RepoAsk page
2. User types a real question
3. Backend returns a real answer with real citations
4. User clicks a citation chip → navigates to that spec (or opens code snippet panel — implementation detail, design review will clarify)
5. User navigates back to Explore
6. User browses the group tree
7. User clicks a group → sees real summary + member specs
8. User clicks a spec → sees full spec detail
9. All of this works with real backend data (not mocks)
10. All pages keyboard-accessible

## Notes

- Every page uses TopBar with workspace variant (not marketing variant)
- Secondary nav (Ask / Explore) shown in top bar, can switch between pages
- RepoId is a URL param (captured from ingest redirect in future 6c phase)
- Status badges use `--l2` and `--l3` colors (layer color rules still apply)
- CitationChip is used consistently everywhere — no plain text citations
- No ambient idle motion on these pages (per design principles)
