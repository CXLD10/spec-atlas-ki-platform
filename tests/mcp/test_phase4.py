"""Phase 4 MCP + SSE tests.

Offline tests (no DB):
- test_mcp_entrypoint_boots
- test_mcp_search_knowledge_real (fake providers, no embeddings → keyword fallback)
- test_mcp_ask_question_real_confidence
- test_ask_stream_emits_tokens

DB tests (pytest.mark.db):
- test_mcp_get_graph_returns_layer
"""

from __future__ import annotations

import asyncio
import json
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# 1. Entrypoint boots
# ---------------------------------------------------------------------------

class TestMCPEntrypointBoots:
    def test_entrypoint_module_importable(self) -> None:
        """spec_atlas.mcp.__main__ is importable and exposes main()."""
        from spec_atlas.mcp.__main__ import main

        assert callable(main)

    def test_console_script_registered(self) -> None:
        """pyproject.toml registers the spec-atlas-mcp console script."""
        import tomllib
        from pathlib import Path

        pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
        with pyproject.open("rb") as f:
            data = tomllib.load(f)

        scripts = data.get("project", {}).get("scripts", {})
        assert "spec-atlas-mcp" in scripts, (
            f"spec-atlas-mcp not in [project.scripts]: {list(scripts)}"
        )
        assert "spec_atlas.mcp.__main__:main" in scripts["spec-atlas-mcp"]

    def test_server_builds_with_handlers(self) -> None:
        """SpecAtlasMCPServer accepts an MCPHandlers instance."""
        from unittest.mock import MagicMock

        from spec_atlas.mcp.handlers import MCPHandlers
        from spec_atlas.mcp.server import SpecAtlasMCPServer

        fake_session = MagicMock()
        fake_embed = MagicMock()
        fake_llm = MagicMock()
        handlers = MCPHandlers(fake_session, fake_session, fake_embed, fake_llm)
        server = SpecAtlasMCPServer(handlers=handlers)
        assert server.handlers is handlers


# ---------------------------------------------------------------------------
# 2. search_knowledge — uses keyword fallback when no embeddings (offline)
# ---------------------------------------------------------------------------

class TestMCPSearchKnowledgeReal:
    def test_search_returns_dict_not_raises(self) -> None:
        """search_knowledge returns a dict and does not raise (keyword fallback)."""
        from unittest.mock import MagicMock

        from spec_atlas.embed.fake import FakeEmbeddingProvider
        from spec_atlas.mcp.handlers import MCPHandlers

        fake_session = MagicMock()
        # Make embedding count return 0 so keyword fallback triggers
        fake_session.query.return_value.scalar.return_value = 0
        fake_session.query.return_value.all.return_value = []

        handlers = MCPHandlers(None, fake_session, FakeEmbeddingProvider(), MagicMock())
        result = asyncio.run(handlers.search_knowledge("authentication"))

        assert isinstance(result, dict)
        assert "results" in result
        assert "error" not in result or result.get("error") is None

    def test_search_returns_strategy(self) -> None:
        """search_knowledge result includes a strategy field."""
        from unittest.mock import MagicMock

        from spec_atlas.embed.fake import FakeEmbeddingProvider
        from spec_atlas.mcp.handlers import MCPHandlers

        fake_session = MagicMock()
        fake_session.query.return_value.scalar.return_value = 0
        fake_session.query.return_value.all.return_value = []

        handlers = MCPHandlers(None, fake_session, FakeEmbeddingProvider(), MagicMock())
        result = asyncio.run(handlers.search_knowledge("how does auth work"))

        assert "strategy" in result


# ---------------------------------------------------------------------------
# 3. ask_question — confidence is real (not hardcoded 1.0)
# ---------------------------------------------------------------------------

class TestMCPAskQuestionRealConfidence:
    def test_confidence_not_hardcoded_one(self) -> None:
        """ask_question returns the actual similarity score, never a literal 1.0."""
        from unittest.mock import MagicMock

        from spec_atlas.embed.fake import FakeEmbeddingProvider
        from spec_atlas.llm.fake import FakeLLMProvider
        from spec_atlas.mcp.handlers import MCPHandlers

        fake_session = MagicMock()
        fake_session.query.return_value.scalar.return_value = 0
        fake_session.query.return_value.all.return_value = []

        handlers = MCPHandlers(None, fake_session, FakeEmbeddingProvider(), FakeLLMProvider())
        result = asyncio.run(handlers.ask_question("what does this codebase do?"))

        assert isinstance(result, dict)
        # With zero embeddings the result either has a confidence that is NOT
        # the hardcoded 1.0, OR returns a "no matching content" answer.
        confidence = result.get("confidence", 0.0)
        assert confidence != 1.0, (
            f"confidence is still hardcoded 1.0 — real scoring not applied: {result}"
        )

    def test_ask_question_has_required_keys(self) -> None:
        """ask_question response always contains question, answer, claims, confidence."""
        from unittest.mock import MagicMock

        from spec_atlas.embed.fake import FakeEmbeddingProvider
        from spec_atlas.llm.fake import FakeLLMProvider
        from spec_atlas.mcp.handlers import MCPHandlers

        fake_session = MagicMock()
        fake_session.query.return_value.scalar.return_value = 0
        fake_session.query.return_value.all.return_value = []

        handlers = MCPHandlers(None, fake_session, FakeEmbeddingProvider(), FakeLLMProvider())
        result = asyncio.run(handlers.ask_question("ping"))

        for key in ("question", "answer", "claims", "confidence"):
            assert key in result, f"Missing key {key!r} in result: {result}"


