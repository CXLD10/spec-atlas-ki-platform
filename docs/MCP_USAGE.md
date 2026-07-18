# MCP Server Usage Guide

## Overview

Spec-Atlas exposes an MCP (Model Context Protocol) bridge so AI agents (Claude Code, etc.) can query your knowledge base mid-conversation. Tools are called via `POST /api/mcp/call` — no separate process needed.

---

## Available Tools

### `search_knowledge`
Vector search over indexed code and documents.

**Input:**
```json
{ "query": "How does user authentication work?", "repo": "default" }
```

**Output:**
```json
{
  "results": [
    {
      "group": "auth/service",
      "summary": "AuthService handles login via session tokens...",
      "relevance": 0.91,
      "confidence": 0.91
    }
  ]
}
```

---

### `ask_question`
Full RAG pipeline — vector search + LLM answer with citations.

**Input:**
```json
{ "question": "How does authentication work?", "repo": "default" }
```

**Output:**
```json
{
  "answer": "Authentication is managed by AuthService...",
  "claims": [
    { "text": "AuthService manages sessions", "source": "auth/service.py:42" }
  ],
  "confidence": 0.87,
  "strategy": "vector_search",
  "status": "success"
}
```

---

### `get_spec`
Fetch a specific component's spec by reference.

**Input:**
```json
{ "component_ref": "AuthService", "repo": "default" }
```

**Output:**
```json
{
  "component_ref": "AuthService",
  "content": "# AuthService\n\n...",
  "status": "generated",
  "version": 1,
  "citations": [{ "file": "auth/service.py", "start_line": 42, "end_line": 150 }]
}
```

---

### `get_graph`
Fetch graph nodes and edges for a repo.

**Input:**
```json
{ "repo": "default" }
```

**Output:**
```json
{
  "nodes": [...],
  "edges": [...]
}
```

---

## Calling Tools (HTTP)

All tools go through one endpoint:

```bash
curl -X POST http://localhost:8000/api/mcp/call \
  -H "Content-Type: application/json" \
  -d '{"tool": "ask_question", "args": {"question": "How does auth work?"}}'
```

---

## Claude Code Integration

Add to your Claude Code MCP config (`~/.config/claude/mcp.json` or project `.claude/mcp.json`):

```json
{
  "mcpServers": {
    "spec-atlas": {
      "command": "python",
      "args": ["-m", "spec_atlas.mcp.server"],
      "env": {
        "SPEC_ATLAS_BACKEND": "http://localhost:8000"
      }
    }
  }
}
```

---

## Tool Stability

| Tool | Input | Stability |
|------|-------|-----------|
| `search_knowledge` | `query`, `repo?` | Stable |
| `ask_question` | `question`, `repo?` | Stable |
| `get_spec` | `component_ref`, `repo?` | Stable |
| `get_graph` | `repo?` | Stable |

---

## Troubleshooting

**Tool returns empty results:**
- Check the repo has been indexed: `GET /api/sources`
- Run ingest: `POST /api/ingest` with a repo URL

**Backend not reachable:**
- Verify it's running: `curl http://localhost:8000/health`

**"Spec not found":**
- Generate specs first via `POST /api/specs/generate/{component_ref}`

---

**Status:** HTTP bridge fully implemented at `POST /api/mcp/call`  
**Backend required:** Spec-Atlas backend running on port 8000
