"""Ingest API endpoints (job tracking and code snippets).

Real work, not simulated: clones/validates the repo (``RepoResolver``), inventories
files with content hashes + LOC (``FileInventory``), and detects language per file
(``LanguageDetector``). Then runs the full analysis pipeline: symbol extraction
(parse/), edge building (graph/), group clustering (groups/), group summarization,
and embedding creation (embed/). Job state is persisted in the ``ingest_jobs`` table
via ``IngestJobStore`` — not an in-memory dict — so it survives process restarts.

URL validation (https-only, host allowlist) and path-traversal guarding
(``_safe_resolve_path``) were restored here after being dropped by a prior
regression (see T-017.1/T-017.2 in git history) — tests/api/test_security.py
and tests/api/test_rate_limiting.py cover them.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func

from spec_atlas.embed.pipeline import EmbeddingPipeline
from spec_atlas.graph.edges_crossfile import CrossFileEdgeExtractor
from spec_atlas.graph.edges_intrafile import IntraFileEdgeExtractor
from spec_atlas.groups.clustering import GroupClustering
from spec_atlas.groups.group_writer import GroupWriter
from spec_atlas.ingest.document_pipeline import (
    ADAPTERS_BY_FORMAT,
    detect_format,
    process_document_ingest_job,
)
from spec_atlas.ingest.inventory import FileInventory
from spec_atlas.ingest.job_store import IngestJobStore
from spec_atlas.ingest.language import LanguageDetector
from spec_atlas.ingest.manager import calculate_eta
from spec_atlas.ingest.resolver import RepoResolver
from spec_atlas.parse.python_symbols import PythonSymbolExtractor
from spec_atlas.parse.ts_symbols import TypeScriptSymbolExtractor
from spec_atlas.specify.batch_generator import BatchSpecGenerator
from spec_atlas.specify.spec_graph_builder import SpecGraphBuilder

MAX_DOCUMENT_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB

# Rate limiter (optional; requires slowapi) — mirrors api/answer.py's pattern.
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address)
    HAS_LIMITER = True
except ImportError:
    limiter = None
    HAS_LIMITER = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

ALLOWED_GIT_HOSTS = {"github.com", "gitlab.com", "gitea.io", "codeberg.org"}


def _safe_resolve_path(repo_root: Path, requested_file: str) -> Path:
    """Resolve ``requested_file`` within ``repo_root``, rejecting path traversal."""
    repo_root_resolved = repo_root.resolve()
    candidate = (repo_root / requested_file).resolve()
    try:
        candidate.relative_to(repo_root_resolved)
    except ValueError as err:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file path: {requested_file} (path traversal not allowed)",
        ) from err
    return candidate


def _apply_rate_limit(func):
    """Apply 5/hour rate limit to ingest endpoints when slowapi is available."""
    if HAS_LIMITER and limiter is not None:
        return limiter.limit("5/hour")(func)
    return func


def _update_phase_progress(
    session,
    job_id: str,
    phase_name: str,
    progress_pct: int,
) -> None:
    """Update job progress and track phase timing.

    This helper tracks phase start times and duration for ETA calculation.
    """
    from spec_atlas.db.analysis import IngestJob

    job = session.query(IngestJob).filter(IngestJob.id == job_id).first()
    if not job:
        return

    now = datetime.now(timezone.utc)

    # If this is a new phase, record the start time
    if job.current_phase != phase_name:
        # If there was a previous phase, record its duration
        if job.current_phase and job.phase_start_time:
            elapsed = (now - job.phase_start_time).total_seconds()
            if job.phase_durations is None:
                job.phase_durations = {}
            job.phase_durations[job.current_phase] = elapsed

        # Start the new phase
        job.current_phase = phase_name
        job.phase_start_time = now

    # Update progress
    job.progress_pct = progress_pct
    job.status = "in_progress"
    job.updated_at = now

    session.commit()


class IngestRequest(BaseModel):
    """Request model for starting an ingest job."""

    repo_url: str = Field(..., min_length=1, description="Repository URL")

    @field_validator("repo_url")
    @classmethod
    def validate_repo_url(cls, v: str) -> str:
        """Only https:// URLs to allowlisted git hosts (SSRF prevention)."""
        parsed = urlparse(v)
        if parsed.scheme != "https":
            raise ValueError(f"only https:// URLs are supported, got: {parsed.scheme}://")
        if parsed.hostname not in ALLOWED_GIT_HOSTS:
            raise ValueError(
                f"host not in allowlist: {parsed.hostname} "
                f"(allowed: {', '.join(sorted(ALLOWED_GIT_HOSTS))})"
            )
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "repo_url": "https://github.com/openai/openai-python",
            }
        }
    )


