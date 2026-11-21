"""
Alembic base module — imports all models so metadata is fully populated.
Import this in alembic/env.py to enable auto-generate migrations.
"""
from app.core.database import Base  # noqa: F401 — the SQLAlchemy declarative Base
import app.models  # noqa: F401 — registers every model table with Base.metadata

__all__ = ["Base"]
