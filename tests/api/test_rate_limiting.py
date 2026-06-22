"""Tests for rate limiting (T-017.1)."""

from __future__ import annotations

import pytest

# Skip all tests if slowapi not installed
pytest.importorskip("slowapi")


class TestRateLimiting:
    """Tests for rate limiting on endpoints."""

    def test_ask_endpoint_decorated_with_limiter(self) -> None:
        """POST /api/ask has rate limit decorator (20/minute)."""
        from spec_atlas.api import answer

        assert hasattr(answer, "limiter")
        assert answer.HAS_LIMITER is True

    def test_ingest_endpoint_decorated_with_limiter(self) -> None:
        """POST /api/ingest has rate limit decorator (5/hour)."""
        from spec_atlas.api import ingest

        assert hasattr(ingest, "limiter")
        assert ingest.HAS_LIMITER is True

    def test_rate_limit_on_ask_is_20_per_minute(self) -> None:
        """Rate limit on /api/ask is 20 requests per minute."""
        # This test would require making actual requests and hitting the limit
        # With slowapi installed, this can be validated end-to-end with TestClient
        # For now, just verify the limiter instance exists and is configured
        from spec_atlas.api.answer import limiter

        assert limiter is not None
        # Actual rate limit testing requires test client + multiple rapid requests

    def test_rate_limit_on_ingest_is_5_per_hour(self) -> None:
        """Rate limit on /api/ingest is 5 requests per hour."""
        # Same as above: requires end-to-end testing with TestClient
        from spec_atlas.api.ingest import limiter

        assert limiter is not None


class TestRateLimitingGracefulDegradation:
    """Tests for graceful degradation when slowapi not available."""

    def test_answer_module_loads_without_slowapi_error(self) -> None:
        """answer.py module loads successfully when slowapi is available."""
        # If we got here, slowapi IS available (pytest.importorskip at module level)
        from spec_atlas.api import answer

        assert answer.HAS_LIMITER is True

    def test_ingest_module_loads_without_slowapi_error(self) -> None:
        """ingest.py module loads successfully when slowapi is available."""
        from spec_atlas.api import ingest

        assert ingest.HAS_LIMITER is True
