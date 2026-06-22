"""Tests for security vulnerabilities (T-017.2)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from spec_atlas.api.ingest import IngestRequest


class TestPathTraversalSecurity:
    """Tests for path traversal vulnerability fix."""

    def test_safe_resolve_rejects_parent_traversal(self) -> None:
        """Path with ../ to escape repo root is rejected."""
        from pathlib import Path

        from spec_atlas.api.ingest import _safe_resolve_path

        repo_root = Path("/safe/repo")
        with pytest.raises(Exception) as exc_info:
            _safe_resolve_path(repo_root, "../../../../etc/passwd")
        assert "path traversal not allowed" in str(exc_info.value).lower()

    def test_safe_resolve_rejects_absolute_paths(self) -> None:
        """Absolute paths outside repo are rejected."""
        from pathlib import Path

        from spec_atlas.api.ingest import _safe_resolve_path

        repo_root = Path("/safe/repo")
        with pytest.raises(Exception) as exc_info:
            _safe_resolve_path(repo_root, "/etc/passwd")
        assert "path traversal" in str(exc_info.value).lower()

    def test_safe_resolve_allows_valid_paths(self) -> None:
        """Valid paths within repo root are allowed."""
        from pathlib import Path

        from spec_atlas.api.ingest import _safe_resolve_path

        repo_root = Path("/safe/repo")
        result = _safe_resolve_path(repo_root, "src/main.py")
        # Should not raise
        assert "main.py" in str(result)

    def test_safe_resolve_allows_nested_valid_paths(self) -> None:
        """Valid nested paths within repo root are allowed."""
        from pathlib import Path

        from spec_atlas.api.ingest import _safe_resolve_path

        repo_root = Path("/safe/repo")
        result = _safe_resolve_path(repo_root, "a/b/c/file.ts")
        # Should not raise
        assert "file.ts" in str(result)


class TestURLValidationSecurity:
    """Tests for URL validation vulnerability fix."""

    def test_ingest_request_rejects_file_scheme(self) -> None:
        """file:// URLs are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            IngestRequest(repo_url="file:///etc/passwd")
        assert "https" in str(exc_info.value).lower()

    def test_ingest_request_rejects_http_scheme(self) -> None:
        """http:// (non-TLS) URLs are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            IngestRequest(repo_url="http://github.com/user/repo")
        assert "https" in str(exc_info.value).lower()

    def test_ingest_request_rejects_gopher_scheme(self) -> None:
        """gopher:// URLs are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            IngestRequest(repo_url="gopher://localhost")
        assert "https" in str(exc_info.value).lower()

    def test_ingest_request_rejects_localhost_url(self) -> None:
        """https://localhost URLs are rejected (SSRF prevention)."""
        with pytest.raises(ValidationError) as exc_info:
            IngestRequest(repo_url="https://localhost:8080/admin")
        assert "allowlist" in str(exc_info.value).lower()

    def test_ingest_request_rejects_internal_ip_url(self) -> None:
        """https://192.168.x.x URLs are rejected (SSRF prevention)."""
        with pytest.raises(ValidationError) as exc_info:
            IngestRequest(repo_url="https://192.168.1.1/internal")
        assert "allowlist" in str(exc_info.value).lower()

    def test_ingest_request_accepts_github_https(self) -> None:
        """Valid github.com https URLs are accepted."""
        req = IngestRequest(repo_url="https://github.com/user/repo")
        assert req.repo_url == "https://github.com/user/repo"

    def test_ingest_request_accepts_gitlab_https(self) -> None:
        """Valid gitlab.com https URLs are accepted."""
        req = IngestRequest(repo_url="https://gitlab.com/group/project")
        assert req.repo_url == "https://gitlab.com/group/project"

    def test_ingest_request_accepts_codeberg_https(self) -> None:
        """Valid codeberg.org https URLs are accepted."""
        req = IngestRequest(repo_url="https://codeberg.org/user/repo")
        assert req.repo_url == "https://codeberg.org/user/repo"
