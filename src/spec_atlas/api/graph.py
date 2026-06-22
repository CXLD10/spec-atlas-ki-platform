"""Graph API endpoints (L1 code knowledge graph queries)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from spec_atlas.db.analysis import Edge, File, Node
from spec_atlas.graph.store import GraphStore

router = APIRouter(prefix="/api/graph", tags=["graph"])


def get_analysis_session(request: Request) -> Session:
    """Get analysis DB session from app state."""
    factory = request.app.state.analysis_session_factory
    if not factory:
        raise HTTPException(status_code=503, detail="Analysis database not configured")
    session = factory()
    try:
        yield session
    finally:
        session.close()


class NodeDetail(BaseModel):
    """Detailed node information."""

    id: str
    qualified_name: str
    kind: str
    name: str
    language: str
    signature: str | None
    docstring: str | None
    start_line: int
    end_line: int
    file_path: str
    repo_id: str

    model_config = ConfigDict(from_attributes=True)


class EdgeDetail(BaseModel):
    """Edge information."""

    id: str
    src_node_id: str
    dst_node_id: str
    kind: str
    confidence: float

    model_config = ConfigDict(from_attributes=True)


class NeighborsResponse(BaseModel):
    """Response for neighbors endpoint."""

    edges: list[EdgeDetail]
    target_nodes: list[NodeDetail]


class SubgraphResponse(BaseModel):
    """Response for subgraph endpoint."""

    nodes: list[NodeDetail]
    edges: list[EdgeDetail]


class SearchResponse(BaseModel):
    """Response for search endpoint."""

    results: list[NodeDetail]


class ReachabilityRequest(BaseModel):
    """Request body for reachability endpoint."""

    src_id: str
    dst_id: str


class ReachabilityResponse(BaseModel):
    """Response for reachability endpoint."""

    reachable: bool
    path: list[str] | None = None


def _node_to_detail(node: Node, file_path: str = "") -> NodeDetail:
    """Convert a Node ORM object to NodeDetail."""
    return NodeDetail(
        id=str(node.id),
        qualified_name=node.qualified_name,
        kind=node.kind,
        name=node.name,
        language=node.language,
        signature=node.signature,
        docstring=node.docstring,
        start_line=node.start_line,
        end_line=node.end_line,
        file_path=file_path,
        repo_id=str(node.repo_id),
    )


def _edge_to_detail(edge) -> EdgeDetail:
    """Convert an Edge ORM object to EdgeDetail."""
    return EdgeDetail(
        id=str(edge.id),
        src_node_id=str(edge.src_node_id),
        dst_node_id=str(edge.dst_node_id),
        kind=edge.kind,
        confidence=edge.confidence,
    )


@router.get("/nodes/{node_id}", response_model=NodeDetail)
def get_node(
    node_id: str,
    session: Session = Depends(get_analysis_session),  # noqa: B008
) -> NodeDetail:
    """Get full details of a node."""
    try:
        parsed_id = uuid.UUID(node_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid node ID format") from e

    node = session.query(Node).filter(Node.id == parsed_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found") from None

    # Get file path
    file_path = ""
    if node.file_id:
        file = session.query(File).filter(File.id == node.file_id).first()
        if file:
            file_path = file.path

    return _node_to_detail(node, file_path)


@router.get("/nodes/{node_id}/neighbors", response_model=NeighborsResponse)
def get_neighbors(
    node_id: str,
    session: Session = Depends(get_analysis_session),  # noqa: B008
    direction: str = Query("both", pattern="^(in|out|both)$"),
    edge_kinds: str | None = Query(None),
    min_confidence: float | None = Query(None, ge=0.0, le=1.0),
) -> NeighborsResponse:
    """Get neighbors of a node."""
    try:
        parsed_id = uuid.UUID(node_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid node ID format") from e

    node = session.query(Node).filter(Node.id == parsed_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found") from None

    repo_id = node.repo_id
    store = GraphStore(session, repo_id)

    edge_kinds_list = None
    if edge_kinds:
        edge_kinds_list = [k.strip() for k in edge_kinds.split(",")]

    result = store.neighbors(
        parsed_id,
        direction=direction,
        edge_kinds=edge_kinds_list,
        min_confidence=min_confidence,
    )

    # Fetch file paths for nodes
    file_map = {}
    for target_node in result["target_nodes"]:
        if target_node.file_id:
            file = session.query(File).filter(File.id == target_node.file_id).first()
            if file:
                file_map[target_node.id] = file.path

    node_details = [_node_to_detail(n, file_map.get(n.id, "")) for n in result["target_nodes"]]
    edge_details = [_edge_to_detail(e) for e in result["edges"]]

    return NeighborsResponse(edges=edge_details, target_nodes=node_details)


@router.get("/subgraph", response_model=SubgraphResponse)
def get_subgraph(
    node_id: str = Query(...),
    session: Session = Depends(get_analysis_session),  # noqa: B008
    max_depth: int = Query(2, ge=0, le=10),
    edge_kinds: str | None = Query(None),
    min_confidence: float | None = Query(None, ge=0.0, le=1.0),
    max_nodes: int = Query(500, ge=1, le=5000),
) -> SubgraphResponse:
    """Get a subgraph neighborhood around a node."""
    try:
        parsed_id = uuid.UUID(node_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid node ID format") from e

    node = session.query(Node).filter(Node.id == parsed_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found") from None

    repo_id = node.repo_id
    store = GraphStore(session, repo_id)

    edge_kinds_list = None
    if edge_kinds:
        edge_kinds_list = [k.strip() for k in edge_kinds.split(",")]

    result = store.subgraph(
        parsed_id,
        max_depth=max_depth,
        edge_kinds=edge_kinds_list,
        min_confidence=min_confidence,
        max_nodes=max_nodes,
    )

    # Fetch file paths
    file_map = {}
    for sg_node in result["nodes"]:
        if sg_node.file_id:
            file = session.query(File).filter(File.id == sg_node.file_id).first()
            if file:
                file_map[sg_node.id] = file.path

    node_details = [_node_to_detail(n, file_map.get(n.id, "")) for n in result["nodes"]]
    edge_details = [_edge_to_detail(e) for e in result["edges"]]

    return SubgraphResponse(nodes=node_details, edges=edge_details)


# Graph visualization endpoints (for frontend visualization)
class GraphNodeViz(BaseModel):
    """Node data for visualization."""

    id: str
    label: str
    kind: str
    file_path: str


class GraphEdgeViz(BaseModel):
    """Edge data for visualization."""

    id: str
    source: str
    target: str
    kind: str
    confidence: float


@router.get("/nodes", response_model=list[GraphNodeViz])
def get_all_nodes(
    session: Session = Depends(get_analysis_session),  # noqa: B008
    limit: int = Query(1000, ge=1, le=10000),
) -> list[GraphNodeViz]:
    """Get all nodes for visualization (with limit for performance)."""
    nodes = session.query(Node).limit(limit).all()

    # Fetch file paths
    file_map = {}
    for node in nodes:
        if node.file_id:
            file = session.query(File).filter(File.id == node.file_id).first()
            if file:
                file_map[node.id] = file.path

    return [
        GraphNodeViz(
            id=str(node.id),
            label=node.name,
            kind=node.kind or "unknown",
            file_path=file_map.get(node.id, ""),
        )
        for node in nodes
    ]


@router.get("/edges", response_model=list[GraphEdgeViz])
def get_all_edges(
    session: Session = Depends(get_analysis_session),  # noqa: B008
    limit: int = Query(2000, ge=1, le=50000),
) -> list[GraphEdgeViz]:
    """Get all edges for visualization (with limit for performance)."""
    edges = session.query(Edge).limit(limit).all()

    return [
        GraphEdgeViz(
            id=str(edge.id),
            source=str(edge.src_node_id),
            target=str(edge.dst_node_id),
            kind=edge.kind or "unknown",
            confidence=edge.confidence or 0.5,
        )
        for edge in edges
    ]


@router.get("/search", response_model=SearchResponse)
def search_nodes(
    q: str = Query(..., min_length=1),
    session: Session = Depends(get_analysis_session),  # noqa: B008
    language: str | None = Query(None),
    kind: str | None = Query(None),
) -> SearchResponse:
    """Search for nodes by qualified_name pattern."""
    # Get first repo for context (v1 limitation: per-repo search)
    first_repo = session.query(Node.repo_id).first()
    if not first_repo:
        return SearchResponse(results=[])

    repo_id = first_repo[0]
    store = GraphStore(session, repo_id)

    nodes = store.search_nodes(q, language=language, kind=kind)

    # Limit to 100 results
    nodes = nodes[:100]

    # Fetch file paths
    file_map = {}
    for node in nodes:
        if node.file_id:
            file = session.query(File).filter(File.id == node.file_id).first()
            if file:
                file_map[node.id] = file.path

    node_details = [_node_to_detail(n, file_map.get(n.id, "")) for n in nodes]

    return SearchResponse(results=node_details)


@router.post("/reachable", response_model=ReachabilityResponse)
def check_reachability(
    request: ReachabilityRequest,
    session: Session = Depends(get_analysis_session),  # noqa: B008
) -> ReachabilityResponse:
    """Check if there is a path between two nodes."""
    try:
        src_id = uuid.UUID(request.src_id)
        dst_id = uuid.UUID(request.dst_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid node ID format") from e

    src_node = session.query(Node).filter(Node.id == src_id).first()
    if not src_node:
        raise HTTPException(status_code=404, detail="Source node not found")

    dst_node = session.query(Node).filter(Node.id == dst_id).first()
    if not dst_node:
        raise HTTPException(status_code=404, detail="Destination node not found")

    # Both nodes must be in same repo
    if src_node.repo_id != dst_node.repo_id:
        raise HTTPException(
            status_code=400,
            detail="Nodes must be in the same repository",
        )

    store = GraphStore(session, src_node.repo_id)
    reachable = store.reachability(src_id, dst_id)

    return ReachabilityResponse(reachable=reachable, path=None)
