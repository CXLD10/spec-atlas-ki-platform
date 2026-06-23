# EXECUTION PROMPT — Phase 1: Wire real backend to UI

Repo: `CXLD10/spec-atlas-ki-platform`. **Phase 0 must be done (real DB, one client, honest confidence/provenance).** Goal: every primary page renders backend-only data; build the missing aggregation APIs; switch `/graph` to real THREE.js; make Specify perform real generate/save/verify.

## Rules
- No `MockFallback` in any production page. Provenance stays mandatory.
- Offline test contract holds. Commit only at the stop point.

## Do these, in order

**1. `GET /api/sources` + `/api/sources/:id` (Dev B).** Aggregate `repos` + ingested documents into the `Source` shape the UI expects. Point `Dashboard.tsx`, `Sources.tsx`, `SourceDetail.tsx` (`useSources()`) at it. Remove the fudged `domains: Math.ceil(len*0.3) // Mock` in `Dashboard.tsx:16`; compute real counts.

**2. `GET /api/kb` + `/api/kb/:ref` (Dev B).** `/api/kb` lists `specs` as card summaries; `/api/kb/:ref` returns a single card. Wire `KnowledgeBase.tsx` + `KnowledgeCard.tsx` (`useCards()`); drop `MOCK_CARDS`.

**3. Layered subgraph + THREE.js (Dev B + Dev A).** Backend: new endpoint returning nodes tagged L1/L3/L4 + edges + layout hints (distinct from `GET /api/graph/subgraph`, which needs `node_id` and returns `NodeDetail`). Frontend: point `/graph` (`pages/Graph.tsx`) at `scene/GraphScene.tsx` + `useGraphBuild.ts` (THREE.js, raycasting) instead of the 2D `IsoGraph` fed by `MOCK_SUBGRAPH`. Keep `Inspector` + "Ask about this".

**4. Wire Specify (Dev A + Dev B).** Replace the 5-stage `setTimeout` animation with progress from a real call to `POST /api/specs/generate/{component_ref}?repo=…` (generate-on-demand; returns cached or v1). Render real provenance. **Save** → real spec mutation (remove `alert('demo stub')`). **Verify** → `POST /api/specs/{ref}/verify` (remove local-state flip).

**5. Verification dashboard (Dev A + Dev B).** New page/section consuming `GET /api/reports/{verification,issues,confidence}`. Show spec status, confidence distribution, open issues.

## Seed
Reuse the Phase 0 repo; ensure ≥1 group (L4), ≥1 spec edge (L3), ≥1 verifiable spec. If sparse, index a slightly larger repo.

## Must pass before commit
```bash
pytest -q tests/api/test_sources.py tests/api/test_kb.py
pytest -q tests/api/test_graph.py tests/api/test_specs.py tests/api/test_reports.py
pytest -q
cd frontend && npm run build && npm run test
```
Add: `test_sources_aggregates_repos_and_docs`, `test_kb_lists_and_fetches_specs`, `test_layered_subgraph_tags_l1_l3_l4`, `test_specs_generate_on_demand_returns_provenance`, `test_verify_mutates_spec_db`.

## Frontend checks (manual)
1. Dashboard numbers == DB counts; no `// Mock` math.
2. Sources/SourceDetail list the seeded repo; detail is real.
3. KnowledgeBase lists real specs; KnowledgeCard shows real provenance.
4. `/graph` renders in THREE.js, L1/L3/L4 toggles real, raycast selects real node, Inspector real, "Ask about this" navigates.
5. Specify: real component → live generate → real card+provenance → Save persists (re-fetch) → Verify flips status via API (re-fetch).
6. Verification dashboard shows real numbers.
7. Zero `MockFallback` anywhere.

## STOP & COMMIT
```
feat(phase1): wire Sources/KB/Graph(THREE.js)/Specify/Reports to real backend
```
Report changed files, test output, and screenshots/notes confirming each surface is backend-only. Do not start Phase 2.
