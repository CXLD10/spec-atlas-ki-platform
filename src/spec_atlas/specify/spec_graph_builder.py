"""Build spec graph (L3) from L1 code edges."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from spec_atlas.db.analysis import Edge, Node
from spec_atlas.db.analysis import Repo as RepoModel
from spec_atlas.db.spec import Spec, SpecEdge

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# L1 Edge.kind ('imports','calls','inherits','defines') -> L3 SpecEdge.kind
# ('depends-on','part-of','uses' — see ck_spec_edges_kind in db/spec.py).
# Without this mapping every insert violates the CHECK constraint, since the
# two tables use disjoint vocabularies.
_L1_TO_L3_KIND = {
    "calls": "uses",
    "imports": "uses",
    "inherits": "depends-on",
    "defines": "part-of",
}


def _map_edge_kind(l1_kind: str) -> str:
    return _L1_TO_L3_KIND.get(l1_kind, "uses")


class SpecGraphBuilder:
    """Build spec graph edges from code graph edges."""

    @staticmethod
    def build_spec_graph(
        repo_id: str,
        user_id: str = "default",
        analysis_session: Session | None = None,
        spec_session: Session | None = None,
    ) -> dict:
        """Build spec graph edges from L1 code edges.

        Args:
            repo_id: Repository ID.
            user_id: User ID for spec ownership.
            analysis_session: Analysis DB session.
            spec_session: Spec DB session.

        Returns:
            Report: {
                "total_edges": int,
                "created_edges": int,
                "errors": []
            }
        """
        report = {
            "total_edges": 0,
            "created_edges": 0,
            "errors": [],
        }

        if not analysis_session or not spec_session:
            logger.warning("Spec graph builder: missing session")
            return report

        try:
            # Spec.repo / SpecEdge.repo store the repo *name* (loose ref), not
            # the analysis-DB repo_id UUID — resolve it once so the queries
            # below compare like with like (varchar = uuid has no implicit
            # cast in Postgres).
            repo_row = analysis_session.query(RepoModel).filter(RepoModel.id == repo_id).first()
            repo_name = repo_row.name if repo_row else str(repo_id)

            # Get all edges in the code graph
            all_edges = analysis_session.query(Edge).filter(Edge.repo_id == repo_id).all()

            report["total_edges"] = len(all_edges)
            logger.info(f"Building spec graph from {len(all_edges)} code edges")

            # Get all specs for this repo
            all_specs = (
                spec_session.query(Spec)
                .filter(
                    Spec.repo == repo_name,
                    Spec.status != "error",  # Skip error specs
                )
                .all()
            )

            # Build a mapping: component_ref -> Spec
            spec_map = {spec.component_ref: spec for spec in all_specs}

            # Process each edge
            for edge in all_edges:
                try:
                    # Get source and target nodes
                    src_node = (
                        analysis_session.query(Node).filter(Node.id == edge.src_node_id).first()
                    )
                    dst_node = (
                        analysis_session.query(Node).filter(Node.id == edge.dst_node_id).first()
                    )

                    if not src_node or not dst_node:
                        continue

                    # Find specs that contain these nodes
                    src_spec_ref = src_node.qualified_name
                    dst_spec_ref = dst_node.qualified_name

                    # Check if both nodes have specs
                    if src_spec_ref not in spec_map or dst_spec_ref not in spec_map:
                        continue

                    spec_edge_kind = _map_edge_kind(edge.kind)

                    # Skip if spec edge already exists
                    existing_edge = (
                        spec_session.query(SpecEdge)
                        .filter(
                            SpecEdge.session_id == user_id,
                            SpecEdge.repo == repo_name,
                            SpecEdge.src_component_ref == src_spec_ref,
                            SpecEdge.dst_component_ref == dst_spec_ref,
                            SpecEdge.kind == spec_edge_kind,
                        )
                        .first()
                    )

                    if existing_edge:
                        continue

                    # Create spec edge
                    spec_edge = SpecEdge(
                        user_id=user_id,
                        repo=repo_name,
                        src_component_ref=src_spec_ref,
                        dst_component_ref=dst_spec_ref,
                        kind=spec_edge_kind,
                        derived_from=edge.kind,
                    )
                    spec_session.add(spec_edge)
                    report["created_edges"] += 1

                except Exception as e:
                    logger.warning(f"Failed to create spec edge for L1 edge {edge.id}: {e}")
                    report["errors"].append({"edge_id": str(edge.id), "error": str(e)})

            spec_session.commit()
            logger.info(f"Spec graph built: {report['created_edges']} edges created")

        except Exception as e:
            logger.error(f"Spec graph builder failed: {e}")
            report["errors"].append({"error": str(e)})

        return report
