"""Tests for groups API endpoints."""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException

from spec_atlas import db
from spec_atlas.api.app import create_app
from spec_atlas.api.groups import (
    GroupDetailResponse,
    GroupTreeNode,
    GroupTreeResponse,
    get_group_tree,
)
from spec_atlas.config import Settings


class TestGroupsAPI:
    """Tests for groups API endpoints."""

    def test_groups_endpoints_registered(self) -> None:
        """Groups endpoints are registered in app."""
        app = create_app(Settings())
        assert len(app.routes) > 0

    def test_group_detail_response_schema(self) -> None:
        """GroupDetailResponse schema is valid."""
        response = GroupDetailResponse(
            id="group-1",
            path="auth",
            title="Authentication",
            summary_md="Handles user auth...",
            level=1,
            parent_id="group-0",
            children=["auth/tokens", "auth/sessions"],
            member_spec_refs=["AuthService"],
            created_at="2026-06-20T00:00:00",
        )

        assert response.id == "group-1"
        assert response.path == "auth"
        assert response.title == "Authentication"
        assert len(response.children) == 2
        assert len(response.member_spec_refs) == 1

    def test_group_tree_node_schema(self) -> None:
        """GroupTreeNode schema with nested children."""
        child = GroupTreeNode(id="child-1", path="auth/tokens", title="Tokens", children=[])
        parent = GroupTreeNode(id="parent-1", path="auth", title="Auth", children=[child])

        assert parent.path == "auth"
        assert len(parent.children) == 1
        assert parent.children[0].path == "auth/tokens"

    def test_group_tree_response_schema(self) -> None:
        """GroupTreeResponse schema with root."""
        root = GroupTreeNode(id="root", path="root", title="Root", children=[])
        response = GroupTreeResponse(root=root)

        assert response.root is not None
        assert response.root.path == "root"

    def test_group_tree_response_with_no_root(self) -> None:
        """GroupTreeResponse can have None root."""
        response = GroupTreeResponse(root=None)
        assert response.root is None


@pytest.mark.db
class TestGroupsResolveRepoName:
    """Regression: GET /api/groups?repo=<name> must resolve the real repo,
    not a hardcoded placeholder UUID (api/groups.py used to always query
    00000000-0000-0000-0000-000000000001, so real ingested repos never
    matched and the tree was always empty)."""

    def test_groups_resolves_repo_name(self, migrated: None) -> None:
        AnalysisSession = db.analysis_session()
        with AnalysisSession() as session:
            repo_a = db.Repo(name="repo-a", source="/tmp/repo-a")
            repo_b = db.Repo(name="repo-b", source="/tmp/repo-b")
            session.add_all([repo_a, repo_b])
            session.flush()

            root_a = db.Group(
                repo_id=repo_a.id, parent_id=None, level=0, path="", title="repo-a"
            )
            root_b = db.Group(
                repo_id=repo_b.id, parent_id=None, level=0, path="", title="repo-b"
            )
            session.add_all([root_a, root_b])
            session.commit()

            response = get_group_tree(repo="repo-a", session_factory=lambda: session)
            assert response.root is not None
            assert response.root.title == "repo-a"

            response_b = get_group_tree(repo="repo-b", session_factory=lambda: session)
            assert response_b.root is not None
            assert response_b.root.title == "repo-b"

    def test_groups_unknown_repo_returns_404(self, migrated: None) -> None:
        AnalysisSession = db.analysis_session()
        with AnalysisSession() as session:
            with pytest.raises(HTTPException) as exc_info:
                get_group_tree(repo=f"does-not-exist-{uuid.uuid4()}", session_factory=lambda: session)
            assert exc_info.value.status_code == 404
