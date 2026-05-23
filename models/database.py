"""
ORACLE-X/N — Database Setup
=============================
SQLAlchemy async engine + session factory.
Defaults to SQLite for zero-config local runs.
"""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


def _get_settings():
    """Lazy import to avoid circular imports."""
    from config import OracleSettings
    return OracleSettings()


# ── Sync engine (used for scripts & seeding) ──────────────────────────────────

def _build_sync_url(db_url: str) -> str:
    """Convert async URL to sync URL if needed."""
    return db_url.replace("sqlite+aiosqlite", "sqlite")


settings = _get_settings()
_sync_url = _build_sync_url(settings.database_url)
_async_url = settings.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")

engine = create_engine(_sync_url, echo=False, connect_args={"check_same_thread": False})
SyncSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

async_engine = create_async_engine(_async_url, echo=False)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def get_db() -> Session:
    """Sync session generator (dependency injection for sync routes/scripts)."""
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Async session generator for FastAPI dependency injection."""
    async with AsyncSessionLocal() as session:
        yield session


def init_db() -> None:
    """Create all tables (idempotent)."""
    # Import all ORM models so Base.metadata is populated
    import models.user   # noqa: F401
    import models.item   # noqa: F401
    Base.metadata.create_all(bind=engine)
