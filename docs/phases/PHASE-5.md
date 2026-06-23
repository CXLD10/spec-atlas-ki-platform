# Phase 5 — Robustness & spec parity

**Effort:** L · **Depends on:** all prior · **Audit items:** §3.12, §3.20, "Specified but not implemented" (F-014, F-016)

## Objective
Close the spec≠code gaps and harden. Drift detection marks stale specs on re-ingest; the eval harness runs in CI; TS/JS parsing uses tree-sitter instead of regex; rate limiting is active. After this, the system matches its own specs.

---

## Tasks

### 5.1 — Drift detection (F-014) *(Dev B, L)*
- No `src/` implementation exists despite the spec being "ready" and advertised in the UI (no `DriftDetector`, no `staleness_detected_at`).
- Implement `DriftDetector` comparing `source_fingerprint` on re-ingest; mark specs `stale` + set `staleness_detected_at`; filter stale specs in retrieval (or flag them in answers).
- Spec: `specs/features/F-014-drift-detection.md`.

### 5.2 — Eval harness (F-016) *(Dev B, M)*
- `tests/eval/` has only `fixtures/`; no eval module.
- Implement the retrieval/answer eval over `tests/eval/fixtures`; report precision/recall or grounded-citation metrics. Run in CI (offline, `fake`/`fastembed`).
- Spec: `specs/features/F-016-eval-harness.md`.

### 5.3 — TS/JS via tree-sitter *(Dev B, M)*
- Replace regex extraction (`parse/ts_symbols.py:36-75`) and regex cross-file edges (`graph/edges_crossfile.py`) with real tree-sitter CST, matching the Python path (`parse/python_symbols.py`).

### 5.4 — Enable rate limiting *(Dev B, S)* — §3.12
- `api/ingest.py:73-77`, `api/answer.py:268-272`: `_apply_rate_limit` is a no-op (`# TODO: Fix slowapi compatibility`). Wire `slowapi` middleware/limiter properly per NFR/F-017.

### 5.5 — Docs page (optional) *(Dev A, S)* — §3.20
- `pages/Docs.tsx` embeds all docs as in-file constants; search is non-functional. Optionally source from `docs/` and wire search. Low priority; demo-cosmetic.

---

## Seed / fixtures
- Re-ingest the Phase 0 repo after a small simulated change to exercise drift.
- Eval fixtures already under `tests/eval/fixtures`.
- A small TS/JS file with classes/functions/imports for the tree-sitter test.

## Backend tests
```bash
pytest -q tests/eval                      # harness runs
pytest -q tests/parse                     # TS/JS tree-sitter
pytest -q tests/api                       # rate limiting active
pytest -q                                 # full suite
```
New tests:
- `test_drift_marks_stale_on_reingest` — changed fingerprint → `stale` + `staleness_detected_at`; retrieval filters/flags.
- `test_eval_harness_reports_metrics` — runs offline, emits metrics, fails on regression threshold.
- `test_ts_symbols_via_treesitter` — TS/JS symbols+edges from CST, parity with Python extractor.
- `test_rate_limit_enforced` — exceeding the limit returns 429.

## Frontend integration checks
1. After re-ingesting a changed repo, affected specs show a **stale** badge (the advertised drift feature now backed by real data).
2. TS/JS repos produce real symbols/edges in `/graph` (not regex-degraded).
3. Hammering Ask/Ingest triggers a real 429 (rate limiting on).
4. (If 5.5 done) Docs search returns real matches.

## Definition of Done
- Drift detection live; eval harness in CI; TS/JS uses tree-sitter; rate limiting enforced.
- Spec and code agree; "Specified but not implemented" list is empty for these items.
- Full suite green; CI offline.

## Commit checkpoint
```
feat(phase5): drift detection, eval harness, tree-sitter TS/JS, rate limiting
```

---

## Program close-out
Run the whole-program Definition of Done checklist in `00-MASTER-PLAN.md`. Confirm `lib/mock.ts` is referenced only by tests, the route-table smoke test is green against a seeded DB, and a clean `docker compose up` demos the full flow end-to-end with zero mock fallbacks.
