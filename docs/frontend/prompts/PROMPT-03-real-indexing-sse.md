# PROMPT-03 — Phase 6c: Real Indexing Flow

**Phase:** 6c — Real indexing flow  
**Tasks:** T-009.6 (backend) + T-FE.9–10 (frontend)  
**Duration estimate:** 3–4 days  
**Dependencies:** T-FE.8 (6b complete), backend live

## Context

Phase 6a built visuals. Phase 6b wired to real data. Phase 6c makes the signature build animation **the real progress UI** — not a separate progress bar bolted next to a visual demo.

This phase requires one small backend task first (T-009.6): an SSE endpoint that streams indexing progress. The frontend then consumes that stream and drives the GraphScene animation with real events.

**Interim state is acceptable:** Phase 6a/6b can ship with polling (`/api/ingest/{job_id}/status`) instead of waiting for SSE. This phase adds SSE, but polling is the fallback if needed.

## Read order (before starting)

1. `docs/frontend/architecture/API-CONTRACT.md` § "NOT YET LIVE" — the planned SSE endpoint shape
2. `docs/frontend/ui-ux/COMPONENTS.md` § `useGraphBuild` — the hook spec
3. This prompt file — execution order for T-009.6 + T-FE.9 + T-FE.10

## Execution order (Task breakdown)

### T-009.6 — Backend: Add SSE progress endpoint (BACKEND TASK)
**Involves:** Backend developer. This is small (~1–2 hours).

**What it does:**  
Creates `GET /api/ingest/{job_id}/events` — a Server-Sent Events endpoint that streams indexing progress in real-time.

**Endpoint spec:**  
- Path: `GET /api/ingest/{job_id}/events`
- Authentication: none (rate limiting still applies per F-017)
- Response: SSE stream (Content-Type: `text/event-stream`)
- Event format:
  ```
  event: stage
  data: {"stage": "l1", "status": "running", "progress": {"nodes_so_far": 142, "edges_so_far": 88}}
  
  event: stage
  data: {"stage": "l2", "status": "running", "progress": {"specs_generated": 17, "errors": 0}}
  
  event: stage
  data: {"stage": "l4", "status": "done", "progress": {"groups_formed": 5}}
  ```
- Stages: `l1`, `l2`, `l3`, `l4` (one event per stage transition + progress updates during)
- Each stage event includes progress details (what was just finished)

**Implementation notes:**
- Read the ingest job status from the Analysis DB (already DB-backed per F-017)
- For now, simulate stage transitions based on elapsed time or sampling the real ingest task state
- Don't block on implementing actual progress tracking in the ingest pipeline — emit synthetic events based on job status + elapsed time
- Return `404 Not Found` if job_id doesn't exist
- Stream until job status is `done` or `error`

**Acceptance:**
- Endpoint exists and is reachable
- Client can open EventSource and receive events
- Events match the schema (valid JSON in `data` field)
- Stream closes when job completes
- Staging: verify locally with `curl` and `node` EventSource client before handing to frontend

---

### T-FE.9 — extend useGraphBuild to live mode
Owns: `src/components/scene/useGraphBuild.ts` (extend existing hook)

**What this does:**  
The `useGraphBuild` hook currently only runs in `mode: 'timer'` (demo mode on Landing page). Add a `mode: 'live'` that consumes real SSE events.

**Hook signature (expand existing):**  
```ts
export function useGraphBuild(mode: 'timer' | 'live', jobId?: string) {
  // mode='timer' → existing demo logic (scripted phases)
  // mode='live' → consumes SSE events from /api/ingest/{jobId}/events
  return { phase, camTargetZ, nodes, edges, interactive };
}
```

**Live mode implementation:**  
- On mount, open `EventSource('/api/ingest/{jobId}/events')`
- On each `stage` event:
  - Parse `{stage, status, progress}`
  - Update internal `phase` (0=l1, 1=l2, 2=l3, 3=l4)
  - Increment `progress_pct` based on event content
  - Emit phase-complete callback if transitioning between stages
