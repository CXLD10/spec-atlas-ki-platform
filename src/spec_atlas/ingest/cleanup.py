"""Background cleanup job for expired sessions."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from spec_atlas.db.analysis import Session, get_analysis_session

logger = logging.getLogger(__name__)


async def cleanup_expired_sessions():
    """Background job: delete sessions older than 2 hours."""
    while True:
        try:
            db_session = get_analysis_session()
            now = datetime.utcnow()

            # Find expired sessions
            expired = db_session.query(Session).filter(
                Session.created_at < now - timedelta(hours=2),
                Session.is_deleted == False,
            ).all()

            deleted_count = 0
            for session in expired:
                logger.info(f"Cleaning up expired session: {session.id}")
                session.is_deleted = True
                deleted_count += 1

            if deleted_count > 0:
                db_session.commit()
                logger.info(f"Cleaned up {deleted_count} expired sessions")

            db_session.close()

            # Run every 15 minutes
            await asyncio.sleep(900)

        except Exception as e:
            logger.error(f"Cleanup job error: {e}", exc_info=True)
            await asyncio.sleep(60)  # Retry after 1 min on error


def start_cleanup_job():
    """Start the cleanup background task."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.create_task(cleanup_expired_sessions())
        logger.info("Cleanup job started")
    except Exception as e:
        logger.error(f"Failed to start cleanup job: {e}")
