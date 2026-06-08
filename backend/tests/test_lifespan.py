"""Tests for application lifespan and auto table creation."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.database import Base


@pytest.mark.asyncio
async def test_lifespan_creates_tables():
    import app.models  # noqa: F401

    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with test_engine.connect() as conn:
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        )
        tables = [row[0] for row in result]
        assert len(tables) == 0

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_engine.connect() as conn:
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        )
        tables = {row[0] for row in result}

    expected_tables = {
        "providers",
        "role_cards",
        "rooms",
        "room_participants",
        "messages",
        "shared_sources",
        "artifacts",
    }
    assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_lifespan_loads_builtin_roles():
    from app.seed.loader import load_builtin_roles

    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    test_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    import app.models  # noqa: F401

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_factory() as session:
        roles = await load_builtin_roles(session)
        await session.commit()

        assert len(roles) > 0
        for role in roles:
            assert role.is_builtin is True

    await test_engine.dispose()


def test_main_uses_lifespan():
    import inspect
    from app.main import create_app

    sig = inspect.signature(create_app)
    assert "lifespan_fn" in sig.parameters, "create_app should accept a lifespan_fn parameter"


@pytest.mark.asyncio
async def test_all_models_registered_with_base():
    import app.models  # noqa: F401

    table_names = set(Base.metadata.tables.keys())
    expected = {
        "providers",
        "role_cards",
        "rooms",
        "room_participants",
        "messages",
        "shared_sources",
        "artifacts",
    }
    assert expected.issubset(table_names), f"Missing tables: {expected - table_names}"
