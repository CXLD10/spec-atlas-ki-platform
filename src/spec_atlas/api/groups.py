"""Groups API endpoints (group hierarchy browsing)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict

from spec_atlas.groups.clustering import GroupClustering

if TYPE_CHECKING:
    pass

router = APIRouter(prefix="/api/groups", tags=["groups"])


class GroupDetailResponse(BaseModel):
    """Group details with children and member specs."""

    id: str
    path: str
    title: str
    summary_md: str | None
    level: int
    parent_id: str | None
    children: list[str]  # List of child group paths
    member_spec_refs: list[str]  # List of spec component_refs
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class GroupTreeNode(BaseModel):
    """Single node in group tree hierarchy."""

    id: str
    path: str
    title: str
    children: list[GroupTreeNode] = []

    model_config = ConfigDict(from_attributes=True)


class GroupTreeResponse(BaseModel):
    """Root group tree response."""

    root: GroupTreeNode | None


def get_analysis_session(request: Request):
    """Get analysis database session from app state.

    Args:
        request: FastAPI request object.

    Returns:
        Session factory from app state.

    Raises:
        HTTPException: If database not configured.
    """
    if not request.app.state.analysis_session_factory:
        raise HTTPException(status_code=503, detail="Analysis database not configured")
    return request.app.state.analysis_session_factory


@router.get("", response_model=GroupTreeResponse)
def get_group_tree(
    repo: str = Query("default"),
    session_factory=Depends(get_analysis_session),  # noqa: B008
) -> GroupTreeResponse:
    """Fetch the group tree hierarchy (root + nested children).

    GET /api/groups?repo=default

    Returns:
    {
        "root": {
            "id": "group-1",
            "path": "root",
            "title": "Root",
            "children": [
                {
                    "id": "group-2",
                    "path": "auth",
                    "title": "Authentication",
                    "children": [...]
                }
            ]
        }
    }
    """
    session = session_factory()
    try:
        # Fetch root group for repo
        # Note: for v1, we assume one repo per database instance
        root = GroupClustering.get_group_tree(
            repo_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),  # Placeholder
            session=session,
        )

        if not root:
            return GroupTreeResponse(root=None)

        # Build tree recursively
        def build_tree_node(group) -> GroupTreeNode:
            children = GroupClustering.get_child_groups(group.id, session)
            return GroupTreeNode(
                id=str(group.id),
                path=group.path,
                title=group.title or group.path,
                children=[build_tree_node(child) for child in children],
            )

        return GroupTreeResponse(root=build_tree_node(root))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch group tree: {str(e)}") from e
    finally:
        session.close()


@router.get("/{group_id}", response_model=GroupDetailResponse)
def get_group_detail(
    group_id: str,
    repo: str = Query("default"),
    session_factory=Depends(get_analysis_session),  # noqa: B008
) -> GroupDetailResponse:
    """Fetch a single group with its details.

    GET /api/groups/{group_id}?repo=default

    Returns:
    {
        "id": "group-1",
        "path": "auth",
        "title": "Authentication",
        "summary_md": "Handles user authentication...",
        "level": 1,
        "parent_id": "group-0",
        "children": ["auth/tokens", "auth/sessions"],
        "member_spec_refs": ["AuthService", "TokenValidator"],
        "created_at": "2026-06-19T..."
    }
    """
    session = session_factory()
    try:
        # Convert string group_id to UUID
        try:
            group_uuid = uuid.UUID(group_id)
        except ValueError as ve:
            raise HTTPException(status_code=400, detail="Invalid group ID format") from ve

        # Fetch the group
        from spec_atlas.db.analysis import Group

        group = session.query(Group).filter(Group.id == group_uuid).first()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        # Fetch child groups
        child_groups = GroupClustering.get_child_groups(group_uuid, session)
        children_paths = [child.path for child in child_groups]

        return GroupDetailResponse(
            id=str(group.id),
            path=group.path,
            title=group.title or group.path,
            summary_md=group.summary_md,
            level=group.level or 0,
            parent_id=str(group.parent_id) if group.parent_id else None,
            children=children_paths,
            member_spec_refs=group.member_spec_refs or [],
            created_at=group.created_at.isoformat() if group.created_at else "",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch group: {str(e)}") from e
    finally:
        session.close()
