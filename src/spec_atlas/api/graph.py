"""Graph API endpoints (L1 code knowledge graph queries)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from spec_atlas.db.analysis import Edge, File, Group, Node, Repo
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


def get_spec_session(request: Request) -> Session:
    """Get spec DB session from app state."""
    factory = request.app.state.spec_session_factory
    if not factory:
        raise HTTPException(status_code=503, detail="Spec database not configured")
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


# ── Layered graph (L1 code + L3 specs + L4 groups), for the /graph explorer ──
# Distinct from /subgraph (requires a node_id, returns only L1 NodeDetail) and
# /nodes+/edges (L1-only, no layer tagging — see api/useGraph.ts's GraphNode,
# which expects a `layer` field these never sent).


class LayeredNode(BaseModel):
    """A node in the layered (L1/L3/L4) graph."""

    id: str
    label: str
    kind: str
    layer: str  # "L1" | "L3" | "L4"
    file_path: str = ""
    qualified_name: str = ""


class LayeredEdge(BaseModel):
    """An edge in the layered (L1/L3/L4) graph. May cross layers (inter=True)."""

    id: str
    source: str
    target: str
    kind: str
    confidence: float = 1.0
    inter: bool = False


class LayeredGraphResponse(BaseModel):
    """Response for the layered graph endpoint."""

    nodes: list[LayeredNode]
    edges: list[LayeredEdge]


def _resolve_repo_id_by_name(repo: str, session: Session) -> uuid.UUID:
    row = session.query(Repo).filter(Repo.name == repo).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Repo not found: {repo!r}")
    return row.id


@router.get("/layered", response_model=LayeredGraphResponse)
def get_layered_graph(
    repo: str = Query(...),
    session: Session = Depends(get_analysis_session),  # noqa: B008
    spec_session: Session = Depends(get_spec_session),  # noqa: B008
    max_nodes: int = Query(1000, ge=1, le=5000),
) -> LayeredGraphResponse:
    """Get the full layered graph for a repo: L1 code, L3 specs, L4 groups.

    L3 spec nodes are synthetic (specs have no row in the Analysis DB) with
    id ``spec:{component_ref}``, joined to their L1 node by qualified_name.
    Inter-layer edges (kind="documents"/"contains"/"member-of") connect
    L3 specs to the L1 node they describe, and L4 groups to their L1 member
    nodes and L4 parent group.
    """
    from spec_atlas.db.spec import Spec, SpecEdge

    repo_id = _resolve_repo_id_by_name(repo, session)

    nodes_q = session.query(Node).filter(Node.repo_id == repo_id).limit(max_nodes).all()
    file_map = {f.id: f.path for f in session.query(File).filter(File.repo_id == repo_id).all()}
    qname_to_node_id = {n.qualified_name: str(n.id) for n in nodes_q}

    nodes: list[LayeredNode] = [
        LayeredNode(
            id=str(n.id),
            label=n.name,
            kind=n.kind,
            layer="L1",
            file_path=file_map.get(n.file_id, ""),
            qualified_name=n.qualified_name,
        )
        for n in nodes_q
    ]

    edges: list[LayeredEdge] = [
        LayeredEdge(
            id=str(e.id),
            source=str(e.src_node_id),
            target=str(e.dst_node_id),
            kind=e.kind,
            confidence=e.confidence or 0.5,
            inter=False,
        )
        for e in session.query(Edge).filter(Edge.repo_id == repo_id).all()
    ]

    # L4: groups
    groups = session.query(Group).filter(Group.repo_id == repo_id).all()
    for g in groups:
        nodes.append(
            LayeredNode(id=str(g.id), label=g.title or g.path or "root", kind="group", layer="L4")
        )
        if g.parent_id:
            edges.append(
                LayeredEdge(
                    id=f"group-parent:{g.id}",
                    source=str(g.id),
                    target=str(g.parent_id),
                    kind="part-of",
                    inter=False,
                )
            )
        for member_id in g.member_node_ids or []:
            edges.append(
                LayeredEdge(
                    id=f"group-member:{g.id}:{member_id}",
                    source=str(g.id),
                    target=str(member_id),
                    kind="contains",
                    inter=True,
                )
            )

    # L3: specs (current versions only) + spec graph edges
    specs = (
        spec_session.query(Spec)
        .filter(Spec.repo == repo, Spec.valid_to.is_(None))
        .all()
    )
    spec_node_id = {s.component_ref: f"spec:{s.component_ref}" for s in specs}
    for s in specs:
        nodes.append(
            LayeredNode(
                id=spec_node_id[s.component_ref],
                label=s.component_ref,
                kind="spec",
                layer="L3",
                qualified_name=s.component_ref,
            )
        )
        l1_target = qname_to_node_id.get(s.component_ref)
        if l1_target:
            edges.append(
                LayeredEdge(
                    id=f"spec-documents:{s.id}",
                    source=spec_node_id[s.component_ref],
                    target=l1_target,
                    kind="documents",
                    inter=True,
                )
            )

    spec_edges = spec_session.query(SpecEdge).filter(SpecEdge.repo == repo).all()
    for se in spec_edges:
        src = spec_node_id.get(se.src_component_ref)
        dst = spec_node_id.get(se.dst_component_ref)
        if src and dst:
            edges.append(
                LayeredEdge(
                    id=str(se.id),
                    source=src,
                    target=dst,
                    kind=se.kind,
                    inter=False,
                )
            )

    return LayeredGraphResponse(nodes=nodes, edges=edges)
