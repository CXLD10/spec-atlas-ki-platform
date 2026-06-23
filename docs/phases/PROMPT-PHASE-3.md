# EXECUTION PROMPT — Phase 3: Real external sources

Repo: `CXLD10/spec-atlas-ki-platform`. Phases 0–2 done. Goal: git history, Jira, and the Deep Wiki fallback return real data behind provider interfaces. No literal/mock payloads left in `api/sources.py` or the answer fallback. CI stays offline; real-provider paths are env-gated.

## Do these, in order

**1. Real git history (Dev B).** `api/sources.py:30-66` returns 5 literal commits. Replace with `git log` against the resolved repo working dir (via `ingest/resolver.py`) **or** commits stored at ingest, queried by repo + optional `file_path`. Honor `file_path` and `limit` for real. References panel shows real commits.

**2. Real Jira (Dev B).** `api/sources.py:92-142` returns literal `ATLAS-123..126`. Replace with a Jira export-JSON import to a table (offline default) and/or a Jira REST call behind a provider interface (httpx-only, no vendor SDK — match the LLM/embed provider pattern). Index issues as `SourceUnit`s with provenance (uses Phase 2 persistence). Filter over real data.

**3. Real Deep Wiki fallback (Dev B).** `api/answer.py:219-242` only returns a canned string under `LLM_PROVIDER=fake`. Replace with a real general-knowledge call behind the provider interface (or the configured LLM with a "no project context" prompt). Keep the disclaimer. Derive confidence honestly (no hardcode). Triggered by the real `<0.4` confidence from Phase 0.

## Seed
A committed `git log` fixture (or the seeded repo's real history); a sample Jira export under `tests/fixtures/jira/`; keep `fake` deterministic for CI and env-gate the real Deep-Wiki call.

## Must pass before commit
```bash
pytest -q tests/api/test_sources.py
pytest -q tests/answer
pytest -q
cd frontend && npm run build && npm run test
```
Add: `test_git_history_from_real_log`, `test_jira_import_indexes_issues`, `test_deep_wiki_fallback_honest_confidence`.

## Frontend checks (manual)
1. References panel shows real commits for the seeded repo (not `a864233…`).
2. Jira panel shows imported issues; filtering returns real subsets.
3. Out-of-scope question → low real confidence → Deep Wiki fallback with disclaimer + believable answer (not the canned string).

## STOP & COMMIT
```
feat(phase3): real git history, Jira import, and honest Deep Wiki fallback
```
Report changed files, test output, confirmation no literal payloads remain. Do not start Phase 4.
