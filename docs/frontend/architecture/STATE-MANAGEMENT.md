# State Management

Three distinct kinds of state in this app — don't blur them into one system.

## 1. Server state → React Query

Anything that comes from the backend (answers, groups, specs, ingest job status) is React Query's job. It gives you caching, loading/error states, and refetch-on-window-focus for free, which matters here specifically because:
- Ingest job status needs polling (`useIndexJob.ts` — `useQuery` with `refetchInterval`, drop the interval once status is `done`/`failed`)
- An answer to a previously-asked question shouldn't re-trigger a 20/min-rate-limited call if the user navigates back to it — cache it

```ts
// api/useAsk.ts
export function useAsk(question: string, repo: string) {
  return useQuery({
    queryKey: ['ask', repo, question],
    queryFn: () => client.ask({ question, repo }),
    enabled: !!question,
  });
}
```

## 2. Scene state → local component state + a tiny event bus

The `GraphScene` canvas has its own internal animation state (node positions, phase, camera depth) that lives entirely inside the component via `useRef` (mutable, RAF-loop-friendly — does NOT belong in React state, would cause a re-render every frame).

Cross-component communication (a `CitationChip` in `AnswerDock` needs to tell `GraphScene` to fly to a node) goes through a minimal pub/sub, not React context or prop drilling:

```ts
// components/scene/sceneEvents.ts
type SceneEvent = { type: 'fly-to-node'; layer: number } | { type: 'reset' };
const listeners = new Set<(e: SceneEvent) => void>();
export const sceneEvents = {
  emit: (e: SceneEvent) => listeners.forEach(l => l(e)),
  subscribe: (fn: (e: SceneEvent) => void) => { listeners.add(fn); return () => listeners.delete(fn); },
};
```

This mirrors what the prototype already does informally (a function call from the citation chip's `onclick` directly nudging `camTargetZ`) — just formalized so it works across separate React components instead of one big script scope.

## 3. UI/local state → `useState`

Theme (persisted to `localStorage`, read on mount, no need for anything heavier), current route params, form input values, accordion open/closed state in `GroupTree`. Plain React state, nothing fancier needed.

## What this deliberately avoids

- **No global store (Redux/Zustand) for server data** — React Query already owns that; a global store would just be a second cache fighting the first.
- **No global store for scene state** — it's render-loop-critical (60fps target), doesn't belong in any system that triggers React re-renders per update.
- **No prop-drilling the active repo through every component** — use a route param (`/repo/:repoId/...`) as the source of truth, read via `useParams()` where needed, rather than threading it through context for what's fundamentally URL state.
