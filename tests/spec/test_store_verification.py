"""Integration tests for spec verification workflow (SpecStore + Verifier)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from spec_atlas import db
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


@pytest.mark.db
def test_verification_metadata_persists_and_feeds_reports(migrated: None) -> None:
    """Regression: Spec.content was a plain JSONB column, so
    spec.content["_verification_metadata"] = {...} (an in-place dict
    mutation) was never dirty-tracked by SQLAlchemy and silently never
    committed. avg_confidence/confidence distribution always read back 0/empty
    no matter how many specs were verified. Caught by re-querying in a fresh
    session instead of trusting the same Python object the test created."""
    AnalysisSession = db.analysis_session()
    SpecSession = db.spec_session()

    with AnalysisSession() as s:
        repo = db.Repo(name="verify-meta-repo", source="/tmp/verify-meta-repo")
        s.add(repo)
        s.flush()

        file = db.File(
            repo_id=repo.id, path="a.py", language="python", content_hash="x", loc=10
        )
        s.add(file)
        s.flush()

        s.add(
            db.Node(
                repo_id=repo.id,
                file_id=file.id,
                language="python",
                kind="function",
                name="f",
                qualified_name="a.f",
                signature="def f():",
                docstring="Docstring for grounding.",
                start_line=1,
                end_line=2,
            )
        )
        s.commit()

    with SpecSession() as s:
        SpecStore(s).create(
            user_id="default",
            repo="verify-meta-repo",
            component_ref="a.f",
            spec_content={"purpose": "Docstring for grounding."},
            provenance=[{"file": "a.py", "start_line": 1, "end_line": 2}],
            status="draft",
        )

    with SpecSession() as spec_s, AnalysisSession() as analysis_s:
        SpecStore(spec_s).verify_spec(
            user_id="default",
            repo="verify-meta-repo",
            component_ref="a.f",
            version=1,
            analysis_session=analysis_s,
        )

    # Fresh sessions: no identity-map carryover from the verify call above.
    with SpecSession() as fresh:
        from spec_atlas.db.spec import Spec

        spec = (
            fresh.query(Spec)
            .filter(Spec.repo == "verify-meta-repo", Spec.component_ref == "a.f")
            .first()
        )
        assert "_verification_metadata" in spec.content
        assert spec.content["_verification_metadata"]["confidence"] > 0

        report = SpecStore(fresh).get_verification_report("default", "verify-meta-repo")
        assert report["avg_confidence"] > 0

        distribution = SpecStore(fresh).get_confidence_distribution(
            "default", "verify-meta-repo"
        )
        assert sum(distribution["counts"]) >= 1
