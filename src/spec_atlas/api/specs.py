"""Spec store API endpoints (L2/L3 specs and spec graph)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from spec_atlas.spec.store import SpecStore

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
