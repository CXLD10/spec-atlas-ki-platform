# Spec-Atlas — De-Mock Remediation Master Plan

**Goal:** Replace every mock/stub/fake-fallback with real, DB-backed, end-to-end working code. Every page renders only backend data. No `MockFallback` in production paths. CI stays green and fully offline using `fake`/`fastembed` providers (the zero-cost contract).

**Source of truth:** This plan is derived from `SYSTEM_STATUS_AND_REMEDIATION.md` (file-cited audit) and verified against the live repo `CXLD10/spec-atlas-ki-platform`. Where the audit and code disagreed, code was re-checked — all audited claims held.

---

## Operating principles

1. **Code wins over docs.** If a spec contradicts code, fix the code path and note it in the commit.
2. **Provenance is mandatory.** No spec field, answer claim, or card without a `{file, start_line, end_line}` (or page/cell/section) span. Never weaken this to make a path "work."
3. **Offline-first stays intact.** Default boot uses `fake` LLM + `fastembed`. Tests must pass with **no network, no credentials, no cost.** Real providers (Gemini/Groq/Ollama) remain opt-in behind the provider interface — never a vendor SDK.
4. **One client.** Collapse `lib/api.ts` (mock-fallback) and `api/client.ts` (throws) into a single typed client matching the backend contract. Mock data (`lib/mock.ts`) survives **only** in tests/storybook.
5. **Each phase ends green.** Backend suite passes; the named frontend integration checks pass; commit at the stop point.
6. **Honest results, not underwhelming.** "Real" must also be *good*: real confidence scores, real layered graph, real citations that resolve. A correct-but-empty screen is a failure of seeding, not of scope — every phase includes a seed/fixture step so the demo has real, non-trivial data.

---

## Phase map (ordered; each unblocks the next)

| Phase | Theme | Removes mocks | Effort | Depends on |
|-------|-------|---------------|--------|------------|
| **0** | Real happy path out of the box | DB 503→mock cascade, dual clients, groups repo-id, fake confidence, dead provenance | M | — |
| **1** | Wire real backend to UI | Dashboard/Sources, KnowledgeBase/Card, Graph (THREE.js), Specify, Reports dashboard | L | 0 |
| **2** | Real document ingestion | `POST /api/documents`, SourceUnit persistence, doc citations, persistent docs store | L | 0,1 |
| **3** | Real external sources | git history, Jira, Deep Wiki fallback | M | 2 |
| **4** | Agents & real-time | MCP handlers rewrite, MCP entrypoint+package, SSE streaming Ask | M | 0–3 |
| **5** | Robustness & spec parity | Drift detection, eval harness, TS/JS tree-sitter, rate limiting | L | all |

Detailed phase docs: `phases/PHASE-0.md` … `phases/PHASE-5.md`.
Copy-paste execution prompts: `prompts/PROMPT-PHASE-0.md` … `prompts/PROMPT-PHASE-5.md`.

---

## How to run a phase

Each phase doc has the same shape:

- **Objective** — what "real" means for this phase.
- **Tasks** — numbered, each citing the file(s) and the audit item (§).
- **Seed/fixtures** — how to get real non-trivial data on screen.
- **Backend tests** — new/changed tests; commands to run.
- **Frontend integration checks** — explicit, observable pass criteria (what renders, what no longer falls back to mock).
- **Definition of Done** — the gate to the next phase.
- **Commit checkpoint** — exact commit message convention.

Each prompt file is a single self-contained brief you can hand to an executor (Dev A frontend / Dev B backend split noted inline). Run phases **in order**; do not start a phase until the prior phase's DoD is met.

---

## Global commands (run from repo root)

```bash
# Backend (offline, fake providers — the CI contract)
pytest -q                      # full suite, must stay green every phase
pytest -q tests/<area>         # focused

# Stand up real infra (Phase 0 onward)
docker compose up -d db        # Postgres + pgvector
alembic upgrade head           # migrations

# Frontend
cd frontend && npm ci && npm run build && npm run dev
npm run test                   # vitest (component/integration)
```

## Cross-phase "no-mock" tripwire (add in Phase 0, keep forever)

A test that fails CI if a production page path resolves to `MockFallback`. Backend equivalent: a smoke test that boots the app against a seeded DB and asserts every GET in the route table returns 200 with non-empty, schema-valid bodies. This is the mechanical guarantee behind "nothing faked."

---

## Definition of Done — whole program (from the audit, made checkable)

- [ ] `docker compose up` provisions Postgres+pgvector; **no endpoint silently falls back to mock**; `lib/mock.ts` referenced only by tests.
- [ ] Indexing a real repo populates L1/L3/L4; `/graph` renders it in **THREE.js** with raycast selection + inspector.
- [ ] Uploading PDF/Excel/Markdown yields searchable knowledge; answer citations resolve to real page/cell/section locators.
- [ ] Dashboard, Sources, KnowledgeBase, Specify, and the verification dashboard render **only** backend data; Specify Save/Verify mutate the Spec DB.
- [ ] Answer confidence reflects true vector distance; Deep Wiki, Jira, git-history return real data.
- [ ] MCP server runs from a published entrypoint with DB-backed handlers; all four tools return real results + tests.
- [ ] Drift marks stale specs on re-ingest; eval harness runs in CI; rate limiting active; TS/JS uses tree-sitter.
- [ ] CI green and fully offline with `fake`/`fastembed`.
