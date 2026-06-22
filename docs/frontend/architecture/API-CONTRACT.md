# API Contract — Confirmed Live Endpoints

**Source of truth:** `PROJECT-STATE-REPORT.md` §3 (endpoint table, verified wired in `app.py`) + F-017 HANDOFF (CORS/rate-limiting/security fixes applied on top of these same endpoints). Every endpoint below is **confirmed wired and tested** as of the F-017 handoff — this is not a proposed contract, it's what actually exists.

**Base URL:** configurable via `VITE_API_URL` env var in the frontend build. Local dev: `http://localhost:8000`.

**CORS:** locked to the frontend's origin (set via backend's `allowed_origins` config) — confirm your local dev origin (`http://localhost:5173` for Vite default) is in that allowlist before wiring `useAsk`/etc., or every call will fail with a CORS error in-browser even though `curl` works fine.

---

## Ask

### `POST /api/ask`
**Rate limit:** 20/min per IP (per F-017 spec — verify this is actually active, see deck README warning)

Request:
```json
{ "question": "How does authentication work?", "repo": "my-repo" }
```

Response:
```json
{
  "answer": "Authentication is handled in the auth/tokens module...",
  "claims": [
    { "text": "...validates credentials...", "file": "auth/session.py", "start_line": 88, "end_line": 92, "confidence": 1.0 }
  ],
  "confidence": 0.92,
  "route_used": "vector_search"
}
```

**Frontend mapping:** `claims[]` → render as `CitationChip` components inline in the answer text (the backend returns structured claims, not inline markup — the frontend is responsible for interleaving chip components with the answer text at the right positions, matching the pattern in `02-design/prototype/spec-atlas-hero.html`'s `answerParts` array, but driven by real data instead of a scripted array).

---

## Groups (L4 tree)

### `GET /api/groups`
Returns the root group tree (recursive children included).

### `GET /api/groups/{id}`
Single group detail: summary markdown, children, member specs.

```json
{
  "id": "auth",
  "path": "auth",
  "summary_md": "## Auth\nHandles user authentication...",
  "children": [{ "id": "auth/tokens", "path": "auth/tokens" }],
  "member_specs": ["auth/tokens.TokenManager", "auth/session.Session"]
}
```

**Frontend mapping:** `GroupTree.tsx` renders the hierarchy from `/api/groups`; clicking a node fetches `/api/groups/{id}` for `GroupDetail.tsx`, and renders `summary_md` through a markdown renderer (add `react-markdown` — small, no new architectural decision needed).

---

## Specs (L2)

### `GET /api/specs/{ref}`
Full spec, current version, with `status` field (`draft` / `verified` / `stale`).

### `GET /api/specs/{ref}/versions`
Version history.

### `POST /api/specs`
Create a new spec (used by the ingest pipeline, not typically called directly from the frontend in v1 — the frontend reads specs, it doesn't generate them on demand from the UI).

**Frontend mapping:** `SpecDetail.tsx` renders the structured fields (purpose/inputs/outputs/dependencies/invariants/side_effects/failure_modes); every field with provenance renders as a `CitationChip`. The `status` field drives a small badge (draft = neutral, verified = `--l2` teal-green accent, stale = `--l3` amber accent — reuse the layer-color system since it's already the app's established "state of trust" color language).

---

## Ingest

### `POST /api/ingest`
**Rate limit:** 5/hr per IP. **Validated** (per F-017) against URL scheme + host allowlist (`https://` + `github.com`/`gitlab.com` only) and path traversal protections.

Request:
```json
{ "repo_url": "https://github.com/org/repo" }
```

Response:
```json
{ "job_id": "abc123" }
```

### `GET /api/ingest/{job_id}/status`
Poll-based progress. **DB-backed per F-017.3** — survives a backend restart.

```json
{ "status": "running", "progress_pct": 42, "error_message": null }
```

**Frontend mapping:** `T-FE.3`'s `POST /api/ingest` call → redirect to `/index/{job_id}` → `IndexProgress.tsx` polls this endpoint (or, once Phase 6c's SSE endpoint lands, subscribes to the stream instead — see below).

### `GET /api/code-snippet`
**⚠️ Known stub** — per the state report, this currently returns empty content. The frontend should handle this gracefully: render the citation chip and file:line reference regardless (that data is real), but show a "source preview unavailable" placeholder instead of a blank code block when this endpoint returns nothing. Don't build a broken-looking empty `<pre>` block.

---

## Health

### `GET /health`
```json
{ "status": "ok", "analysis_db": "ok", "spec_db": "ok", "llm": "ok", "embed": "ok" }
```
Not consumed by end-user UI, but useful for a `/settings` "system status" panel if you want one (optional, not in the locked v1 scope).

---

## NOT YET LIVE — needed for Phase 6c only

### `GET /api/ingest/{job_id}/events` (Server-Sent Events)
**Status:** does not exist yet. This is `T-009.6`, a small backend task slotted into Phase 6c (see `06-prompts/PROMPT-03-real-indexing-sse.md`). Don't build frontend code against this until that backend task lands — Phase 6a/6b work entirely without it (uses the polling `/status` endpoint or the timer-driven demo mode instead).

Planned shape:
```
event: stage
data: {"stage": "l1", "status": "running", "progress": {"nodes_so_far": 142, "edges_so_far": 88}}
```

---

## Graph (L1) — exists, not needed for v1 frontend scope

`/graph/nodes/{id}`, `/graph/nodes/{id}/neighbors`, `/graph/subgraph`, `/graph/search`, `/graph/reachable` are all live and tested per the state report, but **nothing in the locked F-009 frontend scope calls these directly** — the `/api/ask` endpoint's router already decides when to use the graph path internally. Don't build a "raw graph explorer" UI against these unless that becomes an explicit, separately-scoped request — it's not in the current information architecture.
