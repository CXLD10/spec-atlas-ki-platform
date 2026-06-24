"""Session manager for multi-user isolation."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session as DBSession

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages user sessions with automatic isolation and cleanup."""

    @staticmethod
    def create_session(db_session: DBSession) -> uuid.UUID:
        """Create a new session (no user input needed)."""
        from spec_atlas.db.analysis import Session

        session = Session(
            id=uuid.uuid4(),
            created_at=datetime.utcnow(),
            last_interaction_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=2),
            assigned_groq_key_index=0,
            repo_count=0,
        )
        db_session.add(session)
        db_session.commit()
        return session.id

    @staticmethod
    def get_session(db_session: DBSession, session_id: uuid.UUID):
        """Retrieve session or raise error."""
        from spec_atlas.db.analysis import Session

        session = (
            db_session.query(Session)
            .filter(Session.id == session_id, Session.is_deleted == False)
            .first()
        )

        if not session:
            raise ValueError(f"Session {session_id} not found or expired")

        return session

    @staticmethod
    def update_last_interaction(db_session: DBSession, session_id: uuid.UUID):
        """Update last_interaction_at timestamp."""
        from spec_atlas.db.analysis import Session

        db_session.query(Session).filter(Session.id == session_id).update(
            {Session.last_interaction_at: datetime.utcnow()}
        )
        db_session.commit()

    @staticmethod
    def is_session_expired(db_session: DBSession, session_id: uuid.UUID) -> bool:
        """Check if session is beyond 2-hour limit."""
        from spec_atlas.db.analysis import Session

        session = (
            db_session.query(Session)
            .filter(Session.id == session_id, Session.is_deleted == False)
            .first()
        )

        if not session:
            return True

        return datetime.utcnow() > session.expires_at

    @staticmethod
    def delete_session_data(db_session: DBSession, session_id: uuid.UUID):
        """Mark session as deleted (cascade delete via FK)."""
        from spec_atlas.db.analysis import Session

        session = db_session.query(Session).filter(Session.id == session_id).first()
        if session:
            session.is_deleted = True
            db_session.commit()
            logger.info(f"Session {session_id} marked for deletion")

    @staticmethod
    def increment_repo_count(db_session: DBSession, session_id: uuid.UUID):
        """Increment repo count for session."""
        from spec_atlas.db.analysis import Session

        db_session.query(Session).filter(Session.id == session_id).update(
            {Session.repo_count: Session.repo_count + 1}
        )
        db_session.commit()

    @staticmethod
    def decrement_repo_count(db_session: DBSession, session_id: uuid.UUID):
        """Decrement repo count for session."""
        from spec_atlas.db.analysis import Session

        db_session.query(Session).filter(Session.id == session_id).update(
            {Session.repo_count: Session.repo_count - 1}
        )
        db_session.commit()
