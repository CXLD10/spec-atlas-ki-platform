# MCP Server Usage Guide

## Overview

The Spec-Atlas MCP (Model Context Protocol) server exposes spec/group retrieval as tools for AI agents (Claude Code, Codex, etc.). Agents can call tools like `search`, `get_spec`, and `get_group` mid-conversation to fetch real spec data instead of guessing.

## Installation

```bash
pip install mcp httpx
```

## Starting the MCP Server

### Option 1: Standalone (stdio transport)

```python
import asyncio
from spec_atlas.mcp.server import SpecAtlasMCPServer

async def main():
    server = SpecAtlasMCPServer(backend_url="http://localhost:8000")
    await server.run()

asyncio.run(main())
```

### Option 2: Claude Code Integration

Add to your Claude Code settings or MCP configuration:

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

## Available Tools

### 1. `search`

Search specs and groups by natural language query.

**Input:**
```json
{
  "query": "How does user authentication work?",
  "repo": "default"
}
```

**Output:**
```json
{
  "answer": "The auth module handles user login via the AuthService class...",
  "claims": [
    {
      "claim": "AuthService manages authentication",
      "source": "auth.py:42"
    }
  ],
  "confidence": 0.85,
  "strategy": "vector_search"
}
```

---

### 2. `get_spec`

Fetch a specific component's spec by reference.

**Input:**
```json
{
  "component_ref": "AuthService",
  "repo": "default"
}
```

**Output:**
```json
{
  "component_ref": "AuthService",
  "spec": {
    "purpose": "Handles user authentication and session management",
    "inputs": [...],
    "outputs": [...],
    "invariants": ["Tokens expire after 1 hour", "..."]
  },
  "status": "verified",
  "version": 1,
  "provenance": [
    {
      "file": "auth/service.py",
      "start_line": 42,
      "end_line": 150
    }
  ]
}
```

---

### 3. `get_group`

Fetch a group summary and its members.

**Input:**
```json
{
  "group_path": "auth/tokens",
  "repo": "default"
}
```

**Output:**
```json
{
  "group_path": "auth/tokens",
  "title": "Token Management",
  "summary": "Handles JWT token generation, validation, and expiration...",
  "children": ["auth/tokens/jwt", "auth/tokens/refresh"],
  "member_specs": ["TokenService", "RefreshTokenHandler"],
  "level": 2
}
```

---

### 4. `list_stale_specs`

List specs that are marked stale (source code has changed).

**Input:**
```json
{
  "repo": "default"
}
```

**Output:**
```json
{
  "repo": "default",
  "stale_specs": [
    {
      "component_ref": "OldAuthService",
      "staleness_detected_at": "2026-06-19T12:00:00Z"
    }
  ],
  "count": 1
}
```

---

## Example Agent Usage

### Claude Code Example

```python
# In a Claude Code conversation, you might ask:
user: "How does this repo handle authentication?"

# Claude Code calls:
# Tool: search
# Input: { "query": "How does this repo handle authentication?" }
# Result: Answer with cited specs and provenance

# Then follow up:
user: "Show me the AuthService spec in detail"

# Claude Code calls:
# Tool: get_spec
# Input: { "component_ref": "AuthService" }
# Result: Full spec with inputs, outputs, invariants
```

## Backend Requirements

The MCP server expects a running Spec-Atlas backend with these endpoints:

```
POST /api/ask                { question, repo? }
GET  /api/specs/{ref}        { repo? }
GET  /api/groups             { repo?, path? }
GET  /api/specs              { repo?, status? }
```

These are wired by **F-009** (backend wiring tasks T-009.1–T-009.3).

## Configuration

### Environment Variables

- `SPEC_ATLAS_BACKEND`: Backend URL (default: `http://localhost:8000`)
- `MCP_SERVER_LOGLEVEL`: Logging level (default: `INFO`)

### Custom Backend URL

```python
from spec_atlas.mcp.server import SpecAtlasMCPServer

server = SpecAtlasMCPServer(backend_url="http://prod-api.example.com:8080")
```

## Testing Locally

Run the MCP server and test with direct calls:

```python
import asyncio
from spec_atlas.mcp.server import SpecAtlasMCPServer

async def test():
    server = SpecAtlasMCPServer()
    
    # Test search
    result = await server._search_handler("How does auth work?", "default")
    print(f"Search result: {result}")
    
    # Test get_spec
    result = await server._get_spec_handler("AuthService", "default")
    print(f"Spec result: {result}")

asyncio.run(test())
```

## Tool Schemas (Stable)

All tool schemas are frozen in `server.py` once shipped. Changes require version bumps or new tools.

```
Tool Name    | Input Schema | Output Format | Stability |
|-----------|-------------|---------------|-----------|
| search | query, repo? | answer, claims, confidence, strategy | Stable v1 |
| get_spec | component_ref, repo? | spec, status, version, provenance | Stable v1 |
| get_group | group_path, repo? | summary, children, member_specs, level | Stable v1 |
| list_stale_specs | repo? | stale_specs[], count | Stable v1 |
```

## Troubleshooting

### Tool call times out

- Check backend is running: `curl http://localhost:8000/health`
- Increase timeout: pass `timeout=60.0` to `MCPToolHandlers`

### Tool returns "error"

- Check logs for HTTP error details
- Verify backend has the repo indexed
- Confirm tool input schema matches (see above)

### "Spec not found" / "Group not found"

- Run ingest: `POST /api/ingest` with repo URL
- Wait for ingest to complete
- Retry tool call

## Next Steps

- Integrate with Claude Code settings
- Wire backend endpoints (F-009)
- Deploy MCP server alongside backend
- Test with agents in production repos

---

**Phase:** 5 (Agents)  
**Status:** Scaffold + handlers implemented, wired to backend stubs (await F-009)  
**Next:** F-009 backend wiring (T-009.1–T-009.3) to connect tools to real services
