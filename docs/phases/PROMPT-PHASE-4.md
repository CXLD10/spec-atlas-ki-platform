# EXECUTION PROMPT — Phase 4: Agents & real-time

Repo: `CXLD10/spec-atlas-ki-platform`. Phases 0–3 done. Goal: the MCP server works for real (handlers reuse real code paths, `get_graph` populated, runnable entrypoint, Console calls it live) and Ask gets genuine SSE streaming. CI stays offline.

## Do these, in order

**1. Rewrite `MCPHandlers` (Dev B).** `mcp/handlers.py:43-88,185-225` instantiate `VectorSearch(...)`/`TreeDescent(...)` and call instance methods, but those are **static** with different signatures (`retrieve/search.py:20`, `retrieve/descent.py:32`) — they raise at runtime; `ask_question` hardcodes `confidence:1.0`. Legacy `MCPToolHandlers` (`:229-275`) and server branches (`mcp/server.py:228-274`) are stubs. Rewrite `MCPHandlers` to call the same paths as `AnswerRouter` (`api/answer.py`) and reuse `SpecStore`/`GraphStore`. Implement `get_graph` (`handlers.py:146-183`) by querying `GraphStore`/`Group` per layer. Remove stub branches; use real confidence.

**2. MCP entrypoint + package (Dev B).** Add a `spec-atlas-mcp` console script in `pyproject.toml` building the server with real `MCPHandlers` over configured sessions. Make `uvx spec-atlas-mcp` (advertised in `MCPServer.tsx:31-41`) actually runnable (or update the UI to the real command). Replace `components/mcp/Console.tsx:66-133` hardcoded `mockResponses` (800ms timeout) with a real HTTP bridge to the MCP tools (or equivalent REST). `MCPServer.tsx` health must reflect reality, not always "OK".

**3. SSE streaming Ask (Dev A + Dev B).** `pages/Ask.tsx:76,95` fakes streaming via `answer.length*20ms`. Add a real SSE/streaming `/api/ask` variant (see `docs/frontend/prompts/PROMPT-03-real-indexing-sse.md`) and consume it token-by-token.

## Seed
Reuse the seeded repo + documents; construct MCP test server over seeded sessions (pattern in `tests/mcp/`).

## Must pass before commit
```bash
pytest -q tests/mcp
pytest -q tests/api/test_answer_stream.py
pytest -q
cd frontend && npm run build && npm run test
```
Add: `test_mcp_search_knowledge_real`, `test_mcp_ask_question_real_confidence`, `test_mcp_get_graph_returns_layer`, `test_mcp_entrypoint_boots`, `test_ask_stream_emits_tokens`.

## Frontend checks (manual)
1. `/mcp` Console Playground runs a tool and shows a real response (no canned `mockResponses`); health is honest.
2. `uvx spec-atlas-mcp` starts a server answering all four tools.
3. Ask streams tokens progressively via SSE (network tab shows a streaming response, not a timer-revealed blob).

## STOP & COMMIT
```
feat(phase4): real MCP handlers + entrypoint, live Console, SSE streaming Ask
```
Report changed files, test output, confirmation all four tools return real data. Do not start Phase 5.
