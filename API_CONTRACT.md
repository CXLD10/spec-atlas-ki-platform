# API_CONTRACT.md — Spec-Atlas Backend API Specification

**Version**: 2.0 (Phase 0–4 scope)  
**Last Updated**: 2026-06-22  
**Status**: Living document; updated as phases progress

---

## Overview

Spec-Atlas exposes RESTful endpoints for ingest, graph exploration, spec generation, and retrieval. All endpoints use JSON; authentication via bearer token (config in .env).

**Base URL**: `http://localhost:8000/api` (dev) or `https://api.spec-atlas.com` (prod)

---

## Core Domains

### 1. Projects

#### `POST /projects`
Create a new project (repo or document collection).

**Request**:
```json
{
  "name": "my-repo",
  "description": "A Python FastAPI project",
  "repo_url": "https://github.com/user/my-repo.git",  // optional for code
  "language_hint": ["python", "typescript"]            // optional
}
```

**Response** (201):
```json
{
  "id": "proj_abc123",
  "name": "my-repo",
  "created_at": "2026-06-22T10:00:00Z",
  "status": "queued"
}
```

---

#### `GET /projects/{project_id}`
Fetch project metadata + ingest status.

**Response** (200):
```json
{
  "id": "proj_abc123",
  "name": "my-repo",
  "status": "ingesting",  // queued, ingesting, complete, failed
  "progress": 0.45,
  "ingest_phase": "spec_generation",
  "created_at": "2026-06-22T10:00:00Z",
  "completed_at": null,
  "error": null
}
```

---

#### `GET /projects`
List all projects.

**Response** (200):
```json
{
  "projects": [
    { "id": "proj_abc123", "name": "my-repo", "status": "complete" },
    { "id": "proj_def456", "name": "another-project", "status": "ingesting" }
  ]
}
```

---

### 2. Sources (Phase 1+)

#### `POST /projects/{project_id}/sources`
Add a source (code repo, PDF, Excel, Markdown file, Jira export, git history).

**Request**:
```json
{
  "type": "pdf",           // "code", "pdf", "excel", "markdown", "jira", "git_history"
  "name": "architecture.pdf",
  "file_or_url": "<binary PDF or URL>",
  "metadata": {
    "author": "Team",
    "pages": 42
  }
}
```

**Response** (201):
```json
{
  "source_id": "src_pdf_001",
  "type": "pdf",
  "name": "architecture.pdf",
  "status": "ingesting"
}
```

---

#### `GET /projects/{project_id}/sources`
List all sources in project.

**Response** (200):
```json
{
  "sources": [
    { "source_id": "src_code_001", "type": "code", "name": "my-repo" },
    { "source_id": "src_pdf_001", "type": "pdf", "name": "architecture.pdf" }
  ]
}
```

---

### 3. Graph API

#### `GET /projects/{project_id}/graph`
Fetch 3-layer graph (L1 code, L2 specs, L3 clusters).

**Query Parameters**:
- `layers`: comma-separated (default: "1,2,3")
- `node_filter`: optional (e.g., "kind=function")

**Response** (200):
```json
{
  "nodes": [
    {
      "id": "node_abc123",
      "kind": "module",          // module, class, function, spec, cluster
      "name": "ingest.parser",
      "qualified_name": "spec_atlas.ingest.parser",
      "layer": 1,
      "file_path": "src/spec_atlas/ingest/parser.py",
      "start_line": 10,
      "end_line": 50,
      "citations": {
        "file": "src/spec_atlas/ingest/parser.py",
        "start_line": 10,
        "end_line": 50
      }
    }
  ],
  "edges": [
    {
      "source_id": "node_abc123",
      "target_id": "node_def456",
      "kind": "imports",         // imports, calls, defines, inherits, clusters, cites
      "confidence": 0.95
    }
  ]
}
```

---

#### `POST /projects/{project_id}/graph/generate-spec`
Generate a spec for a selected node (LLM-powered).

**Request**:
```json
{
  "node_id": "node_abc123",
  "include_context": true,   // include related nodes
  "output_format": "markdown" // markdown, json
}
```

**Response** (202 or 200):
```json
{
  "spec_id": "spec_xyz789",
  "node_id": "node_abc123",
  "content": "# Parser Module\n\n...",
  "status": "generated",
  "citations": [
    {
      "file": "src/spec_atlas/ingest/parser.py",
      "start_line": 10,
      "end_line": 50
    }
  ],
  "generated_at": "2026-06-22T10:05:00Z"
}
```

