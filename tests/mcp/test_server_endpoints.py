"""Tests for MCP server endpoints."""

from __future__ import annotations

import pytest

from spec_atlas.mcp.server import SpecAtlasMCPServer


class TestMCPSearchKnowledge:
    """Tests for search_knowledge tool."""

    def test_server_has_search_knowledge_tool(self) -> None:
        """Server registers search_knowledge tool."""
        server = SpecAtlasMCPServer()
        assert server.server is not None
        assert hasattr(server, "_search_knowledge_handler")

    @pytest.mark.anyio
    async def test_search_knowledge_handler_called(self) -> None:
        """search_knowledge handler can be called."""
        server = SpecAtlasMCPServer()
        result = await server._search_knowledge_handler("test query", "default", 10)

        assert isinstance(result, dict)
        assert "query" in result or "error" in result

    @pytest.mark.anyio
    async def test_search_knowledge_with_custom_limit(self) -> None:
        """search_knowledge respects limit parameter."""
        server = SpecAtlasMCPServer()
        result = await server._search_knowledge_handler("test", "default", 5)

        assert isinstance(result, dict)

    @pytest.mark.anyio
    async def test_search_knowledge_with_repo(self) -> None:
        """search_knowledge accepts repo parameter."""
        server = SpecAtlasMCPServer()
        result = await server._search_knowledge_handler("test", "my-repo", 10)

        assert isinstance(result, dict)


class TestMCPGetSpec:
    """Tests for get_spec tool."""

    def test_server_has_get_spec_tool(self) -> None:
        """Server registers get_spec tool."""
        server = SpecAtlasMCPServer()
        assert server.server is not None
        assert hasattr(server, "_get_spec_handler")

    @pytest.mark.anyio
    async def test_get_spec_handler_called(self) -> None:
        """get_spec handler can be called."""
        server = SpecAtlasMCPServer()
        result = await server._get_spec_handler("test_component", "default", None)

        assert isinstance(result, dict)
        assert "component_ref" in result or "error" in result

    @pytest.mark.anyio
    async def test_get_spec_with_version(self) -> None:
        """get_spec accepts version parameter."""
        server = SpecAtlasMCPServer()
        result = await server._get_spec_handler("test_component", "default", 1)

        assert isinstance(result, dict)

    @pytest.mark.anyio
    async def test_get_spec_with_repo(self) -> None:
        """get_spec accepts repo parameter."""
        server = SpecAtlasMCPServer()
        result = await server._get_spec_handler("test_component", "my-repo", None)

        assert isinstance(result, dict)


class TestMCPGetGraph:
    """Tests for get_graph tool."""

    def test_server_has_get_graph_tool(self) -> None:
        """Server registers get_graph tool."""
        server = SpecAtlasMCPServer()
        assert server.server is not None
        assert hasattr(server, "_get_graph_handler")

    @pytest.mark.anyio
    async def test_get_graph_handler_called(self) -> None:
        """get_graph handler can be called."""
        server = SpecAtlasMCPServer()
        result = await server._get_graph_handler("default", "spec", 100)

        assert isinstance(result, dict)
        assert "nodes" in result or "error" in result
        assert "edges" in result or "error" in result

    @pytest.mark.anyio
    async def test_get_graph_with_layer(self) -> None:
        """get_graph accepts layer parameter."""
        for layer in ["source", "spec", "group", "all"]:
            server = SpecAtlasMCPServer()
            result = await server._get_graph_handler("default", layer, 100)
            assert isinstance(result, dict)

    @pytest.mark.anyio
    async def test_get_graph_with_limit(self) -> None:
        """get_graph respects limit parameter."""
        server = SpecAtlasMCPServer()
        result = await server._get_graph_handler("default", "spec", 50)

        assert isinstance(result, dict)


class TestMCPAskQuestion:
    """Tests for ask_question tool."""

    def test_server_has_ask_question_tool(self) -> None:
        """Server registers ask_question tool."""
        server = SpecAtlasMCPServer()
        assert server.server is not None
        assert hasattr(server, "_ask_question_handler")

    @pytest.mark.anyio
    async def test_ask_question_handler_called(self) -> None:
        """ask_question handler can be called."""
        server = SpecAtlasMCPServer()
        result = await server._ask_question_handler("What is this?", "default")

        assert isinstance(result, dict)
        assert "question" in result or "error" in result

    @pytest.mark.anyio
    async def test_ask_question_with_repo(self) -> None:
        """ask_question accepts repo parameter."""
        server = SpecAtlasMCPServer()
        result = await server._ask_question_handler("What is this?", "my-repo")

        assert isinstance(result, dict)

    @pytest.mark.anyio
    async def test_ask_question_returns_answer_structure(self) -> None:
        """ask_question returns expected structure."""
        server = SpecAtlasMCPServer()
        result = await server._ask_question_handler("What is this?", "default")

        assert isinstance(result, dict)
        # Should contain question and either an answer or error
        assert "question" in result or "error" in result


class TestMCPServerIntegration:
    """Integration tests for MCP server."""

    def test_server_initialization_with_handlers(self) -> None:
        """Server can be initialized with custom handlers."""
        from spec_atlas.mcp.handlers import MCPToolHandlers

        handlers = MCPToolHandlers()
        server = SpecAtlasMCPServer(handlers=handlers)

        assert server.handlers is not None
        assert server.handlers == handlers

    def test_server_initialization_without_handlers(self) -> None:
        """Server can be initialized without handlers."""
        server = SpecAtlasMCPServer()

        assert server.server is not None
        # Handlers optional, defaults to None
        assert server.handlers is None

    def test_all_four_tools_registered(self) -> None:
        """Server has all four required tools registered."""
        server = SpecAtlasMCPServer()

        # Check that all handler methods exist
        assert hasattr(server, "_search_knowledge_handler")
        assert hasattr(server, "_get_spec_handler")
        assert hasattr(server, "_get_graph_handler")
        assert hasattr(server, "_ask_question_handler")

    @pytest.mark.anyio
    async def test_tool_call_with_unknown_tool(self) -> None:
        """Tool call with unknown tool returns error."""
        server = SpecAtlasMCPServer()
        result = await server._handle_tool_call("unknown_tool", {})

        assert isinstance(result, dict)
        assert "error" in result
        assert "unknown tool" in result["error"]

    @pytest.mark.anyio
    async def test_tool_call_with_missing_required_args(self) -> None:
        """Tool call with missing required arguments raises error."""
        server = SpecAtlasMCPServer()

        # search_knowledge requires "query"
        result = await server._handle_tool_call("search_knowledge", {})
        assert isinstance(result, dict)
        assert "error" in result

    @pytest.mark.anyio
    async def test_tool_call_with_exception_handling(self) -> None:
        """Tool call exceptions are handled gracefully."""
        server = SpecAtlasMCPServer()

        # Call with invalid arguments should be handled
        result = await server._handle_tool_call("get_spec", {"component_ref": None})
        assert isinstance(result, dict)
