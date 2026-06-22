"""Integration tests for spec verification workflow (SpecStore + Verifier)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from spec_atlas.spec.store import SpecStore


def test_verify_spec_idempotent():
    """Verify that calling verify 2x returns same result (idempotent)."""
    mock_session = MagicMock()

    # Create a mock spec
    mock_spec = MagicMock()
    mock_spec.status = "verified"  # Already verified
    mock_spec.content = {
        "purpose": "Test function",
        "_verification_metadata": {
            "confidence": 0.75,
            "is_grounded": False,
            "issues": [],
            "verified_at": "2026-06-22T00:00:00",
        },
    }

    store = SpecStore(mock_session)

    # Mock get_version to return our spec
    with patch.object(store, "get_version", return_value=mock_spec):
        analysis_session = MagicMock()

        # Verify 1st time
        result1 = store.verify_spec(
            user_id="default",
            repo="test-repo",
            component_ref="test.function",
            version=1,
            analysis_session=analysis_session,
        )

        # Verify 2nd time (should use cached result)
        result2 = store.verify_spec(
            user_id="default",
            repo="test-repo",
            component_ref="test.function",
            version=1,
            analysis_session=analysis_session,
        )

        # Results should be identical
        assert result1.confidence == result2.confidence
        assert result1.is_grounded == result2.is_grounded
        assert len(result1.issues) == len(result2.issues)


def test_verify_raises_without_analysis_session():
    """Verify that verify raises ValueError without analysis_session."""
    mock_session = MagicMock()
    store = SpecStore(mock_session)

    try:
        store.verify_spec(
            user_id="default",
            repo="test-repo",
            component_ref="test.function",
            version=1,
            analysis_session=None,
        )
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        assert "analysis_session required" in str(e)


def test_verify_raises_on_missing_spec():
    """Verify that verify raises ValueError when spec not found."""
    mock_session = MagicMock()
    analysis_session = MagicMock()

    store = SpecStore(mock_session)

    # Mock get_version and get_current to return None
    with patch.object(store, "get_version", return_value=None):
        with patch.object(store, "get_current", return_value=None):
            try:
                store.verify_spec(
                    user_id="default",
                    repo="test-repo",
                    component_ref="nonexistent",
                    version=1,
                    analysis_session=analysis_session,
                )
                raise AssertionError("Should have raised ValueError")
            except ValueError as e:
                assert "Spec not found" in str(e)


def test_verify_already_verified_returns_cached():
    """Verify that already-verified specs return cached result without rerunning verifier."""
    mock_session = MagicMock()
    analysis_session = MagicMock()

    # Create a mock spec that's already verified with cached metadata
    mock_spec = MagicMock()
    mock_spec.status = "verified"
    mock_spec.content = {
        "purpose": "Test",
        "_verification_metadata": {
            "confidence": 0.95,
            "is_grounded": True,
            "verified_at": "2026-06-22T00:00:00",
            "issues": [],
        },
    }

    store = SpecStore(mock_session)

    with patch.object(store, "get_version", return_value=mock_spec):
        result = store.verify_spec(
            user_id="default",
            repo="test-repo",
            component_ref="test.function",
            version=1,
            analysis_session=analysis_session,
        )

        # Should return cached result without calling verifier
        assert result.confidence == 0.95
        assert result.is_grounded is True
        assert len(result.issues) == 0


def test_spec_store_has_verify_spec_method():
    """Verify that SpecStore has the verify_spec method."""
    mock_session = MagicMock()
    store = SpecStore(mock_session)

    # Verify the method exists and is callable
    assert hasattr(store, "verify_spec")
    assert callable(store.verify_spec)
