"""Knowledge Base API: specs rendered as Knowledge Cards.

GET /api/kb and /api/kb/{ref} are pure views over the Spec DB — every card
is a real spec (purpose/inputs/outputs/... + provenance), rendered to
markdown and to the frontend's KnowledgeCard shape. No new data; this is
purely an aggregation/projection layer the UI was missing.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from spec_atlas.db.spec import Spec, SpecEdge
from spec_atlas.specify.batch_generator import _spec_to_markdown

router = APIRouter(prefix="/api/kb", tags=["kb"])


def get_spec_session(request: Request) -> Session:
    factory = request.app.state.spec_session_factory
    if not factory:
        raise HTTPException(status_code=503, detail="Spec database not configured")
    session = factory()
    try:
        yield session
    finally:
        session.close()


class ProvenanceItem(BaseModel):
    ref: str
    kind: str
    loc: str


class RelationItem(BaseModel):
    kind: str
    ref: str


class KnowledgeCardResponse(BaseModel):
    ref: str
    title: str
    status: str
    markdown: str
    provenance: list[ProvenanceItem]
    relations: list[RelationItem]


_PROVENANCE_KIND_BY_SUFFIX = {".pdf": "pdf", ".xlsx": "xlsx", ".md": "md", ".markdown": "md"}


def _provenance_kind(file_path: str) -> str:
    for suffix, kind in _PROVENANCE_KIND_BY_SUFFIX.items():
        if file_path.endswith(suffix):
            return kind
    return "code"


def _spec_to_card(spec: Spec, session: Session) -> KnowledgeCardResponse:
    markdown = _spec_to_markdown(spec.content, spec.component_ref, spec.provenance)

    provenance = [
        ProvenanceItem(
            ref=span.get("file", ""),
            kind=_provenance_kind(span.get("file", "")),
            loc=f"{span.get('start_line', '?')}-{span.get('end_line', '?')}",
        )
        for span in (spec.provenance or [])
        if isinstance(span, dict)
    ]

    relations = [
        RelationItem(kind=edge.kind, ref=edge.dst_component_ref)
        for edge in (
            session.query(SpecEdge)
            .filter(
                SpecEdge.session_id == spec.session_id,
                SpecEdge.repo == spec.repo,
                SpecEdge.src_component_ref == spec.component_ref,
            )
            .all()
        )
    ]

    return KnowledgeCardResponse(
        ref=spec.component_ref,
        title=spec.component_ref,
        status=spec.status,
        markdown=markdown,
        provenance=provenance,
        relations=relations,
    )


@router.get("", response_model=list[KnowledgeCardResponse])
def list_cards(
    repo: str | None = Query(None),
    session: Session = Depends(get_spec_session),  # noqa: B008
) -> list[KnowledgeCardResponse]:
    """List all knowledge cards (current spec versions), optionally scoped to a repo."""
    q = session.query(Spec).filter(Spec.valid_to.is_(None))
    if repo:
        q = q.filter(Spec.repo == repo)
    return [_spec_to_card(s, session) for s in q.order_by(Spec.component_ref).all()]


@router.get("/{ref}", response_model=KnowledgeCardResponse)
def get_card(
    ref: str,
    repo: str | None = Query(None),
    session: Session = Depends(get_spec_session),  # noqa: B008
) -> KnowledgeCardResponse:
    """Get a single knowledge card by component_ref."""
    q = session.query(Spec).filter(Spec.component_ref == ref, Spec.valid_to.is_(None))
    if repo:
        q = q.filter(Spec.repo == repo)
    spec = q.first()
    if not spec:
        raise HTTPException(status_code=404, detail=f"Card not found: {ref!r}")
    return _spec_to_card(spec, session)
