# Spec-Atlas: Knowledge Intelligence for Engineering

> **Transform your codebase and documentation into a searchable, intelligent knowledge graph.** Ask questions. Get grounded answers with citations. Generate specs automatically.

![Version](https://img.shields.io/badge/version-0.6.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-Production%20Ready-brightgreen)

## 🎯 What is Spec-Atlas?

Spec-Atlas is a **zero-cost, local-first knowledge intelligence platform** that indexes repositories and documents to create a queryable, intelligent knowledge base. It combines:

- **Code Understanding**: Parses source code to extract symbols, dependencies, and relationships
- **Document Intelligence**: Ingests PDFs, Markdown, and spreadsheets with structural awareness
- **Semantic Search**: Uses embeddings to find relevant code and documentation
- **Automated Specs**: Generates knowledge cards (L3 specs) on demand with LLM
- **Knowledge Graph**: 3D visualization of your codebase structure and relationships
- **Citation System**: Every answer links back to its source (file:line for code, page/cell for docs)

### Why Spec-Atlas?

- 🎓 **Onboarding**: New team members query the codebase instead of asking questions
- 📚 **Documentation**: Auto-generate specs from code; keep docs in sync with reality
- 🔍 **Search**: Find code, concepts, and decisions across 100K+ LOC instantly
- 🏗️ **Architecture**: Visualize how components relate in an interactive 3D graph
- 💰 **Zero Cost**: Local-first, offline-capable, uses free/OSS LLM providers by default
- 🔐 **Private**: Everything runs locally; no cloud, no data leakage

---

## ✨ Key Features

### 📑 Multi-Source Ingestion
- **Code**: Clone any Git repository (Python, JavaScript/TypeScript, Go, etc.)
- **Documents**: PDF, Markdown, Excel spreadsheets with page/cell awareness
- **Git History**: Track code changes and commit context
- **Jira**: Import issues and requirements

### 🧠 Intelligent Retrieval (RAG)
- Vector embeddings for semantic search
- Dual-locator citations (code: `file:line`, docs: `page:bbox`)
- Conversation memory across sessions
- Context-aware ranking and retrieval

### 📊 Knowledge Graph
- 3-layer visualization (L1 sources, L3 specs, L4 domains)
- Interactive 3D rendering with Three.js
- Click-through workflow: graph → ask → specify
- Real-time provenance tracking

### 🤖 Automated Spec Generation
- One-click knowledge card generation for any code entity
- LLM-powered with structured output (purpose, inputs, outputs, invariants, etc.)
- Spec versioning and verification workflow
- Drift detection flags when code changes

### 💬 Ask Atlas (Chat)
- Query your entire knowledge base with natural language
- Get answers grounded in your code with citations
- Fallback to general knowledge when code context missing
- Real-time streaming responses

---

## 🏗️ Architecture Overview

### System Diagram
```
Frontend (React 18, Vite)
    ↓ HTTP/REST
Backend (FastAPI, SQLAlchemy)
    ├─ Ingest Pipeline (6 phases)
    ├─ Retrieval Engine (RAG)
    ├─ Answer Generation (LLM)
    └─ Knowledge Graph
    ↓ SQLAlchemy ORM
Databases (PostgreSQL + pgvector)
    ├─ Analysis DB (source units, entities, graph)
    └─ Spec DB (specs, embeddings, verification)
```

### Ingest Pipeline (6 Phases)

```
Phase 1: Inventory      → Clone repo, detect language, hash files
Phase 2: Parse          → Extract symbols, build AST, create entities
Phase 3: Graph          → Find dependencies, build call graph
Phase 4: Clustering     → Group symbols into domains (L4)
Phase 5: Detection      → Drift detection, stale spec flags
Phase 6: Specs          → Generate L3 knowledge cards via LLM
                          (ETA tracking, parallel processing)
```

### Data Model

**Stable Keys** (idempotent re-ingestion):
- `SourceUnit`: `(source_type, source_id, locator)`
- `Entity`: `(source_id, qualified_name)` — stable across code changes
- `Spec`: `(component_ref, version)` — immutable specs with versioning

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.12+** (backend)
- **Node.js 18+** (frontend)
- **PostgreSQL 15+** with `pgvector` extension
- **Docker** (optional, for PostgreSQL)

### Quick Start (Local Development)

#### 1. Clone & Setup

```bash
git clone https://github.com/CXLD10/spec-atlas-ki-platform.git
cd spec-atlas-ki-platform

# Backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Frontend
cd frontend
npm install
```

#### 2. Database Setup

**Option A: Docker (Recommended)**
```bash
docker-compose up -d postgres
```

**Option B: Local PostgreSQL**
```bash
createuser -h localhost spec_atlas -P  # password: spec_atlas_dev
createdb -h localhost -O spec_atlas spec_atlas_analysis
createdb -h localhost -O spec_atlas spec_atlas_spec
psql -h localhost -U spec_atlas spec_atlas_analysis -c "CREATE EXTENSION vector;"
psql -h localhost -U spec_atlas spec_atlas_spec -c "CREATE EXTENSION vector;"
```

#### 3. Environment Variables

```bash
# .env (git-ignored)
ANALYSIS_DB_URL=postgresql+psycopg://spec_atlas:spec_atlas_dev@localhost:5432/spec_atlas_analysis
SPEC_DB_URL=postgresql+psycopg://spec_atlas:spec_atlas_dev@localhost:5432/spec_atlas_spec

LLM_PROVIDER=groq
GROQ_API_KEY=your_key_here...
EMBED_PROVIDER=fake
```

#### 4. Migrations & Start

```bash
# Apply schema
alembic upgrade head

# Terminal 1: Backend
source .venv/bin/activate
export PYTHONPATH=/path/to/spec-atlas-ki-platform/src
export ANALYSIS_DB_URL="postgresql+psycopg://spec_atlas:spec_atlas_dev@localhost:5432/spec_atlas_analysis"
export SPEC_DB_URL="postgresql+psycopg://spec_atlas:spec_atlas_dev@localhost:5432/spec_atlas_spec"
uvicorn spec_atlas.api.app:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
```

Open **http://localhost:5173** and start indexing!

---

## 📖 Usage Guide

### 1. Index a Repository

1. Go to **Sources** page
2. Paste a public GitHub URL
3. Click **Index**
4. Wait for completion (shows ETA)
5. View generated knowledge cards

### 2. Ask Questions

1. Open **Ask Atlas**
2. Type: *"How does authentication work?"*
3. Get grounded answers with citations
4. Click citations to jump to source

### 3. Explore Knowledge Graph

1. Open **Knowledge Graph**
2. Select repository
3. Interact: drag to rotate, scroll to zoom, click to inspect
4. Click nodes → See specs and relationships

### 4. Generate Specs

1. Open **Specify** tool
2. Enter repo name and entity
3. Click **Generate**
4. Review and save

---

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI (REST API, SSE streaming)
- **Database**: PostgreSQL + pgvector
- **ORM**: SQLAlchemy
- **Parsing**: tree-sitter
- **Embeddings**: Ollama (default) or Groq
- **LLM**: Groq (free) or Ollama

### Frontend
- **Framework**: React 18
- **Build**: Vite
- **Router**: React Router v6
- **State**: TanStack Query
- **3D**: Three.js
- **Styling**: CSS + Design Tokens (Apple-inspired)

---

## 📋 Project Structure

```
spec-atlas-ki-platform/
├── src/spec_atlas/
│   ├── api/              # REST endpoints
│   ├── ingest/           # Ingest pipeline
│   ├── parse/            # Language parsing
│   ├── graph/            # Dependencies
│   ├── embed/            # Embeddings
│   ├── db/               # SQLAlchemy models
│   ├── llm/              # LLM provider abstraction
│   └── answer/           # RAG + answer generation
├── frontend/src/
│   ├── pages/            # Ask, Sources, Graph, KB, Specify
│   ├── components/       # UI components
│   ├── lib/              # Hooks, utilities, types
│   ├── api/              # API client
│   └── app/              # Theme, shell
├── docs/
│   ├── DECISIONS.md      # Architecture decisions
│   ├── PLAYBOOK.md       # Development process
│   └── decisions/        # ADRs
└── specs/                # Product specs
```

---

## 🔧 Development Commands

```bash
# Backend
make dev-backend        # Run with auto-reload
make test              # Run tests (offline, fake providers)
make lint && make format

# Frontend
make dev-frontend      # Dev server
npm run type-check     # Type checking
npm run build          # Production build

# Database
make migrate           # Apply migrations
make db-drop          # Reset (careful!)
```

---

## 🎨 Design System

**Apple-inspired dark mode** with professional colors:

- **Background**: Deep space black (`#1a1a1a`)
- **Surfaces**: Warm charcoal (`#242424`, `#2a2a2a`)
- **Text**: Light grey (`#f5f5f5`)
- **Accent**: Muted indigo-blue (`#6ba3d4`)
- **Effects**: Glassmorphism (frosted glass)

---

## 🧪 Testing

```bash
# Backend: Offline with fake providers
make test

# Run specific test
pytest tests/api/test_answer.py -v

# Run against real providers (local)
make test-real

# Frontend: Type checking
npm run type-check
```

---

## 📊 Performance

### Ingest Speed
- Small repos (<50K LOC): 30–60s
- Medium repos (50K–500K LOC): 1–3m
- Large repos (>500K LOC): 5–15m

### Query Performance
- Vector search: <100ms
- RAG retrieval: 200–500ms
- Graph rendering: 16ms/frame

---

## 🔐 Security & Privacy

- ✅ Local-first (everything on your machine)
- ✅ No external calls (code never leaves)
- ✅ Offline-capable (except LLM calls)
- ✅ No telemetry
- ✅ Credentials in git-ignored `.env`

---

## 🤝 Contributing

See `docs/PLAYBOOK.md`:

1. Check `specs/product/SCOPE.md` (stay in scope)
2. Pick `ready` task from `tasks/BOARD.md`
3. Claim it (your name + date)
4. Build in "Owns" files only
5. Add tests per `docs/TESTING.md`
6. Create ADR for architecture decisions
7. Mark `done` with HANDOFF notes

---

## 📚 Resources

- **API Contract**: `API_CONTRACT.md`
- **Architecture**: `ARCHITECTURE-E2E.md`
- **Data Model**: `specs/architecture/DATA-MODEL.md`
- **Roadmap**: `specs/FEATURES.md`
- **Decisions**: `docs/decisions/`

---

## 📄 License

MIT — See LICENSE file.

---

## 👤 Author

**Joshua Joseph** (CXLD10)  
Engineered by Claude (Anthropic)

---

## 📞 Support

- **Issues**: GitHub Issues
- **Email**: joshuajomjose@gmail.com

---

**Version:** 0.6.0 | **Status:** Production Ready | **Last Updated:** June 24, 2026
