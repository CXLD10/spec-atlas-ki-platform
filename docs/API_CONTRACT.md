# API Contract — Spec-Atlas

**Base URL:** `http://localhost:8000` (dev) · `https://your-backend.railway.app` (prod)  
**Auth:** None — session-scoped via cookie (`session_id` set automatically on first request)  
**Format:** All request/response bodies are JSON unless noted

---

## Health

### `GET /health`
Returns service + dependency status.

**Response (200):**
```json
{
  "status": "ok",
  "analysis_db": { "status": "ok" },
  "spec_db": { "status": "ok" },
  "llm": { "status": "ok", "provider": "groq", "model": "llama-3.1-8b-instant" },
  "embed": { "status": "ok", "provider": "fake" }
}
```

---

## Ingest

### `POST /api/ingest`
Queue a code repository for ingestion.

**Request:**
```json
{ "repo_url": "https://github.com/user/repo" }
```

**Response (200):**
```json
{
  "job_id": "abc123",
  "status": "queued",
  "progress_pct": 0,
  "repo_url": "https://github.com/user/repo"
}
```

### `GET /api/ingest/{job_id}`
Poll ingestion job status.

**Response (200):**
```json
{
  "job_id": "abc123",
  "status": "in_progress",
  "progress_pct": 45,
  "phase": "spec_generation",
  "error": null
}
```
Status values: `queued` · `in_progress` · `done` · `failed`

### `POST /api/documents`
Upload a document (PDF, Markdown, Excel) for ingestion. Multipart form.

**Form fields:**
- `file` — the file
- `repo` — target repo identifier (default: `"default"`)

---

## Ask / Q&A

### `POST /api/ask`
Ask a question; returns a grounded answer with citations.

**Request:**
```json
{ "question": "How does authentication work?", "repo": "default" }
```

**Response (200):**
```json
{
  "answer": "Authentication is handled by...",
  "claims": [
    { "text": "AuthService manages sessions", "source": "auth/service.py:42" }
  ],
  "confidence": 0.87,
  "strategy": "vector_search",
  "status": "success"
}
```
Status values: `success` · `empty_db` · `no_results` · `error`

### `POST /api/ask/stream`
SSE streaming variant — same request body as `/api/ask`.

Emits:
```
data: {"type":"token","token":" word"}

data: {"type":"done","answer":"...","claims":[...],"confidence":0.87,"strategy":"...","status":"success"}
```
On error:
```
data: {"type":"error","message":"..."}
```

---

## Graph

### `GET /api/graph/nodes`
Fetch all nodes for a repo.

**Query params:** `repo` (default: `"default"`)

**Response (200):**
```json
{
  "nodes": [
    {
      "id": "uuid",
      "kind": "function",
      "name": "parse_symbols",
      "qualified_name": "spec_atlas.parse.parser.parse_symbols",
      "layer": "L1",
      "file_path": "src/spec_atlas/parse/parser.py",
      "start_line": 42,
      "end_line": 80
    }
  ]
}
```

### `GET /api/graph/edges`
Fetch all edges for a repo.

**Query params:** `repo` (default: `"default"`)

**Response (200):**
```json
{
  "edges": [
    { "src": "uuid-a", "dst": "uuid-b", "kind": "calls", "confidence": 0.95 }
  ]
}
```

---

## Groups

### `GET /api/groups`
Fetch the group tree (L3/L4 clustering).

**Query params:** `repo` (default: `"default"`)

**Response (200):**
```json
{
  "groups": [
    {
      "id": "uuid",
      "path": "spec_atlas/ingest",
      "title": "Ingest Pipeline",
      "level": 2,
      "summary_md": "Handles multi-phase repo ingestion...",
      "parent_id": null
    }
  ]
}
```

---

## Specs

### `GET /api/specs/{component_ref}`
Fetch a generated spec by component reference.

**Query params:** `repo` (default: `"default"`)

**Response (200):**
```json
{
  "spec_id": "uuid",
  "node_id": "uuid",
  "component_ref": "AuthService",
  "content": "# AuthService\n\n...",
  "version": 1,
  "status": "generated",
  "citations": [{ "file": "auth/service.py", "start_line": 10, "end_line": 80 }],
  "created_at": "2026-06-24T10:00:00Z"
}
```

### `POST /api/specs/generate/{component_ref}`
Trigger spec generation for a component.

**Query params:** `repo` (default: `"default"`)

**Response (200):** Same shape as `GET /api/specs/{component_ref}`

### `POST /api/specs/{component_ref}/verify`
Mark a spec as verified.

**Query params:** `repo`, `version`

---

## Sources

### `GET /api/sources`
List all indexed sources (repos + documents).

**Query params:** `repo` (default: `"default"`)

**Response (200):**
```json
{
  "sources": [
    { "id": "uuid", "name": "my-repo", "type": "code", "status": "done" }
  ]
}
```

### `DELETE /api/sources/{source_id}`
Delete a source and its associated data.

---

## Knowledge Base

### `GET /api/kb`
List all knowledge cards.

**Query params:** `repo` (default: `"default"`)

### `GET /api/kb/{ref}`
Fetch a single knowledge card.

---

## MCP Bridge

### `POST /api/mcp/call`
Call an MCP tool by name.

**Request:**
```json
{ "tool": "search_knowledge", "args": { "query": "How does auth work?", "repo": "default" } }
```

**Available tools:**
| Tool | Args | Description |
|------|------|-------------|
| `search_knowledge` | `query`, `repo?` | Vector search + semantic answer |
| `ask_question` | `question`, `repo?` | Full RAG pipeline answer |
| `get_spec` | `component_ref`, `repo?` | Fetch a component spec |
| `get_graph` | `repo?` | Fetch graph nodes and edges |

**Response (200):**
```json
{ "result": { ... } }
```

---

## Reports

### `GET /api/reports`
Fetch system analytics and usage summary.

---

## Docs

### `GET /api/docs`
List ingested documentation sources.

---

## Error Format

All errors return:
```json
{ "detail": "Human-readable error message" }
```

Common status codes: `400` bad request · `404` not found · `422` validation error · `500` server error · `503` service unavailable (DB not configured)
