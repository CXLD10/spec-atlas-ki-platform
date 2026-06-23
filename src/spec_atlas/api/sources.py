"""Sources API: real source aggregation (repos + documents), plus git history
and Jira integration endpoints (still mocked — see SYSTEM_STATUS_AND_REMEDIATION.md)."""

from __future__ import annotations

import logging
import uuid
from typing import Optional

import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
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
    is_document = repo.source_format != "git"

    if is_document:
        from spec_atlas.db.analysis import SourceUnit

        entities = (
            analysis_session.query(SourceUnit).filter(SourceUnit.repo_id == repo.id).count()
        )
        domains = 0  # documents have no L4 group tree
    else:
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
        type="document" if is_document else "repo",
        name=repo.name,
        subtitle=repo.source,
        status=status,
        progress=progress,
        stats=SourceStats(entities=entities, cards=cards, domains=domains),
        format=repo.source_format,
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
    request: Request,
    project_id: str = Query(...),
    file_path: Optional[str] = Query(None),
    limit: int = Query(10),
) -> dict:
    """Get git commit history harvested at ingest time from ``repos.recent_commits``.

    Args:
        project_id: Repo name or UUID.
        file_path: Optional keyword filter applied to commit messages.
        limit: Maximum commits to return.
    """
    factory = request.app.state.analysis_session_factory
    if not factory:
        return {"commits": [], "error": "Database not configured", "project_id": project_id}

    session = factory()
    try:
        repo: Repo | None = None
        try:
            repo_uuid = uuid.UUID(project_id)
            repo = session.query(Repo).filter(Repo.id == repo_uuid).first()
        except ValueError:
            repo = session.query(Repo).filter(Repo.name == project_id).first()

        if not repo or not repo.recent_commits:
            return {"commits": [], "total": 0, "file_path": file_path, "project_id": project_id}

        commits: list[dict] = list(repo.recent_commits)

        if file_path:
            kw = file_path.lower()
            commits = [c for c in commits if kw in c.get("message", "").lower()]

        return {
            "commits": commits[:limit],
            "file_path": file_path,
            "total": len(commits),
            "project_id": project_id,
        }
    except Exception as e:
        logger.error(f"Error getting git history: {e}")
        return {"commits": [], "error": str(e), "project_id": project_id}
    finally:
        session.close()


@router.get("/jira/issues")
async def get_jira_issues(
    request: Request,
    project_id: str = Query(...),
    query: str = Query(""),
    limit: int = Query(5),
) -> dict:
    """Get Jira issues indexed as SourceUnits (source_type='jira').

    Args:
        project_id: Project key or repo name (filters by source_id if provided).
        query: Keyword filter applied to issue text.
        limit: Maximum issues to return.
    """
    factory = request.app.state.analysis_session_factory
    if not factory:
        return {"issues": [], "error": "Database not configured", "project_id": project_id}

    from spec_atlas.db.analysis import SourceUnit

    session = factory()
    try:
        q = session.query(SourceUnit).filter(SourceUnit.source_type == "jira")
        units = q.all()

        issues = []
        kw = query.lower() if query else ""
        for unit in units:
            if kw and kw not in unit.text.lower():
                continue
            struct: dict = unit.structure or {}
            issues.append({
                "key": struct.get("key", unit.section or ""),
                "summary": struct.get("summary", ""),
                "status": struct.get("status", ""),
                "created": struct.get("created", ""),
                "url": struct.get("url", ""),
            })

        return {
            "issues": issues[:limit],
            "total": len(issues),
            "query": query,
            "project_id": project_id,
        }
    except Exception as e:
        logger.error(f"Error getting Jira issues: {e}")
        return {"issues": [], "error": str(e), "project_id": project_id}
    finally:
        session.close()


@router.post("/jira/import")
async def import_jira_export(
    request: Request,
    file: UploadFile = File(...),  # noqa: B008
) -> dict:
    """Import a Jira export JSON file and index issues as SourceUnits.

    The JSON can be a list of issue objects or ``{"issues": [...]}`` — the
    canonical format produced by Jira's "Export to JSON" action.  Each issue
    must have at least ``key`` and ``summary`` fields.  Import is idempotent:
    re-uploading the same export skips issues that already have a matching
    ``locator`` (``jira:<KEY>``).

    Returns a summary with the project key, repo_id, and count of new units.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        payload = json.loads(contents)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {exc}") from exc

    issues: list[dict] = payload if isinstance(payload, list) else payload.get("issues", [])
    if not issues:
        raise HTTPException(status_code=422, detail="No issues found in the uploaded JSON")

    # Derive project key from first issue's key (e.g. "ATLAS-123" → "ATLAS")
    first_key: str = issues[0].get("key", "UNKNOWN")
    project_key = first_key.rsplit("-", 1)[0] if "-" in first_key else first_key

    factory = request.app.state.analysis_session_factory
    if not factory:
        raise HTTPException(status_code=503, detail="Analysis database not configured")

    # Write to a temp file so JiraImporter can work from disk (consistent with
    # DocumentPipeline's contract — adapters open by path, not by in-memory bytes)
    fd, tmp_path = tempfile.mkstemp(prefix="spec_atlas_jira_", suffix=".json")
    try:
        import os
        with os.fdopen(fd, "wb") as fh:
            fh.write(contents)

        from spec_atlas.jira.importer import JiraImporter

        session = factory()
        try:
            repo_id, count = JiraImporter.import_from_file(tmp_path, project_key, session)
        finally:
            session.close()
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return {"project_key": project_key, "repo_id": repo_id, "indexed": count}
