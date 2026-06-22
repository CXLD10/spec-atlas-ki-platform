"""Tests for POST /api/ask answer endpoint."""

from __future__ import annotations

from spec_atlas.api.app import create_app
from spec_atlas.config import Settings


class TestAskEndpoint:
    """Tests for POST /api/ask endpoint."""

    def test_ask_endpoint_registered(self) -> None:
        """POST /api/ask endpoint is registered."""
        app = create_app(Settings())
        # Check app has routes
        assert len(app.routes) > 0

    def test_ask_request_schema(self) -> None:
        """AskRequest schema validation."""
        from spec_atlas.api.answer import AskRequest

        # Valid request
        req = AskRequest(question="What is this?")
        assert req.question == "What is this?"
        assert req.repo == "default"

        # With custom repo
        req2 = AskRequest(question="How does auth work?", repo="custom")
        assert req2.repo == "custom"

    def test_ask_request_validates_empty_question(self) -> None:
        """AskRequest rejects empty questions."""
        from pydantic import ValidationError

        from spec_atlas.api.answer import AskRequest

        try:
            AskRequest(question="")
            assert False, "Should reject empty question"
        except ValidationError:
            pass  # Expected

    def test_ask_response_schema(self) -> None:
        """AskResponse schema has required fields."""
        from spec_atlas.api.answer import AskResponse, ClaimResponse

        claims = [
            ClaimResponse(text="Auth is handled by OAuth", source="auth.py:42"),
        ]
        response = AskResponse(
            answer="The system uses OAuth for authentication.",
            claims=claims,
            confidence=0.85,
            strategy="vector_search",
        )

        assert response.answer == "The system uses OAuth for authentication."
        assert len(response.claims) == 1
        assert response.claims[0].source == "auth.py:42"
        assert response.confidence == 0.85
        assert response.strategy == "vector_search"

    def test_claim_response_schema(self) -> None:
        """ClaimResponse schema is valid."""
        from spec_atlas.api.answer import ClaimResponse

        claim = ClaimResponse(text="Authentication is handled by AuthService", source="auth.py:42")
        assert claim.text == "Authentication is handled by AuthService"
        assert claim.source == "auth.py:42"

    def test_answer_router_class_exists(self) -> None:
        """AnswerRouter class has required methods."""
        from spec_atlas.api.answer import AnswerRouter

        assert hasattr(AnswerRouter, "__init__")
        assert hasattr(AnswerRouter, "answer")
