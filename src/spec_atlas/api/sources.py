"""Sources API: real source aggregation (repos + documents), plus git history
and Jira integration endpoints (still mocked — see SYSTEM_STATUS_AND_REMEDIATION.md)."""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from spec_atlas.db.analysis import Group, IngestJob, Node, Repo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["sources"])


def get_analysis_session(request: Request) -> Session:
    factory = request.app.state.analysis_session_factory
    if not factory:
        raise HTTPException(status_code=503, detail="Analysis database not configured")
    session = factory()
    try:
        yield session
    finally:
        session.close()


def get_spec_session(request: Request) -> Session:
    factory = request.app.state.spec_session_factory
    if not factory:
        raise HTTPException(status_code=503, detail="Spec database not configured")
    session = factory()
    try:
        yield session
    finally:
        session.close()


class SourceStats(BaseModel):
    entities: int
    cards: int
    domains: int


class SourceResponse(BaseModel):
    """A Source: either an indexed repo or an ingested document.

    Matches frontend/src/lib/types.ts's Source interface. Document sources
    are not yet populated — document ingestion (POST /api/documents,
    SourceUnit persistence) is Phase 2 scope; this aggregates only repos
    until then (real data, just incomplete coverage — never fabricated).
    """

    id: str
    type: str  # "repo" | "document"
    name: str
    subtitle: str | None = None
    status: str  # "queued" | "indexing" | "ready" | "error"
    progress: int | None = None
    stats: SourceStats
    format: str | None = None
    updatedAt: str


_JOB_STATUS_TO_SOURCE_STATUS = {
    "queued": "queued",
    "in_progress": "indexing",
    "done": "ready",
    "error": "error",
}


def _repo_to_source(
    repo: Repo,
    analysis_session: Session,
    spec_session: Session | None,
    latest_job: IngestJob | None,
) -> SourceResponse:
    entities = analysis_session.query(Node).filter(Node.repo_id == repo.id).count()
    domains = analysis_session.query(Group).filter(Group.repo_id == repo.id).count()

    cards = 0
    if spec_session is not None:
        from spec_atlas.db.spec import Spec

        cards = (
            spec_session.query(Spec)
            .filter(Spec.repo == repo.name, Spec.valid_to.is_(None))
            .count()
        )

    if latest_job:
        status = _JOB_STATUS_TO_SOURCE_STATUS.get(latest_job.status, "ready")
        progress = latest_job.progress_pct
    else:
        # No matching ingest_jobs row (e.g. job already cleaned up) but the
        # repo exists, so indexing reached at least the point of creating it.
        status = "ready"
        progress = 100

    return SourceResponse(
        id=str(repo.id),
        type="repo",
        name=repo.name,
        subtitle=repo.source,
        status=status,
        progress=progress,
        stats=SourceStats(entities=entities, cards=cards, domains=domains),
        format="git",
        updatedAt=repo.updated_at.isoformat() if repo.updated_at else "",
    )


def _list_sources(analysis_session: Session, spec_session: Session | None) -> list[SourceResponse]:
    repos = analysis_session.query(Repo).order_by(Repo.created_at.desc()).all()

    # One query for the latest job per repo_url, instead of N+1.
    jobs_by_url: dict[str, IngestJob] = {}
    for job in analysis_session.query(IngestJob).order_by(IngestJob.created_at.desc()).all():
        jobs_by_url.setdefault(job.repo_url, job)

    return [
        _repo_to_source(repo, analysis_session, spec_session, jobs_by_url.get(repo.source))
        for repo in repos
    ]


@router.get("/sources", response_model=list[SourceResponse])
def list_sources(
    analysis_session: Session = Depends(get_analysis_session),  # noqa: B008
    spec_session: Session = Depends(get_spec_session),  # noqa: B008
) -> list[SourceResponse]:
    """List all sources (indexed repos; documents once Phase 2 lands)."""
    return _list_sources(analysis_session, spec_session)


@router.get("/sources/{source_id}", response_model=SourceResponse)
def get_source(
    source_id: str,
    analysis_session: Session = Depends(get_analysis_session),  # noqa: B008
    spec_session: Session = Depends(get_spec_session),  # noqa: B008
) -> SourceResponse:
    """Get a single source by id."""
    try:
        repo_uuid = uuid.UUID(source_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid source id") from e

    repo = analysis_session.query(Repo).filter(Repo.id == repo_uuid).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Source not found")

    jobs_by_url: dict[str, IngestJob] = {}
    for job in (
        analysis_session.query(IngestJob)
        .filter(IngestJob.repo_url == repo.source)
        .order_by(IngestJob.created_at.desc())
        .all()
    ):
        jobs_by_url.setdefault(job.repo_url, job)

    return _repo_to_source(repo, analysis_session, spec_session, jobs_by_url.get(repo.source))


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
