# EXECUTION PROMPT — Phase 5: Robustness & spec parity

Repo: `CXLD10/spec-atlas-ki-platform`. Phases 0–4 done. Goal: close spec≠code gaps and harden — drift detection, eval harness in CI, TS/JS tree-sitter, rate limiting. After this the system matches its own specs. CI stays offline.

## Do these, in order

**1. Drift detection — F-014 (Dev B).** No `src/` implementation exists despite the spec being "ready" and advertised in the UI. Implement `DriftDetector` comparing `source_fingerprint` on re-ingest; mark specs `stale` + set `staleness_detected_at`; filter/flag stale specs in retrieval. Spec: `specs/features/F-014-drift-detection.md`.

**2. Eval harness — F-016 (Dev B).** `tests/eval/` has only `fixtures/`. Implement the retrieval/answer eval over those fixtures; report grounded-citation / precision-recall metrics; run in CI offline (`fake`/`fastembed`); fail on regression threshold. Spec: `specs/features/F-016-eval-harness.md`.

**3. TS/JS tree-sitter (Dev B).** Replace regex extraction (`parse/ts_symbols.py:36-75`) and regex cross-file edges (`graph/edges_crossfile.py`) with real tree-sitter CST, matching the Python path (`parse/python_symbols.py`).

**4. Rate limiting (Dev B).** `api/ingest.py:73-77` and `api/answer.py:268-272`: `_apply_rate_limit` is a no-op (`# TODO: Fix slowapi compatibility`). Wire `slowapi` middleware/limiter properly per F-017/NFR.

**5. Docs page — optional (Dev A).** `pages/Docs.tsx` embeds docs as in-file constants; search is dead. Optionally source from `docs/` and wire search. Demo-cosmetic; lowest priority.

## Seed
Re-ingest the Phase 0 repo after a small change to exercise drift. Use existing `tests/eval/fixtures`. Add a small TS/JS file (classes/functions/imports) for the tree-sitter test.

## Must pass before commit
```bash
pytest -q tests/eval tests/parse tests/api
pytest -q
cd frontend && npm run build && npm run test
```
Add: `test_drift_marks_stale_on_reingest`, `test_eval_harness_reports_metrics`, `test_ts_symbols_via_treesitter`, `test_rate_limit_enforced`.

## Frontend checks (manual)
1. Re-ingesting a changed repo shows a **stale** badge on affected specs.
2. TS/JS repos produce real symbols/edges in `/graph` (not regex-degraded).
3. Hammering Ask/Ingest triggers a real 429.
4. (If 5.5 done) Docs search returns real matches.

## STOP & COMMIT
```
feat(phase5): drift detection, eval harness, tree-sitter TS/JS, rate limiting
```

## Program close-out
Run the whole-program Definition of Done in `00-MASTER-PLAN.md`. Confirm: `lib/mock.ts` referenced only by tests; route-table smoke test green on a seeded DB; clean `docker compose up` demos the full flow end-to-end with **zero** mock fallbacks. Report the final checklist state.
