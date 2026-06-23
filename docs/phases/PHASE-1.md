# Phase 1 — Connect the existing real backend to the UI

**Effort:** L · **Depends on:** Phase 0 · **Audit items:** §2, §3.15, §3.16, §3.17, §3.18, §3.19(partial)

## Objective
Every primary page renders **only backend data**. The real-but-unconsumed APIs (`graph`, `specs`, `reports`, `groups`) get UI consumers; the missing aggregation APIs (`sources`, `kb`) get built. The shipped `/graph` switches to the real THREE.js renderer. Specify performs real generate/save/verify.

---

## Tasks

### 1.1 — `GET /api/sources` + `/api/sources/:id` *(Dev B, M)* — §3.15
- New endpoint aggregating `repos` + ingested documents into the `Source` shape the UI expects.
- Dashboard stats computed from **real** counts — remove the `domains: Math.ceil(len*0.3) // Mock` fudge (`Dashboard.tsx:16`).
- Point `Dashboard.tsx`, `Sources.tsx`, `SourceDetail.tsx` (`useSources()` → `client.listSources()`) at it.

### 1.2 — `GET /api/kb` + `/api/kb/:ref` *(Dev B, M)* — §3.16
- `GET /api/kb` lists `specs` mapped to card summaries; `GET /api/kb/:ref` returns a single spec/card view (data already in Spec DB).
- Wire `KnowledgeBase.tsx`, `KnowledgeCard.tsx` (`useCards()`); drop `MOCK_CARDS`.

### 1.3 — Layered subgraph endpoint + THREE.js graph *(Dev B + Dev A, L)* — §3.17
- **Backend:** new endpoint returning nodes tagged **L1/L3/L4** with edges and layout hints (or layout client-side). Distinct from the existing `GET /api/graph/subgraph` which requires `node_id` and returns `NodeDetail`.
- **Frontend:** point `/graph` (`pages/Graph.tsx`) at the real `scene/GraphScene.tsx` + `useGraphBuild.ts` (THREE.js, raycasting) instead of the 2D `IsoGraph` fed by `MOCK_SUBGRAPH`. Keep `Inspector` for selection.
- Preserve "Ask about this" navigation from a selected node.

### 1.4 — Wire Specify for real *(Dev A + Dev B, M)* — §3.18
- Replace the 5-stage `setTimeout` animation with progress from a **real** generate call.
- Call `POST /api/specs/generate/{component_ref}?repo=…` (generate-on-demand, already implemented, returns cached or v1) — **not** the incompatible `POST /api/specs` body that 422s.
- Render real provenance from the response.
- **Save** → real spec mutation (not `alert('demo stub')`). **Verify** → `POST /api/specs/{ref}/verify` (not local state flip).

### 1.5 — Verification dashboard *(Dev A + Dev B, S–M)* — §2
- New page/section consuming `GET /api/reports/{verification,issues,confidence}` (real analytics, currently consumed by nothing).
- Charts/tables of spec status, confidence distribution, open issues.

---

## Seed / fixtures
Reuse the Phase 0 seeded repo. Ensure it produced ≥1 group (L4), ≥1 spec graph edge (L3), and ≥1 verifiable spec so every page has non-trivial content. If sparse, index a slightly larger repo.

## Backend tests
```bash
pytest -q tests/api/test_sources.py      # new
pytest -q tests/api/test_kb.py           # new
pytest -q tests/api/test_graph.py        # layered subgraph shape
pytest -q tests/api/test_specs.py        # generate-on-demand + verify
pytest -q tests/api/test_reports.py
pytest -q
```
New tests:
- `test_sources_aggregates_repos_and_docs` — shape + real counts; no fudged domains.
- `test_kb_lists_and_fetches_specs` — `/api/kb` ↔ `specs`.
- `test_layered_subgraph_tags_l1_l3_l4` — every node carries a layer tag + edges resolve.
- `test_specs_generate_on_demand_returns_provenance` — real spans.
- `test_verify_mutates_spec_db` — verify changes persisted state.

## Frontend integration checks
1. **Dashboard** numbers equal DB counts (cross-check via API); no `// Mock` math.
2. **Sources / SourceDetail** list the seeded repo + any docs; clicking opens real detail.
3. **KnowledgeBase** lists real specs; **KnowledgeCard** opens a real card with provenance.
4. **/graph** renders in **THREE.js** (`GraphScene`), L1/L3/L4 toggles populated by real data, raycast click selects a real node, Inspector shows real fields, "Ask about this" navigates.
5. **Specify**: enter a real component → live generate → real card + provenance → **Save** persists (re-fetch shows it) → **Verify** flips status via API (re-fetch confirms).
6. **Verification dashboard** shows real report numbers.
7. Across all pages: **zero** `MockFallback` in the network/console.

## Definition of Done
- All six primary surfaces render backend-only data.
- `/graph` is THREE.js with raycasting over real layered data.
- Specify Save/Verify mutate the Spec DB and survive refresh.
- New endpoints covered by tests; full suite green.

## Commit checkpoint
```
feat(phase1): wire Sources/KB/Graph(THREE.js)/Specify/Reports to real backend
```
