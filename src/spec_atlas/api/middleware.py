"""Session middleware for automatic multi-user isolation."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class SessionMiddleware(BaseHTTPMiddleware):
    """Automatic session management middleware."""

    SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/static"}

    async def dispatch(self, request: Request, call_next):
        # Skip middleware for certain paths
        if request.url.path in self.SKIP_PATHS or request.url.path.startswith("/static"):
            return await call_next(request)

        try:
            # Generate or get session ID from cookie
            session_id_str = request.cookies.get("session_id")
            if not session_id_str:
                session_id_str = str(uuid.uuid4())
                logger.info(f"Created new session: {session_id_str}")
                session_id_uuid = uuid.UUID(session_id_str)

                # Create session in database (ensure FK constraint is satisfied)
                try:
                    from spec_atlas.db import get_analysis_session
                    from spec_atlas.db.analysis import Session

                    session = get_analysis_session()
                    try:
                        # Check if session exists
                        existing = session.query(Session).filter(Session.id == session_id_uuid).first()
                        if not existing:
                            new_session = Session(
                                id=session_id_uuid,
                                expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
                            )
                            session.add(new_session)
                            session.commit()
                            logger.info(f"Session {session_id_str} inserted into database")
                    finally:
                        session.close()
                except Exception as e:
                    logger.warning(f"Failed to create session in database: {e}")
            else:
                session_id_uuid = uuid.UUID(session_id_str)

            # Inject into request state
            request.state.session_id = session_id_uuid

            # Process request
            response = await call_next(request)

            # Set secure session cookie
            response.set_cookie(
                "session_id",
                session_id_str,
                max_age=7200,  # 2 hours
                httponly=True,
                secure=False,  # Set to True in production (HTTPS only)
                samesite="Lax",
            )

            return response

        except Exception as e:
            logger.error(f"Session middleware error: {e}", exc_info=True)
            return JSONResponse({"error": "Session error"}, status_code=500)
