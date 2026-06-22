"""MCP Server: Agent interface for Spec-Atlas."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Try to import mcp; if not available, create stub for testing
try:
    from mcp.server import Server
    from mcp.types import TextContent, Tool

    HAS_MCP = True
except ImportError:
    HAS_MCP = False

    # Stubs for testing without mcp SDK installed
    class Server:  # type: ignore
        """Stub Server for testing."""

        def __init__(self, name: str):
            self.name = name
            self.tools = {}

        def register_tool(self, tool: Any) -> None:
            """Stub tool registration."""
            pass

        def on_call_tool(self, handler: Any) -> Any:
            """Stub handler decorator."""
            return handler

        async def wait_for_exit(self) -> None:
            """Stub wait."""
            pass

        async def __aenter__(self) -> Any:
            return self

        async def __aexit__(self, *args: Any) -> None:
            pass

    class Tool:  # type: ignore
        """Stub Tool."""

        def __init__(self, name: str, description: str, inputSchema: dict):
            self.name = name
            self.description = description
            self.inputSchema = inputSchema

    class TextContent:  # type: ignore
        """Stub TextContent."""

        def __init__(self, text: str):
            self.text = text


class SpecAtlasMCPServer:
    """MCP server exposing Spec-Atlas retrieval + spec access to agents."""

    def __init__(self, handlers=None, backend_url: str = "http://localhost:8000"):
        """Initialize MCP server.

        Args:
            handlers: MCPHandlers instance (optional, for testing)
            backend_url: Backend API base URL (only used if handlers not provided)
        """
        self.backend_url = backend_url
        self.handlers = handlers
        self.server = Server("spec-atlas")

        # Register tools
        self._register_tools()

    def _register_tools(self) -> None:
        """Register MCP tools with stable schemas."""
        # Tool 1: search_knowledge
        self.server.register_tool(
            Tool(
                name="search_knowledge",
                description="Search the knowledge graph for relevant specs and sources",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query",
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository identifier",
                            "default": "default",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results to return",
                            "default": 10,
                        },
                    },
                    "required": ["query"],
                },
            )
        )

        # Tool 2: get_spec
        self.server.register_tool(
            Tool(
                name="get_spec",
                description="Retrieve a specification for a component",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "component_ref": {
                            "type": "string",
                            "description": "Component name",
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository identifier",
                            "default": "default",
                        },
                        "version": {
                            "type": "integer",
                            "description": "Spec version (optional)",
                        },
                    },
                    "required": ["component_ref"],
                },
            )
        )

        # Tool 3: get_graph
        self.server.register_tool(
            Tool(
                name="get_graph",
                description="Retrieve knowledge graph structure",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repo": {
                            "type": "string",
                            "description": "Repository identifier",
                            "default": "default",
                        },
                        "layer": {
                            "type": "string",
                            "description": "Layer: source, spec, group, or all",
                            "default": "spec",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum nodes to return",
                            "default": 100,
                        },
                    },
                    "required": [],
                },
            )
        )

        # Tool 4: ask_question
        self.server.register_tool(
            Tool(
                name="ask_question",
                description="Ask a question about the project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "User question",
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository identifier",
                            "default": "default",
                        },
                    },
                    "required": ["question"],
                },
            )
        )

        # Register tool call handler
        self.server.on_call_tool(self._handle_tool_call)

    async def _handle_tool_call(self, name: str, arguments: dict) -> Any:
        """Handle a tool call.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result (dict or error)
        """
        try:
            if name == "search_knowledge":
                return await self._search_knowledge_handler(
                    arguments["query"],
                    arguments.get("repo", "default"),
                    arguments.get("limit", 10),
                )
            elif name == "get_spec":
                return await self._get_spec_handler(
                    arguments["component_ref"],
                    arguments.get("repo", "default"),
                    arguments.get("version"),
                )
            elif name == "get_graph":
                return await self._get_graph_handler(
                    arguments.get("repo", "default"),
                    arguments.get("layer", "spec"),
                    arguments.get("limit", 100),
                )
            elif name == "ask_question":
                return await self._ask_question_handler(
                    arguments["question"], arguments.get("repo", "default")
                )
            else:
                return {"error": f"unknown tool: {name}"}
        except Exception as e:
            logger.error(f"Tool call error: {name}, {e}")
            return {"error": str(e), "code": "TOOL_CALL_FAILED"}

    async def _search_knowledge_handler(self, query: str, repo: str, limit: int) -> dict:
        """Search the knowledge graph."""
        if self.handlers:
            return await self.handlers.search_knowledge(query, repo, limit)
        return {
            "answer": "Search not yet implemented",
            "claims": [],
            "confidence": 0.0,
            "strategy": "vector_search",
            "repo": repo,
            "query": query,
        }

    async def _get_spec_handler(self, component_ref: str, repo: str, version: int | None) -> dict:
        """Fetch a spec by reference."""
        if self.handlers:
            return await self.handlers.get_spec(component_ref, repo, version)
        return {
            "component_ref": component_ref,
            "repo": repo,
            "spec": None,
            "error": "Spec not found",
        }

    async def _get_graph_handler(self, repo: str, layer: str, limit: int) -> dict:
        """Retrieve graph structure."""
        if self.handlers:
            return await self.handlers.get_graph(repo, layer, limit)
        return {
            "repo": repo,
            "layer": layer,
            "nodes": [],
            "edges": [],
            "node_count": 0,
            "edge_count": 0,
        }

    async def _ask_question_handler(self, question: str, repo: str) -> dict:
        """Ask a question about the project."""
        if self.handlers:
            return await self.handlers.ask_question(question, repo)
        return {
            "question": question,
            "answer": "",
            "claims": [],
            "confidence": 0.0,
        }

    async def run(self) -> None:
        """Run the MCP server (stdio transport)."""
        async with self.server:
            logger.info("MCP server running on stdio")
            await self.server.wait_for_exit()
