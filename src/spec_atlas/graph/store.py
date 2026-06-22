"""Graph persistence and query layer for the L1 code knowledge graph."""

from __future__ import annotations

import uuid
from collections import deque

from sqlalchemy import or_
from sqlalchemy.orm import Session

from spec_atlas.db.analysis import Edge, Node


class GraphStore:
    """Query interface for the L1 code knowledge graph."""

    def __init__(self, session: Session, repo_id: uuid.UUID) -> None:
        """Initialize the graph store.

        Args:
            session: SQLAlchemy session.
            repo_id: Repository ID.
        """
        self.session = session
        self.repo_id = repo_id

    def neighbors(
        self,
        node_id: uuid.UUID,
        direction: str = "both",
        edge_kinds: list[str] | None = None,
        min_confidence: float | None = None,
    ) -> dict:
        """Get neighbors of a node.

        Args:
            node_id: The node ID.
            direction: "in", "out", or "both" (default "both").
            edge_kinds: Filter by edge kind (e.g., ["calls", "imports"]).
            min_confidence: Minimum confidence threshold (0-1).

        Returns:
            Dict with "edges" (list of Edge) and "target_nodes" (list of Node).
        """
        query = self.session.query(Edge).filter(Edge.repo_id == self.repo_id)

        if direction in ("out", "both"):
            outgoing = query.filter(Edge.src_node_id == node_id)
        else:
            outgoing = query.filter(False)

        if direction in ("in", "both"):
            incoming = query.filter(Edge.dst_node_id == node_id)
        else:
            incoming = query.filter(False)

        if direction == "both":
            edges = list(outgoing) + list(incoming)
        elif direction == "out":
            edges = list(outgoing)
        else:
            edges = list(incoming)

        if edge_kinds:
            edges = [e for e in edges if e.kind in edge_kinds]

        if min_confidence is not None:
            edges = [e for e in edges if e.confidence >= min_confidence]

        # Get target nodes
        target_node_ids = set()
        for edge in edges:
            if edge.src_node_id == node_id:
                target_node_ids.add(edge.dst_node_id)
            else:
                target_node_ids.add(edge.src_node_id)

        target_nodes = []
        if target_node_ids:
            target_nodes = self.session.query(Node).filter(Node.id.in_(target_node_ids)).all()

        return {"edges": edges, "target_nodes": target_nodes}

    def subgraph(
        self,
        node_id: uuid.UUID,
        max_depth: int = 2,
        edge_kinds: list[str] | None = None,
        min_confidence: float | None = None,
        max_nodes: int = 500,
    ) -> dict:
        """Get a subgraph neighborhood around a node.

        Args:
            node_id: The root node ID.
            max_depth: Maximum traversal depth.
            edge_kinds: Filter by edge kind.
            min_confidence: Minimum confidence threshold.
            max_nodes: Maximum nodes to return.

        Returns:
            Dict with "nodes" and "edges".
        """
        # BFS traversal
        visited_nodes = set()
        visited_edges = set()
        queue = deque([(node_id, 0)])

        while queue and len(visited_nodes) < max_nodes:
            current_id, depth = queue.popleft()

            if current_id in visited_nodes:
                continue

            visited_nodes.add(current_id)

            if depth >= max_depth:
                continue

            # Find neighbors
            neighbors_result = self.neighbors(
                current_id,
                direction="both",
                edge_kinds=edge_kinds,
                min_confidence=min_confidence,
            )

            for edge in neighbors_result["edges"]:
                edge_id = (edge.src_node_id, edge.dst_node_id, edge.kind)
                if edge_id not in visited_edges:
                    visited_edges.add(edge_id)

                # Add neighbor to queue if not visited
                other_id = edge.dst_node_id if edge.src_node_id == current_id else edge.src_node_id
                if other_id not in visited_nodes and len(visited_nodes) < max_nodes:
                    queue.append((other_id, depth + 1))

        # Fetch all visited nodes
        nodes = self.session.query(Node).filter(Node.id.in_(visited_nodes)).all()

        # Fetch edges between visited nodes
        edges = (
            self.session.query(Edge)
            .filter(
                Edge.repo_id == self.repo_id,
                or_(
                    Edge.src_node_id.in_(visited_nodes),
                    Edge.dst_node_id.in_(visited_nodes),
                ),
            )
            .all()
        )

        # Filter edges to only those in the subgraph
        subgraph_edges = [
            e for e in edges if e.src_node_id in visited_nodes and e.dst_node_id in visited_nodes
        ]

        return {"nodes": nodes, "edges": subgraph_edges}

    def reachability(self, src_node_id: uuid.UUID, dst_node_id: uuid.UUID) -> bool:
        """Check if there is a path from src to dst.

        Args:
            src_node_id: Source node ID.
            dst_node_id: Destination node ID.

        Returns:
            True if reachable, False otherwise.
        """
        if src_node_id == dst_node_id:
            return True

        # BFS with depth limit
        visited = set()
        queue = deque([(src_node_id, 0)])
        max_depth = 10

        while queue:
            current_id, depth = queue.popleft()

            if current_id in visited or depth > max_depth:
                continue

            visited.add(current_id)

            # Find outgoing neighbors
            edges = (
                self.session.query(Edge)
                .filter(
                    Edge.repo_id == self.repo_id,
                    Edge.src_node_id == current_id,
                )
                .all()
            )

            for edge in edges:
                if edge.dst_node_id == dst_node_id:
                    return True

                if edge.dst_node_id not in visited:
                    queue.append((edge.dst_node_id, depth + 1))

        return False

    def search_nodes(
        self,
        pattern: str,
        language: str | None = None,
        kind: str | None = None,
    ) -> list[Node]:
        """Search for nodes by qualified_name pattern.

        Args:
            pattern: Substring pattern to match against qualified_name.
            language: Filter by language (e.g., "python", "typescript").
            kind: Filter by kind (e.g., "function", "class").

        Returns:
            List of matching Node objects.
        """
        query = self.session.query(Node).filter(Node.repo_id == self.repo_id)

        # Pattern matching: case-insensitive substring
        query = query.filter(Node.qualified_name.ilike(f"%{pattern}%"))

        if language:
            query = query.filter(Node.language == language)

        if kind:
            query = query.filter(Node.kind == kind)

        return query.all()
