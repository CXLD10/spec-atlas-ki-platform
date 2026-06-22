"""Ingest job store — persistence layer for async ingest jobs."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from spec_atlas.db.analysis import IngestJob

if TYPE_CHECKING:
    pass


class IngestJobStore:
    """Store and retrieve ingest jobs from the database."""

    @staticmethod
    def create_job(session: Session, repo_url: str) -> str:
        """Create a new ingest job.

        Args:
            session: Analysis DB session.
            repo_url: Repository URL to ingest.

        Returns:
            Job ID (UUID string).
        """
        job = IngestJob(
            id=uuid.uuid4(),
            repo_url=repo_url,
            status="queued",
            progress_pct=0,
            error_message=None,
        )
        session.add(job)
        session.commit()
        return str(job.id)

    @staticmethod
    def get_job(session: Session, job_id: str) -> IngestJob | None:
        """Retrieve an ingest job by ID.

        Args:
            session: Analysis DB session.
            job_id: Job ID (UUID string).

        Returns:
            IngestJob or None if not found.
        """
        try:
            job_uuid = uuid.UUID(job_id)
        except ValueError:
            return None

        return session.query(IngestJob).filter(IngestJob.id == job_uuid).first()

    @staticmethod
    def update_job_status(
        session: Session,
        job_id: str,
        status: str,
        progress_pct: int = 0,
        error_message: str | None = None,
    ) -> bool:
        """Update an ingest job's status.

        Args:
            session: Analysis DB session.
            job_id: Job ID.
            status: New status (queued, in_progress, done, error).
            progress_pct: Progress percentage (0-100).
            error_message: Optional error message if status is 'error'.

        Returns:
            True if job was updated, False if not found.
        """
        job = IngestJobStore.get_job(session, job_id)
        if not job:
            return False

        job.status = status
        job.progress_pct = progress_pct
        if error_message:
            job.error_message = error_message

        session.commit()
        return True
