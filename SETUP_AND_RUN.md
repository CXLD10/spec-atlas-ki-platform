# Spec-Atlas: Complete Setup & Run Guide

## Prerequisites Check
```bash
# Verify you have:
- Docker & Docker Compose installed
- Python 3.12+
- npm/node (for frontend)
```

## Step 1: Start Databases (FIRST - Required for backend)

```bash
cd /home/cxld/projects/spec-atlas-ki-platform

# Start PostgreSQL with pgvector (via Docker)
docker-compose up -d

# Wait for health check (10-15 seconds)
sleep 15

# Verify databases are running
docker-compose ps
# Should show: spec-atlas-postgres and spec-atlas-api both "healthy"

# Check database connectivity
curl http://localhost:8000/health
# Should return: {"status":"ok","analysis_db":{"status":"ok"},...}
```

## Step 2: Install Backend Dependencies

```bash
cd /home/cxld/projects/spec-atlas-ki-platform

# Create/activate venv (if not already done)
uv venv --python 3.12 .venv
source .venv/bin/activate

# Install package with dev dependencies
uv pip install -e ".[dev]"
```

## Step 3: Set Environment Variables

```bash
# File: /home/cxld/projects/spec-atlas-ki-platform/.env
# (Already configured with correct values)

ANALYSIS_DB_URL=postgresql+psycopg://spec_atlas:spec_atlas_dev@localhost:5432/spec_atlas_analysis
SPEC_DB_URL=postgresql+psycopg://spec_atlas:spec_atlas_dev@localhost:5432/spec_atlas_spec
LLM_PROVIDER=groq
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.1-8b-instant
EMBED_PROVIDER=fake
EMBED_DIM=384
```

## Step 4: Run Backend (Terminal 1)

```bash
cd /home/cxld/projects/spec-atlas-ki-platform

# DO NOT use docker-compose spec-atlas service - use local uvicorn instead
# (Docker version has issues with localhost:5432 connection)

# Start backend with auto-reload
make dev

# Expected output:
# INFO:     Uvicorn running on http://127.0.0.1:8000
# INFO:     Application startup complete
```

**✅ Backend running on:** `http://localhost:8000`

## Step 5: Install & Run Frontend (Terminal 2)

```bash
cd /home/cxld/projects/spec-atlas-ki-platform/frontend

# Install dependencies
npm install

# Start dev server
npm run dev

# Expected output:
# VITE v5.0.0  ready in XX ms
# ➜  Local:   http://localhost:5173/
```

**✅ Frontend running on:** `http://localhost:5173`

## Step 6: Verify Everything Works

### Backend Health Check
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "analysis_db": {"status": "ok"},
  "spec_db": {"status": "ok"},
  "llm": {"status": "ok", "provider": "groq", "model": "llama-3.1-8b-instant"},
  "embed": {"status": "ok", "provider": "fake"}
}
```

### Frontend Access
```bash
# Open browser
open http://localhost:5173
# or
curl http://localhost:5173
```

## Step 7: Test Ingest Pipeline

```bash
# Index a repository
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"repo_url":"https://github.com/anthropics/anthropic-sdk-python"}'

# Expected response:
# {"job_id":"...", "status":"queued", "progress":0, ...}

# Monitor progress
JOB_ID="..." # from response above
curl http://localhost:8000/api/ingest/$JOB_ID

# Watch progress increase: 0% → 40% → 75% → 80% → 85% → 88% → 96% → 100%
# (With the Groq JSON mode fix, Phase 6 should now complete successfully)
```

## Troubleshooting

### ❌ Backend says "database not configured"
```bash
# Check if PostgreSQL is running
docker-compose ps
# Should show spec-atlas-postgres as "Up"

# If not running:
docker-compose up -d
sleep 15
curl http://localhost:8000/health
```

### ❌ "Connection refused on port 5432"
```bash
# Database not started. Do Step 1 first
docker-compose up -d
```

### ❌ Port 5173 (Frontend) already in use
```bash
# Kill existing process
lsof -i :5173 | grep LISTEN | awk '{print $2}' | xargs kill -9
# Then restart: npm run dev
```

### ❌ Port 8000 (Backend) already in use
```bash
# Kill existing process
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9
# Then restart: make dev
```

## Complete Clean Restart (Nuclear Option)

```bash
# Stop everything
pkill -f "uvicorn\|npm\|node" || true
docker-compose down -v  # -v removes volumes (data loss!)
sleep 5

# Start fresh
docker-compose up -d
sleep 15
cd /home/cxld/projects/spec-atlas-ki-platform && make dev &
cd /home/cxld/projects/spec-atlas-ki-platform/frontend && npm run dev &
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Your Browser                             │
│                   localhost:5173                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ HTTP (React + Vite)
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                   Frontend (React)                            │
│        src/pages/*.tsx + components + hooks                  │
│                 Runs on npm run dev                          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ REST API (JSON)
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                   Backend (FastAPI)                          │
│         src/spec_atlas/api/*.py                             │
│         Runs on make dev (uvicorn)                          │
│              localhost:8000                                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┴──────────────────┐
        │                                     │
        ▼                                     ▼
    ┌────────────┐                    ┌────────────┐
    │ PostgreSQL │                    │  LLM       │
    │  (Analysis)│                    │ (Groq API) │
    │            │                    │            │
    │ :5432      │                    │  Remote    │
    └────────────┘                    └────────────┘
        ▲
        │
    ┌───────────┐
    │ PostgreSQL│
    │  (Specs)  │
    │           │
    │  :5432    │
    └───────────┘
```

## Recent Fixes Applied

All fixes are in the current codebase:

1. **Commit 6fa4663** — Input field styling (removed boxy highlight)
2. **Commit afca72b** — URL validation bug fix
3. **Commit 3ab7a63** — Ask page scroll handling  
4. **Commit ebd70a4** — **Groq JSON mode fix** (CRITICAL for RAG)
   - Enables `response_format: {type: "json_object"}` 
   - Fixes spec generation failures
   - Enables proper vector search
   - Grounds answers in actual code specs

## Running Tests

```bash
# Backend tests (uses fake LLM/embedding)
LLM_PROVIDER=fake EMBED_PROVIDER=fake make test

# Expected: 499 tests passed
```

## Key Ports

- **5173** — Frontend (React dev server)
- **8000** — Backend API (FastAPI + uvicorn)
- **5432** — PostgreSQL (database, internal docker only)

## Useful Commands

```bash
# View backend logs
docker-compose logs spec-atlas-api -f

# View database logs
docker-compose logs spec-atlas-postgres -f

# Check what's running
ps aux | grep -E "uvicorn|npm|node" | grep -v grep

# Kill all node processes
pkill -f "node\|npm"

# Kill all Python processes
pkill -f "python.*uvicorn"
```

## Expected Behavior After Setup

1. ✅ Frontend loads on http://localhost:5173
2. ✅ Can paste GitHub/GitLab URLs to index repos
3. ✅ Ingest progresses: 0% → 100% (no longer stuck at 85%)
4. ✅ Can ask questions about indexed code
5. ✅ Answers include citations to actual specs
6. ✅ See Knowledge Cards with sources

---

**Status:** All systems ready. Backend is fully functional with Groq JSON mode enabled for proper RAG pipeline operation.
