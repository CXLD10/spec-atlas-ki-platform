"""Groq API key manager with round-robin rotation and 429 tracking."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session as DBSession

logger = logging.getLogger(__name__)


class GroqKeyManager:
    """Manages multiple Groq API keys with round-robin rotation."""

    def __init__(self):
        keys_str = os.environ.get("GROQ_API_KEYS", "")
        if not keys_str:
            logger.warning("No GROQ_API_KEYS set, falling back to fake provider")
            self.keys = []
        else:
            self.keys = [k.strip() for k in keys_str.split(",") if k.strip()]

        logger.info(f"Initialized Groq manager with {len(self.keys)} API keys")

    def get_key_for_session(self, db_session: DBSession, session_id) -> str | None:
        """Get API key for session (respects assignment + rotation)."""
        if not self.keys:
            return None

        try:
            from spec_atlas.db.analysis import Session

            session = db_session.query(Session).filter(Session.id == session_id).first()
            assigned_idx = session.assigned_groq_key_index if session else 0

            # Find next available key starting from assigned
            for offset in range(len(self.keys)):
                idx = (assigned_idx + offset) % len(self.keys)
                if self._is_key_available(db_session, idx):
                    return self.keys[idx]

            # All keys rate-limited
            logger.warning("All Groq keys rate-limited, will use fake provider")
            return None
        except Exception as e:
            logger.error(f"Error getting key for session: {e}")
            return None

    def _is_key_available(self, db_session: DBSession, key_idx: int) -> bool:
        """Check if key is currently available (not in cooldown)."""
        from spec_atlas.db.analysis import GroqKeyStatus

        status = db_session.query(GroqKeyStatus).filter(
            GroqKeyStatus.key_index == key_idx
        ).first()

        if not status:
            # First use, mark as available
            status = GroqKeyStatus(key_index=key_idx, is_available=True)
            db_session.add(status)
            db_session.commit()
            return True

        if status.is_available:
            return True

        # Check if cooldown period has passed (5 minutes)
        if (
            status.last_429_at
            and datetime.utcnow() > status.last_429_at + timedelta(minutes=5)
        ):
            status.is_available = True
            status.consecutive_failures = 0
            db_session.commit()
            return True

        return False

    def on_429_error(self, db_session: DBSession, key_idx: int):
        """Handle 429 rate limit error for a key."""
        from spec_atlas.db.analysis import GroqKeyStatus

        status = db_session.query(GroqKeyStatus).filter(
            GroqKeyStatus.key_index == key_idx
        ).first()

        if not status:
            status = GroqKeyStatus(key_index=key_idx)
            db_session.add(status)

        status.consecutive_failures += 1
        status.last_429_at = datetime.utcnow()

        if status.consecutive_failures > 3:
            status.is_available = False
            logger.warning(f"Groq key {key_idx} disabled for 5 minutes")

        db_session.commit()

    def rotate_key_for_session(self, db_session: DBSession, session_id):
        """Move session to next key (on 429)."""
        from spec_atlas.db.analysis import Session

        session = db_session.query(Session).filter(Session.id == session_id).first()

        if session:
            session.assigned_groq_key_index = (
                session.assigned_groq_key_index + 1
            ) % len(self.keys)
            db_session.commit()
            logger.info(f"Session {session_id} rotated to key {session.assigned_groq_key_index}")
