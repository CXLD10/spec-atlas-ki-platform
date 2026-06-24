"""FastAPI application wiring for Spec-Atlas."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from spec_atlas.config import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    logger.info("Spec-Atlas starting up")
    yield
    logger.info("Spec-Atlas shutting down")


def create_app(settings=None) -> FastAPI:
    """Create and configure the FastAPI application."""
    resolved = settings or get_settings()

    app = FastAPI(
        title="Spec-Atlas",
        description="From what the code is to what the code means.",
        lifespan=lifespan,
    )

    # Store settings in app state
    app.state.settings = resolved

    # Initialize database session factories (needed by health/answer/graph/groups/specs)
    try:
        from spec_atlas.db import analysis_session, spec_session

        app.state.analysis_session_factory = (
            analysis_session(resolved) if resolved.analysis_db_url else None
        )
        app.state.spec_session_factory = spec_session(resolved) if resolved.spec_db_url else None
    except Exception as e:
        logger.warning(f"Failed to initialize database sessions: {e}")
        app.state.analysis_session_factory = None
        app.state.spec_session_factory = None

    # Initialize providers
    try:
        from spec_atlas.embed import get_embedding_provider
        from spec_atlas.llm import get_llm_provider

        app.state.llm_provider = get_llm_provider(resolved)
        app.state.embedding_provider = get_embedding_provider(resolved)
    except Exception as e:
        logger.warning(f"Failed to initialize providers: {e}")
        app.state.llm_provider = None
        app.state.embedding_provider = None

    # Rate limiting — register the exception handler so slowapi returns 429
    try:
        from slowapi import _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded
        from spec_atlas.api.ingest import HAS_LIMITER, limiter

        if HAS_LIMITER and limiter is not None:
            app.state.limiter = limiter
            app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    except Exception as e:
        logger.debug(f"slowapi wiring skipped: {e}")

    # Session Middleware (automatic multi-user isolation)
    from spec_atlas.api.middleware import SessionMiddleware

    app.add_middleware(SessionMiddleware)

    # CORS Middleware (permissive for local dev)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # ── Health — plain function, not a router ────────────────────
    from spec_atlas.api.health import health

    app.add_api_route("/health", health, methods=["GET"], tags=["health"])

    # ── Routers ──────────────────────────────────────────────────
    from spec_atlas.api.answer import router as answer_router
    from spec_atlas.api.docs import router as docs_router
    from spec_atlas.api.graph import router as graph_router
    from spec_atlas.api.groups import router as groups_router
    from spec_atlas.api.ingest import router as ingest_router
    from spec_atlas.api.kb import router as kb_router
    from spec_atlas.api.mcp_bridge import router as mcp_router
    from spec_atlas.api.reports import router as reports_router
    from spec_atlas.api.sources import router as sources_router
    from spec_atlas.api.specs import router as specs_router

    app.include_router(ingest_router, tags=["ingest"])
    app.include_router(answer_router, tags=["answer"])
    app.include_router(graph_router, tags=["graph"])
    app.include_router(groups_router, tags=["groups"])
    app.include_router(specs_router, tags=["specs"])
    app.include_router(kb_router, tags=["kb"])
    app.include_router(reports_router, tags=["reports"])
    app.include_router(sources_router, tags=["sources"])
    app.include_router(docs_router, tags=["docs"])
    app.include_router(mcp_router, tags=["mcp"])

    # ── Root ─────────────────────────────────────────────────────
    @app.get("/")
    async def root():
        return {"status": "ok", "service": "spec-atlas"}

    return app


# Create the app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
