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
                          └─ (optional) retrieve memory facts from prior sessions
                                └─ Answerer (LLM) ─► answer + provenance (code + doc citations)
```
No live graph traversal. Retrieval cost ≈ one ANN search + a bounded descent + optional memory fetch.

## Three-Layer Graph-RAG Architecture (Phase 1–3)

Spec-Atlas integrates a **three-layer graph** with **multi-source RAG** to ground answers in code, docs, and memory:

```
┌─────────────────────────────────────────────────────┐
│ L1: Code Knowledge Graph (tree-sitter)              │
│   Nodes: modules, classes, functions                │
│   Edges: imports, calls, inherits, defines          │
│   Source: Python, TypeScript, Go (tree-sitter)      │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ L2: Spec Layer (LLM-generated, versioned)           │
│   Specs: purpose, inputs/outputs, invariants        │
│   Provenance: file:line spans in code               │
│   Storage: Spec DB (separate from L1)               │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ L3: Spec Graph + Multi-Source Links                 │
│   Spec-to-spec edges: depends-on, part-of, uses    │
│   Multi-source edges: code ↔ PDF, Markdown, Excel  │
│   Dual-locator citations:                           │
│     - Code: {file, start_line, end_line}            │
│     - PDF: {source, page, bbox}                     │
│     - Markdown/Excel: {source, section}             │
│   Memory facts: {fact, sources, relevance}          │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ L4: Knowledge Synthesis (group.md tree + memory)    │
│   Hierarchical summaries: system → group → subgroup │
│   Embedded for vector search                        │
│   Memory facts retrieved by relevance               │
│   Output: answer with mixed citations               │
└─────────────────────────────────────────────────────┘
```

### Multi-Source Ingestion (Phase 1)

**SourceUnit abstraction** normalizes ingestion across code, PDF, Markdown, Excel, Jira, git history:

```python
class SourceUnit:
    source_id: str          # unique per project
    type: str               # "code", "pdf", "markdown", "excel", "jira", "git_history"
    name: str               # file name or URL
    metadata: Dict          # language, pages, encoding, etc.
    locator: Union[CodeLocator, PDFLocator, TextLocator]  # how to cite

class CodeLocator:
    file: str
    start_line: int
    end_line: int

class PDFLocator:
    page: int
    bbox: Tuple[float, float, float, float]  # normalized [x0, y0, x1, y1]
```

Each source is embedded + indexed for retrieval; answers cite sources with proper locators.

### Conversation Memory (Phase 3)

```python
class MemoryFact:
    fact: str               # "entry point is main.py"
    sources: List[str]      # ["code", "pdf", "memory"]
    provenance: Dict        # {source: locator}
    relevance: float        # 0.0–1.0
    created_at: datetime
    project_id: str
```

Facts are extracted from each conversation turn, stored in a durable facts DB, and retrieved by relevance in subsequent sessions. Agents access memory via API + MCP.

## Components & responsibilities
1. **Ingestor** — resolves repo (local path / public git URL), inventories files, detects language, hashes.
2. **Parser (tree-sitter)** — language-agnostic CST → L1 nodes; per-language query packs extract symbols/edges.
3. **Edge Extractor** — imports/calls/inherits/defines with confidence (best-effort cross-file).
4. **Graph Store (Analysis DB)** — persists L1; supports the bounded lookups used during index-time spec generation.
5. **SourceUnit Registry** *(Phase 1)* — abstracts multi-source ingestion (code, PDF, Markdown, Excel, Jira, git). Per-source adapters extract + normalize text + metadata + locators.
6. **PDF Adapter** *(Phase 1)* — PyMuPDF extracts text + preserves page/bbox citations.
7. **Specify engine (L2)** — LLM generates specs from graph regions; schema-validated; provenance-bound.
8. **Spec Graph builder (L3)** — links specs into the parent graph; includes multi-source edges (code ↔ PDF).
9. **Group/Summary builder (L4)** — clusters into a tree and writes `group.md` rollups; embeds them.
10. **Embedder** — vectors for `group.md` (primary) and specs (for direct lookup) → pgvector. Handles multi-source text normalization.
11. **Retriever** — vector search over L4, then tree descent into L3/L2/L1. Retrieves memory facts by relevance *(Phase 3)*.
12. **Answerer** — grounded answer + provenance. Formats citations by source type (code, PDF, Markdown, etc.).
13. **Memory Store** *(Phase 3)* — durable facts DB; extracts facts from conversations, retrieves by relevance.
14. **Spec Store (Spec DB, separate)** — per-user, versioned specs + the spec graph.
15. **Spec Verifier** — checks invariants/claims against code before marking `verified`.
16. **Drift Detector** — commit diff → stale specs/groups → regenerate affected subtree only.
17. **MCP Server (local)** — tools: `search` (vector+descend), `get_spec`, `get_group`, `list_stale_specs`, `get_memory_facts` *(Phase 3)*.
18. **API Gateway (FastAPI)** + **Web UI (TS/React)** — source manager UI, graph explorer, specify tool, conversation history + memory sidebar *(Phases 1–3)*.

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
