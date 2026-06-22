"""Database clients for the two separate logical databases.

- **Analysis DB** (rebuildable): L1 graph + L4 groups + embeddings — :mod:`.analysis`.
- **Spec DB** (durable): L2 specs + L3 spec graph — :mod:`.spec`.

Two independent engines/sessions; nothing here couples the two databases. URLs come
from :class:`spec_atlas.config.Settings` (``ANALYSIS_DB_URL`` / ``SPEC_DB_URL``).
"""

from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from spec_atlas.config import Settings, get_settings

from .analysis import (
    AnalysisBase,
    Edge,
    Embedding,
    File,
    Group,
    Node,
    Repo,
)
from .spec import Spec, SpecBase, SpecEdge

__all__ = [
    "AnalysisBase",
    "SpecBase",
    "Repo",
    "File",
    "Node",
    "Edge",
    "Group",
    "Embedding",
    "Spec",
    "SpecEdge",
    "make_engine",
    "analysis_engine",
    "spec_engine",
    "analysis_session",
    "spec_session",
]


def make_engine(url: str) -> Engine:
    """Create a SQLAlchemy engine for ``url`` (psycopg3 driver expected)."""
    return create_engine(url, future=True, pool_pre_ping=True)


def _require(url: str | None, name: str) -> str:
    if not url:
        raise RuntimeError(
            f"{name} is not set. Provide it in .env (see .env.example) — "
            f"a reachable Postgres is required for database operations."
        )
    return url


def analysis_engine(settings: Settings | None = None) -> Engine:
    s = settings or get_settings()
    return make_engine(_require(s.analysis_db_url, "ANALYSIS_DB_URL"))


def spec_engine(settings: Settings | None = None) -> Engine:
    s = settings or get_settings()
    return make_engine(_require(s.spec_db_url, "SPEC_DB_URL"))


def analysis_session(settings: Settings | None = None) -> sessionmaker[Session]:
    return sessionmaker(bind=analysis_engine(settings), expire_on_commit=False, future=True)


def spec_session(settings: Settings | None = None) -> sessionmaker[Session]:
    return sessionmaker(bind=spec_engine(settings), expire_on_commit=False, future=True)
