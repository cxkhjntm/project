"""Database configuration with SQLAlchemy async engine."""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def migrate_compat_schema() -> None:
    """Apply small SQLite compatibility migrations for existing local databases."""
    async with engine.begin() as conn:
        if conn.dialect.name != "sqlite":
            return

        result = await conn.execute(text("PRAGMA table_info(artifacts)"))
        columns = {row[1] for row in result.fetchall()}
        if columns and "artifact_kind" not in columns:
            await conn.execute(
                text("ALTER TABLE artifacts ADD COLUMN artifact_kind TEXT NOT NULL DEFAULT 'final'")
            )


__all__ = [
    "Base",
    "engine",
    "async_session_factory",
    "get_session",
    "init_db",
    "migrate_compat_schema",
]
