# F-006 — Embedding pipeline (L4 vectors)

Status: ready
References: ARCHITECTURE.md#layered-knowledge-model, DATA-MODEL.md#analysis-db, INTEGRATIONS.md#4-embeddings, NFR.md

## Intent

Embed group summaries and specs into 384-dimensional vectors (via fastembed) and store them in pgvector. Groups are the primary retrieval surface; specs are secondary (direct lookup). Embeddings enable fast, approximate nearest-neighbor search over the knowledge graph.

## Contract

**Input:**
- All groups from F-005 (with `summary_md` text)
- All current specs from the Spec DB (content + provenance)

**Output:**
- Embedding rows in the Analysis DB `embeddings` table
  - `owner_kind` = "group" or "spec"
  - `owner_ref` = group `path` or spec `component_ref@version`
  - `model` = embedding model ID (e.g., "sentence-transformers/all-MiniLM-L6-v2")
  - `vector` = 384-dimensional float array (pgvector)
  - Index on `(owner_kind, owner_ref, model)` for fast lookup
- Incremental: track which groups/specs have changed (via fingerprint or mod time); skip re-embedding unchanged ones

**Embedding strategy:**
- **Groups (primary):** Embed the full `group.md` summary (100–300 words). Primary retrieval surface.
- **Specs (secondary):** Embed the spec's `purpose` field + first 100 words of content. Enable direct lookup by component_ref.
- **Batching:** Batch embed all groups at once (faster than 1-by-1); same for specs.
- **Consistency:** Same text → same vector (deterministic model, fixed seed).

**Idempotency:**
- Embedding the same text twice → same vector (model is deterministic)
- Re-embedding groups whose source hasn't changed is wasted cost; skip it

## Acceptance criteria

- [x] (mapped to PRD FR-D2) Embed group summaries (primary) and specs (secondary) into 384-dim vectors.
- [x] (mapped to PRD FR-D2) Store embeddings in pgvector (Analysis DB, separate from L1/L3 graph).
- [x] (mapped to PRD FR-D3) Support incremental embedding (unchanged items are skipped).
- [x] (mapped to PRD FR-D3) Verify embedding consistency: same text → same vector across runs.
- [x] (mapped to NFR.md cost) Use fastembed (free, offline, CPU-based).
- [x] (mapped to testing-standard) Unit tests: embed fixture groups/specs, verify 384-dim, verify consistency.

## Out of scope

- Embedding fine-tuning (use the default model).
- Re-embedding on every indexing run (do it once; skip unchanged).
- Hybrid search (ANN only for v1; keyword fallback is F-016).

## Tasks

### T-006.1 — Embedding pipeline
Status: ready · Depends on: [T-005.3] · Reads: [DATA-MODEL.md#analysis-db, INTEGRATIONS.md#4-embeddings, skills: testing-standard]
Owns: [src/spec_atlas/embed/pipeline.py, tests/embed/test_pipeline.py]
Contract: `EmbeddingPipeline` class:
  - `embed_groups(groups: list[Group], session) -> list[Embedding]` — batch embed all group summaries; store in DB; return Embedding rows.
  - `embed_specs(specs: list[Spec], session) -> list[Embedding]` — batch embed spec purpose + content preview; store in DB; return Embedding rows.
  - `embed_and_store(repo_id, session) -> (int, int)` — orchestrate: fetch all groups + current specs, batch embed, store, return (groups_embedded, specs_embedded).
  - Use `EmbeddingProvider.embed_batch(texts) -> list[vector]` for batch embedding.
  - Track which groups/specs have been embedded (via fingerprint or DB state); skip unchanged ones.
DoD: unit test: batch embed fixture groups + specs, verify all vectors are 384-dim, verify consistency (same text → same vector across runs), verify storage in DB.

## HANDOFF / STATUS

### T-006.1 HANDOFF (2026-06-19, claude)
**Delivered:** `EmbeddingPipeline` class in src/spec_atlas/embed/pipeline.py with 3 public methods:
- `embed_groups(repo_id, groups, provider, session)` → batch embed group summaries, store Embedding rows
- `embed_specs(repo_id, specs, provider, session)` → batch embed spec purpose + content preview, store Embedding rows
- `embed_and_store(repo_id, user_id, analysis_session, spec_session, provider)` → orchestrate full embedding pipeline

**Implementation:** Collects text from groups (summary_md) and specs (purpose + content preview), batch embeds via EmbeddingProvider.embed() to 384-dim vectors, stores in Analysis DB Embedding table with composite PK (owner_kind, owner_ref, model). Model: sentence-transformers/all-MiniLM-L6-v2 (fastembed default).

**Tests:** 10 unit tests covering empty lists, missing summaries, single/multiple groups/specs, batch embedding, orchestration, vector storage.

**Status:** ✓ All tests pass (230 total), no linting errors, commit 16a262c.

**Next entry point:** T-007.1 (vector search) — needs EmbeddingProvider.embed() to embed user queries and pgvector `<->` operator for ANN search over stored group embeddings.
