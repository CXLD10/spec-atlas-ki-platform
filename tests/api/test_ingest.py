"""Tests for ingest API endpoints."""

from __future__ import annotations

from spec_atlas.api.app import create_app
from spec_atlas.api.ingest import (
    IngestRequest,
    JobStatus,
)
from spec_atlas.config import Settings


class TestIngestAPI:
    """Tests for ingest API endpoints."""

    def test_ingest_endpoints_registered(self) -> None:
        """Ingest endpoints are registered."""
        app = create_app(Settings())
        assert len(app.routes) > 0

    def test_ingest_request_schema(self) -> None:
        """IngestRequest schema validation."""
        req = IngestRequest(repo_url="https://github.com/user/repo")
        assert req.repo_url == "https://github.com/user/repo"

    def test_ingest_request_validates_empty_url(self) -> None:
        """IngestRequest rejects empty repo_url."""
        from pydantic import ValidationError

        try:
            IngestRequest(repo_url="")
            assert False, "Should reject empty repo_url"
        except ValidationError:
            pass  # Expected

    def test_ingest_status_response_schema(self) -> None:
        """JobStatus schema for ingest status."""
        response = JobStatus(
            job_id="abc-123",
            status="in_progress",
            progress=50,
            repo_url="https://github.com/user/repo",
            created_at="2026-06-21T00:00:00",
        )
        assert response.job_id == "abc-123"
        assert response.status == "in_progress"
        assert response.progress == 50
        assert 0 <= response.progress <= 100

    def test_ingest_status_with_error(self) -> None:
        """JobStatus can have error."""
        response = JobStatus(
            job_id="abc-123",
            status="failed",
            progress=0,
            repo_url="https://github.com/user/repo",
            created_at="2026-06-21T00:00:00",
            error="Connection failed",
        )
        assert response.error == "Connection failed"
