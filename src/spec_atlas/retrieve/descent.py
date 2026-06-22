"""Tree descent: bounded context assembly from group hierarchy."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from spec_atlas.db.analysis import Group
from spec_atlas.db.spec import Spec

if TYPE_CHECKING:
    pass


@dataclass
class Context:
    """Bounded context assembled from group hierarchy."""

    matched_group: Group
    child_groups: list[Group]
    specs: list[Spec]
    source_spans: list[dict]
    tree_path: list[Group]


class TreeDescent:
    """Walk group tree downward and assemble bounded context."""

    @staticmethod
    def descend(
        group_id: uuid.UUID,
        session: Session,
        max_specs: int = 8,
        max_spans: int = 100,
    ) -> Context:
        """Walk from group downward, collect specs + source spans.

        Args:
            group_id: Root group to descend from.
            session: Analysis DB session.
            max_specs: Maximum number of specs to collect.
            max_spans: Maximum number of source spans to collect.

        Returns:
            Context object with matched_group, child_groups, specs, source_spans, tree_path.
        """
        # Fetch the matched group
        matched_group = session.query(Group).filter(Group.id == group_id).first()
        if not matched_group:
            raise ValueError(f"Group {group_id} not found")

        # Build tree path (root to matched group)
        tree_path = TreeDescent._build_tree_path(matched_group, session)

        # Collect child groups (immediate children)
        child_groups = (
            session.query(Group).filter(Group.parent_id == group_id).order_by(Group.path).all()
        )

        # Collect specs from matched group
        specs = []
        source_spans = []

        # Get specs for the matched group
        if matched_group.member_spec_refs:
            for spec_ref in matched_group.member_spec_refs[:max_specs]:
                # Parse component_ref@version (or just component_ref for current)
                parts = spec_ref.split("@")
                component_ref = parts[0]

                # Fetch current spec (valid_to is None)
                spec = (
                    session.query(Spec)
                    .filter(
                        Spec.component_ref == component_ref,
                        Spec.valid_to.is_(None),
                    )
                    .first()
                )

                if spec:
                    specs.append(spec)

                    # Collect source spans from provenance
                    if spec.provenance:
                        for span in spec.provenance:
                            if len(source_spans) < max_spans:
                                source_spans.append(span)

        return Context(
            matched_group=matched_group,
            child_groups=child_groups,
            specs=specs,
            source_spans=source_spans,
            tree_path=tree_path,
        )

    @staticmethod
    def _build_tree_path(group: Group, session: Session) -> list[Group]:
        """Build path from root to the given group.

        Args:
            group: The target group.
            session: Analysis DB session.

        Returns:
            List of groups from root to target (inclusive).
        """
        path = [group]

        # Walk up to root
        current = group
        while current.parent_id is not None:
            parent = session.query(Group).filter(Group.id == current.parent_id).first()
            if parent:
                path.insert(0, parent)
                current = parent
            else:
                break

        return path