class JobStatus(BaseModel):
    """Response model for job status."""

    job_id: str
    status: str  # queued, in_progress, done, failed
    progress: int = Field(0, ge=0, le=100)
    repo_url: str
    created_at: str
    error: str | None = None
    eta_seconds: int | None = None  # Estimated seconds remaining
    show_warning: bool = False  # Whether to show a warning banner
    warning_message: str | None = None  # Warning message text


def _to_job_status(job) -> JobStatus:
    """Map an ``IngestJob`` DB row to the public ``JobStatus`` response shape."""
    # Calculate ETA if job is in progress
    eta_result = None
    if job.status == "in_progress" and job.progress_pct < 100:
        eta_result = calculate_eta(
            current_progress_pct=job.progress_pct,
            phase_durations=job.phase_durations or {},
            phase_start_time=job.phase_start_time,
            current_phase=job.current_phase,
        )

    return JobStatus(
        job_id=str(job.id),
        # The DB model uses "error"; the public API uses "failed" (matches the
        # frontend's IngestStatus union — see STATUS_REPORT.md §4).
        status="failed" if job.status == "error" else job.status,
        progress=job.progress_pct,
        repo_url=job.repo_url,
        created_at=job.created_at.isoformat() if job.created_at else "",
        error=job.error_message,
        eta_seconds=eta_result.get("eta_seconds") if eta_result else None,
        show_warning=eta_result.get("show_warning", False) if eta_result else False,
        warning_message=eta_result.get("warning_message") if eta_result else None,
    )


