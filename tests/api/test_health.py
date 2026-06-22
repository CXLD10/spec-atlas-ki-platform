"""Health endpoint tests for app wiring and dependency state."""

from __future__ import annotations

from fastapi import Response
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

from spec_atlas.api.app import create_app
from spec_atlas.api.health import health
from spec_atlas.config import Settings


def _session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _request_for(app: object) -> Request:
    scope = {"type": "http", "method": "GET", "path": "/health", "headers": [], "app": app}
    return Request(scope)


def test_health_reports_ok_with_fake_providers_and_reachable_databases() -> None:
    app = create_app(Settings(_env_file=None))
    app.state.analysis_session_factory = _session_factory()
    app.state.spec_session_factory = _session_factory()
    response = Response()

    payload = health(_request_for(app), response)

    assert response.status_code == 200
    assert payload == {
        "status": "ok",
        "analysis_db": {"status": "ok"},
        "spec_db": {"status": "ok"},
        "llm": {
            "status": "ok",
            "provider": "fake",
            "model": "gemini-1.5-flash",
            "impl": "FakeLLMProvider",
        },
        "embed": {
            "status": "ok",
            "provider": "fake",
            "model": "BAAI/bge-small-en-v1.5",
            "dim": 384,
            "impl": "FakeEmbeddingProvider",
        },
    }


def test_health_reports_degraded_when_databases_are_not_configured() -> None:
    app = create_app(Settings(_env_file=None))
    response = Response()

    payload = health(_request_for(app), response)

    assert response.status_code == 503
    assert payload["status"] == "degraded"
    assert payload["analysis_db"] == {"status": "not_configured"}
    assert payload["spec_db"] == {"status": "not_configured"}
