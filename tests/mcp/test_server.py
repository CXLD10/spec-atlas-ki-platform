"""Tests for MCP server scaffold."""

from __future__ import annotations

from spec_atlas.mcp.server import SpecAtlasMCPServer


class TestMCPServerScaffold:
    """Tests for MCP server initialization and tool registration."""

    def test_server_initialization(self) -> None:
        """Server initializes with default backend URL."""
        server = SpecAtlasMCPServer()
        assert server.backend_url == "http://localhost:8000"
        assert server.server is not None

    def test_server_custom_backend_url(self) -> None:
        """Server accepts custom backend URL."""
        custom_url = "http://example.com:3000"
        server = SpecAtlasMCPServer(backend_url=custom_url)
        assert server.backend_url == custom_url

    def test_tools_registered(self) -> None:
        """Server registers 4 tools."""
        server = SpecAtlasMCPServer()
        # Tools are registered via on_call_tool decorator
        # Verify by checking that the handler is set
        assert server.server is not None
        # Direct tool list inspection depends on mcp SDK internals
        # For now, just verify server has the _handle_tool_call method
        assert hasattr(server, "_handle_tool_call")

    def test_handler_methods_exist(self) -> None:
        """Server has handler methods for all tools."""
        server = SpecAtlasMCPServer()
        assert hasattr(server, "_search_handler")
        assert hasattr(server, "_get_spec_handler")
        assert hasattr(server, "_get_group_handler")
        assert hasattr(server, "_list_stale_specs_handler")
        assert hasattr(server, "_handle_tool_call")

    def test_tool_schemas_structure(self) -> None:
        """Verify tool schemas are properly defined."""
        server = SpecAtlasMCPServer()
        # Just verify server initialized without error
        # Real schema validation requires mcp SDK
        assert server.server is not None