def _run_ingest_sync(
    job_id: str, repo_url: str, session_factory, spec_session_factory=None, llm_provider=None
) -> None:
    """Synchronous ingest work: resolve, inventory, detect languages, parse, cluster, embed,
    spec, and build graphs.

    Phases:
    1. Resolve git repo (10-40%)
    2. Inventory files (40-70%)
    3. Detect languages (70-75%)
    4. Extract symbols/nodes (75-80%)
    5. Extract edges (80-85%)
    6. Generate specs (85-88%)
    7. Form groups (88-92%)
    8. Summarize groups + write group.md files + link specs (92-96%) — done in
       one pass by GroupWriter.write_groups_for_repo (skipped if no spec DB).
    9. Embed groups (96-98%)
    10. Build spec graph (98-99%)

    Runs off the event loop via ``asyncio.to_thread`` (clone + file I/O block).
    """
    session = session_factory()
    try:
        _update_phase_progress(session, job_id, "resolve", 10)

        repo_metadata = RepoResolver.resolve_git(repo_url)
        _update_phase_progress(session, job_id, "inventory", 40)

        repo, files = FileInventory.scan(repo_metadata, repo_metadata.file_paths, session)

        # Harvest recent commits and persist on the Repo row so GET /api/git/history
        # can serve real data without requiring the ephemeral clone to still exist.
        commits = _harvest_commits(repo_metadata.working_dir)
        if commits:
            repo.recent_commits = commits
            session.commit()

        _update_phase_progress(session, job_id, "inventory", 70)

        for file in files:
            file.language = LanguageDetector.detect(file.path)
        session.commit()
        _update_phase_progress(session, job_id, "languages", 75)

        logger.info(
            f"Job {job_id}: resolved repo {repo.name!r} "
            f"({len(files)} files at commit {repo_metadata.commit})"
        )

        # Phase 4: Extract symbols from source files (L1)
        _extract_symbols(job_id, repo.id, repo_metadata.working_dir, files, session)
        _update_phase_progress(session, job_id, "symbols", 80)

        # Phase 5: Extract edges between symbols (L1)
        _extract_edges(job_id, repo.id, repo_metadata.working_dir, files, session)
        _update_phase_progress(session, job_id, "edges", 85)

        # Phase 6: Generate specs from code graph (L2) - optional, skip if no spec session
        if spec_session_factory and llm_provider:
            try:
                spec_session = spec_session_factory()
                BatchSpecGenerator.generate_for_repo(
                    repo.id,
                    repo_metadata.working_dir,
                    user_id="default",
                    analysis_session=session,
                    spec_session=spec_session,
                    llm_provider=llm_provider,
                )
                spec_session.close()
            except Exception as e:
                logger.warning(f"Spec generation failed, continuing: {e}")
        _update_phase_progress(session, job_id, "specs", 88)

        # Phase 7-9: Group clustering (L4) - optional, skip on error
        groups = []
        try:
            groups = _form_groups(job_id, repo.id, repo_metadata.working_dir, session)
            _update_phase_progress(session, job_id, "groups", 92)

            # Phase 8: Summarize groups, write group.md files, and link specs
            if spec_session_factory:
                try:
                    from spec_atlas.config import get_settings as _get_settings
                    spec_session = spec_session_factory()
                    GroupWriter.write_groups_for_repo(
                        repo.id,
                        repo_metadata.working_dir,
                        session,
                        spec_session,
                        llm_provider,
                        docs_dir=_get_settings().docs_dir,
                    )
                    spec_session.close()
                except Exception as e:
                    logger.warning(f"Group writing failed, continuing: {e}")
            _update_phase_progress(session, job_id, "summarize", 96)

            # Phase 9: Embed groups
            _embed_groups(job_id, repo.id, groups, session)
            _update_phase_progress(session, job_id, "embed", 98)
        except Exception as e:
            logger.warning(f"Group clustering/embedding failed, continuing without groups: {e}")
            session.rollback()
            groups = []

        # Phase 10: Build spec graph (L3 edges from L1 edges)
        if spec_session_factory:
            try:
                spec_session = spec_session_factory()
                SpecGraphBuilder.build_spec_graph(
                    repo.id,
                    user_id="default",
                    analysis_session=session,
                    spec_session=spec_session,
                )
                spec_session.close()
            except Exception as e:
                logger.warning(f"Spec graph building failed, continuing: {e}")
        _update_phase_progress(session, job_id, "spec_graph", 99)

        # Phase 11: Drift detection — re-fingerprint specs after re-ingest
        if spec_session_factory:
            try:
                from spec_atlas.drift.detector import DriftDetector

                spec_session = spec_session_factory()
                drift_report = DriftDetector.detect_drift(repo.id, spec_session)
                if not drift_report.is_clean():
                    stale_count = DriftDetector.mark_stale(drift_report, spec_session)
                    logger.info(
                        f"Job {job_id}: drift detection found "
                        f"{stale_count} stale spec(s) for repo {repo.name!r}"
                    )
                spec_session.close()
            except Exception as e:
                logger.warning(f"Drift detection failed, continuing: {e}")
        _update_phase_progress(session, job_id, "drift", 100)

        IngestJobStore.update_job_status(session, job_id, status="done", progress_pct=100)

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        IngestJobStore.update_job_status(
            session, job_id, status="error", progress_pct=0, error_message=str(e)
        )
    finally:
        session.close()


async def _process_ingest_job(
    job_id: str, repo_url: str, session_factory, spec_session_factory=None, llm_provider=None
) -> None:
    """Background task: real ingest work, run off the event loop."""
    await asyncio.to_thread(
        _run_ingest_sync, job_id, repo_url, session_factory, spec_session_factory, llm_provider
    )


