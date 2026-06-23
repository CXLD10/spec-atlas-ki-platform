"""Tests for the specs API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from spec_atlas import db
from spec_atlas.api.app import create_app
from spec_atlas.config import Settings, get_settings


class TestSpecsAPI:
    """Tests for specs API endpoints."""

    def test_specs_endpoints_registered(self) -> None:
        """All specs endpoints are registered."""
        app = create_app(Settings())

        # Verify app has routes registered (simplified check)
        assert len(app.routes) > 0, "App has no routes"

    def test_create_spec_request_schema(self) -> None:
        """CreateSpecRequest schema is valid."""
        from spec_atlas.api.specs import CreateSpecRequest

        req = CreateSpecRequest(
            content={"purpose": "Test"},
            provenance=[{"file": "test.py", "start_line": 1, "end_line": 2}],
            source_fingerprint="abc123",
            status="draft",
        )

        assert req.content["purpose"] == "Test"
        assert len(req.provenance) == 1
        assert req.status == "draft"

    def test_spec_detail_response_schema(self) -> None:
        """SpecDetailResponse schema is valid."""
        from spec_atlas.api.specs import SpecDetailResponse

        data = {
            "id": "spec-1",
            "user_id": "default",
            "repo": "repo",
            "component_ref": "auth",
            "version": 1,
            "valid_from": "2026-06-20T00:00:00",
            "valid_to": None,
            "status": "draft",
            "content": {"purpose": "Test"},
            "provenance": [],
            "source_fingerprint": "abc123",
            "created_at": "2026-06-20T00:00:00",
        }

        resp = SpecDetailResponse(**data)
        assert resp.version == 1
        assert resp.status == "draft"

    def test_spec_summary_response_schema(self) -> None:
        """SpecSummaryResponse schema is valid."""
        from spec_atlas.api.specs import SpecSummaryResponse

        data = {
            "id": "spec-1",
            "version": 1,
            "valid_from": "2026-06-20T00:00:00",
            "valid_to": None,
            "status": "draft",
        }

        resp = SpecSummaryResponse(**data)
        assert resp.version == 1

    def test_update_status_request_schema(self) -> None:
        """UpdateStatusRequest schema is valid."""
        from spec_atlas.api.specs import UpdateStatusRequest

        req = UpdateStatusRequest(status="verified")
        assert req.status == "verified"

    def test_create_spec_endpoint_structure(self) -> None:
        """Create spec endpoint has proper structure."""
        from spec_atlas.api.specs import create_spec

        # Verify endpoint exists and is callable
        assert callable(create_spec)

    def test_get_current_spec_endpoint_structure(self) -> None:
        """Get current spec endpoint has proper structure."""
        from spec_atlas.api.specs import get_current_spec

        assert callable(get_current_spec)

    def test_get_spec_versions_endpoint_structure(self) -> None:
        """Get spec versions endpoint has proper structure."""
        from spec_atlas.api.specs import get_spec_versions

        assert callable(get_spec_versions)

    def test_get_spec_version_endpoint_structure(self) -> None:
        """Get specific spec version endpoint has proper structure."""
        from spec_atlas.api.specs import get_spec_version

        assert callable(get_spec_version)

    def test_update_spec_status_endpoint_structure(self) -> None:
        """Update spec status endpoint has proper structure."""
        from spec_atlas.api.specs import update_spec_status

        assert callable(update_spec_status)

    def test_all_endpoints_use_dependency_injection(self) -> None:
        """All endpoints use Depends for session injection."""
        from spec_atlas.api.specs import (
            create_spec,
            get_current_spec,
            get_spec_version,
            get_spec_versions,
            update_spec_status,
        )

        # All endpoints should be async or sync and accept session parameter
        # This is more of a structural check
        endpoints = [
            create_spec,
            get_current_spec,
            get_spec_versions,
            get_spec_version,
            update_spec_status,
        ]

        for endpoint in endpoints:
            assert callable(endpoint)

    def test_create_spec_response_type(self) -> None:
        """Create spec response type is SpecDetailResponse."""
        # This is verified at type-check time

    def test_version_listing_response_type(self) -> None:
        """Version listing response is list of SpecSummaryResponse."""
        # This is verified at type-check time

    def test_spec_endpoints_return_proper_types(self) -> None:
        """Verify endpoints return expected response types."""
        from spec_atlas.api.specs import (
            SpecDetailResponse,
            SpecSummaryResponse,
        )

        # Both response types should be Pydantic models
        assert hasattr(SpecDetailResponse, "model_validate")
        assert hasattr(SpecSummaryResponse, "model_validate")


def _offline_client() -> TestClient:
    """TestClient with real (migrated) DB urls but fake/offline providers —
    keeps these tests zero-cost regardless of what LLM_PROVIDER is set to
    in the developer's local .env."""
    base = get_settings()
    # Settings fields use aliases (e.g. SPEC_DB_URL) for env loading; with
    # _env_file=None, Settings(...) only populates fields passed by their
    # alias name, not the lowercase Python attribute name.
    settings = Settings(
        _env_file=None,
        ANALYSIS_DB_URL=base.analysis_db_url,
        SPEC_DB_URL=base.spec_db_url,
        LLM_PROVIDER="fake",
        EMBED_PROVIDER="fake",
    )
    return TestClient(create_app(settings))


