"""Async SQLAlchemy engine + session factory.

Supports SQLite (dev / tests) and PostgreSQL (production) through the
`DATABASE_URL` setting. The `get_db` dependency yields one session per request.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.core.config import PROJECT_ROOT, get_settings


def build_engine(url: str) -> AsyncEngine:
    """Create an async engine, normalising sqlite paths and pooling."""
    kwargs: dict[str, Any] = {"echo": False}
    if url.startswith("sqlite"):
        # Make relative sqlite paths resolve from the project root regardless of CWD.
        if ":///./" in url:
            rel = url.split(":///./", 1)[1]
            abs_path = (PROJECT_ROOT / rel).resolve()
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            url = f"sqlite+aiosqlite:///{abs_path.as_posix()}"
        if url.endswith(":memory:") or url.rstrip("/").endswith("sqlite+aiosqlite:"):
            # In-memory DB must share a single connection across sessions.
            kwargs["poolclass"] = StaticPool
        kwargs["connect_args"] = {"check_same_thread": False}
    eng = create_async_engine(url, **kwargs)
    if url.startswith("sqlite"):
        # SQLite ignores ON DELETE CASCADE unless foreign keys are switched on per connection.
        @event.listens_for(eng.sync_engine, "connect")
        def _enable_fk(dbapi_conn: Any, _record: Any) -> None:
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return eng


engine: AsyncEngine = build_engine(get_settings().database_url)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one DB session per request, rolled back on error."""
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def create_all_tables() -> None:
    """Create all tables (dev convenience; production uses Alembic)."""
    from app.models import Base  # imported here to avoid import cycles

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
