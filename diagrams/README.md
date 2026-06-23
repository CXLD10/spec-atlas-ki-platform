# Spec-Atlas Architecture Diagrams

This folder contains individual Mermaid diagram files extracted from `ARCHITECTURE-E2E.md`. 
Each `.mmd` file can be viewed directly in VS Code with the Mermaid extension.

## Diagram List

| # | Filename | Type | Description |
|---|----------|------|-------------|
| 1 | `d01-system-context-c4-level-1.mmd` | flowchart | Engineers, agents, Spec-Atlas system, Postgres, LLM/embed providers, git hosts, Jira (with real/mock legend) |
| 2 | `d02-container-and-component-view.mmd` | flowchart | Frontend SPA, FastAPI routers (ingest/answer/graph/groups/specs/reports/sources/health), workers, retrieval pipeline, providers, MCP server, two DBs |
| 3 | `d03-multi-layer-knowledge-model-l1-l4.mmd` | flowchart | L1 code graph → L4 groups (directory clustering) → L2 specs (LLM generate) → L3 spec_edges (derived from L1 edges) |
| 4 | `d04-data-model-erd---analysis-db.mmd` | erDiagram | Analysis DB schema: repos, files, nodes, edges, groups, embeddings, ingest_jobs (rebuildable index) |
| 5 | `d05-data-model-erd---spec-db.mmd` | erDiagram | Spec DB schema: specs (versioned, current = valid_to IS NULL), spec_edges (L3 graph edges, derived from L1) |
| 6 | `d06-ingestion-sequence.mmd` | sequenceDiagram | Full ingest flow: paste URL → resolve repo → inventory files → detect languages → extract symbols/edges → generate specs → cluster groups → summarize → embed → build spec graph (with progress %) |
| 7 | `d07-query-rag-sequence.mmd` | sequenceDiagram | `/api/ask` RAG pipeline: route query → vector search (pgvector ANN or keyword fallback) → tree descent → answer via LLM → confidence check → Deep Wiki fallback (mock) or real claims |
| 8 | `d08-provider-abstraction.mmd` | classDiagram | `LLMProvider` + `EmbeddingProvider` interface; implementations: `FakeLLMProvider`, `GeminiLLMProvider`, `OllamaProvider`, `GroqProvider` (all httpx, no SDK); `FakeEmbeddingProvider`, `FastembedEmbeddingProvider` |
| 9 | `d09-mcp-agent-integration.mmd` | flowchart | MCP server (no entrypoint), four tools (search_knowledge, get_spec, get_graph, ask_question), handlers with real/broken/stub status |
| 10 | `d10-frontend-architecture.mmd` | flowchart | React routes (Dashboard, Sources, KB, Graph, Ask, Specify, MCP, Index); two divergent API clients (lib/api.ts mock-fallback vs api/client.ts throwing); backend endpoints (many missing) |
| 11 | `d11-deployment-and-runtime-topology.mmd` | flowchart | docker-compose.yml: postgres (pgvector), spec-atlas (FastAPI); alembic migrations; frontend (Vite dev server, not in compose); real/mock division |

## Legend

**Color scheme (used across all diagrams):**
- **Solid green nodes** = REAL, implemented and wired end-to-end
- **Dashed amber nodes** = MOCK / stub / not-wired (status report `SYSTEM_STATUS_AND_REMEDIATION.md §4` lists remediation phases)

## Usage in VS Code

1. Install the **Mermaid** extension (e.g., "Markdown Preview Mermaid Support")
2. Open any `.mmd` file → the diagram renders in the preview pane
3. All diagrams parse cleanly (validated via `mermaid@11`)

## Reference

- Full architecture document: `../ARCHITECTURE-E2E.md`
- System status & remediation roadmap: `../SYSTEM_STATUS_AND_REMEDIATION.md`
- Code root: `../src/spec_atlas/`
