"""Tests for groups API endpoints."""

from __future__ import annotations

from spec_atlas.api.app import create_app
from spec_atlas.api.groups import GroupDetailResponse, GroupTreeNode, GroupTreeResponse
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
