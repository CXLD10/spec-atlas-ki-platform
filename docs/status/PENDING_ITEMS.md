# PENDING_ITEMS.md — Spec-Atlas (2026-06-19)

Prioritized. Grouped by **Discrepancy** (fix first — they undermine the tracking system),
**Blocker**, then **Priority** work. Each traces to a spec path.

## 🔴 Discrepancies (resolve before any new task is claimed)

- [ ] **T-000.4/.5/.6 are marked `done`/`in-progress` on the BOARD but exist only as uncommitted working-tree changes** — `git log master..HEAD` is empty; `llm/`, `parse/`, `api/` are untracked. → reconcile git with `tasks/BOARD.md` lines 14–16. Either commit/merge the work or revert the BOARD edits; status currently lies relative to history.
- [ ] **BOARD/feature-file status edits are themselves uncommitted** — `git diff tasks/BOARD.md` and `specs/features/F-000-foundations.md` show the done/in-progress flips and the new HANDOFF notes are unsaved. → commit them with the code they describe.
- [ ] **T-000.5 (codex) and T-000.6 (codex) have no dedicated `task/T-NNN.M-*` branch** — both were built on `task/T-000.4-llm-provider`, mixing three tasks on one branch. → violates one-task-one-branch in `docs/PLAYBOOK.md` (Agent Operating Loop). Split or document.
- [ ] **T-000.4 HANDOFF authorship is ambiguous** — attributed to `claude` (F-000:159) but references a "takeover"; BOARD agent = claude. → confirm which agent owns it so attribution is accurate.
- [ ] **F-000 feature-file `Status: ready`** (F-000:3) never advanced though 6/7 tasks have code. → update to reflect active state once tracking is reconciled.

## 🟠 Blockers (external/environmental — block feature-level acceptance, not unit work)

- [ ] **No reachable Postgres** → `make migrate` and the DB roundtrip test (`tests/db/test_schema_roundtrip.py`) cannot be verified; two feature acceptance criteria (`make dev` both-DB ok; `make migrate` pgvector dim 384) remain unverified. Trace: `INTEGRATIONS.md#2-postgresql` (Neon free / local Docker fallback). Not a code defect — a verification gap.
- [ ] **No git remote configured** → nothing can be pushed/PR'd; "Merge" commits to date are local only. Decide on remote before relying on PR-based review in `docs/PLAYBOOK.md`.

## 🟡 Priority work (Phase 0 completion)

- [ ] **T-000.7 — CI workflow** (`ready`, not started): no `.github/workflows/`. Last open Phase-0 task; gates the "CI green" acceptance criterion + the P0 exit gate. Trace: `F-000` AC line 24, `FEATURES.md` P0 gate, `skills:testing-standard`.
- [ ] **Finish + close T-000.6**: verify `make dev` actually boots the server and `/health` responds (DoD: "`make dev` boots"). Code looks complete (`api/app.py`, `api/health.py`); only the live-boot check is unconfirmed. Trace: `F-000` T-000.6 DoD.
- [ ] **Run the DB-backed verification once** (local Docker Postgres + pgvector): apply `migrations/versions/0001_initial.py`, confirm tables match `DATA-MODEL.md` and `embeddings.vector` dim = 384, then check the two DB-dependent feature criteria. Trace: `F-000` AC lines 19–20.

## 🟢 Next phase (do NOT start until P0 exit gate is met + reviewed)

- [ ] **Slice Phase 1 into `tasks/BOARD.md`**: F-001 → F-002 → F-003 → F-004 (build order per `FEATURES.md` line 13). BOARD line 25 explicitly says F-001 is "sliced next, after P0 review". No Phase-1 work should exist yet — confirm none does (it doesn't).
