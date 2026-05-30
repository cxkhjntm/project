"""Tests for discussion API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.room import Room, RoomParticipant
from app.routers.discussion import start_discussion, get_messages, stream_messages


@pytest.fixture
def sample_room():
    room = Room(
        id="test-room-id",
        name="Test Room",
        goal="Test goal",
        mode="code_document",
        strategy="standard",
        output_directory="/tmp/test",
        round_limit=5,
        status="draft",
    )
    room.participants = [
        RoomParticipant(
            room_id="test-room-id",
            role_card_id="test-role-id",
            provider_id="test-provider-id",
        )
    ]
    return room


def _mock_session_with_room(room_or_none):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = room_or_none

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock(return_value=mock_result)
    return mock_session


@pytest.mark.asyncio
async def test_start_discussion_room_not_found():
    session = _mock_session_with_room(None)

    with pytest.raises(HTTPException) as exc_info:
        await start_discussion("nonexistent-id", session)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Room not found"


@pytest.mark.asyncio
async def test_start_discussion_invalid_status(sample_room):
    sample_room.status = "running"
    session = _mock_session_with_room(sample_room)

    with pytest.raises(HTTPException) as exc_info:
        await start_discussion("test-room-id", session)

    assert exc_info.value.status_code == 400
    assert "running" in exc_info.value.detail


@pytest.mark.asyncio
async def test_start_discussion_no_participants(sample_room):
    sample_room.participants = []
    session = _mock_session_with_room(sample_room)

    with pytest.raises(HTTPException) as exc_info:
        await start_discussion("test-room-id", session)

    assert exc_info.value.status_code == 400
    assert "no participants" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_messages_room_not_found():
    session = _mock_session_with_room(None)

    with pytest.raises(HTTPException) as exc_info:
        await get_messages("nonexistent-id", session=session)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Room not found"


@pytest.mark.asyncio
async def test_stream_messages_room_not_found():
    session = _mock_session_with_room(None)

    with pytest.raises(HTTPException) as exc_info:
        await stream_messages("nonexistent-id", session=session)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Room not found"


@pytest.mark.asyncio
async def test_start_discussion_completed_is_allowed(sample_room):
    sample_room.status = "completed"
    session = _mock_session_with_room(sample_room)

    sample_room.participants[0].provider = MagicMock()
    sample_room.participants[0].provider.default_model = "gpt-4"
    sample_room.participants[0].provider.base_url = "https://api.openai.com/v1"
    sample_room.participants[0].role_card = MagicMock()
    sample_room.participants[0].role_card.name = "Test Expert"

    response = await start_discussion("test-room-id", session)
    assert response is not None
    assert sample_room.status == "running"