---

### 4. Retrieval & Ask

#### `POST /projects/{project_id}/ask`
Ask a question about the project; retrieve relevant specs/code + generate answer.

**Request**:
```json
{
  "query": "How does the ingest pipeline handle different file types?",
  "include_memory": true,  // retrieve from conversation memory (Phase 3+)
  "sources": ["code", "pdf"],  // filter by source type (default: all)
  "temperature": 0.7
}
```

**Response** (200):
```json
{
  "answer_id": "ans_2026062210_001",
  "query": "How does the ingest pipeline handle different file types?",
  "answer": "The ingest pipeline uses a SourceUnit abstraction...",
  "citations": [
    {
      "source": "code",
      "file": "src/spec_atlas/ingest/resolver.py",
      "start_line": 42,
      "end_line": 65,
      "snippet": "def resolve_language(...)"
    },
    {
      "source": "pdf",
      "name": "architecture.pdf",
      "page": 15,
      "bbox": [0.1, 0.2, 0.9, 0.8],
      "text": "The pipeline detects MIME type..."
    }
  ],
  "memory_context": [
    { "fact": "project uses Python + TypeScript", "relevance": 0.8 }
  ],
  "latency_ms": 450
}
```

---

#### `GET /projects/{project_id}/conversations`
List conversation history (Phase 3+).

**Response** (200):
```json
{
  "conversations": [
    {
      "id": "conv_001",
      "created_at": "2026-06-22T09:00:00Z",
      "turns": 3,
      "memory_facts": 5
    }
  ]
}
```

---

#### `GET /projects/{project_id}/conversations/{conversation_id}`
Fetch a conversation + memory facts.

**Response** (200):
```json
{
  "id": "conv_001",
  "turns": [
    {
      "query": "What is the entry point?",
      "answer": "...",
      "citations": [...]
    }
  ],
  "memory_facts": [
    {
      "fact": "main.py is the entry point",
      "sources": ["code"],
      "relevance": 0.95
    }
  ]
}
```

---

### 5. Specs (Phase 2+)

#### `GET /projects/{project_id}/specs`
List all generated specs in the project.

**Response** (200):
```json
{
  "specs": [
    {
      "spec_id": "spec_xyz789",
      "node_id": "node_abc123",
      "title": "Parser Module",
      "version": 1,
      "created_at": "2026-06-22T10:05:00Z",
      "citations": [...]
    }
  ]
}
```

---

#### `GET /projects/{project_id}/specs/{spec_id}`
Fetch a specific spec.

**Response** (200):
```json
{
  "spec_id": "spec_xyz789",
  "node_id": "node_abc123",
  "content": "# Parser Module\n\n...",
  "version": 1,
  "citations": [...],
  "created_at": "2026-06-22T10:05:00Z"
}
```

---

### 6. MCP Server (Phase 3+, Stretch)

#### `POST /mcp/ask`
Expose ask endpoint via MCP for external agents.

**Request** (via MCP):
```json
{
  "project_id": "proj_abc123",
  "query": "...",
  "memory": true
}
```

**Response**:
```json
{
  "answer": "...",
  "citations": [...]
}
```

---

## Error Responses

All endpoints return structured errors:

```json
{
  "error": "project_not_found",
  "message": "Project proj_xyz not found",
  "status": 404,
  "trace_id": "trace_abc123"  // for debugging
}
```

### Common Errors
- `400`: Invalid request (missing field, bad JSON)
- `401`: Unauthorized (invalid or missing token)
- `404`: Resource not found
- `409`: Conflict (e.g., project already ingesting)
- `500`: Server error

---

## Async Workflows

Long-running operations (ingest, spec generation) return `202 Accepted` with a location header. Poll the status endpoint:

```
POST /projects
  → 202 Accepted
  → Location: /projects/proj_abc123
  
GET /projects/proj_abc123
  → 200 OK (status: "ingesting" or "complete")
```

---

## Authentication

All requests (except health check) require a bearer token:

```
Authorization: Bearer <token>
```

Token is loaded from `SPEC_ATLAS_API_TOKEN` (env var).

---

## Backwards Compatibility

- **v1.x**: Legacy endpoint (deprecated in v2.0)
- **v2.0**: Current (Phase 0–4 scope)

---

## Reference

- See `docs/frontend/architecture/API-CONTRACT.md` for frontend-specific field mappings
- See `specs/features/F-007-retrieval.md` for retrieval implementation details
- See `specs/features/F-010-specify.md` for spec generation flow
