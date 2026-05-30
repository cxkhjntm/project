"""Tests for path validation in sources API."""

import os
import uuid
from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_session
from app.main import app
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
    room = Room(
        id=str(uuid.uuid4()),
        name="Test Room",
        goal="Test goal",
        mode="code_document",
        strategy="standard",
        output_directory="/tmp/test-output",
        round_limit=5,
        status="draft",
    )
    test_db_session.add(room)
    return room


class TestFolderPathTraversalRejection:
    """Test that path traversal attempts are rejected for folder sources."""

    @pytest.mark.asyncio
    async def test_rejects_dot_dot_traversal_in_folder_path(
        self, client: AsyncClient, sample_room: Room, test_db_session: AsyncSession
    ) -> None:
        """Test that path with .. traversal is rejected."""
        await test_db_session.commit()

        response = await client.post(
            f"/api/rooms/{sample_room.id}/sources",
            data={
                "source_type": "folder",
                "path": "/some/path/../../etc",
            },
        )
        assert response.status_code == 400
        assert "traversal" in response.json()["message"].lower() or "invalid" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_rejects_relative_dot_dot_traversal(
        self, client: AsyncClient, sample_room: Room, test_db_session: AsyncSession
    ) -> None:
        """Test that relative path with .. is rejected."""
        await test_db_session.commit()

        response = await client.post(
            f"/api/rooms/{sample_room.id}/sources",
            data={
                "source_type": "folder",
                "path": "../../../etc/passwd",
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_rejects_path_with_double_dot_in_middle(
        self, client: AsyncClient, sample_room: Room, test_db_session: AsyncSession
    ) -> None:
        """Test that path with .. in the middle is rejected."""
        await test_db_session.commit()

        response = await client.post(
            f"/api/rooms/{sample_room.id}/sources",
            data={
                "source_type": "folder",
                "path": "/app/data/../../../etc",
            },
        )
        assert response.status_code == 400


class TestValidFolderPathAccepted:
    """Test that valid folder paths are accepted."""

    @pytest.mark.asyncio
    async def test_accepts_valid_folder_within_base_directory(
        self, client: AsyncClient, sample_room: Room, test_db_session: AsyncSession
    ) -> None:
        """Test that a valid folder path within base directory is accepted."""
        await test_db_session.commit()

        base_dir = os.getcwd()
        test_dir = os.path.join(base_dir, "test_folder_source")
        os.makedirs(test_dir, exist_ok=True)
        try:
            test_file = os.path.join(test_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test content")

            response = await client.post(
                f"/api/rooms/{sample_room.id}/sources",
                data={
                    "source_type": "folder",
                    "path": test_dir,
                },
            )
            assert response.status_code == 201
            data = response.json()
            assert data["source_type"] == "folder"
        finally:
            import shutil
            shutil.rmtree(test_dir, ignore_errors=True)


class TestFileSourceNotAffected:
    """Test that file sources are not affected by path validation."""

    @pytest.mark.asyncio
    async def test_file_source_not_subject_to_path_validation(
        self, client: AsyncClient, sample_room: Room, test_db_session: AsyncSession
    ) -> None:
        """Test that file uploads don't go through folder path validation."""
        await test_db_session.commit()

        file_content = b"test file content"
        
        response = await client.post(
            f"/api/rooms/{sample_room.id}/sources",
            data={
                "source_type": "file",
            },
            files={"file": ("test.txt", file_content, "text/plain")},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["source_type"] == "file"

    @pytest.mark.asyncio
    async def test_text_source_not_subject_to_path_validation(
        self, client: AsyncClient, sample_room: Room, test_db_session: AsyncSession
    ) -> None:
        """Test that text sources don't go through path validation."""
        await test_db_session.commit()

        response = await client.post(
            f"/api/rooms/{sample_room.id}/sources",
            data={
                "source_type": "text",
                "content": "Some pasted text content",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["source_type"] == "text"

    @pytest.mark.asyncio
    async def test_file_source_with_dot_dot_filename_is_not_rejected(
        self, client: AsyncClient, sample_room: Room, test_db_session: AsyncSession
    ) -> None:
        """Test that file uploads with .. in filename don't trigger path validation."""
        await test_db_session.commit()

        file_content = b"test content"
        
        response = await client.post(
            f"/api/rooms/{sample_room.id}/sources",
            data={
                "source_type": "file",
            },
            files={"file": ("test..file.txt", file_content, "text/plain")},
        )
        assert response.status_code == 201


class TestEdgeCases:
    """Test edge cases for path validation."""

    @pytest.mark.asyncio
    async def test_folder_path_required_for_folder_source_type(
        self, client: AsyncClient, sample_room: Room, test_db_session: AsyncSession
    ) -> None:
        """Test that path is required when source_type is folder."""
        await test_db_session.commit()

        response = await client.post(
            f"/api/rooms/{sample_room.id}/sources",
            data={
                "source_type": "folder",
            },
        )
        assert response.status_code == 400
        assert "path is required" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_room_not_found_returns_404(
        self, client: AsyncClient, test_db_session: AsyncSession
    ) -> None:
        """Test that nonexistent room returns 404."""
        response = await client.post(
            "/api/rooms/nonexistent-room-id/sources",
            data={
                "source_type": "folder",
                "path": "/some/path",
            },
        )
        assert response.status_code == 404
        assert "room not found" in response.json()["message"].lower()
