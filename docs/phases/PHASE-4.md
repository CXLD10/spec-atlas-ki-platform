# Phase 4 — Agents & real-time

**Effort:** M · **Depends on:** Phases 0–3 · **Audit items:** §3.6, §3.7, §3.8, §3.19, §3.21

## Objective
The MCP server actually works: handlers reuse the real retrieval/spec/graph code paths, `get_graph` returns real data, there's a runnable published entrypoint, and the `/mcp` Console calls it for real. Ask gains genuine SSE streaming.

---

## Tasks

### 4.1 — Rewrite `MCPHandlers` over real code paths *(Dev B, M)* — §3.6, §3.7
- `mcp/handlers.py:43-88,185-225` call non-existent `VectorSearch.search`/`TreeDescent.descend` (those are **static** with different signatures — `retrieve/search.py:20`, `retrieve/descent.py:32`) and will raise at runtime; `ask_question` hardcodes `confidence: 1.0`. The legacy `MCPToolHandlers` (`:229-275`) and server fallback branches (`mcp/server.py:228-274`) are pure stubs.
- Rewrite `MCPHandlers` to call the **same code paths as `AnswerRouter`** (`api/answer.py`) and reuse `SpecStore`/`GraphStore`.
- Implement `get_graph` (`handlers.py:146-183`, currently always `nodes:[],edges:[]`) by querying `GraphStore`/`Group` for the requested layer and serializing.
- Remove the stub branches; real confidence from Phase 0.4.

### 4.2 — MCP entrypoint + package *(Dev B, M)* — §3.8, §3.19
- Add a `spec-atlas-mcp` console script in `pyproject.toml` that builds the server with the real `MCPHandlers` over configured sessions.
- Make `uvx spec-atlas-mcp` (advertised in `MCPServer.tsx:31-41`) actually runnable — or update the UI to the real command if the name changes.
- **Console:** `components/mcp/Console.tsx:66-133` returns hardcoded `mockResponses` after an 800ms timeout. Replace with a real HTTP bridge to the MCP tools (or the equivalent REST endpoints) and render real responses. `MCPServer.tsx` health must reflect reality, not always "OK".

### 4.3 — SSE streaming Ask *(Dev A + Dev B, M)* — §3.21
- `pages/Ask.tsx:76,95` fakes streaming via `answer.length*20ms` reveal. Add a real SSE/streaming `/api/ask` variant (the prompt `docs/frontend/prompts/PROMPT-03-real-indexing-sse.md` already anticipates this) and consume it token-by-token.

---

## Seed / fixtures
Reuse the seeded repo + documents. MCP tests construct the server over the seeded sessions (pattern already in `tests/mcp/`).

## Backend tests
```bash
pytest -q tests/mcp                       # handlers now real, not stubs
pytest -q tests/api/test_answer_stream.py # new SSE endpoint
pytest -q
```
New tests:
- `test_mcp_search_knowledge_real` — returns real retrieval results (not a raise, not a stub string).
- `test_mcp_ask_question_real_confidence` — confidence is genuine, not `1.0`.
- `test_mcp_get_graph_returns_layer` — non-empty nodes/edges for a seeded layer.
- `test_mcp_entrypoint_boots` — console script constructs a working server.
- `test_ask_stream_emits_tokens` — SSE yields incremental chunks then a final payload.

## Frontend integration checks
1. **/mcp Console** "Playground" runs a tool and shows a **real** response (no 800ms canned `mockResponses`); health reflects actual server state.
2. The advertised `uvx spec-atlas-mcp` command starts a server that answers all four tools.
3. **Ask** streams tokens progressively via SSE (verify in network tab: a streaming response, not a single blob revealed by timer).

## Definition of Done
- All four MCP tools return real, DB-backed results; `get_graph` populated; no stub branches remain.
- `spec-atlas-mcp` entrypoint runs; Console calls it for real; health honest.
- Ask uses real SSE streaming.
- Tests green; full suite green; CI offline.

## Commit checkpoint
```
feat(phase4): real MCP handlers + entrypoint, live Console, SSE streaming Ask
```