- On SSE stream close: set `status = 'done'` or `'error'`
- If SSE endpoint doesn't exist (Phase 6c not yet landed on backend): **gracefully fall back to polling mode**
  - Try to open SSE stream
  - On error (404, 500, etc.): fall back to polling `/api/ingest/{jobId}/status` every 1s
  - Synthesize fake stage events based on progress_pct (0→25%=l1, 25→50%=l2, 50→75%=l3, 75→100%=l4)
  - This lets Phase 6b ship without waiting for T-009.6

**Graceful degradation:**  
```ts
async function initLiveMode(jobId: string) {
  try {
    const eventSource = new EventSource(`/api/ingest/${jobId}/events`);
    // ... set up event listeners
  } catch (e) {
    // Fall back to polling
    console.log('SSE not available, using polling fallback');
    initPollingMode(jobId);
  }
}
```

**Acceptance:**  
- Hook accepts `mode: 'live'` and `jobId` parameter
- Live mode opens SSE stream to backend
- Phase updates occur as events arrive
- If SSE fails, polling fallback kicks in
- GraphScene animation driven by real events (not timer)
- Tests verify both SSE and polling paths

---

### T-FE.10 — IndexProgress page
Owns: `src/pages/IndexProgress.tsx`

**What this does:**  
User starts an ingest job, lands on a progress page, watches the real L1→L4 build animation (powered by real backend events or polling fallback), and gets automatically redirected to `/repo/:repoId/ask` when done.

**Layout:**  
- Top bar (marketing variant, no secondary nav)
- PipelineHUD (L1–L4 stage list, updates as phases complete)
- GraphScene (mounted in `mode: 'live'`, `jobId={repoId}`)
- Status text: "Indexing github.com/org/repo" + progress % (if polling) or live event data
- On completion: auto-redirect to `/repo/:repoId/ask`
- On error: show error message, "Try a different repo" action

**Route:**  
- Path: `/index/:jobId`
- `jobId` comes from ingest response (`POST /api/ingest` returns `{job_id}`)

**Flow:**  
1. User submits repo URL on Landing page (future: separate Index page)
2. Frontend calls `POST /api/ingest` → gets `job_id`
3. Frontend redirects to `/index/{job_id}`
4. IndexProgress page mounts
5. `useGraphBuild(mode='live', jobId)` opens SSE stream (or polling)
6. GraphScene animates in real-time as stages complete
7. PipelineHUD shows which stage is active
8. Progress % displayed (if polling) or just "stage X/4" (if SSE)
9. When job status = `done`: redirect to `/repo/{repoId}/ask`
10. If job status = `error`: show error, "Try again" button

**Acceptance:**  
- IndexProgress page loads
- GraphScene animation driven by real backend progress
- PipelineHUD updates as phases complete
- Auto-redirects to Ask page on completion
- Error handling: shows error message if ingest fails
- Polling fallback works if SSE not available
- TypeScript compiles, no console errors

---

## Integration with earlier phases

**Landing page (T-FE.4):**  
Currently shows a scripted demo (timer-driven). After Phase 6c, add a real ingest flow:
- Repo input field on Landing (already exists)
- Submit button calls `POST /api/ingest`
- On success: redirect to `/index/{job_id}` → IndexProgress page
- "Watch a live index" link points to a demo repo (optional, can be added post-MVP)

This integration is **NOT part of T-FE.10** — it's a small follow-up (add ingest submission to Landing's input field). But it's the last step to complete the real end-to-end flow.

## Exit gate

The signature build animation is now the real progress UI:
1. User submits a real repo URL
2. IndexProgress page shows real progress with real backend events
3. L1→L4 stages complete as the backend processes them
4. On completion, user automatically lands on `/repo/:repoId/ask`
5. User can ask questions about the indexed repo

That's the full end-to-end flow: real index, real progress UI, real questions, real answers. Everything wired.

## Notes

- SSE stream must respect rate limiting (same limits as other endpoints per F-017)
- Progress % is advisory (not canonical) — the stage events are the source of truth
- If backend sends invalid JSON in SSE data: log warning, skip event, continue streaming
- Keep polling fallback logic in place even after SSE is live (defensive against backend issues)
- Auto-redirect on completion must be instant (no delay) unless there's a specific UX reason for a "Success!" screen
