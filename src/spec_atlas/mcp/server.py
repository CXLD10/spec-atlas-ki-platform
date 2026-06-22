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

    def __init__(self, backend_url: str = "http://localhost:8000"):
        """Initialize MCP server.

        Args:
            backend_url: Backend API base URL (e.g., http://localhost:8000)
        """
        self.backend_url = backend_url
        self.server = Server("spec-atlas")

        # Register tools
        self._register_tools()

    def _register_tools(self) -> None:
        """Register MCP tools with stable schemas."""
        # Tool 1: search
        self.server.register_tool(
            Tool(
                name="search",
                description="Search specs and groups by query. Routes query → retrieves context → generates answer.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "User question about the codebase",
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository identifier (e.g., github.com/user/repo)",
                            "default": "default",
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
                description="Fetch a spec by component reference.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "component_ref": {
                            "type": "string",
                            "description": "Component reference (e.g., AuthService)",
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository identifier",
                            "default": "default",
                        },
                    },
                    "required": ["component_ref"],
                },
            )
        )

        # Tool 3: get_group
        self.server.register_tool(
            Tool(
                name="get_group",
                description="Fetch a group summary and its members.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "group_path": {
                            "type": "string",
                            "description": "Group path (e.g., auth/tokens)",
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository identifier",
                            "default": "default",
                        },
                    },
                    "required": ["group_path"],
                },
            )
        )

        # Tool 4: list_stale_specs
        self.server.register_tool(
            Tool(
                name="list_stale_specs",
                description="List specs marked stale (source has changed).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repo": {
                            "type": "string",
                            "description": "Repository identifier",
                            "default": "default",
                        },
                    },
                    "required": [],
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
            if name == "search":
                return await self._search_handler(
                    arguments["query"], arguments.get("repo", "default")
                )
            elif name == "get_spec":
                return await self._get_spec_handler(
                    arguments["component_ref"], arguments.get("repo", "default")
                )
            elif name == "get_group":
                return await self._get_group_handler(
                    arguments["group_path"], arguments.get("repo", "default")
                )
            elif name == "list_stale_specs":
                return await self._list_stale_specs_handler(arguments.get("repo", "default"))
            else:
                return {"error": f"unknown tool: {name}"}
        except Exception as e:
            logger.error(f"Tool call error: {name}, {e}")
            return {"error": str(e), "code": "TOOL_CALL_FAILED"}

    async def _search_handler(self, query: str, repo: str) -> dict:
        """Search specs and groups.

        (Placeholder: will wire to F-007/F-008 pipeline)
        """
        return {
            "answer": "Search not yet implemented",
            "claims": [],
            "confidence": 0.0,
            "strategy": "vector_search",
            "repo": repo,
            "query": query,
        }

    async def _get_spec_handler(self, component_ref: str, repo: str) -> dict:
        """Fetch a spec by reference.

        (Placeholder: will wire to F-011 SpecStore)
        """
        return {
            "component_ref": component_ref,
            "repo": repo,
            "spec": None,
            "error": "Spec not found",
        }

    async def _get_group_handler(self, group_path: str, repo: str) -> dict:
        """Fetch a group and its members.

        (Placeholder: will wire to GroupClustering)
        """
        return {
            "group_path": group_path,
            "repo": repo,
            "group": None,
            "error": "Group not found",
        }

    async def _list_stale_specs_handler(self, repo: str) -> dict:
        """List stale specs.

        (Placeholder: will wire to drift detection, returns empty until F-014)
        """
        return {"repo": repo, "stale_specs": []}

    async def run(self) -> None:
        """Run the MCP server (stdio transport)."""
        async with self.server:
            logger.info("MCP server running on stdio")
            await self.server.wait_for_exit()