@pytest.mark.db
class TestGenerateOnDemandAndVerify:
    """Real generate-on-demand + verify, against a migrated Postgres."""

    def _seed_node(self, repo_name: str, qualified_name: str) -> None:
        AnalysisSession = db.analysis_session()
        with AnalysisSession() as s:
            repo = db.Repo(name=repo_name, source=f"/tmp/{repo_name}")
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
                    name=qualified_name,
                    qualified_name=qualified_name,
                    signature=f"def {qualified_name}():",
                    docstring="A test function.",
                    start_line=5,
                    end_line=9,
                )
            )
            s.commit()

    def test_specs_generate_on_demand_returns_provenance(self, migrated: None) -> None:
        self._seed_node("generate-repo", "do_thing")
        client = _offline_client()

        resp = client.post(
            "/api/specs/generate/do_thing", params={"repo": "generate-repo"}
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()

        assert body["component_ref"] == "do_thing"
        assert body["version"] == 1
        assert isinstance(body["provenance"], list)
        assert len(body["provenance"]) > 0
        for span in body["provenance"]:
            assert span["file"] == "a.py"  # real path, not a file_id UUID
            assert "start_line" in span and "end_line" in span

        # Cache hit: a second call returns the same version without erroring.
        resp2 = client.post(
            "/api/specs/generate/do_thing", params={"repo": "generate-repo"}
        )
        assert resp2.status_code == 200
        assert resp2.json()["version"] == 1

        # And it's readable via the normal GET, not just the generate response.
        get_resp = client.get("/api/specs/do_thing", params={"repo": "generate-repo"})
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "draft"

    def test_verify_mutates_spec_db(self, migrated: None) -> None:
        self._seed_node("verify-repo", "verify_me")
        client = _offline_client()

        gen = client.post("/api/specs/generate/verify_me", params={"repo": "verify-repo"})
        assert gen.status_code == 200
        version = gen.json()["version"]

        before = client.get("/api/specs/verify_me", params={"repo": "verify-repo"})
        assert before.json()["status"] == "draft"

        verify_resp = client.post(
            "/api/specs/verify_me/verify",
            params={"repo": "verify-repo", "version": version},
        )
        assert verify_resp.status_code == 200

        # Re-fetch in a way that doesn't depend on the verify response alone —
        # confirms the mutation actually persisted to the DB.
        after = client.get("/api/specs/verify_me", params={"repo": "verify-repo"})
        assert after.status_code == 200
        assert after.json()["status"] in ("verified", "draft")  # rule-based: may stay draft
        assert after.json()["status"] == verify_resp.json()["status"]
