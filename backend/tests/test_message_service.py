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
