"""Spec store service — versioning, retrieval, status management."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from spec_atlas.db.spec import Spec, SpecEdge

if TYPE_CHECKING:
    from spec_atlas.verify.verifier import VerificationResult


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
                    Spec.session_id == user_id,
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
                    Spec.session_id == user_id,
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
                    Spec.session_id == user_id,
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
                    Spec.session_id == user_id,
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
                    SpecEdge.session_id == user_id,
                    SpecEdge.repo == repo,
                    SpecEdge.src_component_ref == src_component_ref,
                )
            )
            .all()
        )

    def verify_spec(
        self,
        user_id: str,
        repo: str,
        component_ref: str,
        version: int | None = None,
        analysis_session: Session | None = None,
    ) -> VerificationResult:
        """Verify a spec against source code (idempotent).

        Runs rule-based verification and updates spec status.
        Safe to call multiple times (returns cached result if already verified).

        Args:
            user_id: User ID (fixed to "default" in v1).
            repo: Repository name.
            component_ref: Component reference.
            version: Specific version to verify (latest if None).
            analysis_session: Analysis DB session for verifier (required).

        Returns:
            VerificationResult with confidence, is_grounded, issues.

        Raises:
            ValueError: If spec not found or analysis_session not provided.
        """
        if not analysis_session:
            raise ValueError("analysis_session required for verification")

        # Get spec (use provided version or latest)
        if version is not None:
            spec = self.get_version(user_id, repo, component_ref, version)
        else:
            spec = self.get_current(user_id, repo, component_ref)

        if not spec:
            raise ValueError(f"Spec not found: {component_ref} v{version or 'current'}")

        # Idempotency: if already verified, return cached result
        if spec.status == "verified":
            # Return cached result from metadata
            verification_meta = spec.content.get("_verification_metadata", {})
            if verification_meta:
                from spec_atlas.verify.verifier import (
                    VerificationIssue,
                    VerificationResult,
                )

                return VerificationResult(
                    is_grounded=True,
                    confidence=verification_meta.get("confidence", 1.0),
                    issues=[
                        VerificationIssue(
                            claim=i.get("claim", ""),
                            reason=i.get("reason", ""),
                            severity=i.get("severity", "warning"),
                        )
                        for i in verification_meta.get("issues", [])
                    ],
                )

        # Run verification
        from spec_atlas.verify.verifier import SpecVerifier

        verifier = SpecVerifier(analysis_session)
        result = verifier.verify(spec, repo, component_ref)

        # Determine new status based on confidence
        if result.confidence > 0.8 and result.is_grounded:
            new_status = "verified"
        elif result.confidence >= 0.5:
            new_status = "review"
        else:
            new_status = "draft"

        # Update spec with status and verification metadata
        if new_status != spec.status:
            spec.status = new_status

        # Store verification metadata in spec content for idempotency
        if "content" not in dir(spec):
            spec.content = {}
        spec.content["_verification_metadata"] = {
            "confidence": result.confidence,
            "is_grounded": result.is_grounded,
            "verified_at": datetime.utcnow().isoformat(),
            "issues": [
                {"claim": i.claim, "reason": i.reason, "severity": i.severity}
                for i in result.issues
            ],
        }

        self.session.commit()

        return result

    def get_verification_report(self, user_id: str, repo: str) -> dict:
        """Get overall verification statistics for a repo.

        Args:
            user_id: User ID (fixed to "default" in v1).
            repo: Repository name.

        Returns:
            Dict with verification statistics.
        """
        # Get all current specs for this repo
        specs = (
            self.session.query(Spec)
            .filter(
                and_(
                    Spec.session_id == user_id,
                    Spec.repo == repo,
                    Spec.valid_to.is_(None),  # current versions only
                )
            )
            .all()
        )

        if not specs:
            return {
                "total_specs": 0,
                "verified_count": 0,
                "review_count": 0,
                "draft_count": 0,
                "avg_confidence": 0.0,
                "verification_rate": 0.0,
                "specs_needing_review": 0,
            }

        verified = [s for s in specs if s.status == "verified"]
        review = [s for s in specs if s.status == "review"]
        draft = [s for s in specs if s.status == "draft"]

        # Extract confidence from verification metadata
        confidences = []
        for spec in specs:
            metadata = spec.content.get("_verification_metadata", {})
            if metadata and "confidence" in metadata:
                confidences.append(metadata["confidence"])

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return {
            "total_specs": len(specs),
            "verified_count": len(verified),
            "review_count": len(review),
            "draft_count": len(draft),
            "avg_confidence": round(avg_confidence, 3),
            "verification_rate": (round(len(verified) / len(specs) * 100, 1) if specs else 0.0),
            "specs_needing_review": len(review),
        }

    def get_verification_issues(self, user_id: str, repo: str, limit: int = 10) -> list[dict]:
        """Get most common verification issues in a repo.

        Args:
            user_id: User ID.
            repo: Repository name.
            limit: Maximum number of issues to return.

        Returns:
            List of dicts with reason and count.
        """
        # Get all current specs
        specs = (
            self.session.query(Spec)
            .filter(
                and_(
                    Spec.session_id == user_id,
                    Spec.repo == repo,
                    Spec.valid_to.is_(None),  # current versions only
                )
            )
            .all()
        )

        all_issues = []
        for spec in specs:
            issues = spec.content.get("_verification_metadata", {}).get("issues", [])
            all_issues.extend(issues)

        # Count by reason
        issue_reasons = Counter([i.get("reason", "unknown") for i in all_issues])

        return [
            {"reason": reason, "count": count} for reason, count in issue_reasons.most_common(limit)
        ]

    def get_confidence_distribution(self, user_id: str, repo: str, bins: int = 5) -> dict:
        """Get histogram of confidence scores.

        Args:
            user_id: User ID.
            repo: Repository name.
            bins: Number of bins for histogram (default 5).

        Returns:
            Dict with bin edges and counts.
        """
        # Get all current specs
        specs = (
            self.session.query(Spec)
            .filter(
                and_(
                    Spec.session_id == user_id,
                    Spec.repo == repo,
                    Spec.valid_to.is_(None),  # current versions only
                )
            )
            .all()
        )

        # Extract confidence values
        confidences = []
        for spec in specs:
            metadata = spec.content.get("_verification_metadata", {})
            if metadata and "confidence" in metadata:
                confidences.append(metadata["confidence"])

        if not confidences:
            return {"bins": [], "counts": []}

        # Create bins: 0.0-1/n, 1/n-2/n, ..., (n-1)/n-1.0
        bin_edges = [i / bins for i in range(bins + 1)]
        bin_counts = [0] * bins

        for conf in confidences:
            # Find which bin this confidence falls into
            bin_found = False
            for i in range(len(bin_edges) - 1):
                if bin_edges[i] <= conf < bin_edges[i + 1]:
                    bin_counts[i] += 1
                    bin_found = True
                    break

            # conf == 1.0, put in last bin
            if not bin_found:
                bin_counts[-1] += 1

        return {
            "bins": [
                f"{bin_edges[i]:.1f}-{bin_edges[i + 1]:.1f}" for i in range(len(bin_edges) - 1)
            ],
            "counts": bin_counts,
        }
