"""Fixtures for DB-backed tests.

These require a reachable Postgres (ANALYSIS_DB_URL / SPEC_DB_URL). When neither is
configured or reachable, the whole module is skipped — so the offline suite stays
green with no database (testing-standard: offline & free by default)."""

from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from spec_atlas import db
from spec_atlas.config import get_settings


def _reachable(url: str) -> bool:
    try:
        engine = db.make_engine(url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def require_dbs() -> None:
    s = get_settings()
    if not s.analysis_db_url or not s.spec_db_url:
        pytest.skip("ANALYSIS_DB_URL / SPEC_DB_URL not set — DB tests skipped (offline).")
    if not _reachable(s.analysis_db_url) or not _reachable(s.spec_db_url):
        pytest.skip("Postgres not reachable — DB tests skipped.")


@pytest.fixture
def migrated(require_dbs: None) -> None:
    """Apply both DBs' migrations (`alembic upgrade head`), then tear down."""
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    try:
        yield
    finally:
        command.downgrade(cfg, "base")
