"""Session middleware for automatic multi-user isolation."""

from __future__ import annotations

import logging
import uuid
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
            session_id = request.cookies.get("session_id")
            if not session_id:
                session_id = str(uuid.uuid4())
                logger.info(f"Created new session: {session_id}")

            # Inject into request state
            request.state.session_id = uuid.UUID(session_id)

            # Process request
            response = await call_next(request)

            # Set secure session cookie
            response.set_cookie(
                "session_id",
                session_id,
                max_age=7200,  # 2 hours
                httponly=True,
                secure=False,  # Set to True in production (HTTPS only)
                samesite="Lax",
            )

            return response

        except Exception as e:
            logger.error(f"Session middleware error: {e}", exc_info=True)
            return JSONResponse({"error": "Session error"}, status_code=500)
