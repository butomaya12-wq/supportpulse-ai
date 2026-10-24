"""Migration runner. Only explicitly acknowledged isolated synthetic staging DBs."""
import os
import re
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from app.db import Base
from app import models  # noqa: F401 - register all declared tables

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def validate_migration_target() -> str:
    if os.getenv("SP_MODE") != "synthetic_staging":
        raise RuntimeError("Refusing migration outside synthetic_staging")
    if os.getenv("SP_STAGING_SYNTHETIC_ONLY") != "YES":
        raise RuntimeError("Refusing migration without synthetic-only acknowledgment")
    if os.getenv("SP_SCHEMA_MIGRATE_CONFIRM") != "MIGRATE_ISOLATED_STAGING_ONLY":
        raise RuntimeError("Refusing migration without explicit staging migration authorization")
    raw_url = os.getenv("DATABASE_URL", "")
    if not raw_url.startswith("postgresql+psycopg://"):
        raise RuntimeError("Refusing migration against non-PostgreSQL database")
    parsed = make_url(raw_url)
    database = parsed.database or ""
    if (not re.fullmatch(r"[a-zA-Z0-9_]+", database)
            or not ("stage" in database.lower() or "staging" in database.lower())):
        raise RuntimeError("Refusing migration: database name must identify staging")
    if os.getenv("SP_STAGE_DB_NAME") != database:
        raise RuntimeError("Refusing migration: expected database name mismatch")
    if os.getenv("SP_SCHEMA_MIGRATION_ROLE") != "migrator":
        raise RuntimeError("Refusing migration: dedicated migrator acknowledgment missing")
    return raw_url


url = validate_migration_target()


def run_migrations_offline() -> None:
    # Offline SQL is supported for code review, with all the same configuration gates.
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True,
                      dialect_opts={"paramstyle": "named"}, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(url, poolclass=NullPool, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata,
                              compare_type=True)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
