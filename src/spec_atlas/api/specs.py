"""Spec store API endpoints (L2/L3 specs and spec graph)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from spec_atlas.db.analysis import Edge, Node
from spec_atlas.spec.store import SpecStore
from spec_atlas.specify.engine import SpecifyEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/specs", tags=["specs"])


def get_spec_session(request: Request) -> Session:
    """Get Spec DB session from app state."""
    factory = request.app.state.spec_session_factory
    if not factory:
        raise HTTPException(status_code=503, detail="Spec database not configured")
    session = factory()
    try:
        yield session
    finally:
        session.close()


def get_analysis_session(request: Request) -> Session:
    """Get Analysis DB session from app state."""
    factory = request.app.state.analysis_session_factory
    if not factory:
        raise HTTPException(status_code=503, detail="Analysis database not configured")
    session = factory()
    try:
        yield session
    finally:
        session.close()


def get_llm_provider(request: Request):
    """Get LLM provider from app state."""
    provider = request.app.state.llm_provider
    if not provider:
        raise HTTPException(status_code=503, detail="LLM provider not configured")
    return provider


class SpecDetailResponse(BaseModel):
    """Full spec details."""

    id: str
    user_id: str
    repo: str
    component_ref: str
    version: int
    valid_from: str
    valid_to: str | None
    status: str
    content: dict
    provenance: list
    source_fingerprint: str | None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class SpecSummaryResponse(BaseModel):
    """Lightweight spec summary for version listing."""

    id: str
    version: int
    valid_from: str
    valid_to: str | None
    status: str

    model_config = ConfigDict(from_attributes=True)


class CreateSpecRequest(BaseModel):
    """Request to create a new spec."""

    content: dict
    provenance: list | None = None
    source_fingerprint: str | None = None
    status: str = "draft"


class UpdateStatusRequest(BaseModel):
    """Request to update spec status."""

    status: str


@router.post("", response_model=SpecDetailResponse)
def create_spec(
    repo: str = Query(...),
    component_ref: str = Query(...),
    request: CreateSpecRequest = None,
    session: Session = Depends(get_spec_session),  # noqa: B008
) -> SpecDetailResponse:
    """Create a new spec version.

    Args:
        repo: Repository name.
        component_ref: Component reference (qualified_name or group path).
        request: Spec content and metadata.
        session: Spec DB session.

    Returns:
        The created spec with version number.
    """
    if not session:
        raise HTTPException(status_code=500, detail="Database session not available")

    store = SpecStore(session)
    spec = store.create(
        user_id="default",
        repo=repo,
        component_ref=component_ref,
        spec_content=request.content,
        provenance=request.provenance,
        source_fingerprint=request.source_fingerprint,
        status=request.status,
    )

    return SpecDetailResponse.model_validate(spec)


@router.get("/{component_ref}", response_model=SpecDetailResponse)
def get_current_spec(
    component_ref: str,
    repo: str = Query(...),
    session: Session = Depends(get_spec_session),  # noqa: B008
) -> SpecDetailResponse:
    """Get the current version of a spec.

    Args:
        component_ref: Component reference.
        repo: Repository name.
        session: Spec DB session.

    Returns:
        The current spec version.

    Raises:
        HTTPException: 404 if spec not found.
    """
    if not session:
        raise HTTPException(status_code=500, detail="Database session not available")

    store = SpecStore(session)
    spec = store.get_current("default", repo, component_ref)

    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found") from None

    return SpecDetailResponse.model_validate(spec)


@router.get("/{component_ref}/versions", response_model=list[SpecSummaryResponse])
def get_spec_versions(
    component_ref: str,
    repo: str = Query(...),
    session: Session = Depends(get_spec_session),  # noqa: B008
) -> list[SpecSummaryResponse]:
    """Get all versions of a spec.

    Args:
        component_ref: Component reference.
        repo: Repository name.
        session: Spec DB session.

    Returns:
        List of spec summaries (newest first).
    """
    if not session:
        raise HTTPException(status_code=500, detail="Database session not available")

    store = SpecStore(session)
    specs = store.get_all_versions("default", repo, component_ref)

    if not specs:
        raise HTTPException(status_code=404, detail="No specs found") from None

    return [SpecSummaryResponse.model_validate(s) for s in specs]


@router.get("/{component_ref}/v/{version}", response_model=SpecDetailResponse)
def get_spec_version(
    component_ref: str,
    version: int,
    repo: str = Query(...),
    session: Session = Depends(get_spec_session),  # noqa: B008
) -> SpecDetailResponse:
    """Get a specific version of a spec.

    Args:
        component_ref: Component reference.
        version: Version number.
        repo: Repository name.
        session: Spec DB session.

    Returns:
        The spec at that version.

    Raises:
        HTTPException: 404 if not found.
    """
    if not session:
        raise HTTPException(status_code=500, detail="Database session not available")

    store = SpecStore(session)
    spec = store.get_version("default", repo, component_ref, version)

    if not spec:
        raise HTTPException(status_code=404, detail="Spec version not found") from None

    return SpecDetailResponse.model_validate(spec)


@router.patch("/{component_ref}", response_model=SpecDetailResponse)
def update_spec_status(
    component_ref: str,
    version: int = Query(...),
    repo: str = Query(...),
    request: UpdateStatusRequest = None,
    session: Session = Depends(get_spec_session),  # noqa: B008
) -> SpecDetailResponse:
    """Update the status of a spec version.

    Args:
        component_ref: Component reference.
        version: Version number.
        repo: Repository name.
        request: New status.
        session: Spec DB session.

    Returns:
        The updated spec.

    Raises:
        HTTPException: 404 if spec not found or 400 if invalid status.
    """
    if not session:
        raise HTTPException(status_code=500, detail="Database session not available")

    if request.status not in ("draft", "verified", "stale"):
        raise HTTPException(status_code=400, detail="Invalid status") from None

    store = SpecStore(session)
    spec = store.update_status("default", repo, component_ref, version, request.status)

    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found") from None

    return SpecDetailResponse.model_validate(spec)


class GenerateSpecRequest(BaseModel):
    """Request to generate a spec for a component."""

    repo: str = Query(...)


class GenerateSpecResponse(BaseModel):
    """Response after generating a spec."""

    component_ref: str
    version: int
    status: str
    content: dict
    provenance: list
    created_at: str

    model_config = ConfigDict(from_attributes=True)


@router.post("/generate/{component_ref}", response_model=GenerateSpecResponse)
def generate_spec(
    component_ref: str = Path(...),
    repo: str = Query(...),
    spec_session: Session = Depends(get_spec_session),  # noqa: B008
    analysis_session: Session = Depends(get_analysis_session),  # noqa: B008
    llm_provider=Depends(get_llm_provider),  # noqa: B008
) -> GenerateSpecResponse:
    """Generate or retrieve a spec for a component (generate-on-demand).

    If spec exists: return cached (no LLM call).
    If not: generate via LLM, persist as v1, return.

    Args:
        component_ref: Component reference (qualified name).
        repo: Repository name.
        spec_session: Spec DB session.
        analysis_session: Analysis DB session.
        llm_provider: LLM provider for generation.

    Returns:
        The spec (generated or cached).

    Raises:
        HTTPException: 404 if component not found, 500 on generation error.
    """
    if not spec_session or not analysis_session:
        raise HTTPException(status_code=503, detail="Database session not available")

    store = SpecStore(spec_session)

    # Check if spec already exists (cache hit)
    existing = store.get_current("default", repo, component_ref)
    if existing:
        logger.info(f"Spec cache hit: {component_ref} v{existing.version}")
        return GenerateSpecResponse.model_validate(existing)

    # Spec doesn't exist — generate via LLM
    logger.info(f"Generating spec for {component_ref}")

    try:
        # Fetch focal node from analysis DB
        focal_node = (
            analysis_session.query(Node).filter(Node.qualified_name == component_ref).first()
        )

        if not focal_node:
            raise HTTPException(
                status_code=404, detail=f"Component not found: {component_ref}"
            ) from None

        # Fetch neighbors (related nodes) and edges
        neighbors = (
            analysis_session.query(Node)
            .join(
                Edge,
                (Edge.src_node_id == Node.id) | (Edge.dst_node_id == Node.id),
            )
            .filter((Edge.src_node_id == focal_node.id) | (Edge.dst_node_id == focal_node.id))
            .limit(20)
            .all()
        )

        edges = (
            analysis_session.query(Edge)
            .filter((Edge.src_node_id == focal_node.id) | (Edge.dst_node_id == focal_node.id))
            .limit(10)
            .all()
        )

        # Generate spec via LLM
        spec_content, provenance = SpecifyEngine.generate(
            focal_node=focal_node,
            neighbors=neighbors,
            edges=edges,
            llm_provider=llm_provider,
        )

        # Persist the spec (version=1, status=draft)
        spec = store.create(
            user_id="default",
            repo=repo,
            component_ref=component_ref,
            spec_content=spec_content,
            provenance=provenance,
            status="draft",
        )

        logger.info(f"Spec generated and persisted: {component_ref} v{spec.version}")
        return GenerateSpecResponse.model_validate(spec)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate spec for {component_ref}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate spec: {str(e)}") from e


class SpecGraphResponse(BaseModel):
    """Spec with its dependencies and dependents in the spec graph."""

    spec: SpecDetailResponse
    dependencies: list[SpecSummaryResponse] = []
    dependents: list[SpecSummaryResponse] = []

    model_config = ConfigDict(from_attributes=True)


@router.get("/graph/{component_ref}", response_model=SpecGraphResponse)
def get_spec_graph(
    component_ref: str,
    repo: str = Query(...),
    session: Session = Depends(get_spec_session),  # noqa: B008
) -> SpecGraphResponse:
    """Get a spec and its graph relationships (dependencies/dependents).

    Args:
        component_ref: Component reference.
        repo: Repository name.
        session: Spec DB session.

    Returns:
        The spec with its dependencies and dependents.

    Raises:
        HTTPException: 404 if spec not found.
    """
    if not session:
        raise HTTPException(status_code=500, detail="Database session not available")

    from spec_atlas.db.spec import SpecEdge

    store = SpecStore(session)
    spec = store.get_current("default", repo, component_ref)

    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found") from None

    # Find dependencies (outgoing edges)
    dependencies = (
        session.query(SpecEdge)
        .filter(
            SpecEdge.user_id == "default",
            SpecEdge.repo == repo,
            SpecEdge.src_component_ref == component_ref,
        )
        .all()
    )

    # Find dependents (incoming edges)
    dependents = (
        session.query(SpecEdge)
        .filter(
            SpecEdge.user_id == "default",
            SpecEdge.repo == repo,
            SpecEdge.dst_component_ref == component_ref,
        )
        .all()
    )

    # Get specs for dependencies
    dep_specs = []
    for edge in dependencies:
        dep_spec = store.get_current("default", repo, edge.dst_component_ref)
        if dep_spec:
            dep_specs.append(SpecSummaryResponse.model_validate(dep_spec))

    # Get specs for dependents
    dependent_specs = []
    for edge in dependents:
        dependent_spec = store.get_current("default", repo, edge.src_component_ref)
        if dependent_spec:
            dependent_specs.append(SpecSummaryResponse.model_validate(dependent_spec))

    return SpecGraphResponse(
        spec=SpecDetailResponse.model_validate(spec),
        dependencies=dep_specs,
        dependents=dependent_specs,
    )


class VerifySpecRequest(BaseModel):
    """Request to verify a spec."""

    repo: str = Query(...)


class VerificationIssue(BaseModel):
    """A single verification issue."""

    claim: str
    reason: str
    severity: str


class VerifySpecResponse(BaseModel):
    """Response from verification."""

    component_ref: str
    version: int
    status: str
    confidence: float
    is_grounded: bool
    issues: list[VerificationIssue]

    model_config = ConfigDict(from_attributes=True)


@router.post("/{component_ref}/verify", response_model=VerifySpecResponse)
def verify_spec(
    component_ref: str = Path(...),
    repo: str = Query(...),
    version: int = Query(...),
    spec_session: Session = Depends(get_spec_session),  # noqa: B008
    analysis_session: Session = Depends(get_analysis_session),  # noqa: B008
) -> VerifySpecResponse:
    """Verify that a spec's claims are grounded in source code (idempotent).

    Uses SpecStore to run rule-based checks and update status.
    Safe to call multiple times (returns cached result if already verified).

    Args:
        component_ref: Component reference (qualified name).
        repo: Repository name.
        version: Spec version to verify.
        spec_session: Spec DB session.
        analysis_session: Analysis DB session.

    Returns:
        VerifySpecResponse with confidence score, pass/fail, and issues.

    Raises:
        HTTPException: 404 if spec not found, 503 if databases unavailable.
    """
    if not spec_session:
        raise HTTPException(status_code=503, detail="Spec database not available")

    if not analysis_session:
        raise HTTPException(status_code=503, detail="Analysis database not available")

    # Use SpecStore for verification (idempotent)
    store = SpecStore(spec_session)
    try:
        result = store.verify_spec(
            user_id="default",
            repo=repo,
            component_ref=component_ref,
            version=version,
            analysis_session=analysis_session,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None

    # Get updated spec to return current status
    spec = store.get_version("default", repo, component_ref, version)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found") from None

    return VerifySpecResponse(
        component_ref=component_ref,
        version=version,
        status=spec.status,
        confidence=result.confidence,
        is_grounded=result.is_grounded,
        issues=[
            VerificationIssue(
                claim=issue.claim,
                reason=issue.reason,
                severity=issue.severity,
            )
            for issue in result.issues
        ],
    )


@router.get("/project-specs")
async def get_project_specs(
    project_id: str = Query(...),
    db: Session = Depends(get_spec_session),
) -> dict:
    """Get all specs for a project."""
    from spec_atlas.db.spec import Spec

    specs = db.query(Spec).filter(Spec.repo == project_id).all()

    return {
        "specs": [
            {
                "component_ref": s.component_ref,
                "status": s.status,
                "version": s.version,
                "confidence": s.content.get("confidence", 0),
                "interconnections": s.content.get("interconnections", []),
                "markdown": s.content.get("markdown", ""),
            }
            for s in specs
            if s.valid_to is None  # Current version only
        ],
        "total": len(specs),
        "verified_count": sum(
            1 for s in specs if s.status == "verified" and s.valid_to is None
        ),
    }


@router.post("/project-notes")
async def save_project_notes(
    project_id: str = Query(...),
    notes: str = Query(...),
    db: Session = Depends(get_spec_session),
) -> dict:
    """Save research notes for project."""
    from spec_atlas.db.spec import Spec

    # Store notes as a special spec document
    from datetime import datetime
    from spec_atlas.db.spec import Spec as SpecModel
    import uuid

    notes_spec = SpecModel(
        id=uuid.uuid4(),
        user_id="system",
        repo=project_id,
        component_ref="__notes__",
        version=1,
        status="draft",
        content={"notes": notes, "type": "research_notes"},
        provenance=[],
    )

    # Invalidate old notes
    db.query(SpecModel).filter(
        SpecModel.repo == project_id, SpecModel.component_ref == "__notes__"
    ).update({"valid_to": datetime.now()})

    db.add(notes_spec)
    db.commit()

    return {"success": True}


@router.get("/project-notes")
async def get_project_notes(
    project_id: str = Query(...),
    db: Session = Depends(get_spec_session),
) -> dict:
    """Get research notes for project."""
    from spec_atlas.db.spec import Spec

    notes_spec = (
        db.query(Spec)
        .filter(
            Spec.repo == project_id,
            Spec.component_ref == "__notes__",
            Spec.valid_to.is_(None),
        )
        .first()
    )

    return {
        "notes": notes_spec.content.get("notes", "") if notes_spec else "",
        "project_id": project_id,
    }
