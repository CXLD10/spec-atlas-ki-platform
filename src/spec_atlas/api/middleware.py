"""Session middleware for automatic multi-user isolation."""

from __future__ import annotations

import logging
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from spec_atlas.session.manager import SessionManager
from spec_atlas.db.analysis import get_analysis_session

logger = logging.getLogger(__name__)


class SessionMiddleware(BaseHTTPMiddleware):
    """Automatic session management middleware."""

    SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/static"}

    async def dispatch(self, request: Request, call_next):
        # Skip middleware for certain paths
        if request.url.path in self.SKIP_PATHS or request.url.path.startswith("/static"):
            return await call_next(request)

        db_session = get_analysis_session()
        session_id = None

        try:
            # Get or create session from cookie
            session_id = request.cookies.get("session_id")

            if not session_id:
                # New user → create session
                session_id = SessionManager.create_session(db_session)
                logger.info(f"Created new session: {session_id}")
            else:
                # Existing user → check if expired
                try:
                    session_uuid = uuid.UUID(session_id)

                    if SessionManager.is_session_expired(db_session, session_uuid):
                        logger.warning(f"Session expired: {session_id}, creating new")
                        SessionManager.delete_session_data(db_session, session_uuid)
                        session_id = SessionManager.create_session(db_session)
                    else:
                        # Update last interaction
                        SessionManager.update_last_interaction(db_session, session_uuid)

                except (ValueError, AttributeError):
                    # Invalid session ID, create new
                    logger.warning(f"Invalid session ID: {session_id}, creating new")
                    session_id = SessionManager.create_session(db_session)

            # Inject into request state
            request.state.session_id = uuid.UUID(str(session_id))

            # Process request
            response = await call_next(request)

            # Set secure session cookie
            response.set_cookie(
                "session_id",
                str(session_id),
                max_age=7200,  # 2 hours
                httponly=True,
                secure=False,  # Set to True in production (HTTPS only)
                samesite="Lax",
            )

            return response

        except Exception as e:
            logger.error(f"Session middleware error: {e}", exc_info=True)
            return JSONResponse({"error": "Session error"}, status_code=500)

        finally:
            if db_session:
                db_session.close()
