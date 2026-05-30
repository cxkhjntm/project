"""Tests for artifact API endpoints."""

import os
import pytest
import tempfile
from typing import AsyncGenerator

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_session
from app.main import app
from app.models.artifact import Artifact
from app.models.room import Room


@pytest.fixture
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
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


@pytest.fixture
def sample_room(test_db_session: AsyncSession) -> Room:
    import uuid
    room = Room(
        id=str(uuid.uuid4()),
        name="Test Room",
        goal="Test goal",
        mode="code_document",
        strategy="standard",
        output_directory="/tmp/test-output",
        round_limit=5,
        status="completed",
    )
    test_db_session.add(room)
    return room


@pytest.fixture
def sample_artifact(test_db_session: AsyncSession, sample_room: Room) -> Artifact:
    import uuid
    artifact = Artifact(
        id=str(uuid.uuid4()),
        room_id=sample_room.id,
        artifact_type="markdown",
        title="Test Artifact",
        file_path="/tmp/test-output/artifact.md",
        summary="Test summary",
    )
    test_db_session.add(artifact)
    return artifact


class TestSynthesizeEndpoint:

    @pytest.mark.asyncio
    async def test_synthesize_returns_404_for_nonexistent_room(
        self, client: AsyncClient
    ) -> None:
        response = await client.post(
            "/api/rooms/nonexistent-room-id/synthesize",
            json={"artifact_type": "markdown"},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Room not found"

    @pytest.mark.asyncio
    async def test_synthesize_returns_400_for_room_without_messages(
        self, client: AsyncClient, sample_room: Room, test_db_session: AsyncSession
    ) -> None:
        await test_db_session.commit()
        response = await client.post(
            f"/api/rooms/{sample_room.id}/synthesize",
            json={"artifact_type": "markdown"},
        )
        assert response.status_code == 400
        assert "No messages" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_synthesize_creates_artifact(
        self, client: AsyncClient, sample_room: Room, test_db_session: AsyncSession
    ) -> None:
        from app.models.message import Message
        import uuid

        message = Message(
            id=str(uuid.uuid4()),
            room_id=sample_room.id,
            sender_type="expert",
            sender_id="test-expert",
            content="This is a test discussion message.",
            round=1,
        )
        test_db_session.add(message)
        await test_db_session.commit()

        with tempfile.TemporaryDirectory() as tmpdir:
            sample_room.output_directory = tmpdir
            await test_db_session.flush()

            response = await client.post(
                f"/api/rooms/{sample_room.id}/synthesize",
                json={"artifact_type": "markdown"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "artifact" in data
        assert data["artifact"]["room_id"] == sample_room.id
        assert data["artifact"]["artifact_type"] == "markdown"
        assert "content_preview" in data
        assert data["message"] == "Artifact generated successfully"


class TestListArtifactsEndpoint:

    @pytest.mark.asyncio
    async def test_list_artifacts_returns_404_for_nonexistent_room(
        self, client: AsyncClient
    ) -> None:
        response = await client.get("/api/rooms/nonexistent-room-id/artifacts")
        assert response.status_code == 404
        assert response.json()["detail"] == "Room not found"

    @pytest.mark.asyncio
    async def test_list_artifacts_returns_empty_list(
        self, client: AsyncClient, sample_room: Room, test_db_session: AsyncSession
    ) -> None:
        await test_db_session.commit()
        response = await client.get(f"/api/rooms/{sample_room.id}/artifacts")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_artifacts_returns_artifacts(
        self, client: AsyncClient, sample_artifact: Artifact, test_db_session: AsyncSession
    ) -> None:
        await test_db_session.commit()
        response = await client.get(
            f"/api/rooms/{sample_artifact.room_id}/artifacts"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == sample_artifact.id
        assert data[0]["title"] == "Test Artifact"


class TestGetArtifactContentEndpoint:

    @pytest.mark.asyncio
    async def test_get_content_returns_404_for_nonexistent_artifact(
        self, client: AsyncClient
    ) -> None:
        response = await client.get("/api/artifacts/nonexistent-id/content")
        assert response.status_code == 404
        assert response.json()["detail"] == "Artifact not found"

    @pytest.mark.asyncio
    async def test_get_content_returns_file_content(
        self, client: AsyncClient, sample_artifact: Artifact, test_db_session: AsyncSession
    ) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write("# Test Content\n\nThis is test artifact content.")
            temp_path = f.name

        try:
            sample_artifact.file_path = temp_path
            await test_db_session.commit()

            response = await client.get(
                f"/api/artifacts/{sample_artifact.id}/content"
            )
            assert response.status_code == 200
            data = response.json()
            assert "# Test Content" in data["content"]
            assert data["encoding"] == "utf-8"
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_get_content_returns_500_when_file_missing(
        self, client: AsyncClient, sample_artifact: Artifact, test_db_session: AsyncSession
    ) -> None:
        sample_artifact.file_path = "/nonexistent/path/artifact.md"
        await test_db_session.commit()

        response = await client.get(
            f"/api/artifacts/{sample_artifact.id}/content"
        )
        assert response.status_code == 500
        assert "Failed to read artifact file" in response.json()["detail"]
