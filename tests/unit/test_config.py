"""Unit tests for spec_atlas.config — env-validated settings."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from spec_atlas.config import Settings, get_settings


def test_defaults_are_offline_and_zero_cost() -> None:
    s = Settings(_env_file=None)
    assert s.llm_provider == "fake"
    assert s.embed_provider == "fake"
    assert s.offline is True
    # Embedding dim must line up with the schema's vector(384).
    assert s.embed_dim == 384
    # No DB required to construct settings.
    assert s.analysis_db_url is None
    assert s.spec_db_url is None


def test_env_overrides_are_read_and_validated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("EMBED_PROVIDER", "fastembed")
    monkeypatch.setenv("ANALYSIS_DB_URL", "postgresql+psycopg://u:p@h:5432/a")
    monkeypatch.setenv("SPEC_DB_URL", "postgresql+psycopg://u:p@h:5432/s")

    s = Settings(_env_file=None)

    assert s.llm_provider == "gemini"
    assert s.embed_provider == "fastembed"
    assert s.offline is False
    assert s.analysis_db_url is not None and s.analysis_db_url.endswith("/a")
    assert s.spec_db_url is not None and s.spec_db_url.endswith("/s")


def test_invalid_provider_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "not-a-provider")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()
