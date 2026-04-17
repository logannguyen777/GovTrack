"""
backend/migrations/env.py
Alembic environment — uses GovFlow settings for the DB URL.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---------------------------------------------------------------------------
# Ensure the backend package is importable
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# ---------------------------------------------------------------------------
# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
# ---------------------------------------------------------------------------
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url from GovFlow settings
try:
    from src.config import settings as _settings

    _dsn = _settings.hologres_dsn
    # Ensure asyncpg DSN is converted to sync form for Alembic
    if _dsn.startswith("postgresql+asyncpg://"):
        _dsn = _dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    config.set_main_option("sqlalchemy.url", _dsn)
except Exception as exc:
    # Falls back to alembic.ini value
    import warnings

    warnings.warn(f"Could not load GovFlow settings: {exc}", stacklevel=1)

# ---------------------------------------------------------------------------
# Metadata — not using SQLAlchemy models (raw SQL migrations)
# ---------------------------------------------------------------------------
target_metadata = None


# ---------------------------------------------------------------------------
# Run migrations
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
