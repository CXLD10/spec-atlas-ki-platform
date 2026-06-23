"""DriftDetector: compare source fingerprints on re-ingest, mark stale (F-014)."""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fingerprint computation (deterministic, matches F-005.3 algorithm)
# ---------------------------------------------------------------------------

def compute_fingerprint(spans: list[dict]) -> str:
    """SHA256 of sorted '{file}:{start_line}:{end_line}' provenance spans.

    Same algorithm used at spec-creation time (F-005.3). Identical source
    spans always produce the same fingerprint — guaranteed stable for
    idempotent re-ingests when code hasn't changed.

    Args:
        spans: List of {file, start_line, end_line} dicts.

    Returns:
        Hex-encoded SHA256 string.
    """
    tokens = sorted(
        f"{s.get('file', '')}:{s.get('start_line', '')}:{s.get('end_line', '')}"
        for s in spans
    )
    return hashlib.sha256("\n".join(tokens).encode()).hexdigest()


# ---------------------------------------------------------------------------
# Report dataclasses
# ---------------------------------------------------------------------------

@dataclass
class StaleItem:
    id: str
    kind: str  # "spec"
    component_ref: str
    old_fingerprint: str
    new_fingerprint: str
    reason: str


@dataclass
class DriftReport:
    repo_id: str
    stale_specs: list[StaleItem] = field(default_factory=list)
    stale_groups: list[StaleItem] = field(default_factory=list)
    new_coverage: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)

    def is_clean(self) -> bool:
        return not self.stale_specs and not self.stale_groups


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------

class DriftDetector:
    """Compare stored source fingerprints against recomputed ones after re-ingest."""

    @staticmethod
    def detect_drift(
        repo_id: uuid.UUID | str,
        spec_session: Session,
        file_contents: dict[str, str] | None = None,
    ) -> DriftReport:
        """Compare stored fingerprints for all specs in ``repo_id`` against
        recomputed fingerprints from current provenance spans.

        Since the spec DB stores provenance as ``{file, start_line, end_line}``
        lists, drift is detected by re-hashing those same spans and comparing
        to ``source_fingerprint``. If the code file has changed (different
        content at those lines), the calling pipeline should update the file
        hashes *before* calling detect_drift so the fingerprint reflects the
        new state.

        For v1 (on-demand, no file-watching): we re-hash the stored spans.
        Drift is detected when the file content at those spans changes.  The
        simplest implementation hashes the *span identifiers* only (not the
        actual file bytes at those lines), which means drift is triggered when
        provenance metadata changes (e.g. line numbers shift after a refactor).
        Content-based drift (same lines, different code) requires the caller
        to pass ``file_contents`` — we XOR a content hash into the fingerprint
        when available.

        Args:
            repo_id: Repository UUID (used to scope the spec query).
            spec_session: SQLAlchemy session for the Spec DB.
            file_contents: Optional {file_path: content_hash_or_text} map.
                When provided, content drift at the same lines is also detected.

        Returns:
            DriftReport with stale_specs listed.
        """
        from spec_atlas.db.spec import Spec

        repo_id_str = str(repo_id)
        report = DriftReport(repo_id=repo_id_str)

        # Query all current (valid_to IS NULL) specs for this repo
        specs = (
            spec_session.query(Spec)
            .filter(Spec.repo == repo_id_str, Spec.valid_to.is_(None))
            .all()
        )

        for spec in specs:
            if not spec.source_fingerprint:
                continue  # never fingerprinted — skip

            provenance = spec.provenance or []
            if not provenance:
                continue

            new_fp = compute_fingerprint(provenance)

            # Optionally fold in content hash for each referenced file
            if file_contents:
                content_tokens = []
                for span in provenance:
                    fpath = span.get("file", "")
                    if fpath in file_contents:
                        content_tokens.append(f"{fpath}:{file_contents[fpath][:64]}")
                if content_tokens:
                    combined = new_fp + "\n".join(sorted(content_tokens))
                    new_fp = hashlib.sha256(combined.encode()).hexdigest()

            if new_fp != spec.source_fingerprint:
                report.stale_specs.append(
                    StaleItem(
                        id=str(spec.id),
                        kind="spec",
                        component_ref=spec.component_ref,
                        old_fingerprint=spec.source_fingerprint,
                        new_fingerprint=new_fp,
                        reason="source_fingerprint_mismatch",
                    )
                )

        report.details["specs_checked"] = len(specs)
        report.details["stale_count"] = len(report.stale_specs)
        return report

    @staticmethod
    def mark_stale(report: DriftReport, spec_session: Session) -> int:
        """Update Spec rows identified in the report to status='stale'.

        Sets:
          - status = 'stale'
          - staleness_detected_at = utcnow()

        Args:
            report: DriftReport returned by detect_drift().
            spec_session: SQLAlchemy session for the Spec DB (write access).

        Returns:
            Number of specs updated.
        """
        from spec_atlas.db.spec import Spec

        if not report.stale_specs:
            return 0

        now = datetime.now(tz=timezone.utc)
        stale_ids = {item.id for item in report.stale_specs}
        updated = 0

        specs = spec_session.query(Spec).filter(
            Spec.id.in_(stale_ids)  # type: ignore[arg-type]
        ).all()

        for spec in specs:
            if spec.status != "stale":
                spec.status = "stale"
                spec.staleness_detected_at = now
                updated += 1
                logger.info(
                    f"Marked spec {spec.component_ref!r} (id={spec.id}) stale "
                    f"(repo={spec.repo})"
                )

        spec_session.commit()
        return updated
