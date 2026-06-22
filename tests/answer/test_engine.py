"""Tests for answer generation engine."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from spec_atlas.answer.engine import Answer, AnswerEngine


class TestAnswerEngine:
    """Tests for answer generation."""

    def test_answer_basic(self) -> None:
        """Engine generates answer from context."""
        # Mock context
        context = MagicMock()
        context.matched_group.path = "auth"
        context.matched_group.summary_md = "Authentication module"
        context.specs = []
        context.source_spans = []

        # Mock LLM provider
        llm_provider = MagicMock()
        llm_provider.complete.return_value = json.dumps(
            {
                "answer": "The auth module handles user authentication.",
                "claims": [{"claim": "Handles authentication", "source": "auth.py:10"}],
            }
        )

        result = AnswerEngine.answer(
            query="How does authentication work?",
            context=context,
            llm_provider=llm_provider,
        )

        assert isinstance(result, Answer)
        assert "authentication" in result.text.lower()
        assert len(result.claims) == 1
        assert result.claims[0].claim == "Handles authentication"

    def test_answer_with_specs(self) -> None:
        """Engine includes specs in context."""
        context = MagicMock()
        context.matched_group.path = "api"
        context.matched_group.summary_md = "API layer"

        spec = MagicMock()
        spec.component_ref = "HTTPRouter"
        spec.content = {"purpose": "Routes HTTP requests"}
        context.specs = [spec]
        context.source_spans = []

        llm_provider = MagicMock()
        llm_provider.complete.return_value = json.dumps(
            {
                "answer": "API routes HTTP requests.",
                "claims": [],
            }
        )

        AnswerEngine.answer(
            query="What does the API do?",
            context=context,
            llm_provider=llm_provider,
        )

        # Verify LLM was called
        llm_provider.complete.assert_called_once()
        call_args = llm_provider.complete.call_args[0][0][0]["content"]
        assert "HTTPRouter" in call_args

    def test_answer_with_source_spans(self) -> None:
        """Engine includes source spans."""
        context = MagicMock()
        context.matched_group.path = "core"
        context.matched_group.summary_md = "Core module"
        context.specs = []
        context.source_spans = [{"file": "core.py", "start_line": 1, "end_line": 50}]

        llm_provider = MagicMock()
        llm_provider.complete.return_value = '{"answer": "...", "claims": []}'

        AnswerEngine.answer(
            query="What's in core?",
            context=context,
            llm_provider=llm_provider,
        )

        # Verify spans are in prompt
        call_args = llm_provider.complete.call_args[0][0][0]["content"]
        assert "core.py:1" in call_args

    def test_answer_string_response(self) -> None:
        """Engine handles string LLM responses."""
        context = MagicMock()
        context.matched_group.path = "test"
        context.matched_group.summary_md = "Test module"
        context.specs = []
        context.source_spans = []

        llm_provider = MagicMock()
        # Return non-JSON string (fallback case)
        llm_provider.complete.return_value = "Some text response"

        result = AnswerEngine.answer(
            query="What is this?",
            context=context,
            llm_provider=llm_provider,
        )

        assert result.text == "Some text response"
        assert result.claims == []

    def test_answer_dict_response(self) -> None:
        """Engine handles dict LLM responses."""
        context = MagicMock()
        context.matched_group.path = "test"
        context.matched_group.summary_md = ""
        context.specs = []
        context.source_spans = []

        llm_provider = MagicMock()
        llm_provider.complete.return_value = {
            "answer": "Dict response",
            "claims": [{"claim": "Test", "source": "test.py:5"}],
        }

        result = AnswerEngine.answer(
            query="Test?",
            context=context,
            llm_provider=llm_provider,
        )

        assert result.text == "Dict response"
        assert len(result.claims) == 1

    def test_answer_multiple_claims(self) -> None:
        """Engine handles multiple claims."""
        context = MagicMock()
        context.matched_group.path = "root"
        context.matched_group.summary_md = ""
        context.specs = []
        context.source_spans = []

        llm_provider = MagicMock()
        llm_provider.complete.return_value = json.dumps(
            {
                "answer": "Multi-claim answer",
                "claims": [
                    {"claim": "Claim 1", "source": "file1.py:10"},
                    {"claim": "Claim 2", "source": "file2.py:20"},
                    {"claim": "Claim 3", "source": "file3.py:30"},
                ],
            }
        )

        result = AnswerEngine.answer(
            query="Test",
            context=context,
            llm_provider=llm_provider,
        )

        assert len(result.claims) == 3
        assert result.claims[0].claim == "Claim 1"
        assert result.claims[1].source == "file2.py:20"

    def test_build_prompt_structure(self) -> None:
        """Prompt includes all required elements."""
        context = MagicMock()
        context.matched_group.path = "auth"
        context.matched_group.summary_md = "Auth summary"

        spec = MagicMock()
        spec.component_ref = "LoginHandler"
        spec.content = {"purpose": "Handles login"}
        context.specs = [spec]

        context.source_spans = [{"file": "login.py", "start_line": 10}]

        prompt = AnswerEngine._build_prompt("How to login?", context)

        assert "How to login?" in prompt
        assert "Auth summary" in prompt
        assert "LoginHandler" in prompt
        assert "login.py:10" in prompt
        assert "JSON" in prompt

    def test_answer_strategy_from_context(self) -> None:
        """Answer strategy comes from matched group path."""
        context = MagicMock()
        context.matched_group.path = "special_group"
        context.matched_group.summary_md = ""
        context.specs = []
        context.source_spans = []

        llm_provider = MagicMock()
        llm_provider.complete.return_value = '{"answer": "Test", "claims": []}'

        result = AnswerEngine.answer("Test?", context, llm_provider)

        assert result.strategy_used == "special_group"

    def test_answer_malformed_claims(self) -> None:
        """Engine handles malformed claims gracefully."""
        context = MagicMock()
        context.matched_group.path = "test"
        context.matched_group.summary_md = ""
        context.specs = []
        context.source_spans = []

        llm_provider = MagicMock()
        llm_provider.complete.return_value = json.dumps(
            {
                "answer": "Answer",
                "claims": [
                    {"claim": "Valid", "source": "file.py:1"},
                    {"claim": "Missing source"},  # Missing source field
                    "Not a dict",  # Not a dict at all
                ],
            }
        )

        result = AnswerEngine.answer("Test?", context, llm_provider)

        # Should skip malformed claims
        assert len(result.claims) >= 1
        # First claim should be valid
        assert result.claims[0].claim == "Valid"
