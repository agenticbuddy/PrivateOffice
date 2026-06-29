"""Database engine, session factory and schema bootstrap.

Uses async SQLAlchemy. Models use portable column types so the same schema runs on
PostgreSQL (production) and SQLite (tests). Schema is created with ``create_all`` for
this internal-install scope (no migration history needed yet).
"""
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    pass


# SQLite (tests) uses NullPool so each operation opens a fresh connection in the
# current event loop — avoids cross-loop reuse under pytest's per-test loops.
_is_sqlite = settings.database_url.startswith("sqlite")
_engine_kwargs = {"poolclass": NullPool} if _is_sqlite else {"pool_pre_ping": True}
engine = create_async_engine(settings.database_url, future=True, **_engine_kwargs)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields a request-scoped session."""
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create tables if missing. Imported here to avoid circular imports."""
    from sqlalchemy import text

    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # lightweight migration for DBs created before a column existed. Each ALTER runs
    # in its OWN transaction — on PostgreSQL a failed statement (column already exists)
    # poisons the whole transaction, which would otherwise roll back create_all above.
    for ddl in [
        "ALTER TABLE users ADD COLUMN design VARCHAR(16) DEFAULT 'glass'",
    ]:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(ddl))
        except Exception:  # noqa: BLE001 — column already exists
            pass
