"""Tests for message service."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.message import MessageCreate
from app.services.message_service import message_service


@pytest.mark.asyncio
async def test_create_message(db_session: AsyncSession):
    """Test creating a message."""
    # Arrange
    data = MessageCreate(
        room_id="test-room-id",
        sender_type="expert",
        sender_id="role-architect",
        content="This is a test message",
        round=1,
    )

    # Act
    message = await message_service.create(db_session, data)

    # Assert
    assert message.id is not None
    assert message.room_id == "test-room-id"
    assert message.sender_type == "expert"
    assert message.sender_id == "role-architect"
    assert message.content == "This is a test message"
    assert message.round == 1


@pytest.mark.asyncio
async def test_get_messages_by_room(db_session: AsyncSession):
    """Test getting messages by room ID."""
    # Arrange
    room_id = "test-room-id"
    for i in range(3):
        data = MessageCreate(
            room_id=room_id,
            sender_type="expert",
            sender_id=f"role-{i}",
            content=f"Message {i}",
            round=1,
        )
        await message_service.create(db_session, data)

    # Act
    messages = await message_service.get_by_room(db_session, room_id)

    # Assert
    assert len(messages) == 3
    assert all(m.room_id == room_id for m in messages)


@pytest.mark.asyncio
async def test_get_message_by_id(db_session: AsyncSession):
    """Test getting a single message by ID."""
    # Arrange
    data = MessageCreate(
        room_id="test-room-id",
        sender_type="expert",
        sender_id="role-architect",
        content="Test message for get_by_id",
        round=1,
    )
    created = await message_service.create(db_session, data)

    # Act
    found = await message_service.get_by_id(db_session, created.id)

    # Assert
    assert found is not None
    assert found.id == created.id
    assert found.content == "Test message for get_by_id"
    assert found.room_id == "test-room-id"


@pytest.mark.asyncio
async def test_get_message_by_id_not_found(db_session: AsyncSession):
    """Test get_by_id returns None for non-existent message."""
    # Act
    found = await message_service.get_by_id(db_session, "non-existent-id")

    # Assert
    assert found is None


@pytest.mark.asyncio
async def test_get_latest_round(db_session: AsyncSession):
    """Test getting the latest round number for a room."""
    # Arrange
    room_id = "test-room-id"
    for round_num in [1, 2, 3]:
        data = MessageCreate(
            room_id=room_id,
            sender_type="expert",
            sender_id="role-architect",
            content=f"Message in round {round_num}",
            round=round_num,
        )
        await message_service.create(db_session, data)

    # Act
    latest = await message_service.get_latest_round(db_session, room_id)

    # Assert
    assert latest == 3


@pytest.mark.asyncio
async def test_get_latest_round_empty_room(db_session: AsyncSession):
    """Test get_latest_round returns 0 for empty room."""
    # Act
    latest = await message_service.get_latest_round(db_session, "empty-room")

    # Assert
    assert latest == 0


@pytest.mark.asyncio
async def test_count_by_room(db_session: AsyncSession):
    """Test counting messages in a room."""
    # Arrange
    room_id = "test-room-id"
    for i in range(5):
        data = MessageCreate(
            room_id=room_id,
            sender_type="expert",
            sender_id=f"role-{i}",
            content=f"Message {i}",
            round=1,
        )
        await message_service.create(db_session, data)

    # Act
    count = await message_service.count_by_room(db_session, room_id)

    # Assert
    assert count == 5


@pytest.mark.asyncio
async def test_count_by_room_empty(db_session: AsyncSession):
    """Test count_by_room returns 0 for empty room."""
    # Act
    count = await message_service.count_by_room(db_session, "empty-room")

    # Assert
    assert count == 0


@pytest.mark.asyncio
async def test_create_message_with_citations(db_session: AsyncSession):
    """Test creating a message with citations."""
    # Arrange
    data = MessageCreate(
        room_id="test-room-id",
        sender_type="expert",
        sender_id="role-architect",
        content="Message with citations",
        round=1,
        citations=[
            {"source_id": "src-1", "file": "main.py", "snippet": "def main():"},
            {"source_id": "src-2", "file": "README.md", "snippet": "# Project"},
        ],
    )

    # Act
    message = await message_service.create(db_session, data)

    # Assert
    assert message.id is not None
    assert message.citations is not None
    assert len(message.citations) == 2
    assert message.citations[0]["source_id"] == "src-1"
    assert message.citations[0]["file"] == "main.py"
    assert message.citations[0]["snippet"] == "def main():"
    assert message.citations[1]["source_id"] == "src-2"
