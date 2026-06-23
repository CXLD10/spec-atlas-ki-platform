"""Tests for BaselineRetriever (F-016 T-016.1).

All offline — no DB required.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from spec_atlas.eval.baseline import BaselineRetriever


def _make_node(name: str, qualified_name: str | None = None, docstring: str | None = None) -> MagicMock:
    node = MagicMock()
    node.name = name
    node.qualified_name = qualified_name or name
    node.language = "python"
    node.file_id = str(uuid.uuid4())
    node.start_line = 1
    node.end_line = 10
    node.signature = f"def {name}():"
    node.docstring = docstring
    node.repo_id = "test-repo"
    return node


class TestBaselineRetriever:
    def test_retrieve_returns_list(self) -> None:
        """retrieve() returns a list (may be empty) — never raises."""
        retriever = BaselineRetriever()
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = []

        nodes = retriever.retrieve("authentication", "repo-123", mock_session)
        assert isinstance(nodes, list)

    def test_retrieve_keyword_match(self) -> None:
        """retrieve() returns nodes whose names match query keywords."""
        retriever = BaselineRetriever()

        auth_node = _make_node("authenticate", "auth.authenticate")
        other_node = _make_node("render_template", "views.render_template")

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [
            auth_node, other_node
        ]

        nodes = retriever.retrieve("authenticate user", "repo-123", mock_session)
        names = {n.name for n in nodes}
        assert "authenticate" in names

    def test_retrieve_top_k_limited(self) -> None:
        """retrieve() returns at most k nodes."""
        retriever = BaselineRetriever()
        many_nodes = [_make_node(f"func_{i}") for i in range(20)]

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = many_nodes
        # Make all names match keyword "func"
        nodes = retriever.retrieve("func", "repo-123", mock_session, k=3)
        assert len(nodes) <= 3

    def test_answer_from_nodes_returns_string(self) -> None:
        """answer_from_nodes() returns a non-empty string."""
        from spec_atlas.llm.fake import FakeLLMProvider

        retriever = BaselineRetriever()
        nodes = [_make_node("auth_check", docstring="Checks authentication token")]
        answer = retriever.answer_from_nodes("how does auth work?", nodes, FakeLLMProvider())

        assert isinstance(answer, str)
        assert len(answer) > 0

    def test_answer_from_empty_nodes(self) -> None:
        """answer_from_nodes() handles empty nodes list gracefully."""
        from spec_atlas.llm.fake import FakeLLMProvider

        retriever = BaselineRetriever()
        answer = retriever.answer_from_nodes("what is this?", [], FakeLLMProvider())
        assert isinstance(answer, str)
        assert "no relevant" in answer.lower() or len(answer) > 0

    def test_context_token_estimate_nonzero(self) -> None:
        """context_token_estimate() returns a positive integer for non-empty nodes."""
        retriever = BaselineRetriever()
        nodes = [_make_node("big_function", docstring="A very detailed function")]
        tokens = retriever.context_token_estimate(nodes)
        assert tokens > 0

    def test_context_token_estimate_scales_with_nodes(self) -> None:
        """More nodes → larger token estimate."""
        retriever = BaselineRetriever()
        one_node = [_make_node("f", docstring="doc")]
        ten_nodes = [_make_node(f"f{i}", docstring="doc") for i in range(10)]

        assert retriever.context_token_estimate(ten_nodes) >= retriever.context_token_estimate(one_node)
