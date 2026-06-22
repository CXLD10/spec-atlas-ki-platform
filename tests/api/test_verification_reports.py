"""Tests for verification analytics reporting endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock

from spec_atlas.api.reports import (
    ConfidenceDistribution,
    VerificationIssue,
    VerificationIssuesReport,
    VerificationReport,
)
from spec_atlas.spec.store import SpecStore


def test_verification_report_response_model():
    """Test that VerificationReport has all required fields."""
    report = VerificationReport(
        total_specs=10,
        verified_count=8,
        review_count=1,
        draft_count=1,
        avg_confidence=0.85,
        verification_rate=80.0,
        specs_needing_review=1,
    )

    assert report.total_specs == 10
    assert report.verified_count == 8
    assert report.review_count == 1
    assert report.draft_count == 1
    assert report.avg_confidence == 0.85
    assert report.verification_rate == 80.0
    assert report.specs_needing_review == 1


def test_verification_issue_response_model():
    """Test that VerificationIssue model works."""
    issue = VerificationIssue(reason="Component not found", count=5)

    assert issue.reason == "Component not found"
    assert issue.count == 5


def test_verification_issues_report_model():
    """Test that VerificationIssuesReport model works."""
    issues = [
        VerificationIssue(reason="Missing docstring", count=3),
        VerificationIssue(reason="Parameter mismatch", count=2),
    ]
    report = VerificationIssuesReport(issues=issues, count=2)

    assert len(report.issues) == 2
    assert report.count == 2


def test_confidence_distribution_model():
    """Test that ConfidenceDistribution model works."""
    dist = ConfidenceDistribution(
        bins=["0.0-0.2", "0.2-0.4", "0.4-0.6", "0.6-0.8", "0.8-1.0"],
        counts=[0, 1, 2, 3, 4],
    )

    assert len(dist.bins) == 5
    assert len(dist.counts) == 5
    assert sum(dist.counts) == 10


def test_spec_store_verification_report():
    """Test SpecStore.get_verification_report() method."""
    mock_session = MagicMock()

    # Create mock specs
    verified_spec = MagicMock()
    verified_spec.status = "verified"
    verified_spec.content = {"_verification_metadata": {"confidence": 0.95, "issues": []}}

    review_spec = MagicMock()
    review_spec.status = "review"
    review_spec.content = {"_verification_metadata": {"confidence": 0.6, "issues": []}}

    draft_spec = MagicMock()
    draft_spec.status = "draft"
    draft_spec.content = {"_verification_metadata": {"confidence": 0.3, "issues": []}}

    # Mock the query chain
    mock_query = MagicMock()
    mock_query.filter.return_value.all.return_value = [verified_spec, review_spec, draft_spec]
    mock_session.query.return_value = mock_query

    store = SpecStore(mock_session)
    report = store.get_verification_report("default", "test-repo")

    assert report["total_specs"] == 3
    assert report["verified_count"] == 1
    assert report["review_count"] == 1
    assert report["draft_count"] == 1
    assert report["verification_rate"] == 33.3  # 1 verified out of 3
    assert report["avg_confidence"] == round((0.95 + 0.6 + 0.3) / 3, 3)


def test_spec_store_verification_report_empty():
    """Test SpecStore report with no specs."""
    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.all.return_value = []
    mock_session.query.return_value = mock_query

    store = SpecStore(mock_session)
    report = store.get_verification_report("default", "empty-repo")

    assert report["total_specs"] == 0
    assert report["verified_count"] == 0
    assert report["avg_confidence"] == 0.0
    assert report["verification_rate"] == 0.0


def test_spec_store_verification_issues():
    """Test SpecStore.get_verification_issues() method."""
    mock_session = MagicMock()

    # Create mock specs with issues
    spec1 = MagicMock()
    spec1.content = {
        "_verification_metadata": {
            "issues": [
                {"reason": "Missing docstring", "severity": "warning"},
                {"reason": "Missing docstring", "severity": "warning"},
            ]
        }
    }

    spec2 = MagicMock()
    spec2.content = {
        "_verification_metadata": {
            "issues": [{"reason": "Parameter mismatch", "severity": "error"}]
        }
    }

    mock_query = MagicMock()
    mock_query.filter.return_value.all.return_value = [spec1, spec2]
    mock_session.query.return_value = mock_query

    store = SpecStore(mock_session)
    issues = store.get_verification_issues("default", "test-repo", limit=10)

    assert len(issues) == 2
    # "Missing docstring" should be first (count=2)
    assert issues[0]["reason"] == "Missing docstring"
    assert issues[0]["count"] == 2
    assert issues[1]["reason"] == "Parameter mismatch"
    assert issues[1]["count"] == 1


def test_spec_store_confidence_distribution():
    """Test SpecStore.get_confidence_distribution() method."""
    mock_session = MagicMock()

    # Create specs with various confidence levels
    specs = []
    for conf in [0.1, 0.3, 0.5, 0.7, 0.9]:
        spec = MagicMock()
        spec.content = {"_verification_metadata": {"confidence": conf, "issues": []}}
        specs.append(spec)

    mock_query = MagicMock()
    mock_query.filter.return_value.all.return_value = specs
    mock_session.query.return_value = mock_query

    store = SpecStore(mock_session)
    dist = store.get_confidence_distribution("default", "test-repo", bins=5)

    assert "bins" in dist
    assert "counts" in dist
    assert len(dist["bins"]) == 5
    assert len(dist["counts"]) == 5
    assert sum(dist["counts"]) == 5  # Total number of specs


def test_spec_store_confidence_distribution_empty():
    """Test confidence distribution with no specs."""
    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.all.return_value = []
    mock_session.query.return_value = mock_query

    store = SpecStore(mock_session)
    dist = store.get_confidence_distribution("default", "empty-repo", bins=5)

    assert dist["bins"] == []
    assert dist["counts"] == []


def test_verification_report_response_fields():
    """Test that report response includes all expected fields."""
    report = VerificationReport(
        total_specs=5,
        verified_count=3,
        review_count=1,
        draft_count=1,
        avg_confidence=0.8,
        verification_rate=60.0,
        specs_needing_review=1,
    )

    # Check that all fields can be accessed
    assert hasattr(report, "total_specs")
    assert hasattr(report, "verified_count")
    assert hasattr(report, "review_count")
    assert hasattr(report, "draft_count")
    assert hasattr(report, "avg_confidence")
    assert hasattr(report, "verification_rate")
    assert hasattr(report, "specs_needing_review")

    # Convert to dict to verify JSON serialization
    data = report.model_dump()
    assert isinstance(data, dict)
    assert "total_specs" in data
    assert "avg_confidence" in data
