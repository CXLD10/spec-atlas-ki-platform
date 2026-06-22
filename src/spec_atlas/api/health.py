"""Health endpoint for app wiring, databases, and provider configuration."""

from __future__ import annotations

from typing import Any

from fastapi import Request, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from spec_atlas.config import Settings
from spec_atlas.embed.base import EmbeddingProvider
from spec_atlas.llm.base import LLMProvider

SessionFactory = sessionmaker[Session] | None


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_analysis_session_factory(request: Request) -> SessionFactory:
    return request.app.state.analysis_session_factory


def get_spec_session_factory(request: Request) -> SessionFactory:
    return request.app.state.spec_session_factory


def get_llm_provider(request: Request) -> LLMProvider:
    return request.app.state.llm_provider


def get_embedding_provider(request: Request) -> EmbeddingProvider:
    return request.app.state.embedding_provider


def _check_database(session_factory: SessionFactory) -> dict[str, str]:
    if session_factory is None:
        return {"status": "not_configured"}

    try:
        with session_factory() as session:
            session.execute(text("SELECT 1"))
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}

    return {"status": "ok"}


def _provider_status(
    provider: Any, configured_name: str, extra: dict[str, Any] | None = None
) -> dict[str, Any]:
    status_payload: dict[str, Any] = {"status": "ok", "provider": configured_name}
    if extra:
        status_payload.update(extra)
    status_payload["impl"] = provider.__class__.__name__
    return status_payload


def health(request: Request, response: Response) -> dict[str, Any]:
    settings = get_settings(request)
    analysis_factory = get_analysis_session_factory(request)
    spec_factory = get_spec_session_factory(request)
    llm_provider = get_llm_provider(request)
    embed_provider = get_embedding_provider(request)

    analysis_db = _check_database(analysis_factory)
    spec_db = _check_database(spec_factory)
    llm = _provider_status(llm_provider, settings.llm_provider, {"model": settings.llm_model})
    embed = _provider_status(
        embed_provider,
        settings.embed_provider,
        {"model": settings.embed_model, "dim": embed_provider.dim},
    )

    overall_status = (
        "ok" if analysis_db["status"] == "ok" and spec_db["status"] == "ok" else "degraded"
    )
    response.status_code = (
        status.HTTP_200_OK if overall_status == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return {
        "status": overall_status,
        "analysis_db": analysis_db,
        "spec_db": spec_db,
        "llm": llm,
        "embed": embed,
    }
