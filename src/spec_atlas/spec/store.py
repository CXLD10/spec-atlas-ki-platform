"""Spec store service — versioning, retrieval, status management."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from spec_atlas.db.spec import Spec, SpecEdge


class SpecStore:
    """Service for storing and retrieving versioned specs."""

    def __init__(self, session: Session) -> None:
        """Initialize with a database session.

        Args:
            session: SQLAlchemy session for the Spec DB.
        """
        self.session = session

    def create(
        self,
        user_id: str,
        repo: str,
        component_ref: str,
        spec_content: dict,
        provenance: list | None = None,
        source_fingerprint: str | None = None,
        status: str = "draft",
    ) -> Spec:
        """Create a new spec version.

        Args:
            user_id: User ID (fixed to "default" in v1).
            repo: Repository name.
            component_ref: Component reference (qualified name or group path).
            spec_content: The spec JSON content.
            provenance: List of {file, start_line, end_line} spans.
            source_fingerprint: Hash of source code the spec was generated from.
            status: Initial status ("draft", "verified", or "stale").

        Returns:
            The newly created Spec object.
        """
        # Get next version number
        latest = (
            self.session.query(func.max(Spec.version))
            .filter(
                and_(
                    Spec.user_id == user_id,
                    Spec.repo == repo,
                    Spec.component_ref == component_ref,
                )
            )
            .scalar()
        )
        next_version = (latest or 0) + 1

        # Mark prior version as stale (set valid_to)
        prior = self.get_current(user_id, repo, component_ref)
        if prior:
            prior.valid_to = datetime.utcnow()
            self.session.flush()

        # Create new spec
        spec = Spec(
            user_id=user_id,
            repo=repo,
            component_ref=component_ref,
            version=next_version,
            status=status,
            content=spec_content,
            provenance=provenance or [],
            source_fingerprint=source_fingerprint,
        )
        self.session.add(spec)
        self.session.flush()

        # Create spec edges for dependencies
        if spec_content.get("dependencies"):
            for dep_ref in spec_content["dependencies"]:
                edge = SpecEdge(
                    user_id=user_id,
                    repo=repo,
                    src_component_ref=component_ref,
                    dst_component_ref=dep_ref,
                    kind="depends-on",
                    derived_from="",  # Will be set later if there's a corresponding L1 edge
                )
                self.session.add(edge)

        self.session.commit()
        return spec

    def get_current(self, user_id: str, repo: str, component_ref: str) -> Spec | None:
        """Get the current (latest) version of a spec.

        Args:
            user_id: User ID.
            repo: Repository name.
            component_ref: Component reference.

        Returns:
            The current Spec or None if not found.
        """
        return (
            self.session.query(Spec)
            .filter(
                and_(
                    Spec.user_id == user_id,
                    Spec.repo == repo,
                    Spec.component_ref == component_ref,
                    Spec.valid_to.is_(None),  # current version
                )
            )
            .first()
        )

    def get_version(self, user_id: str, repo: str, component_ref: str, version: int) -> Spec | None:
        """Get a specific version of a spec.

        Args:
            user_id: User ID.
            repo: Repository name.
            component_ref: Component reference.
            version: Version number.

        Returns:
            The Spec at that version or None if not found.
        """
        return (
            self.session.query(Spec)
            .filter(
                and_(
                    Spec.user_id == user_id,
                    Spec.repo == repo,
                    Spec.component_ref == component_ref,
                    Spec.version == version,
                )
            )
            .first()
        )

    def get_all_versions(self, user_id: str, repo: str, component_ref: str) -> list[Spec]:
        """Get all versions of a spec (newest first).

        Args:
            user_id: User ID.
            repo: Repository name.
            component_ref: Component reference.

        Returns:
            List of Spec objects ordered by version descending.
        """
        return (
            self.session.query(Spec)
            .filter(
                and_(
                    Spec.user_id == user_id,
                    Spec.repo == repo,
                    Spec.component_ref == component_ref,
                )
            )
            .order_by(desc(Spec.version))
            .all()
        )

    def update_status(
        self, user_id: str, repo: str, component_ref: str, version: int, status: str
    ) -> Spec | None:
        """Update the status of a specific spec version.

        Args:
            user_id: User ID.
            repo: Repository name.
            component_ref: Component reference.
            version: Version number.
            status: New status ("draft", "verified", or "stale").

        Returns:
            The updated Spec or None if not found.
        """
        spec = self.get_version(user_id, repo, component_ref, version)
        if spec:
            spec.status = status
            self.session.commit()
        return spec

    def get_edges(self, user_id: str, repo: str, src_component_ref: str) -> list[SpecEdge]:
        """Get outgoing edges from a component.

        Args:
            user_id: User ID.
            repo: Repository name.
            src_component_ref: Source component reference.

        Returns:
            List of SpecEdge objects.
        """
        return (
            self.session.query(SpecEdge)
            .filter(
                and_(
                    SpecEdge.user_id == user_id,
                    SpecEdge.repo == repo,
                    SpecEdge.src_component_ref == src_component_ref,
                )
            )
            .all()
        )
