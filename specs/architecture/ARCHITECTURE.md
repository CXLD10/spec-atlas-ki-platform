# ARCHITECTURE.md — Spec-Atlas

Status: ready (revised)
References: DATA-MODEL.md, INTEGRATIONS.md, NFR.md
Supersedes: the earlier Python-first / graph-RAG architecture (project formerly "Sextant").

## Guiding decisions
1. **Multi-language from day one.** The structural parser is **tree-sitter**, which has uniform grammars across many languages. Adding a language is an additive grammar + query pack, not a rewrite. No reliance on Python's `ast`.
2. **Expensive understanding at index time; cheap retrieval at query time.** All graph construction, LLM spec generation, and summarization happen offline during indexing. Query time is a vector search plus a tree descent — never a live graph traversal.
3. **The LLM carries the semantic load.** Structural analysis (imports/calls) is only the substrate. Meaning ("context and know-how") is synthesized by the LLM into specs and group summaries. This is what makes multi-language tractable without perfect per-language call resolution.
4. **Local-first, zero cost.** Runs on the developer's machine; only externals are free Postgres (Neon) + a free-tier LLM. Source stays local; the MCP server is local.

## The layered knowledge model
Four layers. Lower layers are facts; higher layers are understanding.

- **L1 — Code Knowledge Graph (structural substrate).** tree-sitter parses every supported language into a uniform graph: `nodes` (modules, classes, functions, methods) and `edges` (imports, calls, inherits, defines) with confidence. Multi-language from the start.
- **L2 — Spec layer ("Specify" tool).** An LLM reads a region of the L1 graph and generates a structured, schema-validated **spec** (purpose, inputs/outputs, dependencies, invariants, side effects, failure modes), grounded in source spans. This is where semantic understanding is created.
- **L3 — Spec graph (parent/context graph).** Specs are linked to one another (`depends-on`, `part-of`, `uses`) into a higher-level semantic graph that provides context the raw L1 edges don't carry.
- **L4 — group.md tree (navigable knowledge, retrieval entry).** Specs and sub-groups are rolled up into a hierarchy of condensed markdown summaries (system → group → sub-group), each capturing context and know-how. The `group.md` layer is what gets embedded and vector-searched.

## Index-time pipeline (bottom-up, offline)
```
source (any language)
  └─ tree-sitter parse ─────────────► L1: nodes + edges (Analysis DB)
        └─ Specify (LLM over graph regions) ─► L2: structured specs (Spec DB)
              └─ spec linking ──────────────► L3: spec graph (edges between specs)
                    └─ roll-up summaries ───► L4: group.md tree + embeddings (pgvector)
```
Each stage is incremental: unchanged source (same content hash) is skipped; only affected specs/groups are regenerated.

## Query-time pipeline (top-down, fast)
```
question
  └─ embed query
        └─ vector search over L4 group.md  ──► matched group(s)
              └─ descend the tree: group → sub-group → spec → code span
                    └─ assemble grounded context (specs + summaries + spans)
                          └─ Answerer (LLM) ─► answer + provenance
```
No live graph traversal. Retrieval cost ≈ one ANN search + a bounded descent.

## Components & responsibilities
1. **Ingestor** — resolves repo (local path / public git URL), inventories files, detects language, hashes.
2. **Parser (tree-sitter)** — language-agnostic CST → L1 nodes; per-language query packs extract symbols/edges.
3. **Edge Extractor** — imports/calls/inherits/defines with confidence (best-effort cross-file).
4. **Graph Store (Analysis DB)** — persists L1; supports the bounded lookups used during index-time spec generation.
5. **Specify engine (L2)** — LLM generates specs from graph regions; schema-validated; provenance-bound.
6. **Spec Graph builder (L3)** — links specs into the parent graph.
7. **Group/Summary builder (L4)** — clusters into a tree and writes `group.md` rollups; embeds them.
8. **Embedder** — vectors for `group.md` (primary) and specs (for direct lookup) → pgvector.
9. **Retriever** — vector search over L4, then tree descent into L3/L2/L1.
10. **Answerer** — grounded answer + provenance.
11. **Spec Store (Spec DB, separate)** — per-user, versioned specs + the spec graph.
12. **Spec Verifier** — checks invariants/claims against code before marking `verified`.
13. **Drift Detector** — commit diff → stale specs/groups → regenerate affected subtree only.
14. **MCP Server (local)** — tools: `search` (vector+descend), `get_spec`, `get_group`, `list_stale_specs`.
15. **API Gateway (FastAPI)** + **Web UI (TS/React)**.

## Stack
- Backend: Python 3.12 + FastAPI (+ tree-sitter bindings, fastembed).
- Frontend: TypeScript + React (Vite); group-tree + answer/citation views.
- Storage: PostgreSQL (Neon free) + pgvector. **Analysis DB** (L1) + **Spec DB** (L2/L3 specs + spec graph). L4 group embeddings live in pgvector.
- LLM + embeddings: provider-abstracted (`LLMProvider`, `EmbeddingProvider`); defaults Gemini/Groq free + local fastembed.
- Agent interface: local MCP server (stdio).

## Module layout (backend)
```
src/spec_atlas/
  ingest/      parse/      graph/        # L1
  specify/     specgraph/                # L2, L3
  groups/      embed/                    # L4
  retrieve/    answer/                   # query time
  spec/        drift/      mcp/          # store, verify, drift, agents
  llm/         db/         api/   config.py
frontend/
```

## Cross-cutting contracts (freeze before dependents build)
- **Node identity:** `(repo_id, language, qualified_name, kind)` — stable, idempotent re-ingest.
- **Provenance everywhere:** every spec field, group claim, and answer carries `{file, start_line, end_line}`.
- **Provider interfaces only:** never call a vendor SDK directly.
- **Language packs are additive:** a new language adds a tree-sitter grammar + query pack implementing the same L1 node/edge contract; nothing upstream changes.

## Open decisions (must resolve before DATA-MODEL/FEATURES regen)
- **D1 — group/tree formation:** directory/package structure (deterministic, multi-language-friendly) vs. graph community detection (Louvain/Leiden on L1) vs. LLM clustering. *Recommendation: directory/package skeleton first, refine with community detection later.*
- **D2 — initial languages shipped:** which set at v1 (e.g. Python + TypeScript/JS, optionally Go/Java). *Recommendation: Python + TypeScript/JS first; both cover your own stack.*
- **D3 — vector-search scope:** embed L4 groups (primary) + specs (direct lookup); code spans fetched by descent, not embedded. *Recommendation: as stated.*
