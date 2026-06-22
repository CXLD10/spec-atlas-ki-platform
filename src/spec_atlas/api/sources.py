"""Sources API: git history and Jira integration endpoints."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["sources"])


@router.get("/git/history")
async def get_git_history(
    project_id: str = Query(...),
    file_path: Optional[str] = Query(None),
    limit: int = Query(10),
) -> dict:
    """Get git commit history for reference.

    Args:
        project_id: Project identifier.
        file_path: Optional file path to filter commits.
        limit: Maximum commits to return.

    Returns:
        Dict with commits list or error.
    """
    try:
        # Mock implementation for demo
        # In production, this would query the actual git repository
        commits = [
            {
                "sha": "a864233",
                "short_sha": "a864233",
                "message": "feat(ingest): Excel and Markdown adapters",
            },
            {
                "sha": "8251a59",
                "short_sha": "8251a59",
                "message": "docs: add HANDOFF note for Phase 3 adapters",
            },
            {
                "sha": "72e1150",
                "short_sha": "72e1150",
                "message": "feat(frontend): Phase 3.5 Sprint 1 - Core UI",
            },
            {
                "sha": "8a71935",
                "short_sha": "8a71935",
                "message": "feat(graph): improve node navigation for Ask feature",
            },
            {
                "sha": "2a04c9a",
                "short_sha": "2a04c9a",
                "message": "feat(frontend): MCP modal + Specify Tool page",
            },
        ]

        return {
            "commits": commits[:limit],
            "file_path": file_path,
            "total": len(commits),
            "project_id": project_id,
        }
    except Exception as e:
        logger.error(f"Error getting git history: {e}")
        return {
            "commits": [],
            "error": f"Failed to get git history: {str(e)}",
            "project_id": project_id,
        }


@router.get("/jira/issues")
async def get_jira_issues(
    project_id: str = Query(...),
    query: str = Query(""),
    limit: int = Query(5),
) -> dict:
    """Get Jira issues related to a query.

    Args:
        project_id: Project identifier.
        query: Search query to filter issues.
        limit: Maximum issues to return.

    Returns:
        Dict with issues list or error.
    """
    try:
        # Mock implementation for demo
        # In production, this would load Jira export JSON or query Jira API
        all_issues = [
            {
                "key": "ATLAS-123",
                "summary": "Add spec generation for components",
                "status": "Done",
                "created": "2024-06-01",
                "url": "https://jira.example.com/browse/ATLAS-123",
            },
            {
                "key": "ATLAS-124",
                "summary": "Implement git history tracking",
                "status": "In Progress",
                "created": "2024-06-15",
                "url": "https://jira.example.com/browse/ATLAS-124",
            },
            {
                "key": "ATLAS-125",
                "summary": "Add MCP server integration",
                "status": "Done",
                "created": "2024-06-10",
                "url": "https://jira.example.com/browse/ATLAS-125",
            },
            {
                "key": "ATLAS-126",
                "summary": "Deep Wiki fallback for answers",
                "status": "In Progress",
                "created": "2024-06-20",
                "url": "https://jira.example.com/browse/ATLAS-126",
            },
        ]

        # Filter by query if provided
        if query:
            filtered = [
                i
                for i in all_issues
                if query.lower() in i["summary"].lower()
                or query.lower() in i["key"].lower()
            ]
        else:
            filtered = all_issues

        return {
            "issues": filtered[:limit],
            "total": len(filtered),
            "query": query,
            "project_id": project_id,
        }
    except Exception as e:
        logger.error(f"Error getting Jira issues: {e}")
        return {
            "issues": [],
            "error": f"Failed to get Jira issues: {str(e)}",
            "project_id": project_id,
        }
