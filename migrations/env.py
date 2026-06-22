"""Alembic environment — two databases (Analysis + Spec) via the multidb pattern.

A single ``alembic upgrade head`` migrates both DBs. Each database has its own
``alembic_version`` table (they are physically separate). URLs are loaded from
``spec_atlas.config`` so there are no credentials in version control.
"""

from __future__ import annotations

import re
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from spec_atlas.config import get_settings
from spec_atlas.db.analysis import AnalysisBase
from spec_atlas.db.spec import SpecBase

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# engine_name -> target metadata
TARGET_METADATA = {
    "analysis": AnalysisBase.metadata,
    "spec": SpecBase.metadata,
}

DB_NAMES = re.split(r",\s*", config.get_main_option("databases", ""))


def _url_for(name: str) -> str:
    settings = get_settings()
    url = {"analysis": settings.analysis_db_url, "spec": settings.spec_db_url}[name]
    if not url:
        raise RuntimeError(
            f"No URL for database '{name}'. Set "
            f"{'ANALYSIS_DB_URL' if name == 'analysis' else 'SPEC_DB_URL'} in .env "
            f"(see .env.example) — a reachable Postgres is required to migrate."
        )
    return url


def run_migrations_offline() -> None:
    for name in DB_NAMES:
        context.configure(
            url=_url_for(name),
            target_metadata=TARGET_METADATA[name],
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
            upgrade_token=f"{name}_upgrades",
            downgrade_token=f"{name}_downgrades",
        )
        with context.begin_transaction():
            context.run_migrations(engine_name=name)


def run_migrations_online() -> None:
    engines: dict[str, dict] = {}
    for name in DB_NAMES:
        engines[name] = {
            "engine": engine_from_config(
                {"sqlalchemy.url": _url_for(name)},
                prefix="sqlalchemy.",
                poolclass=pool.NullPool,
            )
        }

    for rec in engines.values():
        rec["connection"] = rec["engine"].connect()
        rec["transaction"] = rec["connection"].begin()

    try:
        for name, rec in engines.items():
            context.configure(
                connection=rec["connection"],
                target_metadata=TARGET_METADATA[name],
                upgrade_token=f"{name}_upgrades",
                downgrade_token=f"{name}_downgrades",
            )
            context.run_migrations(engine_name=name)
        for rec in engines.values():
            rec["transaction"].commit()
    except Exception:
        for rec in engines.values():
            rec["transaction"].rollback()
        raise
    finally:
        for rec in engines.values():
            rec["connection"].close()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
