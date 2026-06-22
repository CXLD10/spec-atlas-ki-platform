# INTEGRATIONS.md — Spec-Atlas

Status: ready
References: ARCHITECTURE.md, NFR.md

Every external dependency must be free-tier-sufficient; quotas drift, re-verify before relying on a limit. Each is wrapped behind an interface so it can be swapped without touching callers.

## 1. Parsing — tree-sitter (library, local, free)
- **Use:** language-agnostic CST → L1 nodes/edges. Multi-language from v1.
- **Contract:** a per-language **query pack** (grammar + queries) implementing the shared node/edge contract. Initial packs: Python, TypeScript/JS (ADR-0001 D2). Adding a language = adding a pack; nothing upstream changes.

## 2. PostgreSQL — Neon (free)
- **Use:** Analysis DB (graph + group tree + embeddings via `pgvector`) and a separate Spec DB.
- **Contract:** connection strings via env (`ANALYSIS_DB_URL`, `SPEC_DB_URL`); migrations via Alembic.
- **Limits:** storage + compute-hours on free tier; free projects can auto-suspend (cold start). Store structure/summaries, not raw source.
- **Fallback:** local Postgres in Docker ($0).

## 3. LLM provider — abstracted (`llm/`)
- **Interface:** `LLMProvider.complete(messages, schema=None) -> text|json`.
- **Default:** Gemini or Groq free tier; **local Ollama** for fully offline.
- **Used by:** Specify engine (spec generation), group summaries, Answerer. Structured-output prompting; never trust free-form where JSON is required.
- **Limits:** requests/min + tokens/day. Batch generation; cache; never regenerate unchanged areas.

## 4. Embeddings — local by default (`embed/`)
- **Interface:** `EmbeddingProvider.embed(texts) -> vectors`.
- **Default:** `fastembed` + `BAAI/bge-small-en-v1.5` (384-dim, CPU, zero cost). Dim must match `embeddings.vector(N)`; changing models needs an ADR (re-embed).

## 5. MCP server — local (`mcp/`)
- **Use:** exposes `search` (vector + descend), `get_group`, `get_spec`, `list_stale_specs` to coding agents over stdio.
- **Why local:** agents run on the dev machine; no hosting cost; source stays private. Tool schemas frozen in the MCP feature spec.

## 6. Source access
- Git via local CLI / `gitpython`. Public repos only in v1 (no stored credentials). The pipeline **reads files only — never executes repo code**.

## 7. Hosting (optional, later) — all free tier
- API on Render/Fly free (or run locally); frontend on Vercel/Cloudflare Pages free; CI on GitHub Actions; heavy indexing local or in Actions. Never a paid worker.

## Integration contract checklist
Config via env (documented in `.env.example`); a contract test against a **fake/stub** by default (offline, free CI) and optionally the real service when creds present; explicit handling of 429 / timeout / cold-start; no secret committed (`.env` gitignored).
