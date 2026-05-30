import pytest
from typing import AsyncGenerator

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_session
from app.main import app
from app.seed.loader import load_builtin_roles


@pytest.fixture
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        await load_builtin_roles(session)
        await session.commit()
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def client(test_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield test_db_session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


class TestEndToEndFlow:

    @pytest.mark.asyncio
    async def test_full_flow_provider_to_room(self, client: AsyncClient) -> None:
        """create provider -> get role cards -> create room -> verify room"""
        provider_response = await client.post(
            "/api/providers",
            json={
                "name": "OpenAI Provider",
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-test-key-12345",
                "default_model": "gpt-4o",
                "default_temperature": 0.7,
                "default_max_tokens": 4096,
            },
        )
        assert provider_response.status_code == 201
        provider_data = provider_response.json()
        provider_id = provider_data["id"]

        assert provider_data["name"] == "OpenAI Provider"
        assert provider_data["base_url"] == "https://api.openai.com/v1"
        assert provider_data["default_model"] == "gpt-4o"
        assert provider_data["enabled"] is True
        assert provider_data["api_key_masked"] != "sk-test-key-12345"
        assert "***" in provider_data["api_key_masked"]

        role_cards_response = await client.get("/api/role-cards", params={"builtin": "true"})
        assert role_cards_response.status_code == 200
        role_cards = role_cards_response.json()

        assert len(role_cards) >= 1
        role_card_ids = [rc["id"] for rc in role_cards]

        first_role = role_cards[0]
        assert "id" in first_role
        assert "name" in first_role
        assert "system_prompt" in first_role
        assert first_role["is_builtin"] is True

        room_response = await client.post(
            "/api/rooms",
            json={
                "name": "E2E Test Room",
                "goal": "Design a new feature for the application",
                "mode": "code_document",
                "strategy": "standard",
                "output_directory": "/tmp/e2e-test-output",
                "round_limit": 5,
                "participants": [
                    {
                        "role_card_id": role_card_ids[0],
                        "provider_id": provider_id,
                    }
                ],
            },
        )
        assert room_response.status_code == 201
        room_data = room_response.json()
        room_id = room_data["id"]

        assert room_data["name"] == "E2E Test Room"
        assert room_data["goal"] == "Design a new feature for the application"
        assert room_data["mode"] == "code_document"
        assert room_data["strategy"] == "standard"
        assert room_data["output_directory"] == "/tmp/e2e-test-output"
        assert room_data["round_limit"] == 5
        assert room_data["status"] == "draft"

        assert len(room_data["participants"]) == 1
        participant = room_data["participants"][0]
        assert participant["role_card_id"] == role_card_ids[0]
        assert participant["provider_id"] == provider_id
        assert participant["room_id"] == room_id

        get_room_response = await client.get(f"/api/rooms/{room_id}")
        assert get_room_response.status_code == 200
        fetched_room = get_room_response.json()

        assert fetched_room["id"] == room_id
        assert fetched_room["name"] == "E2E Test Room"
        assert fetched_room["goal"] == "Design a new feature for the application"
        assert len(fetched_room["participants"]) == 1
        assert fetched_room["participants"][0]["role_card_id"] == role_card_ids[0]
        assert fetched_room["participants"][0]["provider_id"] == provider_id

    @pytest.mark.asyncio
    async def test_provider_appears_in_list_after_creation(self, client: AsyncClient) -> None:
        """created provider appears in GET /api/providers"""
        create_response = await client.post(
            "/api/providers",
            json={
                "name": "Test Provider",
                "base_url": "https://api.example.com/v1",
                "api_key": "test-api-key",
                "default_model": "gpt-4",
            },
        )
        assert create_response.status_code == 201
        provider_id = create_response.json()["id"]

        list_response = await client.get("/api/providers")
        assert list_response.status_code == 200
        providers = list_response.json()

        provider_ids = [p["id"] for p in providers]
        assert provider_id in provider_ids

    @pytest.mark.asyncio
    async def test_room_appears_in_list_after_creation(self, client: AsyncClient) -> None:
        """created room appears in GET /api/rooms"""
        provider_response = await client.post(
            "/api/providers",
            json={
                "name": "List Test Provider",
                "base_url": "https://api.example.com/v1",
                "api_key": "test-key",
                "default_model": "gpt-4",
            },
        )
        provider_id = provider_response.json()["id"]

        role_cards_response = await client.get("/api/role-cards", params={"builtin": "true"})
        role_card_id = role_cards_response.json()[0]["id"]

        create_response = await client.post(
            "/api/rooms",
            json={
                "name": "List Test Room",
                "goal": "Test room listing",
                "mode": "document",
                "strategy": "standard",
                "output_directory": "/tmp/list-test",
                "round_limit": 3,
                "participants": [
                    {"role_card_id": role_card_id, "provider_id": provider_id}
                ],
            },
        )
        assert create_response.status_code == 201
        room_id = create_response.json()["id"]

        list_response = await client.get("/api/rooms")
        assert list_response.status_code == 200
        rooms = list_response.json()

        room_ids = [r["id"] for r in rooms]
        assert room_id in room_ids

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient) -> None:
        """GET /api/health returns ok"""
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "0.1.0"
