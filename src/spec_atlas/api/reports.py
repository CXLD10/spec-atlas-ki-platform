"""Verification analytics and reporting endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from spec_atlas.spec.store import SpecStore

router = APIRouter(prefix="/api/reports", tags=["reports"])


def get_spec_session(request: Request) -> Session:
    """Get Spec DB session from app state."""
    from fastapi import HTTPException

    factory = request.app.state.spec_session_factory
    if not factory:
        raise HTTPException(status_code=503, detail="Spec database not configured")
    session = factory()
    try:
        yield session
    finally:
        session.close()


class VerificationReport(BaseModel):
    """Overall verification statistics."""

    total_specs: int
    verified_count: int
    review_count: int
    draft_count: int
    avg_confidence: float
    verification_rate: float
    specs_needing_review: int

    model_config = ConfigDict(from_attributes=True)


class VerificationIssue(BaseModel):
    """A single verification issue with frequency."""

    reason: str
    count: int


class VerificationIssuesReport(BaseModel):
    """Report of verification issues."""

    issues: list[VerificationIssue]
    count: int


class ConfidenceDistribution(BaseModel):
    """Histogram of confidence scores."""

    bins: list[str]
    counts: list[int]


@router.get("/verification", response_model=VerificationReport)
def get_verification_report(
    repo: str = Query(...),
    session: Session = Depends(get_spec_session),  # noqa: B008
) -> VerificationReport:
    """Get overall verification statistics for a repository.

    Args:
        repo: Repository name.
        session: Spec DB session.

    Returns:
        VerificationReport with overall statistics.
    """
    if not session:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="Spec database not available")

    store = SpecStore(session)
    report = store.get_verification_report(user_id="default", repo=repo)

    return VerificationReport(**report)


@router.get("/verification/issues", response_model=VerificationIssuesReport)
def get_verification_issues(
    repo: str = Query(...),
    limit: int = Query(10, ge=1, le=100),
    session: Session = Depends(get_spec_session),  # noqa: B008
) -> VerificationIssuesReport:
    """Get most common verification issues in a repository.

    Args:
        repo: Repository name.
        limit: Maximum number of issues to return (default 10, max 100).
        session: Spec DB session.

    Returns:
        VerificationIssuesReport with top issues.
    """
    if not session:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="Spec database not available")

    store = SpecStore(session)
    issues = store.get_verification_issues(user_id="default", repo=repo, limit=limit)

    return VerificationIssuesReport(
        issues=[VerificationIssue(**i) for i in issues], count=len(issues)
    )


@router.get("/verification/confidence", response_model=ConfidenceDistribution)
def get_confidence_distribution(
    repo: str = Query(...),
    bins: int = Query(5, ge=2, le=20),
    session: Session = Depends(get_spec_session),  # noqa: B008
) -> ConfidenceDistribution:
    """Get confidence score distribution for a repository.

    Args:
        repo: Repository name.
        bins: Number of histogram bins (default 5, between 2-20).
        session: Spec DB session.

    Returns:
        ConfidenceDistribution with histogram data.
    """
    if not session:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="Spec database not available")

    store = SpecStore(session)
    distribution = store.get_confidence_distribution(user_id="default", repo=repo, bins=bins)

    return ConfidenceDistribution(**distribution)
