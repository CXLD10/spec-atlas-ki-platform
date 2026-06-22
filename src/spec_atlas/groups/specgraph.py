"""Build spec graph (L3) from L1 edges that cross group boundaries."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from spec_atlas.db.analysis import Edge, Group
from spec_atlas.db.spec import Spec, SpecEdge

if TYPE_CHECKING:
    pass


class SpecGraphBuilder:
    """Build spec graph edges from L1 code edges that cross group boundaries."""

    # Mapping from L1 edge kinds to L3 spec edge kinds
    L1_TO_L3_KIND = {
        "imports": "depends-on",
        "calls": "depends-on",
        "inherits": "depends-on",
        "defines": "part-of",
    }

    @staticmethod
    def build_edges(
        repo_id: uuid.UUID,
        user_id: str,
        repo_name: str,
        groups: list[Group],
        specs: list[Spec],
        edges: list[Edge],
        session: Session,
    ) -> list[SpecEdge]:
        """Build spec edges from L1 edges crossing group boundaries.

        Args:
            repo_id: Repository ID.
            user_id: User ID (for spec lookups).
            repo_name: Repository name (for spec lookups).
            groups: List of all Group objects for the repo.
            specs: List of all current Spec objects for the repo.
            edges: List of all Edge objects (L1) for the repo.
            session: Analysis DB session.

        Returns:
            List of SpecEdge objects (not yet persisted).
        """
        # Build mappings
        # Map node_id → group_id
        node_to_group: dict[uuid.UUID, uuid.UUID] = {}
        for group in groups:
            for node_id in group.member_node_ids:
                node_to_group[node_id] = group.id

        # Map group_id → list of specs (component_ref)
        group_to_specs: dict[uuid.UUID, list[str]] = {}
        for group in groups:
            group_to_specs[group.id] = group.member_spec_refs

        # Build list of candidate spec edges
        candidate_edges: dict[tuple[str, str, str], SpecEdge] = {}

        for edge in edges:
            src_node_id = edge.src_node_id
            dst_node_id = edge.dst_node_id
            l1_kind = edge.kind

            # Skip if either node is unknown
            if src_node_id not in node_to_group or dst_node_id not in node_to_group:
                continue

            src_group_id = node_to_group[src_node_id]
            dst_group_id = node_to_group[dst_node_id]

            # Skip if within the same group
            if src_group_id == dst_group_id:
                continue

            # Find source specs (anchored to source group)
            src_specs = group_to_specs.get(src_group_id, [])
            dst_specs = group_to_specs.get(dst_group_id, [])

            # Create edges for each (src_spec, dst_spec) pair
            l3_kind = SpecGraphBuilder.L1_TO_L3_KIND.get(l1_kind, "depends-on")

            for src_ref in src_specs:
                for dst_ref in dst_specs:
                    # Avoid self-loops
                    if src_ref == dst_ref:
                        continue

                    # Deduplicate by (src_ref, dst_ref, kind)
                    key = (src_ref, dst_ref, l3_kind)
                    if key in candidate_edges:
                        continue

                    spec_edge = SpecEdge(
                        user_id=user_id,
                        repo=repo_name,
                        src_component_ref=src_ref,
                        dst_component_ref=dst_ref,
                        kind=l3_kind,
                        derived_from=l1_kind,
                    )
                    candidate_edges[key] = spec_edge

        return list(candidate_edges.values())

    @staticmethod
    def persist_edges(
        edges: list[SpecEdge],
        session: Session,
    ) -> list[SpecEdge]:
        """Persist spec edges to the Spec DB.

        Args:
            edges: List of SpecEdge objects to persist.
            session: Spec DB session.

        Returns:
            List of persisted SpecEdge objects.
        """
        for edge in edges:
            session.add(edge)

        session.commit()
        return edges
