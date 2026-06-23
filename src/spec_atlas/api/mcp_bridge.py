"""REST bridge: POST /api/mcp/call → MCPHandlers.

Lets the Console UI (and any HTTP client) call MCP tools without needing the
stdio MCP transport.  Each call opens fresh sessions from app state and closes
them when the response is sent, following the same pattern as other routers.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mcp", tags=["mcp"])


class MCPCallRequest(BaseModel):
    tool: str
    args: dict = {}


@router.post("/call")
async def mcp_call(body: MCPCallRequest, request: Request) -> dict:
    """Invoke an MCP tool by name with the given arguments.

    Supported tools: ``search_knowledge``, ``get_spec``, ``get_graph``,
    ``ask_question``.  Arguments are passed verbatim; extra keys are ignored.
    """
    a_factory = request.app.state.analysis_session_factory
    if not a_factory:
        raise HTTPException(status_code=503, detail="Analysis database not configured")

    from spec_atlas.mcp.handlers import MCPHandlers

    a_session = a_factory()
    s_factory = request.app.state.spec_session_factory
    s_session = s_factory() if s_factory else None
    embed = getattr(request.app.state, "embedding_provider", None)
    llm = getattr(request.app.state, "llm_provider", None)

    try:
        handlers = MCPHandlers(s_session, a_session, embed, llm)
        tool = body.tool
        args = body.args

        if tool == "search_knowledge":
            return await handlers.search_knowledge(
                args.get("query", ""),
                args.get("repo", "default"),
                int(args.get("limit", 10)),
            )
        elif tool == "get_spec":
            return await handlers.get_spec(
                args.get("component_ref", ""),
                args.get("repo", "default"),
                args.get("version"),
            )
        elif tool == "get_graph":
            return await handlers.get_graph(
                args.get("repo", "default"),
                args.get("layer", "spec"),
                int(args.get("limit", 100)),
            )
        elif tool == "ask_question":
            return await handlers.ask_question(
                args.get("question", ""),
                args.get("repo", "default"),
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {tool!r}")
    finally:
        a_session.close()
        if s_session:
            s_session.close()
