"""Test database configuration."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from app.config import settings
from app.database import Base, engine, async_session_factory


def test_settings_defaults():
    assert settings.app_name == "Expert Room"
    assert settings.debug is False
    assert settings.database_url == "sqlite+aiosqlite:///./expert_room.db"
    assert settings.cors_origins == ["http://localhost:5173", "http://localhost:3000"]
    assert settings.encryption_key == ""
    assert settings.default_max_tokens == 4096
    assert settings.default_temperature == 0.7
    assert settings.max_discussion_rounds == 5
    assert settings.max_file_size_mb == 10


def test_settings_allowed_extensions():
    expected_extensions = [
        ".txt", ".md", ".json", ".csv", ".py", ".ts", ".js", ".tsx", ".jsx",
        ".html", ".css", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ]
    assert settings.allowed_extensions == expected_extensions


def test_settings_excluded_directories():
    expected_directories = [
        "node_modules", ".git", "dist", "build", ".next", ".venv",
        "__pycache__", "target", "coverage", ".idea", ".vscode",
    ]
    assert settings.excluded_directories == expected_directories


def test_database_engine_created():
    assert engine is not None
    assert "aiosqlite" in str(engine.url)


def test_session_factory_created():
    assert async_session_factory is not None


def test_base_class_has_metadata():
    assert hasattr(Base, "metadata")


@pytest.mark.asyncio
async def test_init_db_creates_tables():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    class TestModel(Base):
        __tablename__ = "test_model"
        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str] = mapped_column()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_engine.connect() as conn:
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result]
        assert "test_model" in tables

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_get_session_yields_session():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    test_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    import app.database
    original_factory = app.database.async_session_factory
    app.database.async_session_factory = test_factory

    try:
        from app.database import get_session
        gen = get_session()
        session = await gen.__anext__()
        assert isinstance(session, AsyncSession)
        assert session.is_active
        await gen.aclose()
    finally:
        app.database.async_session_factory = original_factory
        await test_engine.dispose()


@pytest.mark.asyncio
async def test_session_commit_on_success():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    test_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    import app.database
    original_factory = app.database.async_session_factory
    app.database.async_session_factory = test_factory

    try:
        from app.database import get_session
        gen = get_session()
        session = await gen.__anext__()

        await session.execute(text("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY)"))
        await session.execute(text("INSERT INTO test (id) VALUES (1)"))

        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass

        async with test_engine.connect() as conn:
            result = await conn.execute(text("SELECT COUNT(*) FROM test"))
            count = result.scalar()
            assert count == 1
    finally:
        app.database.async_session_factory = original_factory
        await test_engine.dispose()
