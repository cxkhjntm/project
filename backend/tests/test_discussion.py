"""Tests for discussion API endpoints."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.room import Room, RoomParticipant
from app.routers.discussion import (
    control_discussion,
    get_discussion_status,
    get_messages,
    start_discussion,
    stream_messages,
)
from app.schemas.discussion import DiscussionAction, DiscussionControlRequest


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


@pytest.mark.asyncio
async def test_control_discussion_start(sample_room):
    sample_room.status = "draft"
    session = _mock_session_with_room(sample_room)
    request = DiscussionControlRequest(action=DiscussionAction.START)

    result = await control_discussion("test-room-id", request, session)

    assert result["status"] == "running"
    assert result["action"] == "start"
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_control_discussion_start_invalid_status(sample_room):
    sample_room.status = "running"
    session = _mock_session_with_room(sample_room)
    request = DiscussionControlRequest(action=DiscussionAction.START)

    with pytest.raises(HTTPException) as exc_info:
        await control_discussion("test-room-id", request, session)

    assert exc_info.value.status_code == 400
    assert "draft" in exc_info.value.detail


@pytest.mark.asyncio
async def test_control_discussion_pause(sample_room):
    sample_room.status = "running"
    session = _mock_session_with_room(sample_room)
    request = DiscussionControlRequest(action=DiscussionAction.PAUSE)

    result = await control_discussion("test-room-id", request, session)

    assert result["status"] == "paused"
    assert result["action"] == "pause"


@pytest.mark.asyncio
async def test_control_discussion_pause_invalid_status(sample_room):
    sample_room.status = "draft"
    session = _mock_session_with_room(sample_room)
    request = DiscussionControlRequest(action=DiscussionAction.PAUSE)

    with pytest.raises(HTTPException) as exc_info:
        await control_discussion("test-room-id", request, session)

    assert exc_info.value.status_code == 400
    assert "not running" in exc_info.value.detail


@pytest.mark.asyncio
async def test_control_discussion_resume(sample_room):
    sample_room.status = "paused"
    session = _mock_session_with_room(sample_room)
    request = DiscussionControlRequest(action=DiscussionAction.RESUME)

    result = await control_discussion("test-room-id", request, session)

    assert result["status"] == "running"
    assert result["action"] == "resume"


@pytest.mark.asyncio
async def test_control_discussion_resume_invalid_status(sample_room):
    sample_room.status = "running"
    session = _mock_session_with_room(sample_room)
    request = DiscussionControlRequest(action=DiscussionAction.RESUME)

    with pytest.raises(HTTPException) as exc_info:
        await control_discussion("test-room-id", request, session)

    assert exc_info.value.status_code == 400
    assert "not paused" in exc_info.value.detail


@pytest.mark.asyncio
async def test_control_discussion_stop_from_running(sample_room):
    sample_room.status = "running"
    session = _mock_session_with_room(sample_room)
    request = DiscussionControlRequest(action=DiscussionAction.STOP)

    result = await control_discussion("test-room-id", request, session)

    assert result["status"] == "stopped"
    assert result["action"] == "stop"


@pytest.mark.asyncio
async def test_control_discussion_stop_from_paused(sample_room):
    sample_room.status = "paused"
    session = _mock_session_with_room(sample_room)
    request = DiscussionControlRequest(action=DiscussionAction.STOP)

    result = await control_discussion("test-room-id", request, session)

    assert result["status"] == "stopped"
    assert result["action"] == "stop"


@pytest.mark.asyncio
async def test_control_discussion_stop_invalid_status(sample_room):
    sample_room.status = "draft"
    session = _mock_session_with_room(sample_room)
    request = DiscussionControlRequest(action=DiscussionAction.STOP)

    with pytest.raises(HTTPException) as exc_info:
        await control_discussion("test-room-id", request, session)

    assert exc_info.value.status_code == 400
    assert "cannot be stopped" in exc_info.value.detail


@pytest.mark.asyncio
async def test_control_discussion_room_not_found():
    session = _mock_session_with_room(None)
    request = DiscussionControlRequest(action=DiscussionAction.START)

    with pytest.raises(HTTPException) as exc_info:
        await control_discussion("nonexistent-id", request, session)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_discussion_status(sample_room):
    sample_room.status = "running"
    session = _mock_session_with_room(sample_room)

    result = await get_discussion_status("test-room-id", session)

    assert result.room_id == "test-room-id"
    assert result.status == "running"
    assert result.total_rounds == 5
    assert result.is_paused is False
    assert result.can_pause is True
    assert result.can_resume is False
    assert result.can_stop is True


@pytest.mark.asyncio
async def test_get_discussion_status_paused(sample_room):
    sample_room.status = "paused"
    session = _mock_session_with_room(sample_room)

    result = await get_discussion_status("test-room-id", session)

    assert result.status == "paused"
    assert result.is_paused is True
    assert result.can_pause is False
    assert result.can_resume is True
    assert result.can_stop is True


@pytest.mark.asyncio
async def test_get_discussion_status_draft(sample_room):
    sample_room.status = "draft"
    session = _mock_session_with_room(sample_room)

    result = await get_discussion_status("test-room-id", session)

    assert result.status == "draft"
    assert result.is_paused is False
    assert result.can_pause is False
    assert result.can_resume is False
    assert result.can_stop is False


@pytest.mark.asyncio
async def test_get_discussion_status_room_not_found():
    session = _mock_session_with_room(None)

    with pytest.raises(HTTPException) as exc_info:
        await get_discussion_status("nonexistent-id", session)

    assert exc_info.value.status_code == 404