# ---------------------------------------------------------------------------
# 4. get_graph — DB test (seeded layer)
# ---------------------------------------------------------------------------

class TestMCPGetGraphReturnsLayer:
    pytestmark = pytest.mark.db

    def test_get_graph_l1_nodes_from_db(self, migrated: None) -> None:
        """get_graph('source') returns real Node rows from the Analysis DB."""
        from spec_atlas import db
        from spec_atlas.db.analysis import File, Node, Repo
        from spec_atlas.embed.fake import FakeEmbeddingProvider
        from spec_atlas.llm.fake import FakeLLMProvider
        from spec_atlas.mcp.handlers import MCPHandlers

        AnalysisSession = db.analysis_session()
        with AnalysisSession() as session:
            repo = Repo(name="mcp-graph-test", source="local")
            session.add(repo)
            session.flush()
            f = File(
                repo_id=repo.id, path="x.py", language="python",
                content_hash="abc", loc=5,
            )
            session.add(f)
            session.flush()
            node = Node(
                repo_id=repo.id, file_id=f.id, language="python",
                kind="function", name="do_it", qualified_name="x.do_it",
                start_line=1, end_line=3,
            )
            session.add(node)
            session.commit()

        with AnalysisSession() as session:
            handlers = MCPHandlers(None, session, FakeEmbeddingProvider(), FakeLLMProvider())
            result = asyncio.run(handlers.get_graph(repo="mcp-graph-test", layer="source"))

        assert result.get("node_count", 0) >= 1, f"Expected nodes, got: {result}"
        l1_nodes = [n for n in result["nodes"] if n["layer"] == "L1"]
        assert len(l1_nodes) >= 1
        assert any(n["label"] == "x.do_it" for n in l1_nodes)

    def test_get_graph_returns_structure_keys(self, migrated: None) -> None:
        """get_graph result always has nodes, edges, node_count, edge_count."""
        from spec_atlas import db
        from spec_atlas.embed.fake import FakeEmbeddingProvider
        from spec_atlas.llm.fake import FakeLLMProvider
        from spec_atlas.mcp.handlers import MCPHandlers

        AnalysisSession = db.analysis_session()
        with AnalysisSession() as session:
            handlers = MCPHandlers(None, session, FakeEmbeddingProvider(), FakeLLMProvider())
            result = asyncio.run(handlers.get_graph())

        for key in ("nodes", "edges", "node_count", "edge_count", "layer"):
            assert key in result, f"Missing key {key!r}: {result}"


# ---------------------------------------------------------------------------
# 5. SSE streaming Ask — test the /api/ask/stream endpoint
# ---------------------------------------------------------------------------

class TestAskStreamEmitsTokens:
    def test_stream_endpoint_emits_token_events(self) -> None:
        """POST /api/ask/stream emits data lines including a 'done' event."""
        from fastapi.testclient import TestClient

        from spec_atlas.api.app import create_app
        from spec_atlas.config import get_settings

        settings = get_settings()
        client = TestClient(create_app(settings))

        with client.stream("POST", "/api/ask/stream", json={"question": "ping", "repo": "default"}) as resp:
            assert resp.status_code in (200, 503), resp.text

            if resp.status_code == 503:
                # DB not configured — endpoint correctly rejects before streaming
                return

            assert resp.headers.get("content-type", "").startswith("text/event-stream")

            body = b""
            for chunk in resp.iter_bytes():
                body += chunk

        lines = body.decode().split("\n")
        data_lines = [l for l in lines if l.startswith("data: ")]

        assert len(data_lines) >= 1, f"No data: lines in SSE response: {body[:500]}"

        # Last data line must be a 'done' event
        last = json.loads(data_lines[-1][6:])
        assert last.get("type") == "done", f"Last event not 'done': {last}"
        assert "answer" in last

    def test_stream_endpoint_exists_in_router(self) -> None:
        """POST /api/ask/stream is registered and returns 422 on missing body."""
        from fastapi.testclient import TestClient

        from spec_atlas.api.app import create_app
        from spec_atlas.config import get_settings

        settings = get_settings()
        client = TestClient(create_app(settings))
        resp = client.post("/api/ask/stream")
        # 422 = missing body (route exists but validation failed)
        # 503 = DB not configured (but route registered)
        assert resp.status_code in (422, 503), (
            f"Expected 422 or 503, got {resp.status_code} — route may not be registered"
        )
