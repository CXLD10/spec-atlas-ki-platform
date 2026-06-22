"""Tests for MCP tool handlers."""

from __future__ import annotations

from spec_atlas.mcp.handlers import MCPToolHandlers


class TestMCPToolHandlers:
    """Tests for backend-wired tool handlers."""

    def test_handler_initialization(self) -> None:
        """Handlers initialize with backend URL."""
        handlers = MCPToolHandlers(backend_url="http://example.com:3000")
        assert handlers.backend_url == "http://example.com:3000"

    def test_handler_default_url(self) -> None:
        """Handlers use default backend URL."""
        handlers = MCPToolHandlers()
        assert handlers.backend_url == "http://localhost:8000"

    def test_handler_has_methods(self) -> None:
        """Handlers have all tool methods."""
        handlers = MCPToolHandlers()
        assert hasattr(handlers, "search")
        assert hasattr(handlers, "get_spec")
        assert hasattr(handlers, "get_group")
        assert hasattr(handlers, "list_stale_specs")
        assert hasattr(handlers, "close")
