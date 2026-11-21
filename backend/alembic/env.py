"""Alembic environment configuration for HRMS Platform."""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add the backend directory to sys.path so models can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import all models so Alembic can detect them for auto-generate
from app.db.base import Base  # noqa: F401 — registers all models via __init__

# this is the Alembic Config object, which provides access to the .ini file
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata — Alembic uses this for auto-generate
target_metadata = Base.metadata


def get_database_url() -> str:
    """Read DATABASE_URL from environment, falling back to alembic.ini value."""
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        # SQLAlchemy 2.x: replace deprecated postgres:// scheme
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return db_url
    return config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine. Calls to context.execute() emit the given
    string to the script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
