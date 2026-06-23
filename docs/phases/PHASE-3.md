# Phase 3 — Real external sources

**Effort:** M · **Depends on:** Phase 2 · **Audit items:** §3.1, §3.2, §3.3

## Objective
The three hardcoded external integrations become real: git history from the resolved repo, Jira from a real import/REST path, and the Deep Wiki fallback from a real provider call with honest confidence. The references panel (commits/Jira) and low-confidence fallback now show genuine data.

---

## Tasks

### 3.1 — Real git history *(Dev B, S–M)* — §3.1
- `api/sources.py:30-66` returns 5 literal commits. Replace with either:
  - `git log` against the resolved repo working dir (available via `ingest/resolver.py`), or
  - commits stored during ingest, queried by repo + optional file path.
- Honor `file_path` filter and `limit` for real.
- **Frontend:** the collapsible references panel shows real commits.

### 3.2 — Real Jira *(Dev B, M)* — §3.2
- `api/sources.py:92-142` returns literal `ATLAS-123..126`. Replace with:
  - a Jira **export-JSON import** to a table (offline-friendly, default), and/or
  - a **Jira REST** call behind a provider interface (opt-in, httpx-only, no vendor SDK — consistent with the LLM/embed provider pattern).
- Index issues as `SourceUnit`s with provenance (depends on Phase 2 persistence).
- Query filter runs over real data, not the mock list.

### 3.3 — Real Deep Wiki fallback *(Dev B, M)* — §3.3
- `api/answer.py:219-242` only returns a canned string when `LLM_PROVIDER=fake`. Replace with a real general-knowledge call behind the provider interface (or the configured LLM with a "no project context" prompt).
- Keep the disclaimer. Derive confidence **honestly** (do not hardcode). Triggered by the now-real `< 0.4` confidence from Phase 0.4.

---

## Seed / fixtures
- A small committed `git log` fixture (or use the Phase 0 seeded repo's real history).
- A sample Jira export JSON under `tests/fixtures/jira/`.
- For Deep Wiki: keep `fake` provider deterministic in CI; gate the real-call test behind an env flag so CI stays offline.

## Backend tests
```bash
pytest -q tests/api/test_sources.py      # git + jira now real
pytest -q tests/answer                   # deep wiki fallback honest
pytest -q
```
New tests:
- `test_git_history_from_real_log` — commits come from the repo, respect `file_path`+`limit`; no literal SHAs.
- `test_jira_import_indexes_issues` — export JSON → `SourceUnit`s with provenance; filter works on real data.
- `test_deep_wiki_fallback_honest_confidence` — fallback path returns provider content + disclaimer + non-hardcoded confidence (offline `fake` deterministic; real-provider variant env-gated).

## Frontend integration checks
1. References panel shows **real** commit messages/SHAs for the seeded repo (not `a864233…`).
2. Jira issues panel shows imported issues; filtering returns real subsets.
3. Ask a deliberately out-of-scope question → low real confidence → Deep Wiki fallback renders **with disclaimer** and a believable answer (not the canned `"Based on general knowledge about '…'"`).

## Definition of Done
- git history, Jira, and Deep Wiki fallback return real data behind provider interfaces; no literal/mock payloads remain in `api/sources.py` or the answer fallback.
- CI stays offline/deterministic; real-provider paths env-gated.
- Tests green; full suite green.

## Commit checkpoint
```
feat(phase3): real git history, Jira import, and honest Deep Wiki fallback
```