def _harvest_commits(repo_path: str, limit: int = 100) -> list[dict]:
    """Run git log against the cloned working dir and return structured commit dicts.

    The initial clone uses --depth=1, so we try to fetch more history first.
    Failure (air-gapped CI, no remote) is silent — the ingest still succeeds.
    """
    subprocess.run(
        ["git", "-C", repo_path, "fetch", "--depth=100"],
        capture_output=True,
        timeout=60,
    )  # best-effort; ignore returncode
    result = subprocess.run(
        ["git", "-C", repo_path, "log", f"--max-count={limit}",
         "--pretty=format:%H\x1f%s\x1f%an\x1f%ai"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return []
    commits = []
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        parts = line.split("\x1f", 3)
        sha = parts[0] if parts else ""
        if not sha:
            continue
        commits.append({
            "sha": sha,
            "short_sha": sha[:7],
            "message": parts[1] if len(parts) > 1 else "",
            "author": parts[2] if len(parts) > 2 else "",
            "date": parts[3] if len(parts) > 3 else "",
        })
    return commits


def _extract_symbols(job_id: str, repo_id, repo_path: str, files, session) -> None:
    """Extract symbols (functions, classes) from source files."""
    from spec_atlas.db.analysis import Node

    count = 0
    for file in files:
        if not file.language:
            continue

        file_full_path = Path(repo_path) / file.path
        try:
            content = file_full_path.read_text(errors="ignore")
        except Exception as e:
            logger.warning(f"Could not read {file.path}: {e}")
            continue

        symbols = []
        if file.language == "python":
            try:
                symbols = PythonSymbolExtractor.extract(file.path, content)
            except Exception as e:
                logger.warning(f"Failed to extract Python symbols from {file.path}: {e}")
        elif file.language in ("javascript", "typescript", "jsx", "tsx"):
            try:
                symbols = TypeScriptSymbolExtractor.extract(file.path, content, file.language)
            except Exception as e:
                logger.warning(f"Failed to extract symbols from {file.path}: {e}")
        else:
            logger.debug(f"No symbol extractor for language {file.language}")

        # Create Node objects for each symbol (with deduplication)
        for sym in symbols:
            # Check if this node already exists
            existing = (
                session.query(Node)
                .filter(
                    Node.repo_id == repo_id,
                    Node.language == file.language,
                    Node.qualified_name == sym.qualified_name,
                    Node.kind == sym.kind,
                )
                .first()
            )

            if existing:
                # Update existing node
                existing.start_line = sym.start_line
                existing.end_line = sym.end_line
                existing.docstring = getattr(sym, "docstring", None)
                existing.signature = getattr(sym, "signature", None)
                session.merge(existing)
            else:
                # Create new node
                node = Node(
                    repo_id=repo_id,
                    file_id=file.id,
                    kind=sym.kind,
                    name=sym.name,
                    qualified_name=sym.qualified_name,
                    language=file.language,
                    signature=getattr(sym, "signature", None),
                    docstring=getattr(sym, "docstring", None),
                    start_line=sym.start_line,
                    end_line=sym.end_line,
                )
                session.add(node)
            count += 1

    session.commit()
    logger.info(f"Job {job_id}: extracted {count} symbols")


def _extract_edges(job_id: str, repo_id, repo_path: str, files, session) -> None:
    """Extract edges (calls, imports) between symbols."""
    from spec_atlas.db.analysis import Node

    count = 0

    # Build maps of nodes and file contents for edge extraction
    nodes_by_file = {}
    file_contents = {}

    for file in files:
        if not file.language:
            continue

        file_full_path = Path(repo_path) / file.path
        try:
            content = file_full_path.read_text(errors="ignore")
            file_contents[file.id] = content
        except Exception as e:
            logger.warning(f"Could not read {file.path}: {e}")
            continue

        # Get nodes for this file
        file_nodes = session.query(Node).filter(Node.file_id == file.id).all()
        nodes_by_file[file.id] = file_nodes

    # Extract intra-file edges (within a file)
    for file in files:
        if file.id not in file_contents or file.id not in nodes_by_file:
            continue

        try:
            edges = IntraFileEdgeExtractor.extract(
                file.id,
                file.path,
                file.language,
                nodes_by_file[file.id],
                file_contents[file.id],
            )
            for edge in edges:
                session.add(edge)
                count += 1
        except Exception as e:
            logger.warning(f"Failed to extract intra-file edges from {file.path}: {e}")

    session.commit()

    # Extract cross-file edges (imports, dependencies)
    try:
        edges = CrossFileEdgeExtractor.extract(repo_id, files, nodes_by_file, file_contents)
        for edge in edges:
            session.add(edge)
            count += 1
        session.commit()
    except Exception as e:
        logger.warning(f"Failed to extract cross-file edges: {e}")

    logger.info(f"Job {job_id}: extracted {count} edges")


def _form_groups(job_id: str, repo_id, repo_path: str, session) -> list:
    """Form groups from directory structure."""
    try:
        root_group, node_to_group_map = GroupClustering.cluster_from_directory(
            repo_id, repo_path, session
        )

        # Collect all groups
        from spec_atlas.db.analysis import Group

        groups = session.query(Group).filter(Group.repo_id == repo_id).all()

        session.commit()
        logger.info(f"Job {job_id}: formed {len(groups)} groups")
        return groups
    except Exception as e:
        logger.warning(f"Group clustering failed: {e}")
        return []


def _embed_groups(job_id: str, repo_id, groups: list, session) -> None:
    """Create embeddings for group summaries."""
    try:
        from spec_atlas.embed import get_embedding_provider

        embed_provider = get_embedding_provider()
        embeddings = EmbeddingPipeline.embed_groups(repo_id, groups, embed_provider, session)

        logger.info(f"Job {job_id}: created {len(embeddings)} embeddings")
    except Exception as e:
        logger.warning(f"Embedding failed: {e}")


def _get_session_factory(request: Request):
    factory = request.app.state.analysis_session_factory
    if not factory:
        raise HTTPException(status_code=503, detail="Analysis database not configured")
    return factory


@router.post("/ingest", response_model=JobStatus)
@_apply_rate_limit
async def start_ingest(
    request: Request,
    body: IngestRequest,
    background_tasks: BackgroundTasks,
):
    """
    Start indexing a repository.

    - **repo_url**: URL to a GitHub/GitLab repo or local path

    Returns a job_id to poll for status.
    """
    if not body.repo_url or not body.repo_url.strip():
        raise HTTPException(status_code=400, detail="repo_url is required")

    session_factory = _get_session_factory(request)
    spec_session_factory = None
    llm_provider = None

    # Get spec session factory and LLM provider from app state if available
    if hasattr(request.app.state, "spec_session_factory"):
        spec_session_factory = request.app.state.spec_session_factory
    if hasattr(request.app.state, "llm_provider"):
        llm_provider = request.app.state.llm_provider

    session = session_factory()
    try:
        # Check 3-repo limit per session
        from spec_atlas.db.analysis import Repo as RepoModel
        session_id = request.state.session_id
        repo_count = session.query(func.count(RepoModel.id)).filter(
            RepoModel.session_id == session_id
        ).scalar() or 0

        if repo_count >= 3:
            raise HTTPException(
                status_code=429,
                detail="Max 3 repositories per session. Delete one to add another."
            )

        job_id = IngestJobStore.create_job(session, body.repo_url)
        job = IngestJobStore.get_job(session, job_id)
        status_response = _to_job_status(job)
    finally:
        session.close()

    background_tasks.add_task(
        _process_ingest_job,
        job_id,
        body.repo_url,
        session_factory,
        spec_session_factory,
        llm_provider,
    )
    logger.info(f"Started ingest job {job_id} for {body.repo_url}")

    return status_response


@router.get("/ingest/{job_id}", response_model=JobStatus)
async def get_ingest_status(job_id: str, request: Request):
    """Get the status of an ingest job."""
    session_factory = _get_session_factory(request)

    session = session_factory()
    try:
        job = IngestJobStore.get_job(session, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return _to_job_status(job)
    finally:
        session.close()


@router.post("/documents", response_model=JobStatus)
@_apply_rate_limit
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),  # noqa: B008
):
    """Upload a PDF/Excel/Markdown document for ingestion.

    Runs the matching adapter (ingest/adapters/), persists SourceUnits with
    real locators (page/sheet+row/section), and embeds them so the content
    is retrievable and citable — mirrors POST /api/ingest's job tracking, so
    the same GET /api/ingest/:jobId polling and useIndexJob hook work
    unchanged for documents.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    source_format = detect_format(file.filename)
    if source_format is None or source_format not in ADAPTERS_BY_FORMAT:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type: {file.filename!r}. "
                f"Allowed: {', '.join(sorted({'.pdf', '.xlsx', '.md', '.markdown'}))}"
            ),
        )

    contents = await file.read()
    if len(contents) > MAX_DOCUMENT_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: max {MAX_DOCUMENT_UPLOAD_BYTES // (1024 * 1024)} MB",
        )
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Stage to a temp file the adapter can open by path; cleaned up by
    # run_document_ingest_sync once parsing finishes (success or failure).
    suffix = Path(file.filename).suffix
    fd, temp_path = tempfile.mkstemp(prefix="spec_atlas_doc_", suffix=suffix)
    with open(fd, "wb") as f:
        f.write(contents)

    session_factory = _get_session_factory(request)
    embed_provider = getattr(request.app.state, "embedding_provider", None)
    if not embed_provider:
        Path(temp_path).unlink(missing_ok=True)
        raise HTTPException(status_code=503, detail="Embedding provider not configured")

    session = session_factory()
    try:
        job_id = IngestJobStore.create_job(session, file.filename)
        job = IngestJobStore.get_job(session, job_id)
        status_response = _to_job_status(job)
    finally:
        session.close()

    background_tasks.add_task(
        process_document_ingest_job,
        job_id,
        temp_path,
        file.filename,
        source_format,
        session_factory,
        embed_provider,
    )
    logger.info(f"Started document ingest job {job_id} for {file.filename!r}")

    return status_response
